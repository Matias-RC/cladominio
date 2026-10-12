"""Clase base de escenas y overlays comunes (ayuda, registro)."""
from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from .. import dibujo
from ..widgets import Boton, Widget

if TYPE_CHECKING:
    from ..app import App


class Escena:
    def __init__(self, app: "App"):
        self.app = app
        self.tema = app.tema
        self.widgets: list[Widget] = []
        self.overlay: Overlay | None = None
        self._mensaje = ""
        self._mensaje_color = "tinta"
        self._mensaje_t = 0.0

    @property
    def W(self) -> int:
        return self.app.ancho

    @property
    def H(self) -> int:
        return self.app.alto

    # ------------------------------------------------------------ helpers
    def boton(self, *args, **kw) -> Boton:
        b = Boton(self.tema, *args, **kw)
        self.widgets.append(b)
        return b

    def mensaje(self, texto: str, color: str = "tinta", segundos: float = 4.0) -> None:
        self._mensaje, self._mensaje_color, self._mensaje_t = texto, color, segundos

    # ------------------------------------------------------------ ciclo
    def manejar(self, ev: pygame.event.Event) -> None:
        if self.overlay:
            self.overlay.manejar(ev)
            return
        for w in reversed(self.widgets):
            if w.manejar(ev):
                break
        self.manejar_extra(ev)

    def manejar_extra(self, ev: pygame.event.Event) -> None:
        pass

    def actualizar(self, dt: float) -> None:
        if self._mensaje_t > 0:
            self._mensaje_t -= dt

    def dibujar(self, s: pygame.Surface) -> None:
        s.fill(self.tema.c["fondo"])
        self.dibujar_fondo(s)
        for w in self.widgets:
            w.dibujar(s)
        self.dibujar_frente(s)
        if self._mensaje and self._mensaje_t > 0:
            img = self.tema.texto(self._mensaje, "normal", self._mensaje_color, negrita=True)
            r = img.get_rect(center=(self.W // 2, self.H - 22))
            pygame.draw.rect(s, self.tema.c["panel"], r.inflate(24, 10), border_radius=8)
            s.blit(img, r)
        if self.overlay:
            self.overlay.dibujar(s)

    def dibujar_fondo(self, s: pygame.Surface) -> None:
        pass

    def dibujar_frente(self, s: pygame.Surface) -> None:
        pass


class Overlay:
    """Ventana modal encima de la escena. Se cierra con clic fuera, Esc o el botón."""

    def __init__(self, escena: Escena, titulo: str, rect=None):
        self.escena = escena
        self.tema = escena.tema
        self.titulo = titulo
        self.rect = pygame.Rect(rect or (140, 70, escena.W - 280, escena.H - 140))
        self.cerrar_btn = Boton(self.tema, (self.rect.right - 130, self.rect.bottom - 56, 110, 40),
                                "Cerrar", self.cerrar, tam="normal")

    def cerrar(self) -> None:
        self.escena.overlay = None

    def manejar(self, ev) -> None:
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            self.cerrar()
        elif ev.type == pygame.MOUSEBUTTONDOWN and not self.rect.collidepoint(ev.pos):
            self.cerrar()
        else:
            self.cerrar_btn.manejar(ev)
            self.manejar_contenido(ev)

    def manejar_contenido(self, ev) -> None:
        pass

    def dibujar(self, s) -> None:
        velo = pygame.Surface(s.get_size(), pygame.SRCALPHA)
        velo.fill((0, 0, 0, 110))
        s.blit(velo, (0, 0))
        pygame.draw.rect(s, self.tema.c["fondo"], self.rect, border_radius=12)
        dibujo.rect_boceto(s, self.tema.c["linea"], self.rect, 3, self.tema)
        s.blit(self.tema.texto(self.titulo, "grande", titulo=True), (self.rect.x + 24, self.rect.y + 14))
        self.dibujar_contenido(s)
        self.cerrar_btn.dibujar(s)

    def dibujar_contenido(self, s) -> None:
        pass


class OverlayAyuda(Overlay):
    def __init__(self, escena: Escena):
        super().__init__(escena, "¿Quién vence a quién?")

    def dibujar_contenido(self, s) -> None:
        fen = self.escena.app.motor.fen
        cx = self.rect.x + 270
        cy = self.rect.centery + 20
        dibujo.pentagono_reglas(s, self.tema, (cx, cy), 170, fen)
        x = self.rect.x + 560
        y = self.rect.y + 80
        for a in fen.orden:
            txt = f"{fen.nombre(a)} vence a " + " y ".join(fen.nombre(b) for b in fen.orden if b in fen.vence[a])
            s.blit(dibujo.icono_fenotipo(self.tema, a, 28), (x, y))
            s.blit(self.tema.texto(txt, "normal"), (x + 36, y + 2))
            y += 36
        y += 14
        cfg = self.escena.app.motor.cfg
        notas = (
            f"• Gana quien tenga {cfg.victoria.fenotipos_distintos} especies vivas con dominantes distintos.\n"
            f"• Cada especie expresa su dominante con prob. {cfg.expresion.prob_dominante:.0%} "
            f"y su recesivo con el resto (especialista = 100% dominante).\n"
            f"• La diversidad gastada en selección se recarga al final de la ronda; "
            f"la perdida en combate no.\n"
            f"• Las flechas del pentágono apuntan del ganador al perdedor."
        )
        dibujo.parrafo(s, self.tema, notas, (x, y), self.rect.right - x - 30, "chica")


class OverlayRegistro(Overlay):
    def __init__(self, escena: Escena, jid: int | None, eventos=None, titulo: str = "Registro"):
        super().__init__(escena, titulo)
        self.jid = jid
        self.eventos = eventos  # si se da una lista, se muestra en orden cronológico
        self.scroll = 0

    def _eventos(self):
        m = self.escena.app.motor
        if self.eventos is not None:
            return list(self.eventos)
        evs = m.eventos if self.jid is None else m.eventos_para(self.jid)
        return list(reversed(evs))

    def manejar_contenido(self, ev) -> None:
        if ev.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, min(self.scroll - ev.y * 3, max(0, len(self._eventos()) - 5)))

    def dibujar_contenido(self, s) -> None:
        x, y = self.rect.x + 30, self.rect.y + 70
        ancho = self.rect.w - 60
        limite = self.rect.bottom - 70
        for e in self._eventos()[self.scroll:]:
            color = "acento" if e.visible is not None else "tinta"
            s.blit(self.tema.texto(f"R{e.ronda}", "chica", "tinta_suave"), (x, y + 2))
            y = dibujo.parrafo(s, self.tema, e.texto, (x + 46, y), ancho - 46, "chica", color)
            if y > limite:
                break
        s.blit(self.tema.texto("(azul = privado · rueda del ratón para desplazar)", "chica", "tinta_suave"),
               (self.rect.x + 30, self.rect.bottom - 44))
