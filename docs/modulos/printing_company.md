A gráfica recebe uma carteira de pedidos e precisa decidir quantos metros
de cada item $i \in I$ produzir em cada máquina de impressão $m \in M$ e,
para os itens que exigem acabamento ($i \in F$), em cada máquina de
acabamento $n \in N$. O trabalho usa uma versão relaxada (contínua) do
modelo do artigo, resolvida com o pacote `simplex`, que minimiza o tempo
de operação das máquinas ou o consumo de energia (veja
`printing_company.problem.model.Objective`).

**Módulos:**

- `printing_company.problem`: os dados do problema (máquinas e carteiras
  de pedidos), em `printing_company.problem.spec`, e as instâncias do
  artigo, em `printing_company.problem.data`;
- `printing_company.settings`: caminhos do projeto e os parâmetros do
  cenário (horas de um turno e tarifa de energia);
- `printing_company.report`: as tabelas que o comando mostra.

**Comando:** `printing-company` (a função `main`) resolve as três
carteiras do artigo e mostra, para cada uma, uma tabela com as horas, o
tempo real e a energia de cada máquina, e no fim um resumo que compara as
carteiras (veja `printing_company.report`). Cada carteira é resolvida com
o menor número de turnos diários que a torna viável. Com `--debug`,
mostra também o modelo e o tableau de cada iteração do simplex, com a
variável que entra, a que sai e o pivô em destaque (veja
`simplex.display`). Os tableaux da Fase 1 só aparecem com `--phase-one`.
Com `--objective energy`, minimiza o consumo de energia em vez do tempo:

```sh
uv run printing-company --debug              # as três carteiras
uv run printing-company --debug --portfolio 2  # só a Portfolio II
uv run printing-company --debug --phase-one    # inclui a Fase 1
uv run printing-company --objective energy     # minimiza a energia
uv run printing-company -o time -o energy      # compara os dois objetivos
SHIFT_HOURS=8 uv run printing-company          # turnos de 8 h
```

O uso pelo Python, com as carteiras do artigo, está no notebook
[`notebooks/02_grafica.ipynb`](https://github.com/alinespereira/SME0211/blob/main/notebooks/02_grafica.ipynb)
([abrir no Colab](https://colab.research.google.com/github/alinespereira/SME0211/blob/main/notebooks/02_grafica.ipynb)).
