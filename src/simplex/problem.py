r"""Descrição de problemas de otimização linear e conversão para a forma
padrão.

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

`Problem.solve` junta os quatro passos.
"""

import tomllib
from pathlib import Path
from typing import Literal, Self

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator

from simplex.defaults import TOLERANCE
from simplex.solver import Result, Solver, Status
from simplex.tableau import FloatArray, Matrix, Tableau, Vector

__all__ = [
    "Constraint",
    "ConstraintSense",
    "ObjectiveSense",
    "Problem",
    "Solution",
    "StandardForm",
]

type ConstraintSense = Literal["<=", ">=", "=="]
"""Sentido de uma restrição: $\\leq$, $\\geq$ ou $=$."""

type ObjectiveSense = Literal["min", "max"]
"""Sentido da otimização."""

_FLIPPED_SENSE: dict[ConstraintSense, ConstraintSense] = {
    "<=": ">=",
    ">=": "<=",
    "==": "==",
}
"""Sentido da restrição depois de multiplicá-la por $-1$."""


class Constraint(BaseModel):
    r"""Uma restrição $a_i^\top x \;\square_i\; b_i$.

    **Exemplo:** $x_1 + 3 x_2 \leq 6$.

    >>> k = Constraint(coefs=[1, 3], sense="<=", rhs=6)
    >>> k.coefs.tolist()
    [1.0, 3.0]
    >>> k.rhs
    6.0
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    coefs: Vector
    r"""Coeficientes $a_i \in \mathbb{R}^n$."""

    sense: ConstraintSense
    r"""Sentido $\square_i$: `"<="`, `">="` ou `"=="`."""

    rhs: float
    r"""Lado direito $b_i$ (pode ser negativo)."""


class Problem(BaseModel):
    r"""Problema de otimização linear, como escrito no papel.

    **Exemplo:** o problema de `examples/pequeno.toml`,

    $$
    \begin{aligned}
    \max \quad & 3 x_1 + 2 x_2 \cr
    \text{s.a.} \quad & x_1 + x_2 \leq 4, \cr
    & x_1 + 3 x_2 \leq 6, \cr
    & x_1 \geq 1, \cr
    & x \geq 0.
    \end{aligned}
    $$

    >>> p = Problem(
    ...     sense="max",
    ...     c=[3, 2],
    ...     constraints=(
    ...         Constraint(coefs=[1, 1], sense="<=", rhs=4),
    ...         Constraint(coefs=[1, 3], sense="<=", rhs=6),
    ...         Constraint(coefs=[1, 0], sense=">=", rhs=1),
    ...     ),
    ... )
    >>> p.variable_names
    ('x1', 'x2')
    >>> solution = p.solve()
    >>> solution.status
    <Status.OPTIMAL: 'optimal'>
    >>> solution.x.tolist()
    [4.0, 0.0]
    >>> solution.objective
    12.0

    O mesmo problema pode ser lido de um arquivo com
    `Problem.from_toml(path="examples/pequeno.toml")`.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    sense: ObjectiveSense = "min"
    """Minimizar ou maximizar."""

    c: Vector
    r"""Vetor de custos $c \in \mathbb{R}^n$."""

    constraints: tuple[Constraint, ...] = Field(min_length=1)
    """Restrições, na ordem em que aparecem."""

    names: tuple[str, ...] | None = None
    """Nomes das variáveis (opcional). Sem nomes, usa-se `x1`, ..., `xn`."""

    @model_validator(mode="after")
    def _check_dimensions(self: Self) -> Self:
        """Confere se todas as restrições e os nomes têm $n$ entradas."""
        n = self.num_variables
        for i, constraint in enumerate(self.constraints, start=1):
            if constraint.coefs.shape != (n,):
                raise ValueError(
                    f"A restrição {i} tem {constraint.coefs.shape[0]} "
                    f"coeficientes, mas c tem {n}."
                )
        if self.names is not None:
            if len(self.names) != n:
                raise ValueError(
                    f"names tem {len(self.names)} nomes, mas c tem {n}."
                )
            if len(set(self.names)) != n:
                raise ValueError("names não pode ter nomes repetidos.")
        return self

    @property
    def num_variables(self: Self) -> int:
        """Número de variáveis, $n$."""
        return int(self.c.shape[0])

    @property
    def num_constraints(self: Self) -> int:
        """Número de restrições, $m$."""
        return len(self.constraints)

    @property
    def variable_names(self: Self) -> tuple[str, ...]:
        """`names`, ou `x1`, ..., `xn` se não foram dados."""
        if self.names is not None:
            return self.names
        return tuple(f"x{j}" for j in range(1, self.num_variables + 1))

    # ------------------------------------------------------------------
    # Leitura
    # ------------------------------------------------------------------

    @classmethod
    def from_toml(cls: type[Self], *, path: Path | str) -> Self:
        """Lê um problema de um arquivo TOML.

        O arquivo tem as mesmas chaves que os campos da classe; cada
        restrição é uma tabela `[[constraints]]`:

            sense = "max"
            c = [3, 2]
            names = ["x1", "x2"]

            [[constraints]]
            coefs = [1, 1]
            sense = "<="
            rhs = 4

        Dica: `tomllib.load` (com o arquivo aberto em modo binário) devolve
        um `dict`, e `cls.model_validate` cria e valida o problema.
        """
        path = Path(path)
        with path.open(mode="rb") as fp:
            return cls.model_validate(tomllib.load(fp))

    # ------------------------------------------------------------------
    # Conversão e resolução
    # ------------------------------------------------------------------

    def to_standard_form(self: Self) -> "StandardForm":
        r"""Converte o problema para a forma padrão.

        1. **Sentido.** Se for de maximização, troque $c$ por $-c$, pois
           $\max c^\top x = -\min (-c)^\top x$; guarde o sinal em
           `StandardForm.objective_sign`.
        2. **Lado direito negativo.** Se $b_i < 0$, multiplique a restrição
           por $-1$ e inverta o sentido ($\leq$ vira $\geq$ e vice-versa).
        3. **Folgas e excessos.** Para cada restrição $i$, na ordem:
           - $a_i^\top x \leq b_i$: some uma folga
             $s_i \geq 0$, ficando $a_i^\top x + s_i = b_i$;
           - $a_i^\top x \geq b_i$: subtraia um excesso
             $e_i \geq 0$, ficando $a_i^\top x - e_i = b_i$;
           - $a_i^\top x = b_i$: nada a fazer.

        As colunas de $\tilde{A}$ são as $n$ variáveis originais, na
        ordem, seguidas das folgas e dos excessos, na ordem das restrições,
        com custo zero. Os nomes das novas variáveis são `s{i}` e `e{i}`,
        com `i` começando em 1.
        """
        m = self.num_constraints
        sign: Literal[1, -1] = -1 if self.sense == "max" else 1

        rows: list[FloatArray] = []
        rhs: list[float] = []
        extra_columns: list[FloatArray] = []
        names = list(self.variable_names)

        for i, constraint in enumerate(self.constraints):
            coefs, b_i, sense = (
                constraint.coefs,
                constraint.rhs,
                constraint.sense,
            )

            # Passo 2: lado direito negativo -> multiplica a linha por -1.
            if b_i < 0:
                coefs, b_i = -coefs, -b_i
                sense = _FLIPPED_SENSE[sense]
            rows.append(coefs)
            rhs.append(b_i)

            # Passo 3: folga (+1) para <=, excesso (-1) para >=.
            if sense != "==":
                column = np.zeros(m)
                column[i] = 1.0 if sense == "<=" else -1.0
                extra_columns.append(column)
                names.append(f"{'s' if sense == '<=' else 'e'}{i + 1}")

        matrix = np.vstack(rows)
        if extra_columns:
            matrix = np.hstack([matrix, np.column_stack(extra_columns)])

        # Passo 1: max c^T x = -min (-c)^T x; folgas e excessos custam 0.
        c = np.concatenate([sign * self.c, np.zeros(len(extra_columns))])

        return StandardForm(
            A=matrix,
            b=np.array(rhs),
            c=c,
            names=tuple(names),
            num_original=self.num_variables,
            objective_sign=sign,
        )

    def solve(self: Self, *, solver: Solver | None = None) -> "Solution":
        """Resolve o problema: forma padrão, Fase 1, Fase 2 e volta às
        variáveis originais.

        **Parâmetros:**

        - `solver`: o `Solver` usado nas duas fases; se `None`, usa
          `Solver()` (regra de Bland).

        **Devolve:** uma `Solution`. Se a Fase 1 mostrar que o problema é
        inviável, o status é `Status.INFEASIBLE`.
        """
        solver = solver if solver is not None else Solver()
        standard = self.to_standard_form()

        # Fase 1: base viável inicial (ou prova de inviabilidade).
        tableau = standard.initial_tableau(solver=solver)
        if tableau is None:
            return Solution(status=Status.INFEASIBLE)

        # Fase 2: o simplex a partir dessa base.
        result = solver.solve(tableau=tableau)
        final = result.tableau
        return Solution(
            status=result.status,
            x=standard.original_solution(x=final.solution),
            objective=standard.original_objective(value=final.objective_value),
            result=result,
        )


