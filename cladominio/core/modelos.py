"""Estructuras de datos del estado de juego (sin lógica de reglas)."""
from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass, field

GENEROS = [
    "Lapis", "Cartus", "Forfex", "Ignis", "Bombarda", "Silex", "Papyrus", "Lamina",
    "Fulgur", "Ferrum", "Clados", "Mutatus", "Genus", "Hélix", "Saxum", "Scintilla",
]
EPITETOS = [
    "rex", "minor", "vulgaris", "astuta", "furiosa", "pacifica", "rapida", "obscura",
    "magna", "fragilis", "audax", "silvestris", "nova", "antiqua", "ludens", "tenax",
    "versicolor", "cautus", "ferox", "humilis",
]


def nombre_aleatorio(rng: random.Random, genero: str | None = None) -> str:
    return f"{genero or rng.choice(GENEROS)} {rng.choice(EPITETOS)}"


@dataclass
class PocionActiva:
    articulo: str          # id del artículo en el mercado (p. ej. "cuello_botella")
    rondas_restantes: int
    ronda_activacion: int


@dataclass
class Especie:
    id: int
    nombre: str
    dominante: str
    recesivo: str
    diversidad: float                 # diversidad permanente ("vida")
    gastada: float = 0.0              # diversidad gastada esta ronda (se recarga al final)
    pociones: list[PocionActiva] = field(default_factory=list)
    cambio_gratis: str = "ninguno"    # ninguno | adyacente | libre (heredado de la cladogénesis)
    madre: int | None = None
    ronda_nacimiento: int = 0

    @property
    def efectiva(self) -> float:
        return max(0.0, self.diversidad - self.gastada)

    @property
    def especialista(self) -> bool:
        return self.dominante == self.recesivo

    def expresion(self, orden: list[str], prob_dominante: float) -> dict[str, float]:
        """Distribución de probabilidad de las cartas que produce esta especie."""
        dist = {f: 0.0 for f in orden}
        if self.especialista:
            dist[self.dominante] = 1.0
        else:
            dist[self.dominante] = prob_dominante
            dist[self.recesivo] = 1.0 - prob_dominante
        return dist


@dataclass
class Carta:
    fenotipo: str
    especie_id: int


@dataclass
class Jugador:
    id: int
    nombre: str
    cromos: float
    especies: list[Especie] = field(default_factory=list)
    inventario: Counter = field(default_factory=Counter)
    fallos_cladogenesis: int = 0
    siguiente_id_especie: int = 1

    def especie(self, especie_id: int) -> Especie:
        for e in self.especies:
            if e.id == especie_id:
                return e
        raise KeyError(f"El jugador {self.id} no tiene la especie {especie_id}")

    def nuevo_id(self) -> int:
        i = self.siguiente_id_especie
        self.siguiente_id_especie += 1
        return i

    def fenotipos_cubiertos(self) -> set[str]:
        return {e.dominante for e in self.especies}

    @property
    def vivo(self) -> bool:
        return bool(self.especies)
