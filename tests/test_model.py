"""Testes de `printing_company.problem.model`: o modelo relaxado."""

import math

import pytest

from printing_company.problem import data
from printing_company.problem.model import (
    Objective,
    build_problem,
    min_capacity,
)
from printing_company.problem.spec import (
    Demand,
    FinishingMachine,
    Portfolio,
    PrintingMachine,
)
from printing_company.settings import settings
from simplex import Problem, Status

# Duas impressoras, uma máquina de acabamento e dois itens, dos quais só o
# primeiro precisa de acabamento.
PORTFOLIO = Portfolio(
    label="Exemplo",
    demands=[
        Demand(label="D01", quantity=15_000, requires_finishing=True),
        Demand(label="D02", quantity=20_000),
    ],
)
PRINTERS = [
    PrintingMachine(id="P1", speed=10_500, setup=0.25, consumption=40),
    PrintingMachine(id="P2", speed=3_000, setup=0.5, consumption=112),
]
FINISHINGS = [
    FinishingMachine(id="F1", speed=7_800, setup=0.5, consumption=40),
]


def small(
    *, capacity: float | None = None, objective: Objective = Objective.TIME
) -> Problem:
    return build_problem(
        portfolio=PORTFOLIO,
        printers=PRINTERS,
        finishings=FINISHINGS,
        capacity=capacity,
        objective=objective,
    )


def article(
    *, capacity: float | None = None, objective: Objective = Objective.TIME
) -> Problem:
    """A carteira I do artigo."""
    return build_problem(
        portfolio=data.portfolios[0],
        printers=data.printers,
        finishings=data.finishers,
        capacity=capacity,
        objective=objective,
    )


def hours_on(problem: Problem) -> dict[str, float]:
    """As horas das máquinas ligadas na solução ótima, com 4 casas."""
    solution = problem.solve()
    assert solution.x is not None
    return {
        name: round(t, 4)
        for name, t in zip(
            problem.variable_names, solution.x.tolist(), strict=True
        )
        if t > 0
    }


def objective(problem: Problem) -> float:
    value = problem.solve().objective
    assert value is not None
    return value


def test_objective() -> None:
    assert Objective("energy") is Objective.ENERGY
    assert [str(o) for o in Objective] == ["time", "energy"]
    assert (Objective.ENERGY.label, Objective.ENERGY.unit) == ("energia", "kWh")
    assert (Objective.TIME.label, Objective.TIME.unit) == ("tempo", "h")


def test_build_problem_without_capacity() -> None:
    problem = small()
    assert problem.variable_names == ("P1", "P2", "F1")
    assert problem.c.tolist() == [1.0, 1.0, 1.0]
    # Velocidades em mil m/h e demandas em mil m.
    assert [k.coefs.tolist() for k in problem.constraints] == [
        [10.5, 3.0, 0.0],
        [0.0, 0.0, 7.8],
    ]
    assert [k.rhs for k in problem.constraints] == [35.0, 15.0]
    # 35 000 m na impressora mais rápida e 15 000 m na única de acabamento.
    assert hours_on(problem) == {"P1": 3.3333, "F1": 1.9231}
    assert round(objective(problem), 4) == 5.2564


def test_build_problem_with_capacity() -> None:
    """Com 3 horas, a P1 imprime 31 500 m e a P2, o resto."""
    problem = small(capacity=3)
    assert [k.sense for k in problem.constraints] == [
        ">=",
        ">=",
        "<=",
        "<=",
        "<=",
    ]
    assert hours_on(problem) == {"P1": 3.0, "P2": 1.1667, "F1": 1.9231}


def test_build_problem_infeasible() -> None:
    """Com 2 horas, as impressoras só dão conta de 27 000 m."""
    assert small(capacity=2).solve().status == Status.INFEASIBLE


def test_build_problem_capacity_must_be_positive() -> None:
    with pytest.raises(ValueError, match="capacity deve ser positiva"):
        small(capacity=0)


def test_article_without_capacity() -> None:
    problem = article()
    assert hours_on(problem) == {"Print04": 43.0952, "Finish02": 18.75}
    assert round(objective(problem), 4) == 61.8452


def test_article_two_shifts() -> None:
    problem = article(capacity=2 * settings.shift_hours)
    assert hours_on(problem) == {
        "Print01": 20.0,
        "Print04": 20.0,
        "Print05": 9.0,
        "Finish02": 18.75,
    }
    assert round(objective(problem), 4) == 67.75


def test_energy_small() -> None:
    """A P1 gasta menos energia por metro, então a impressão fica nela."""
    problem = small(objective=Objective.ENERGY)
    assert problem.c.tolist() == [40.0, 112.0, 40.0]  # kW
    assert hours_on(problem) == {"P1": 3.3333, "F1": 1.9231}
    assert round(objective(problem), 2) == 210.26  # kWh


def test_energy_article_two_shifts() -> None:
    problem = article(
        capacity=2 * settings.shift_hours, objective=Objective.ENERGY
    )
    assert hours_on(problem) == {
        "Print01": 10.5714,
        "Print04": 20.0,
        "Print05": 20.0,
        "Finish01": 1.1538,
        "Finish03": 20.0,
    }
    solution = problem.solve()
    assert solution.x is not None and solution.objective is not None
    assert round(solution.objective, 2) == 1993.01  # kWh
    assert round(float(solution.x.sum()), 2) == 71.73  # horas


def test_min_capacity() -> None:
    capacities = [
        round(
            min_capacity(
                portfolio=portfolio,
                printers=data.printers,
                finishings=data.finishers,
            ),
            2,
        )
        for portfolio in data.portfolios
    ]
    assert capacities == [12.66, 27.11, 60.85]
    # Turnos diários para a carteira I.
    assert math.ceil(12.66 / settings.shift_hours) == 2
