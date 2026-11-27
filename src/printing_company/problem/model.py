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

**Variáveis em horas.** Em vez dos metros $z_m$ e $w_n$, as variáveis são
as horas que cada máquina fica ligada,

$$
t_m = T_{im} z_m = \frac{z_m}{v_m}, \quad m \in M, \qquad
t_n = \frac{w_n}{v_n}, \quad n \in N.
$$

É só uma mudança de escala de cada variável ($z_m = v_m t_m$, com
$v_m > 0$), então os dois modelos têm as mesmas soluções, e a função
objetivo passa a ser a soma das horas. Somando (4) em $i \in I$ e (5) em
$i \in F$, o modelo fica

$$
\begin{aligned}
\min \quad & \sum_{m \in M} t_m + \sum_{n \in N} t_n \cr
\text{s.a.} \quad & \sum_{m \in M} v_m t_m \geq \sum_{i \in I} D_i, \cr
& \sum_{n \in N} v_n t_n \geq \sum_{i \in F} D_i, \cr
& t_m \leq T, \quad m \in M, \cr
& t_n \leq T, \quad n \in N, \cr
& t \geq 0,
\end{aligned}
$$

com $t$ em horas e $v$ em metros por hora. As restrições de demanda são
escritas com $\geq$, mas, como os custos são positivos, no ótimo elas
valem com igualdade, como as restrições (4) e (5) do artigo. Para que os
coeficientes fiquem na mesma escala que os custos (1) e as capacidades
($T$, dezenas de horas), as restrições de demanda são divididas por
`SCALE` = 1 000: velocidades em milhares de metros por hora e demandas em
milhares de metros.

