"""Pós-processamento da solução do modelo: tempo real com setup e consumo
de energia.

.. include:: ../../../docs/modulos/printing_company.problem.analysis.md
"""

import logging
import math
import time
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
    r"""Tempo real $\tau_m = t_m + A_m [t_m > 0]$ de cada máquina, em horas."""
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
    r"""Consumo de energia $E_m = kw_m \, \tau_m$ de cada máquina, em kWh."""
    return {
        machine.id: machine.consumption * times.get(machine.id, 0.0)
        for machine in machines
    }


def energy_cost(
    *,
    energy: Mapping[str, float],
    price: float | None = None,
) -> float:
    r"""Custo de energia $c \sum_m E_m$, em reais (tarifa `price` ou a de
    `settings`).
    """
    if price is None:
        price = settings.energy_price
    return price * sum(energy.values())


class MachineResult(BaseModel):
    """O resultado de uma máquina na solução ótima."""

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
    """O resultado de uma carteira (`solve_portfolio`); sem ótimo, só o
    `status` é preenchido.
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

    solve_seconds: NonNegativeFloat = 0.0
    """Tempo de execução de `simplex.Problem.solve` (forma padrão, Fase 1
    e Fase 2), em segundos de relógio (`time.perf_counter`). Com
    `--debug`, inclui o tempo de montar e registrar os tableaux."""

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
    """Resolve uma carteira com o menor número de turnos que a torna
    viável (veja o módulo).
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
    start = time.perf_counter()
    solution = problem.solve(solver=solver)
    elapsed = time.perf_counter() - start
    result = PortfolioResult(
        portfolio=portfolio,
        objective=objective,
        shifts=shifts,
        capacity=capacity,
        status=solution.status,
        solve_seconds=elapsed,
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
