"""Colores, fuentes y sprites (con fallback a dibujo procedural)."""
from __future__ import annotations

from pathlib import Path

import pygame

from ..config import RAIZ, Config


# Glifos que muchas fuentes manuscritas no traen.
SUSTITUTOS = str.maketrans({"−": "-", "→": "->", "←": "<-", "…": "..."})


def _color(v) -> pygame.Color:
    return pygame.Color(*v)


class Tema:
    def __init__(self, ui: Config):
        self.ui = ui
        self.c = {k: _color(v) for k, v in ui.colores.items() if k != "fenotipos"}
        self.fen = {k: _color(v) for k, v in ui.colores.fenotipos.items()}
        disponibles = set(pygame.font.get_fonts())

        def elegir(lista):
            for nombre in lista:
                if nombre in disponibles:
                    return nombre
            return None

        self._nombre_titulo = elegir(ui.fuentes.titulo)
        self._nombre_texto = elegir(ui.fuentes.texto)
        self._fuentes: dict[tuple, pygame.font.Font] = {}
        self._sprites: dict[str, pygame.Surface | None] = {}
        self.boceto = bool(ui.animacion.efecto_boceto)

    # ------------------------------------------------------------ fuentes
    def fuente(self, tam: str | int = "normal", titulo: bool = False, negrita: bool = False) -> pygame.font.Font:
        px = self.ui.fuentes.tamanos[tam] if isinstance(tam, str) else tam
        clave = (px, titulo, negrita)
        if clave not in self._fuentes:
            nombre = self._nombre_titulo if titulo else self._nombre_texto
            if nombre:
                f = pygame.font.SysFont(nombre, px, bold=negrita)
            else:
                f = pygame.font.Font(None, int(px * 1.3))
                f.set_bold(negrita)
            self._fuentes[clave] = f
        return self._fuentes[clave]

    def texto(self, txt: str, tam: str | int = "normal", color: str | pygame.Color = "tinta",
              titulo: bool = False, negrita: bool = False) -> pygame.Surface:
        col = self.c[color] if isinstance(color, str) else color
        return self.fuente(tam, titulo, negrita).render(str(txt).translate(SUSTITUTOS), True, col)

    # ------------------------------------------------------------ sprites
    def sprite(self, clave: str, ruta: str | None) -> pygame.Surface | None:
        """Carga un sprite opcional definido en ui.yaml; None si no existe."""
        if clave not in self._sprites:
            img = None
            if ruta:
                p = Path(ruta)
                p = p if p.is_absolute() else RAIZ / p
                if p.exists():
                    try:
                        img = pygame.image.load(str(p)).convert_alpha()
                    except pygame.error:
                        img = None
            self._sprites[clave] = img
        return self._sprites[clave]

    def sprite_fenotipo(self, fen: str) -> pygame.Surface | None:
        return self.sprite(f"fen:{fen}", self.ui.sprites.fenotipos.get(fen))

    def sprite_cromo(self) -> pygame.Surface | None:
        return self.sprite("cromo", self.ui.sprites.get("cromo"))

    def sprite_carta(self) -> pygame.Surface | None:
        return self.sprite("carta", self.ui.sprites.get("carta_fondo"))
