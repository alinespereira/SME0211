r"""Implementação própria do método simplex, seguindo as aulas de SME0211.

O pacote resolve problemas de otimização linear

$$
\begin{aligned}
\min_{x} \quad & c^\top x \cr
\text{s.a.} \quad & a_i^\top x \;\square_i\; b_i, \quad i = 1, \dots, m, \cr
& x \geq 0,
\end{aligned}
$$

em que cada $\square_i$ é $\leq$, $\geq$ ou $=$ (e o problema pode ser de
maximização), com o método simplex em duas fases.

**Módulos:**

- `simplex.problem`: descrição do problema como escrito no papel
  (`simplex.problem.Problem`), leitura de TOML, conversão para a forma
  padrão e Fase 1;
- `simplex.tableau`: o `simplex.tableau.Tableau`, com a base, $x_B$,
  os custos reduzidos e o tableau completo;
- `simplex.solver`: o `simplex.solver.Solver`, que executa o método a
  partir de uma base viável, com a regra de Bland ou a lexicográfica;
- `simplex.defaults`: tolerância e limite de iterações.

**Exemplo:**

>>> from simplex.problem import Constraint, Problem
>>> from simplex.solver import PivotingRule, Solver
>>> p = Problem(
...     sense="max",
...     c=[3, 2],
...     constraints=(
...         Constraint(coefs=[1, 1], sense="<=", rhs=4),
...         Constraint(coefs=[1, 3], sense="<=", rhs=6),
...     ),
... )
>>> solution = p.solve(solver=Solver(rule=PivotingRule.LEXICOGRAPHIC))
>>> solution.x.tolist(), solution.objective
([4.0, 0.0], 12.0)

**Logs.** Importar o pacote configura o `logging` com o `RichHandler`, no
nível INFO. O `simplex.solver.Solver` registra cada iteração no nível
DEBUG.
"""

import logging

from rich.logging import RichHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, markup=True)],
)


def main() -> None:
    """Ponto de entrada do comando `simplex` (ainda não implementado)."""
    raise NotImplementedError


if __name__ == "__main__":
    main()
