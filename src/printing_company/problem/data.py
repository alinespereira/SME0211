r"""Instâncias do artigo *Energy consumption optimization in a printing
company* (Gestão & Produção, 2024).

As máquinas vêm da Tabela 1 (velocidade em m/h, setup em h e consumo em
kWh) e as carteiras de pedidos, das Tabelas 2 a 4 (demandas em metros). Os
itens que exigem acabamento são D01 a D05 na carteira I, D01 a D10 na II e
D01 a D35 na III.
"""

from .spec import Demand, FinishingMachine, Portfolio, PrintingMachine

__all__ = ["finishers", "portfolios", "printers"]

printers = [
    PrintingMachine(id="Print01", speed=10_500, setup=0.25, consumption=40),
    PrintingMachine(id="Print02", speed=3_000, setup=0.5, consumption=112),
    PrintingMachine(id="Print03", speed=7_800, setup=0.33, consumption=49.2),
    PrintingMachine(id="Print04", speed=12_600, setup=0.17, consumption=24),
    PrintingMachine(id="Print05", speed=9_000, setup=0.25, consumption=2.2),
]
"""Máquinas de impressão $m \\in M$ (Tabela 1 do artigo)."""

finishers = [
    FinishingMachine(id="Finish01", speed=7_800, setup=0.5, consumption=40),
    FinishingMachine(id="Finish03", speed=10_800, setup=0.75, consumption=50),
    FinishingMachine(id="Finish02", speed=12_000, setup=0.75, consumption=112),
]
"""Máquinas de acabamento $n \\in N$ (Tabela 1 do artigo)."""

portfolios = [
    Portfolio(
        label="Portfolio I",
        demands=[
            Demand(label="D01", quantity=15_000, requires_finishing=True),
            Demand(label="D02", quantity=20_000, requires_finishing=True),
            Demand(label="D03", quantity=55_000, requires_finishing=True),
            Demand(label="D04", quantity=85_000, requires_finishing=True),
            Demand(label="D05", quantity=50_000, requires_finishing=True),
            Demand(label="D06", quantity=60_000, requires_finishing=False),
            Demand(label="D07", quantity=70_000, requires_finishing=False),
            Demand(label="D08", quantity=80_000, requires_finishing=False),
            Demand(label="D09", quantity=90_000, requires_finishing=False),
            Demand(label="D10", quantity=18_000, requires_finishing=False),
        ],
    ),
    Portfolio(
        label="Portfolio II",
        demands=[
            Demand(label="D01", quantity=15_000, requires_finishing=True),
            Demand(label="D02", quantity=20_000, requires_finishing=True),
            Demand(label="D03", quantity=55_000, requires_finishing=True),
            Demand(label="D04", quantity=85_000, requires_finishing=True),
            Demand(label="D05", quantity=50_000, requires_finishing=True),
            Demand(label="D06", quantity=60_000, requires_finishing=True),
            Demand(label="D07", quantity=70_000, requires_finishing=True),
            Demand(label="D08", quantity=80_000, requires_finishing=True),
            Demand(label="D09", quantity=90_000, requires_finishing=True),
            Demand(label="D10", quantity=18_000, requires_finishing=True),
            Demand(label="D11", quantity=13_000, requires_finishing=False),
            Demand(label="D12", quantity=28_000, requires_finishing=False),
            Demand(label="D13", quantity=59_000, requires_finishing=False),
            Demand(label="D14", quantity=82_000, requires_finishing=False),
            Demand(label="D15", quantity=55_000, requires_finishing=False),
            Demand(label="D16", quantity=61_000, requires_finishing=False),
            Demand(label="D17", quantity=77_000, requires_finishing=False),
            Demand(label="D18", quantity=84_000, requires_finishing=False),
            Demand(label="D19", quantity=91_000, requires_finishing=False),
            Demand(label="D20", quantity=70_000, requires_finishing=False),
        ],
    ),
    Portfolio(
        label="Portfolio III",
        demands=[
            Demand(label="D01", quantity=15_000, requires_finishing=True),
            Demand(label="D02", quantity=20_000, requires_finishing=True),
            Demand(label="D03", quantity=55_000, requires_finishing=True),
            Demand(label="D04", quantity=85_000, requires_finishing=True),
            Demand(label="D05", quantity=50_000, requires_finishing=True),
            Demand(label="D06", quantity=60_000, requires_finishing=True),
            Demand(label="D07", quantity=70_000, requires_finishing=True),
            Demand(label="D08", quantity=80_000, requires_finishing=True),
            Demand(label="D09", quantity=90_000, requires_finishing=True),
            Demand(label="D10", quantity=18_000, requires_finishing=True),
            Demand(label="D11", quantity=13_000, requires_finishing=True),
            Demand(label="D12", quantity=28_000, requires_finishing=True),
            Demand(label="D13", quantity=59_000, requires_finishing=True),
            Demand(label="D14", quantity=82_000, requires_finishing=True),
            Demand(label="D15", quantity=55_000, requires_finishing=True),
            Demand(label="D16", quantity=61_000, requires_finishing=True),
            Demand(label="D17", quantity=77_000, requires_finishing=True),
            Demand(label="D18", quantity=84_000, requires_finishing=True),
            Demand(label="D19", quantity=91_000, requires_finishing=True),
            Demand(label="D20", quantity=70_000, requires_finishing=True),
            Demand(label="D21", quantity=77_000, requires_finishing=True),
            Demand(label="D22", quantity=54_000, requires_finishing=True),
            Demand(label="D23", quantity=10_000, requires_finishing=True),
            Demand(label="D24", quantity=13_000, requires_finishing=True),
            Demand(label="D25", quantity=67_000, requires_finishing=True),
            Demand(label="D26", quantity=35_000, requires_finishing=True),
            Demand(label="D27", quantity=12_000, requires_finishing=True),
            Demand(label="D28", quantity=98_000, requires_finishing=True),
            Demand(label="D29", quantity=43_000, requires_finishing=True),
            Demand(label="D30", quantity=40_000, requires_finishing=True),
            Demand(label="D31", quantity=17_000, requires_finishing=True),
            Demand(label="D32", quantity=46_000, requires_finishing=True),
            Demand(label="D33", quantity=98_000, requires_finishing=True),
            Demand(label="D34", quantity=78_000, requires_finishing=True),
            Demand(label="D35", quantity=11_000, requires_finishing=True),
            Demand(label="D36", quantity=98_000, requires_finishing=False),
            Demand(label="D37", quantity=45_000, requires_finishing=False),
            Demand(label="D38", quantity=85_000, requires_finishing=False),
            Demand(label="D39", quantity=35_000, requires_finishing=False),
            Demand(label="D40", quantity=27_000, requires_finishing=False),
            Demand(label="D41", quantity=55_000, requires_finishing=False),
            Demand(label="D42", quantity=67_000, requires_finishing=False),
            Demand(label="D43", quantity=43_000, requires_finishing=False),
            Demand(label="D44", quantity=45_000, requires_finishing=False),
            Demand(label="D45", quantity=12_000, requires_finishing=False),
            Demand(label="D46", quantity=17_000, requires_finishing=False),
            Demand(label="D47", quantity=74_000, requires_finishing=False),
            Demand(label="D48", quantity=33_000, requires_finishing=False),
            Demand(label="D49", quantity=42_000, requires_finishing=False),
            Demand(label="D50", quantity=17_000, requires_finishing=False),
        ],
    ),
]
"""Carteiras de pedidos I, II e III (Tabelas 2 a 4 do artigo)."""
