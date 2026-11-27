O modelo relaxado (`printing_company.problem.model`) dá as horas $t$ que
cada máquina fica produzindo, sem os setups. As funções deste módulo
calculam, a partir dessas horas, as grandezas do artigo:

- `operating_times`: o **tempo real** de cada máquina, com o setup. No
  artigo, a máquina $m$ gasta $A_{im}$ horas de setup para cada item $i$
  designado a ela ($x_{im} = 1$). O modelo relaxado agrega os itens por
  máquina e não diz quantos itens cada uma recebe, então contamos **um
  setup por máquina ligada**:

  $$
  \tau_m = t_m + A_m \, [t_m > 0].
  $$

  Toda máquina ligada recebe pelo menos um item, então esse é um limite
  inferior para o tempo do artigo. Os setups não entram na restrição de
  capacidade, então $\tau_m$ pode passar um pouco de $T$. Uma máquina
  desligada ($t_m = 0$, a menos de `simplex.defaults.TOLERANCE`) não tem
  setup, e horas negativas levantam `ValueError`.
- `energy_consumption`: o **consumo de energia** de cada máquina, em kWh.
  Como na função objetivo (1) do artigo, o consumo $kw_m$ da Tabela 1 é a
  energia por hora de operação (a potência), e a máquina consome
  $kw_m$ durante todo o tempo real, setup incluído:

  $$
  E_m = kw_m \, \tau_m.
  $$

  O custo de energia do artigo é $c \sum_m E_m$, com a tarifa
  $c$ = `printing_company.settings.Settings.energy_price`, de 0,86 real
  por kWh (veja `energy_cost`).

As horas vêm de `Solution.x`, indexadas pelos nomes das variáveis (os
`Machine.id`): `dict(zip(problem.variable_names, solution.x))`.

## Resolver uma carteira

`solve_portfolio` junta tudo: escolhe o menor número de turnos que torna
a carteira viável, monta e resolve o modelo e devolve um
`PortfolioResult`, com as grandezas acima para cada máquina
(`MachineResult`). É o que o comando `printing-company` mostra (veja
`printing_company.report`).

O número de turnos é $d = \lceil T_{\min} / h \rceil$, com
$T_{\min}$ de `printing_company.problem.model.min_capacity` e $h$ as
horas de um turno (`printing_company.settings.Settings.shift_hours`, se
não for dado); o modelo é o de
`printing_company.problem.model.build_problem`, com $T = d h$. Sem um
`solver`, usa a regra lexicográfica. No nível DEBUG do `logging`,
registra o modelo montado (o `simplex.Problem`, como escrito no papel)
antes de resolvê-lo.

Por exemplo, a carteira I do artigo precisa de 2 turnos (20 h); ficam
ligadas a `Print01`, a `Print04`, a `Print05` e a `Finish02`, com ótimo de
67,75 h, tempo real de 69,17 h e 3 498,43 kWh (R$ 3 008,65). Veja o
notebook
[`notebooks/02_grafica.ipynb`](https://github.com/alinespereira/SME0211/blob/main/notebooks/02_grafica.ipynb).
