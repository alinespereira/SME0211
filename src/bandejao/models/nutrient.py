"""Modelos do domínio: nutrientes e suas metas para o almoço."""

import csv
from collections.abc import Mapping
from enum import StrEnum
from pathlib import Path
from typing import Self

from pydantic import BaseModel, Field

from .base import Limit, Unit


class NutrientType(StrEnum):
    """Nutrientes considerados nas restrições do modelo.

    Os valores são o prefixo das colunas de nutrientes dos CSVs em ``data/``
    (ex.: ``energia`` em ``energia_kcal``).
    """

    ENERGY = "energia"
    PROTEIN = "proteina"
    CARBOHYDRATE = "carboidrato"
    LIPID = "lipidio"
    FIBER = "fibra"
    IRON = "ferro"
    CALCIUM = "calcio"
    SODIUM = "sodio"


class Nutrient(BaseModel):
    """Um nutriente e a faixa que o almoço deve atingir.

    Cada nutriente gera até duas restrições no PL: uma de mínimo e uma de
    máximo, conforme os extremos definidos em ``limit``.

    Atributos:
        type: qual nutriente é.
        unit: unidade em que a quantidade é medida.
        limit: faixa aceitável da quantidade no almoço (derivada das DRIs).
        description: texto livre explicando a origem da meta.
    """

    type: NutrientType
    unit: Unit
    limit: Limit = Field(default_factory=Limit)
    description: str = ""

    @property
    def column(self) -> str:
        """Nome da coluna deste nutriente em ``alimentos_estimados.csv``.

        Exemplo: ``energia_kcal`` para energia em kcal.
        """
        return f"{self.type}_{self.unit.lower()}"

    def is_met(self, amount: float) -> bool:
        """Indica se a quantidade ``amount`` respeita a meta (extremos inclusos)."""
        return amount in self.limit

    @classmethod
    def from_csv_row(cls, row: Mapping[str, str]) -> Self:
        """Cria um nutriente a partir de uma linha de ``metas_dri_almoco.csv``.

        A coluna ``nutriente`` tem o formato ``<nutriente>_<unidade>`` (ex.:
        ``energia_kcal``); a parte antes do último ``_`` é o valor de
        :class:`NutrientType`. Células vazias em ``minimo``/``maximo`` indicam
        que não há limite daquele lado.
        """
        name, _, _unit = row["nutriente"].rpartition("_")
        return cls(
            type=NutrientType(name),
            unit=Unit(row["unidade"]),
            limit=Limit(
                minimum=_optional_float(row["minimo"]),
                maximum=_optional_float(row["maximo"]),
            ),
            description=row["base_DRI_diaria"],
        )


def _optional_float(text: str) -> float | None:
    """Converte uma célula do CSV em ``float``, ou ``None`` se estiver vazia."""
    text = text.strip()
    return float(text) if text else None


def load_nutrients(path: Path) -> list[Nutrient]:
    """Lê todas as metas de um CSV no formato de ``metas_dri_almoco.csv``."""
    with path.open(encoding="utf-8", newline="") as f:
        return [Nutrient.from_csv_row(row) for row in csv.DictReader(f)]
