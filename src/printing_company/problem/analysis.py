r"""Pós-processamento da solução do modelo: tempo real com setup e consumo
de energia.

O modelo relaxado (`printing_company.problem.model`) dá as horas $t$ que
cada máquina fica produzindo, sem os setups. As funções deste módulo
calculam, a partir dessas horas, as grandezas do artigo:

- `operating_times`: o **tempo real** de cada máquina, com o setup. No
  artigo, a máquina $m$ gasta $A_{im}$ horas de setup para cada item $i$
  designado a ela ($x_{im} = 1$). O modelo relaxado agrega os itens por
  máquina e não diz quantos itens cada uma recebe, então contamos **um
  setup por máquina ligada**:

  $$
  \tau_m = t_m + A_m \, [t_m > 0].
  $$

  Toda máquina ligada recebe pelo menos um item, então esse é um limite
  inferior para o tempo do artigo. Os setups não entram na restrição de
  capacidade, então $\tau_m$ pode passar um pouco de $T$.
- `energy_consumption`: o **consumo de energia** de cada máquina, em kWh.
  Como na função objetivo (1) do artigo, o consumo $kw_m$ da Tabela 1 é a
  energia por hora de operação (a potência), e a máquina consome
  $kw_m$ durante todo o tempo real, setup incluído:

  $$
  E_m = kw_m \, \tau_m.
  $$

  O custo de energia do artigo é $c \sum_m E_m$, com a tarifa
  $c$ = `printing_company.settings.Settings.energy_price`, de 0,86 real
  por kWh (veja `energy_cost`).

As horas vêm de `Solution.x`, indexadas pelos nomes das variáveis (os
`Machine.id`): `dict(zip(problem.variable_names, solution.x))`.

`solve_portfolio` junta tudo: escolhe o menor número de turnos que torna
a carteira viável, monta e resolve o modelo e devolve um
`PortfolioResult`, com as grandezas acima para cada máquina
(`MachineResult`). É o que o comando `printing-company` mostra (veja
`printing_company.report`).
"""

import logging
import math
from collections.abc import Mapping, Sequence
from typing import Self

from pydantic import BaseModel, ConfigDict, NonNegativeFloat, PositiveInt
from rich.text import Text

from printing_company.problem.model import (
    Objective,
    build_problem,
    min_capacity,
)
from printing_company.problem.spec import (
    FinishingMachine,
    Machine,
    Portfolio,
    PrintingMachine,
)
from printing_company.settings import settings
from simplex import PivotingRule, Solver, Status
from simplex.defaults import TOLERANCE
from simplex.logs import RICH_TEXT

__all__ = [
    "MachineResult",
    "PortfolioResult",
    "energy_consumption",
    "energy_cost",
    "operating_times",
    "solve_portfolio",
]

logger = logging.getLogger(__name__)


def operating_times(
    *,
    hours: Mapping[str, float],
    machines: Sequence[Machine],
) -> dict[str, float]:
    r"""Tempo real $\tau_m = t_m + A_m [t_m > 0]$ de cada máquina, em horas.

    **Argumentos:**

    - `hours`: as horas de produção $t_m$ de cada máquina, pelo `id`
      (máquinas ausentes contam como desligadas);
    - `machines`: as máquinas, com os setups $A_m$ (`Machine.setup`).

    Devolve um dicionário com todas as `machines`, na ordem dada. Uma
    máquina desligada ($t_m = 0$, a menos da tolerância
    `simplex.defaults.TOLERANCE` do simplex) não tem setup.

    **Exemplo:** a `Print01` (setup de 0,25 h) imprime 20 h; a `Print02`
    fica desligada.

    >>> from printing_company.problem.spec import PrintingMachine
    >>> machines = [
    ...     PrintingMachine(id="Print01", speed=10_500, setup=0.25, consumption=40),
    ...     PrintingMachine(id="Print02", speed=3_000, setup=0.5, consumption=112),
    ... ]
    >>> operating_times(hours={"Print01": 20.0, "Print02": 0.0}, machines=machines)
    {'Print01': 20.25, 'Print02': 0.0}

    **Levanta:** `ValueError` se alguma hora for negativa.

    >>> operating_times(hours={"Print01": -1.0}, machines=machines)
    Traceback (most recent call last):
        ...
    ValueError: Horas negativas para Print01: -1.0.
    """
    times: dict[str, float] = {}
    for machine in machines:
        t = hours.get(machine.id, 0.0)
        if t < -TOLERANCE:
            raise ValueError(f"Horas negativas para {machine.id}: {t}.")
        times[machine.id] = t + machine.setup if t > TOLERANCE else 0.0
    return times


