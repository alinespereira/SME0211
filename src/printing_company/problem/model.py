from typing import Sequence

import numpy as np

from printing_company.problem.spec import (
    FinishingMachine,
    Portfolio,
    PrintingMachine,
)
from simplex import Constraint, Problem


def build_problem(
    *,
    portfolio: Portfolio,
    printers: Sequence[PrintingMachine],
    finishings: Sequence[FinishingMachine],
) -> Problem:
    """Formulação (relaxada) do tempo de impressão do artigo."""

    printer_names = [printer.id for printer in printers]
    finishing_names = [finishing.id for finishing in finishings]
    names = tuple([*printer_names, *finishing_names])

    printer_costs = [1.0 / printer.speed for printer in printers]
    finishing_costs = [1.0 / finishing.speed for finishing in finishings]
    c = np.array([*printer_costs, *finishing_costs], dtype=np.float64)

    printer_constraint = Constraint(
        coefs=np.ones_like(c),
        sense=">=",
        rhs=portfolio.total,
    )
    finishing_constraint = Constraint(
        coefs=np.hstack(
            (
                np.zeros_like(printer_costs),
                np.ones_like(finishing_costs),
            )
        ),
        sense=">=",
        rhs=portfolio.with_finishing,
    )

    return Problem(
        sense="min",
        c=c,
        constraints=(
            printer_constraint,
            finishing_constraint,
        ),
        names=names,
    )