class StandardForm(BaseModel):
    r"""Problema na forma padrão $\min \tilde{c}^\top \tilde{x}$,
    $\tilde{A} \tilde{x} = \tilde{b}$, $\tilde{x} \geq 0$, com
    $\tilde{b} \geq 0$, mais o que é preciso para voltar ao problema
    original.

    **Exemplo:** a forma padrão do problema do exemplo de `Problem`. O
    $\max$ vira $\min$ (custos com sinal trocado), as restrições
    $\leq$ ganham folgas `s1` e `s2` e a restrição $\geq$ ganha o excesso
    `e3`.

    >>> p = Problem(
    ...     sense="max",
    ...     c=[3, 2],
    ...     constraints=(
    ...         Constraint(coefs=[1, 1], sense="<=", rhs=4),
    ...         Constraint(coefs=[1, 3], sense="<=", rhs=6),
    ...         Constraint(coefs=[1, 0], sense=">=", rhs=1),
    ...     ),
    ... )
    >>> sf = p.to_standard_form()
    >>> sf.names
    ('x1', 'x2', 's1', 's2', 'e3')
    >>> for row in sf.A:
    ...     print(row.tolist())
    [1.0, 1.0, 1.0, 0.0, 0.0]
    [1.0, 3.0, 0.0, 1.0, 0.0]
    [1.0, 0.0, 0.0, 0.0, -1.0]
    >>> sf.c.tolist()
    [-3.0, -2.0, 0.0, 0.0, 0.0]
    >>> sf.objective_sign
    -1

    A Fase 1 começa com as artificiais (colunas 5, 6 e 7) na base e
    termina numa base viável só com colunas de $\tilde{A}$:

    >>> sf.phase_one_tableau().basis
    (5, 6, 7)
    >>> t = sf.initial_tableau(solver=Solver())
    >>> all(j < 5 for j in t.basis)
    True
    >>> sf.original_solution(x=t.solution).shape
    (2,)
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    A: Matrix
    r"""Matriz $\tilde{A} \in \mathbb{R}^{m \times N}$, com $N \geq n$."""

    b: Vector
    r"""Lado direito $\tilde{b} \in \mathbb{R}^m$, com $\tilde{b} \geq 0$."""

    c: Vector
    r"""Custos $\tilde{c} \in \mathbb{R}^N$ (minimização)."""

    names: tuple[str, ...]
    """Nome de cada coluna de $\\tilde{A}$: as originais, depois as folgas
    (`s{i}`) e os excessos (`e{i}`)."""

    num_original: int = Field(ge=1)
    """Número $n$ de variáveis originais: as $n$ primeiras colunas."""

    objective_sign: Literal[1, -1] = 1
    r"""$+1$ se o problema original é de minimização e $-1$ se é de
    maximização: o valor original é `objective_sign` vezes o valor de
    $\tilde{c}^\top \tilde{x}$."""

    @model_validator(mode="after")
    def _check(self: Self) -> Self:
        r"""Confere as dimensões e que $\tilde{b} \geq 0$."""
        m, n = self.A.shape
        if self.b.shape != (m,):
            raise ValueError(f"b deve ter {m} entradas, tem {self.b.shape}.")
        if self.c.shape != (n,):
            raise ValueError(f"c deve ter {n} entradas, tem {self.c.shape}.")
        if len(self.names) != n:
            raise ValueError(
                f"names deve ter {n} nomes, tem {len(self.names)}."
            )
        if self.num_original > n:
            raise ValueError(
                "num_original não pode passar do número de colunas."
            )
        if (self.b < -TOLERANCE).any():
            raise ValueError("Na forma padrão, b deve ser não negativo.")
        return self

    # ------------------------------------------------------------------
    # Fase 1
    # ------------------------------------------------------------------

    def phase_one_tableau(self: Self) -> Tableau:
        r"""Tableau inicial do problema auxiliar da Fase 1.

        Acrescenta uma variável artificial $y_i$ por restrição:

        $$
        \begin{aligned}
        \min \quad & y_1 + \cdots + y_m \cr
        \text{s.a.} \quad & \tilde{A} \tilde{x} + y = \tilde{b}, \cr
        & \tilde{x} \geq 0, \; y \geq 0.
        \end{aligned}
        $$

        A matriz é $[\tilde{A} \;|\; I_m]$, os custos são $(0, \dots, 0,
        1, \dots, 1)$ e a base inicial são as artificiais (colunas $N$ a
        $N + m - 1$), viável porque $\tilde{b} \geq 0$ e $B = I_m$.
        """
        num_constraints, num_variables = self.A.shape
        A = np.hstack([self.A, np.eye(num_constraints)])  # noqa: N806
        b = self.b
        # Custo 0 nas variáveis da forma padrão e 1 nas artificiais.
        c = np.concatenate([np.zeros(num_variables), np.ones(num_constraints)])
        basis = tuple(range(num_variables, num_variables + num_constraints))
        return Tableau(A=A, b=b, c=c, basis=basis)

    def initial_tableau(self: Self, *, solver: Solver) -> Tableau | None:
        r"""Fase 1: encontra uma base viável para a forma padrão.

        1. Resolva o problema auxiliar (`phase_one_tableau`) com `solver`.
        2. Se o custo ótimo for positivo (maior que `TOLERANCE`), o
           problema original é inviável: devolva `None`.
        3. Senão, todas as artificiais valem zero. Se alguma artificial
           ainda estiver na base (degenerada, na linha $\ell$), tire-a:
           procure uma coluna original $j$ fora da base com
           $(B^{-1} \tilde{A}_j)_\ell \neq 0$ e troque $B(\ell)$ por $j$.
           Se não houver nenhuma, a restrição $\ell$ é redundante
           (combinação das outras): remova essa linha.
        4. Devolva o tableau com $\tilde{A}$, $\tilde{b}$, $\tilde{c}$
           (sem as linhas redundantes) e a base encontrada, só com
           colunas originais.

        Na troca do passo 3 o pivô pode ser negativo, mas como a
        artificial vale zero a solução continua viável.
        """
        num_constraints, num_variables = self.A.shape

        # 1. Resolve o problema auxiliar.
        tableau = solver.solve(tableau=self.phase_one_tableau()).tableau

        # 2. Custo ótimo positivo: alguma artificial não pode ser zerada.
        if tableau.objective_value > TOLERANCE:
            return None

        # 3. Tira da base as artificiais que sobraram (todas valem zero).
        basis = list(tableau.basis)
        redundant: list[int] = []
        for ell in range(num_constraints):
            if basis[ell] < num_variables:
                continue
            # Linha ell de B^{-1} [A | I], só nas colunas originais.
            row = np.linalg.solve(tableau.B, tableau.A)[ell, :num_variables]
            candidates = [
                j
                for j in range(num_variables)
                if j not in basis and abs(row[j]) > TOLERANCE
            ]
            if candidates:
                basis[ell] = candidates[0]
                tableau = tableau.with_basis(basis=basis)
            else:
                redundant.append(ell)

        # 4. Remove as linhas redundantes e volta aos dados originais.
        keep = [i for i in range(num_constraints) if i not in redundant]
        return Tableau(
            A=self.A[keep],
            b=self.b[keep],
            c=self.c,
            basis=tuple(basis[i] for i in keep),
        )

    # ------------------------------------------------------------------
    # Volta ao problema original
    # ------------------------------------------------------------------

    def original_solution(self: Self, *, x: FloatArray) -> FloatArray:
        r"""Restringe uma solução $\tilde{x}$ da forma padrão às $n$
        variáveis originais (descarta folgas e excessos)."""
        return x[: self.num_original]

    def original_objective(self: Self, *, value: float) -> float:
        r"""Converte o valor $\tilde{c}^\top \tilde{x}$ no valor da função
        objetivo original, multiplicando por `objective_sign`."""
        return self.objective_sign * value


class Solution(BaseModel):
    r"""Resultado de `Problem.solve`, nas variáveis originais.

    **Exemplo:** um problema inviável ($x_1 \leq 1$ e $x_1 \geq 2$).

    >>> p = Problem(
    ...     c=[1],
    ...     constraints=(
    ...         Constraint(coefs=[1], sense="<=", rhs=1),
    ...         Constraint(coefs=[1], sense=">=", rhs=2),
    ...     ),
    ... )
    >>> solution = p.solve()
    >>> solution.status
    <Status.INFEASIBLE: 'infeasible'>
    >>> solution.x is None and solution.objective is None
    True
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    status: Status
    """Como terminou: ótimo, ilimitado, inviável ou limite de iterações."""

    x: Vector | None = None
    """Valores das variáveis originais na última base (`None` se
    inviável)."""

    objective: float | None = None
    """Valor da função objetivo original em `x` (`None` se inviável)."""

    result: Result | None = None
    """Resultado da Fase 2, com o tableau final (`None` se inviável)."""
