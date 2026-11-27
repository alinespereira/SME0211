r"""Modelo de otimização linear da gráfica: a versão relaxada do artigo,
focada no tempo de operação das máquinas.

O artigo *Energy consumption optimization in a printing company* propõe um
modelo de programação linear inteira, com variáveis $z_{im}$ (metros do
item $i$ impressos na máquina $m$), $w_{in}$ (metros do item $i \in F$
acabados na máquina $n$) e variáveis binárias de designação $x_{im}$ e
$y_{in}$. A função objetivo (16) do artigo minimiza o tempo de operação:

$$
\min \sum_{m \in M} \sum_{i \in I} (T_{im} z_{im} + A_{im} x_{im})
   + \sum_{n \in N} \sum_{i \in F} (T_{in} w_{in} + A_{in} y_{in}).
$$

**Relaxação.** Aqui ficam só a parte contínua do tempo e as restrições de
demanda (4) e (5):

- as variáveis binárias $x_{im}$, $y_{in}$ (e, com elas, os setups $A$ e as
  restrições (6) a (11)) são removidas. Na relaxação linear,
  $x_{im} \geq z_{im} / G$ com $G$ grande, então o setup contribui com
  $A_{im} z_{im} / G \approx 0$;
- as restrições de capacidade (2) e (3), $\sum_i (T_{im} z_{im} + \dots)
  \leq T_m$, também ficam de fora;
- como o tempo por metro $T_{im} = 1 / v_m$ não depende do item, as
  variáveis podem ser agregadas por máquina:
  $z_m = \sum_{i \in I} z_{im}$ e $w_n = \sum_{i \in F} w_{in}$.

Somando (4) em $i \in I$ e (5) em $i \in F$, o modelo fica

$$
\begin{aligned}
\min \quad & \sum_{m \in M} \frac{z_m}{v_m}
   + \sum_{n \in N} \frac{w_n}{v_n} \cr
\text{s.a.} \quad & \sum_{m \in M} z_m \geq \sum_{i \in I} D_i, \cr
& \sum_{n \in N} w_n \geq \sum_{i \in F} D_i, \cr
& z, w \geq 0,
\end{aligned}
$$

em horas, com $v$ em metros por hora. As restrições de demanda são
escritas com $\geq$, mas, como os custos $1/v$ são positivos, no ótimo
elas valem com igualdade, como as restrições (4) e (5) do artigo.

Sem as capacidades, a solução ótima manda toda a impressão para a
impressora mais rápida e todo o acabamento para a máquina de acabamento
mais rápida. `build_problem` monta esse modelo como um `simplex.Problem`.
"""

from collections.abc import Sequence

import numpy as np

from printing_company.problem.spec import (
    FinishingMachine,
    Portfolio,
    PrintingMachine,
)
from simplex import Constraint, Problem

__all__ = ["build_problem"]


def build_problem(
    *,
    portfolio: Portfolio,
    printers: Sequence[PrintingMachine],
    finishings: Sequence[FinishingMachine],
) -> Problem:
    r"""Monta o modelo relaxado (veja o módulo) de tempo de operação.

    As variáveis são, nesta ordem, $z_m$ para cada impressora de
    `printers` e $w_n$ para cada máquina de acabamento de `finishings`, e
    levam os nomes das máquinas (`Machine.id`). O custo de cada uma é o
    tempo por metro, $1 / v$, em horas; as duas restrições são

    $$
    \begin{aligned}
    \sum_{m \in M} z_m &\geq \sum_{i \in I} D_i
       \quad \text{(impressão)}, \cr
    \sum_{n \in N} w_n &\geq \sum_{i \in F} D_i
       \quad \text{(acabamento)},
    \end{aligned}
    $$

    com os lados direitos `Portfolio.total` e `Portfolio.with_finishing`.

    **Exemplo:** duas impressoras, uma máquina de acabamento e dois itens,
    dos quais só o primeiro precisa de acabamento.

    >>> from printing_company.problem.spec import Demand
    >>> portfolio = Portfolio(
    ...     label="Exemplo",
    ...     demands=[
    ...         Demand(label="D01", quantity=15_000, requires_finishing=True),
    ...         Demand(label="D02", quantity=20_000),
    ...     ],
    ... )
    >>> problem = build_problem(
    ...     portfolio=portfolio,
    ...     printers=[
    ...         PrintingMachine(id="P1", speed=10_500, setup=0.25, consumption=40),
    ...         PrintingMachine(id="P2", speed=3_000, setup=0.5, consumption=112),
    ...     ],
    ...     finishings=[
    ...         FinishingMachine(id="F1", speed=7_800, setup=0.5, consumption=40),
    ...     ],
    ... )
    >>> problem.variable_names
    ('P1', 'P2', 'F1')
    >>> [round(cj, 6) for cj in problem.c.tolist()]  # horas por metro
    [9.5e-05, 0.000333, 0.000128]
    >>> [k.coefs.tolist() for k in problem.constraints]
    [[1.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    >>> [k.rhs for k in problem.constraints]
    [35000.0, 15000.0]

    Os 35 000 m vão para a impressora mais rápida e os 15 000 m de
    acabamento, para a única máquina de acabamento:
    $35\,000 / 10\,500 + 15\,000 / 7\,800 \approx 5{,}2564$ horas.

    >>> solution = problem.solve()
    >>> solution.x.tolist()
    [35000.0, 0.0, 15000.0]
    >>> round(solution.objective, 4)
    5.2564

    Com os dados do artigo (`printing_company.problem.data`), na carteira
    I, tudo vai para a `Print04` (12 600 m/h) e para a `Finish02`
    (12 000 m/h):

    >>> from printing_company.problem import data
    >>> problem = build_problem(
    ...     portfolio=data.portfolios[0],
    ...     printers=data.printers,
    ...     finishings=data.finishers,
    ... )
    >>> solution = problem.solve()
    >>> dict(zip(problem.variable_names, solution.x.tolist()))
    ... # doctest: +NORMALIZE_WHITESPACE
    {'Print01': 0.0, 'Print02': 0.0, 'Print03': 0.0, 'Print04': 543000.0,
     'Print05': 0.0, 'Finish01': 0.0, 'Finish03': 0.0, 'Finish02': 225000.0}
    >>> round(solution.objective, 4)
    61.8452
    """
    names = tuple(machine.id for machine in (*printers, *finishings))

    printer_costs = [1.0 / printer.speed for printer in printers]
    finishing_costs = [1.0 / finishing.speed for finishing in finishings]
    c = np.array([*printer_costs, *finishing_costs], dtype=np.float64)

    # Só as impressoras imprimem: as máquinas de acabamento ficam com
    # coeficiente 0 na restrição de impressão.
    is_printer = np.array(
        [1.0] * len(printers) + [0.0] * len(finishings),
        dtype=np.float64,
    )

    printer_constraint = Constraint(
        coefs=is_printer,
        sense=">=",
        rhs=portfolio.total,
    )
    finishing_constraint = Constraint(
        coefs=1.0 - is_printer,
        sense=">=",
        rhs=portfolio.with_finishing,
    )

    return Problem(
        sense="min",
        c=c,
        constraints=(
            printer_constraint,
            finishing_constraint,
        ),
        names=names,
    )
