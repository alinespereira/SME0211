"""Dados do problema da gráfica: máquinas e carteira de pedidos.

.. include:: ../../../docs/modulos/printing_company.problem.spec.md
"""

from abc import ABC
from functools import cached_property
from typing import Any

from pydantic import BaseModel, ConfigDict, PositiveFloat, computed_field

__all__ = [
    "Demand",
    "FinishingMachine",
    "Machine",
    "Portfolio",
    "PrintingMachine",
]


class Machine(BaseModel, ABC):
    """Máquina da gráfica (classe base abstrata, use uma subclasse)."""

    model_config = ConfigDict(frozen=True)

    id: str
    """Identificador da máquina (por exemplo, `"P1"`)."""

    speed: PositiveFloat
    r"""Velocidade de operação $v$, em metros por hora. O tempo por metro
    é $T = 1 / v$, em horas."""

    setup: PositiveFloat
    r"""Tempo médio de setup $A$, em horas: o tempo gasto para preparar a
    máquina antes de produzir um item."""

    consumption: PositiveFloat
    r"""Consumo de energia $kw$ da máquina, em kWh por hora de operação
    (a potência, em kW; veja `printing_company.problem.analysis`)."""

    def __init__(self, **data: Any) -> None:  # noqa: ANN401
        """Cria a máquina; levanta `TypeError` se a classe for `Machine`."""
        if type(self) is Machine:
            raise TypeError("Base é abstrata")
        super().__init__(**data)


class PrintingMachine(Machine):
    r"""Máquina de impressão $m \in M$. Todo item passa por uma delas."""

    model_config = ConfigDict(frozen=True)
    pass


class FinishingMachine(Machine):
    r"""Máquina de acabamento $n \in N$, para os itens com
    `Demand.requires_finishing`.
    """

    model_config = ConfigDict(frozen=True)
    pass


class Demand(BaseModel):
    r"""Demanda de um item $i \in I$ da carteira de pedidos."""

    model_config = ConfigDict(frozen=True)

    label: str
    """Nome do item (por exemplo, o tipo de formulário)."""

    quantity: PositiveFloat
    r"""Demanda $D_i$ do item, em metros."""

    requires_finishing: bool = False
    r"""Se o item precisa de acabamento, isto é, se $i \in F$."""


class Portfolio(BaseModel):
    r"""Carteira de pedidos: as demandas de todos os itens $i \in I$."""

    model_config = ConfigDict(frozen=True)

    label: str
    """Nome da carteira (por exemplo, `"Portfolio I"`)."""

    demands: list[Demand]
    """Demandas dos itens, na ordem em que foram pedidos."""

    @computed_field  # type: ignore[prop-decorator]
    @cached_property
    def total(self) -> float:
        r"""Total, em metros, dos itens demandados:
        $\sum_{i \in I} D_i$."""
        return sum(
            (demand.quantity for demand in self.demands),
            start=0.0,
        )

    @computed_field  # type: ignore[prop-decorator]
    @cached_property
    def with_finishing(self) -> float:
        r"""Total, em metros, dos itens que precisam de acabamento:
        $\sum_{i \in F} D_i$."""
        return sum(
            (
                demand.quantity
                for demand in self.demands
                if demand.requires_finishing
            ),
            start=0.0,
        )

    @computed_field  # type: ignore[prop-decorator]
    @cached_property
    def without_finishing(self) -> float:
        r"""Total, em metros, dos itens que não precisam de acabamento:
        $\sum_{i \in I \setminus F} D_i$."""
        return sum(
            (
                demand.quantity
                for demand in self.demands
                if not demand.requires_finishing
            ),
            start=0.0,
        )
