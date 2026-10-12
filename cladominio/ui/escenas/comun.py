"""Escena base para las pantallas privadas de un jugador."""
from __future__ import annotations

import pygame

from ...core.motor import ErrorJugada
from .. import dibujo
from .base import Escena, OverlayAyuda, OverlayRegistro

NOMBRES_FASE = {
    "seleccion": "Etapa 1 · Selección natural",
    "decision": "Etapa 2 · Decisión de combate",
    "combate": "Etapa 2 · Combate",
    "revelacion": "Etapa 2 · Revelación",
    "mercado": "Etapa 3 · Mercado",
    "fin": "Fin de la partida",
}


class EscenaJugador(Escena):
    def __init__(self, app, jid: int):
        super().__init__(app)
        self.jid = jid
        self.m = app.motor
        self.yo = self.m.jugadores[jid]
        self.boton((self.W - 52, 12, 40, 40), "?", lambda: self.abrir(OverlayAyuda(self)), tam="media")
        self.boton((self.W - 172, 12, 112, 40), "Registro",
                   lambda: self.abrir(OverlayRegistro(self, self.jid)), tam="normal")

    def abrir(self, ov) -> None:
        self.overlay = ov

    def intentar(self, fn, *args, exito: str | None = None):
        """Ejecuta una acción del motor mostrando el error si falla."""
        try:
            r = fn(*args)
        except ErrorJugada as e:
            self.mensaje(str(e), "pierde")
            return None
        if exito:
            self.mensaje(exito, "gana")
        return r if r is not None else True

    def dibujar_cabecera(self, s, titulo_centro: str | None = None) -> None:
        t = self.tema
        s.blit(t.texto(self.yo.nombre, "media", negrita=True, titulo=True), (20, 14))
        info = f"Ronda {self.m.ronda} · {NOMBRES_FASE[self.m.fase.value]}"
        s.blit(t.texto(info, "chica", "tinta_suave"), (22, 48))
        if titulo_centro:
            dibujo.blit_centrado(s, t.texto(titulo_centro, "grande", titulo=True), (self.W // 2, 40))

    def dibujar_intel(self, s, rect: pygame.Rect, tam_carta: int = 34) -> None:
        """Panel con lo que se sabe del rival."""
        t = self.tema
        r = pygame.Rect(rect)
        rival = self.m.rival(self.jid)
        pygame.draw.rect(s, t.c["panel"], r, border_radius=8)
        s.blit(t.texto(f"Rival: {rival.nombre}", "normal", negrita=True), (r.x + 10, r.y + 6))
        if self.m.cfg.get("info_publica", {}).get("cromos_rival", True):
            dibujo.cantidad_cromos(s, t, rival.cromos, (r.right - 90, r.y + 6), "normal", 22)
        intel = self.m.intel[self.jid]
        y = r.y + 36
        if not intel:
            s.blit(t.texto("Aún no ha mostrado cartas.", "chica", "tinta_suave"), (r.x + 10, y))
            return
        ronda, cartas = intel
        hace = self.m.ronda - ronda
        cuando = "esta ronda" if hace == 0 else ("ronda anterior" if hace == 1 else f"hace {hace} rondas")
        s.blit(t.texto(f"Cartas mostradas ({cuando}):", "chica", "tinta_suave"), (r.x + 10, y))
        y += 22
        x = r.x + 10
        for f in cartas:
            s.blit(dibujo.icono_fenotipo(t, f, tam_carta), (x, y))
            x += tam_carta + 4
