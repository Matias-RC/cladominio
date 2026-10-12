"""Menú principal, pantalla de pase de turno y fin de partida."""
from __future__ import annotations

import math

import pygame

from ...core.fenotipos import Fenotipos
from .. import dibujo
from .base import Escena


class MenuEscena(Escena):
    def __init__(self, app):
        super().__init__(app)
        self.fen = Fenotipos(app.reglas)
        self.t = 0.0
        self.boton((470, 330, 340, 70), "1 jugador vs IA", lambda: app.nueva_partida(humanos=1), tam="grande",
                   color_borde=self.tema.c["actual"])
        self.boton((470, 420, 340, 70), "2 jugadores", lambda: app.nueva_partida(humanos=2), tam="grande",
                   color_borde=self.tema.c["objetivo"])
        self.boton((540, 520, 200, 56), "Salir", app.salir, tam="media")

    def actualizar(self, dt: float) -> None:
        super().actualizar(dt)
        self.t += dt

    def dibujar_fondo(self, s) -> None:
        t = self.tema
        dibujo.blit_centrado(s, t.texto("Cachipún Evolución", "enorme", titulo=True), (640, 110))
        dibujo.blit_centrado(s, t.texto("el dominio de los clados", "grande", "tinta_suave", titulo=True), (640, 170))
        # pentágono decorativo con una forma que "respira"
        orden = self.fen.orden
        for lado, cx, col in ((0, 210, t.c["actual"]), (1, 1070, t.c["objetivo"])):
            dist = {f: 0.5 + 0.5 * math.sin(self.t * 1.3 + i * 1.7 + lado * 2) for i, f in enumerate(orden)}
            tot = sum(dist.values())
            dist = {f: v / tot * 1.6 for f, v in dist.items()}
            dibujo.pentagono(s, t, (cx, 420), 110, orden, self.fen.nombres, dist, col, tam_etiqueta="chica")
        dibujo.blit_centrado(s, t.texto("Las reglas se ajustan en config/reglas.yaml · F11 pantalla completa",
                                        "chica", "tinta_suave"), (640, 690))


class PaseEscena(Escena):
    """Oculta la información privada mientras se pasa el dispositivo (modo 2 jugadores)."""

    def __init__(self, app, jid: int, al_continuar):
        super().__init__(app)
        self.jid = jid
        self.al_continuar = al_continuar
        self.boton((490, 420, 300, 80), "Estoy listo", al_continuar, tam="grande", rayado=self.tema.c["acento"])

    def manejar_extra(self, ev) -> None:
        if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_SPACE, pygame.K_RETURN):
            self.al_continuar()

    def dibujar_fondo(self, s) -> None:
        t, m = self.tema, self.app.motor
        j = m.jugadores[self.jid]
        dibujo.rayado(s, t.c["panel"], [(0, 0), (self.W, 0), (self.W, self.H), (0, self.H)], 14, 3)
        dibujo.blit_centrado(s, t.texto(f"Turno de {j.nombre}", "enorme", titulo=True), (640, 240))
        dibujo.blit_centrado(s, t.texto("Pásale el dispositivo. El otro jugador no debe mirar.", "media",
                                        "tinta_suave"), (640, 320))


class FinEscena(Escena):
    def __init__(self, app):
        super().__init__(app)
        self.boton((540, 630, 200, 60), "Menú", app.ir_menu, tam="media")

    def dibujar_fondo(self, s) -> None:
        t, m = self.tema, self.app.motor
        if m.empate:
            titulo = "¡Empate!"
        else:
            titulo = f"¡Gana {m.jugadores[m.ganador].nombre}!"
        dibujo.blit_centrado(s, t.texto(titulo, "enorme", "gana" if not m.empate else "tinta", titulo=True), (640, 70))
        dibujo.blit_centrado(s, t.texto(m.motivo_fin, "normal", "tinta_suave"), (640, 125))
        dibujo.blit_centrado(s, t.texto(f"Partida terminada en la ronda {m.ronda}", "chica", "tinta_suave"), (640, 150))
        dmax = float(m.cfg.diversidad.maxima)
        for lado, j in enumerate(m.jugadores):
            x = 80 + lado * 600
            y = 190
            s.blit(t.texto(j.nombre, "grande", titulo=True), (x, y))
            dibujo.cantidad_cromos(s, t, j.cromos, (x + 260, y + 4), "media", 30)
            s.blit(t.texto(f"Fenotipos cubiertos: {len(j.fenotipos_cubiertos())}", "normal"), (x, y + 44))
            y += 80
            for e in j.especies:
                s.blit(dibujo.icono_fenotipo(t, e.dominante, 36), (x, y))
                if not e.especialista:
                    s.blit(dibujo.icono_fenotipo(t, e.recesivo, 22), (x + 36, y + 16))
                s.blit(t.texto(e.nombre, "normal", negrita=True), (x + 66, y))
                dibujo.barra_diversidad(s, t, pygame.Rect(x + 66, y + 26, 220, 12), e.diversidad, 0, dmax,
                                        vertical=False, etiqueta=False)
                s.blit(t.texto(f"{dibujo.fmt(e.diversidad)}%", "chica"), (x + 296, y + 20))
                y += 54
            if not j.especies:
                s.blit(t.texto("Sin especies vivas", "normal", "pierde"), (x, y))
