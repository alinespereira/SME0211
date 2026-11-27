r"""Configurações do projeto, lidas de variáveis de ambiente pelo
pydantic-settings.

Ficam aqui os **parâmetros do cenário** do artigo, que descrevem a
operação da gráfica e que faz sentido trocar sem mexer no código: as horas
de um turno (`Settings.shift_hours`) e a tarifa de energia
(`Settings.energy_price`). Os detalhes numéricos não ficam aqui: a
tolerância e o limite de iterações do simplex são do pacote `simplex`
(`simplex.defaults`), que não depende de `printing_company`, e a escala
das restrições de demanda (`printing_company.problem.model.SCALE`) é
parte da formulação do modelo.

O objeto `settings` é carregado na importação e usado em todo o pacote.
Para mudar um valor, defina a variável de ambiente com o nome do campo
(em maiúsculas ou minúsculas):

```sh
SHIFT_HOURS=8 uv run printing-company   # turnos sem horas extras
```

>>> Settings(shift_hours=8).shift_hours
8.0
>>> Settings(energy_price=0)  # doctest: +ELLIPSIS
Traceback (most recent call last):
    ...
pydantic_core._pydantic_core.ValidationError: 1 validation error for Settings
energy_price
  Input should be greater than 0 ...
"""

from pathlib import Path
from typing import Self

from pydantic import DirectoryPath, Field, PositiveFloat, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["ROOT_DIR", "Settings", "settings"]

ROOT_DIR = Path(__file__).parent.parent.parent.resolve()
"""Raiz do projeto (a pasta que contém `src/`)."""


class Settings(BaseSettings):
    """Configurações imutáveis do projeto.

    Os valores podem ser trocados por variáveis de ambiente (por exemplo,
    `ROOT_DIR` ou `SHIFT_HOURS`), como em todo
    `pydantic_settings.BaseSettings`.
    """

    model_config = SettingsConfigDict(
        frozen=True,
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
