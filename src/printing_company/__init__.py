"""Modelo do problema da gráfica, baseado no artigo *Energy consumption
optimization in a printing company* (Gestão & Produção, 2024).

.. include:: ../../docs/modulos/printing_company.md
"""

import click
from rich.console import Console

from printing_company.problem.analysis import PortfolioResult, solve_portfolio
from printing_company.problem.data import finishers, portfolios, printers
from printing_company.problem.model import Objective
from printing_company.report import portfolio_report, summary_table
from simplex import configure_logging


@click.command()
@click.option(
    "--debug",
    is_flag=True,
    help=(
        "Mostra também o modelo de cada carteira e os logs de DEBUG, com o "
        "tableau de cada iteração do simplex (variável que entra, que sai "
        "e pivô em destaque)."
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
    "objectives",
    type=click.Choice(list(Objective), case_sensitive=False),
    multiple=True,
    default=[Objective.TIME.value],
    show_default=True,
    help=(
        "O que minimizar: o tempo de operação (time, soma das horas "
        "ligadas) ou o consumo de energia (energy, soma das potências "
        "vezes as horas). Pode ser repetida, como em `-o time -o energy`, "
        "para comparar os dois objetivos em cada carteira."
    ),
)
def main(
    *,
    debug: bool,
    phase_one: bool,
    selected: tuple[int, ...],
    objectives: tuple[Objective, ...],
) -> None:
    """Resolve as três carteiras de pedidos do artigo.

    Com `--portfolio`, resolve só as carteiras escolhidas (numeradas de 1
    a 3, na ordem do artigo). Com `--objective`, escolhe se minimiza o
    tempo de operação (padrão), o consumo de energia ou, repetindo a
    opção, os dois, um depois do outro. Cada carteira é
    resolvida com o menor número de turnos diários que a torna viável;
    para cada uma, mostra as horas, o tempo real (com setup), a energia
    de cada máquina e o custo. As horas de um turno vêm da variável de
    ambiente SHIFT_HOURS (padrão: 10).
    """
    # A docstring acima é a ajuda do comando (`printing-company --help`).
    # Veja `printing_company.problem.analysis.solve_portfolio` e
    # `printing_company.report`.
    configure_logging(debug=debug, phase_one=phase_one)
    console = Console()
    chosen = sorted(set(selected)) or range(1, len(portfolios) + 1)
    results: list[PortfolioResult] = []
    # Sem repetir objetivos e na ordem de `Objective` (tempo, energia).
    chosen_objectives = [o for o in Objective if o in objectives]
    for k in chosen:
        for objective in chosen_objectives:
            result = solve_portfolio(
                portfolio=portfolios[k - 1],
                printers=printers,
                finishings=finishers,
                objective=objective,
            )
            console.print()
            console.print(portfolio_report(result=result))
            results.append(result)
    if len(results) > 1:
        console.print()
        console.print(summary_table(results=results))


if __name__ == "__main__":
    main()
