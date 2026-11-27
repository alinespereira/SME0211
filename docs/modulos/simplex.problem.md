Um `Problem` descreve o problema como ele é escrito no papel:

$$
\begin{aligned}
\min \text{ ou } \max \quad & c^\top x \cr
\text{s.a.} \quad & a_i^\top x \;\square_i\; b_i, \quad
\square_i \in \lbrace \leq, \geq, = \rbrace, \quad i = 1, \dots, m, \cr
& x \geq 0,
\end{aligned}
$$

e pode ser lido de um arquivo TOML (veja `Problem.from_toml` e
`examples/`). Todas as variáveis são supostas não negativas.

Para resolvê-lo com o simplex, o caminho é:

1. `Problem.to_standard_form`: converte para a forma padrão
   $\min \tilde{c}^\top \tilde{x}$, $\tilde{A} \tilde{x} = \tilde{b}$,
   $\tilde{x} \geq 0$, com $\tilde{b} \geq 0$ (`StandardForm`);
2. `StandardForm.initial_tableau`: encontra uma base viável inicial pela
   Fase 1 (aula 22), resolvendo um problema auxiliar com variáveis
   artificiais;
3. `simplex.solver.Solver.solve`: a Fase 2, a partir dessa base;
4. `StandardForm.original_solution` e `StandardForm.original_objective`:
   traduzem a resposta de volta para as variáveis e o sentido originais.

`Problem.solve` junta os quatro passos. Se a Fase 1 mostrar que o
problema é inviável, a `Solution` tem status
`simplex.solver.Status.INFEASIBLE`.

## Arquivo TOML

O arquivo tem as mesmas chaves que os campos de `Problem`; cada restrição
é uma tabela `[[constraints]]` (veja `examples/pequeno.toml`):

```toml
sense = "max"
c = [3, 2]
names = ["x1", "x2"]

[[constraints]]
coefs = [1, 1]
sense = "<="
rhs = 4
```

## Forma padrão

`Problem.to_standard_form` faz, nesta ordem:

1. **Sentido.** Se for de maximização, troca $c$ por $-c$, pois
   $\max c^\top x = -\min (-c)^\top x$, e guarda o sinal em
   `StandardForm.objective_sign`.
2. **Lado direito negativo.** Se $b_i < 0$, multiplica a restrição
   por $-1$ e inverte o sentido ($\leq$ vira $\geq$ e vice-versa).
3. **Folgas e excessos.** Para cada restrição $i$, na ordem:
   - $a_i^\top x \leq b_i$: soma uma folga
     $s_i \geq 0$, ficando $a_i^\top x + s_i = b_i$;
   - $a_i^\top x \geq b_i$: subtrai um excesso
     $e_i \geq 0$, ficando $a_i^\top x - e_i = b_i$;
   - $a_i^\top x = b_i$: nada a fazer.

As colunas de $\tilde{A}$ são as $n$ variáveis originais, na
ordem, seguidas das folgas e dos excessos, na ordem das restrições,
com custo zero. Os nomes das novas variáveis são `s{i}` e `e{i}`,
com `i` começando em 1.

## Fase 1

`StandardForm.phase_one_tableau` acrescenta uma variável artificial $y_i$
por restrição:

$$
\begin{aligned}
\min \quad & y_1 + \cdots + y_m \cr
\text{s.a.} \quad & \tilde{A} \tilde{x} + y = \tilde{b}, \cr
& \tilde{x} \geq 0, \; y \geq 0.
\end{aligned}
$$

A matriz é $[\tilde{A} \;|\; I_m]$, os custos são $(0, \dots, 0,
1, \dots, 1)$ e a base inicial são as artificiais (colunas $N$ a
$N + m - 1$, chamadas `y1`, ..., `ym`), viável porque
$\tilde{b} \geq 0$ e $B = I_m$.

`StandardForm.initial_tableau` então:

1. resolve o problema auxiliar com o `solver` dado (os tableaux vão para
   o logger `simplex.logs.PHASE_ONE_LOGGER`);
2. se o custo ótimo for positivo (maior que `simplex.defaults.TOLERANCE`),
   o problema original é inviável e devolve `None`;
3. senão, todas as artificiais valem zero. Se alguma artificial
   ainda estiver na base (degenerada, na linha $\ell$), tira-a:
   procura uma coluna original $j$ fora da base com
   $(B^{-1} \tilde{A}_j)_\ell \neq 0$ e troca $B(\ell)$ por $j$.
   Se não houver nenhuma, a restrição $\ell$ é redundante
   (combinação das outras) e a linha é removida;
4. devolve o tableau com $\tilde{A}$, $\tilde{b}$, $\tilde{c}$
   (sem as linhas redundantes) e a base encontrada, só com
   colunas originais.

Na troca do passo 3 o pivô pode ser negativo, mas como a
artificial vale zero a solução continua viável.

## Exemplo

O problema de `examples/pequeno.toml`,

$$
\begin{aligned}
\max \quad & 3 x_1 + 2 x_2 \cr
\text{s.a.} \quad & x_1 + x_2 \leq 4, \cr
& x_1 + 3 x_2 \leq 6, \cr
& x_1 \geq 1, \cr
& x \geq 0,
\end{aligned}
$$

tem ótimo $x = (4, 0)$, com valor $12$. Na forma padrão, o $\max$ vira
$\min$ (custos com sinal trocado), as restrições $\leq$ ganham folgas `s1`
e `s2` e a restrição $\geq$ ganha o excesso `e3`. O notebook
[`notebooks/01_simplex.ipynb`](https://github.com/alinespereira/SME0211/blob/main/notebooks/01_simplex.ipynb)
mostra cada passo.
