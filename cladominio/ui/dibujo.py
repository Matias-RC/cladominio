"""Primitivas de dibujo con estilo boceto: líneas, pentágono, iconos, cartas, barras."""
from __future__ import annotations

import math
import random
from functools import lru_cache

import pygame

from .tema import Tema

Punto = tuple[float, float]


# ================================================================ texto
def blit_centrado(surf: pygame.Surface, img: pygame.Surface, centro: Punto) -> pygame.Rect:
    r = img.get_rect(center=(int(centro[0]), int(centro[1])))
    surf.blit(img, r)
    return r


def envolver(tema: Tema, texto: str, ancho: int, tam="normal", titulo: bool = False,
             negrita: bool = False) -> list[str]:
    f = tema.fuente(tam, titulo, negrita)
    lineas: list[str] = []
    for parrafo in texto.split("\n"):
        actual = ""
        for palabra in parrafo.split(" "):
            prueba = f"{actual} {palabra}".strip()
            if f.size(prueba)[0] <= ancho or not actual:
                actual = prueba
            else:
                lineas.append(actual)
                actual = palabra
        lineas.append(actual)
    return lineas


def parrafo(surf, tema: Tema, texto: str, pos: Punto, ancho: int, tam="normal", color="tinta",
            interlineado: float = 1.15) -> int:
    """Dibuja texto envuelto; devuelve la y final."""
    x, y = pos
    alto = int(tema.fuente(tam).get_height() * interlineado)
    for linea in envolver(tema, texto, ancho, tam):
        surf.blit(tema.texto(linea, tam, color), (x, y))
        y += alto
    return y


# ================================================================ líneas boceto
def _rng(*claves) -> random.Random:
    return random.Random(hash(tuple(round(c) if isinstance(c, float) else c for c in claves)))


def linea(surf, color, a: Punto, b: Punto, ancho: int = 2, tema: Tema | None = None) -> None:
    if tema is None or not tema.boceto:
        pygame.draw.line(surf, color, a, b, ancho)
        return
    rng = _rng(a[0], a[1], b[0], b[1])
    largo = math.dist(a, b)
    amp = min(2.0, largo / 60)
    mx, my = (a[0] + b[0]) / 2 + rng.uniform(-amp, amp), (a[1] + b[1]) / 2 + rng.uniform(-amp, amp)
    pts = []
    for i in range(9):
        t = i / 8
        # curva cuadrática por el punto medio desplazado
        x = (1 - t) ** 2 * a[0] + 2 * (1 - t) * t * mx + t ** 2 * b[0]
        y = (1 - t) ** 2 * a[1] + 2 * (1 - t) * t * my + t ** 2 * b[1]
        pts.append((x, y))
    pygame.draw.lines(surf, color, False, pts, ancho)


def poligono_contorno(surf, color, pts: list[Punto], ancho: int = 2, tema: Tema | None = None) -> None:
    for i in range(len(pts)):
        linea(surf, color, pts[i], pts[(i + 1) % len(pts)], ancho, tema)


def rect_boceto(surf, color, rect: pygame.Rect, ancho: int = 2, tema: Tema | None = None) -> None:
    r = pygame.Rect(rect)
    poligono_contorno(surf, color, [r.topleft, r.topright, r.bottomright, r.bottomleft], ancho, tema)


def rect_discontinuo(surf, color, rect: pygame.Rect, ancho: int = 3, guion: int = 16, hueco: int = 10) -> None:
    """Rectángulo con línea discontinua (zona donde soltar cartas)."""
    r = pygame.Rect(rect)
    lados = [(r.topleft, r.topright), (r.topright, r.bottomright),
             (r.bottomright, r.bottomleft), (r.bottomleft, r.topleft)]
    for a, b in lados:
        largo = math.dist(a, b)
        ux, uy = (b[0] - a[0]) / largo, (b[1] - a[1]) / largo
        d = 0.0
        while d < largo:
            e = min(d + guion, largo)
            pygame.draw.line(surf, color, (a[0] + ux * d, a[1] + uy * d), (a[0] + ux * e, a[1] + uy * e), ancho)
            d += guion + hueco


