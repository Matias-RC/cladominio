"""Motor de reglas de Cachipún Evolución.

No depende de pygame: la UI, la IA (o un entorno tipo gym) llaman a los métodos
públicos y leen el estado. Flujo de una ronda:

    SELECCION  -> cada jugador hace cambios y llama a listo()
    DECISION   -> cada jugador llama a decidir(acepta)
    COMBATE    -> si ambos aceptan: duelo a duelo, cada jugador puede descartar() y luego
                  jugar_carta(); el duelo se resuelve cuando ambos han jugado
    REVELACION -> se muestra el resultado; cada jugador llama a listo()
    MERCADO    -> compras; cada jugador llama a listo()  -> fin de ronda
    FIN        -> partida terminada (ver .ganador)

`pendientes()` dice qué jugadores aún deben actuar en la fase actual.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum

from ..config import Config
from .efectos import EFECTOS, ResultadoDuelo
from .fenotipos import Fenotipos
from .modelos import Carta, Especie, Jugador, PocionActiva, nombre_aleatorio


class Fase(str, Enum):
    SELECCION = "seleccion"
    DECISION = "decision"
    COMBATE = "combate"
    REVELACION = "revelacion"
    MERCADO = "mercado"
    FIN = "fin"


class ErrorJugada(Exception):
    """Acción inválida. El mensaje está pensado para mostrarse al jugador."""


@dataclass
class Coste:
    cromos: float = 0.0
    diversidad: float = 0.0
    usa_cambio_gratis: bool = False

    @property
    def nulo(self) -> bool:
        return self.cromos == 0 and self.diversidad == 0


@dataclass
class ResultadoEtapa2:
    ronda: int
    decisiones: tuple[bool, bool]
    hubo_combate: bool
    cromos: list[float] = field(default_factory=lambda: [0.0, 0.0])
    duelos: list[ResultadoDuelo] = field(default_factory=list)
    victorias: list[int] = field(default_factory=lambda: [0, 0])


@dataclass
class ResultadoCladogenesis:
    exito: bool
    probabilidad: float
    madre: Especie
    hija: Especie | None = None


@dataclass
class Evento:
    ronda: int
    texto: str
    visible: int | None = None  # None = ambos jugadores


def _r(x: float) -> float:
    return round(x, 2)


class Motor:
    def __init__(self, reglas: Config, nombres: tuple[str, str] = ("Jugador 1", "Jugador 2"),
                 semilla: int | None = None):
        self.cfg = reglas
        self.fen = Fenotipos(reglas)
        self.rng = random.Random(semilla)
        self.ronda = 1
        self.fase = Fase.SELECCION
        self.eventos: list[Evento] = []
        self.ganador: int | None = None
        self.empate = False
        self.motivo_fin = ""

        self._listos: set[int] = set()
        self._decisiones: dict[int, bool] = {}
        self.manos: dict[int, list[Carta]] = {}
        self.descartes: dict[int, int] = {0: 0, 1: 0}
        self._jugadas: dict[int, Carta] = {}
        self._delta_div: dict[tuple[int, int], float] = {}
        self.resultado: ResultadoEtapa2 | None = None
        # intel[j] = (ronda, cartas que mostró el rival de j)
        self.intel: dict[int, tuple[int, list[str]] | None] = {0: None, 1: None}

        cj = reglas.jugadores
        self.jugadores = [Jugador(i, nombres[i], float(cj.cromos_iniciales)) for i in range(2)]
        for j in self.jugadores:
            for _ in range(cj.especies_iniciales):
                fen = self.rng.choice(self.fen.orden)
                j.especies.append(Especie(
                    id=j.nuevo_id(), nombre=nombre_aleatorio(self.rng),
                    dominante=fen, recesivo=fen,
                    diversidad=float(reglas.diversidad.inicial),
                ))
        self._log("Comienza la partida. Ronda 1: selección natural.")

    # ================================================================ utilidades
    def _log(self, texto: str, visible: int | None = None) -> None:
        self.eventos.append(Evento(self.ronda, texto, visible))

    def eventos_para(self, jid: int, desde: int = 0) -> list[Evento]:
        return [e for e in self.eventos[desde:] if e.visible is None or e.visible == jid]

    def rival(self, jid: int) -> Jugador:
        return self.jugadores[1 - jid]

    def articulo(self, art: str) -> Config:
        try:
            return self.cfg.mercado.articulos[art]
        except KeyError:
            raise ErrorJugada(f"Artículo desconocido: {art}")

    def _exigir_fase(self, *fases: Fase) -> None:
        if self.fase not in fases:
            raise ErrorJugada(f"No se puede hacer eso en la fase '{self.fase.value}'.")

    def _modificar_cromos(self, j: Jugador, delta: float) -> None:
        j.cromos = _r(max(float(self.cfg.jugadores.cromos_minimos), j.cromos + delta))

    def _modificar_diversidad(self, e: Especie, delta: float) -> None:
        e.diversidad = _r(min(float(self.cfg.diversidad.maxima), e.diversidad + delta))
        e.gastada = min(e.gastada, max(0.0, e.diversidad))

    @property
    def terminado(self) -> bool:
        return self.fase == Fase.FIN

    def pendientes(self) -> set[int]:
        """Jugadores que todavía deben actuar en la fase actual."""
        if self.fase in (Fase.SELECCION, Fase.REVELACION, Fase.MERCADO):
            return {0, 1} - self._listos
        if self.fase == Fase.DECISION:
            return {0, 1} - set(self._decisiones)
        if self.fase == Fase.COMBATE:
            return {0, 1} - set(self._jugadas)
        return set()

    # ================================================================ etapa 1: selección
    def coste_seleccion(self, jid: int, especie_id: int, dominante: str, recesivo: str) -> Coste:
        e = self.jugadores[jid].especie(especie_id)
        cs = self.cfg.seleccion
        c = Coste()
        if dominante != e.dominante:
            ady = self.fen.son_adyacentes(e.dominante, dominante)
            if e.cambio_gratis == "libre" or (e.cambio_gratis == "adyacente" and ady):
                c.usa_cambio_gratis = True
            else:
                f = 1.0 if ady else float(cs.factor_no_adyacente)
                c.cromos += cs.cambio_dominante.cromos * f
                c.diversidad += cs.cambio_dominante.diversidad * f
        if recesivo != e.recesivo:
            f = 1.0 if self.fen.son_adyacentes(e.recesivo, recesivo) else float(cs.factor_no_adyacente)
            c.cromos += cs.cambio_recesivo.cromos * f
            c.diversidad += cs.cambio_recesivo.diversidad * f
        c.cromos, c.diversidad = _r(c.cromos), _r(c.diversidad)
        return c

    def validar_seleccion(self, jid: int, especie_id: int, dominante: str, recesivo: str) -> Coste:
        self._exigir_fase(Fase.SELECCION)
        if dominante not in self.fen.vence or recesivo not in self.fen.vence:
            raise ErrorJugada("Fenotipo desconocido.")
        j = self.jugadores[jid]
        e = j.especie(especie_id)
        if dominante == e.dominante and recesivo == e.recesivo:
            raise ErrorJugada("No hay cambios que aplicar.")
        c = self.coste_seleccion(jid, especie_id, dominante, recesivo)
        if c.cromos > j.cromos:
            raise ErrorJugada(f"Faltan cromos ({c.cromos:g} > {j.cromos:g}).")
        minima = float(self.cfg.diversidad.minima_tras_gasto)
        if c.diversidad > 0 and e.efectiva - c.diversidad < minima:
            raise ErrorJugada(f"Diversidad insuficiente: debe quedar al menos {minima:g}%.")
        return c

    def seleccionar(self, jid: int, especie_id: int, dominante: str, recesivo: str) -> Coste:
        c = self.validar_seleccion(jid, especie_id, dominante, recesivo)
        j = self.jugadores[jid]
        e = j.especie(especie_id)
        self._modificar_cromos(j, -c.cromos)
        e.gastada = _r(e.gastada + c.diversidad)
        if c.usa_cambio_gratis:
            e.cambio_gratis = "ninguno"
        n = self.fen.nombre
        self._log(f"{e.nombre}: {n(e.dominante)}/{n(e.recesivo)} → {n(dominante)}/{n(recesivo)} "
                  f"(-{c.cromos:g} cromos, -{c.diversidad:g}% diversidad)", jid)
        e.dominante, e.recesivo = dominante, recesivo
        return c

    def activar_pocion(self, jid: int, articulo: str, especie_id: int) -> None:
        self._exigir_fase(Fase.SELECCION)
        a = self.articulo(articulo)
        if a.tipo != "pocion":
            raise ErrorJugada("Ese artículo no es una poción.")
        j = self.jugadores[jid]
        if j.inventario[articulo] <= 0:
            raise ErrorJugada(f"No tienes {a.nombre}.")
        e = j.especie(especie_id)
        if any(p.articulo == articulo for p in e.pociones):
            raise ErrorJugada(f"{e.nombre} ya tiene {a.nombre} activa.")
        if a.efecto not in EFECTOS:
            raise ErrorJugada(f"Efecto '{a.efecto}' no implementado.")
        j.inventario[articulo] -= 1
        e.pociones.append(PocionActiva(articulo, int(a.duracion), self.ronda))
        self._log(f"Activas {a.nombre} en {e.nombre} ({a.duracion} rondas).", jid)

    def prob_cladogenesis(self, jid: int) -> float:
        c = self.cfg.cladogenesis
        j = self.jugadores[jid]
        p = c.prob_base + c.prob_por_carta * j.inventario["carta_mutacion"] + c.prob_por_fallo * j.fallos_cladogenesis
        return max(0.0, min(float(c.prob_maxima), p))

    def madres_validas(self, jid: int) -> list[Especie]:
        minima = float(self.cfg.cladogenesis.diversidad_minima_madre)
        return [e for e in self.jugadores[jid].especies if e.diversidad >= minima]

    def intentar_cladogenesis(self, jid: int, articulo: str, madre_id: int | None = None) -> ResultadoCladogenesis:
        self._exigir_fase(Fase.SELECCION)
        a = self.articulo(articulo)
        if a.tipo != "potenciador":
            raise ErrorJugada("Ese artículo no es un potenciador de macroevolución.")
        j = self.jugadores[jid]
        if j.inventario[articulo] <= 0:
            raise ErrorJugada(f"No tienes {a.nombre}.")
        if len(j.especies) >= self.cfg.jugadores.max_especies:
            raise ErrorJugada("Ya tienes el máximo de especies.")
        validas = self.madres_validas(jid)
        if not validas:
            raise ErrorJugada("Ninguna especie tiene diversidad suficiente para especiarse.")
        if a.elegir_madre:
            if madre_id is None:
                raise ErrorJugada("Debes elegir la especie madre.")
            madre = j.especie(madre_id)
            if madre not in validas:
                raise ErrorJugada(f"{madre.nombre} no tiene diversidad suficiente "
                                  f"(mín. {self.cfg.cladogenesis.diversidad_minima_madre}%).")
        else:
            madre = self.rng.choice(validas)

        cc = self.cfg.cladogenesis
        p = self.prob_cladogenesis(jid)
        exito = self.rng.random() < p
        j.inventario[articulo] -= 1
        if cc.consume_cartas == "al_intentar" or (exito and cc.consume_cartas == "al_exito"):
            j.inventario["carta_mutacion"] = 0

        res = ResultadoCladogenesis(exito, p, madre)
        if not exito:
            j.fallos_cladogenesis += 1
            self._log(f"Cladogénesis ({a.nombre}) desde {madre.nombre}: fallida ({p:.0%}).", jid)
            return res

        j.fallos_cladogenesis = 0
        parte = _r(madre.diversidad * float(cc.fraccion_hija))
        frac_restante = (madre.diversidad - parte) / madre.diversidad if madre.diversidad else 0
        madre.diversidad = _r(madre.diversidad - parte)
        madre.gastada = _r(madre.gastada * frac_restante)
        genero = madre.nombre.split()[0]
        hija = Especie(
            id=j.nuevo_id(), nombre=nombre_aleatorio(self.rng, genero),
            dominante=madre.dominante, recesivo=madre.recesivo, diversidad=parte,
            cambio_gratis=str(a.get("cambio_gratis_hija", "ninguno")),
            madre=madre.id, ronda_nacimiento=self.ronda,
        )
        j.especies.append(hija)
        res.hija = hija
        self._log(f"¡Cladogénesis! {madre.nombre} da origen a {hija.nombre} ({parte:g}% de diversidad).", jid)
        return res

    # ================================================================ etapa 2: decisión y combate
    def decidir(self, jid: int, acepta: bool) -> None:
        self._exigir_fase(Fase.DECISION)
        if jid in self._decisiones:
            raise ErrorJugada("Ya decidiste esta ronda.")
        self._decisiones[jid] = bool(acepta)
        if len(self._decisiones) == 2:
            self._resolver_decision()

    def _resolver_decision(self) -> None:
        d = (self._decisiones[0], self._decisiones[1])
        k = float(self.cfg.combate.k)
        res = ResultadoEtapa2(self.ronda, d, hubo_combate=all(d))
        self.resultado = res

        if all(d):
            self._iniciar_combate()
            return

        if not any(d):  # paz mutua
            bono = float(self.cfg.paz.bono_diversidad)
            for j in self.jugadores:
                self._modificar_cromos(j, k)
                res.cromos[j.id] = k
                for e in j.especies:
                    self._modificar_diversidad(e, bono)
                if self.cfg.paz.anula_pociones_activadas:
                    for e in j.especies:
                        perdidas = [p for p in e.pociones if p.ronda_activacion == self.ronda]
                        for p in perdidas:
                            e.pociones.remove(p)
                            self._log(f"La paz anuló {self.articulo(p.articulo).nombre} en {e.nombre}.", j.id)
            self._log(f"Paz mutua: ambos ganan {k:g} cromos y +{bono:g}% de diversidad por especie.")
        else:  # rechazo unilateral
            g = 0 if d[0] else 1
            premio = _r(k * float(self.cfg.combate.factor_rechazo_unilateral))
            self._modificar_cromos(self.jugadores[g], premio)
            res.cromos[g] = premio
            self._log(f"{self.jugadores[g].nombre} aceptó y {self.jugadores[1 - g].nombre} rechazó: "
                      f"{self.jugadores[g].nombre} gana {premio:g} cromos.")
        self._listos.clear()
        self.fase = Fase.REVELACION

    # ---------------------------------------------------------------- combate
    @property
    def n_duelos(self) -> int:
        return int(self.cfg.combate.cartas)

    def _iniciar_combate(self) -> None:
        cc = self.cfg.combate
        self.manos = {j.id: [self._robar_carta(j) for _ in range(self.n_duelos)] for j in self.jugadores}
        self.descartes = {0: int(cc.descartes), 1: int(cc.descartes)}
        self._jugadas = {}
        self._delta_div = {}
        if cc.modo == "automatico":
            for i in range(self.n_duelos):
                self._resolver_duelo(self.manos[0][i], self.manos[1][i])
            self._cerrar_combate()
        else:
            self.fase = Fase.COMBATE

    def _peso_especie(self, e: Especie) -> float:
        modo = self.cfg.combate.peso_especie
        if modo == "uniforme":
            return 1.0
        if modo == "diversidad":
            return max(0.0, e.diversidad)
        return e.efectiva

    def _robar_carta(self, j: Jugador) -> Carta:
        """Saca una carta del pool genético: especie según su peso, fenotipo según su expresión."""
        pesos = [self._peso_especie(e) for e in j.especies]
        if sum(pesos) <= 0:
            pesos = [1.0] * len(j.especies)
        e = self.rng.choices(j.especies, weights=pesos)[0]
        dist = e.expresion(self.fen.orden, float(self.cfg.expresion.prob_dominante))
        fen = self.rng.choices(list(dist), weights=list(dist.values()))[0]
        return Carta(fen, e.id)

    def ya_jugo(self, jid: int) -> bool:
        return jid in self._jugadas

    def descartar(self, jid: int, indices: list[int]) -> None:
        """Devuelve las cartas `indices` de la mano al pool y roba otras tantas."""
        self._exigir_fase(Fase.COMBATE)
        if self.ya_jugo(jid):
            raise ErrorJugada("Ya jugaste tu carta en este duelo.")
        mano = self.manos[jid]
        indices = sorted(set(indices))
        if not indices:
            raise ErrorJugada("Selecciona cartas para descartar.")
        if any(i < 0 or i >= len(mano) for i in indices):
            raise ErrorJugada("Carta inválida.")
        if len(indices) > self.descartes[jid]:
            raise ErrorJugada(f"Solo te quedan {self.descartes[jid]} descarte(s).")
        j = self.jugadores[jid]
        for i in indices:
            mano[i] = self._robar_carta(j)
        self.descartes[jid] -= len(indices)
        self._log(f"Descartas {len(indices)} carta(s) y robas otras tantas del pool genético.", jid)

    def jugar_carta(self, jid: int, indice: int) -> None:
        self._exigir_fase(Fase.COMBATE)
        if self.ya_jugo(jid):
            raise ErrorJugada("Ya jugaste tu carta en este duelo.")
        mano = self.manos[jid]
        if not 0 <= indice < len(mano):
            raise ErrorJugada("Carta inválida.")
        self._jugadas[jid] = mano.pop(indice)
        if len(self._jugadas) == 2:
            self._resolver_duelo(self._jugadas[0], self._jugadas[1])
            self._jugadas = {}
            if len(self.resultado.duelos) >= self.n_duelos:
                self._cerrar_combate()

    def _resolver_duelo(self, a: Carta, b: Carta) -> ResultadoDuelo:
        cc = self.cfg.combate
        por_duelo = float(cc.k) / self.n_duelos
        res = self.resultado
        arts = self.cfg.mercado.articulos
        i = len(res.duelos)
        r = self.fen.duelo(a.fenotipo, b.fenotipo)
        g = None if r == 0 else (0 if r > 0 else 1)
        d = ResultadoDuelo(i, (a, b), g)
        if g is not None:
            p = 1 - g
            res.victorias[g] += 1
            d.cromos[g] += por_duelo
            d.cromos[p] -= por_duelo
            d.diversidad[g] += float(cc.diversidad_por_duelo_ganado)
            d.diversidad[p] -= float(cc.diversidad_por_duelo_perdido)
            for lado, cuando in ((g, "al_ganar"), (p, "al_perder")):
                esp = self.jugadores[lado].especie(d.cartas[lado].especie_id)
                for poc in esp.pociones:
                    art = arts[poc.articulo]
                    fn = getattr(EFECTOS[art.efecto], cuando)
                    if fn:
                        fn(d, lado, dict(art.get("params", {})))
        # cromos y diversidad se aplican al cerrar el combate (no hay extinciones a mitad)
        for lado in (0, 1):
            res.cromos[lado] += d.cromos[lado]
            clave = (lado, d.cartas[lado].especie_id)
            self._delta_div[clave] = self._delta_div.get(clave, 0.0) + d.diversidad[lado]
        for vis, txt in d.notas:
            self._log(f"Duelo {i + 1}: {txt}", vis)
        res.duelos.append(d)
        return d

    def cartas_jugadas(self, jid: int) -> list[str]:
        """Fenotipos que `jid` ha jugado en el combate en curso (son públicos)."""
        if not self.resultado:
            return []
        return [d.cartas[jid].fenotipo for d in self.resultado.duelos]

    def _cerrar_combate(self) -> None:
        res = self.resultado
        for j in self.jugadores:
            self._modificar_cromos(j, res.cromos[j.id])
            res.cromos[j.id] = _r(res.cromos[j.id])
        for (lado, eid), dd in self._delta_div.items():
            j = self.jugadores[lado]
            e = j.especie(eid)
            if dd:
                self._modificar_diversidad(e, dd)
                self._log(f"{e.nombre}: {dd:+g}% de diversidad en combate (queda {e.diversidad:g}%).", lado)
            if e.diversidad <= 0:
                j.especies.remove(e)
                self._log(f"{e.nombre} se ha extinguido.", lado)
                self._log(f"Una especie de {j.nombre} se ha extinguido.", 1 - lado)

        # revelación: cada jugador ve las cartas que jugó el rival
        for j in (0, 1):
            self.intel[j] = (self.ronda, self.cartas_jugadas(1 - j))
        v = res.victorias
        self._log(f"Combate: {self.jugadores[0].nombre} {v[0]} – {v[1]} {self.jugadores[1].nombre} "
                  f"(cromos {res.cromos[0]:+g} / {res.cromos[1]:+g}).")
        self._listos.clear()
        self.fase = Fase.REVELACION

    # ================================================================ etapa 3: mercado
    def comprar(self, jid: int, articulo: str) -> None:
        self._exigir_fase(Fase.MERCADO)
        a = self.articulo(articulo)
        j = self.jugadores[jid]
        if j.cromos < a.precio:
            raise ErrorJugada(f"Faltan cromos para {a.nombre}.")
        self._modificar_cromos(j, -float(a.precio))
        j.inventario[articulo] += 1
        self._log(f"Compras {a.nombre} (-{a.precio} cromos).", jid)

    # ================================================================ transiciones
    def listo(self, jid: int) -> None:
        self._exigir_fase(Fase.SELECCION, Fase.REVELACION, Fase.MERCADO)
        self._listos.add(jid)
        if len(self._listos) < 2:
            return
        self._listos.clear()
        if self.fase == Fase.SELECCION:
            self._decisiones.clear()
            self.resultado = None
            self.fase = Fase.DECISION
        elif self.fase == Fase.REVELACION:
            if self._comprobar_extincion():
                return
            n = float(self.cfg.mercado.ingreso_por_ronda)
            for j in self.jugadores:
                self._modificar_cromos(j, n)
            self._log(f"Mercado: ambos reciben {n:g} cromos.")
            self.fase = Fase.MERCADO
        elif self.fase == Fase.MERCADO:
            self._fin_de_ronda()

    def _terminar(self, ganador: int | None, motivo: str) -> None:
        self.ganador = ganador
        self.empate = ganador is None
        self.motivo_fin = motivo
        self.fase = Fase.FIN
        self._log(motivo)

    def _comprobar_extincion(self) -> bool:
        muertos = [j for j in self.jugadores if not j.vivo]
        if not muertos:
            return False
        if len(muertos) == 2:
            self._terminar(None, "Ambos jugadores se quedaron sin especies: empate.")
        else:
            g = 1 - muertos[0].id
            self._terminar(g, f"{muertos[0].nombre} se quedó sin especies. ¡Gana {self.jugadores[g].nombre}!")
        return True

    def _fin_de_ronda(self) -> None:
        regen = float(self.cfg.diversidad.regeneracion_por_ronda)
        for j in self.jugadores:
            for e in j.especies:
                e.gastada = 0.0
                if regen:
                    self._modificar_diversidad(e, regen)
                for p in list(e.pociones):
                    p.rondas_restantes -= 1
                    if p.rondas_restantes <= 0:
                        e.pociones.remove(p)
                        self._log(f"{self.articulo(p.articulo).nombre} se agotó en {e.nombre}.", j.id)

        meta = int(self.cfg.victoria.fenotipos_distintos)
        cubiertos = [len(j.fenotipos_cubiertos()) for j in self.jugadores]
        ganan = [j for j in self.jugadores if cubiertos[j.id] >= meta]
        max_r = int(self.cfg.victoria.max_rondas)
        if ganan or (max_r and self.ronda >= max_r):
            if len(ganan) == 1:
                self._terminar(ganan[0].id, f"¡{ganan[0].nombre} cubre {meta} fenotipos y gana!")
            else:
                candidatos = ganan or self.jugadores
                clave = lambda j: (cubiertos[j.id], sum(e.diversidad for e in j.especies))
                candidatos = sorted(candidatos, key=clave, reverse=True)
                if clave(candidatos[0]) == clave(candidatos[1]):
                    self._terminar(None, "Empate perfecto.")
                else:
                    self._terminar(candidatos[0].id, f"¡Gana {candidatos[0].nombre} por desempate "
                                                     f"(fenotipos cubiertos y diversidad total)!")
            return

        self.ronda += 1
        self.fase = Fase.SELECCION
        self._log(f"Ronda {self.ronda}: selección natural.")

    # ================================================================ observación
    def observacion(self, jid: int) -> dict:
        """Todo lo que el jugador `jid` puede saber. Útil para IA / entornos RL."""
        j, r = self.jugadores[jid], self.rival(jid)
        pdom = float(self.cfg.expresion.prob_dominante)
        return {
            "ronda": self.ronda,
            "fase": self.fase.value,
            "pendiente": jid in self.pendientes(),
            "propio": {
                "cromos": j.cromos,
                "inventario": dict(j.inventario),
                "fallos_cladogenesis": j.fallos_cladogenesis,
                "prob_cladogenesis": self.prob_cladogenesis(jid),
                "especies": [{
                    "id": e.id, "nombre": e.nombre, "dominante": e.dominante, "recesivo": e.recesivo,
                    "diversidad": e.diversidad, "efectiva": e.efectiva, "cambio_gratis": e.cambio_gratis,
                    "pociones": [(p.articulo, p.rondas_restantes) for p in e.pociones],
                    "expresion": e.expresion(self.fen.orden, pdom),
                } for e in j.especies],
                "mano": [(c.fenotipo, c.especie_id) for c in self.manos.get(jid, [])]
                if self.fase == Fase.COMBATE else None,
                "descartes": self.descartes[jid] if self.fase == Fase.COMBATE else None,
            },
            "rival": {
                "nombre": r.nombre,
                "cromos": r.cromos,
                "cartas_reveladas": self.intel[jid],
                "jugadas_este_combate": self.cartas_jugadas(1 - jid) if self.fase == Fase.COMBATE else [],
            },
        }
