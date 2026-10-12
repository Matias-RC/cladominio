"""Grafo de fenotipos: quién vence a quién y adyacencias."""
from __future__ import annotations

from ..config import Config


class Fenotipos:
    def __init__(self, cfg: Config):
        f = cfg.fenotipos
        self.orden: list[str] = list(f.orden)
        self.nombres: dict[str, str] = {k: f.nombres.get(k, k) for k in self.orden}
        self.vence: dict[str, frozenset[str]] = {k: frozenset(f.vence.get(k, [])) for k in self.orden}
        self.verbos: dict = {k: dict(v) for k, v in (f.get("verbos") or {}).items()}

        if f.adyacencias == "auto":
            n = len(self.orden)
            self.adyacentes = {
                fen: frozenset({self.orden[(i - 1) % n], self.orden[(i + 1) % n]})
                for i, fen in enumerate(self.orden)
            }
        else:
            self.adyacentes = {k: frozenset(f.adyacencias.get(k, [])) for k in self.orden}

        self._validar()

    def _validar(self) -> None:
        for a in self.orden:
            for b in self.vence[a]:
                if b not in self.vence:
                    raise ValueError(f"Fenotipo desconocido en 'vence': {b}")
                if a in self.vence[b]:
                    raise ValueError(f"'{a}' y '{b}' se vencen mutuamente")

    def __iter__(self):
        return iter(self.orden)

    def __len__(self) -> int:
        return len(self.orden)

    def nombre(self, fen: str) -> str:
        return self.nombres[fen]

    def duelo(self, a: str, b: str) -> int:
        """+1 si a vence a b, -1 si b vence a a, 0 si empatan."""
        if b in self.vence[a]:
            return 1
        if a in self.vence[b]:
            return -1
        return 0

    def verbo(self, ganador: str, perdedor: str) -> str:
        """Texto para "<ganador> <verbo> <perdedor>" (configurable en fenotipos.verbos)."""
        return self.verbos.get(ganador, {}).get(perdedor, "vence a")

    def son_adyacentes(self, a: str, b: str) -> bool:
        return b in self.adyacentes[a]

    def pierde_contra(self, fen: str) -> list[str]:
        return [o for o in self.orden if fen in self.vence[o]]