def flecha(surf, color, a: Punto, b: Punto, ancho: int = 3, punta: int = 14, tema: Tema | None = None) -> None:
    linea(surf, color, a, b, ancho, tema)
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    for s in (-1, 1):
        p = (b[0] - punta * math.cos(ang + s * 0.45), b[1] - punta * math.sin(ang + s * 0.45))
        linea(surf, color, b, p, ancho, tema)


def rayado(surf, color, pts: list[Punto], sep: int = 7, ancho: int = 2, alfa: int = 255) -> None:
    """Relleno con rayas diagonales recortado al polígono (como el boceto)."""
    if len(pts) < 3:
        return
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    bx, by = int(min(xs)) - 2, int(min(ys)) - 2
    w, h = int(max(xs)) - bx + 4, int(max(ys)) - by + 4
    if w <= 0 or h <= 0:
        return
    capa = pygame.Surface((w, h), pygame.SRCALPHA)
    col = pygame.Color(color)
    col.a = alfa
    for d in range(-h, w, sep):
        pygame.draw.line(capa, col, (d, h), (d + h, 0), ancho)
    mascara = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.polygon(mascara, (255, 255, 255, 255), [(x - bx, y - by) for x, y in pts])
    capa.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surf.blit(capa, (bx, by))


def relleno_alfa(surf, color, pts: list[Punto], alfa: int = 60) -> None:
    if len(pts) < 3:
        return
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    bx, by = int(min(xs)) - 1, int(min(ys)) - 1
    capa = pygame.Surface((int(max(xs)) - bx + 2, int(max(ys)) - by + 2), pygame.SRCALPHA)
    col = pygame.Color(color)
    col.a = alfa
    pygame.draw.polygon(capa, col, [(x - bx, y - by) for x, y in pts])
    surf.blit(capa, (bx, by))


# ================================================================ pentágono
def vertices(centro: Punto, radio: float, n: int) -> list[Punto]:
    return [(centro[0] + radio * math.cos(-math.pi / 2 + 2 * math.pi * i / n),
             centro[1] + radio * math.sin(-math.pi / 2 + 2 * math.pi * i / n)) for i in range(n)]


def forma_expresion(centro: Punto, radio: float, orden: list[str], dist: dict[str, float],
                    minimo: float = 0.1) -> list[Punto]:
    vs = vertices(centro, radio, len(orden))
    pts = []
    for v, f in zip(vs, orden):
        r = minimo + (1 - minimo) * dist.get(f, 0.0)
        pts.append((centro[0] + r * (v[0] - centro[0]), centro[1] + r * (v[1] - centro[1])))
    return pts


def pentagono(surf, tema: Tema, centro: Punto, radio: float, orden: list[str], nombres: dict[str, str],
              dist: dict[str, float] | None = None, color=None, dominante: str | None = None,
              recesivo: str | None = None, resaltados: set[str] | None = None,
              iconos: bool = True, tam_etiqueta="normal") -> list[Punto]:
    """Dibuja el pentágono de fenotipos con la forma de expresión `dist`. Devuelve los vértices."""
    vs = vertices(centro, radio, len(orden))
    if resaltados:
        for v, f in zip(vs, orden):
            if f in resaltados:
                pygame.draw.circle(surf, tema.c["acento"], v, 17, 3)
    if dist is not None:
        col = color or tema.c["actual"]
        forma = forma_expresion(centro, radio, orden, dist)
        relleno_alfa(surf, col, forma, 45)
        rayado(surf, col, forma, sep=7, ancho=2)
        poligono_contorno(surf, col, forma, 2, tema)
    poligono_contorno(surf, tema.c["linea"], vs, 4, tema)

    for v, f in zip(vs, orden):
        dx, dy = v[0] - centro[0], v[1] - centro[1]
        d = math.hypot(dx, dy) or 1
        if f == dominante:
            pygame.draw.circle(surf, color or tema.c["actual"], v, 9)
        if f == recesivo:
            pygame.draw.circle(surf, color or tema.c["actual"], v, 13, 3)
        # etiqueta hacia fuera
        lx, ly = v[0] + dx / d * 40, v[1] + dy / d * 24
        img = tema.texto(nombres[f], tam_etiqueta, negrita=True)
        if iconos:
            ic = icono_fenotipo(tema, f, 26)
            if dy < -radio * 0.5:  # vértice superior: icono a la izquierda del texto
                blit_centrado(surf, img, (lx + 14, ly - 6))
                blit_centrado(surf, ic, (lx - img.get_width() / 2 - 4, ly - 6))
            else:
                r = blit_centrado(surf, img, (lx, ly + 4))
                blit_centrado(surf, ic, (r.centerx, r.bottom + 12) if dy > 0 else (r.centerx, r.top - 12))
        else:
            blit_centrado(surf, img, (lx, ly))
    return vs


