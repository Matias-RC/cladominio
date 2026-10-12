"""Etapa 2 interactiva: elegir carta (arrastrar), descartar, y revelar cada duelo."""
from __future__ import annotations

import math

import pygame

from .. import dibujo
from .base import Escena, OverlayAyuda
from .comun import EscenaJugador

CARTA = (120, 165)
Y_MANO = 470          # y de las cartas en reposo
ALZADA = 60           # cuánto sube una carta seleccionada para descartar
ZONA = pygame.Rect(555, 95, 170, 230)
UMBRAL_ARRASTRE = 6   # px antes de considerar que un clic es un arrastre


class CombateEscena(EscenaJugador):
    """Mano privada del jugador. Clic = marcar para descartar; arrastrar a la zona roja = jugar."""

    def __init__(self, app, jid: int):
        super().__init__(app, jid)
        self.sel: set[int] = set()
        self.presionada: int | None = None
        self.arrastrando = False
        self.inicio = (0, 0)
        self.offset = (0, 0)
        self.raton = (0, 0)
        self.nuevas: dict[int, float] = {}   # índice -> tiempo restante del destello
        self.jugando: tuple[int, float] | None = None  # (índice, tiempo) animación de soltar
        self.t = 0.0
        self.boton((30, 92, 300, 52), lambda: f"Descartar (restantes: {self.m.descartes[jid]})",
                   self._descartar, tam="media", color_borde=self.tema.c["objetivo"],
                   habilitado=lambda: bool(self.sel) and self.jugando is None)

    @property
    def mano(self):
        return self.m.manos[self.jid]

    # ------------------------------------------------------------ geometría
    def _rect(self, i: int) -> pygame.Rect:
        n = len(self.mano)
        paso = CARTA[0] + 22
        x0 = (self.W - (n * paso - 22)) // 2
        y = Y_MANO - (ALZADA if i in self.sel else 0)
        if self._hover() == i and i not in self.sel and not self.arrastrando:
            y -= 10
        return pygame.Rect(x0 + i * paso, y, *CARTA)

    def _hover(self) -> int | None:
        for i in reversed(range(len(self.mano))):
            r = self._rect_base(i)
            if r.collidepoint(self.raton):
                return i
        return None

    def _rect_base(self, i: int) -> pygame.Rect:
        n = len(self.mano)
        paso = CARTA[0] + 22
        x0 = (self.W - (n * paso - 22)) // 2
        y = Y_MANO - (ALZADA if i in self.sel else 0)
        return pygame.Rect(x0 + i * paso, y - 10, CARTA[0], CARTA[1] + 10)

    def _rect_arrastre(self) -> pygame.Rect:
        return pygame.Rect(self.raton[0] - self.offset[0], self.raton[1] - self.offset[1], *CARTA)

    # ------------------------------------------------------------ acciones
    def _descartar(self) -> None:
        indices = sorted(self.sel)
        if self.intentar(self.m.descartar, self.jid, indices):
            self.nuevas = {i: 0.7 for i in indices}
            self.sel.clear()

    def _jugar(self, i: int) -> None:
        self.sel.discard(i)
        self.jugando = (i, 0.0)

    def manejar_extra(self, ev) -> None:
        if self.jugando is not None:
            return
        if ev.type == pygame.MOUSEMOTION:
            self.raton = ev.pos
            if self.presionada is not None and not self.arrastrando:
                if math.dist(ev.pos, self.inicio) > UMBRAL_ARRASTRE:
                    self.arrastrando = True
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            self.raton = ev.pos
            i = self._hover()
            if i is not None:
                r = self._rect(i)
                self.presionada = i
                self.inicio = ev.pos
                self.offset = (ev.pos[0] - r.x, ev.pos[1] - r.y)
        elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1 and self.presionada is not None:
            i = self.presionada
            if self.arrastrando:
                if ZONA.inflate(40, 40).colliderect(self._rect_arrastre()) and \
                        ZONA.inflate(60, 60).collidepoint(self._rect_arrastre().center):
                    self._jugar(i)
            else:
                self._alternar(i)
            self.presionada = None
            self.arrastrando = False
        elif ev.type == pygame.KEYDOWN and pygame.K_1 <= ev.key <= pygame.K_9:
            i = ev.key - pygame.K_1   # atajo: teclas 1..n juegan esa carta
            if i < len(self.mano):
                self._jugar(i)

    def _alternar(self, i: int) -> None:
        if i in self.sel:
            self.sel.remove(i)
        elif len(self.sel) < self.m.descartes[self.jid]:
            self.sel.add(i)
        else:
            self.mensaje("No te quedan más descartes.", "pierde")

    def actualizar(self, dt: float) -> None:
        super().actualizar(dt)
        self.t += dt
        self.nuevas = {i: v - dt for i, v in self.nuevas.items() if v - dt > 0}
        if self.jugando is not None:
            i, t = self.jugando
            t += dt
            self.jugando = (i, t)
            if t >= 0.35:
                self.jugando = None
                self.m.jugar_carta(self.jid, i)
                self.app.director.avanzar()

    # ------------------------------------------------------------ dibujo
    def dibujar_fondo(self, s) -> None:
        t, m = self.tema, self.m
        res = m.resultado
        n_duelo = len(res.duelos) + 1
        self.dibujar_cabecera(s, f"Duelo {n_duelo}/{m.n_duelos}")
        rival = m.rival(self.jid)
        v = res.victorias
        dibujo.blit_centrado(s, t.texto(f"{self.yo.nombre} {v[self.jid]} – {v[1 - self.jid]} {rival.nombre}",
                                        "normal", "tinta_suave"), (640, 76))
        s.blit(t.texto("Clic: marcar para descartar", "chica", "tinta_suave"), (32, 152))
        s.blit(t.texto("Arrastra una carta a la zona roja para jugarla", "chica", "tinta_suave"), (32, 172))
        s.blit(t.texto("(o pulsa 1-6)", "chica", "tinta_suave"), (32, 192))

        # zona de juego (rectángulo discontinuo rojo con un +)
        sobre = self.arrastrando and ZONA.inflate(60, 60).collidepoint(self._rect_arrastre().center)
        if sobre:
            dibujo.relleno_alfa(s, t.c["objetivo"], [ZONA.topleft, ZONA.topright, ZONA.bottomright,
                                                     ZONA.bottomleft], 40)
        dibujo.rect_discontinuo(s, t.c["objetivo"], ZONA, 3 if not sobre else 5)
        if self.jugando is None:
            pulso = 1 + 0.08 * math.sin(self.t * 4)
            pygame.draw.circle(s, t.c["objetivo"], ZONA.center, int(20 * pulso), 3)
            c = ZONA.center
            pygame.draw.line(s, t.c["objetivo"], (c[0] - 9, c[1]), (c[0] + 9, c[1]), 3)
            pygame.draw.line(s, t.c["objetivo"], (c[0], c[1] - 9), (c[0], c[1] + 9), 3)

        self._dibujar_historial(s)
        self.dibujar_intel(s, pygame.Rect(930, 70, 330, 92), 30)

        # mano
        for i, c in enumerate(self.mano):
            if i == self.presionada and self.arrastrando:
                continue
            if self.jugando and self.jugando[0] == i:
                continue
            self._dibujar_carta(s, i, self._rect(i))
        if self.presionada is not None and self.arrastrando:
            self._dibujar_carta(s, self.presionada, self._rect_arrastre(), alzada=True)
        if self.jugando is not None:
            i, tt = self.jugando
            k = min(1.0, tt / 0.25)
            ini = self._rect(i) if not self.arrastrando else self._rect_arrastre()
            fin = pygame.Rect(0, 0, *CARTA)
            fin.center = ZONA.center
            r = pygame.Rect(0, 0, *CARTA)
            r.center = (ini.centerx + (fin.centerx - ini.centerx) * k, ini.centery + (fin.centery - ini.centery) * k)
            self._dibujar_carta(s, i, r)

    def _dibujar_carta(self, s, i: int, rect: pygame.Rect, alzada: bool = False) -> None:
        t, m = self.tema, self.m
        c = self.mano[i]
        try:
            sub = self.yo.especie(c.especie_id).nombre.split()[-1]
        except KeyError:
            sub = ""
        if alzada:
            pygame.draw.rect(s, (205, 202, 194), rect.move(8, 10), border_radius=10)
        dibujo.carta(s, t, rect, c.fenotipo, m.fen.nombre(c.fenotipo), sub,
                     borde=t.c["objetivo"] if i in self.sel else None, seleccionada=i in self.sel)
        if i in self.nuevas:
            capa = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(capa, (*t.c["acento"][:3], int(140 * self.nuevas[i] / 0.7)), capa.get_rect(),
                             border_radius=10)
            s.blit(capa, rect)
        s.blit(t.texto(str(i + 1), "chica", "tinta_suave"), (rect.x + 8, rect.y + 6))

    def _dibujar_historial(self, s) -> None:
        """Duelos ya jugados en este combate (información pública)."""
        t, m = self.tema, self.m
        res = m.resultado
        x, y = 930, 180
        s.blit(t.texto("Este combate", "normal", negrita=True), (x, y))
        s.blit(t.texto("tú", "chica", "tinta_suave"), (x + 40, y + 28))
        s.blit(t.texto("rival", "chica", "tinta_suave"), (x + 82, y + 28))
        y += 50
        if not res.duelos:
            s.blit(t.texto("Aún no hay duelos.", "chica", "tinta_suave"), (x, y))
        for d in res.duelos:
            mia, suya = d.cartas[self.jid].fenotipo, d.cartas[1 - self.jid].fenotipo
            s.blit(t.texto(f"{d.indice + 1}.", "chica"), (x, y + 6))
            s.blit(dibujo.icono_fenotipo(t, mia, 30), (x + 36, y))
            s.blit(dibujo.icono_fenotipo(t, suya, 30), (x + 82, y))
            if d.ganador is None:
                txt, col = "empate", "empata"
            elif d.ganador == self.jid:
                txt, col = "ganas", "gana"
            else:
                txt, col = "pierdes", "pierde"
            s.blit(t.texto(txt, "chica", col, negrita=True), (x + 126, y + 6))
            y += 36


