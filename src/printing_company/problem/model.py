"""Modelo de otimização linear da gráfica: a versão relaxada do artigo,
com dois objetivos possíveis, o tempo de operação das máquinas ou o
consumo de energia.

.. include:: ../../../docs/modulos/printing_company.problem.model.md
"""

from collections.abc import Sequence
from enum import StrEnum
from typing import Self

import numpy as np

from printing_company.problem.spec import (
    FinishingMachine,
    Portfolio,
    PrintingMachine,
)
from simplex import Constraint, Problem

__all__ = [
    "SCALE",
    "Objective",
    "build_problem",
    "min_capacity",
]

SCALE = 1_000.0
"""Escala das restrições de demanda: velocidades e demandas entram no
modelo em milhares de metros (por hora). Fica aqui, e não em
`printing_company.settings`, porque é parte da formulação (deixa os
coeficientes na escala dos custos), e não um parâmetro do cenário."""


class Objective(StrEnum):
    """O que o modelo minimiza; o valor é o da opção `--objective`."""

    TIME = "time"
    r"""Tempo de operação, $\sum_m t_m$, em horas (objetivo (16) do artigo,
    sem os setups)."""

    ENERGY = "energy"
    r"""Consumo de energia, $\sum_m kw_m t_m$, em kWh (objetivo (1) do
    artigo, sem os setups e sem a tarifa)."""

    @property
    def label(self: Self) -> str:
        """Nome do objetivo em português, para a saída do comando."""
        match self:
            case Objective.TIME:
                return "tempo"
            case Objective.ENERGY:
                return "energia"

    @property
    def unit(self: Self) -> str:
        """Unidade do valor ótimo: horas (`h`) ou kWh."""
        match self:
            case Objective.TIME:
                return "h"
            case Objective.ENERGY:
                return "kWh"


def build_problem(
    *,
    portfolio: Portfolio,
    printers: Sequence[PrintingMachine],
    finishings: Sequence[FinishingMachine],
    capacity: float | None = None,
    objective: Objective = Objective.TIME,
) -> Problem:
    """Monta o modelo relaxado como um `simplex.Problem` (veja o módulo).

    Sem `capacity`, as restrições de capacidade ficam de fora.
    """
    if capacity is not None and capacity <= 0:
        raise ValueError(f"capacity deve ser positiva, mas é {capacity}.")

    machines = (*printers, *finishings)
    names = tuple(machine.id for machine in machines)

    # Tempo: custo 1 para cada variável (a soma das horas ligadas).
    # Energia: a potência de cada máquina, em kW (kWh por hora ligada).
    match objective:
        case Objective.TIME:
            c = np.ones(len(machines), dtype=np.float64)
        case Objective.ENERGY:
            c = np.array([m.consumption for m in machines], dtype=np.float64)

    # Velocidades em milhares de metros por hora. Só as impressoras
    # imprimem e só as máquinas de acabamento acabam: cada restrição de
    # demanda tem coeficiente 0 nas máquinas do outro tipo.
    speeds = np.array([m.speed for m in machines], dtype=np.float64) / SCALE
    is_printer = np.array(
        [1.0] * len(printers) + [0.0] * len(finishings),
        dtype=np.float64,
    )

    printer_constraint = Constraint(
        coefs=speeds * is_printer,
        sense=">=",
        rhs=portfolio.total / SCALE,
    )
    finishing_constraint = Constraint(
        coefs=speeds * (1.0 - is_printer),
        sense=">=",
        rhs=portfolio.with_finishing / SCALE,
    )

    # Capacidade: cada máquina fica ligada no máximo T horas.
    capacity_constraints = (
        ()
        if capacity is None
        else tuple(
            Constraint(coefs=e_j, sense="<=", rhs=capacity)
            for e_j in np.eye(len(machines))
        )
    )

    return Problem(
        sense="min",
        c=c,
        constraints=(
            printer_constraint,
            finishing_constraint,
            *capacity_constraints,
        ),
        names=names,
    )


def min_capacity(
    *,
    portfolio: Portfolio,
    printers: Sequence[PrintingMachine],
    finishings: Sequence[FinishingMachine],
) -> float:
    r"""Menor capacidade $T_{\min}$, em horas, que torna o modelo viável."""
    printing = portfolio.total / sum(printer.speed for printer in printers)
    finishing = (
        portfolio.with_finishing / sum(f.speed for f in finishings)
        if portfolio.with_finishing > 0
        else 0.0
    )
    return max(printing, finishing)
