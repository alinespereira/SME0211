"""Modelos do domínio: alimentos do cardápio e seus grupos."""

import csv
from collections.abc import Mapping
from enum import StrEnum
from pathlib import Path
from typing import Self

from pydantic import (
    BaseModel,
    Field,
    NonNegativeFloat,
    PositiveFloat,
    computed_field,
)

from .base import Limit
from .nutrient import NutrientType


class FoodGroup(StrEnum):
    """Grupo do alimento no prato do bandejão.

    Os valores são os mesmos da coluna ``grupo`` dos CSVs em ``data/``.
    """

    BASE = "base"
    LEGUME = "leguminosa"
    PROTEIN = "proteina"
    SIDE_DISH = "guarnicao"
    SALAD = "salada"
    DESSERT = "sobremesa"
    PREPARATION = "preparo"


class Food(BaseModel):
    """Um alimento que pode entrar no almoço.

    Cada alimento é uma variável de decisão do PL: a massa (em gramas, já
    pronto) servida no prato.

    Atributos:
        description: nome do alimento (ex.: "Arroz branco cozido").
        group: grupo do alimento, usado nas restrições de massa por grupo.
        raw_price: preço do alimento cru, em R$/kg.
        cooking_yield: massa pronta obtida por massa crua (ex.: 2,5 para o
            arroz, que absorve água; 0,7 para a carne, que perde água).
        portion: limites da porção servida, em gramas de alimento pronto.
        nutrition: quantidade de cada nutriente em 100 g do alimento pronto,
            na unidade do nutriente (kcal, g ou mg), como na tabela TACO.
    """

    description: str
    group: FoodGroup
    raw_price: PositiveFloat
    cooking_yield: PositiveFloat
    portion: Limit = Field(default_factory=lambda: Limit(minimum=0))
    nutrition: dict[NutrientType, NonNegativeFloat]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cooked_price(self) -> float:
        """Preço do alimento pronto, em R$/kg (preço cru ÷ rendimento)."""
        return self.raw_price / self.cooking_yield

    @property
    def cost_per_gram(self) -> float:
        """Custo de 1 g do alimento pronto, em R$ (coeficiente da função objetivo)."""
        return self.cooked_price / 1000

    def nutrient_per_gram(self, nutrient: NutrientType) -> float:
        """Quantidade de ``nutrient`` em 1 g do alimento pronto.

        É o coeficiente do alimento na restrição daquele nutriente. Nutrientes
        ausentes de ``nutrition`` contam como zero.
        """
        return self.nutrition.get(nutrient, 0.0) / 100

    @classmethod
    def from_csv_row(cls, row: Mapping[str, str]) -> Self:
        """Cria um alimento a partir de uma linha de ``alimentos_estimados.csv``.

        As colunas de nutrientes têm o formato ``<nutriente>_<unidade>``
        (ex.: ``energia_kcal``), em que ``<nutriente>`` é o valor de
        :class:`NutrientType`. A coluna ``preco_pronto_R$kg`` é ignorada,
        pois o preço pronto é calculado a partir do preço cru e do rendimento.
        """
        nutrition: dict[NutrientType, float] = {}
        for column, value in row.items():
            name, _, _unit = column.rpartition("_")
            if name in NutrientType:
                nutrition[NutrientType(name)] = float(value)
        return cls(
            description=row["alimento"],
            group=FoodGroup(row["grupo"]),
            raw_price=float(row["preco_cru_R$kg"]),
            cooking_yield=float(row["rendimento"]),
            portion=Limit(
                minimum=float(row["porcao_min_g"]),
                maximum=float(row["porcao_max_g"]),
            ),
            nutrition=nutrition,
        )


def load_foods(path: Path) -> list[Food]:
    """Lê todos os alimentos de um CSV no formato de ``alimentos_estimados.csv``."""
    with path.open(encoding="utf-8", newline="") as f:
        return [Food.from_csv_row(row) for row in csv.DictReader(f)]
