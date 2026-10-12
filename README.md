# Cachipún Evolución: el dominio de los clados

> Juego de estrategia para 2 jugadores sobre evolución, especiación y selección natural.
> Los puntos marcados son reglas sugeridas que aún hay que probar y equilibrar.

## 1. Objetivo

Gana el primer jugador que tenga **5 especies vivas que cubran los 5 fenotipos** (piedra, papel, tijera, fósforo, pistola), con un fenotipo dominante distinto en cada una.

## 2. Componentes

- **Fenotipos:** piedra, papel, tijera, fósforo y pistola. Cada uno le gana a 2 y pierde con 2 (pentágono sin fenotipo superior).
- **Especie:** tiene un punto **dominante**, un punto **recesivo** y su propia **diversidad (%)**.
- **Diversidad:** se lleva **por especie**, no de forma global. Parte en 50%. Es vida y recurso a la vez. Si una especie llega a 0%, se extingue.
- **Cromos:** moneda del juego. Cada jugador parte con 30.

## 3. Inicio

Cada jugador parte con **una especie**, 50% de diversidad en ella y 30 cromos.

### Información oculta

Los fenotipos de las especies del rival **no son públicos**. La única información que tienes sobre ellos es:

- Las **cartas que el rival jugó en la etapa 2 de la ronda anterior** (si hubo combate).

Con eso puedes inferir qué fenotipos tiene, pero nunca con certeza: el rival puede haber cambiado de fenotipo en la etapa 1 de esta ronda, o tener especies que aún no ha mostrado.

## 4. Ciclo de ronda (3 etapas)

### Etapa 1: Selección natural

Gastas cromos **y diversidad** para asignar fenotipo a una especie:

- **Especialista:** dominante y recesivo en el mismo fenotipo (fuerte, predecible).
- **Generalista:** dominante en un fenotipo y recesivo en otro (flexible, más débil en el primero).

También activas los consumibles comprados la ronda anterior: pociones sobre una especie o intentos de cladogénesis.
La diversidad gastada **se recarga sola** al final de la ronda.

### Etapa 2: Decisión de combate

Cada jugador decide **en secreto y a la vez** si acepta o rechaza.

|                | Rival acepta          | Rival rechaza          |
| -------------- | --------------------- | ---------------------- |
| **Yo acepto**  | Combate               | Gano 1,5k , mi rival 0 |
| **Yo rechazo** | Rival gana 1,5k, yo 0 | Ambos ganamos k        |

**Combate:** cada jugador recibe un mazo de 6 cartas aleatorias, tomadas de las expresiones fenotípicas de sus especies (el dominante con más probabilidad que el recesivo). Se juegan **simultáneamente** 6 duelos. Por cada duelo ganado, +k/6 cromos para ti y −k/6 para el rival.

**Revelación:** al terminar el combate, las cartas jugadas quedan a la vista de ambos. Es la única fuente de información para la ronda siguiente.

### Etapa 3: Mercado

Ambos reciben **n cromos** y pueden comprar:

1. **Pociones** (duran X rondas, se aplican a una especie propia):
   - _Cuello de botella:_ cuando esa especie pierde duelos, baja la diversidad del rival.
   - _Efecto fundador:_ cuando esa especie pierde, pierde un poco de diversidad pero gana cromos, y el rival no gana nada.
2. **Cartas de mutación:** suben la probabilidad de especiación. Cuestan cromos y son acumulables.
3. **Potenciadores de macroevolución** (para usar en la etapa 1 siguiente):
   - _Peripátrico:_ más caro, **eliges** de qué especie nace la nueva.
   - _Parapátrico:_ más barato, debes elegir un **nodo adyacente** (tabla de adyacencias) a la especie madre.

## 5. Cladogénesis

- La nueva especie hereda el fenotipo de la madre.
- Cuesta diversidad a la madre (se divide el pool) .
- Después puedes reasignar el fenotipo de la hija, pagando cromos y diversidad.
- La probabilidad de éxito aumenta con cartas de mutación. Conviene un **piso mínimo** para no frustrarse muchas rondas seguidas.

**Tabla de adyacencias [propuesta]:** cada fenotipo es adyacente a sus 2 vecinos en el pentágono (no a los que derrota). Especiarse a un fenotipo cercano es barato, y cubrir los 5 exige rutas largas.

## 6. La paz estratégica

**Situación típica:** sospecho (por las cartas que mostró el rival) que mi especie pierde contra la suya. No quiero gastar cromos y diversidad cambiando de fenotipo porque la cladogénesis viene la próxima ronda. Prefiero **asegurar mis recursos** y rechazo el combate.

Reglas que sostienen esta decisión **[propuestas]**:

1. **Perder un duelo cuesta diversidad**, no solo cromos (p. ej. −2% por duelo perdido).
2. **Ganar un duelo da diversidad** (p. ej. +1%). El agresor tiene un incentivo real.
3. **Bono de paz mutua:** además de k cromos, ambos recargan +5% de diversidad.
4. **Costo oculto de la paz:** en una ronda de paz mutua no puedes activar pociones.
5. **Rechazo protegido:** si rechazas y el rival acepta, tu diversidad no se ve afectada, aunque él gana 1,5k.
6. **Paz = sin información:** si ninguno combate, no se revelan cartas. Ambos llegan a la ronda siguiente con datos viejos.

**Lógica resultante:**

- Si crees que te dominan, **rechazar** conserva cromos y diversidad aunque regales 1,5k.
- Si crees tener ventaja, **aceptar** te da diversidad y cromos, pero si el rival también rechaza, solo obtienes k.
- Como los fenotipos son ocultos, todo es una apuesta sobre lo que el rival hizo desde su última aparición. Combatir da información, y la paz la oculta.

## 7. Qué hay que equilibrar

- **Valores de k, n y precios:** son la principal perilla de balance. Con k = 6 y 30 cromos iniciales, un combate mueve como máximo 6 cromos de diferencia.
- **Rechazo unilateral (1,5k vs 2k):** si aceptar rinde mucho más, nadie rechaza. Hay que probarlo.
- **Diversidad por duelo:** si es muy alta, el combate es demasiado punitivo; si es muy baja, la paz pierde sentido.
- **Valor de la información:** ¿cuánto vale ver las cartas del rival? Debería compensar parte del riesgo de combatir.
- **Extinción:** definir qué pasa con una especie en 0% y cómo interactúa con el cuello de botella.
- **Victoria con fenotipos mixtos:** en esta versión solo cuenta el fenotipo dominante .
