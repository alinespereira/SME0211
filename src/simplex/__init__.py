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
- `simplex.display`: exibição do tableau, com a variável que entra, a
  que sai e o pivô em destaque;
- `simplex.logs`: configuração do `logging` (`simplex.logs.configure_logging`);
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

**Logs.** Importar o pacote configura o `logging` com o
`simplex.logs.Handler` (um `RichHandler`), no nível INFO. O
`simplex.solver.Solver` registra o tableau de cada iteração no nível
DEBUG, destacando a variável que entra, a que sai e o pivô; use
`simplex.logs.configure_logging` com `debug=True` para vê-lo.
"""

import logging

from . import display, logs, problem, solver, tableau
from .logs import Handler, configure_logging
from .problem import (
    Constraint,
    ConstraintSense,
    ObjectiveSense,
    Problem,
    Solution,
    StandardForm,
)
from .solver import (
    PivotingRule,
    Result,
    Solver,
    Status,
)
from .tableau import Tableau

__all__ = [
    "Constraint",
    "ConstraintSense",
    "Handler",
    "ObjectiveSense",
    "PivotingRule",
    "Problem",
    "Result",
    "Solution",
    "Solver",
    "StandardForm",
    "Status",
    "Tableau",
    "configure_logging",
    "display",
    "logs",
    "problem",
    "solver",
    "tableau",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[Handler(rich_tracebacks=True, markup=True)],
)


def main() -> None:
    """Ponto de entrada do comando `simplex` (ainda não implementado)."""
    raise NotImplementedError


if __name__ == "__main__":
    main()
