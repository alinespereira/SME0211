"""Testes de simplex.problem: descrição, forma padrão, Fase 1 e solve.

Os testes de validação já passam; os demais guiam a implementação de
`from_toml`, `to_standard_form`, `phase_one_tableau`, `initial_tableau`,
`original_solution`, `original_objective` e `solve`.
"""

# Problem e StandardForm aceitam listas (o pydantic converte para arrays),
# mas o pyright só vê o tipo declarado (np.ndarray) e reclamaria aqui.
# pyright: reportArgumentType=false

from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from simplex.problem import Constraint, Problem, StandardForm, _linear_terms
from simplex.solver import PivotingRule, Solver, Status

EXAMPLES = Path(__file__).parent.parent / "examples"

RULES = list(PivotingRule)


@pytest.fixture(params=RULES, ids=[rule.value for rule in RULES])
def solver(request: pytest.FixtureRequest) -> Solver:
    return Solver(rule=request.param)


def make(
    sense: str, c: list[float], *rows: tuple[list[float], str, float]
) -> Problem:
    """Atalho: make("min", c, (coefs, "<=", rhs), ...)."""
    return Problem.model_validate(
        {
            "sense": sense,
            "c": c,
            "constraints": [
                {"coefs": coefs, "sense": s, "rhs": rhs}
                for coefs, s, rhs in rows
            ],
        }
    )


@pytest.fixture
def pequeno() -> Problem:
    """O mesmo problema de examples/pequeno.toml."""
    return Problem(
        sense="max",
        c=[3, 2],
        names=("x1", "x2"),
        constraints=(
            Constraint(coefs=[1, 1], sense="<=", rhs=4),
            Constraint(coefs=[1, 3], sense="<=", rhs=6),
            Constraint(coefs=[1, 0], sense=">=", rhs=1),
        ),
    )


# ----------------------------------------------------------------------
# Validação (já implementada)
# ----------------------------------------------------------------------


def test_default_names() -> None:
    p = make("min", [1, 2, 3], ([1, 1, 1], "<=", 1))
    assert p.variable_names == ("x1", "x2", "x3")
    assert p.num_variables == 3
    assert p.num_constraints == 1


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ({"constraints": [{"coefs": [1], "sense": "<=", "rhs": 1}]}, "1 coef"),
        ({"names": ["x"]}, "names tem 1"),
        ({"names": ["x", "x"]}, "repetidos"),
        ({"constraints": []}, "at least 1"),
        ({"sense": "maximize"}, "sense"),
        ({"constraints": [{"coefs": [1, 1], "sense": "<", "rhs": 1}]}, "sense"),
    ],
)
def test_problem_validation(data: dict[str, object], message: str) -> None:
    base: dict[str, object] = {
        "c": [1, 1],
        "constraints": [{"coefs": [1, 1], "sense": "<=", "rhs": 1}],
    }
    with pytest.raises(ValidationError, match=message):
        Problem.model_validate(base | data)


def test_standard_form_requires_nonnegative_b() -> None:
    with pytest.raises(ValidationError, match="não negativo"):
        StandardForm(
            A=[[1, 1]], b=[-1], c=[1, 1], names=("x1", "x2"), num_original=2
        )


# ----------------------------------------------------------------------
# Leitura de TOML
# ----------------------------------------------------------------------


def test_from_toml(pequeno: Problem) -> None:
    p = Problem.from_toml(path=EXAMPLES / "pequeno.toml")
    assert p.sense == "max"
    np.testing.assert_array_equal(p.c, pequeno.c)
    assert p.names == pequeno.names
    assert [k.sense for k in p.constraints] == ["<=", "<=", ">="]
    assert [k.rhs for k in p.constraints] == [4, 6, 1]


def test_from_toml_accepts_str_path() -> None:
    p = Problem.from_toml(path=str(EXAMPLES / "pequeno.toml"))
    assert p.num_constraints == 3


# ----------------------------------------------------------------------
# Forma padrão
# ----------------------------------------------------------------------


def test_standard_form_pequeno(pequeno: Problem) -> None:
    """max -> min, folgas s1 e s2, excesso e3."""
    sf = pequeno.to_standard_form()
    np.testing.assert_allclose(
        sf.A,
        [
            [1, 1, 1, 0, 0],
            [1, 3, 0, 1, 0],
            [1, 0, 0, 0, -1],
        ],
    )
    np.testing.assert_allclose(sf.b, [4, 6, 1])
    np.testing.assert_allclose(sf.c, [-3, -2, 0, 0, 0])
    assert sf.names == ("x1", "x2", "s1", "s2", "e3")
    assert sf.num_original == 2
    assert sf.objective_sign == -1


