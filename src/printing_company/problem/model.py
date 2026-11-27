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

**Relaxação.** Aqui ficam só a parte contínua do tempo, as restrições de
capacidade (2) e (3) e as restrições de demanda (4) e (5):

- as variáveis binárias $x_{im}$, $y_{in}$ (e, com elas, os setups $A$ e as
  restrições (6) a (11)) são removidas. Na relaxação linear,
  $x_{im} \geq z_{im} / G$ com $G$ grande, então o setup contribui com
  $A_{im} z_{im} / G \approx 0$;
- nas restrições de capacidade (2) e (3), sem os setups, sobra o tempo de
  produção: $\sum_{i \in I} T_{im} z_{im} \leq T_m$. Todas as máquinas têm
  a mesma capacidade $T_m = T_n = T$, o número de horas de turno do
  horizonte de planejamento. No artigo, o turno é diário, de 8 horas mais
  até 2 horas extras (`SHIFT_HOURS`), então $T = 10 d$ para $d$ dias;
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
& \frac{z_m}{v_m} \leq T, \quad m \in M, \cr
& \frac{w_n}{v_n} \leq T, \quad n \in N, \cr
& z, w \geq 0,
\end{aligned}
$$

em horas, com $v$ em metros por hora. As restrições de demanda são
escritas com $\geq$, mas, como os custos $1/v$ são positivos, no ótimo
elas valem com igualdade, como as restrições (4) e (5) do artigo.

