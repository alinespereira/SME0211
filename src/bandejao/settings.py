"""Configurações do projeto, lidas de variáveis de ambiente pelo pydantic-settings."""

from pathlib import Path

from pydantic import DirectoryPath, Field
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
