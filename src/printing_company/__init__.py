r"""Modelo do problema da gráfica, baseado no artigo *Energy consumption
optimization in a printing company* (Gestão & Produção, 2024).

A gráfica recebe uma carteira de pedidos e precisa decidir quantos metros
de cada item $i \in I$ produzir em cada máquina de impressão $m \in M$ e,
para os itens que exigem acabamento ($i \in F$), em cada máquina de
acabamento $n \in N$. O trabalho usa uma versão relaxada (contínua) do
modelo do artigo, focada no tempo de impressão, resolvida com o pacote
`simplex`.

**Módulos:**

- `printing_company.problem`: os dados do problema (máquinas e carteiras
  de pedidos), em `printing_company.problem.spec`, e as instâncias do
  artigo, em `printing_company.problem.data`;
- `printing_company.settings`: caminhos do projeto.

**Comando:** `printing-company` (a função `main`) resolve as três
carteiras do artigo. Com `--debug`, mostra também o tableau de cada
iteração do simplex, com a variável que entra, a que sai e o pivô em
destaque (veja `simplex.display`):

```sh
uv run printing-company --debug
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
    build_problem,
    min_capacity,
)
from printing_company.settings import Settings
from simplex import PivotingRule, Solver, configure_logging

logger = logging.getLogger(__name__)

settings = Settings()
"""Configurações do projeto, carregadas na importação."""


@click.command()
@click.option(
    "--debug",
    is_flag=True,
    help=(
        "Mostra os logs de DEBUG, com o tableau de cada iteração do "
        "simplex (variável que entra, que sai e pivô em destaque)."
    ),
)
def main(*, debug: bool) -> None:
    """Resolve as três carteiras de pedidos do artigo.

    Cada carteira é resolvida com o menor número de turnos diários que a
    torna viável; para cada uma, mostra o tempo real (com setup), o
    consumo e o custo de energia.
    """
    # A docstring acima é a ajuda do comando (`printing-company --help`).
    # Veja `SHIFT_HOURS`, `min_capacity` e `printing_company.problem.analysis`.
    configure_logging(debug=debug)
    for portfolio in portfolios:
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
        )
        logger.info(f">>> {portfolio.label}: {days} turnos")
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