class DueloEscena(Escena):
    """Revelación pública de un único duelo."""

    def __init__(self, app, duelo, al_continuar):
        super().__init__(app)
        self.m = app.motor
        self.d = duelo
        self.al_continuar = al_continuar
        self.t = 0.0
        self.oculto = 0.5     # segundos boca abajo
        self.giro = 0.35      # segundos del giro
        self.fin = self.oculto + self.giro + 0.15
        self.boton((self.W - 52, 12, 40, 40), "?", lambda: setattr(self, "overlay", OverlayAyuda(self)))
        self.boton((1060, 636, 190, 58), "Continuar", self._continuar, tam="media",
                   color_borde=self.tema.c["acento"])

    def _continuar(self) -> None:
        if self.t < self.fin:
            self.t = self.fin
            return
        self.al_continuar()

    def manejar_extra(self, ev) -> None:
        if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_SPACE, pygame.K_RETURN):
            self._continuar()

    def actualizar(self, dt: float) -> None:
        super().actualizar(dt)
        self.t += dt

    def dibujar_fondo(self, s) -> None:
        t, m, d = self.tema, self.m, self.d
        res = m.resultado
        dibujo.blit_centrado(s, t.texto(f"Duelo {d.indice + 1}/{m.n_duelos}", "grande", titulo=True), (640, 44))
        w, h = 160, 220
        centros = ((420, 300), (860, 300))
        revelado = self.t >= self.oculto + self.giro / 2
        terminado = self.t >= self.fin
        for lado, (cx, cy) in enumerate(centros):
            dibujo.blit_centrado(s, t.texto(m.jugadores[lado].nombre, "grande", titulo=True), (cx, cy - h // 2 - 34))
            # temblor mientras está boca abajo, luego giro (escala en x)
            dx = math.sin(self.t * 40 + lado) * 3 if self.t < self.oculto else 0
            ancho = w
            if self.oculto <= self.t < self.oculto + self.giro:
                k = (self.t - self.oculto) / self.giro
                ancho = max(4, int(w * abs(math.cos(k * math.pi))))
            r = pygame.Rect(0, 0, ancho, h)
            r.center = (cx + dx, cy)
            c = d.cartas[lado]
            borde = None
            if terminado and d.ganador is not None:
                borde = t.c["gana"] if d.ganador == lado else t.c["pierde"]
            if revelado:
                dibujo.carta(s, t, r, c.fenotipo, m.fen.nombre(c.fenotipo) if ancho > 80 else "", borde=borde,
                             seleccionada=terminado and d.ganador == lado)
            else:
                dibujo.carta(s, t, r, None, oculta=True)

        if terminado:
            a, b = d.cartas[0].fenotipo, d.cartas[1].fenotipo
            if d.ganador is None:
                txt, col = f"Empate: {m.fen.nombre(a)} contra {m.fen.nombre(b)}", "empata"
                dibujo.blit_centrado(s, t.texto("=", "enorme", "empata"), (640, 300))
            else:
                g, p = (a, b) if d.ganador == 0 else (b, a)
                txt = f"{m.fen.nombre(g)} {m.fen.verbo(g, p)} {m.fen.nombre(p)}"
                col = "gana"
                ini, fin = (520, 300), (760, 300)
                if d.ganador == 1:
                    ini, fin = fin, ini
                dibujo.flecha(s, t.c["gana"], ini, fin, 5, 18, t)
            dibujo.blit_centrado(s, t.texto(txt, "grande", col, titulo=True), (640, 470))
            for lado, (cx, _) in enumerate(centros):
                v = d.cromos[lado]
                if v:
                    ancho = dibujo.ancho_cromos(t, v, "media", 28, "+" if v > 0 else "")
                    dibujo.cantidad_cromos(s, t, v, (cx - ancho // 2, 530), "media", 28, "+" if v > 0 else "",
                                           color="gana" if v > 0 else "pierde")

        # marcador del combate
        v = self._victorias(incluir_actual=terminado)
        j0, j1 = m.jugadores
        dibujo.blit_centrado(s, t.texto(f"{j0.nombre} {v[0]} – {v[1]} {j1.nombre}", "media"), (640, 590))
        x0 = 640 - (m.n_duelos * 30) // 2
        for i in range(m.n_duelos):
            cx = x0 + i * 30 + 15
            if i < d.indice or (i == d.indice and terminado):
                dd = res.duelos[i]
                col = t.c["empata"] if dd.ganador is None else (t.c["gana"] if dd.ganador == 0 else t.c["pierde"])
                pygame.draw.circle(s, col, (cx, 628), 9)
            pygame.draw.circle(s, t.c["linea"], (cx, 628), 9, 2)
        dibujo.blit_centrado(s, t.texto("(verde = gana " + j0.nombre + ", rojo = gana " + j1.nombre + ")",
                                        "chica", "tinta_suave"), (640, 656))

    def _victorias(self, incluir_actual: bool) -> list[int]:
        v = [0, 0]
        for dd in self.m.resultado.duelos[:self.d.indice + (1 if incluir_actual else 0)]:
            if dd.ganador is not None:
                v[dd.ganador] += 1
        return v
