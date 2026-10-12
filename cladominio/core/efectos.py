"""Efectos de pociones.

Para crear una poción nueva:
  1. Escribe una función con el decorador @efecto("mi_efecto").
  2. Añade el artículo en config/reglas.yaml con `tipo: pocion` y `efecto: mi_efecto`.

Cada efecto recibe el ResultadoDuelo (mutable) y lo modifica antes de aplicarlo.
Los efectos de la especie perdedora se aplican después de los de la ganadora.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .modelos import Carta


@dataclass
class ResultadoDuelo:
    indice: int
    cartas: tuple[Carta, Carta]
    ganador: int | None                 # 0, 1 o None (empate)
    cromos: list[float] = field(default_factory=lambda: [0.0, 0.0])      # delta por jugador
    diversidad: list[float] = field(default_factory=lambda: [0.0, 0.0])  # delta a la especie de cada carta
    notas: list[tuple[int | None, str]] = field(default_factory=list)    # (jugador que lo ve | None=todos, texto)

    @property
    def perdedor(self) -> int | None:
        return None if self.ganador is None else 1 - self.ganador


# firma: (resultado, lado_de_la_especie_con_la_pocion, params) -> None
FuncionEfecto = Callable[[ResultadoDuelo, int, dict], None]


@dataclass
class Efecto:
    al_ganar: FuncionEfecto | None = None
    al_perder: FuncionEfecto | None = None


EFECTOS: dict[str, Efecto] = {}


def efecto(nombre: str, cuando: str = "al_perder"):
    def deco(fn: FuncionEfecto) -> FuncionEfecto:
        e = EFECTOS.setdefault(nombre, Efecto())
        setattr(e, cuando, fn)
        return fn
    return deco


# ---------------------------------------------------------------------------
@efecto("cuello_botella", "al_perder")
def _cuello_botella(res: ResultadoDuelo, lado: int, params: dict) -> None:
    dano = float(params.get("diversidad_rival_por_derrota", 2))
    rival = 1 - lado
    res.diversidad[rival] -= dano
    res.notas.append((lado, f"Cuello de botella: la especie rival pierde {dano:g}% de diversidad"))


@efecto("efecto_fundador", "al_perder")
def _efecto_fundador(res: ResultadoDuelo, lado: int, params: dict) -> None:
    rival = 1 - lado
    res.diversidad[lado] = -float(params.get("diversidad_perdida", 1))
    res.cromos[lado] = float(params.get("cromos_ganados", 0.5))
    res.cromos[rival] = 0.0
    res.diversidad[rival] = min(res.diversidad[rival], 0.0)
    res.notas.append((lado, "Efecto fundador: pierdes poca diversidad y ganas cromos"))
    res.notas.append((rival, "El rival tenía efecto fundador: no ganas nada en este duelo"))
