"""Punto de entrada.

    python main.py                 # juego normal
    python main.py --semilla 42    # partida reproducible
"""
import argparse

from cladominio.ui.app import App


def main() -> None:
    ap = argparse.ArgumentParser(description="Cachipún Evolución: el dominio de los clados")
    ap.add_argument("--semilla", type=int, default=None, help="semilla aleatoria (partidas reproducibles)")
    ap.add_argument("--ia", default="heuristica", help="IA rival (ver cladominio/ia/__init__.py)")
    args = ap.parse_args()
    App(semilla=args.semilla, ia=args.ia).run()


if __name__ == "__main__":
    main()
