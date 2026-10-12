"""IA sencilla basada en reglas.

Interfaz que debe cumplir cualquier IA (útil si luego entrenas una política):
    ia = MiIA(motor, jid, semilla)
    ia.actuar()   # se llama cuando jid está en motor.pendientes(); debe dejarlo resuelto
"""
from __future__ import annotations

import random

from ..core.analisis import ventaja_estimada
from ..core.motor import ErrorJugada, Fase, Motor


class IAHeuristica:
    reserva = 6.0  # cromos que intenta no gastar

    def __init__(self, motor: Motor, jid: int, semilla: int | None = None):
        self.m = motor
        self.jid = jid
        self.rng = random.Random(semilla)

    @property
    def yo(self):
        return self.m.jugadores[self.jid]

    def actuar(self) -> None:
        f = self.m.fase
        if f == Fase.SELECCION:
            self._seleccion()
            self.m.listo(self.jid)
        elif f == Fase.DECISION:
            self.m.decidir(self.jid, self._decidir())
        elif f == Fase.COMBATE:
            self._combate()
        elif f == Fase.REVELACION:
            self.m.listo(self.jid)
        elif f == Fase.MERCADO:
            self._mercado()
            self.m.listo(self.jid)

    # ------------------------------------------------------------ etapa 1
    def _intentar(self, fn, *args) -> bool:
        try:
            fn(*args)
            return True
        except ErrorJugada:
            return False

    def _seleccion(self) -> None:
        m, j = self.m, self.yo
        arts = m.cfg.mercado.articulos

        # pociones: sobre la especie más diversa que no la tenga
        for art, cant in list(j.inventario.items()):
            if cant > 0 and arts[art].tipo == "pocion":
                for e in sorted(j.especies, key=lambda e: -e.diversidad):
                    if self._intentar(m.activar_pocion, self.jid, art, e.id):
                        break

        # cladogénesis
        for art, cant in list(j.inventario.items()):
            while j.inventario[art] > 0 and arts[art].tipo == "potenciador":
                madres = sorted(m.madres_validas(self.jid), key=lambda e: -e.diversidad)
                if not madres:
                    break
                if not self._intentar(m.intentar_cladogenesis, self.jid, art, madres[0].id):
                    break

        # mover especies duplicadas (o con cambio gratis) a fenotipos no cubiertos
        vistos: set[str] = set()
        for e in sorted(j.especies, key=lambda e: -e.diversidad):
            libres = [f for f in m.fen.orden if f not in j.fenotipos_cubiertos()]
            duplicada = e.dominante in vistos
            vistos.add(e.dominante)
            if not libres or not (duplicada or e.cambio_gratis != "ninguno"):
                continue
            opciones = sorted(libres, key=lambda f: m.coste_seleccion(self.jid, e.id, f, e.recesivo).cromos)
            for f in opciones:
                c = m.coste_seleccion(self.jid, e.id, f, e.recesivo)
                if c.cromos == 0 or j.cromos - c.cromos >= self.reserva:
                    if self._intentar(m.seleccionar, self.jid, e.id, f, e.recesivo):
                        break

        # contraataque: usar el recesivo para cubrir lo que el rival mostró
        intel = m.intel[self.jid]
        if intel and self.rng.random() < 0.5:
            cartas = intel[1]
            mejor = max(m.fen.orden, key=lambda f: sum(m.fen.duelo(f, c) for c in cartas))
            e = max(j.especies, key=lambda e: e.efectiva)
            if e.recesivo != mejor:
                c = m.coste_seleccion(self.jid, e.id, e.dominante, mejor)
                if j.cromos - c.cromos >= self.reserva:
                    self._intentar(m.seleccionar, self.jid, e.id, e.dominante, mejor)

    # ------------------------------------------------------------ etapa 2
    def _decidir(self) -> bool:
        v = ventaja_estimada(self.m, self.jid) + self.rng.gauss(0, 0.15)
        return v > -0.05

    def _rival_estimado(self) -> dict[str, float]:
        """Mezcla de: cartas del último combate, cartas jugadas en este combate (pesan doble)
        y un poco de prior uniforme."""
        m = self.m
        cuenta = {f: 0.5 for f in m.fen.orden}
        if m.intel[self.jid]:
            for f in m.intel[self.jid][1]:
                cuenta[f] += 1
        for f in m.cartas_jugadas(1 - self.jid):
            cuenta[f] += 2
        tot = sum(cuenta.values())
        return {f: c / tot for f, c in cuenta.items()}

    def _combate(self) -> None:
        m = self.m
        rival = self._rival_estimado()
        puntua = lambda f: sum(p * m.fen.duelo(f, b) for b, p in rival.items())
        mano = m.manos[self.jid]
        malas = sorted((i for i, c in enumerate(mano) if puntua(c.fenotipo) < -0.1),
                       key=lambda i: puntua(mano[i].fenotipo))[:m.descartes[self.jid]]
        if malas and self.rng.random() < 0.7:
            m.descartar(self.jid, malas)
        mano = m.manos[self.jid]
        mejor = max(range(len(mano)), key=lambda i: puntua(mano[i].fenotipo) + self.rng.gauss(0, 0.1))
        m.jugar_carta(self.jid, mejor)

    # ------------------------------------------------------------ etapa 3
    def _mercado(self) -> None:
        m, j = self.m, self.yo
        arts = m.cfg.mercado.articulos
        potenciadores = sum(c for a, c in j.inventario.items() if arts[a].tipo == "potenciador")

        def comprar(art: str) -> bool:
            if j.cromos - arts[art].precio >= self.reserva:
                return self._intentar(m.comprar, self.jid, art)
            return False

        if len(j.especies) < m.cfg.jugadores.max_especies and potenciadores == 0:
            barato = min((a for a in arts if arts[a].tipo == "potenciador"), key=lambda a: arts[a].precio)
            comprar(barato)
        if m.prob_cladogenesis(self.jid) < 0.6:
            comprar("carta_mutacion")
        if self.rng.random() < 0.25:
            pociones = [a for a in arts if arts[a].tipo == "pocion"]
            if pociones:
                comprar(self.rng.choice(pociones))
