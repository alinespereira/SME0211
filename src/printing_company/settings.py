"""Configurações do projeto, lidas de variáveis de ambiente pelo pydantic-settings."""

from pathlib import Path
from typing import Self

from pydantic import DirectoryPath, Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).parent.parent.parent.resolve()


class Settings(BaseSettings):
    """Configurações imutáveis do projeto.

    Atributos:
        root_dir: diretório raiz do projeto (onde ficam ``data/`` e ``docs/``).
    """

    model_config = SettingsConfigDict(
        frozen=True,
    )

    root_dir: DirectoryPath = Field(default=ROOT_DIR)

    @computed_field
    def data_dir(self: Self) -> DirectoryPath:
        return self.root_dir / "data"

    @computed_field
    def docs_dir(self: Self) -> DirectoryPath:
        return self.root_dir / "docs"
