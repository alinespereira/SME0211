"""Implementação própria do método simplex, seguindo as aulas de SME0211.

.. include:: ../../docs/modulos/simplex.md
"""

import logging

from . import display, logs, problem, solver, tableau
from .logs import Handler, configure_logging
from .problem import (
    Constraint,
    ConstraintSense,
    ObjectiveSense,
    Problem,
    Solution,
    StandardForm,
)
from .solver import (
    PivotingRule,
    Result,
    Solver,
    Status,
)
from .tableau import Tableau

__all__ = [
    "Constraint",
    "ConstraintSense",
    "Handler",
    "ObjectiveSense",
    "PivotingRule",
    "Problem",
    "Result",
    "Solution",
    "Solver",
    "StandardForm",
    "Status",
    "Tableau",
    "configure_logging",
    "display",
    "logs",
    "problem",
    "solver",
    "tableau",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[Handler(rich_tracebacks=True, markup=True)],
)


def main() -> None:
    """Ponto de entrada do comando `simplex` (ainda não implementado)."""
    raise NotImplementedError


if __name__ == "__main__":
    main()
