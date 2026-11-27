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

**Exemplo:** a primeira carteira de pedidos do artigo.

>>> from printing_company.problem.data import portfolios, printers
>>> [p.id for p in printers]
['Print01', 'Print02', 'Print03', 'Print04', 'Print05']
>>> portfolios[1].label, len(portfolios[1].demands)
('Portfolio II', 20)
"""

import logging
import math

from rich.logging import RichHandler

from printing_company.problem.data import finishers, portfolios, printers
from printing_company.problem.model import (
    SHIFT_HOURS,
    build_problem,
    min_capacity,
)
from printing_company.settings import Settings
from simplex import PivotingRule, Solver

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, markup=True)],
)

logger = logging.getLogger(__name__)

settings = Settings()
"""Configurações do projeto, carregadas na importação."""


def main() -> None:
    """Ponto de entrada do comando `printing-company`: resolve as três
    carteiras do artigo, cada uma com o menor número de turnos diários
    (`SHIFT_HOURS`) que a torna viável (veja `min_capacity`)."""
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
        logger.info(problem.to_standard_form().initial_tableau(solver=solver))
        solution = problem.solve(solver=solver)
        logger.info(solution)


if __name__ == "__main__":
    main()
