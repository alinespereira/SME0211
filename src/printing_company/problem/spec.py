r"""Dados do problema da gráfica: máquinas e carteira de pedidos.

Os modelos seguem os parâmetros do artigo *Energy consumption optimization
in a printing company* (Gestão & Produção, 2024), na versão relaxada do
trabalho, focada no tempo de impressão:

- as **máquinas de impressão** $m \in M$ e as **máquinas de acabamento**
  $n \in N$, cada uma com velocidade $v$ (em metros por hora), tempo
  médio de setup $A$ (em horas) e consumo de energia $kw$ (em kWh), nas
  unidades da Tabela 1 do artigo;
- a **carteira de pedidos**: os itens $i \in I$, cada um com demanda $D_i$
  (em metros), e o subconjunto $F \subseteq I$ dos itens que, depois de
  impressos, também passam por uma máquina de acabamento.

Com esses dados, o tempo para produzir $z$ metros de um item na máquina
$m$ é $T_m z + A_m$ horas, em que $T_m = 1 / v_m$ é o tempo por metro.
Os dados do artigo estão em `printing_company.problem.data`.

Todos os modelos são imutáveis (`frozen`).
"""

from abc import ABC
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
    r"""Máquina da gráfica (classe base abstrata).

    Guarda os dados comuns às máquinas de impressão (`PrintingMachine`) e de
    acabamento (`FinishingMachine`). Não pode ser instanciada diretamente: use uma
    das subclasses.

    **Exemplo:**

    >>> Machine(id="M1", speed=200, setup=30, consumption=50)
    Traceback (most recent call last):
        ...
    TypeError: Base é abstrata

    Os três números precisam ser positivos:

    >>> PrintingMachine(id="P1", speed=0, setup=30, consumption=50)  # doctest: +ELLIPSIS
    Traceback (most recent call last):
        ...
    pydantic_core._pydantic_core.ValidationError: 1 validation error for PrintingMachine
    speed
      Input should be greater than 0 ...
    """

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
    r"""Consumo de energia $kw$ da máquina, em kWh."""

    def __init__(self, **data: Any) -> None:  # noqa: ANN401
        """Cria a máquina, recusando instâncias da própria `Machine`.

        **Levanta:** `TypeError` se a classe for `Machine`, e não uma
        subclasse.
        """
        if type(self) is Machine:
            raise TypeError("Base é abstrata")
        super().__init__(**data)


class PrintingMachine(Machine):
    r"""Máquina de impressão $m \in M$. Todo item passa por uma delas.

    **Exemplo:** a `Print01` do artigo, que imprime 10 500 m/h, com setup
    médio de 0,25 h e consumo de 40 kWh.

    >>> p = PrintingMachine(id="Print01", speed=10_500, setup=0.25, consumption=40)
    >>> p
    PrintingMachine(id='Print01', speed=10500.0, setup=0.25, consumption=40.0)
    >>> round(p.setup + 15_000 / p.speed, 4)  # horas para 15 000 m, com setup
    1.6786
    >>> p.speed = 300  # doctest: +ELLIPSIS
    Traceback (most recent call last):
        ...
    pydantic_core._pydantic_core.ValidationError: 1 validation error for PrintingMachine
    speed
      Instance is frozen ...
    """

    model_config = ConfigDict(frozen=True)
    pass


class FinishingMachine(Machine):
    r"""Máquina de acabamento $n \in N$. Só os itens que exigem acabamento
    (`Demand.requires_finishing`) passam por uma delas, depois de
    impressos.

    **Exemplo:**

    >>> f = FinishingMachine(id="Finish01", speed=7_800, setup=0.5, consumption=40)
    >>> f.setup
    0.5
    >>> isinstance(f, Machine)
    True
    """

    model_config = ConfigDict(frozen=True)
    pass


class Demand(BaseModel):
    r"""Demanda de um item $i \in I$ da carteira de pedidos.

    **Exemplo:** 1500 metros de formulários que precisam de acabamento.

    >>> d = Demand(label="formulários", quantity=1500, requires_finishing=True)
    >>> d.quantity
    1500.0
    >>> Demand(label="notas fiscais", quantity=800).requires_finishing
    False
    """

    model_config = ConfigDict(frozen=True)

    label: str
    """Nome do item (por exemplo, o tipo de formulário)."""

    quantity: PositiveFloat
    r"""Demanda $D_i$ do item, em metros."""

    requires_finishing: bool = False
    r"""Se o item precisa de acabamento, isto é, se $i \in F$."""


class Portfolio(BaseModel):
    r"""Carteira de pedidos: as demandas de todos os itens $i \in I$.

    **Exemplo:**

    >>> portfolio = Portfolio(
    ...     label="Escritório",
    ...     demands=[
    ...         Demand(label="notas fiscais", quantity=800),
    ...         Demand(label="formulários", quantity=1500, requires_finishing=True),
    ...         Demand(label="boletos", quantity=1200, requires_finishing=True),
    ...     ]
    ... )
    >>> portfolio.with_finishing
    2700.0
    >>> portfolio.without_finishing
    800.0

    Os totais também aparecem na serialização:

    >>> portfolio.model_dump()["with_finishing"]
    2700.0
    """

    model_config = ConfigDict(frozen=True)

    label: str
    """Nome da carteira (por exemplo, `"Portfolio I"`)."""

    demands: list[Demand]
    """Demandas dos itens, na ordem em que foram pedidos."""

    @computed_field
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

    @computed_field
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
