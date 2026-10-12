"""Etapa 2: resumen del resultado (combate completo, paz o rechazo unilateral)."""
from __future__ import annotations

import pygame

from .. import dibujo
from .base import Escena, OverlayAyuda


class RevelacionEscena(Escena):
    """Pantalla pública: ambos jugadores pueden mirarla."""

    def __init__(self, app, humanos: list[int]):
        super().__init__(app)
        self.m = app.motor
        self.humanos = humanos
        self.res = self.m.resultado
        self.t = 0.0
        self.seg = float(app.ui.animacion.segundos_por_duelo)
        n = len(self.res.duelos) if self.res and self.res.hubo_combate else 0
        self.duracion = self.seg * n + 0.3
        if self.m.cfg.combate.modo == "interactivo":
            self.t = self.duracion  # los duelos ya se vieron uno a uno
        self.boton((self.W - 52, 12, 40, 40), "?", lambda: setattr(self, "overlay", OverlayAyuda(self)))
        self.boton((1060, 636, 190, 58), "Continuar", self._continuar, tam="media",
                   color_borde=self.tema.c["acento"])

    def _continuar(self) -> None:
        if self.t < self.duracion:
            self.t = self.duracion  # primer clic salta la animación
            return
        for j in self.humanos:
            if j in self.m.pendientes():
                self.m.listo(j)
        self.app.director.avanzar()

    def manejar_extra(self, ev) -> None:
        if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_SPACE, pygame.K_RETURN):
            self._continuar()

    def actualizar(self, dt: float) -> None:
        super().actualizar(dt)
        self.t += dt

    def dibujar_fondo(self, s) -> None:
        t, m, res = self.tema, self.m, self.res
        j0, j1 = m.jugadores
        dibujo.blit_centrado(s, t.texto(f"Ronda {res.ronda} · Resultado de la etapa 2", "grande", titulo=True),
                             (640, 44))
        if res.hubo_combate:
            self._dibujar_combate(s)
        else:
            self._dibujar_paz(s)

    def _dibujar_paz(self, s) -> None:
        t, m, res = self.tema, self.m, self.res
        for i, j in enumerate(m.jugadores):
            r = pygame.Rect(200 + i * 480, 160, 400, 260)
            acepta = res.decisiones[i]
            col = t.c["gana"] if acepta else t.c["pierde"]
            pygame.draw.rect(s, t.c["panel"], r, border_radius=12)
            dibujo.rect_boceto(s, col, r, 3, t)
            dibujo.blit_centrado(s, t.texto(j.nombre, "grande", titulo=True), (r.centerx, r.y + 40))
            dibujo.blit_centrado(s, t.texto("Acepta" if acepta else "Rechaza", "enorme", col, titulo=True),
                                 (r.centerx, r.y + 120))
            ancho = dibujo.ancho_cromos(t, res.cromos[i], "grande", 34, "+ ")
            dibujo.cantidad_cromos(s, t, res.cromos[i], (r.centerx - ancho // 2, r.y + 180), "grande", 34, "+ ")
        if not any(res.decisiones):
            txt = (f"Paz mutua: ambos ganan cromos y +{m.cfg.paz.bono_diversidad}% de diversidad en cada especie. "
                   "No se revelan cartas.")
        else:
            txt = "Rechazo unilateral: no hay combate ni se revelan cartas; quien aceptó se lleva el premio."
        dibujo.blit_centrado(s, t.texto(txt, "normal"), (640, 470))

    def _dibujar_combate(self, s) -> None:
        t, m, res = self.tema, self.m, self.res
        n = len(res.duelos)
        w, h = 110, 140
        paso = w + 26
        x0 = (self.W - (n * paso - 26)) // 2 + 60
        filas = (110, 380)
        for lado, y in enumerate(filas):
            s.blit(t.texto(m.jugadores[lado].nombre, "media", titulo=True), (30, y + h // 2 - 20))
        visibles = min(n, int(self.t / self.seg) + 1) if self.t < self.duracion else n
        for i, d in enumerate(res.duelos):
            x = x0 + i * paso
            for lado, y in enumerate(filas):
                c = d.cartas[lado]
                rect = pygame.Rect(x, y, w, h)
                if i < visibles:
                    borde = None
                    if d.ganador is not None:
                        borde = t.c["gana"] if d.ganador == lado else t.c["pierde"]
                    dibujo.carta(s, t, rect, c.fenotipo, m.fen.nombre(c.fenotipo), borde=borde,
                                 seleccionada=d.ganador == lado)
                else:
                    dibujo.carta(s, t, rect, None, oculta=True)
            if i < visibles:
                cy = (filas[0] + h + filas[1]) // 2
                if d.ganador is not None:
                    dibujo.flecha(s, t.c["gana"], (x + w / 2, cy + (18 if d.ganador == 0 else -18)),
                                  (x + w / 2, cy + (-18 if d.ganador == 0 else 18)), 4, 12, t)
                else:
                    dibujo.blit_centrado(s, t.texto("=", "grande", "empata"), (x + w / 2, cy))
        if self.t >= self.duracion:
            v = res.victorias
            y = 560
            for lado in (0, 1):
                j = m.jugadores[lado]
                xx = 220 + lado * 440
                s.blit(t.texto(f"{j.nombre}: {v[lado]} victoria(s)", "media", negrita=True), (xx, y))
                dibujo.cantidad_cromos(s, t, res.cromos[lado], (xx, y + 40), "media", 28,
                                       "+" if res.cromos[lado] >= 0 else "",
                                       color="gana" if res.cromos[lado] > 0 else
                                       ("pierde" if res.cromos[lado] < 0 else "tinta"))
            dibujo.blit_centrado(s, t.texto("Los cambios de diversidad son privados: los verás en tu registro.",
                                            "chica", "tinta_suave"), (640, 680))
        else:
            dibujo.blit_centrado(s, t.texto("(clic en Continuar para saltar)", "chica", "tinta_suave"), (640, 680))
