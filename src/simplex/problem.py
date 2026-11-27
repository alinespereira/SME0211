"""Descrição de problemas de otimização linear e conversão para a forma
padrão.

.. include:: ../../docs/modulos/simplex.problem.md
"""

import logging
import tomllib
from collections.abc import Sequence
from pathlib import Path
from typing import Literal, Self

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator

from simplex.defaults import TOLERANCE
from simplex.display import format_number
from simplex.logs import PHASE_ONE_LOGGER
from simplex.solver import Result, Solver, Status
from simplex.tableau import FloatArray, Matrix, Tableau, Vector

__all__ = [
    "Constraint",
    "ConstraintSense",
    "ObjectiveSense",
    "Problem",
    "Solution",
    "StandardForm",
]

type ConstraintSense = Literal["<=", ">=", "=="]
"""Sentido de uma restrição: $\\leq$, $\\geq$ ou $=$."""

type ObjectiveSense = Literal["min", "max"]
"""Sentido da otimização."""

_FLIPPED_SENSE: dict[ConstraintSense, ConstraintSense] = {
    "<=": ">=",
    ">=": "<=",
    "==": "==",
}
"""Sentido da restrição depois de multiplicá-la por $-1$."""


def _linear_terms(
    *, coefs: FloatArray, names: Sequence[str]
) -> list[tuple[str, str]]:
    r"""Os termos de $a^\top x$, um par `(sinal, termo)` por variável."""
    terms: list[tuple[str, str]] = []
    first = True
    for value, name in zip(coefs.tolist(), names, strict=True):
        if abs(value) <= TOLERANCE:
            terms.append(("", ""))
            continue
        magnitude = abs(value)
        if abs(magnitude - 1) <= TOLERANCE:
            term = name
        else:
            term = f"{format_number(value=magnitude)} {name}"
        if first:
            sign = "-" if value < 0 else ""
        else:
            sign = " - " if value < 0 else " + "
        terms.append((sign, term))
        first = False
    return terms


