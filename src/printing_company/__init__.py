from pathlib import Path

import click

from printing_company.settings import Settings

settings = Settings()


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
def main(data_dir: Path, skip: tuple[str, ...]) -> None:
    raise NotImplementedError


if __name__ == "__main__":
    main()
