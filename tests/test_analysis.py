"""Testes de `printing_company.problem.analysis`: tempo real, energia e
custo."""

import pytest

from printing_company.problem import data
from printing_company.problem.analysis import (
    MachineResult,
    energy_consumption,
    energy_cost,
    operating_times,
    solve_portfolio,
)
from printing_company.problem.model import build_problem
from printing_company.problem.spec import PrintingMachine
from printing_company.settings import settings
from simplex import Status

MACHINES = [
    PrintingMachine(id="Print01", speed=10_500, setup=0.25, consumption=40),
    PrintingMachine(id="Print02", speed=3_000, setup=0.5, consumption=112),
]


def test_operating_times_adds_setup_only_when_on() -> None:
    times = operating_times(
        hours={"Print01": 20.0, "Print02": 0.0}, machines=MACHINES
    )
    assert times == {"Print01": 20.25, "Print02": 0.0}


def test_operating_times_rejects_negative_hours() -> None:
    with pytest.raises(ValueError, match="Horas negativas para Print01"):
        operating_times(hours={"Print01": -1.0}, machines=MACHINES)


def test_energy_consumption() -> None:
    energy = energy_consumption(
        times={"Print01": 20.25, "Print02": 0.0}, machines=MACHINES
    )
    assert energy == {"Print01": 810.0, "Print02": 0.0}


def test_energy_cost() -> None:
    assert round(energy_cost(energy={"Print01": 810.0}), 2) == 696.6
    assert energy_cost(energy={"Print01": 810.0}, price=1.0) == 810.0


def test_article_two_shifts() -> None:
    """A carteira I do artigo com dois turnos, passo a passo."""
    machines = [*data.printers, *data.finishers]
    problem = build_problem(
        portfolio=data.portfolios[0],
        printers=data.printers,
        finishings=data.finishers,
        capacity=2 * settings.shift_hours,
    )
    x = problem.solve().x
    assert x is not None
    hours = dict(zip(problem.variable_names, x.tolist(), strict=True))
    times = operating_times(hours=hours, machines=machines)
    assert {name: round(t, 2) for name, t in times.items() if t > 0} == {
        "Print01": 20.25,
        "Print04": 20.17,
        "Print05": 9.25,
        "Finish02": 19.5,
    }
    energy = energy_consumption(times=times, machines=machines)
    assert {name: round(e, 2) for name, e in energy.items() if e > 0} == {
        "Print01": 810.0,
        "Print04": 484.08,
        "Print05": 20.35,
        "Finish02": 2184.0,
    }
    assert round(sum(energy.values()), 2) == 3498.43
    assert round(energy_cost(energy=energy), 2) == 3008.65


def test_machine_result() -> None:
    r = MachineResult(
        machine=MACHINES[0],
        hours=20.0,
        time=20.25,
        energy=810.0,
    )
    assert r.is_on
    assert r.produced == 210_000.0


def test_solve_portfolio() -> None:
    """A carteira I do artigo precisa de 2 turnos (20 h)."""
    result = solve_portfolio(
        portfolio=data.portfolios[0],
        printers=data.printers,
        finishings=data.finishers,
    )
    assert (result.shifts, result.capacity) == (2, 20.0)
    assert result.status == Status.OPTIMAL
    assert [r.machine.id for r in result.machines if r.is_on] == [
        "Print01",
        "Print04",
        "Print05",
        "Finish02",
    ]
    assert result.objective_value is not None
    assert round(result.objective_value, 2) == 67.75
    assert round(result.total_time, 2) == 69.17
    assert round(result.total_energy, 2) == 3498.43
    assert round(result.cost, 2) == 3008.65
