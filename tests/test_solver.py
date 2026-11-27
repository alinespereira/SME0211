"""Testes da classe Solver.

Os testes cobrem cada passo do método separadamente e depois o método
completo (`solve`). Os índices seguem o código: linhas e variáveis começam
em 0.
"""

# O Tableau aceita listas em A, b e c (o pydantic converte para arrays),
# mas o pyright só vê o tipo declarado (np.ndarray) e reclamaria aqui.
# pyright: reportArgumentType=false

import numpy as np
import pytest

from simplex.solver import PivotingRule, Solver, Status
from simplex.tableau import Tableau

RULES = list(PivotingRule)


@pytest.fixture(params=RULES, ids=[rule.value for rule in RULES])
def solver(request: pytest.FixtureRequest) -> Solver:
    """Um solver para cada regra: testes que o usam rodam duas vezes."""
    return Solver(rule=request.param)


bland = Solver(rule=PivotingRule.BLAND)
lexicographic = Solver(rule=PivotingRule.LEXICOGRAPHIC)


# ----------------------------------------------------------------------
# Passo 1: otimalidade
# ----------------------------------------------------------------------


def test_is_optimal_false_with_negative_reduced_cost(
    solver: Solver, small: Tableau
) -> None:
    assert not solver.is_optimal(tableau=small)


def test_is_optimal_true_at_optimum(solver: Solver, small: Tableau) -> None:
    """Na base ótima, os custos reduzidos são (0, 0, 1/2, 1/2): os zeros
    das variáveis básicas não podem impedir a otimalidade."""
    assert solver.is_optimal(tableau=small.with_basis(basis=(0, 1)))


def test_is_optimal_ignores_tiny_negative_reduced_costs(solver: Solver) -> None:
    """Um custo reduzido de -1e-12 é zero a menos de erro de arredondamento."""
    t = Tableau(A=[[1, 1]], b=[1], c=[-1e-12, 0], basis=(1,))
    assert solver.is_optimal(tableau=t)


# ----------------------------------------------------------------------
# Passo 2: variável que entra
# ----------------------------------------------------------------------


def test_entering_bland_is_smallest_negative_index(small: Tableau) -> None:
    """Custos reduzidos (-1, -2, 0, 0): Bland escolhe j = 0, e não o mais
    negativo."""
    assert bland.entering_variable(tableau=small) == 0


def test_entering_bland_skips_basic_variables() -> None:
    """Custos reduzidos (0, 0, -1): as básicas (0 e 1) têm custo reduzido
    zero e não podem entrar."""
    t = Tableau(A=[[1, 0, 1], [0, 1, 1]], b=[1, 1], c=[0, 0, -1], basis=(0, 1))
    assert bland.entering_variable(tableau=t) == 2


def test_entering_lexicographic_has_negative_reduced_cost(
    small: Tableau,
) -> None:
    j = lexicographic.entering_variable(tableau=small)
    assert small.reduced_costs[j] < 0


def test_entering_variable_returns_int(solver: Solver, small: Tableau) -> None:
    assert isinstance(solver.entering_variable(tableau=small), int)


# ----------------------------------------------------------------------
# Passo 4: variável que sai
# ----------------------------------------------------------------------


def test_leaving_row_minimum_ratio(solver: Solver, small: Tableau) -> None:
    """x1 entra (u = (1, 1)): razões 4/1 e 6/1, sai a linha 0."""
    u = small.column(j=0)
    assert solver.leaving_row(tableau=small, u=u) == 0


def test_leaving_row_ignores_nonpositive_entries(solver: Solver) -> None:
    """u = (-1, 2, 0): só a linha 1 é candidata, mesmo que as razões das
    outras sejam menores ou indefinidas."""
    t = Tableau(
        A=[[1, 0, 0, -1], [0, 1, 0, 2], [0, 0, 1, 0]],
        b=[0, 6, 1],
        c=[0, 0, 0, -1],
        basis=(0, 1, 2),
    )
    u = t.column(j=3)
    assert solver.leaving_row(tableau=t, u=u) == 1