class Constraint(BaseModel):
    r"""Uma restrição $a_i^\top x \;\square_i\; b_i$."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    coefs: Vector
    r"""Coeficientes $a_i \in \mathbb{R}^n$."""

    sense: ConstraintSense
    r"""Sentido $\square_i$: `"<="`, `">="` ou `"=="`."""

    rhs: float
    r"""Lado direito $b_i$ (pode ser negativo)."""


class Problem(BaseModel):
    """Problema de otimização linear, como escrito no papel."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    sense: ObjectiveSense = "min"
    """Minimizar ou maximizar."""

    c: Vector
    r"""Vetor de custos $c \in \mathbb{R}^n$."""

    constraints: tuple[Constraint, ...] = Field(min_length=1)
    """Restrições, na ordem em que aparecem."""

    names: tuple[str, ...] | None = None
    """Nomes das variáveis (opcional). Sem nomes, usa-se `x1`, ..., `xn`."""

    @model_validator(mode="after")
    def _check_dimensions(self: Self) -> Self:
        """Confere se todas as restrições e os nomes têm $n$ entradas."""
        n = self.num_variables
        for i, constraint in enumerate(self.constraints, start=1):
            if constraint.coefs.shape != (n,):
                raise ValueError(
                    f"A restrição {i} tem {constraint.coefs.shape[0]} "
                    f"coeficientes, mas c tem {n}."
                )
        if self.names is not None:
            if len(self.names) != n:
                raise ValueError(
                    f"names tem {len(self.names)} nomes, mas c tem {n}."
                )
            if len(set(self.names)) != n:
                raise ValueError("names não pode ter nomes repetidos.")
        return self

    @property
    def num_variables(self: Self) -> int:
        """Número de variáveis, $n$."""
        return int(self.c.shape[0])

    @property
    def num_constraints(self: Self) -> int:
        """Número de restrições, $m$."""
        return len(self.constraints)

    @property
    def variable_names(self: Self) -> tuple[str, ...]:
        """`names`, ou `x1`, ..., `xn` se não foram dados."""
        if self.names is not None:
            return self.names
        return tuple(f"x{j}" for j in range(1, self.num_variables + 1))

    # ------------------------------------------------------------------
    # Exibição
    # ------------------------------------------------------------------

    def __str__(self: Self) -> str:
        """O problema como escrito no papel, com os termos alinhados por
        variável.
        """
        rows = [
            self.c,
            *(constraint.coefs for constraint in self.constraints),
        ]
        terms = [
            _linear_terms(coefs=row, names=self.variable_names) for row in rows
        ]
        n = self.num_variables
        sign_widths = [max(len(row[j][0]) for row in terms) for j in range(n)]
        term_widths = [max(len(row[j][1]) for row in terms) for j in range(n)]

        def expression(row: list[tuple[str, str]]) -> str:
            return "".join(
                sign.rjust(sw) + term.rjust(tw)
                for (sign, term), sw, tw in zip(
                    row, sign_widths, term_widths, strict=True
                )
            ).rstrip()

        lines = [f"{self.sense:<4}  {expression(terms[0])}"]
        body = [expression(row_terms) for row_terms in terms]
        lhs_width = max(len(b) for b in body[1:])
        for i, constraint in enumerate(self.constraints):
            prefix = "s.a." if i == 0 else ""
            sense = "=" if constraint.sense == "==" else constraint.sense
            rhs = format_number(value=constraint.rhs)
            lines.append(
                f"{prefix:<4}  {body[i + 1].ljust(lhs_width)} {sense} {rhs}"
            )
        lines.append(f"{'':<4}  {', '.join(self.variable_names)} >= 0")
        return "\n".join(line.rstrip() for line in lines)

    # ------------------------------------------------------------------
    # Leitura
    # ------------------------------------------------------------------

    @classmethod
    def from_toml(cls: type[Self], *, path: Path | str) -> Self:
        """Lê um problema de um arquivo TOML (veja o módulo)."""
        path = Path(path)
        with path.open(mode="rb") as fp:
            return cls.model_validate(tomllib.load(fp))

    # ------------------------------------------------------------------
    # Conversão e resolução
    # ------------------------------------------------------------------

    def to_standard_form(self: Self) -> "StandardForm":
        """Converte o problema para a forma padrão (veja o módulo)."""
        m = self.num_constraints
        sign: Literal[1, -1] = -1 if self.sense == "max" else 1

        rows: list[FloatArray] = []
        rhs: list[float] = []
        extra_columns: list[FloatArray] = []
        names = list(self.variable_names)

        for i, constraint in enumerate(self.constraints):
            coefs, b_i, sense = (
                constraint.coefs,
                constraint.rhs,
                constraint.sense,
            )

            # Passo 2: lado direito negativo -> multiplica a linha por -1.
            if b_i < 0:
                coefs, b_i = -coefs, -b_i
                sense = _FLIPPED_SENSE[sense]
            rows.append(coefs)
            rhs.append(b_i)

            # Passo 3: folga (+1) para <=, excesso (-1) para >=.
            if sense != "==":
                column = np.zeros(m)
                column[i] = 1.0 if sense == "<=" else -1.0
                extra_columns.append(column)
                names.append(f"{'s' if sense == '<=' else 'e'}{i + 1}")

        matrix = np.vstack(rows)
        if extra_columns:
            matrix = np.hstack([matrix, np.column_stack(extra_columns)])

        # Passo 1: max c^T x = -min (-c)^T x; folgas e excessos custam 0.
        c = np.concatenate([sign * self.c, np.zeros(len(extra_columns))])

        return StandardForm(
            A=matrix,
            b=np.array(rhs),
            c=c,
            names=tuple(names),
            num_original=self.num_variables,
            objective_sign=sign,
        )

    def solve(self: Self, *, solver: Solver | None = None) -> "Solution":
        """Resolve o problema: forma padrão, Fase 1, Fase 2 e volta às
        variáveis originais (com a regra de Bland se `solver` for `None`).
        """
        solver = solver if solver is not None else Solver()
        standard = self.to_standard_form()

        # Fase 1: base viável inicial (ou prova de inviabilidade).
        tableau = standard.initial_tableau(solver=solver)
        if tableau is None:
            return Solution(status=Status.INFEASIBLE)

        # Fase 2: o simplex a partir dessa base.
        result = solver.solve(tableau=tableau)
        final = result.tableau
        return Solution(
            status=result.status,
            x=standard.original_solution(x=final.solution),
            objective=standard.original_objective(value=final.objective_value),
            result=result,
        )


