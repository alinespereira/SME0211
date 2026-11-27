r"""Saída do comando `printing-company`: tabelas do `rich` com o resultado
de cada carteira.

Para cada carteira, `portfolio_report` mostra

- um cabeçalho com a carteira, o objetivo, as demandas de impressão e de
  acabamento e o horizonte ($d$ turnos, $T$ horas por máquina);
- uma tabela com uma linha por máquina (as impressoras, depois as de
  acabamento): a velocidade $v$, as horas de produção $t$ do modelo, o
  uso da capacidade $t / T$, o tempo real $\tau$ (com setup), os metros
  produzidos $v t$, a potência $kw$ e a energia $E = kw \, \tau$. As
  máquinas desligadas aparecem apagadas;
- uma tabela com o valor ótimo do modelo e os totais com setup: o tempo
  real, a energia e o custo.

Com mais de uma carteira, `summary_table` compara todas no fim. Os
números seguem o padrão brasileiro (`format_br`): vírgula decimal e ponto
nos milhares.
"""

from collections.abc import Sequence

from rich.console import Group, JustifyMethod, RenderableType
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from printing_company.problem.analysis import MachineResult, PortfolioResult
from simplex import Status

__all__ = ["format_br", "portfolio_report", "summary_table"]

_IDLE = "—"
"""O que aparece nas colunas de uma máquina desligada."""


def format_br(*, value: float, digits: int = 2) -> str:
    """Formata um número no padrão brasileiro, com `digits` casas
    decimais, vírgula decimal e ponto separando os milhares.

    >>> format_br(value=3498.4321)
    '3.498,43'
    >>> format_br(value=543_000, digits=0)
    '543.000'
    >>> format_br(value=-0.001)
    '0,00'
    """
    text = f"{value + 0.0:,.{digits}f}"
    if text.lstrip("-").strip("0.,") == "":
        text = text.lstrip("-")
    return text.translate(str.maketrans(",.", ".,"))


def _machine_row(
    *, result: MachineResult, capacity: float
) -> tuple[list[str], str | None]:
    """As células de uma máquina e o estilo da linha."""
    m = result.machine
    fixed = [
        m.id,
        format_br(value=m.speed, digits=0),
    ]
    power = format_br(value=m.consumption, digits=1)
    if not result.is_on:
        return [*fixed, _IDLE, _IDLE, _IDLE, _IDLE, power, _IDLE], "dim"
    usage = result.hours / capacity
    return [
        *fixed,
        format_br(value=result.hours),
        f"{format_br(value=100 * usage, digits=0)}%",
        format_br(value=result.time),
        format_br(value=result.produced, digits=0),
        power,
        format_br(value=result.energy),
    ], ("bold" if usage >= 1 - 1e-6 else None)


def _machine_table(*, result: PortfolioResult) -> Table:
    """A tabela das máquinas de uma carteira resolvida."""
    table = Table(
        show_footer=True,
        header_style="bold",
        footer_style="bold",
        caption="t: horas do modelo · uso: t/T · τ: t + setup · E = kW·τ",
        caption_justify="left",
    )
    columns: list[tuple[str, str, JustifyMethod]] = [
        ("Máquina", "Total", "left"),
        ("v (m/h)", "", "right"),
        ("t (h)", format_br(value=result.total_hours), "right"),
        ("uso", "", "right"),
        ("τ (h)", format_br(value=result.total_time), "right"),
        ("produção (m)", "", "right"),
        ("kW", "", "right"),
        ("E (kWh)", format_br(value=result.total_energy), "right"),
    ]
    for header, footer, justify in columns:
        table.add_column(header, footer=footer, justify=justify)
    for group in (result.printers, result.finishers):
        for machine in group:
            cells, style = _machine_row(
                result=machine, capacity=result.capacity
            )
            table.add_row(*cells, style=style)
        table.add_section()
    return table


