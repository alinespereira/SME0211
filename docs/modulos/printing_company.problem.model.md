O artigo *Energy consumption optimization in a printing company* propõe um
modelo de programação linear inteira, com variáveis $z_{im}$ (metros do
item $i$ impressos na máquina $m$), $w_{in}$ (metros do item $i \in F$
acabados na máquina $n$) e variáveis binárias de designação $x_{im}$ e
$y_{in}$. O artigo trata de dois objetivos. A função objetivo (16)
minimiza o tempo de operação:

$$
\min \sum_{m \in M} \sum_{i \in I} (T_{im} z_{im} + A_{im} x_{im})
   + \sum_{n \in N} \sum_{i \in F} (T_{in} w_{in} + A_{in} y_{in}).
$$

A função objetivo (1) minimiza o custo de energia: cada hora de operação
da máquina $m$ consome $kw_m$ kWh (a potência da Tabela 1,
`Machine.consumption`), e o kWh custa $c$ reais,

$$
\min c \left[ \sum_{m \in M} kw_m \sum_{i \in I}
   (T_{im} z_{im} + A_{im} x_{im})
   + \sum_{n \in N} kw_n \sum_{i \in F} (T_{in} w_{in} + A_{in} y_{in})
   \right].
$$

As restrições são as mesmas nos dois casos.

**Relaxação.** Aqui ficam só a parte contínua do tempo, as restrições de
capacidade (2) e (3) e as restrições de demanda (4) e (5):

- as variáveis binárias $x_{im}$, $y_{in}$ (e, com elas, os setups $A$ e as
  restrições (6) a (11)) são removidas. Na relaxação linear,
  $x_{im} \geq z_{im} / G$ com $G$ grande, então o setup contribui com
  $A_{im} z_{im} / G \approx 0$;
- nas restrições de capacidade (2) e (3), sem os setups, sobra o tempo de
  produção: $\sum_{i \in I} T_{im} z_{im} \leq T_m$. Todas as máquinas têm
  a mesma capacidade $T_m = T_n = T$, o número de horas de turno do
  horizonte de planejamento. No artigo, o turno é diário, de 8 horas mais
  até 2 horas extras (`printing_company.settings.Settings.shift_hours`),
  então $T = 10 d$ para $d$ dias;
- como o tempo por metro $T_{im} = 1 / v_m$ não depende do item, as
  variáveis podem ser agregadas por máquina:
  $z_m = \sum_{i \in I} z_{im}$ e $w_n = \sum_{i \in F} w_{in}$.

**Variáveis em horas.** Em vez dos metros $z_m$ e $w_n$, as variáveis são
as horas que cada máquina fica ligada,

$$
t_m = T_{im} z_m = \frac{z_m}{v_m}, \quad m \in M, \qquad
t_n = \frac{w_n}{v_n}, \quad n \in N.
$$

É só uma mudança de escala de cada variável ($z_m = v_m t_m$, com
$v_m > 0$), então os dois modelos têm as mesmas soluções. A função
objetivo de tempo passa a ser a soma das horas, e a de energia, a soma
das horas ponderada pelas potências (a tarifa $c > 0$ é uma constante
que multiplica o objetivo e não muda a solução ótima, então fica de
fora: o objetivo é a energia, em kWh). Somando (4) em $i \in I$ e (5) em
$i \in F$, o modelo fica

$$
\begin{aligned}
\min \quad & \sum_{m \in M} p_m t_m + \sum_{n \in N} p_n t_n \cr
\text{s.a.} \quad & \sum_{m \in M} v_m t_m \geq \sum_{i \in I} D_i, \cr
& \sum_{n \in N} v_n t_n \geq \sum_{i \in F} D_i, \cr
& t_m \leq T, \quad m \in M, \cr
& t_n \leq T, \quad n \in N, \cr
& t \geq 0,
\end{aligned}
$$

com $t$ em horas e $v$ em metros por hora. Os custos $p$ dependem do
objetivo (`Objective`):

- `Objective.TIME`: $p_m = 1$, e o objetivo é o total de horas ligadas;
- `Objective.ENERGY`: $p_m = kw_m$, e o objetivo é a energia consumida
  na produção, em kWh.

As restrições de demanda são
escritas com $\geq$, mas, como os custos são positivos, no ótimo elas
valem com igualdade, como as restrições (4) e (5) do artigo. Para que os
coeficientes fiquem na mesma escala que os custos (1) e as capacidades
($T$, dezenas de horas), as restrições de demanda são divididas por
`SCALE` = 1 000: velocidades em milhares de metros por hora e demandas em
milhares de metros.