class StandardForm(BaseModel):
    """Problema na forma padrão, com o necessário para voltar ao original."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    A: Matrix
    r"""Matriz $\tilde{A} \in \mathbb{R}^{m \times N}$, com $N \geq n$."""

    b: Vector
    r"""Lado direito $\tilde{b} \in \mathbb{R}^m$, com $\tilde{b} \geq 0$."""

    c: Vector
    r"""Custos $\tilde{c} \in \mathbb{R}^N$ (minimização)."""

    names: tuple[str, ...]
    """Nome de cada coluna de $\\tilde{A}$: as originais, depois as folgas
    (`s{i}`) e os excessos (`e{i}`)."""

    num_original: int = Field(ge=1)
    """Número $n$ de variáveis originais: as $n$ primeiras colunas."""

    objective_sign: Literal[1, -1] = 1
    r"""$+1$ se o problema original é de minimização e $-1$ se é de
    maximização: o valor original é `objective_sign` vezes o valor de
    $\tilde{c}^\top \tilde{x}$."""

    @model_validator(mode="after")
    def _check(self: Self) -> Self:
        r"""Confere as dimensões e que $\tilde{b} \geq 0$."""
        m, n = self.A.shape
        if self.b.shape != (m,):
            raise ValueError(f"b deve ter {m} entradas, tem {self.b.shape}.")
        if self.c.shape != (n,):
            raise ValueError(f"c deve ter {n} entradas, tem {self.c.shape}.")
        if len(self.names) != n:
            raise ValueError(
                f"names deve ter {n} nomes, tem {len(self.names)}."
            )
        if self.num_original > n:
            raise ValueError(
                "num_original não pode passar do número de colunas."
            )
        if (self.b < -TOLERANCE).any():
            raise ValueError("Na forma padrão, b deve ser não negativo.")
        return self

    # ------------------------------------------------------------------
    # Fase 1
    # ------------------------------------------------------------------

    def phase_one_tableau(self: Self) -> Tableau:
        """Tableau inicial do problema auxiliar da Fase 1 (veja o módulo)."""
        num_constraints, num_variables = self.A.shape
        A = np.hstack([self.A, np.eye(num_constraints)])  # noqa: N806
        b = self.b
        # Custo 0 nas variáveis da forma padrão e 1 nas artificiais.
        c = np.concatenate([np.zeros(num_variables), np.ones(num_constraints)])
        basis = tuple(range(num_variables, num_variables + num_constraints))
        # As artificiais se chamam y1, ..., ym, como nas fórmulas acima
        # (com um "_" na frente se o nome já for usado por outra coluna).
        artificial = [f"y{i + 1}" for i in range(num_constraints)]
        while set(artificial) & set(self.names):
            artificial = [f"_{name}" for name in artificial]
        names = (*self.names, *artificial)
        return Tableau(A=A, b=b, c=c, basis=basis, names=names)

    def initial_tableau(self: Self, *, solver: Solver) -> Tableau | None:
        """Fase 1: uma base viável da forma padrão, ou `None` se inviável."""
        num_constraints, num_variables = self.A.shape

        # 1. Resolve o problema auxiliar.
        tableau = solver.solve(
            tableau=self.phase_one_tableau(),
            log=logging.getLogger(PHASE_ONE_LOGGER),
        ).tableau

        # 2. Custo ótimo positivo: alguma artificial não pode ser zerada.
        if tableau.objective_value > TOLERANCE:
            return None

        # 3. Tira da base as artificiais que sobraram (todas valem zero).
        basis = list(tableau.basis)
        redundant: list[int] = []
        for ell in range(num_constraints):
            if basis[ell] < num_variables:
                continue
            # Linha ell de B^{-1} [A | I], só nas colunas originais.
            row = np.linalg.solve(tableau.B, tableau.A)[ell, :num_variables]
            candidates = [
                j
                for j in range(num_variables)
                if j not in basis and abs(row[j]) > TOLERANCE
            ]
            if candidates:
                basis[ell] = candidates[0]
                tableau = tableau.with_basis(basis=basis)
            else:
                redundant.append(ell)

        # 4. Remove as linhas redundantes e volta aos dados originais.
        keep = [i for i in range(num_constraints) if i not in redundant]
        return Tableau(
            A=self.A[keep],
            b=self.b[keep],
            c=self.c,
            basis=tuple(basis[i] for i in keep),
            names=self.names,
        )

    # ------------------------------------------------------------------
    # Volta ao problema original
    # ------------------------------------------------------------------

    def original_solution(self: Self, *, x: FloatArray) -> FloatArray:
        r"""Restringe $\tilde{x}$ às $n$ variáveis originais."""
        return x[: self.num_original]

    def original_objective(self: Self, *, value: float) -> float:
        """Valor da função objetivo original (vezes `objective_sign`)."""
        return self.objective_sign * value


class Solution(BaseModel):
    """Resultado de `Problem.solve`, nas variáveis originais."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    status: Status
    """Como terminou: ótimo, ilimitado, inviável ou limite de iterações."""

    x: Vector | None = None
    """Valores das variáveis originais na última base (`None` se
    inviável)."""

    objective: float | None = None
    """Valor da função objetivo original em `x` (`None` se inviável)."""

    result: Result | None = None
    """Resultado da Fase 2, com o tableau final (`None` se inviável)."""
