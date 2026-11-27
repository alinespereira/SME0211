r"""Configuração do `logging` dos pacotes `simplex` e `printing_company`.

As mensagens vão para o terminal pelo `RichHandler` do `rich`. Para que o
tableau (veja `simplex.display`) apareça colorido no terminal e, ao mesmo
tempo, legível num arquivo de log, o `simplex.solver.Solver` registra o
título e o tableau em texto puro como mensagem e o tableau colorido (um
`rich.text.Text`) no atributo `RICH_TEXT` do registro (com `extra=`); o
`Handler` deste módulo mostra o título na linha de log e o tableau
colorido logo abaixo, e os demais handlers (por exemplo, o arquivo de log
do pytest) usam a mensagem pura.
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
    """`RichHandler` que mostra, abaixo da linha de log, a versão colorida
    da mensagem, quando o registro tem uma (no atributo `RICH_TEXT`).

    A linha de log mostra só a primeira linha da mensagem (o título); o
    texto colorido vem logo abaixo, fora da coluna de mensagens do
    `RichHandler` e sem quebra de linha, para que um tableau largo não
    seja picotado (alargue o terminal para vê-lo inteiro).

    **Exemplo:**

    >>> import io
    >>> from rich.console import Console
    >>> out = io.StringIO()
    >>> handler = Handler(
    ...     console=Console(file=out, width=60),
    ...     show_time=False,
    ...     show_path=False,
    ... )
    >>> record = logging.makeLogRecord(
    ...     {
    ...         "msg": "Título\\ntexto puro",
    ...         "levelname": "DEBUG",
    ...         RICH_TEXT: Text("texto colorido", style="red"),
    ...     }
    ... )
    >>> handler.emit(record)
    >>> for line in out.getvalue().splitlines():
    ...     print(line.rstrip())
    DEBUG    Título
    texto colorido
    """

    def render_message(
        self: Self, record: logging.LogRecord, message: str
    ) -> ConsoleRenderable:
        """Se o registro tem `RICH_TEXT`, usa só a primeira linha de
        `message`; senão, faz como o `RichHandler`."""
        if isinstance(getattr(record, RICH_TEXT, None), Text):
            message = message.split("\n", maxsplit=1)[0]
        return super().render_message(record, message)

    def emit(self: Self, record: logging.LogRecord) -> None:
        """Emite o registro como o `RichHandler` e, se ele tiver
        `RICH_TEXT`, imprime o texto colorido logo abaixo."""
        super().emit(record)
        text = getattr(record, RICH_TEXT, None)
        if isinstance(text, Text):
            self.console.print(text, soft_wrap=True, crop=False)


def configure_logging(*, debug: bool = False, phase_one: bool = False) -> None:
    """Configura o logger raiz: nível DEBUG se `debug`, senão INFO, e um
    `Handler` para o terminal (só se ainda não houver um).

    Com `debug`, o `simplex.solver.Solver` mostra o tableau de cada
    iteração da Fase 2, com a variável que entra, a que sai e o pivô em
    destaque. Os tableaux da Fase 1 (logger `PHASE_ONE_LOGGER`) só
    aparecem se `phase_one` também for verdadeiro.

    **Parâmetros:**

    - `debug`: mostra os logs de DEBUG.
    - `phase_one`: com `debug`, mostra também os tableaux da Fase 1.
    """
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if debug else logging.INFO)
    logging.getLogger(PHASE_ONE_LOGGER).setLevel(
        logging.NOTSET if phase_one else logging.INFO
    )
    if not any(isinstance(h, Handler) for h in root.handlers):
        handler = Handler(rich_tracebacks=True, markup=True)
        handler.setFormatter(logging.Formatter("%(message)s", datefmt="[%X]"))
        root.addHandler(handler)
