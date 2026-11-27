"""Configuração do pytest comum a todos os testes."""

import logging
from collections.abc import Iterator

import pytest
from rich.logging import RichHandler


@pytest.fixture(autouse=True, scope="session")
def _quiet_rich_handler() -> Iterator[None]:
    """Silencia o `RichHandler` de `simplex` durante os testes.

    O pytest baixa o nível do logger raiz para DEBUG (por causa do
    `log_file_level` do pytest.ini), e o `RichHandler` passaria a escrever
    os logs de DEBUG na saída padrão, que alguns testes comparam com a
    saída esperada. O log completo continua indo para `log/tests.log`.
    """
    handlers = [
        h for h in logging.getLogger().handlers if isinstance(h, RichHandler)
    ]
    levels = [h.level for h in handlers]
    for h in handlers:
        h.setLevel(logging.WARNING)
    yield
    for h, level in zip(handlers, levels, strict=True):
        h.setLevel(level)
