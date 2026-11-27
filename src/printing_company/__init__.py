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

from pathlib import Path

import click

from printing_company.settings import Settings

settings = Settings()
"""Configurações do projeto, carregadas na importação."""


@click.command(help="Resolve o PL da dieta do almoço e imprime o resultado.")
@click.option(
    "--data-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=settings.data_dir,
    show_default="data/ na raiz do projeto",
    help="Pasta com os CSVs.",
)
@click.option(
    "--skip",
    multiple=True,
    metavar="NUTRIENTE",
    help="Nutriente a retirar das restrições (ex.: calcio). Pode repetir.",
)
def main(*, data_dir: Path, skip: tuple[str, ...]) -> None:
    """Ponto de entrada do comando `printing-company` (ainda não
    implementado)."""
    raise NotImplementedError


if __name__ == "__main__":
    main()
