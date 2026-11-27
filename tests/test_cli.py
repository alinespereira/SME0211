"""Testes do comando `printing-company` e do log do tableau no solver."""

# O Tableau aceita listas em A, b e c (o pydantic converte para arrays),
# mas o pyright só vê o tipo declarado (np.ndarray) e reclamaria aqui.
# pyright: reportArgumentType=false

import logging
import re
from collections.abc import Iterator

import pytest
from click.testing import CliRunner

from printing_company import main
from printing_company.settings import Settings
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


def _titles(output: str) -> list[tuple[str, str]]:
    """As carteiras e os objetivos dos títulos da saída do comando."""
    return re.findall(r"(Portfolio [IV]+) · objetivo: (\w+)", output)


def _br_number(text: str) -> float:
    """Converte um número no padrão brasileiro (`3.498,43`) em float."""
    return float(text.replace(".", "").replace(",", "."))


def _totals(output: str) -> tuple[float, ...]:
    """O ótimo do modelo, o tempo real, a energia e o custo da tabela de
    totais (a única linha com uma unidade na primeira coluna)."""
    (row,) = re.findall(
        r"│ +([\d.,]+) (?:h|kWh) │ +([\d.,]+) │ +([\d.,]+) │ +([\d.,]+) │",
        output,
    )
    return tuple(_br_number(value) for value in row)


@pytest.mark.usefixtures("_restore_root_level")
@pytest.mark.parametrize(
    ("args", "labels"),
    [
        ([], ["Portfolio I", "Portfolio II", "Portfolio III"]),
        (["--portfolio", "2"], ["Portfolio II"]),
        (["-p", "3", "-p", "1", "-p", "3"], ["Portfolio I", "Portfolio III"]),
    ],
)
def test_main_portfolio_option(args: list[str], labels: list[str]) -> None:
    result = CliRunner().invoke(main, args)
    assert result.exit_code == 0, result.output
    assert [label for label, _ in _titles(result.output)] == labels


@pytest.mark.usefixtures("_restore_root_level")
@pytest.mark.parametrize(
    ("args", "has_summary"),
    [(["-p", "1"], False), (["-p", "1", "-p", "2"], True)],
)
def test_main_summary_only_with_many_portfolios(
    args: list[str], has_summary: bool
) -> None:
    result = CliRunner().invoke(main, args)
    assert result.exit_code == 0, result.output
    assert ("Resumo · objetivo: tempo" in result.output) == has_summary


@pytest.mark.usefixtures("_restore_root_level")
def test_main_shows_machine_table() -> None:
    """A tabela tem uma linha por máquina e o resumo da carteira."""
    result = CliRunner().invoke(main, ["-p", "1"])
    assert result.exit_code == 0, result.output
    for machine in ("Print01", "Print05", "Finish01", "Finish02"):
        assert machine in result.output
    assert _totals(result.output) == (67.75, 69.17, 3498.43, 3008.65)
    assert "Horizonte: 2 turnos de 10 h, T = 20 h" in result.output


@pytest.mark.usefixtures("_restore_root_level")
def test_main_uses_shift_hours_from_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """As horas do turno vêm de `settings` (que lê `SHIFT_HOURS` na
    importação; aqui o objeto é trocado diretamente)."""
    monkeypatch.setattr(
        "printing_company.problem.analysis.settings",
        Settings(shift_hours=8),
    )
    result = CliRunner().invoke(main, ["-p", "1"])
    assert result.exit_code == 0, result.output
    assert "Horizonte: 2 turnos de 8 h, T = 16 h" in result.output


@pytest.mark.usefixtures("_restore_root_level")
def test_main_debug_logs_model(caplog: pytest.LogCaptureFixture) -> None:
    """Com --debug, o modelo de cada carteira vai para o log, antes dos
    tableaux."""
    with caplog.at_level(logging.DEBUG):
        result = CliRunner().invoke(main, ["--debug", "-p", "1"])
    assert result.exit_code == 0, result.output
    names = [r.name for r in caplog.records if hasattr(r, RICH_TEXT)]
    assert names[0] == "printing_company.problem.analysis"
    assert (
        caplog.records[0]
        .getMessage()
        .startswith("Modelo da Portfolio I (T = 20 h, objetivo: tempo)")
    )


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
def test_main_objective_option(args: list[str], label: str) -> None:
    result = CliRunner().invoke(main, [*args, "-p", "1"])
    assert result.exit_code == 0, result.output
    assert _titles(result.output) == [("Portfolio I", label)]


@pytest.mark.usefixtures("_restore_root_level")
def test_main_energy_objective_uses_less_energy() -> None:
    """Minimizar a energia gasta menos kWh que minimizar o tempo."""

    def energy(objective: str) -> float:
        result = CliRunner().invoke(main, ["-o", objective, "-p", "1"])
        assert result.exit_code == 0, result.output
        return _totals(result.output)[2]

    assert energy("energy") < energy("time")


@pytest.mark.usefixtures("_restore_root_level")
def test_main_runs_every_objective() -> None:
    """Com `-o` repetido, cada carteira é resolvida com cada objetivo, na
    ordem tempo, energia, e o resumo ganha a coluna `objetivo`."""
    result = CliRunner().invoke(
        main, ["-o", "energy", "-o", "time", "-o", "energy"]
    )
    assert result.exit_code == 0, result.output
    assert _titles(result.output) == [
        (label, objective)
        for label in ("Portfolio I", "Portfolio II", "Portfolio III")
        for objective in ("tempo", "energia")
    ]
    assert re.search(r"┃ Carteira +┃ objetivo +┃", result.output)
    assert re.search(r"│ Portfolio III +│ energia +│", result.output)


def test_main_rejects_unknown_objective() -> None:
    result = CliRunner().invoke(main, ["--objective", "cost"])
    assert result.exit_code != 0
