"""Configurações do projeto, lidas de variáveis de ambiente pelo
pydantic-settings.

.. include:: ../../docs/modulos/printing_company.settings.md
"""

from pathlib import Path
from typing import Self

from pydantic import DirectoryPath, Field, PositiveFloat, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["ENV_FILE", "ROOT_DIR", "Settings", "settings"]

ROOT_DIR = Path(__file__).parent.parent.parent.resolve()
"""Raiz do projeto (a pasta que contém `src/`)."""

ENV_FILE = ROOT_DIR / ".env"
"""Arquivo `.env` lido por `Settings`, na raiz do projeto (e não na pasta
de onde o comando é chamado). Se não existir, é ignorado."""


class Settings(BaseSettings):
    """Configurações imutáveis do projeto (veja o módulo)."""

    model_config = SettingsConfigDict(
        frozen=True,
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    root_dir: DirectoryPath = Field(default=ROOT_DIR)
    """Diretório raiz do projeto, onde ficam `data/` e `docs/`."""

    shift_hours: PositiveFloat = 8.0 + 2.0
    r"""Horas de um turno diário no artigo: 8 horas normais mais até 2
    horas extras. A capacidade $T$ de $d$ dias é `d * shift_hours`."""

    energy_price: PositiveFloat = 0.86
    r"""Tarifa de energia $c$ do artigo, em reais por kWh (horário fora de
    ponta)."""

    @computed_field
    def data_dir(self: Self) -> DirectoryPath:
        """Pasta `data/` na raiz do projeto."""
        return self.root_dir / "data"

    @computed_field
    def docs_dir(self: Self) -> DirectoryPath:
        """Pasta `docs/` na raiz do projeto."""
        return self.root_dir / "docs"


settings = Settings()
"""Configurações do projeto, carregadas na importação."""
