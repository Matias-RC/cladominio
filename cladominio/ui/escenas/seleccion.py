"""Etapa 1: selección natural, especiación y pociones (la pantalla del boceto)."""
from __future__ import annotations

import pygame

from .. import dibujo
from ..widgets import ZonaClic
from .base import OverlayRegistro
from .comun import EscenaJugador

C_ACT = (350, 335)   # centro del pentágono actual
C_OBJ = (900, 335)   # centro del pentágono objetivo
RADIO = 100
Y_LINEAS = 548
PASO_LINEAS = 25
X_LINEA = (290, 1150)


class SeleccionEscena(EscenaJugador):
    def __init__(self, app, jid: int, novedades=None):
        super().__init__(app, jid)
        self.idx = 0
        self.tab = "seleccion"
        self.resultado_clado = ""
        self._reset_objetivo()
        t = self.tema
        rojo, verde = t.c["objetivo"], t.c["actual"]

        # navegación entre especies
        self.boton((380, 18, 46, 46), "<", lambda: self._mover(-1), tam="grande",
                   habilitado=lambda: len(self.yo.especies) > 1)
        self.boton((854, 18, 46, 46), ">", lambda: self._mover(1), tam="grande",
                   habilitado=lambda: len(self.yo.especies) > 1)

        # pestañas
        for i, (clave, nombre) in enumerate((("seleccion", "Selección"), ("especiacion", "Especiación"),
                                             ("pociones", "Pociones"))):
            self.boton((180 + i * 215, 84, 195, 48), nombre, lambda c=clave: self._tab(c), tam="media",
                       color_borde=rojo, activo=lambda c=clave: self.tab == c)

        # columna izquierda
        self.boton((26, 520, 112, 120), "Listo", self._listo, tam="grande", rayado=t.c["acento"])

        # --- pestaña selección
        en_sel = lambda: self.tab == "seleccion"
        self.boton((550, 384, 180, 46), "Aplicar", self._aplicar, tam="media", color_borde=verde,
                   visible=en_sel, habilitado=self._hay_cambio)
        self.boton((565, 436, 150, 34), "Restablecer", self._reset_objetivo, tam="normal",
                   visible=en_sel, habilitado=self._hay_cambio)
        vs = dibujo.vertices(C_OBJ, RADIO, len(self.m.fen))
        for v, f in zip(vs, self.m.fen.orden):
            self.widgets.append(ZonaClic((v[0] - 34, v[1] - 34, 68, 68),
                                         izq=lambda f=f: self._objetivo(dom=f),
                                         der=lambda f=f: self._objetivo(rec=f), visible=en_sel))

        # --- pestaña especiación
        en_esp = lambda: self.tab == "especiacion"
        arts = self.m.cfg.mercado.articulos
        self.potenciadores = [a for a in arts if arts[a].tipo == "potenciador"]
        for i, a in enumerate(self.potenciadores):
            self.boton((1100, 268 + i * 96, 130, 50), "Intentar", lambda a=a: self._cladogenesis(a),
                       tam="media", color_borde=t.c["acento"], visible=en_esp,
                       habilitado=lambda a=a: self.yo.inventario[a] > 0)

        # --- pestaña pociones
        en_poc = lambda: self.tab == "pociones"
        self.pociones = [a for a in arts if arts[a].tipo == "pocion"]
        for i, a in enumerate(self.pociones):
            self.boton((1060, 218 + i * 96, 170, 50), "Activar aquí", lambda a=a: self._pocion(a),
                       tam="normal", color_borde=t.c["acento"], visible=en_poc,
                       habilitado=lambda a=a: self.yo.inventario[a] > 0)

        if novedades:
            self.overlay = OverlayRegistro(self, jid, novedades, "Novedades")

    # ------------------------------------------------------------ estado
    @property
    def especie(self):
        return self.yo.especies[self.idx % len(self.yo.especies)]

    def _mover(self, d: int) -> None:
        self.idx = (self.idx + d) % len(self.yo.especies)
        self._reset_objetivo()

    def _tab(self, clave: str) -> None:
        self.tab = clave

    def _reset_objetivo(self) -> None:
        e = self.especie
        self.obj_dom, self.obj_rec = e.dominante, e.recesivo

    def _objetivo(self, dom: str | None = None, rec: str | None = None) -> None:
        if dom:
            # si el recesivo coincidía con el dominante (especialista) lo arrastramos
            if self.obj_rec == self.obj_dom:
                self.obj_rec = dom
            self.obj_dom = dom
        if rec:
            self.obj_rec = rec

    def _hay_cambio(self) -> bool:
        e = self.especie
        return (self.obj_dom, self.obj_rec) != (e.dominante, e.recesivo)

    # ------------------------------------------------------------ acciones
    def _aplicar(self) -> None:
        c = self.intentar(self.m.seleccionar, self.jid, self.especie.id, self.obj_dom, self.obj_rec)
        if c:
            self.mensaje("Cambio aplicado.", "gana")

    def _cladogenesis(self, art: str) -> None:
        r = self.intentar(self.m.intentar_cladogenesis, self.jid, art, self.especie.id)
        if not r:
            return
        if r.exito:
            self.resultado_clado = f"¡Éxito ({r.probabilidad:.0%})! {r.madre.nombre} da origen a {r.hija.nombre}."
            self.idx = self.yo.especies.index(r.hija)
            self._reset_objetivo()
            self.mensaje("¡Nueva especie! Puedes reasignar su fenotipo en Selección.", "gana", 5)
        else:
            self.resultado_clado = f"Falló ({r.probabilidad:.0%}). La próxima vez será más probable."
            self.mensaje("La cladogénesis falló.", "pierde")

    def _pocion(self, art: str) -> None:
        nombre = self.m.articulo(art).nombre
        self.intentar(self.m.activar_pocion, self.jid, art, self.especie.id,
                      exito=f"{nombre} activa en {self.especie.nombre}.")

    def _listo(self) -> None:
        self.m.listo(self.jid)
        self.app.director.avanzar()

    # ------------------------------------------------------------ dibujo
    def dibujar_fondo(self, s) -> None:
        t, m, e = self.tema, self.m, self.especie
        n = len(self.yo.especies)
        self.dibujar_cabecera(s)
        dibujo.blit_centrado(s, t.texto(f"Especie {self.idx % n + 1}/{n}", "chica", "tinta_suave"), (640, 18))
        dibujo.blit_centrado(s, t.texto(e.nombre, "grande", titulo=True), (640, 46))

        # columna izquierda: cromos y diversidad de la especie
        dibujo.cantidad_cromos(s, t, self.yo.cromos, (22, 76), "grande", 36, "= ")
        dmax = float(m.cfg.diversidad.maxima)
        dibujo.barra_diversidad(s, t, pygame.Rect(40, 135, 84, 330), e.diversidad, e.gastada, dmax)
        dibujo.blit_centrado(s, t.texto(f"{dibujo.fmt(e.efectiva)}% / {dibujo.fmt(e.diversidad)}%", "chica"),
                             (82, 480))
        dibujo.blit_centrado(s, t.texto("disponible / total", 13, "tinta_suave"), (82, 498))

        self.dibujar_intel(s, pygame.Rect(890, 70, 290, 92), 30)

        pdom = float(m.cfg.expresion.prob_dominante)
        actual = e.expresion(m.fen.orden, pdom)
        # pentágono actual (siempre visible: es la madre en especiación)
        dibujo.pentagono(s, t, C_ACT, RADIO, m.fen.orden, m.fen.nombres, actual, t.c["actual"],
                         e.dominante, e.recesivo, tam_etiqueta="chica")
        self._texto_genotipo(s, e.dominante, e.recesivo, (C_ACT[0], 500), "actual")

        objetivo = actual
        if self.tab == "seleccion":
            objetivo = self._dibujar_tab_seleccion(s)
        elif self.tab == "especiacion":
            self._dibujar_tab_especiacion(s)
        else:
            self._dibujar_tab_pociones(s)
        self._dibujar_lineas(s, actual, objetivo)

    def _texto_genotipo(self, s, dom, rec, centro, color) -> None:
        t, n = self.tema, self.m.fen.nombre
        tipo = "Especialista" if dom == rec else "Generalista"
        txt = f"{tipo}: {n(dom)}" + ("" if dom == rec else f" / {n(rec)}")
        dibujo.blit_centrado(s, t.texto(txt, "normal", color, negrita=True), centro)

    def _dibujar_tab_seleccion(self, s) -> dict:
        t, m, e = self.tema, self.m, self.especie
        rojo = t.c["objetivo"]
        # coste
        if self._hay_cambio():
            c = m.coste_seleccion(self.jid, e.id, self.obj_dom, self.obj_rec)
            x = 470
            img = t.texto("Coste :", "media", negrita=True)
            s.blit(img, (x, 158))
            x += img.get_width() + 10
            r = dibujo.cantidad_cromos(s, t, c.cromos, (x, 156), "media", 30)
            x = r.right + 24
            s.blit(t.texto(f"+ {dibujo.fmt(c.diversidad)}% diversidad", "media"), (x, 158))
            if c.usa_cambio_gratis:
                dibujo.blit_centrado(s, t.texto("(cambio de dominante gratis)", "chica", "acento"), (640, 228))
        else:
            dibujo.blit_centrado(s, t.texto("Elige un objetivo en el pentágono rojo", "media", "tinta_suave"),
                                 (640, 175))
            if e.cambio_gratis != "ninguno":
                txt = "a un nodo adyacente" if e.cambio_gratis == "adyacente" else "a cualquier fenotipo"
                dibujo.blit_centrado(s, t.texto("Tiene un cambio de dominante gratis", "chica", "acento"), (640, 214))
                dibujo.blit_centrado(s, t.texto(f"({txt})", "chica", "acento"), (640, 232))

        # flecha objetivo
        dibujo.blit_centrado(s, t.texto("Objetivo", "grande", rojo, titulo=True), (640, 272))
        dibujo.flecha(s, rojo, (520, 306), (760, 312), 3, 16, t)

        pdom = float(m.cfg.expresion.prob_dominante)
        from ...core.modelos import Especie
        obj = Especie(0, "", self.obj_dom, self.obj_rec, 0).expresion(m.fen.orden, pdom)
        dibujo.pentagono(s, t, C_OBJ, RADIO, m.fen.orden, m.fen.nombres, obj, rojo,
                         self.obj_dom, self.obj_rec, tam_etiqueta="chica")
        self._texto_genotipo(s, self.obj_dom, self.obj_rec, (C_OBJ[0], 500), "objetivo")
        for i, txt in enumerate(("clic izq. = dominante", "clic der. = recesivo")):
            dibujo.blit_centrado(s, t.texto(txt, "chica", "tinta_suave"), (640, 486 + i * 18))
        return obj

    def _fila_articulo(self, s, y: int, art: str, extra: str = "") -> None:
        t = self.tema
        a = self.m.articulo(art)
        r = pygame.Rect(520, y, 720, 84)
        pygame.draw.rect(s, t.c["panel"], r, border_radius=8)
        s.blit(t.texto(f"{a.nombre}  ×{self.yo.inventario[art]}", "media", negrita=True), (r.x + 12, r.y + 6))
        dibujo.parrafo(s, t, a.descripcion + (f"  {extra}" if extra else ""), (r.x + 12, r.y + 38), 540, "chica")

    def _dibujar_tab_especiacion(self, s) -> None:
        t, m = self.tema, self.m
        cc = m.cfg.cladogenesis
        p = m.prob_cladogenesis(self.jid)
        cartas = self.yo.inventario["carta_mutacion"]
        s.blit(t.texto(f"Probabilidad de éxito: {p:.0%}", "grande", "acento", titulo=True), (520, 150))
        s.blit(t.texto(f"base {cc.prob_base:.0%} + {cartas} carta(s) de mutación × {cc.prob_por_carta:.0%} "
                       f"+ {self.yo.fallos_cladogenesis} fallo(s) × {cc.prob_por_fallo:.0%}  (máx. {cc.prob_maxima:.0%})",
                       "chica", "tinta_suave"), (520, 198))
        s.blit(t.texto(f"Especies: {len(self.yo.especies)}/{m.cfg.jugadores.max_especies} · "
                       f"La hija se lleva el {cc.fraccion_hija:.0%} de la diversidad de la madre "
                       f"(mín. {cc.diversidad_minima_madre}%)", "chica", "tinta_suave"), (520, 222))
        for i, art in enumerate(self.potenciadores):
            a = m.articulo(art)
            madre = f"Madre: {self.especie.nombre}." if a.elegir_madre else "Madre: al azar."
            self._fila_articulo(s, 252 + i * 96, art, madre)
        if self.resultado_clado:
            dibujo.parrafo(s, t, self.resultado_clado, (520, 452), 720, "normal", "acento")

    def _dibujar_tab_pociones(self, s) -> None:
        t, m, e = self.tema, self.m, self.especie
        s.blit(t.texto("Pociones: se activan sobre la especie que estás viendo", "media", titulo=True), (520, 166))
        for i, art in enumerate(self.pociones):
            a = m.articulo(art)
            self._fila_articulo(s, 202 + i * 96, art, f"Dura {a.duracion} rondas.")
        y = 202 + len(self.pociones) * 96 + 6
        if e.pociones:
            txt = ", ".join(f"{m.articulo(p.articulo).nombre} ({p.rondas_restantes} r.)" for p in e.pociones)
            s.blit(t.texto(f"Activas en {e.nombre}: {txt}", "normal", "acento"), (520, y))
        else:
            s.blit(t.texto(f"{e.nombre} no tiene pociones activas.", "normal", "tinta_suave"), (520, y))
        if m.cfg.paz.anula_pociones_activadas:
            s.blit(t.texto("Ojo: si esta ronda hay paz mutua, las pociones activadas hoy se pierden.",
                           "chica", "pierde"), (520, y + 28))

    def _dibujar_lineas(self, s, actual: dict, objetivo: dict) -> None:
        """Las líneas inferiores del boceto: verde = actual, rojo = objetivo."""
        t, m = self.tema, self.m
        x0, x1 = X_LINEA
        for i, f in enumerate(m.fen.orden):
            y = Y_LINEAS + i * PASO_LINEAS
            img = t.texto(m.fen.nombre(f), "normal", negrita=True)
            s.blit(img, (x0 - 14 - img.get_width(), y - img.get_height() // 2))
            dibujo.flecha(s, t.c["tinta"], (x0, y), (x1, y), 3, 10, t)
            pa, po = actual[f], objetivo[f]
            dibujo.marcador_cuadrado(s, t.c["objetivo"], (x0 + po * (x1 - x0 - 20), y))
            dibujo.marcador_rombo(s, t.c["actual"], (x0 + pa * (x1 - x0 - 20), y))
            txt = f"{pa:.0%}" if abs(pa - po) < 1e-9 else f"{pa:.0%} -> {po:.0%}"
            s.blit(t.texto(txt, "chica", "tinta_suave"), (x1 + 12, y - 9))