def test_standard_form_equality_adds_no_column() -> None:
    sf = make(
        "min", [2, 3], ([1, 1], "==", 5), ([1, 0], "<=", 3)
    ).to_standard_form()
    np.testing.assert_allclose(sf.A, [[1, 1, 0], [1, 0, 1]])
    assert sf.names == ("x1", "x2", "s2")
    assert sf.objective_sign == 1


def test_standard_form_negative_rhs() -> None:
    """-x1 - x2 <= -2 vira x1 + x2 >= 2, com excesso."""
    sf = make("min", [1, 2], ([-1, -1], "<=", -2)).to_standard_form()
    np.testing.assert_allclose(sf.A, [[1, 1, -1]])
    np.testing.assert_allclose(sf.b, [2])
    assert sf.names == ("x1", "x2", "e1")


def test_original_solution_and_objective(pequeno: Problem) -> None:
    sf = pequeno.to_standard_form()
    np.testing.assert_allclose(
        sf.original_solution(x=np.array([4, 0, 0, 2, 3])), [4, 0]
    )
    assert sf.original_objective(value=-12) == pytest.approx(12)


# ----------------------------------------------------------------------
# Fase 1
# ----------------------------------------------------------------------


def test_phase_one_tableau(pequeno: Problem) -> None:
    sf = pequeno.to_standard_form()
    t = sf.phase_one_tableau()
    np.testing.assert_allclose(t.A, np.hstack([sf.A, np.eye(3)]))
    np.testing.assert_allclose(t.b, sf.b)
    np.testing.assert_allclose(t.c, [0, 0, 0, 0, 0, 1, 1, 1])
    assert t.basis == (5, 6, 7)


def test_initial_tableau_is_feasible(solver: Solver, pequeno: Problem) -> None:
    sf = pequeno.to_standard_form()
    t = sf.initial_tableau(solver=solver)
    assert t is not None
    np.testing.assert_allclose(t.A, sf.A)
    np.testing.assert_allclose(t.c, sf.c)
    assert all(j < sf.A.shape[1] for j in t.basis), "sobrou artificial"
    np.testing.assert_allclose(sf.A @ t.solution, sf.b, atol=1e-9)
    assert (t.solution >= -1e-9).all()


def test_initial_tableau_infeasible(solver: Solver) -> None:
    sf = make(
        "min", [1, 1], ([1, 1], "<=", 1), ([1, 1], ">=", 2)
    ).to_standard_form()
    assert sf.initial_tableau(solver=solver) is None


def test_initial_tableau_removes_redundant_row(solver: Solver) -> None:
    """A segunda restrição é o dobro da primeira."""
    sf = make(
        "min", [1, 0], ([1, 1], "==", 2), ([2, 2], "==", 4)
    ).to_standard_form()
    t = sf.initial_tableau(solver=solver)
    assert t is not None
    assert t.num_constraints == 1
    assert t.basis[0] in (0, 1)


# ----------------------------------------------------------------------
# Problema completo
# ----------------------------------------------------------------------


def test_solve_pequeno(solver: Solver, pequeno: Problem) -> None:
    s = pequeno.solve(solver=solver)
    assert s.status == Status.OPTIMAL
    assert s.objective == pytest.approx(12)
    assert s.x is not None
    np.testing.assert_allclose(s.x, [4, 0], atol=1e-9)
    assert s.result is not None


def test_solve_default_solver(pequeno: Problem) -> None:
    s = pequeno.solve()
    assert s.status == Status.OPTIMAL
    assert s.objective == pytest.approx(12)


def test_solve_from_toml(solver: Solver) -> None:
    s = Problem.from_toml(path=EXAMPLES / "pequeno.toml").solve(solver=solver)
    assert s.objective == pytest.approx(12)


def test_solve_greater_equal(solver: Solver) -> None:
    """Só restrições >=: a origem não é viável e a Fase 1 é necessária."""
    p = make("min", [1, 1], ([1, 2], ">=", 4), ([3, 1], ">=", 6))
    s = p.solve(solver=solver)
    assert s.status == Status.OPTIMAL
    assert s.objective == pytest.approx(14 / 5)
    assert s.x is not None
    np.testing.assert_allclose(s.x, [8 / 5, 6 / 5], atol=1e-9)


