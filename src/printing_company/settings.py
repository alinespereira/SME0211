"""Configurações do projeto, lidas de variáveis de ambiente pelo pydantic-settings."""

from pathlib import Path
from typing import Self

from pydantic import DirectoryPath, Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["ROOT_DIR", "Settings"]

ROOT_DIR = Path(__file__).parent.parent.parent.resolve()
"""Raiz do projeto (a pasta que contém `src/`)."""


class Settings(BaseSettings):
    """Configurações imutáveis do projeto.

    Os valores podem ser trocados por variáveis de ambiente (por exemplo,
    `ROOT_DIR`), como em todo `pydantic_settings.BaseSettings`.
    """

    model_config = SettingsConfigDict(
        frozen=True,
    )

    root_dir: DirectoryPath = Field(default=ROOT_DIR)
    """Diretório raiz do projeto, onde ficam `data/` e `docs/`."""

    @computed_field
    def data_dir(self: Self) -> DirectoryPath:
        """Pasta `data/` na raiz do projeto."""
        return self.root_dir / "data"

    @computed_field
    def docs_dir(self: Self) -> DirectoryPath:
        """Pasta `docs/` na raiz do projeto."""
        return self.root_dir / "docs"
