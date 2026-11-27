"""Saída do comando `printing-company`: tabelas do `rich` com o resultado
de cada carteira.

.. include:: ../../docs/modulos/printing_company.report.md
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
    """Formata `value` no padrão brasileiro, com `digits` casas decimais."""
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
    """O relatório de uma carteira (veja o módulo)."""
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
    """Tabela que compara as carteiras resolvidas, uma por linha."""
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