def test_leaving_row_unbounded_returns_none(
    solver: Solver, unbounded: Tableau
) -> None:
    """x2 entra com u = (-1) <= 0: não há quem saia."""
    u = unbounded.column(j=1)
    assert solver.leaving_row(tableau=unbounded, u=u) is None


def test_leaving_bland_tie_smallest_basic_index(aula21: Tableau) -> None:
    """Empate entre as linhas 0 e 2 (razão 1/3). Com basis = (3, 4, 5),
    B(0) = 3 < B(2) = 5: sai a linha 0."""
    u = aula21.column(j=2)
    np.testing.assert_allclose(u, [3, -1, 9])
    assert bland.leaving_row(tableau=aula21, u=u) == 0


def test_leaving_bland_tie_uses_variable_index_not_row(
    aula21_reversed: Tableau,
) -> None:
    """Mesmo empate, mas com basis = (5, 4, 3): agora B(2) = 3 é o menor
    índice de variável, então sai a linha 2."""
    u = aula21_reversed.column(j=2)
    assert bland.leaving_row(tableau=aula21_reversed, u=u) == 2


def test_leaving_lexicographic_aula21(aula21: Tableau) -> None:
    """Exemplo da aula 21: dividindo as linhas 0 e 2 por 3 e por 9, o
    empate é desfeito na terceira coluna (7/9 < 5/3), e sai a linha 2."""
    u = aula21.column(j=2)
    assert lexicographic.leaving_row(tableau=aula21, u=u) == 2


def test_leaving_row_returns_int(solver: Solver, small: Tableau) -> None:
    ell = solver.leaving_row(tableau=small, u=small.column(j=0))
    assert isinstance(ell, int)


# ----------------------------------------------------------------------
# Passo 5: troca de base
# ----------------------------------------------------------------------


def test_change_basis(solver: Solver, small: Tableau) -> None:
    new = solver.change_basis(tableau=small, j=1, ell=1)
    assert new.basis == (2, 1)
    np.testing.assert_allclose(new.solution, [0, 2, 2, 0])
    assert small.basis == (2, 3), "o tableau original não pode mudar"


# ----------------------------------------------------------------------
# Método completo
# ----------------------------------------------------------------------


def test_solve_small(solver: Solver, small: Tableau) -> None:
    result = solver.solve(tableau=small)
    assert result.status == Status.OPTIMAL
    assert result.tableau.objective_value == pytest.approx(-5)
    np.testing.assert_allclose(result.tableau.solution, [3, 1, 0, 0])
    assert sorted(result.tableau.basis) == [0, 1]
    assert result.iterations > 0


def test_solve_already_optimal(solver: Solver, small: Tableau) -> None:
    result = solver.solve(tableau=small.with_basis(basis=(0, 1)))
    assert result.status == Status.OPTIMAL
    assert result.iterations == 0


def test_solve_unbounded(solver: Solver, unbounded: Tableau) -> None:
    result = solver.solve(tableau=unbounded)
    assert result.status == Status.UNBOUNDED


def test_solve_beale_does_not_cycle(solver: Solver, beale: Tableau) -> None:
    """O exemplo de Beale cicla com a regra do maior custo reduzido; com
    Bland ou com a regra lexicográfica o método termina no ótimo."""
    result = solver.solve(tableau=beale)
    assert result.status == Status.OPTIMAL
    assert result.tableau.objective_value == pytest.approx(-5 / 4)
    np.testing.assert_allclose(
        result.tableau.solution, [3 / 4, 0, 0, 1, 0, 1, 0], atol=1e-9
    )
    assert result.iterations < 20


def test_solve_iteration_limit(small: Tableau) -> None:
    """Partindo das folgas, o exemplo pequeno precisa de mais de uma troca
    de base."""
    result = Solver(rule=PivotingRule.BLAND, max_iterations=1).solve(
        tableau=small
    )
    assert result.status == Status.ITERATION_LIMIT
    assert result.iterations == 1


def test_solve_does_not_change_input(solver: Solver, small: Tableau) -> None:
    solver.solve(tableau=small)
    assert small.basis == (2, 3)


def test_solver_is_frozen() -> None:
    with pytest.raises(ValueError, match="frozen"):
        bland.rule = PivotingRule.LEXICOGRAPHIC  # type: ignore[misc]
