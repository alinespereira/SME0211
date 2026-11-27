Para cada carteira, `portfolio_report` mostra

- um cabeçalho com a carteira, o objetivo, as demandas de impressão e de
  acabamento e o horizonte ($d$ turnos, $T$ horas por máquina);
- uma tabela com uma linha por máquina (as impressoras, depois as de
  acabamento): a velocidade $v$, as horas de produção $t$ do modelo, o
  uso da capacidade $t / T$, o tempo real $\tau$ (com setup), os metros
  produzidos $v t$, a potência $kw$ e a energia $E = kw \, \tau$. As
  máquinas desligadas aparecem apagadas;
- uma tabela com o valor ótimo do modelo, os totais com setup (o tempo
  real, a energia e o custo) e a duração da solução pelo simplex
  (`PortfolioResult.solve_seconds`, formatada por `format_duration`).

Com mais de uma carteira, `summary_table` compara todas no fim, uma por
linha. Se houver mais de um objetivo, a tabela ganha a coluna `objetivo`,
e uma linha separa as carteiras. Os turnos, a capacidade $T$ e o custo
(proporcional à energia) ficam só no relatório de cada carteira, para que
o resumo caiba em 80 colunas:

```text
                 Resumo · objetivo: tempo
┏━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━┓
┃ Carteira      ┃    ótimo ┃  τ (h) ┃   E (kWh) ┃ simplex ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━┩
│ Portfolio I   │  67,75 h │  69,17 │  3.498,43 │  4,2 ms │
│ Portfolio II  │ 162,59 h │ 165,09 │  7.607,13 │  3,9 ms │
│ Portfolio III │ 423,85 h │ 426,85 │ 19.465,85 │  4,1 ms │
└───────────────┴──────────┴────────┴───────────┴─────────┘
τ: tempo real · E: energia · simplex: duração da solução
```

Os números seguem o padrão brasileiro (`format_br`): vírgula decimal e
ponto nos milhares.