O problema é viável se, e só se, as máquinas dão conta da demanda no
horizonte: $T \sum_m v_m \geq \sum_{i \in I} D_i$ e
$T \sum_n v_n \geq \sum_{i \in F} D_i$ (veja `min_capacity`). Sem as
capacidades (`capacity=None`), a solução ótima liga só a impressora e a
máquina de acabamento de menor custo por metro, $p_m / v_m$; com elas, as
máquinas são ligadas em ordem crescente de $p_m / v_m$, até cobrir a
demanda. No objetivo de tempo, essa é a ordem da mais rápida para a mais
lenta; no de energia, a da que gasta menos energia por metro,
$kw_m / v_m$, para a que gasta mais. `build_problem` monta esse modelo
como um `simplex.Problem`.

## Montagem do modelo

Em `build_problem`, as variáveis são, nesta ordem, as horas $t_m$ de cada
impressora de `printers` e $t_n$ de cada máquina de acabamento de
`finishings`, e levam os nomes das máquinas (`Machine.id`). Os custos
dependem de `objective`: com `Objective.TIME`, todos são 1; com
`Objective.ENERGY`, o custo de cada máquina é a sua potência $kw_m$
(`Machine.consumption`). As restrições são, nesta ordem,

$$
\begin{aligned}
\sum_{m \in M} \frac{v_m}{1000} t_m &\geq
   \frac{1}{1000} \sum_{i \in I} D_i
   \quad \text{(impressão)}, \cr
\sum_{n \in N} \frac{v_n}{1000} t_n &\geq
   \frac{1}{1000} \sum_{i \in F} D_i
   \quad \text{(acabamento)}, \cr
t_m &\leq T, \quad t_n \leq T
   \quad \text{(capacidade, uma por máquina)},
\end{aligned}
$$

com as demandas `Portfolio.total` e `Portfolio.with_finishing`
divididas por `SCALE`. A quantidade produzida por uma máquina, em
metros, é $v t$. A capacidade $T$ (`capacity`) é dada em horas por
máquina no horizonte, por exemplo `2 * settings.shift_hours` para dois
dias; com `None`, as restrições de capacidade não entram no modelo, e uma
capacidade que não seja positiva levanta `ValueError`.

## Capacidade mínima

Com todas as máquinas trabalhando $T$ horas, as impressoras produzem
$T \sum_m v_m$ metros e as máquinas de acabamento, $T \sum_n v_n$.
Então o modelo é viável se, e só se,

$$
T \geq T_{\min} = \max\left(
    \frac{\sum_{i \in I} D_i}{\sum_{m \in M} v_m},
    \frac{\sum_{i \in F} D_i}{\sum_{n \in N} v_n}
\right),
$$

que é o que `min_capacity` devolve. Nas carteiras I, II e III do artigo,
$T_{\min}$ vale 12,66 h, 27,11 h e 60,85 h: um único turno de 10 h não
basta para a carteira I, mas dois bastam.

## Exemplos com os dados do artigo

- **Tempo, sem capacidade.** Na carteira I, só a `Print04` (12 600 m/h) e
  a `Finish02` (12 000 m/h) ficam ligadas, por 43,10 h e 18,75 h (ótimo de
  61,85 h).
- **Tempo, dois dias de turno** ($T = 20$ h). A `Print04` e a `Print01`
  ficam ligadas as 20 horas, e a `Print05`, a terceira mais rápida,
  imprime o resto (81 000 m) em 9 horas. O acabamento ainda cabe todo na
  `Finish02`. O tempo total sobe para 67,75 h, porque parte da impressão
  foi para máquinas mais lentas.
- **Energia, dois dias de turno.** As máquinas que gastam menos energia
  por metro não são as mais rápidas. A `Print05` (2,2 kW e 9 000 m/h, ou
  0,00024 kWh/m) é a mais econômica, e a `Print04`, a mais rápida, vem em
  segundo (0,0019 kWh/m). No acabamento, a `Finish02`, a mais rápida, é a
  que mais gasta (112 kW, 0,0093 kWh/m); a `Finish03` (0,0046 kWh/m) e a
  `Finish01` (0,0051 kWh/m) gastam a metade. A impressão vai para a
  `Print05` e a `Print04`, nas 20 horas, e o resto para a `Print01`; o
  acabamento, para a `Finish03` e, o que passa das 20 horas dela, para a
  `Finish01`. O consumo é de 1 993,01 kWh, contra
  $40 \cdot 20 + 24 \cdot 20 + 2{,}2 \cdot 9 + 112 \cdot 18{,}75
  = 3\,399{,}8$ kWh no objetivo de tempo (70% a mais); em troca, o tempo
  total sobe de 67,75 h para 71,73 h.

Esses exemplos estão no notebook
[`notebooks/02_grafica.ipynb`](https://github.com/alinespereira/SME0211/blob/main/notebooks/02_grafica.ipynb).
