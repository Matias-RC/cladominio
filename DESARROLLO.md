# Guía de desarrollo

## Ejecutar

```bash
.venv/Scripts/python.exe main.py                 # juego (F11 = pantalla completa)
.venv/Scripts/python.exe main.py --semilla 42    # partida reproducible
.venv/Scripts/python.exe simular.py -n 500       # IA vs IA sin ventana, para probar balance
```

## Estructura

```
config/
  reglas.yaml        reglas y balance (k, n, precios, probabilidades, quién vence a quién...)
  ui.yaml            colores, fuentes, tamaños, rutas de sprites
  *.local.yaml       (opcional) se mezcla encima del base: útil para experimentar sin tocarlo
cladominio/
  config.py          carga YAML con acceso por atributo (cfg.combate.k)
  core/              REGLAS PURAS, sin pygame
    fenotipos.py     grafo del pentágono: vence / adyacencias
    modelos.py       Especie, Jugador, Carta (dataclasses)
    efectos.py       efectos de pociones (registro con decorador)
    motor.py         máquina de estados de la partida
    analisis.py      cálculos de apoyo (mazo esperado, ventaja estimada)
  ia/                IAs (interfaz: IA(motor, jid, semilla).actuar())
  ui/                todo lo de pygame
    app.py           bucle principal + Director (qué escena toca)
    tema.py          fuentes, colores, carga de sprites
    dibujo.py        primitivas estilo boceto, pentágono, iconos, cartas, barras
    widgets.py       Boton, ZonaClic
    escenas/         una pantalla por etapa (duelo.py = mano, arrastre y revelación de cada duelo)
main.py              entrada del juego
simular.py           simulación IA vs IA
```

La separación clave es **core ↔ ui**: el motor no sabe nada de pantallas. La UI solo llama a
métodos públicos del motor (`seleccionar`, `decidir`, `comprar`, `listo`...) y lee su estado.

## El motor

Fases por ronda: `SELECCION → DECISION → [COMBATE] → REVELACION → MERCADO → (siguiente ronda)`.

`COMBATE` (si ambos aceptan y `combate.modo: interactivo`): cada jugador tiene una mano de
`combate.cartas` cartas robadas de su pool genético. Por cada duelo puede `descartar(jid, indices)`
(máx. `combate.descartes` cartas en todo el combate) y luego `jugar_carta(jid, indice)`. Cuando ambos
han jugado se resuelve ese duelo; las cartas jugadas son públicas (`cartas_jugadas(jid)`). Los cromos y
la diversidad se aplican todos al cerrar el combate, así que ninguna especie se extingue a mitad.

- `motor.pendientes()` → qué jugadores deben actuar aún en la fase actual.
- Las acciones inválidas lanzan `ErrorJugada` con un mensaje para el jugador.
- `motor.observacion(jid)` → dict con todo lo que `jid` puede saber (respeta la información oculta).
- `motor.eventos` → registro; cada `Evento` tiene `visible` (None = público, o el id del jugador).
- Toda la aleatoriedad pasa por `motor.rng` (semilla reproducible).

### Para RL / gym

El motor ya tiene lo necesario para envolverlo en un `gym.Env`: `observacion(jid)` como
observación, las acciones de cada fase como espacio de acciones, `pendientes()` para saber a quién
le toca y `simular.py` como ejemplo del bucle. Una política se registra en `cladominio/ia/__init__.py`
(`IAS`) y se elige con `python main.py --ia nombre`.

## Cómo extender

