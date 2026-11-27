"""Testes de `simplex.logs`: o `Handler` com o texto colorido."""

import io
import logging

from rich.console import Console
from rich.text import Text

from simplex.logs import RICH_TEXT, Handler


def test_handler_prints_rich_text_below_title() -> None:
    out = io.StringIO()
    handler = Handler(
        console=Console(file=out, width=60),
        show_time=False,
        show_path=False,
    )
    record = logging.makeLogRecord(
        {
            "msg": "Título\ntexto puro",
            "levelname": "DEBUG",
            RICH_TEXT: Text("texto colorido", style="red"),
        }
    )
    handler.emit(record)
    lines = [line.rstrip() for line in out.getvalue().splitlines()]
    assert lines == ["DEBUG    Título", "texto colorido"]