O problema é viável se, e só se, as máquinas dão conta da demanda no
horizonte: $T \sum_m v_m \geq \sum_{i \in I} D_i$ e
$T \sum_n v_n \geq \sum_{i \in F} D_i$. Sem as capacidades
(`capacity=None`), a solução ótima manda toda a impressão para a
impressora mais rápida e todo o acabamento para a máquina de acabamento
mais rápida; com elas, as máquinas são ocupadas da mais rápida para a mais
lenta, até cobrir a demanda. `build_problem` monta esse modelo como um
`simplex.Problem`.
"""

from collections.abc import Sequence

import numpy as np

from printing_company.problem.spec import (
    FinishingMachine,
    Portfolio,
    PrintingMachine,
)
from simplex import Constraint, Problem

__all__ = ["SHIFT_HOURS", "build_problem"]

SHIFT_HOURS = 8.0 + 2.0
"""Horas de um turno diário no artigo: 8 horas normais mais até 2 horas
extras. A capacidade de $d$ dias é `d * SHIFT_HOURS`."""


def build_problem(
    *,
    portfolio: Portfolio,
    printers: Sequence[PrintingMachine],
    finishings: Sequence[FinishingMachine],
    capacity: float | None = None,
) -> Problem:
    r"""Monta o modelo relaxado (veja o módulo) de tempo de operação.

    As variáveis são, nesta ordem, $z_m$ para cada impressora de
    `printers` e $w_n$ para cada máquina de acabamento de `finishings`, e
    levam os nomes das máquinas (`Machine.id`). O custo de cada uma é o
    tempo por metro, $1 / v$, em horas. As restrições são, nesta ordem,

    $$
    \begin{aligned}
    \sum_{m \in M} z_m &\geq \sum_{i \in I} D_i
       \quad \text{(impressão)}, \cr
    \sum_{n \in N} w_n &\geq \sum_{i \in F} D_i
       \quad \text{(acabamento)}, \cr
    z_m &\leq T v_m, \quad w_n \leq T v_n
       \quad \text{(capacidade, uma por máquina)},
    \end{aligned}
    $$

    com os lados direitos `Portfolio.total` e `Portfolio.with_finishing`.
    A capacidade $z_m / v_m \leq T$ é escrita em metros, $z_m \leq T v_m$,
    para que todos os coeficientes sejam 0 ou 1.

    **Argumentos:**

    - `portfolio`: a carteira de pedidos;
    - `printers`: as impressoras $m \in M$;
    - `finishings`: as máquinas de acabamento $n \in N$;
    - `capacity`: a capacidade $T$, em horas, de cada máquina no horizonte
      (por exemplo, `2 * SHIFT_HOURS` para dois dias). Com `None`, as
      restrições de capacidade não entram no modelo.

    **Levanta:** `ValueError` se `capacity` não for positiva.

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

    Com um turno de 3 horas, a `P1` imprime no máximo 31 500 m, e a `P2`
    faz o resto, 3 500 m. Os 15 000 m de acabamento levam
    $15\,000 / 7\,800 \approx 1{,}92$ h, então cabem na `F1`:

    >>> problem = build_problem(
    ...     portfolio=portfolio,
    ...     printers=[
    ...         PrintingMachine(id="P1", speed=10_500, setup=0.25, consumption=40),
    ...         PrintingMachine(id="P2", speed=3_000, setup=0.5, consumption=112),
    ...     ],
    ...     finishings=[
    ...         FinishingMachine(id="F1", speed=7_800, setup=0.5, consumption=40),
    ...     ],
    ...     capacity=3,
    ... )
    >>> [k.sense for k in problem.constraints]
    ['>=', '>=', '<=', '<=', '<=']
    >>> [round(x, 6) for x in problem.solve().x.tolist()]
    [31500.0, 3500.0, 15000.0]

    Com 2 horas, as impressoras só dão conta de
    $2 \cdot (10\,500 + 3\,000) = 27\,000$ m, e o problema fica inviável:

    >>> problem = build_problem(
    ...     portfolio=portfolio,
    ...     printers=[
    ...         PrintingMachine(id="P1", speed=10_500, setup=0.25, consumption=40),
    ...         PrintingMachine(id="P2", speed=3_000, setup=0.5, consumption=112),
    ...     ],
    ...     finishings=[
    ...         FinishingMachine(id="F1", speed=7_800, setup=0.5, consumption=40),
    ...     ],
    ...     capacity=2,
    ... )
    >>> problem.solve().status
    <Status.INFEASIBLE: 'infeasible'>

    Com os dados do artigo (`printing_company.problem.data`), na carteira
    I e sem capacidade, tudo vai para a `Print04` (12 600 m/h) e para a
    `Finish02` (12 000 m/h):

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

    Com dois dias de turno ($T = 20$ h), a `Print04` imprime
    $20 \cdot 12\,600 = 252\,000$ m, a `Print01` mais 210 000 m e a
    `Print05`, a terceira mais rápida, o resto. O acabamento ainda cabe
    todo na `Finish02`. O tempo total sobe de 61,85 h para 67,75 h, porque
    parte da impressão foi para máquinas mais lentas:

    >>> problem = build_problem(
    ...     portfolio=data.portfolios[0],
    ...     printers=data.printers,
    ...     finishings=data.finishers,
    ...     capacity=2 * SHIFT_HOURS,
    ... )
    >>> solution = problem.solve()
    >>> {
    ...     name: round(x, 6)
    ...     for name, x in zip(problem.variable_names, solution.x.tolist())
    ...     if x > 0
    ... }
    {'Print01': 210000.0, 'Print04': 252000.0, 'Print05': 81000.0, 'Finish02': 225000.0}
    >>> round(solution.objective, 4)
    67.75

    A capacidade precisa ser positiva:

    >>> build_problem(
    ...     portfolio=portfolio,
    ...     printers=data.printers,
    ...     finishings=data.finishers,
    ...     capacity=0,
    ... )
    Traceback (most recent call last):
        ...
    ValueError: capacity deve ser positiva, mas é 0.
    """
    if capacity is not None and capacity <= 0:
        raise ValueError(f"capacity deve ser positiva, mas é {capacity}.")

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

    # Capacidade: o tempo de produção z_m / v_m (ou w_n / v_n) de cada
    # máquina não passa de T horas. A restrição é escrita como
    # z_m <= T v_m, em metros, para que os coeficientes (1, e não 1 / v,
    # da ordem de 1e-4) fiquem na mesma escala das restrições de demanda.
    speeds = [machine.speed for machine in (*printers, *finishings)]
    capacity_constraints = (
        ()
        if capacity is None
        else tuple(
            Constraint(coefs=e_j, sense="<=", rhs=capacity * speed)
            for e_j, speed in zip(np.eye(len(c)), speeds, strict=True)
        )
    )

    return Problem(
        sense="min",
        c=c,
        constraints=(
            printer_constraint,
            finishing_constraint,
            *capacity_constraints,
        ),
        names=names,
    )
