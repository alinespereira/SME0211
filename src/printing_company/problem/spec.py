r"""Dados do problema da gráfica: máquinas e carteira de pedidos.

Os modelos seguem os parâmetros do artigo *Energy consumption optimization
in a printing company* (Gestão & Produção, 2024), na versão relaxada do
trabalho, focada no tempo de impressão:

- as **máquinas de impressão** $m \in M$ e as **máquinas de acabamento**
  $n \in N$, cada uma com velocidade $v$ (em metros por minuto), tempo
  médio de setup $A$ (em minutos) e consumo de energia $kw$ (em kWh);
- a **carteira de pedidos**: os itens $i \in I$, cada um com demanda $D_i$
  (em metros), e o subconjunto $F \subseteq I$ dos itens que, depois de
  impressos, também passam por uma máquina de acabamento.

Com esses dados, o tempo para produzir $z$ metros de um item na máquina
$m$ é $T_m z + A_m$, em que $T_m = 1 / v_m$ é o tempo por metro.

Todos os modelos são imutáveis (`frozen`).
"""

from abc import ABC
from typing import Any

from pydantic import BaseModel, ConfigDict, PositiveFloat, computed_field


class Machine(BaseModel, ABC):
    r"""Máquina da gráfica (classe base abstrata).

    Guarda os dados comuns às máquinas de impressão (`Printer`) e de
    acabamento (`Finishing`). Não pode ser instanciada diretamente: use uma
    das subclasses.

    **Exemplo:**

    >>> Machine(id="M1", speed=200, setup=30, consumption=50)
    Traceback (most recent call last):
        ...
    TypeError: Base é abstrata

    Os três números precisam ser positivos:

    >>> Printer(id="P1", speed=0, setup=30, consumption=50)  # doctest: +ELLIPSIS
    Traceback (most recent call last):
        ...
    pydantic_core._pydantic_core.ValidationError: 1 validation error for Printer
    speed
      Input should be greater than 0 ...
    """

    model_config = ConfigDict(frozen=True)

    id: str
    """Identificador da máquina (por exemplo, `"P1"`)."""

    speed: PositiveFloat
    r"""Velocidade de operação $v$, em metros por minuto. O tempo por metro
    é $T = 1 / v$."""

    setup: PositiveFloat
    r"""Tempo médio de setup $A$, em minutos: o tempo gasto para preparar a
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


class Printer(Machine):
    r"""Máquina de impressão $m \in M$. Todo item passa por uma delas.

    **Exemplo:** uma impressora que imprime 200 m/min, com setup médio de
    30 minutos e consumo de 50 kWh.

    >>> p = Printer(id="P1", speed=200, setup=30, consumption=50)
    >>> p
    Printer(id='P1', speed=200.0, setup=30.0, consumption=50.0)
    >>> 1 / p.speed  # tempo por metro, em minutos
    0.005
    >>> p.speed = 300  # doctest: +ELLIPSIS
    Traceback (most recent call last):
        ...
    pydantic_core._pydantic_core.ValidationError: 1 validation error for Printer
    speed
      Instance is frozen ...
    """

    model_config = ConfigDict(frozen=True)
    pass


class Finishing(Machine):
    r"""Máquina de acabamento $n \in N$. Só os itens que exigem acabamento
    (`Demand.requires_finishing`) passam por uma delas, depois de
    impressos.

    **Exemplo:**

    >>> f = Finishing(id="A1", speed=100, setup=15, consumption=20)
    >>> f.setup
    15.0
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
