"""Bucle principal de pygame y director de turnos."""
from __future__ import annotations

import pygame

from ..config import cargar_reglas, cargar_ui
from ..core.motor import Fase, Motor
from ..ia import IAS
from .escenas.base import Escena
from .escenas.combate import RevelacionEscena
from .escenas.decision import DecisionEscena
from .escenas.duelo import CombateEscena, DueloEscena
from .escenas.menu import FinEscena, MenuEscena, PaseEscena
from .escenas.mercado import MercadoEscena
from .escenas.seleccion import SeleccionEscena
from .tema import Tema

# fase -> escena privada del jugador. Para añadir una fase nueva: registra aquí su escena.
ESCENAS_FASE = {
    Fase.SELECCION: SeleccionEscena,
    Fase.DECISION: DecisionEscena,
    Fase.COMBATE: CombateEscena,
    Fase.MERCADO: MercadoEscena,
}


class Director:
    """Decide qué escena mostrar según el estado del motor.

    Las IAs actúan en cuanto les toca; cuando un humano debe actuar se muestra su escena
    (con una pantalla de pase intermedia si hay 2 humanos en el mismo equipo)."""

    def __init__(self, app: "App", humanos: list[int], ias: dict):
        self.app = app
        self.humanos = humanos
        self.ias = ias
        self.visor: int | None = None
        self.visto = {j: 0 for j in humanos}
        self.duelos_mostrados: dict[int, int] = {}  # ronda -> nº de duelos ya revelados en pantalla

    @property
    def m(self) -> Motor:
        return self.app.motor

    def avanzar(self) -> None:
        self.app.escena = self._siguiente()

    def _siguiente(self) -> Escena:
        m = self.m
        for _ in range(10_000):
            if m.terminado:
                return FinEscena(self.app)
            ias = [j for j in sorted(m.pendientes()) if j in self.ias]
            if not ias:
                break
            self.ias[ias[0]].actuar()
        duelo = self._duelo_sin_mostrar()
        if duelo is not None:
            if len(self.humanos) > 1:
                self.visor = None  # pantalla pública
            return DueloEscena(self.app, duelo, self._duelo_visto)
        if m.terminado:
            return FinEscena(self.app)

        pend = [j for j in sorted(m.pendientes()) if j in self.humanos]
        if m.fase == Fase.REVELACION:
            if len(self.humanos) > 1:
                self.visor = None
            return RevelacionEscena(self.app, pend)
        jid = pend[0]
        if len(self.humanos) > 1 and self.visor != jid:
            return PaseEscena(self.app, jid, lambda: self._entrar(jid))
        return self._escena_para(jid)

    def _duelo_sin_mostrar(self):
        res = self.m.resultado
        if not res or not res.hubo_combate or self.m.cfg.combate.modo == "automatico":
            return None
        vistos = self.duelos_mostrados.get(res.ronda, 0)
        return res.duelos[vistos] if vistos < len(res.duelos) else None

    def _duelo_visto(self) -> None:
        r = self.m.resultado.ronda
        self.duelos_mostrados[r] = self.duelos_mostrados.get(r, 0) + 1
        self.avanzar()

    def _entrar(self, jid: int) -> None:
        self.visor = jid
        self.app.escena = self._escena_para(jid)

    def _escena_para(self, jid: int) -> Escena:
        m = self.m
        if m.fase == Fase.SELECCION:
            novedades = m.eventos_para(jid, self.visto[jid]) if m.ronda > 1 else None
            self.visto[jid] = len(m.eventos)
            return SeleccionEscena(self.app, jid, novedades)
        return ESCENAS_FASE[m.fase](self.app, jid)


class App:
    def __init__(self, semilla: int | None = None, ia: str = "heuristica"):
        pygame.init()
        self.ui = cargar_ui()
        self.reglas = cargar_reglas()
        self.semilla = semilla
        self.tipo_ia = ia
        self.ancho, self.alto = int(self.ui.ventana.ancho), int(self.ui.ventana.alto)
        self.pantalla = pygame.display.set_mode((self.ancho, self.alto), pygame.SCALED | pygame.RESIZABLE)
        pygame.display.set_caption(self.ui.ventana.titulo)
        self.tema = Tema(self.ui)
        self.reloj = pygame.time.Clock()
        self.motor: Motor | None = None
        self.director: Director | None = None
        self.escena: Escena = MenuEscena(self)
        self.corriendo = True

    def nueva_partida(self, humanos: int = 1) -> None:
        self.reglas = cargar_reglas()  # se recarga para poder iterar el balance sin reiniciar
        nombres = ("Tú", "IA") if humanos == 1 else ("Jugador 1", "Jugador 2")
        self.motor = Motor(self.reglas, nombres, self.semilla)
        ias = {1: IAS[self.tipo_ia](self.motor, 1, self.semilla)} if humanos == 1 else {}
        self.director = Director(self, list(range(humanos)), ias)
        self.director.avanzar()

    def ir_menu(self) -> None:
        self.escena = MenuEscena(self)

    def salir(self) -> None:
        self.corriendo = False

    def run(self) -> None:
        fps = int(self.ui.ventana.fps)
        while self.corriendo:
            dt = self.reloj.tick(fps) / 1000
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    self.corriendo = False
                elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()
                else:
                    self.escena.manejar(ev)
            self.escena.actualizar(dt)
            self.escena.dibujar(self.pantalla)
            pygame.display.flip()
        pygame.quit()