def energy_consumption(
    *,
    times: Mapping[str, float],
    machines: Sequence[Machine],
) -> dict[str, float]:
    r"""Consumo de energia $E_m = kw_m \, \tau_m$ de cada máquina, em kWh.

    **Argumentos:**

    - `times`: os tempos reais $\tau_m$, em horas, como os de
      `operating_times`;
    - `machines`: as máquinas, com os consumos $kw_m$
      (`Machine.consumption`).

    **Exemplo:** a `Print01` (40 kWh por hora) fica ligada 20,25 h.

    >>> from printing_company.problem.spec import PrintingMachine
    >>> machines = [
    ...     PrintingMachine(id="Print01", speed=10_500, setup=0.25, consumption=40),
    ...     PrintingMachine(id="Print02", speed=3_000, setup=0.5, consumption=112),
    ... ]
    >>> energy_consumption(times={"Print01": 20.25, "Print02": 0.0}, machines=machines)
    {'Print01': 810.0, 'Print02': 0.0}

    **Exemplo completo:** a carteira I do artigo com dois turnos.

    >>> from printing_company.problem import data
    >>> from printing_company.problem.model import build_problem
    >>> from printing_company.settings import settings
    >>> machines = [*data.printers, *data.finishers]
    >>> problem = build_problem(
    ...     portfolio=data.portfolios[0],
    ...     printers=data.printers,
    ...     finishings=data.finishers,
    ...     capacity=2 * settings.shift_hours,
    ... )
    >>> hours = dict(zip(problem.variable_names, problem.solve().x.tolist()))
    >>> times = operating_times(hours=hours, machines=machines)
    >>> {name: round(tau, 2) for name, tau in times.items() if tau > 0}
    {'Print01': 20.25, 'Print04': 20.17, 'Print05': 9.25, 'Finish02': 19.5}
    >>> energy = energy_consumption(times=times, machines=machines)
    >>> {name: round(e, 2) for name, e in energy.items() if e > 0}
    {'Print01': 810.0, 'Print04': 484.08, 'Print05': 20.35, 'Finish02': 2184.0}
    >>> round(sum(energy.values()), 2), round(energy_cost(energy=energy), 2)
    (3498.43, 3008.65)
    """
    return {
        machine.id: machine.consumption * times.get(machine.id, 0.0)
        for machine in machines
    }


def energy_cost(
    *,
    energy: Mapping[str, float],
    price: float | None = None,
) -> float:
    r"""Custo total de energia $c \sum_m E_m$, em reais.

    A tarifa $c$ é `price` ou, se `None`, a de
    `printing_company.settings.Settings.energy_price` (0,86 real por kWh).

    **Exemplo:** 810 kWh a 0,86 real por kWh.

    >>> round(energy_cost(energy={"Print01": 810.0}), 2)
    696.6
    >>> energy_cost(energy={"Print01": 810.0}, price=1.0)
    810.0
    """
    if price is None:
        price = settings.energy_price
    return price * sum(energy.values())


class MachineResult(BaseModel):
    r"""O resultado de uma máquina na solução ótima.

    **Exemplo:** a `Print01` (10 500 m/h, setup de 0,25 h, 40 kW) ligada
    20 horas.

    >>> from printing_company.problem.spec import PrintingMachine
    >>> r = MachineResult(
    ...     machine=PrintingMachine(
    ...         id="Print01", speed=10_500, setup=0.25, consumption=40
    ...     ),
    ...     hours=20.0,
    ...     time=20.25,
    ...     energy=810.0,
    ... )
    >>> r.is_on, r.produced
    (True, 210000.0)
    """

    model_config = ConfigDict(frozen=True)

    machine: Machine
    """A máquina."""

    hours: NonNegativeFloat
    r"""Horas de produção $t_m$, a variável do modelo."""

    time: NonNegativeFloat
    r"""Tempo real $\tau_m$, com o setup (veja `operating_times`)."""

    energy: NonNegativeFloat
    r"""Consumo $E_m = kw_m \tau_m$, em kWh (veja `energy_consumption`)."""

    @property
    def is_on(self: Self) -> bool:
        r"""Se a máquina fica ligada ($t_m > 0$, a menos da tolerância)."""
        return self.hours > TOLERANCE

    @property
    def produced(self: Self) -> float:
        r"""Metros produzidos, $v_m t_m$."""
        return self.machine.speed * self.hours


