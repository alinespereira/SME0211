"""Testes do comando `printing-company` e do log do tableau no solver."""

# O Tableau aceita listas em A, b e c (o pydantic converte para arrays),
# mas o pyright só vê o tipo declarado (np.ndarray) e reclamaria aqui.
# pyright: reportArgumentType=false

import logging
from collections.abc import Iterator

import pytest
from click.testing import CliRunner

from printing_company import main
from simplex.logs import PHASE_ONE_LOGGER, RICH_TEXT
from simplex.solver import Solver
from simplex.tableau import Tableau


@pytest.fixture
def _restore_root_level() -> Iterator[None]:
    """O comando muda o nível do logger raiz e o da Fase 1; volta aos
    níveis anteriores."""
    loggers = [logging.getLogger(), logging.getLogger(PHASE_ONE_LOGGER)]
    levels = [log.level for log in loggers]
    yield
    for log, level in zip(loggers, levels, strict=True):
        log.setLevel(level)


@pytest.mark.usefixtures("_restore_root_level")
@pytest.mark.parametrize(
    ("args", "level"),
    [([], logging.INFO), (["--debug"], logging.DEBUG)],
)
def test_main_sets_log_level(args: list[str], level: int) -> None:
    result = CliRunner().invoke(main, args)
    assert result.exit_code == 0, result.output
    assert logging.getLogger().level == level


@pytest.mark.usefixtures("_restore_root_level")
@pytest.mark.parametrize(
    ("args", "labels"),
    [
        ([], ["Portfolio I", "Portfolio II", "Portfolio III"]),
        (["--portfolio", "2"], ["Portfolio II"]),
        (["-p", "3", "-p", "1", "-p", "3"], ["Portfolio I", "Portfolio III"]),
    ],
)
def test_main_portfolio_option(
    caplog: pytest.LogCaptureFixture, args: list[str], labels: list[str]
) -> None:
    with caplog.at_level(logging.INFO, logger="printing_company"):
        result = CliRunner().invoke(main, args)
    assert result.exit_code == 0, result.output
    solved = [
        r.getMessage().removeprefix(">>> ").split(":")[0]
        for r in caplog.records
        if r.getMessage().startswith(">>> ")
    ]
    assert solved == labels


def test_main_rejects_unknown_portfolio() -> None:
    result = CliRunner().invoke(main, ["--portfolio", "4"])
    assert result.exit_code != 0


@pytest.mark.usefixtures("_restore_root_level")
@pytest.mark.parametrize(
    ("args", "shows_phase_one"),
    [(["--debug"], False), (["--debug", "--phase-one"], True)],
)
def test_main_phase_one_hidden_unless_asked(
    caplog: pytest.LogCaptureFixture, args: list[str], shows_phase_one: bool
) -> None:
    """Com --debug, só a Fase 2 mostra tableaux; --phase-one inclui a
    Fase 1."""
    with caplog.at_level(logging.DEBUG):
        result = CliRunner().invoke(main, [*args, "-p", "1"])
    assert result.exit_code == 0, result.output
    names = {r.name for r in caplog.records if hasattr(r, RICH_TEXT)}
    assert "simplex.solver" in names
    assert (PHASE_ONE_LOGGER in names) == shows_phase_one


def test_main_help_mentions_debug() -> None:
    result = CliRunner().invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "--debug" in result.output


def test_solver_logs_highlighted_tableau(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Cada iteração registra o tableau com quem entra, quem sai e o pivô;
    a versão colorida vai no atributo `RICH_TEXT` do registro."""
    tableau = Tableau(
        A=[[1, 1, 1, 0], [1, 3, 0, 1]],
        b=[4, 6],
        c=[-1, -2, 0, 0],
        basis=(2, 3),
        names=("x1", "x2", "s1", "s2"),
    )
    with caplog.at_level(logging.DEBUG, logger="simplex.solver"):
        Solver().solve(tableau=tableau)
    messages = [r.getMessage() for r in caplog.records]
    assert messages[0].startswith(
        "Iteração 0: entra x1 (↓), sai s1 (→), pivô [1]"
    )
    assert "→ s1" in messages[0]
    assert "[1]" in messages[0]
    assert messages[-1].startswith("Iteração 2: solução ótima")
    assert all(hasattr(r, RICH_TEXT) for r in caplog.records)


def test_solver_skips_rendering_without_debug(
    caplog: pytest.LogCaptureFixture,
) -> None:
    tableau = Tableau(A=[[1, 1]], b=[2], c=[1, 0], basis=(0,))
    with caplog.at_level(logging.INFO, logger="simplex.solver"):
        Solver().solve(tableau=tableau)
    assert caplog.records == []


@pytest.mark.usefixtures("_restore_root_level")
@pytest.mark.parametrize(
    ("args", "label"),
    [
        ([], "tempo"),
        (["--objective", "time"], "tempo"),
        (["--objective", "energy"], "energia"),
        (["-o", "ENERGY"], "energia"),
    ],
)
def test_main_objective_option(
    caplog: pytest.LogCaptureFixture, args: list[str], label: str
) -> None:
    with caplog.at_level(logging.INFO, logger="printing_company"):
        result = CliRunner().invoke(main, [*args, "-p", "1"])
    assert result.exit_code == 0, result.output
    headers = [
        r.getMessage()
        for r in caplog.records
        if r.getMessage().startswith(">>> ")
    ]
    assert headers == [f">>> Portfolio I: 2 turnos, objetivo: {label}"]


@pytest.mark.usefixtures("_restore_root_level")
def test_main_energy_objective_uses_less_energy(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Minimizar a energia gasta menos kWh que minimizar o tempo."""

    def energy(objective: str) -> float:
        caplog.clear()
        with caplog.at_level(logging.INFO, logger="printing_company"):
            result = CliRunner().invoke(main, ["-o", objective, "-p", "1"])
        assert result.exit_code == 0, result.output
        (summary,) = (
            r.getMessage()
            for r in caplog.records
            if r.getMessage().startswith("Tempo real")
        )
        return float(summary.split("energia: ")[1].split(" kWh")[0])

    assert energy("energy") < energy("time")


def test_main_rejects_unknown_objective() -> None:
    result = CliRunner().invoke(main, ["--objective", "cost"])
    assert result.exit_code != 0
