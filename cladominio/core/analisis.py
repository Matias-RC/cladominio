"""Cálculos de apoyo (usados por la UI y por la IA)."""
from __future__ import annotations

from .motor import Motor


def expresion_jugador(m: Motor, jid: int) -> dict[str, float]:
    """Distribución de cartas esperada del mazo de `jid` (ponderada como en el combate)."""
    j = m.jugadores[jid]
    pdom = float(m.cfg.expresion.prob_dominante)
    pesos = [max(m._peso_especie(e), 0.0) for e in j.especies]
    if sum(pesos) <= 0:
        pesos = [1.0] * len(j.especies)
    tot = sum(pesos) or 1.0
    dist = {f: 0.0 for f in m.fen.orden}
    for e, w in zip(j.especies, pesos):
        for f, p in e.expresion(m.fen.orden, pdom).items():
            dist[f] += p * w / tot
    return dist


def distribucion_intel(m: Motor, jid: int) -> dict[str, float] | None:
    intel = m.intel[jid]
    if not intel:
        return None
    cartas = intel[1]
    return {f: cartas.count(f) / len(cartas) for f in m.fen.orden}


def ventaja_estimada(m: Motor, jid: int) -> float:
    """Esperanza de (victorias - derrotas) por duelo contra lo último que mostró el rival
    (o contra un rival uniforme si no hay información). Rango [-1, 1]."""
    mia = expresion_jugador(m, jid)
    rival = distribucion_intel(m, jid) or {f: 1 / len(m.fen) for f in m.fen.orden}
    return sum(pa * pb * m.fen.duelo(a, b) for a, pa in mia.items() for b, pb in rival.items())
