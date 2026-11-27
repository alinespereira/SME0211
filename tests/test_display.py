"""Testes de `simplex.display`: formatação dos números e do tableau."""

import pytest

from simplex.display import format_number, render_tableau
from simplex.tableau import Tableau


@pytest.mark.parametrize(
    ("value", "text"),
    [(2 / 3, "0.6667"), (-0.0, "0"), (-2.22e-16, "0"), (1500.0, "1500")],
)
def test_format_number(value: float, text: str) -> None:
    assert format_number(value=value) == text


@pytest.fixture
def named(small: Tableau) -> Tableau:
    return small.model_copy(update={"names": ("x1", "x2", "s1", "s2")})


def test_render_tableau_highlights_pivot(named: Tableau) -> None:
    """x2 entra e a folga s2 sai, com pivô 3."""
    text = render_tableau(tableau=named, entering=1, leaving=1).plain
    assert text.splitlines() == [
        "        │ x1  x2 ↓ s1  s2",
        "────────┼─────────────────",
        "  -z 0  │ -1   -2   0   0",
        "────────┼─────────────────",
        "  s1 4  │  1    1   1   0",
        "→ s2 6  │  1   [3]  0   1",
    ]


def test_render_tableau_without_highlight(named: Tableau) -> None:
    text = render_tableau(tableau=named.with_basis(basis=(0, 1))).plain
    assert text.splitlines() == [
        "        │ x1  x2    s1    s2",
        "────────┼────────────────────",
        "  -z 5  │  0   0   0.5   0.5",
        "────────┼────────────────────",
        "  x1 3  │  1   0   1.5  -0.5",
        "  x2 1  │  0   1  -0.5   0.5",
    ]