class PortfolioResult(BaseModel):
    r"""O resultado de uma carteira, como devolvido por `solve_portfolio`.

    Se o simplex não chegar a uma solução ótima, `status` diz por quê, e
    `objective_value` e `machines` ficam vazios.
    """

    model_config = ConfigDict(frozen=True)

    portfolio: Portfolio
    """A carteira de pedidos."""

    objective: Objective
    """O objetivo minimizado."""

    shifts: PositiveInt
    """Número $d$ de turnos diários do horizonte."""

    capacity: NonNegativeFloat
    r"""Capacidade $T = d \cdot$ `shift_hours` de cada máquina, em horas."""

    status: Status
    """Como o simplex terminou."""

    objective_value: float | None = None
    """Valor ótimo do modelo relaxado, em horas ou kWh (veja
    `printing_company.problem.model.Objective.unit`)."""

    machines: tuple[MachineResult, ...] = ()
    """Uma entrada por máquina: as impressoras, depois as de acabamento."""

    @property
    def printers(self: Self) -> tuple[MachineResult, ...]:
        """As entradas das máquinas de impressão."""
        return tuple(
            r for r in self.machines if isinstance(r.machine, PrintingMachine)
        )

    @property
    def finishers(self: Self) -> tuple[MachineResult, ...]:
        """As entradas das máquinas de acabamento."""
        return tuple(
            r for r in self.machines if isinstance(r.machine, FinishingMachine)
        )

    @property
    def total_hours(self: Self) -> float:
        r"""Total de horas de produção, $\sum_m t_m$."""
        return sum((r.hours for r in self.machines), start=0.0)

    @property
    def total_time(self: Self) -> float:
        r"""Tempo real total, $\sum_m \tau_m$, em horas."""
        return sum((r.time for r in self.machines), start=0.0)

    @property
    def total_energy(self: Self) -> float:
        r"""Consumo total, $\sum_m E_m$, em kWh."""
        return sum((r.energy for r in self.machines), start=0.0)

    @property
    def cost(self: Self) -> float:
        r"""Custo de energia $c \sum_m E_m$, em reais (veja `energy_cost`)."""
        return energy_cost(
            energy={r.machine.id: r.energy for r in self.machines}
        )


def solve_portfolio(
    *,
    portfolio: Portfolio,
    printers: Sequence[PrintingMachine],
    finishings: Sequence[FinishingMachine],
    objective: Objective = Objective.TIME,
    shift_hours: float | None = None,
    solver: Solver | None = None,
) -> PortfolioResult:
    r"""Resolve uma carteira com o menor número de turnos que a torna
    viável.

    O número de turnos é $d = \lceil T_{\min} / h \rceil$, com
    $T_{\min}$ de `printing_company.problem.model.min_capacity` e $h$ as
    horas de um turno; o modelo é o de
    `printing_company.problem.model.build_problem`, com $T = d h$.

    **Argumentos:**

    - `portfolio`, `printers`, `finishings` e `objective`: como em
      `build_problem`;
    - `shift_hours`: as horas $h$ de um turno; com `None`, usa
      `printing_company.settings.Settings.shift_hours`;
    - `solver`: o `simplex.Solver`; com `None`, usa a regra
      lexicográfica.

    No nível DEBUG do `logging`, registra o modelo montado (o
    `simplex.Problem`, como escrito no papel) antes de resolvê-lo, sem
    quebrar as linhas (veja `simplex.logs.Handler`).

    **Devolve:** o `PortfolioResult`.

    **Exemplo:** a carteira I do artigo precisa de 2 turnos (20 h).

    >>> from printing_company.problem import data
    >>> result = solve_portfolio(
    ...     portfolio=data.portfolios[0],
    ...     printers=data.printers,
    ...     finishings=data.finishers,
    ... )
    >>> result.shifts, result.capacity, result.status
    (2, 20.0, <Status.OPTIMAL: 'optimal'>)
    >>> [r.machine.id for r in result.machines if r.is_on]
    ['Print01', 'Print04', 'Print05', 'Finish02']
    >>> round(result.objective_value, 2), round(result.total_time, 2)
    (67.75, 69.17)
    >>> round(result.total_energy, 2), round(result.cost, 2)
    (3498.43, 3008.65)
    """
    shift_hours = settings.shift_hours if shift_hours is None else shift_hours
    solver = (
        Solver(rule=PivotingRule.LEXICOGRAPHIC) if solver is None else solver
    )
    t_min = min_capacity(
        portfolio=portfolio, printers=printers, finishings=finishings
    )
    shifts = max(1, math.ceil(t_min / shift_hours - TOLERANCE))
    capacity = shifts * shift_hours
    problem = build_problem(
        portfolio=portfolio,
        printers=printers,
        finishings=finishings,
        capacity=capacity,
        objective=objective,
    )
    if logger.isEnabledFor(logging.DEBUG):
        text = str(problem)
        logger.debug(
            f"Modelo da {portfolio.label} (T = {capacity:g} h, "
            f"objetivo: {objective.label})\n{text}",
            extra={RICH_TEXT: Text(text)},
        )
    solution = problem.solve(solver=solver)
    result = PortfolioResult(
        portfolio=portfolio,
        objective=objective,
        shifts=shifts,
        capacity=capacity,
        status=solution.status,
    )
    if solution.status != Status.OPTIMAL or solution.x is None:
        return result

    machines: list[Machine] = [*printers, *finishings]
    hours = dict(zip(problem.variable_names, solution.x.tolist(), strict=True))
    # operating_times recusa horas negativas além da tolerância; os
    # resíduos (como -1e-16) viram 0.
    times = operating_times(hours=hours, machines=machines)
    energy = energy_consumption(times=times, machines=machines)
    return result.model_copy(
        update={
            "objective_value": solution.objective,
            "machines": tuple(
                MachineResult(
                    machine=m,
                    hours=max(hours[m.id], 0.0),
                    time=times[m.id],
                    energy=energy[m.id],
                )
                for m in machines
            ),
        }
    )
