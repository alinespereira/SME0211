"""Método simplex (implementação ingênua da aula 18) com regras anticiclagem.

.. include:: ../../docs/modulos/simplex.solver.md
"""

import logging
from enum import StrEnum
from typing import Self

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from simplex.defaults import MAX_ITERATIONS, TOLERANCE
from simplex.display import format_number, render_tableau
from simplex.logs import RICH_TEXT
from simplex.tableau import FloatArray, Tableau

__all__ = [
    "PivotingRule",
    "Result",
    "Solver",
    "Status",
]

logger = logging.getLogger(__name__)


def _log_tableau(
    *,
    log: logging.Logger,
    title: str,
    tableau: Tableau,
    entering: int | None = None,
    leaving: int | None = None,
) -> None:
    """Registra o tableau em destaque no nível DEBUG de `log`, se ativo."""
    if not log.isEnabledFor(logging.DEBUG):
        return
    text = render_tableau(tableau=tableau, entering=entering, leaving=leaving)
    log.debug(f"{title}\n{text.plain}", extra={RICH_TEXT: text})


class PivotingRule(StrEnum):
    """Regra anticiclagem usada para escolher quem entra e quem sai da
    base (veja o módulo).
    """

    BLAND = "bland"
    r"""Regra de Bland: entra o menor $j$ e sai o menor $B(\ell)$."""

    LEXICOGRAPHIC = "lexicographic"
    """Regra lexicográfica: sai a linha lexicograficamente menor."""


class Status(StrEnum):
    """Como o método terminou."""

    OPTIMAL = "optimal"
    r"""Todos os custos reduzidos são não negativos: a solução é ótima."""

    UNBOUNDED = "unbounded"
    r"""Há $j$ com $\bar{c}_j < 0$ e $u \leq 0$: custo ótimo $-\infty$."""

    ITERATION_LIMIT = "iteration_limit"
    """O número máximo de iterações foi atingido antes de uma conclusão."""

    INFEASIBLE = "infeasible"
    """A Fase 1 mostrou que não há solução viável (só em
    `simplex.problem.Problem.solve`).
    """


class Result(BaseModel):
    """Resultado de `Solver.solve`."""

    status: Status
    """Como o método terminou."""

    tableau: Tableau
    """Tableau da última base visitada (a ótima, se `status` for
    `Status.OPTIMAL`)."""

    iterations: int
    """Número de trocas de base realizadas."""


