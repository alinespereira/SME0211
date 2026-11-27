Os modelos seguem os parâmetros do artigo *Energy consumption optimization
in a printing company* (Gestão & Produção, 2024), na versão relaxada do
trabalho, focada no tempo de impressão:

- as **máquinas de impressão** $m \in M$ (`PrintingMachine`) e as
  **máquinas de acabamento** $n \in N$ (`FinishingMachine`), cada uma com
  velocidade $v$ (em metros por hora), tempo médio de setup $A$ (em horas)
  e consumo de energia $kw$ (em kWh por hora de operação, isto é, a
  potência em kW), nas unidades da Tabela 1 do artigo. Os três números
  precisam ser positivos, e a classe base `Machine` não pode ser
  instanciada diretamente;
- a **carteira de pedidos** (`Portfolio`): os itens $i \in I$
  (`Demand`), cada um com demanda $D_i$ (em metros), e o subconjunto
  $F \subseteq I$ dos itens que, depois de impressos, também passam por
  uma máquina de acabamento. Os totais `Portfolio.total`,
  `Portfolio.with_finishing` e `Portfolio.without_finishing` também
  aparecem na serialização (`model_dump`).

Com esses dados, o tempo para produzir $z$ metros de um item na máquina
$m$ é $T_m z + A_m$ horas, em que $T_m = 1 / v_m$ é o tempo por metro.
Os dados do artigo estão em `printing_company.problem.data`.

Todos os modelos são imutáveis (`frozen`).
