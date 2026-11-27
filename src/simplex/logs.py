"""Configuração do `logging` dos pacotes `simplex` e `printing_company`.

.. include:: ../../docs/modulos/simplex.logs.md
"""

import logging
from typing import Self

from rich.console import ConsoleRenderable
from rich.logging import RichHandler
from rich.text import Text

__all__ = ["PHASE_ONE_LOGGER", "RICH_TEXT", "Handler", "configure_logging"]

PHASE_ONE_LOGGER = "simplex.solver.phase_one"
"""Nome do logger dos tableaux da Fase 1 (veja
`simplex.problem.StandardForm.initial_tableau`). Como é filho de
`simplex.solver`, segue o mesmo nível, a menos que se mude o dele."""

RICH_TEXT = "rich_text"
"""Nome do atributo do `logging.LogRecord` com a versão colorida da
mensagem (um `rich.text.Text`)."""


class Handler(RichHandler):
    """`RichHandler` que mostra o texto colorido (`RICH_TEXT`) abaixo da
    linha de log.
    """

    def render_message(
        self: Self, record: logging.LogRecord, message: str
    ) -> ConsoleRenderable:
        """Com `RICH_TEXT`, mostra só a primeira linha de `message`."""
        if isinstance(getattr(record, RICH_TEXT, None), Text):
            message = message.split("\n", maxsplit=1)[0]
        return super().render_message(record, message)

    def emit(self: Self, record: logging.LogRecord) -> None:
        """Emite o registro e, se ele tiver `RICH_TEXT`, o texto colorido."""
        super().emit(record)
        text = getattr(record, RICH_TEXT, None)
        if isinstance(text, Text):
            self.console.print(text, soft_wrap=True, crop=False)


def configure_logging(*, debug: bool = False, phase_one: bool = False) -> None:
    """Configura o logger raiz e o da Fase 1 (veja o módulo)."""
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if debug else logging.INFO)
    logging.getLogger(PHASE_ONE_LOGGER).setLevel(
        logging.NOTSET if phase_one else logging.INFO
    )
    if not any(isinstance(h, Handler) for h in root.handlers):
        handler = Handler(rich_tracebacks=True, markup=True)
        handler.setFormatter(logging.Formatter("%(message)s", datefmt="[%X]"))
        root.addHandler(handler)