class Solver(BaseModel):
    """Método simplex parametrizado pela regra anticiclagem."""

    model_config = ConfigDict(frozen=True)

    rule: PivotingRule = PivotingRule.BLAND
    """Regra anticiclagem usada nos passos 2 e 4."""

    max_iterations: int = Field(default=MAX_ITERATIONS, gt=0)
    """Número máximo de trocas de base antes de desistir."""

    # ------------------------------------------------------------------
    # Laço principal
    # ------------------------------------------------------------------

    def solve(
        self: Self, *, tableau: Tableau, log: logging.Logger = logger
    ) -> Result:
        """Executa o simplex a partir da base viável de `tableau`, registrando
        cada iteração em `log`.
        """
        for i in range(self.max_iterations):
            if self.is_optimal(tableau=tableau):
                _log_tableau(
                    log=log,
                    title=f"Iteração {i}: solução ótima",
                    tableau=tableau,
                )
                return Result(
                    status=Status.OPTIMAL,
                    tableau=tableau,
                    iterations=i,
                )
            entering = self.entering_variable(tableau=tableau)
            u = tableau.column(j=entering)
            leaving = self.leaving_row(tableau=tableau, u=u)
            names = tableau.variable_names
            if leaving is None:
                _log_tableau(
                    log=log,
                    title=(
                        f"Iteração {i}: entra {names[entering]} (↓), mas "
                        "u ≤ 0: custo ótimo -∞"
                    ),
                    tableau=tableau,
                    entering=entering,
                )
                return Result(
                    status=Status.UNBOUNDED,
                    tableau=tableau,
                    iterations=i,
                )
            _log_tableau(
                log=log,
                title=(
                    f"Iteração {i}: entra {names[entering]} (↓), "
                    f"sai {names[tableau.basis[leaving]]} (→), "
                    f"pivô [{format_number(value=float(u[leaving]))}]"
                ),
                tableau=tableau,
                entering=entering,
                leaving=leaving,
            )
            tableau = self.change_basis(
                tableau=tableau,
                j=entering,
                ell=leaving,
            )

        return Result(
            status=Status.ITERATION_LIMIT,
            tableau=tableau,
            iterations=self.max_iterations,
        )

    # ------------------------------------------------------------------
    # Passos de uma iteração
    # ------------------------------------------------------------------

    def is_optimal(self: Self, *, tableau: Tableau) -> bool:
        r"""Passo 1: testa se $\bar{c}_j \geq 0$ para todo $j$."""
        return bool(np.all(tableau.reduced_costs >= -TOLERANCE))

    def entering_variable(self: Self, *, tableau: Tableau) -> int:
        """Passo 2: o índice $j$ da variável que entra, conforme `rule`."""
        match self.rule:
            case PivotingRule.LEXICOGRAPHIC:
                return self._entering_lexicographic(tableau=tableau)
            case PivotingRule.BLAND:
                return self._entering_bland(tableau=tableau)

    def leaving_row(
        self: Self, *, tableau: Tableau, u: FloatArray
    ) -> int | None:
        r"""Passo 4: a linha $\ell$ que sai, ou `None` se $u \leq 0$."""
        # u <= 0 (a menos da tolerância): nenhuma linha limita o passo.
        if np.all(u <= TOLERANCE):
            return None

        match self.rule:
            case PivotingRule.LEXICOGRAPHIC:
                return self._leaving_lexicographic(tableau=tableau, u=u)
            case PivotingRule.BLAND:
                return self._leaving_bland(tableau=tableau, u=u)

    def change_basis(
        self: Self, *, tableau: Tableau, j: int, ell: int
    ) -> Tableau:
        r"""Passo 5: troca $B(\ell)$ por $j$ e devolve o novo tableau."""
        new_basis = list(tableau.basis)
        new_basis[ell] = j
        return tableau.with_basis(basis=new_basis)

    # ------------------------------------------------------------------
    # Partes que dependem da regra anticiclagem
    # ------------------------------------------------------------------

    def _entering_bland(self: Self, *, tableau: Tableau) -> int:
        r"""Bland: o menor $j$ com $\bar{c}_j < 0$."""
        entering, *_ = np.flatnonzero(tableau.reduced_costs < -TOLERANCE)
        return int(entering)

    def _entering_lexicographic(self: Self, *, tableau: Tableau) -> int:
        r"""Lexicográfica: um $j$ qualquer com $\bar{c}_j < 0$, sorteado."""
        entering = np.random.choice(
            np.flatnonzero(tableau.reduced_costs < -TOLERANCE).astype(int)
        )
        return int(entering)

    def _leaving_bland(self: Self, *, tableau: Tableau, u: FloatArray) -> int:
        r"""Bland: a linha que atinge $\theta^*$ com o menor $B(\ell)$."""
        candidates = np.flatnonzero(u > TOLERANCE)
        thetas = tableau.basic_solution[candidates] / u[candidates]
        ties = candidates[thetas <= thetas.min() + TOLERANCE]
        return int(min(ties, key=lambda i: tableau.basis[i]))

    def _leaving_lexicographic(
        self: Self, *, tableau: Tableau, u: FloatArray
    ) -> int:
        r"""Lexicográfica: a linha com $u_\ell > 0$ de menor $v_\ell$ (veja o
        módulo).
        """
        candidates = np.flatnonzero(u > TOLERANCE)
        rows = tableau.table[1:, :]
        thetas = rows[candidates] / u[candidates, None]
        ell = int(candidates[np.lexsort(thetas.T[::-1])[0]])
        return ell
