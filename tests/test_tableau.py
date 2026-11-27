"""Testes da classe Tableau."""

# O Tableau aceita listas em A, b e c (o pydantic converte para arrays),
# mas o pyright só vê o tipo declarado (np.ndarray) e reclamaria aqui.
# pyright: reportArgumentType=false

import numpy as np
import pytest
from pydantic import ValidationError

from simplex.tableau import Tableau

A_SMALL = [[1, 1, 1, 0], [1, 3, 0, 1]]
B_SMALL = [4, 6]
C_SMALL = [-1, -2, 0, 0]


# ----------------------------------------------------------------------
# Construção e validação
# ----------------------------------------------------------------------


def test_converts_lists_to_float_arrays(small: Tableau) -> None:
    assert small.A.dtype == np.float64
    assert small.b.dtype == np.float64
    assert small.c.dtype == np.float64
    assert small.A.shape == (2, 4)


def test_accepts_list_as_basis() -> None:
    t = Tableau(A=A_SMALL, b=B_SMALL, c=C_SMALL, basis=[2, 3])
    assert t.basis == (2, 3)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"A": [1, 2, 3, 4]}, "matriz"),
        ({"b": [4, 6, 8]}, "b deve ter"),
        ({"c": [1, 2]}, "c deve ter"),
        ({"basis": (2,)}, "A base deve ter"),
        ({"basis": (2, 2)}, "repetidos"),
        ({"basis": (2, 7)}, "entre 0 e"),
        ({"basis": (0, 2)}, "não é viável"),
    ],
)
def test_rejects_invalid_data(kwargs: dict[str, object], message: str) -> None:
    data: dict[str, object] = {
        "A": A_SMALL,
        "b": B_SMALL,
        "c": C_SMALL,
        "basis": (2, 3),
    }
    data |= kwargs
    with pytest.raises(ValidationError, match=message):
        Tableau.model_validate(data)


def test_rejects_singular_basis() -> None:
    with pytest.raises(ValidationError, match="não é inversível"):
        Tableau(A=[[1, 2, 1], [2, 4, 0]], b=[1, 2], c=[0, 0, 0], basis=(0, 1))


# ----------------------------------------------------------------------
# Imutabilidade
# ----------------------------------------------------------------------


def test_is_frozen(small: Tableau) -> None:
    with pytest.raises(ValidationError):
        small.basis = (0, 1)  # type: ignore[misc]


def test_arrays_are_read_only(small: Tableau) -> None:
    with pytest.raises(ValueError, match="read-only"):
        small.A[0, 0] = 10
    with pytest.raises(ValueError, match="read-only"):
        small.b[0] = 10
    with pytest.raises(ValueError, match="read-only"):
        small.c[0] = 10


def test_copies_input_arrays() -> None:
    a = np.array(A_SMALL, dtype=float)
    t = Tableau(A=a, b=B_SMALL, c=C_SMALL, basis=(2, 3))
    a[0, 0] = 99
    assert t.A[0, 0] == 1


def test_with_basis_returns_new_tableau(small: Tableau) -> None:
    new = small.with_basis(basis=[0, 1])
    assert new.basis == (0, 1)
    assert small.basis == (2, 3)
    np.testing.assert_array_equal(new.A, small.A)


def test_with_basis_validates(small: Tableau) -> None:
    with pytest.raises(ValidationError, match="não é viável"):
        small.with_basis(basis=(0, 2))


# ----------------------------------------------------------------------
# Grandezas derivadas
# ----------------------------------------------------------------------


def test_dimensions_and_non_basis(small: Tableau) -> None:
    assert small.num_constraints == 2
    assert small.num_variables == 4
    assert small.non_basis == (0, 1)


def test_slack_basis(small: Tableau) -> None:
    np.testing.assert_allclose(small.B, np.eye(2))
    np.testing.assert_allclose(small.basic_solution, [4, 6])
    np.testing.assert_allclose(small.multipliers, [0, 0])
    np.testing.assert_allclose(small.reduced_costs, [-1, -2, 0, 0])
    np.testing.assert_allclose(small.solution, [0, 0, 4, 6])
    assert small.objective_value == pytest.approx(0)


def test_optimal_basis(small: Tableau) -> None:
    t = small.with_basis(basis=(0, 1))
    np.testing.assert_allclose(t.B, [[1, 1], [1, 3]])
    np.testing.assert_allclose(t.basic_solution, [3, 1])
    np.testing.assert_allclose(t.multipliers, [-0.5, -0.5])
    np.testing.assert_allclose(t.reduced_costs, [0, 0, 0.5, 0.5], atol=1e-12)
    np.testing.assert_allclose(t.solution, [3, 1, 0, 0])
    assert t.objective_value == pytest.approx(-5)


def test_basis_order_matters_only_for_rows(small: Tableau) -> None:
    t01 = small.with_basis(basis=(0, 1))
    t10 = small.with_basis(basis=(1, 0))
    np.testing.assert_allclose(t10.basic_solution, [1, 3])
    np.testing.assert_allclose(t10.solution, t01.solution)
    np.testing.assert_allclose(t10.reduced_costs, t01.reduced_costs)


def test_reduced_costs_of_basic_variables_are_zero(small: Tableau) -> None:
    for basis in [(2, 3), (0, 1), (0, 3), (1, 2)]:
        t = small.with_basis(basis=basis)
        np.testing.assert_allclose(t.reduced_costs[list(basis)], 0, atol=1e-12)


def test_column_matches_aula18() -> None:
    """Exemplo da aula 18: u = B^{-1} A_j = (-4, 2, 2)."""
    basis_matrix = np.array(
        [
            [1 / 7, 5 / 21, 1 / 3],
            [0, 2 / 3, 1 / 3],
            [2 / 7, -11 / 21, -1 / 3],
        ]
    )
    a_j = np.array([4 / 7, 2, -20 / 7])
    t = Tableau(
        A=np.column_stack([basis_matrix, a_j]),
        b=basis_matrix @ np.ones(3),
        c=np.zeros(4),
        basis=(0, 1, 2),
    )
    np.testing.assert_allclose(t.column(j=3), [-4, 2, 2])


def test_table(small: Tableau) -> None:
    np.testing.assert_allclose(
        small.table,
        [
            [0, -1, -2, 0, 0],
            [4, 1, 1, 1, 0],
            [6, 1, 3, 0, 1],
        ],
    )
    np.testing.assert_allclose(
        small.with_basis(basis=(0, 1)).table,
        [
            [5, 0, 0, 0.5, 0.5],
            [3, 1, 0, 1.5, -0.5],
            [1, 0, 1, -0.5, 0.5],
        ],
        atol=1e-12,
    )


def test_column(small: Tableau) -> None:
    np.testing.assert_allclose(small.column(j=1), [1, 3])


def test_variable_names_default() -> None:
    t = Tableau(A=[[1, 1]], b=[1], c=[0, 0], basis=(0,))
    assert t.variable_names == ("x1", "x2")