def pentagono_reglas(surf, tema: Tema, centro: Punto, radio: float, fen) -> None:
    """Pentágono con flechas de quién vence a quién."""
    vs = dict(zip(fen.orden, vertices(centro, radio, len(fen))))
    for a in fen.orden:
        for b in fen.vence[a]:
            pa, pb = vs[a], vs[b]
            d = math.dist(pa, pb)
            u = ((pb[0] - pa[0]) / d, (pb[1] - pa[1]) / d)
            ini = (pa[0] + u[0] * 30, pa[1] + u[1] * 30)
            fin = (pb[0] - u[0] * 30, pb[1] - u[1] * 30)
            flecha(surf, tema.fen[a], ini, fin, 3, 12, tema)
    for f, v in vs.items():
        pygame.draw.circle(surf, tema.c["fondo"], v, 26)
        blit_centrado(surf, icono_fenotipo(tema, f, 40), v)
        dx, dy = v[0] - centro[0], v[1] - centro[1]
        d = math.hypot(dx, dy) or 1
        blit_centrado(surf, tema.texto(fen.nombre(f), "normal", negrita=True), (v[0] + dx / d * 50, v[1] + dy / d * 40))


# ================================================================ iconos
@lru_cache(maxsize=None)
def _icono_base(fen: str, color: tuple) -> pygame.Surface:
    """Icono procedural 64x64 para cada fenotipo."""
    s = pygame.Surface((64, 64), pygame.SRCALPHA)
    tinta = (30, 30, 30)
    if fen == "piedra":
        pts = [(12, 40), (16, 22), (30, 12), (46, 16), (54, 32), (50, 48), (32, 54), (18, 50)]
        pygame.draw.polygon(s, color, pts)
        pygame.draw.polygon(s, tinta, pts, 3)
        pygame.draw.line(s, tinta, (24, 30), (32, 24), 2)
        pygame.draw.line(s, tinta, (36, 40), (44, 36), 2)
    elif fen == "papel":
        pts = [(16, 8), (40, 8), (50, 18), (50, 56), (16, 56)]
        pygame.draw.polygon(s, (255, 255, 250), pts)
        pygame.draw.polygon(s, tinta, pts, 3)
        pygame.draw.lines(s, tinta, False, [(40, 8), (40, 18), (50, 18)], 2)
        for y in (26, 34, 42, 50):
            pygame.draw.line(s, color, (22, y), (44, y), 2)
    elif fen == "tijera":
        pygame.draw.line(s, (150, 150, 160), (20, 44), (52, 10), 5)
        pygame.draw.line(s, (150, 150, 160), (44, 44), (12, 10), 5)
        pygame.draw.line(s, tinta, (20, 44), (52, 10), 1)
        pygame.draw.line(s, tinta, (44, 44), (12, 10), 1)
        for cx in (18, 46):
            pygame.draw.circle(s, color, (cx, 50), 9, 4)
        pygame.draw.circle(s, tinta, (32, 28), 3)
    elif fen == "fosforo":
        pygame.draw.line(s, (200, 160, 100), (24, 58), (38, 22), 6)
        pygame.draw.line(s, tinta, (24, 58), (38, 22), 1)
        pygame.draw.circle(s, (150, 40, 30), (39, 20), 6)
        llama = [(39, 2), (48, 16), (44, 22), (34, 22), (31, 14)]
        pygame.draw.polygon(s, color, llama)
        pygame.draw.polygon(s, (255, 210, 60), [(39, 9), (43, 17), (36, 18)])
    elif fen == "pistola":
        cuerpo = [(8, 18), (54, 18), (54, 28), (30, 28), (28, 50), (16, 50), (18, 28), (8, 28)]
        pygame.draw.polygon(s, color, cuerpo)
        pygame.draw.polygon(s, tinta, cuerpo, 3)
        pygame.draw.arc(s, tinta, pygame.Rect(26, 26, 12, 14), math.pi, 2 * math.pi, 2)
        pygame.draw.line(s, tinta, (54, 22), (60, 22), 2)
    else:
        pygame.draw.circle(s, color, (32, 32), 22)
        pygame.draw.circle(s, tinta, (32, 32), 22, 3)
    return s


