"""Simulación sin interfaz: IA contra IA, para probar el balance de config/reglas.yaml.

    python simular.py                  # 200 partidas
    python simular.py -n 1000 -s 42    # 1000 partidas con semilla
"""
from __future__ import annotations

import argparse
import statistics
from collections import Counter

from cladominio.config import cargar_reglas
from cladominio.core import Fase, Motor
from cladominio.ia import IAS


def jugar(reglas, semilla: int, ia: str = "heuristica", max_rondas: int = 200) -> Motor:
    m = Motor(reglas, ("IA-1", "IA-2"), semilla=semilla)
    ias = [IAS[ia](m, i, semilla * 2 + i) for i in range(2)]
    pasos = 0
    while m.fase != Fase.FIN and m.ronda <= max_rondas:
        for jid in sorted(m.pendientes()):
            ias[jid].actuar()
        pasos += 1
        if pasos > max_rondas * 20:
            break
    return m


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=200)
    ap.add_argument("-s", "--semilla", type=int, default=0)
    args = ap.parse_args()

    reglas = cargar_reglas()
    ganadores, rondas, motivos = Counter(), [], Counter()
    combates = paz = unilateral = 0
    for i in range(args.n):
        m = jugar(reglas, args.semilla + i)
        ganadores["empate" if m.empate else ("sin terminar" if m.fase != Fase.FIN else m.ganador)] += 1
        rondas.append(m.ronda)
        motivos[m.motivo_fin.split("!")[0][:40]] += 1
        for e in m.eventos:
            if e.texto.startswith("Combate:"):
                combates += 1
            elif e.texto.startswith("Paz mutua"):
                paz += 1
            elif "rechazó" in e.texto:
                unilateral += 1

    print(f"Partidas: {args.n}")
    print(f"Ganadores: {dict(ganadores)}")
    print(f"Rondas: media {statistics.mean(rondas):.1f}, mediana {statistics.median(rondas)}, "
          f"min {min(rondas)}, max {max(rondas)}")
    tot = combates + paz + unilateral or 1
    print(f"Etapa 2: combate {combates / tot:.0%}, paz mutua {paz / tot:.0%}, unilateral {unilateral / tot:.0%}")
    print("Motivos de fin:")
    for k, v in motivos.most_common(6):
        print(f"  {v:4d}  {k}")


if __name__ == "__main__":
    main()