O problema é viável se, e só se, as máquinas dão conta da demanda no
horizonte: $T \sum_m v_m \geq \sum_{i \in I} D_i$ e
$T \sum_n v_n \geq \sum_{i \in F} D_i$ (veja `min_capacity`). Sem as
capacidades (`capacity=None`), a solução ótima liga só a impressora mais
rápida e a máquina de acabamento mais rápida; com elas, as máquinas são
ligadas da mais rápida para a mais lenta, até cobrir a demanda.
`build_problem` monta esse modelo como um `simplex.Problem`.
"""

from collections.abc import Sequence

import numpy as np

from printing_company.problem.spec import (
    FinishingMachine,
    Portfolio,
    PrintingMachine,
)
from simplex import Constraint, Problem

__all__ = ["SCALE", "SHIFT_HOURS", "build_problem", "min_capacity"]

SHIFT_HOURS = 8.0 + 2.0
"""Horas de um turno diário no artigo: 8 horas normais mais até 2 horas
extras. A capacidade de $d$ dias é `d * SHIFT_HOURS`."""

SCALE = 1_000.0
"""Escala das restrições de demanda: velocidades e demandas entram no
modelo em milhares de metros (por hora)."""


def build_problem(
    *,
    portfolio: Portfolio,
    printers: Sequence[PrintingMachine],
    finishings: Sequence[FinishingMachine],
    capacity: float | None = None,
) -> Problem:
    r"""Monta o modelo relaxado (veja o módulo) de tempo de operação.

    As variáveis são, nesta ordem, as horas $t_m$ de cada impressora de
    `printers` e $t_n$ de cada máquina de acabamento de `finishings`, e
    levam os nomes das máquinas (`Machine.id`). Todos os custos são 1: o
    objetivo é o total de horas ligadas. As restrições são, nesta ordem,

    $$
    \begin{aligned}
    \sum_{m \in M} \frac{v_m}{1000} t_m &\geq
       \frac{1}{1000} \sum_{i \in I} D_i
       \quad \text{(impressão)}, \cr
    \sum_{n \in N} \frac{v_n}{1000} t_n &\geq
       \frac{1}{1000} \sum_{i \in F} D_i
       \quad \text{(acabamento)}, \cr
    t_m &\leq T, \quad t_n \leq T
       \quad \text{(capacidade, uma por máquina)},
    \end{aligned}
    $$

    com as demandas `Portfolio.total` e `Portfolio.with_finishing`
    divididas por `SCALE`. A quantidade produzida por uma máquina, em
    metros, é $v t$.

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
    >>> printers = [
    ...     PrintingMachine(id="P1", speed=10_500, setup=0.25, consumption=40),
    ...     PrintingMachine(id="P2", speed=3_000, setup=0.5, consumption=112),
    ... ]
    >>> finishings = [
    ...     FinishingMachine(id="F1", speed=7_800, setup=0.5, consumption=40),
    ... ]
    >>> problem = build_problem(
    ...     portfolio=portfolio, printers=printers, finishings=finishings
    ... )
    >>> problem.variable_names
    ('P1', 'P2', 'F1')
    >>> problem.c.tolist()
    [1.0, 1.0, 1.0]
    >>> [k.coefs.tolist() for k in problem.constraints]  # mil m/h
    [[10.5, 3.0, 0.0], [0.0, 0.0, 7.8]]
    >>> [k.rhs for k in problem.constraints]  # mil m
    [35.0, 15.0]

    Os 35 000 m vão para a impressora mais rápida, ligada por
    $35\,000 / 10\,500 \approx 3{,}33$ h, e os 15 000 m de acabamento,
    para a única máquina de acabamento, por $15\,000 / 7\,800 \approx
    1{,}92$ h:

    >>> solution = problem.solve()
    >>> [round(t, 4) for t in solution.x.tolist()]  # horas
    [3.3333, 0.0, 1.9231]
    >>> round(solution.objective, 4)
    5.2564

    Com um turno de 3 horas, a `P1` fica ligada as 3 horas e imprime
    31 500 m; a `P2` imprime o resto, 3 500 m, em $3\,500 / 3\,000
    \approx 1{,}17$ h. O acabamento cabe nas 3 horas da `F1`:

    >>> problem = build_problem(
    ...     portfolio=portfolio,
    ...     printers=printers,
    ...     finishings=finishings,
    ...     capacity=3,
    ... )
    >>> [k.sense for k in problem.constraints]
    ['>=', '>=', '<=', '<=', '<=']
    >>> [round(t, 4) for t in problem.solve().x.tolist()]
    [3.0, 1.1667, 1.9231]

    Com 2 horas, as impressoras só dão conta de
    $2 \cdot (10\,500 + 3\,000) = 27\,000$ m, e o problema fica inviável:

    >>> build_problem(
    ...     portfolio=portfolio,
    ...     printers=printers,
    ...     finishings=finishings,
    ...     capacity=2,
    ... ).solve().status
    <Status.INFEASIBLE: 'infeasible'>

    Com os dados do artigo (`printing_company.problem.data`), na carteira
    I e sem capacidade, só a `Print04` (12 600 m/h) e a `Finish02`
    (12 000 m/h) ficam ligadas:

    >>> from printing_company.problem import data
    >>> problem = build_problem(
    ...     portfolio=data.portfolios[0],
    ...     printers=data.printers,
    ...     finishings=data.finishers,
    ... )
    >>> solution = problem.solve()
    >>> {
    ...     name: round(t, 4)
    ...     for name, t in zip(problem.variable_names, solution.x.tolist())
    ...     if t > 0
    ... }
    {'Print04': 43.0952, 'Finish02': 18.75}
    >>> round(solution.objective, 4)
    61.8452

    Com dois dias de turno ($T = 20$ h), a `Print04` e a `Print01` ficam
    ligadas as 20 horas, e a `Print05`, a terceira mais rápida, imprime o
    resto (81 000 m) em 9 horas. O acabamento ainda cabe todo na
    `Finish02`. O tempo total sobe de 61,85 h para 67,75 h, porque parte
    da impressão foi para máquinas mais lentas:

    >>> problem = build_problem(
    ...     portfolio=data.portfolios[0],
    ...     printers=data.printers,
    ...     finishings=data.finishers,
    ...     capacity=2 * SHIFT_HOURS,
    ... )
    >>> solution = problem.solve()
    >>> {
    ...     name: round(t, 4)
    ...     for name, t in zip(problem.variable_names, solution.x.tolist())
    ...     if t > 0
    ... }
    {'Print01': 20.0, 'Print04': 20.0, 'Print05': 9.0, 'Finish02': 18.75}
    >>> round(solution.objective, 4)
    67.75

    A capacidade precisa ser positiva:

    >>> build_problem(
    ...     portfolio=portfolio,
    ...     printers=printers,
    ...     finishings=finishings,
    ...     capacity=0,
    ... )
    Traceback (most recent call last):
        ...
    ValueError: capacity deve ser positiva, mas é 0.
    """
    if capacity is not None and capacity <= 0:
        raise ValueError(f"capacity deve ser positiva, mas é {capacity}.")

    machines = (*printers, *finishings)
    names = tuple(machine.id for machine in machines)

    # Custo 1 para cada variável: o objetivo é a soma das horas ligadas.
    c = np.ones(len(machines), dtype=np.float64)

    # Velocidades em milhares de metros por hora. Só as impressoras
    # imprimem e só as máquinas de acabamento acabam: cada restrição de
    # demanda tem coeficiente 0 nas máquinas do outro tipo.
    speeds = np.array([m.speed for m in machines], dtype=np.float64) / SCALE
    is_printer = np.array(
        [1.0] * len(printers) + [0.0] * len(finishings),
        dtype=np.float64,
    )

    printer_constraint = Constraint(
        coefs=speeds * is_printer,
        sense=">=",
        rhs=portfolio.total / SCALE,
    )
    finishing_constraint = Constraint(
        coefs=speeds * (1.0 - is_printer),
        sense=">=",
        rhs=portfolio.with_finishing / SCALE,
    )

    # Capacidade: cada máquina fica ligada no máximo T horas.
    capacity_constraints = (
        ()
        if capacity is None
        else tuple(
            Constraint(coefs=e_j, sense="<=", rhs=capacity)
            for e_j in np.eye(len(machines))
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


def min_capacity(
    *,
    portfolio: Portfolio,
    printers: Sequence[PrintingMachine],
    finishings: Sequence[FinishingMachine],
) -> float:
    r"""Menor capacidade $T$, em horas, para a qual o modelo é viável.

    Com todas as máquinas trabalhando $T$ horas, as impressoras produzem
    $T \sum_m v_m$ metros e as máquinas de acabamento, $T \sum_n v_n$.
    Então o modelo de `build_problem` é viável se, e só se,

    $$
    T \geq T_{\min} = \max\left(
        \frac{\sum_{i \in I} D_i}{\sum_{m \in M} v_m},
        \frac{\sum_{i \in F} D_i}{\sum_{n \in N} v_n}
    \right).
    $$

    **Exemplo:** na carteira I do artigo, as impressoras juntas fazem
    42 900 m/h, e os 543 000 m levam pelo menos 12,66 h. Um único turno
    (`SHIFT_HOURS`, 10 h) não basta; dois bastam.

    >>> from printing_company.problem import data
    >>> [
    ...     round(
    ...         min_capacity(
    ...             portfolio=portfolio,
    ...             printers=data.printers,
    ...             finishings=data.finishers,
    ...         ),
    ...         2,
    ...     )
    ...     for portfolio in data.portfolios
    ... ]
    [12.66, 27.11, 60.85]
    >>> import math
    >>> math.ceil(12.66 / SHIFT_HOURS)  # turnos diários para a carteira I
    2
    """
    printing = portfolio.total / sum(printer.speed for printer in printers)
    finishing = (
        portfolio.with_finishing / sum(f.speed for f in finishings)
        if portfolio.with_finishing > 0
        else 0.0
    )
    return max(printing, finishing)
