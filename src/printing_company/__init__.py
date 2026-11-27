r"""Modelo do problema da gráfica, baseado no artigo *Energy consumption
optimization in a printing company* (Gestão & Produção, 2024).

A gráfica recebe uma carteira de pedidos e precisa decidir quantos metros
de cada item $i \in I$ produzir em cada máquina de impressão $m \in M$ e,
para os itens que exigem acabamento ($i \in F$), em cada máquina de
acabamento $n \in N$. O trabalho usa uma versão relaxada (contínua) do
modelo do artigo, resolvida com o pacote `simplex`, que minimiza o tempo
de operação das máquinas ou o consumo de energia (veja
`printing_company.problem.model.Objective`).

**Módulos:**

- `printing_company.problem`: os dados do problema (máquinas e carteiras
  de pedidos), em `printing_company.problem.spec`, e as instâncias do
  artigo, em `printing_company.problem.data`;
- `printing_company.settings`: caminhos do projeto.

**Comando:** `printing-company` (a função `main`) resolve as três
carteiras do artigo. Com `--debug`, mostra também o tableau de cada
iteração do simplex, com a variável que entra, a que sai e o pivô em
destaque (veja `simplex.display`). Os tableaux da Fase 1 só aparecem com
`--phase-one`. Com `--objective energy`, minimiza o consumo de energia
em vez do tempo:

```sh
uv run printing-company --debug              # as três carteiras
uv run printing-company --debug --portfolio 2  # só a Portfolio II
uv run printing-company --debug --phase-one    # inclui a Fase 1
uv run printing-company --objective energy     # minimiza a energia
```

**Exemplo:** a primeira carteira de pedidos do artigo.

>>> from printing_company.problem.data import portfolios, printers
>>> [p.id for p in printers]
['Print01', 'Print02', 'Print03', 'Print04', 'Print05']
>>> portfolios[1].label, len(portfolios[1].demands)
('Portfolio II', 20)
"""

import logging
import math

import click

from printing_company.problem.analysis import (
    energy_consumption,
    energy_cost,
    operating_times,
)
from printing_company.problem.data import finishers, portfolios, printers
from printing_company.problem.model import (
    SHIFT_HOURS,
    Objective,
    build_problem,
    min_capacity,
)
from printing_company.settings import Settings
from simplex import PivotingRule, Solver, configure_logging

logger = logging.getLogger(__name__)

settings = Settings()
"""Configurações do projeto, carregadas na importação."""

objective_label = {Objective.TIME: "tempo", Objective.ENERGY: "energia"}
"""Nome de cada objetivo nos logs do comando."""


@click.command()
@click.option(
    "--debug",
    is_flag=True,
    help=(
        "Mostra os logs de DEBUG, com o tableau de cada iteração do "
        "simplex (variável que entra, que sai e pivô em destaque)."
    ),
)
@click.option(
    "--phase-one",
    is_flag=True,
    help="Com --debug, mostra também os tableaux da Fase 1.",
)
@click.option(
    "-p",
    "--portfolio",
    "selected",
    type=click.IntRange(1, len(portfolios)),
    multiple=True,
    help=(
        f"Número da carteira a resolver (de 1 a {len(portfolios)}); pode "
        "ser repetida, como em `-p 1 -p 3`. Sem ela, resolve todas."
    ),
)
@click.option(
    "-o",
    "--objective",
    type=click.Choice(list(Objective), case_sensitive=False),
    default=Objective.TIME.value,
    show_default=True,
    help=(
        "O que minimizar: o tempo de operação (time, soma das horas "
        "ligadas) ou o consumo de energia (energy, soma das potências "
        "vezes as horas)."
    ),
)
def main(
    *,
    debug: bool,
    phase_one: bool,
    selected: tuple[int, ...],
    objective: Objective,
) -> None:
    """Resolve as três carteiras de pedidos do artigo.

    Com `--portfolio`, resolve só as carteiras escolhidas (numeradas de 1
    a 3, na ordem do artigo). Com `--objective`, escolhe se minimiza o
    tempo de operação (padrão) ou o consumo de energia. Cada carteira é
    resolvida com o menor número de turnos diários que a torna viável;
    para cada uma, mostra o tempo real (com setup), o consumo e o custo
    de energia.
    """
    # A docstring acima é a ajuda do comando (`printing-company --help`).
    # Veja `SHIFT_HOURS`, `min_capacity` e `printing_company.problem.analysis`.
    configure_logging(debug=debug, phase_one=phase_one)
    chosen = sorted(set(selected)) or range(1, len(portfolios) + 1)
    for portfolio in (portfolios[k - 1] for k in chosen):
        days = math.ceil(
            min_capacity(
                portfolio=portfolio,
                printers=printers,
                finishings=finishers,
            )
            / SHIFT_HOURS
        )
        problem = build_problem(
            portfolio=portfolio,
            printers=printers,
            finishings=finishers,
            capacity=days * SHIFT_HOURS,
            objective=objective,
        )
        logger.info(
            f">>> {portfolio.label}: {days} turnos, "
            f"objetivo: {objective_label[objective]}"
        )
        logger.info(problem)
        solver = Solver(rule=PivotingRule.LEXICOGRAPHIC)
        solution = problem.solve(solver=solver)
        logger.info(solution.model_dump(exclude={"result"}))
        if solution.x is None:
            continue
        machines = [*printers, *finishers]
        hours = dict(
            zip(problem.variable_names, solution.x.tolist(), strict=True)
        )
        times = operating_times(hours=hours, machines=machines)
        energy = energy_consumption(times=times, machines=machines)
        logger.info(
            {name: round(tau, 2) for name, tau in times.items() if tau > 0}
        )
        logger.info(
            f"Tempo real: {sum(times.values()):.2f} h; "
            f"energia: {sum(energy.values()):.2f} kWh; "
            f"custo: R$ {energy_cost(energy=energy):.2f}"
        )


if __name__ == "__main__":
    main()
