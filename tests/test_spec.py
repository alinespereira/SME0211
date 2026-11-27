"""Testes de `printing_company.problem.spec` e das instâncias do artigo."""

import pytest
from pydantic import ValidationError

from printing_company.problem import data
from printing_company.problem.spec import (
    Demand,
    FinishingMachine,
    Machine,
    Portfolio,
    PrintingMachine,
)


def test_machine_is_abstract() -> None:
    with pytest.raises(TypeError, match="Base é abstrata"):
        Machine(id="M1", speed=200, setup=30, consumption=50)


def test_machine_numbers_must_be_positive() -> None:
    with pytest.raises(ValidationError, match="greater than 0"):
        PrintingMachine(id="P1", speed=0, setup=30, consumption=50)


def test_printing_machine() -> None:
    p = PrintingMachine(id="Print01", speed=10_500, setup=0.25, consumption=40)
    assert repr(p) == (
        "PrintingMachine(id='Print01', speed=10500.0, setup=0.25, "
        "consumption=40.0)"
    )
    # Horas para 15 000 m, com setup.
    assert round(p.setup + 15_000 / p.speed, 4) == 1.6786
    with pytest.raises(ValidationError, match="frozen"):
        p.speed = 300  # type: ignore[misc]


def test_finishing_machine() -> None:
    f = FinishingMachine(id="Finish01", speed=7_800, setup=0.5, consumption=40)
    assert f.setup == 0.5
    assert isinstance(f, Machine)


def test_demand() -> None:
    d = Demand(label="formulários", quantity=1500, requires_finishing=True)
    assert d.quantity == 1500.0
    assert not Demand(label="notas fiscais", quantity=800).requires_finishing


def test_portfolio_totals() -> None:
    portfolio = Portfolio(
        label="Escritório",
        demands=[
            Demand(label="notas fiscais", quantity=800),
            Demand(label="formulários", quantity=1500, requires_finishing=True),
            Demand(label="boletos", quantity=1200, requires_finishing=True),
        ],
    )
    assert portfolio.total == 3500.0
    assert portfolio.with_finishing == 2700.0
    assert portfolio.without_finishing == 800.0
    assert portfolio.model_dump()["with_finishing"] == 2700.0


def test_article_instances() -> None:
    assert [p.id for p in data.printers] == [
        "Print01",
        "Print02",
        "Print03",
        "Print04",
        "Print05",
    ]
    assert len(data.finishers) == 3
    assert [len(p.demands) for p in data.portfolios] == [10, 20, 50]
    assert data.portfolios[1].label == "Portfolio II"
    assert data.portfolios[1].with_finishing == 543_000.0
    assert data.portfolios[1].without_finishing == 620_000.0
