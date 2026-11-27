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

**Exemplo:** o problema

$$
\begin{aligned}
\max \quad & 3 x_1 + 2 x_2 \cr
\text{s.a.} \quad & x_1 + x_2 \leq 4, \cr
& x_1 + 3 x_2 \leq 6, \cr
& x \geq 0,
\end{aligned}
$$

tem ótimo $x = (4, 0)$, com valor $12$:

```python
from simplex import Constraint, PivotingRule, Problem, Solver

p = Problem(
    sense="max",
    c=[3, 2],
    constraints=(
        Constraint(coefs=[1, 1], sense="<=", rhs=4),
        Constraint(coefs=[1, 3], sense="<=", rhs=6),
    ),
)
solution = p.solve(solver=Solver(rule=PivotingRule.LEXICOGRAPHIC))
solution.x, solution.objective  # [4, 0], 12
```

Mais exemplos, passo a passo, estão no notebook
[`notebooks/01_simplex.ipynb`](https://github.com/alinespereira/SME0211/blob/main/notebooks/01_simplex.ipynb)
([abrir no Colab](https://colab.research.google.com/github/alinespereira/SME0211/blob/main/notebooks/01_simplex.ipynb)).

**Logs.** Importar o pacote configura o `logging` com o
`simplex.logs.Handler` (um `RichHandler`), no nível INFO. O
`simplex.solver.Solver` registra o tableau de cada iteração no nível
DEBUG, destacando a variável que entra, a que sai e o pivô; use
`simplex.logs.configure_logging` com `debug=True` para vê-lo.
