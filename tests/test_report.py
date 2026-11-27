"""Testes de `printing_company.report`: as tabelas da saída do comando."""

import io

import pytest
from rich.console import Console, RenderableType

from printing_company.problem import data
from printing_company.problem.analysis import solve_portfolio
from printing_company.report import format_br, portfolio_report, summary_table


@pytest.mark.parametrize(
    ("value", "digits", "text"),
    [(3498.4321, 2, "3.498,43"), (543_000, 0, "543.000"), (-0.001, 2, "0,00")],
)
def test_format_br(value: float, digits: int, text: str) -> None:
    assert format_br(value=value, digits=digits) == text


def render(renderable: RenderableType) -> list[str]:
    """As linhas do texto que o `rich` mostraria num terminal de 88
    colunas."""
    out = io.StringIO()
    Console(file=out, width=88).print(renderable)
    return [line.rstrip() for line in out.getvalue().splitlines()]


def test_portfolio_report() -> None:
    """A carteira I do artigo, minimizando o tempo."""
    result = solve_portfolio(
        portfolio=data.portfolios[0],
        printers=data.printers,
        finishings=data.finishers,
    )
    assert render(portfolio_report(result=result)) == [
        "──────────────────────────── Portfolio I · objetivo: tempo ─────────────────────────────",
        "10 itens · impressão: 543.000 m · acabamento: 225.000 m (5 itens)",
        "Horizonte: 2 turnos de 10 h, T = 20 h por máquina",
        "┏━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━┳━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━┓",
        "┃ Máquina  ┃ v (m/h) ┃ t (h) ┃  uso ┃ τ (h) ┃ produção (m) ┃    kW ┃  E (kWh) ┃",
        "┡━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━╇━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━┩",
        "│ Print01  │  10.500 │ 20,00 │ 100% │ 20,25 │      210.000 │  40,0 │   810,00 │",
        "│ Print02  │   3.000 │     — │    — │     — │            — │ 112,0 │        — │",
        "│ Print03  │   7.800 │     — │    — │     — │            — │  49,2 │        — │",
        "│ Print04  │  12.600 │ 20,00 │ 100% │ 20,17 │      252.000 │  24,0 │   484,08 │",
        "│ Print05  │   9.000 │  9,00 │  45% │  9,25 │       81.000 │   2,2 │    20,35 │",
        "├──────────┼─────────┼───────┼──────┼───────┼──────────────┼───────┼──────────┤",
        "│ Finish01 │   7.800 │     — │    — │     — │            — │  40,0 │        — │",
        "│ Finish03 │  10.800 │     — │    — │     — │            — │  50,0 │        — │",
        "│ Finish02 │  12.000 │ 18,75 │  94% │ 19,50 │      225.000 │ 112,0 │ 2.184,00 │",
        "├──────────┼─────────┼───────┼──────┼───────┼──────────────┼───────┼──────────┤",
        "│ Total    │         │ 67,75 │      │ 69,17 │              │       │ 3.498,43 │",
        "└──────────┴─────────┴───────┴──────┴───────┴──────────────┴───────┴──────────┘",
        "t: horas do modelo · uso: t/T · τ: t + setup · E = kW·τ",
        "┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓",
        "┃ Ótimo do modelo ┃ Tempo real (h) ┃ Energia (kWh) ┃ Custo (R$) ┃",
        "┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩",
        "│         67,75 h │          69,17 │      3.498,43 │   3.008,65 │",
        "└─────────────────┴────────────────┴───────────────┴────────────┘",
    ]


def test_summary_table() -> None:
    results = [
        solve_portfolio(
            portfolio=p, printers=data.printers, finishings=data.finishers
        )
        for p in data.portfolios
    ]
    assert render(summary_table(results=results)) == [
        "                   Resumo · objetivo: tempo",
        "┏━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━┓",
        "┃ Carteira      ┃    ótimo ┃  τ (h) ┃   E (kWh) ┃ custo (R$) ┃",
        "┡━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━┩",
        "│ Portfolio I   │  67,75 h │  69,17 │  3.498,43 │   3.008,65 │",
        "│ Portfolio II  │ 162,59 h │ 165,09 │  7.607,13 │   6.542,13 │",
        "│ Portfolio III │ 423,85 h │ 426,85 │ 19.465,85 │  16.740,63 │",
        "└───────────────┴──────────┴────────┴───────────┴────────────┘",
        "ótimo: valor do modelo · τ: tempo real · E: energia",
    ]