def portfolio_report(*, result: PortfolioResult) -> RenderableType:
    """O relatório de uma carteira (veja o módulo).

    **Exemplo:** a carteira I do artigo, minimizando o tempo.

    >>> import io
    >>> from rich.console import Console
    >>> from printing_company.problem import data
    >>> from printing_company.problem.analysis import solve_portfolio
    >>> result = solve_portfolio(
    ...     portfolio=data.portfolios[0],
    ...     printers=data.printers,
    ...     finishings=data.finishers,
    ... )
    >>> out = io.StringIO()
    >>> Console(file=out, width=88).print(portfolio_report(result=result))
    >>> for line in out.getvalue().splitlines():
    ...     print(line.rstrip())
    ──────────────────────────── Portfolio I · objetivo: tempo ─────────────────────────────
    10 itens · impressão: 543.000 m · acabamento: 225.000 m (5 itens)
    Horizonte: 2 turnos de 10 h, T = 20 h por máquina
    ┏━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━┳━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━┓
    ┃ Máquina  ┃ v (m/h) ┃ t (h) ┃  uso ┃ τ (h) ┃ produção (m) ┃    kW ┃  E (kWh) ┃
    ┡━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━╇━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━┩
    │ Print01  │  10.500 │ 20,00 │ 100% │ 20,25 │      210.000 │  40,0 │   810,00 │
    │ Print02  │   3.000 │     — │    — │     — │            — │ 112,0 │        — │
    │ Print03  │   7.800 │     — │    — │     — │            — │  49,2 │        — │
    │ Print04  │  12.600 │ 20,00 │ 100% │ 20,17 │      252.000 │  24,0 │   484,08 │
    │ Print05  │   9.000 │  9,00 │  45% │  9,25 │       81.000 │   2,2 │    20,35 │
    ├──────────┼─────────┼───────┼──────┼───────┼──────────────┼───────┼──────────┤
    │ Finish01 │   7.800 │     — │    — │     — │            — │  40,0 │        — │
    │ Finish03 │  10.800 │     — │    — │     — │            — │  50,0 │        — │
    │ Finish02 │  12.000 │ 18,75 │  94% │ 19,50 │      225.000 │ 112,0 │ 2.184,00 │
    ├──────────┼─────────┼───────┼──────┼───────┼──────────────┼───────┼──────────┤
    │ Total    │         │ 67,75 │      │ 69,17 │              │       │ 3.498,43 │
    └──────────┴─────────┴───────┴──────┴───────┴──────────────┴───────┴──────────┘
    t: horas do modelo · uso: t/T · τ: t + setup · E = kW·τ
    ┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
    ┃ Ótimo do modelo ┃ Tempo real (h) ┃ Energia (kWh) ┃ Custo (R$) ┃
    ┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
    │         67,75 h │          69,17 │      3.498,43 │   3.008,65 │
    └─────────────────┴────────────────┴───────────────┴────────────┘
    """
    portfolio = result.portfolio
    finishing_items = sum(d.requires_finishing for d in portfolio.demands)
    shift = result.capacity / result.shifts
    header = Text.assemble(
        f"{len(portfolio.demands)} itens · impressão: ",
        (f"{format_br(value=portfolio.total, digits=0)} m", "bold"),
        " · acabamento: ",
        (f"{format_br(value=portfolio.with_finishing, digits=0)} m", "bold"),
        f" ({finishing_items} itens)\nHorizonte: {result.shifts} turnos de "
        f"{format_br(value=shift, digits=0)} h, T = "
        f"{format_br(value=result.capacity, digits=0)} h por máquina",
    )
    title = Rule(
        f"[bold]{portfolio.label}[/] · objetivo: {result.objective.label}"
    )
    if result.status != Status.OPTIMAL or result.objective_value is None:
        return Group(
            title,
            header,
            Text(f"Sem solução ótima: {result.status}.", style="bold red"),
        )
    return Group(
        title,
        header,
        _machine_table(result=result),
        _totals_table(result=result),
    )


def _totals_table(*, result: PortfolioResult) -> Table:
    """A tabela com o ótimo do modelo e os totais de uma carteira
    resolvida (tempo real, energia e custo, com setup)."""
    assert result.objective_value is not None
    table = Table(header_style="bold")
    table.add_column("Ótimo do modelo", justify="right", style="bold green")
    for header in ("Tempo real (h)", "Energia (kWh)", "Custo (R$)"):
        table.add_column(header, justify="right")
    table.add_row(
        f"{format_br(value=result.objective_value)} {result.objective.unit}",
        format_br(value=result.total_time),
        format_br(value=result.total_energy),
        format_br(value=result.cost),
    )
    return table


def summary_table(*, results: Sequence[PortfolioResult]) -> Table:
    """Tabela que compara as carteiras resolvidas, uma por linha.

    Se `results` tiver mais de um objetivo, a tabela ganha a coluna
    `objetivo`, e uma linha separa as carteiras. Os turnos e a capacidade
    $T$ de cada carteira estão no cabeçalho do relatório dela
    (`portfolio_report`), e ficam fora daqui para que a tabela caiba em
    80 colunas.

    **Exemplo:**

    >>> import io
    >>> from rich.console import Console
    >>> from printing_company.problem import data
    >>> from printing_company.problem.analysis import solve_portfolio
    >>> results = [
    ...     solve_portfolio(
    ...         portfolio=p, printers=data.printers, finishings=data.finishers
    ...     )
    ...     for p in data.portfolios
    ... ]
    >>> out = io.StringIO()
    >>> Console(file=out, width=88).print(summary_table(results=results))
    >>> for line in out.getvalue().splitlines():
    ...     print(line.rstrip())
                       Resumo · objetivo: tempo
    ┏━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━┓
    ┃ Carteira      ┃    ótimo ┃  τ (h) ┃   E (kWh) ┃ custo (R$) ┃
    ┡━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━┩
    │ Portfolio I   │  67,75 h │  69,17 │  3.498,43 │   3.008,65 │
    │ Portfolio II  │ 162,59 h │ 165,09 │  7.607,13 │   6.542,13 │
    │ Portfolio III │ 423,85 h │ 426,85 │ 19.465,85 │  16.740,63 │
    └───────────────┴──────────┴────────┴───────────┴────────────┘
    ótimo: valor do modelo · τ: tempo real · E: energia
    """
    objectives = {r.objective for r in results}
    title = "Resumo"
    if len(objectives) == 1:
        title += f" · objetivo: {next(iter(objectives)).label}"
    table = Table(
        title=title,
        header_style="bold",
        caption="ótimo: valor do modelo · τ: tempo real · E: energia",
        caption_justify="left",
    )
    many = len(objectives) > 1
    columns = [
        "Carteira",
        *(["objetivo"] if many else []),
        *("ótimo", "τ (h)", "E (kWh)", "custo (R$)"),
    ]
    for header in columns:
        table.add_column(
            header,
            justify="left" if header in {"Carteira", "objetivo"} else "right",
            no_wrap=True,
        )
    previous: str | None = None
    for r in results:
        if many and previous is not None and r.portfolio.label != previous:
            table.add_section()
        previous = r.portfolio.label
        fixed = [
            r.portfolio.label,
            *([r.objective.label] if many else []),
        ]
        if r.status != Status.OPTIMAL or r.objective_value is None:
            table.add_row(*fixed, str(r.status), "", "", "", style="red")
            continue
        table.add_row(
            *fixed,
            f"{format_br(value=r.objective_value)} {r.objective.unit}",
            format_br(value=r.total_time),
            format_br(value=r.total_energy),
            format_br(value=r.cost),
        )
    return table
