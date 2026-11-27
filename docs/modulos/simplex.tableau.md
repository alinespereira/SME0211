A notação segue as aulas de SME0211 (baseadas em Bertsimas e Tsitsiklis,
*Introduction to Linear Optimization*). O problema considerado é

$$
\begin{aligned}
\min_{x} \quad & c^\top x \cr
\text{s.a.} \quad & A x = b, \cr
& x \geq 0,
\end{aligned}
$$

com $A \in \mathbb{R}^{m \times n}$ ($m$ restrições e $n$ variáveis),
$b \in \mathbb{R}^m$ e $c \in \mathbb{R}^n$.

Uma base é dada pelos índices $B(1), \dots, B(m)$ das variáveis básicas, e
a matriz base é

$$
B = \begin{bmatrix} A_{B(1)} & \cdots & A_{B(m)} \end{bmatrix}
\in \mathbb{R}^{m \times m},
$$

em que $A_j$ é a $j$-ésima coluna de $A$. A solução básica associada tem
$x_B = B^{-1} b$ e as variáveis não básicas iguais a zero; ela é viável
quando $x_B \geq 0$.

O tableau completo (aula 19) associado à base é

$$
\begin{array}{c|c}
-c_B^\top B^{-1} b & c^\top - c_B^\top B^{-1} A \cr
\hline
B^{-1} b & B^{-1} A
\end{array} =
\begin{array}{c|ccc}
-c_B^\top x_B & \bar{c}_1 & \cdots & \bar{c}_n \cr
\hline
x_B & B^{-1} A_1 & \cdots & B^{-1} A_n
\end{array}.
$$

## Grandezas derivadas

Todas são propriedades de `Tableau`, calculadas a partir de $A$, $b$, $c$
e da base:

- `Tableau.B`: $B = \begin{bmatrix} A_{B(1)} & \cdots & A_{B(m)} \end{bmatrix}$;
- `Tableau.basic_costs`: $c_B = (c_{B(1)}, \dots, c_{B(m)})$;
- `Tableau.basic_solution`: $x_B = B^{-1} b$ (coluna 0 do tableau);
- `Tableau.multipliers`: $p^\top = c_B^\top B^{-1}$;
- `Tableau.reduced_costs`: $\bar{c}^\top = c^\top - c_B^\top B^{-1} A =
  c^\top - p^\top A$, ou seja, $\bar{c}_j = c_j - p^\top A_j$ (linha 0
  do tableau). Os das variáveis básicas são zero; se $\bar{c}_j \geq 0$
  para todo $j$, a solução básica viável atual é ótima;
- `Tableau.column`: $u = B^{-1} A_j$. Quando $x_j$ entra na base, $u$ é a
  coluna pivô, usada no teste da razão
  $\theta^* = \min_{u_i > 0} x_{B(i)} / u_i$;
- `Tableau.solution`: $x \in \mathbb{R}^n$, com $x_B = B^{-1} b$ e as não
  básicas iguais a zero;
- `Tableau.objective_value`: $c^\top x = c_B^\top x_B$;
- `Tableau.table`: o tableau completo, uma matriz $(m + 1) \times (n + 1)$,
  $\begin{bmatrix} -c_B^\top x_B & \bar{c}^\top \cr x_B & B^{-1} A \end{bmatrix}$.

**Validação.** O construtor exige $A \in \mathbb{R}^{m \times n}$,
$b \in \mathbb{R}^m$, $c \in \mathbb{R}^n$ e que `basis` tenha $m$
índices distintos em $\lbrace 0, \dots, n - 1 \rbrace$. Também exige que
$B$ seja inversível (as colunas $A_{B(1)}, \dots, A_{B(m)}$ são
linearmente independentes) e que a base seja viável
($x_B \geq -\varepsilon$, com $\varepsilon$ = `simplex.defaults.TOLERANCE`).

**Imutabilidade.** O tableau é `frozen` e os arrays são somente leitura.
Para mudar de base, use `Tableau.with_basis`, que cria um novo tableau e
passa por todas as validações (evite `model_copy(update=...)`, que não
roda os validadores).

## Implementação

A classe guarda apenas os dados originais $A$, $b$ e
$c$ (que não mudam) e a base; tudo o mais é calculado a partir deles. Como
na "implementação ingênua" da aula 18, $B^{-1}$ nunca é calculada
explicitamente: $x_B = B^{-1} b$ sai de $B x_B = b$, o vetor de
multiplicadores do simplex sai de $p^\top B = c_B^\top$ e a coluna
$u = B^{-1} A_j$ sai de $B u = A_j$, todos resolvidos com
`numpy.linalg.solve`.

**Índices.** Nas aulas os índices começam em $1$; no código, como é usual
em Python, começam em $0$. Assim, `basis[0]` é $B(1)$, `basis[1]` é
$B(2)$ etc.

## Exemplo

O problema

$$
\begin{aligned}
\min \quad & -x_1 - 2 x_2 \cr
\text{s.a.} \quad & x_1 + x_2 + x_3 = 4, \cr
& x_1 + 3 x_2 + x_4 = 6, \cr
& x \geq 0,
\end{aligned}
$$

na base das folgas $x_3$ e $x_4$ (índices 2 e 3 no código) tem
$x_B = (4, 6)$ e custos reduzidos $(-1, -2, 0, 0)$; na base
$\lbrace x_1, x_2 \rbrace$, que é a ótima, $x = (3, 1, 0, 0)$, com custo
$-5$. O passo a passo está no notebook
[`notebooks/01_simplex.ipynb`](https://github.com/alinespereira/SME0211/blob/main/notebooks/01_simplex.ipynb).
