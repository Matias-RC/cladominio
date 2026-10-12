"""Carga de configuración YAML con acceso por atributo.

    cfg = cargar_reglas()
    cfg.combate.k            -> 6
    cfg["combate"]["k"]      -> 6   (también funciona como dict)
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

RAIZ = Path(__file__).resolve().parent.parent
DIR_CONFIG = RAIZ / "config"


class Config(dict):
    """dict con acceso por atributo, recursivo."""

    def __getattr__(self, clave: str) -> Any:
        try:
            return self[clave]
        except KeyError as e:
            raise AttributeError(f"Falta la clave de configuración '{clave}'") from e

    def __setattr__(self, clave: str, valor: Any) -> None:
        self[clave] = valor

    @staticmethod
    def envolver(valor: Any) -> Any:
        if isinstance(valor, dict):
            return Config({k: Config.envolver(v) for k, v in valor.items()})
        if isinstance(valor, list):
            return [Config.envolver(v) for v in valor]
        return valor


def _mezclar(base: dict, extra: dict) -> dict:
    """Mezcla profunda: `extra` pisa a `base`."""
    out = dict(base)
    for k, v in extra.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _mezclar(out[k], v)
        else:
            out[k] = v
    return out


def cargar(nombre: str, sobrescribir: dict | None = None) -> Config:
    """Carga config/<nombre>.yaml. Si existe config/<nombre>.local.yaml se mezcla encima
    (útil para experimentar con el balance sin tocar el archivo base)."""
    ruta = DIR_CONFIG / f"{nombre}.yaml"
    with open(ruta, encoding="utf-8") as f:
        datos = yaml.safe_load(f) or {}
    local = DIR_CONFIG / f"{nombre}.local.yaml"
    if local.exists():
        with open(local, encoding="utf-8") as f:
            datos = _mezclar(datos, yaml.safe_load(f) or {})
    if sobrescribir:
        datos = _mezclar(datos, sobrescribir)
    return Config.envolver(datos)


def cargar_reglas(sobrescribir: dict | None = None) -> Config:
    return cargar("reglas", sobrescribir)


def cargar_ui(sobrescribir: dict | None = None) -> Config:
    return cargar("ui", sobrescribir)
