`render_tableau` monta o tableau completo (veja `simplex.tableau.Tableau.table`)

$$
\begin{array}{c|c}
-c_B^\top x_B & \bar{c}^\top \cr
\hline
x_B & B^{-1} A
\end{array}
$$

como um `rich.text.Text`, com os nomes das variáveis no cabeçalho e o nome
da variável básica $x_{B(i)}$ no início de cada linha. Numa iteração do
simplex, destaca

- a coluna $j$ da variável que **entra** (marcada com `↓` no cabeçalho e
  em ciano);
- a linha $\ell$ da variável que **sai** (marcada com `→` antes do nome e
  em magenta);
- o **pivô** $u_\ell = (B^{-1} A_j)_\ell$, entre colchetes e em amarelo.

O pivô só é destacado quando `entering` e `leaving` são dados. As marcas
aparecem no texto puro (`Text.plain`, que vai para arquivos de log) e as
cores só no terminal (veja `simplex.logs`). Por exemplo, no tableau do
exemplo de `simplex.tableau`, com $x_2$ entrando e $s_2$ saindo:

```text
        │ x1  x2 ↓ s1  s2
────────┼─────────────────
  -z 0  │ -1   -2   0   0
────────┼─────────────────
  s1 4  │  1    1   1   0
→ s2 6  │  1   [3]  0   1
```

Os números usam `format_number`: até 4 algarismos significativos, e
valores com módulo até `simplex.defaults.TOLERANCE` (resíduos de ponto
flutuante, como `-2.22e-16`) aparecem como `0`.
