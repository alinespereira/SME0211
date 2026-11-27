Cada iteração parte de um `simplex.tableau.Tableau` associado a uma base
viável e segue os passos das aulas:

1. **Otimalidade** (`Solver.is_optimal`). Calcule os custos reduzidos
   $\bar{c}_j = c_j - p^\top A_j$. Se $\bar{c}_j \geq 0$ para todo $j$, a
   solução básica viável atual é ótima e o método para.
2. **Variável que entra** (`Solver.entering_variable`). Escolha $j$ com
   $\bar{c}_j < 0$.
3. **Coluna pivô** (`simplex.tableau.Tableau.column`). Calcule
   $u = B^{-1} A_j$. Se $u \leq 0$, então $\theta^* = \infty$, o custo
   ótimo é $-\infty$ e o método para.
4. **Variável que sai** (`Solver.leaving_row`). Calcule o passo
   $$
   \theta^* = \min_{\lbrace i \,:\, u_i > 0 \rbrace} \frac{x_{B(i)}}{u_i}
   $$
   e escolha uma linha $\ell$ que atinge esse mínimo.
5. **Troca de base** (`Solver.change_basis`). Substitua $B(\ell)$ por $j$,
   ficando com
   $\bar{B} = \begin{bmatrix} A_{B(1)} & \cdots & A_{B(\ell-1)} & A_j &
   A_{B(\ell+1)} & \cdots & A_{B(m)} \end{bmatrix}$. Como o `Tableau` é
   imutável e guarda os dados originais, basta montar a nova tupla de
   índices e chamar `simplex.tableau.Tableau.with_basis`, que confere que
   $\bar{B}$ é inversível e que a nova solução é viável.

`Solver.solve` repete os passos até encontrar uma solução ótima, detectar
que o custo ótimo é $-\infty$ ou atingir `Solver.max_iterations`. Nos
testes de sinal, usa-se a tolerância $\varepsilon$ =
`simplex.defaults.TOLERANCE`: $\bar{c}_j < 0$ quer dizer
$\bar{c}_j < -\varepsilon$.

No nível DEBUG do `logging`, `Solver.solve` registra o tableau de cada
iteração, com a coluna da variável que entra marcada com `↓`, a linha da
que sai marcada com `→` e o pivô entre colchetes (e em cores no terminal;
veja `simplex.display`). A Fase 1 usa o logger
`simplex.logs.PHASE_ONE_LOGGER`, para que seus tableaux possam ser
escondidos à parte.

## Ciclagem e regras anticiclagem

Em problemas degenerados ($x_{B(i)} = 0$ para algum $i$) pode haver
$\theta^* = 0$, e o método pode voltar a uma base já visitada e repetir
bases para sempre: é a **ciclagem**. As escolhas dos passos 2 e 4 são
livres, e as regras anticiclagem (`PivotingRule`) as fixam de modo a
garantir que o método termina em um número finito de iterações.

**Regra de Bland** (do menor índice, `PivotingRule.BLAND`):

- entra o menor $j$ com $\bar{c}_j < 0$;
- sai, entre as linhas $\ell$ que atingem $\theta^*$, a de menor índice
  de variável $B(\ell)$.

**Regra lexicográfica** (`PivotingRule.LEXICOGRAPHIC`):

- entra qualquer $j$ com $\bar{c}_j < 0$ (a implementação sorteia um);
- sai, entre as linhas $i$ com $u_i > 0$, a linha $\ell$ cujo vetor
  $$
  v_i = \frac{1}{u_i}
  \begin{bmatrix} x_{B(i)} & (B^{-1} A)_i \end{bmatrix}
  $$
  é o lexicograficamente menor, em que $(B^{-1} A)_i$ é a linha $i$
  de $B^{-1} A$. A primeira entrada de $v_i$ é $x_{B(i)} / u_i$, então
  a escolha sempre atinge $\theta^*$; as demais só desempatam.

A garantia de término da regra lexicográfica exige que, no tableau
inicial, todas as linhas
$\begin{bmatrix} x_{B(i)} & (B^{-1} A)_i \end{bmatrix}$ sejam
lexicograficamente positivas (a primeira entrada não nula é positiva).
Isso vale, por exemplo, quando a base inicial é formada pelas variáveis
de folga e elas são as primeiras colunas de $A$.

**Índices.** Como em `simplex.tableau`, as aulas numeram as linhas de $1$ a
$m$ e o código de $0$ a $m - 1$: a linha $\ell$ das fórmulas é o índice
`ell - 1` do código.

Os passos de uma iteração, um de cada vez, estão no notebook
[`notebooks/01_simplex.ipynb`](https://github.com/alinespereira/SME0211/blob/main/notebooks/01_simplex.ipynb).
