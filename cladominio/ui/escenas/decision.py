"""Etapa 2: decisión secreta de aceptar o rechazar el combate."""
from __future__ import annotations

import pygame

from ...core.analisis import distribucion_intel, expresion_jugador, ventaja_estimada
from .. import dibujo
from .comun import EscenaJugador


class DecisionEscena(EscenaJugador):
    def __init__(self, app, jid: int):
        super().__init__(app, jid)
        t = self.tema
        self.boton((380, 600, 230, 80), "Aceptar\ncombate", lambda: self._decidir(True), tam="media",
                   color_borde=t.c["gana"], rayado=t.c["gana"])
        self.boton((670, 600, 230, 80), "Rechazar\n(paz)", lambda: self._decidir(False), tam="media",
                   color_borde=t.c["pierde"], rayado=t.c["pierde"])

    def _decidir(self, acepta: bool) -> None:
        self.m.decidir(self.jid, acepta)
        self.app.director.avanzar()

    def dibujar_fondo(self, s) -> None:
        t, m = self.tema, self.m
        self.dibujar_cabecera(s, "¿Combatir?")
        dibujo.blit_centrado(s, t.texto("Decides en secreto; el rival decide a la vez.", "normal", "tinta_suave"),
                             (640, 78))

        # --- tus especies
        x, y = 30, 110
        s.blit(t.texto("Tus especies", "media", titulo=True), (x, y))
        y += 40
        dmax = float(m.cfg.diversidad.maxima)
        for e in self.yo.especies:
            r = pygame.Rect(x, y, 360, 54)
            pygame.draw.rect(s, t.c["panel"], r, border_radius=8)
            s.blit(dibujo.icono_fenotipo(t, e.dominante, 40), (r.x + 6, r.y + 7))
            if not e.especialista:
                s.blit(dibujo.icono_fenotipo(t, e.recesivo, 24), (r.x + 44, r.y + 26))
            s.blit(t.texto(e.nombre, "normal", negrita=True), (r.x + 76, r.y + 4))
            dibujo.barra_diversidad(s, t, pygame.Rect(r.x + 76, r.y + 32, 200, 14), e.diversidad, e.gastada,
                                    dmax, vertical=False, etiqueta=False)
            s.blit(t.texto(f"{dibujo.fmt(e.efectiva)}%", "chica"), (r.x + 284, r.y + 28))
            if e.pociones:
                s.blit(t.texto(f"{len(e.pociones)} poc.", "chica", "acento"), (r.right - 52, r.y + 4))
            y += 62
            if y > 520:
                break

        # --- tu mazo esperado
        mia = expresion_jugador(m, self.jid)
        y += 16
        s.blit(t.texto("Tu mazo esperado", "normal", negrita=True), (x, y))
        self._barras_dist(s, mia, x, y + 30)

        # --- matriz de pagos
        k = float(m.cfg.combate.k)
        f = float(m.cfg.combate.factor_rechazo_unilateral)
        bono = m.cfg.paz.bono_diversidad
        cx, cy = 450, 140
        s.blit(t.texto("Matriz de pagos (tú, rival)", "media", titulo=True), (cx, cy - 34))
        celdas = [
            ["", "Rival acepta", "Rival rechaza"],
            ["Aceptas", f"Combate (±{dibujo.fmt(k)})", f"{dibujo.fmt(f * k)} , 0"],
            ["Rechazas", f"0 , {dibujo.fmt(f * k)}", f"{dibujo.fmt(k)} , {dibujo.fmt(k)}  +{bono}% div."],
        ]
        anchos = [120, 190, 210]
        for i, fila in enumerate(celdas):
            xx = cx
            for j, txt in enumerate(fila):
                r = pygame.Rect(xx, cy + i * 52, anchos[j], 52)
                if i and j:
                    pygame.draw.rect(s, t.c["panel"], r.inflate(-4, -4), border_radius=6)
                dibujo.blit_centrado(s, t.texto(txt, "chica" if j else "normal", negrita=not (i and j)), r.center)
                xx += anchos[j]
        if m.cfg.combate.modo == "interactivo":
            forma = (f"Combate: recibes {m.cfg.combate.cartas} cartas de tu pool genético y las juegas una a una "
                     f"(puedes descartar y robar {m.cfg.combate.descartes} veces). ")
        else:
            forma = f"Combate: {m.cfg.combate.cartas} duelos simultáneos. "
        notas = (forma + f"Cada duelo ganado: "
                 f"+{dibujo.fmt(k / m.cfg.combate.cartas)} cromos y +{m.cfg.combate.diversidad_por_duelo_ganado}% "
                 f"diversidad; perdido: -{dibujo.fmt(k / m.cfg.combate.cartas)} cromos y "
                 f"-{m.cfg.combate.diversidad_por_duelo_perdido}% diversidad. "
                 f"Si hay combate, ambos veréis las cartas del otro; con paz no se revela nada.")
        dibujo.parrafo(s, t, notas, (cx, cy + 170), 520, "chica", "tinta_suave")

        # --- inteligencia
        r = pygame.Rect(990, 110, 270, 110)
        self.dibujar_intel(s, r, 34)
        rival = distribucion_intel(m, self.jid)
        y = 240
        if rival:
            s.blit(t.texto("Mazo rival observado", "normal", negrita=True), (990, y))
            self._barras_dist(s, rival, 990, y + 30, ancho=150)
            y += 30 + len(m.fen) * 24 + 10
        v = ventaja_estimada(m, self.jid)
        color = "gana" if v > 0.05 else ("pierde" if v < -0.05 else "tinta")
        s.blit(t.texto("Ventaja estimada", "normal", negrita=True), (990, y))
        s.blit(t.texto(f"{v:+.2f}", "grande", color, titulo=True), (990, y + 26))
        base = "según sus últimas cartas" if rival else "contra un rival al azar"
        dibujo.parrafo(s, t, f"(victorias - derrotas esperadas por duelo, {base}; puede haber cambiado de fenotipo)",
                       (990, y + 72), 270, "chica", "tinta_suave")

    def _barras_dist(self, s, dist: dict, x: int, y: int, ancho: int = 200) -> None:
        t = self.tema
        for i, f in enumerate(self.m.fen.orden):
            yy = y + i * 24
            s.blit(dibujo.icono_fenotipo(t, f, 20), (x, yy))
            pygame.draw.rect(s, t.fen[f], (x + 26, yy + 4, int(ancho * dist[f]), 14), border_radius=3)
            pygame.draw.rect(s, t.c["linea"], (x + 26, yy + 4, ancho, 14), 1, border_radius=3)
            s.blit(t.texto(f"{dist[f]:.0%}", "chica"), (x + 32 + ancho, yy))