| Quiero...                         | Dónde                                                                 |
| --------------------------------- | --------------------------------------------------------------------- |
| Cambiar balance                   | `config/reglas.yaml` (se recarga al empezar cada partida)             |
| Cambiar quién vence a quién       | `fenotipos.vence` en `reglas.yaml` (se valida que no haya ciclos de 2) |
| Nueva poción                      | función `@efecto("x")` en `core/efectos.py` + artículo en `reglas.yaml` |
| Nuevo potenciador de especiación  | solo `reglas.yaml` (`tipo: potenciador`, `elegir_madre`, `cambio_gratis_hija`) |
| Nueva IA                          | clase en `cladominio/ia/`, registrar en `IAS`                         |
| Verbos de la revelación ("Piedra rompe Tijera") | `fenotipos.verbos` en `reglas.yaml`              |
| Nueva fase / pantalla             | `Fase` en `motor.py`, escena en `ui/escenas/`, registrar en `ESCENAS_FASE` (`ui/app.py`) |
| Colores, fuentes                  | `config/ui.yaml`                                                      |
| Sprites                           | ver abajo                                                             |

## Sprites (opcionales)

Todo se dibuja por código, pero si un archivo existe se usa en su lugar
(rutas en `config/ui.yaml`, PNG con fondo transparente):

| Archivo                          | Tamaño recomendado | Uso                                  |
| -------------------------------- | ------------------ | ------------------------------------ |
| `assets/fenotipos/piedra.png`    | 64×64              | icono en pentágono, cartas, listas   |
| `assets/fenotipos/tijera.png`    | 64×64              |                                      |
| `assets/fenotipos/fosforo.png`   | 64×64              |                                      |
| `assets/fenotipos/papel.png`     | 64×64              |                                      |
| `assets/fenotipos/pistola.png`   | 64×64              |                                      |
| `assets/cromo.png`               | 64×64              | icono de cromos (hélice de ADN)      |
| `assets/carta.png`               | 120×160            | fondo de las cartas de combate       |

Para pixel art: dibuja a 32×32 (o 16×16) y escálalo ×2/×4 con vecino más cercano antes de guardarlo
a 64×64, así se mantiene nítido (el juego reescala con suavizado).

## Decisiones de diseño tomadas (revisables en `reglas.yaml`)

El README deja varias reglas como propuesta; esto es lo que se implementó:

- **Pentágono:** orden `piedra, tijera, fósforo, papel, pistola`; cada uno vence a los 2 siguientes.
  En un pentágono con 5 fenotipos, cada vecino es necesariamente uno al que vences o uno que te vence,
  así que "adyacente" = vecino en el dibujo.
- **Coste de selección:** cambiar dominante o recesivo tiene un coste fijo (cromos + diversidad),
  ×1,5 si el nuevo fenotipo no es adyacente.
- **Diversidad gastada:** baja la diversidad *disponible* (y el peso de la especie al repartir cartas)
  hasta el final de la ronda. La diversidad perdida en combate es permanente.
- **Mazo:** cada carta sale de una especie al azar ponderada por diversidad disponible, y muestra
  el dominante con prob. 0,7.
- **Duelos:** la diversidad ganada/perdida va a la especie que jugó esa carta. A 0 % se extingue.
  Sin especies, pierdes.
- **Peripátrico:** eliges la madre; la hija hereda el fenotipo. **Parapátrico:** madre al azar, pero
  la hija tiene un cambio de dominante gratis a un nodo adyacente.
- **Cladogénesis:** prob. = 30 % + 15 % por carta de mutación + 10 % por cada fallo previo (máx. 95 %).
  Las cartas se consumen al intentarlo; la hija se lleva el 50 % de la diversidad de la madre.
- **Pociones:** se activan en la etapa 1, duran X rondas (cuentan aunque no haya combate). Con paz
  mutua, las activadas esa misma ronda se pierden ("costo oculto de la paz").
- **Victoria:** se comprueba al final de cada ronda. Si ambos cumplen, desempata el número de
  fenotipos cubiertos y luego la diversidad total.
- **Combate interactivo:** se juega duelo a duelo arrastrando cartas; cada revelación da información
  para el siguiente duelo. Los descartes (3 por combate) devuelven cartas al pool y roban otras con las
  mismas probabilidades, así que solo sirven si tu pool es variado (generalistas o varias especies).
  `combate.modo: automatico` vuelve a los 6 duelos simultáneos sin intervención.