def icono_fenotipo(tema: Tema, fen: str, tam: int = 48) -> pygame.Surface:
    base = tema.sprite_fenotipo(fen)
    if base is None:
        base = _icono_base(fen, tuple(tema.fen.get(fen, pygame.Color(128, 128, 128))))
    return pygame.transform.smoothscale(base, (tam, tam))


@lru_cache(maxsize=None)
def _cromo_base(color: tuple) -> pygame.Surface:
    """Icono de cromos: doble hélice de ADN, como en el boceto."""
    s = pygame.Surface((64, 64), pygame.SRCALPHA)
    a, b = [], []
    for i in range(33):
        t = i / 32
        y = 4 + t * 56
        x1 = 32 + 18 * math.sin(t * 2 * math.pi * 1.25)
        x2 = 32 - 18 * math.sin(t * 2 * math.pi * 1.25)
        a.append((x1 + (t - 0.5) * 16, y))
        b.append((x2 + (t - 0.5) * 16, y))
        if i % 4 == 2:
            pygame.draw.line(s, color, a[-1], b[-1], 2)
    pygame.draw.lines(s, (30, 30, 30), False, a, 4)
    pygame.draw.lines(s, (30, 30, 30), False, b, 4)
    return pygame.transform.rotate(s, -35)


def icono_cromo(tema: Tema, tam: int = 28) -> pygame.Surface:
    base = tema.sprite_cromo() or _cromo_base(tuple(tema.c["cromo"]))
    return pygame.transform.smoothscale(base, (tam, tam))


