"""Configurações do projeto, lidas de variáveis de ambiente pelo
pydantic-settings.

.. include:: ../../docs/modulos/printing_company.settings.md
"""

from pathlib import Path
from typing import Self

from pydantic import DirectoryPath, Field, PositiveFloat, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["Settings", "settings"]

# Privados e sem docstring: são caminhos absolutos, calculados na
# importação, e não devem aparecer na documentação.
_ROOT_DIR = Path(__file__).parent.parent.parent.resolve()
_ENV_FILE = _ROOT_DIR / ".env"


class Settings(BaseSettings):
    """Configurações imutáveis do projeto (veja o módulo)."""

    model_config = SettingsConfigDict(
        frozen=True,
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    root_dir: DirectoryPath = Field(
        default_factory=lambda: _ROOT_DIR,
        repr=False,
    )
    """Diretório raiz do projeto (a pasta que contém `src/`), onde ficam
    `data/`, `docs/` e o `.env`. O padrão é calculado a partir da
    localização do pacote. Fica fora do `repr`, como os caminhos abaixo,
    para que o caminho absoluto não apareça na documentação."""

    shift_hours: PositiveFloat = 8.0 + 2.0
    r"""Horas de um turno diário no artigo: 8 horas normais mais até 2
    horas extras. A capacidade $T$ de $d$ dias é `d * shift_hours`."""

    energy_price: PositiveFloat = 0.86
    r"""Tarifa de energia $c$ do artigo, em reais por kWh (horário fora de
    ponta)."""

    @computed_field(repr=False)
    def data_dir(self: Self) -> DirectoryPath:
        """Pasta `data/` na raiz do projeto."""
        return self.root_dir / "data"

    @computed_field(repr=False)
    def docs_dir(self: Self) -> DirectoryPath:
        """Pasta `docs/` na raiz do projeto."""
        return self.root_dir / "docs"


settings = Settings()
"""Configurações do projeto, carregadas na importação."""
