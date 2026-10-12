"""Etapa 3: mercado."""
from __future__ import annotations

import pygame

from .. import dibujo
from .comun import EscenaJugador

TIPOS = {"pocion": "Poción", "mutacion": "Mutación", "potenciador": "Macroevolución"}


class MercadoEscena(EscenaJugador):
    def __init__(self, app, jid: int):
        super().__init__(app, jid)
        self.arts = list(self.m.cfg.mercado.articulos)
        n = len(self.arts)
        gap = 18
        self.ancho = min(240, (self.W - 60 - gap * (n - 1)) // n)
        self.x0 = (self.W - (n * self.ancho + gap * (n - 1))) // 2
        self.gap = gap
        for i, a in enumerate(self.arts):
            r = self._rect(i)
            self.boton((r.x + 20, r.bottom - 62, r.w - 40, 46), "Comprar", lambda a=a: self._comprar(a),
                       tam="media", color_borde=self.tema.c["acento"],
                       habilitado=lambda a=a: self.yo.cromos >= self.m.articulo(a).precio)
        self.boton((self.W - 210, 610, 180, 80), "Listo", self._listo, tam="grande", rayado=self.tema.c["acento"])

    def _rect(self, i: int) -> pygame.Rect:
        return pygame.Rect(self.x0 + i * (self.ancho + self.gap), 140, self.ancho, 430)

    def _comprar(self, art: str) -> None:
        self.intentar(self.m.comprar, self.jid, art, exito=f"Compraste {self.m.articulo(art).nombre}.")

    def _listo(self) -> None:
        self.m.listo(self.jid)
        self.app.director.avanzar()

    def dibujar_fondo(self, s) -> None:
        t, m = self.tema, self.m
        self.dibujar_cabecera(s, "Mercado")
        dibujo.cantidad_cromos(s, t, self.yo.cromos, (24, 76), "grande", 36, "= ")
        dibujo.blit_centrado(s, t.texto(f"Has recibido {m.cfg.mercado.ingreso_por_ronda} cromos. "
                                        "Lo que compres se usa en la etapa 1 de la próxima ronda.",
                                        "normal", "tinta_suave"), (640, 92))
        for i, a in enumerate(self.arts):
            art = m.articulo(a)
            r = self._rect(i)
            pygame.draw.rect(s, t.c["panel"], r, border_radius=12)
            dibujo.rect_boceto(s, t.c["linea"], r, 2, t)
            y = r.y + 12
            for linea in dibujo.envolver(t, art.nombre, r.w - 24, "media", titulo=True, negrita=True):
                dibujo.blit_centrado(s, t.texto(linea, "media", titulo=True, negrita=True), (r.centerx, y + 14))
                y += 30
            dibujo.blit_centrado(s, t.texto(TIPOS.get(art.tipo, art.tipo), "chica", "acento"), (r.centerx, y + 10))
            y += 30
            ancho = dibujo.ancho_cromos(t, art.precio, "grande", 32)
            dibujo.cantidad_cromos(s, t, art.precio, (r.centerx - ancho // 2, y), "grande", 32)
            y += 52
            desc = art.descripcion
            if art.tipo == "pocion":
                desc += f" Dura {art.duracion} rondas."
            dibujo.parrafo(s, t, desc, (r.x + 14, y), r.w - 28, "chica")
            dibujo.blit_centrado(s, t.texto(f"Tienes: {self.yo.inventario[a]}", "normal", negrita=True),
                                 (r.centerx, r.bottom - 82))

        p = m.prob_cladogenesis(self.jid)
        s.blit(t.texto(f"Probabilidad actual de cladogénesis: {p:.0%}  ·  "
                       f"Especies: {len(self.yo.especies)}/{m.cfg.jugadores.max_especies}  ·  "
                       f"Fenotipos cubiertos: {len(self.yo.fenotipos_cubiertos())}/{m.cfg.victoria.fenotipos_distintos}",
                       "normal"), (30, 586))
        self.dibujar_intel(s, pygame.Rect(30, 624, 620, 90), 24)