def test_solve_equality(solver: Solver) -> None:
    p = make("min", [2, 3], ([1, 1], "==", 5), ([1, 0], "<=", 3))
    s = p.solve(solver=solver)
    assert s.objective == pytest.approx(12)
    assert s.x is not None
    np.testing.assert_allclose(s.x, [3, 2], atol=1e-9)


def test_solve_negative_rhs(solver: Solver) -> None:
    p = make("min", [1, 2], ([-1, -1], "<=", -2))
    s = p.solve(solver=solver)
    assert s.objective == pytest.approx(2)


def test_solve_infeasible(solver: Solver) -> None:
    p = make("min", [1, 1], ([1, 1], "<=", 1), ([1, 1], ">=", 2))
    s = p.solve(solver=solver)
    assert s.status == Status.INFEASIBLE
    assert s.x is None
    assert s.objective is None


def test_solve_unbounded(solver: Solver) -> None:
    p = make("max", [1, 0], ([1, -1], "<=", 1))
    assert p.solve(solver=solver).status == Status.UNBOUNDED


def test_solve_redundant(solver: Solver) -> None:
    p = make("min", [1, 0], ([1, 1], "==", 2), ([2, 2], "==", 4))
    s = p.solve(solver=solver)
    assert s.status == Status.OPTIMAL
    assert s.objective == pytest.approx(0)


# ----------------------------------------------------------------------
# Exemplos (antes nas docstrings)
# ----------------------------------------------------------------------


def test_constraint_converts_to_floats() -> None:
    k = Constraint(coefs=[1, 3], sense="<=", rhs=6)
    assert k.coefs.tolist() == [1.0, 3.0]
    assert k.rhs == 6.0


def test_package_example_lexicographic() -> None:
    """O exemplo do pacote `simplex`, sem a restrição x1 >= 1."""
    p = make("max", [3, 2], ([1, 1], "<=", 4), ([1, 3], "<=", 6))
    s = p.solve(solver=Solver(rule=PivotingRule.LEXICOGRAPHIC))
    assert s.x is not None
    assert s.x.tolist() == [4.0, 0.0]
    assert s.objective == 12.0


def test_pequeno_default_names(pequeno: Problem) -> None:
    p = pequeno.model_copy(update={"names": None})
    assert p.variable_names == ("x1", "x2")


@pytest.mark.parametrize(
    ("coefs", "terms"),
    [
        ([1.0, -2.0, 0.0], [("", "x"), (" - ", "2 y"), ("", "")]),
        ([0.0, -1.0, 0.5], [("", ""), ("-", "y"), (" + ", "0.5 z")]),
    ],
)
def test_linear_terms(coefs: list[float], terms: list[tuple[str, str]]) -> None:
    assert _linear_terms(coefs=np.array(coefs), names=["x", "y", "z"]) == terms


def test_str_pequeno(pequeno: Problem) -> None:
    assert str(pequeno) == (
        "max   3 x1 + 2 x2\n"
        "s.a.    x1 +   x2 <= 4\n"
        "        x1 + 3 x2 <= 6\n"
        "        x1        >= 1\n"
        "      x1, x2 >= 0"
    )


def test_str_names_negative_and_equality() -> None:
    q = Problem(
        c=[1, -0.5, 0],
        constraints=(
            Constraint(coefs=[-1, 2, 0], sense="==", rhs=-3),
            Constraint(coefs=[0, 1, -1], sense="<=", rhs=10),
        ),
        names=("a", "b", "c"),
    )
    assert str(q) == (
        "min    a - 0.5 b\n"
        "s.a.  -a +   2 b     = -3\n"
        "               b - c <= 10\n"
        "      a, b, c >= 0"
    )


def test_phase_one_names_and_initial_basis(pequeno: Problem) -> None:
    sf = pequeno.to_standard_form()
    assert sf.phase_one_tableau().variable_names[5:] == ("y1", "y2", "y3")
    t = sf.initial_tableau(solver=Solver())
    assert t is not None
    assert all(j < 5 for j in t.basis)
    assert sf.original_solution(x=t.solution).shape == (2,)
