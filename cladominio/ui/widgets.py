"""Widgets mínimos: botón y área clicable."""
from __future__ import annotations

from typing import Callable

import pygame

from . import dibujo
from .tema import Tema


class Widget:
    visible: Callable[[], bool] = staticmethod(lambda: True)

    def manejar(self, ev: pygame.event.Event) -> bool:
        return False

    def dibujar(self, surf: pygame.Surface) -> None:
        pass


class Boton(Widget):
    def __init__(self, tema: Tema, rect, texto: str | Callable[[], str], accion: Callable[[], None],
                 tam="media", color_borde=None, habilitado: Callable[[], bool] | None = None,
                 visible: Callable[[], bool] | None = None, activo: Callable[[], bool] | None = None,
                 rayado=None, tooltip: str = ""):
        self.tema = tema
        self.rect = pygame.Rect(rect)
        self._texto = texto
        self.accion = accion
        self.tam = tam
        self.color_borde = color_borde
        self.habilitado = habilitado or (lambda: True)
        self.visible = visible or (lambda: True)
        self.activo = activo or (lambda: False)  # p. ej. pestaña seleccionada
        self.rayado = rayado
        self.tooltip = tooltip
        self.hover = False

    @property
    def texto(self) -> str:
        return self._texto() if callable(self._texto) else self._texto

    def manejar(self, ev) -> bool:
        if not self.visible():
            return False
        if ev.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(ev.pos)
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and self.rect.collidepoint(ev.pos):
            if self.habilitado():
                self.accion()
            return True
        return False

    def dibujar(self, surf) -> None:
        if not self.visible():
            return
        t = self.tema
        hab = self.habilitado()
        fondo = t.c["boton_hover"] if (self.hover and hab) else t.c["boton"]
        pygame.draw.rect(surf, fondo, self.rect)
        if self.rayado is not None and hab:
            r = self.rect
            dibujo.rayado(surf, self.rayado, [r.topleft, r.topright, r.bottomright, r.bottomleft], 9, 2, 120)
        borde = self.color_borde if (self.color_borde is not None and hab) else (
            t.c["boton_borde"] if hab else t.c["boton_deshabilitado"])
        grosor = 4 if self.activo() else 2
        dibujo.rect_boceto(surf, borde, self.rect, grosor, t)
        if self.activo():  # doble trazo, como en el boceto
            dibujo.rect_boceto(surf, borde, self.rect.inflate(-6, -6), 1, t)
        color = (self.color_borde if self.color_borde is not None else t.c["tinta"]) if hab \
            else t.c["boton_deshabilitado"]
        lineas = self.texto.split("\n")
        alto = t.fuente(self.tam, titulo=True).get_height()
        y0 = self.rect.centery - alto * (len(lineas) - 1) / 2
        for i, ln in enumerate(lineas):
            dibujo.blit_centrado(surf, t.texto(ln, self.tam, color, titulo=True), (self.rect.centerx, y0 + i * alto))


class ZonaClic(Widget):
    """Área invisible que reacciona a clic izquierdo/derecho."""

    def __init__(self, rect, izq: Callable[[], None] | None = None, der: Callable[[], None] | None = None,
                 visible: Callable[[], bool] | None = None):
        self.rect = pygame.Rect(rect)
        self.izq, self.der = izq, der
        self.visible = visible or (lambda: True)

    def manejar(self, ev) -> bool:
        if not self.visible() or ev.type != pygame.MOUSEBUTTONDOWN or not self.rect.collidepoint(ev.pos):
            return False
        if ev.button == 1 and self.izq:
            self.izq()
            return True
        if ev.button == 3 and self.der:
            self.der()
            return True
        return False
