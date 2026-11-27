r"""Método simplex (implementação ingênua da aula 18) com regras anticiclagem.

Cada iteração parte de um `simplex.tableau.Tableau` associado a uma base
viável e segue os passos das aulas:

1. **Otimalidade.** Calcule os custos reduzidos
   $\bar{c}_j = c_j - p^\top A_j$. Se $\bar{c}_j \geq 0$ para todo $j$, a
   solução básica viável atual é ótima e o método para.
2. **Variável que entra.** Escolha $j$ com $\bar{c}_j < 0$.
3. **Coluna pivô.** Calcule $u = B^{-1} A_j$. Se $u \leq 0$, então
   $\theta^* = \infty$, o custo ótimo é $-\infty$ e o método para.
4. **Variável que sai.** Calcule o passo
   $$
   \theta^* = \min_{\lbrace i \,:\, u_i > 0 \rbrace} \frac{x_{B(i)}}{u_i}
   $$
   e escolha uma linha $\ell$ que atinge esse mínimo.
5. **Troca de base.** Substitua $B(\ell)$ por $j$.

Em problemas degenerados ($x_{B(i)} = 0$ para algum $i$) pode haver
$\theta^* = 0$, e o método pode voltar a uma base já visitada e repetir
bases para sempre: é a **ciclagem**. As escolhas dos passos 2 e 4 são
livres, e as regras anticiclagem (`PivotingRule`) as fixam de modo a
garantir que o método termina em um número finito de iterações.

**Índices.** Como em `simplex.tableau`, as aulas numeram as linhas de $1$ a
$m$ e o código de $0$ a $m - 1$: a linha $\ell$ das fórmulas é o índice
`ell - 1` do código.
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
    title: str,
    tableau: Tableau,
    entering: int | None = None,
    leaving: int | None = None,
) -> None:
    """Registra o tableau no nível DEBUG, com `title` na primeira linha e
    a variável que entra, a que sai e o pivô em destaque (veja
    `simplex.display.render_tableau`).

    O tableau só é montado se o nível DEBUG estiver ativo, para não custar
    nada nas execuções normais.
    """
    if not logger.isEnabledFor(logging.DEBUG):
        return
    text = render_tableau(tableau=tableau, entering=entering, leaving=leaving)
    logger.debug(f"{title}\n{text.plain}", extra={RICH_TEXT: text})


class PivotingRule(StrEnum):
    r"""Regra anticiclagem usada para escolher quem entra e quem sai da
    base."""

    BLAND = "bland"
    r"""Regra de Bland (do menor índice).

    - Entra: o menor $j$ com $\bar{c}_j < 0$.
    - Sai: entre as linhas $\ell$ que atingem $\theta^*$, a de menor índice
      de variável $B(\ell)$.
    """

    LEXICOGRAPHIC = "lexicographic"
    r"""Regra lexicográfica.

    - Entra: qualquer $j$ com $\bar{c}_j < 0$ (por exemplo, o de menor
      $\bar{c}_j$).
    - Sai: entre as linhas $i$ com $u_i > 0$, a linha $\ell$ cujo vetor
      $$
      v_i = \frac{1}{u_i}
      \begin{bmatrix} x_{B(i)} & (B^{-1} A)_i \end{bmatrix}
      $$
      é o lexicograficamente menor, em que $(B^{-1} A)_i$ é a linha $i$
      de $B^{-1} A$. A primeira entrada de $v_i$ é $x_{B(i)} / u_i$, então
      a escolha sempre atinge $\theta^*$; as demais só desempatam.

    A garantia de término exige que, no tableau inicial, todas as linhas
    $\begin{bmatrix} x_{B(i)} & (B^{-1} A)_i \end{bmatrix}$ sejam
    lexicograficamente positivas (a primeira entrada não nula é positiva).
    Isso vale, por exemplo, quando a base inicial é formada pelas variáveis
    de folga e elas são as primeiras colunas de $A$.
    """


class Status(StrEnum):
    """Como o método terminou."""

    OPTIMAL = "optimal"
    r"""Todos os custos reduzidos são não negativos: a solução é ótima."""

    UNBOUNDED = "unbounded"
    r"""Há $j$ com $\bar{c}_j < 0$ e $u = B^{-1} A_j \leq 0$: o custo ótimo
    é $-\infty$."""

    ITERATION_LIMIT = "iteration_limit"
    """O número máximo de iterações foi atingido antes de uma conclusão."""

    INFEASIBLE = "infeasible"
    """A Fase 1 mostrou que não há solução viável (usado por
    `simplex.problem.Problem.solve`; o `Solver` sozinho não devolve este
    status, porque sempre parte de uma base viável)."""


class Result(BaseModel):
    """Resultado de `Solver.solve`.

    **Exemplo:**

    >>> t = Tableau(A=[[1, 1]], b=[2], c=[1, 0], basis=(0,))
    >>> result = Solver().solve(tableau=t)
    >>> result.status
    <Status.OPTIMAL: 'optimal'>
    >>> result.iterations
    1
    >>> result.tableau.basis
    (1,)
    """

    status: Status
    """Como o método terminou."""

    tableau: Tableau
    """Tableau da última base visitada (a ótima, se `status` for
    `Status.OPTIMAL`)."""

    iterations: int
    """Número de trocas de base realizadas."""


class Solver(BaseModel):
    r"""Método simplex parametrizado pela regra anticiclagem.

    Os métodos públicos correspondem aos passos do método descritos no
    módulo; os métodos `_entering_*` e `_leaving_*` implementam a parte de
    cada passo que depende da regra.

    **Exemplo:** o mesmo problema do exemplo de `simplex.tableau.Tableau`,
    partindo da base das folgas.

    >>> t = Tableau(
    ...     A=[[1, 1, 1, 0], [1, 3, 0, 1]],
    ...     b=[4, 6],
    ...     c=[-1, -2, 0, 0],
    ...     basis=(2, 3),
    ... )
    >>> solver = Solver(rule=PivotingRule.BLAND)

    Os passos de uma iteração, um de cada vez:

    >>> solver.is_optimal(tableau=t)
    False
    >>> j = solver.entering_variable(tableau=t)  # menor j com custo < 0
    >>> j
    0
    >>> u = t.column(j=j)
    >>> solver.leaving_row(tableau=t, u=u)  # razões 4/1 e 6/1
    0
    >>> solver.change_basis(tableau=t, j=0, ell=0).basis
    (0, 3)

    O método completo:

    >>> result = solver.solve(tableau=t)
    >>> result.status
    <Status.OPTIMAL: 'optimal'>
    >>> result.tableau.solution.tolist()
    [3.0, 1.0, 0.0, 0.0]
    >>> result.tableau.objective_value
    -5.0
    """

    model_config = ConfigDict(frozen=True)

    rule: PivotingRule = PivotingRule.BLAND
    """Regra anticiclagem usada nos passos 2 e 4."""

    max_iterations: int = Field(default=MAX_ITERATIONS, gt=0)
    """Número máximo de trocas de base antes de desistir."""

    # ------------------------------------------------------------------
    # Laço principal
    # ------------------------------------------------------------------

    def solve(self: Self, *, tableau: Tableau) -> Result:
        r"""Executa o método simplex a partir de uma base viável.

        Repete os passos 1 a 5 até encontrar uma solução ótima, detectar
        que o custo ótimo é $-\infty$ ou atingir `max_iterations`.

        No nível DEBUG do `logging`, registra o tableau de cada iteração,
        com a coluna da variável que entra marcada com `↓`, a linha da que
        sai marcada com `→` e o pivô entre colchetes (e em cores no
        terminal; veja `simplex.display`).

        **Parâmetros:**

        - `tableau`: tableau associado a uma base viável inicial.

        **Devolve:** um `Result` com o status, o último tableau e o número
        de iterações.
        """
        for i in range(self.max_iterations):
            if self.is_optimal(tableau=tableau):
                _log_tableau(
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
        r"""Passo 1: testa se $\bar{c}_j \geq 0$ para todo $j$.

        Use a tolerância `simplex.tableau.TOLERANCE`: considere
        $\bar{c}_j < 0$ só quando $\bar{c}_j < -\varepsilon$.
        """
        return bool(np.all(tableau.reduced_costs >= -TOLERANCE))

    def entering_variable(self: Self, *, tableau: Tableau) -> int:
        r"""Passo 2: escolhe o índice $j$ da variável que entra na base.

        Deve ser chamado só quando a solução atual não é ótima, isto é,
        quando existe $j$ com $\bar{c}_j < 0$. Delega a escolha a
        `_entering_bland` ou `_entering_lexicographic`, conforme `rule`.
        """
        match self.rule:
            case PivotingRule.LEXICOGRAPHIC:
                return self._entering_lexicographic(tableau=tableau)
            case PivotingRule.BLAND:
                return self._entering_bland(tableau=tableau)

    def leaving_row(
        self: Self, *, tableau: Tableau, u: FloatArray
    ) -> int | None:
        r"""Passo 4: escolhe a linha $\ell$ da variável que sai da base.

        **Parâmetros:**

        - `tableau`: tableau da iteração atual.
        - `u`: coluna pivô $u = B^{-1} A_j$ (veja `Tableau.column`).

        **Devolve:** o índice da linha $\ell$ que atinge
        $\theta^* = \min_{u_i > 0} x_{B(i)} / u_i$, escolhida por
        `_leaving_bland` ou `_leaving_lexicographic`, conforme `rule`; ou
        `None` se $u \leq 0$ (custo ótimo $-\infty$).
        """
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
        r"""Passo 5: troca $B(\ell)$ por $j$ e devolve o novo tableau.

        A nova base é
        $\bar{B} = \begin{bmatrix} A_{B(1)} & \cdots & A_{B(\ell-1)} & A_j &
        A_{B(\ell+1)} & \cdots & A_{B(m)} \end{bmatrix}$.
        Como `Tableau` é imutável e guarda os dados originais, basta
        montar a nova tupla de índices (`tableau.basis` com `j` na posição
        `ell`) e chamar `Tableau.with_basis`, que cria o novo tableau e
        confere que $\bar{B}$ é inversível e que a nova solução é viável.
        """
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
        r"""Lexicográfica: um $j$ com $\bar{c}_j < 0$ (a regra não restringe
        a escolha; uma opção comum é o $j$ de menor $\bar{c}_j$)."""
        entering = np.random.choice(
            np.flatnonzero(tableau.reduced_costs < -TOLERANCE).astype(int)
        )
        return int(entering)

    def _leaving_bland(self: Self, *, tableau: Tableau, u: FloatArray) -> int:
        r"""Bland: entre as linhas que atingem $\theta^*$, a de menor
        $B(\ell)$.

        Supõe que $u_i > 0$ para algum $i$.
        """
        candidates = np.flatnonzero(u > TOLERANCE)
        thetas = tableau.basic_solution[candidates] / u[candidates]
        ties = candidates[thetas <= thetas.min() + TOLERANCE]
        return int(min(ties, key=lambda i: tableau.basis[i]))

    def _leaving_lexicographic(
        self: Self, *, tableau: Tableau, u: FloatArray
    ) -> int:
        r"""Lexicográfica: a linha $\ell$ com $u_\ell > 0$ cuja linha do
        tableau dividida por $u_\ell$ é a lexicograficamente menor (veja
        `PivotingRule.LEXICOGRAPHIC`).

        As linhas do tableau sem a linha 0 são `tableau.table[1:]`.
        Supõe que $u_i > 0$ para algum $i$.
        """
        candidates = np.flatnonzero(u > TOLERANCE)
        rows = tableau.table[1:, :]
        thetas = rows[candidates] / u[candidates, None]
        ell = int(candidates[np.lexsort(thetas.T[::-1])[0]])
        return ell