def cantidad_cromos(surf, tema: Tema, valor: float, pos: Punto, tam="media", icono: int = 30,
                    prefijo: str = "", color="tinta") -> pygame.Rect:
    """Dibuja '[icono] = 30' con la esquina superior izquierda en pos."""
    ic = icono_cromo(tema, icono)
    txt = tema.texto(f"{prefijo}{fmt(valor)}", tam, color, negrita=True)
    x, y = pos
    h = max(ic.get_height(), txt.get_height())
    surf.blit(ic, (x, y + (h - ic.get_height()) // 2))
    surf.blit(txt, (x + ic.get_width() + 6, y + (h - txt.get_height()) // 2))
    return pygame.Rect(x, y, ic.get_width() + 6 + txt.get_width(), h)


def ancho_cromos(tema: Tema, valor: float, tam="media", icono: int = 30, prefijo: str = "") -> int:
    return icono + 6 + tema.fuente(tam, negrita=True).size(f"{prefijo}{fmt(valor)}")[0]


def fmt(x: float) -> str:
    return f"{x:g}" if abs(x - round(x)) > 1e-9 else str(int(round(x)))


# ================================================================ carta
def carta(surf, tema: Tema, rect: pygame.Rect, fen: str | None, nombre_fen: str = "",
          subtitulo: str = "", borde=None, oculta: bool = False, seleccionada: bool = False) -> None:
    r = pygame.Rect(rect)
    sombra = r.move(4, 4)
    pygame.draw.rect(surf, (210, 208, 200), sombra, border_radius=10)
    fondo = tema.sprite_carta()
    if fondo is not None:
        surf.blit(pygame.transform.smoothscale(fondo, r.size), r)
    else:
        pygame.draw.rect(surf, tema.c["boton"], r, border_radius=10)
    if oculta or fen is None:
        rayado(surf, tema.c["tinta_suave"], [r.topleft, r.topright, r.bottomright, r.bottomleft], 10, 2)
        blit_centrado(surf, tema.texto("?", "grande", titulo=True), r.center)
    else:
        col = tema.fen.get(fen, tema.c["linea"])
        pygame.draw.rect(surf, col, r.inflate(-10, -10), 2, border_radius=8)
        tam_ic = int(min(r.w, r.h) * 0.6)
        blit_centrado(surf, icono_fenotipo(tema, fen, tam_ic), (r.centerx, r.top + r.h * 0.42))
        if nombre_fen:
            blit_centrado(surf, tema.texto(nombre_fen, "chica" if r.w < 100 else "normal", negrita=True),
                          (r.centerx, r.bottom - r.h * 0.2))
        if subtitulo:
            blit_centrado(surf, tema.texto(subtitulo, 13, "tinta_suave"), (r.centerx, r.bottom - 12))
    grosor = 4 if seleccionada else 2
    pygame.draw.rect(surf, borde or (tema.c["acento"] if seleccionada else tema.c["linea"]), r, grosor,
                     border_radius=10)


# ================================================================ barras
def barra_diversidad(surf, tema: Tema, rect: pygame.Rect, diversidad: float, gastada: float,
                     maxima: float, vertical: bool = True, etiqueta: bool = True) -> None:
    r = pygame.Rect(rect)
    pygame.draw.rect(surf, tema.c["boton"], r)
    frac = max(0.0, min(1.0, diversidad / maxima))
    frac_g = max(0.0, min(frac, gastada / maxima))
    if vertical:
        h = int(r.h * frac)
        hg = int(r.h * frac_g)
        lleno = pygame.Rect(r.x, r.bottom - h, r.w, h)
        gast = pygame.Rect(r.x, r.bottom - h, r.w, hg)
    else:
        w = int(r.w * frac)
        wg = int(r.w * frac_g)
        lleno = pygame.Rect(r.x, r.y, w, r.h)
        gast = pygame.Rect(r.x + w - wg, r.y, wg, r.h)
    if lleno.h > 0 and lleno.w > 0:
        pts = [lleno.topleft, lleno.topright, lleno.bottomright, lleno.bottomleft]
        relleno_alfa(surf, tema.c["diversidad"], pts, 50)
        rayado(surf, tema.c["diversidad"], pts, 8, 2)
    if gast.h > 0 and gast.w > 0:
        pygame.draw.rect(surf, tema.c["diversidad_gastada"], gast)
        rayado(surf, tema.c["boton"], [gast.topleft, gast.topright, gast.bottomright, gast.bottomleft], 6, 1)
    rect_boceto(surf, tema.c["linea"], r, 3, tema)
    if etiqueta and vertical:
        img = pygame.transform.rotate(tema.texto("Diversidad", "grande", titulo=True), 90)
        blit_centrado(surf, img, r.center)


def marcador_rombo(surf, color, centro: Punto, tam: int = 11) -> None:
    x, y = centro
    pts = [(x, y - tam), (x + tam, y), (x, y + tam), (x - tam, y)]
    pygame.draw.polygon(surf, color, pts)
    pygame.draw.polygon(surf, (30, 30, 30), pts, 1)


def marcador_cuadrado(surf, color, centro: Punto, tam: int = 9) -> None:
    r = pygame.Rect(0, 0, tam * 2, tam * 2)
    r.center = (int(centro[0]), int(centro[1]))
    pygame.draw.rect(surf, color, r, border_radius=3)
    pygame.draw.rect(surf, (30, 30, 30), r, 1, border_radius=3)
