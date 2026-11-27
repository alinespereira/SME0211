"""Testes do comando `printing-company` e do log do tableau no solver."""

# O Tableau aceita listas em A, b e c (o pydantic converte para arrays),
# mas o pyright só vê o tipo declarado (np.ndarray) e reclamaria aqui.
# pyright: reportArgumentType=false

import logging
from collections.abc import Iterator

import pytest
from click.testing import CliRunner

from printing_company import main
from simplex.logs import RICH_TEXT
from simplex.solver import Solver
from simplex.tableau import Tableau


@pytest.fixture
def _restore_root_level() -> Iterator[None]:
    """O comando muda o nível do logger raiz; volta ao nível anterior."""
    root = logging.getLogger()
    level = root.level
    yield
    root.setLevel(level)


@pytest.mark.usefixtures("_restore_root_level")
@pytest.mark.parametrize(
    ("args", "level"),
    [([], logging.INFO), (["--debug"], logging.DEBUG)],
)
def test_main_sets_log_level(args: list[str], level: int) -> None:
    result = CliRunner().invoke(main, args)
    assert result.exit_code == 0, result.output
    assert logging.getLogger().level == level


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
