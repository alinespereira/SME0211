r"""Tableau do método simplex para problemas na forma padrão.

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

**Implementação.** A classe guarda apenas os dados originais $A$, $b$ e
$c$ (que não mudam) e a base; tudo o mais é calculado a partir deles. Como
na "implementação ingênua" da aula 18, $B^{-1}$ nunca é calculada
explicitamente: $x_B = B^{-1} b$ sai de $B x_B = b$, o vetor de
multiplicadores do simplex sai de $p^\top B = c_B^\top$ e a coluna
$u = B^{-1} A_j$ sai de $B u = A_j$, todos resolvidos com
`numpy.linalg.solve`.

**Índices.** Nas aulas os índices começam em $1$; no código, como é usual
em Python, começam em $0$. Assim, `basis[0]` é $B(1)$, `basis[1]` é
$B(2)$ etc.
"""

from collections.abc import Sequence
from typing import Annotated, Self

import numpy as np
import numpy.typing as npt
from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    model_validator,
)

type FloatArray = npt.NDArray[np.float64]
"""Array do numpy com entradas `float64` (de qualquer dimensão)."""

# Tolerância para comparações em ponto flutuante (ex.: x_B >= 0).
TOLERANCE = 1e-9


def _as_float_array(value: object) -> FloatArray:
    """Converte listas, tuplas ou arrays para um array de `float64` somente
    leitura.

    O array é sempre copiado, para que o tableau não compartilhe memória
    com quem o criou, e marcado como somente leitura, para que `A`, `b` e
    `c` não possam ser alterados depois da validação.
    """
    array = np.array(value, dtype=np.float64)
    array.setflags(write=False)
    return array


def _check_ndim(ndim: int, name: str) -> AfterValidator:
    """Cria um validador que exige um array com `ndim` dimensões."""

    def check(value: FloatArray) -> FloatArray:
        if value.ndim != ndim:
            raise ValueError(
                f"esperava {name} ({ndim} dimensões), "
                f"recebeu um array com {value.ndim}."
            )
        return value

    return AfterValidator(check)


type Matrix = Annotated[
    FloatArray, BeforeValidator(_as_float_array), _check_ndim(2, "uma matriz")
]
"""Matriz de reais. Aceita listas de listas e converte para `FloatArray`."""

type Vector = Annotated[
    FloatArray, BeforeValidator(_as_float_array), _check_ndim(1, "um vetor")
]
"""Vetor de reais. Aceita listas e converte para `FloatArray`."""


class Tableau(BaseModel):
    r"""Estado do simplex em uma iteração.

    Guarda $A$, $b$, $c$ e os índices da base; as demais grandezas ($B$,
    $x_B$, $p$, custos reduzidos, colunas do tableau, ...) são calculadas a
    partir deles.
    """

    # arbitrary_types_allowed: numpy.ndarray não é um tipo que o pydantic
    # conheça; isto permite usá-lo nos campos (a conversão é feita pelos
    # validadores acima).
    # frozen: o tableau é imutável; não é possível reatribuir A, b, c ou
    # basis. Para mudar de base, use `with_basis`, que cria um novo
    # Tableau. (Evite model_copy(update=...): ele não roda os validadores.)
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    A: Matrix
    r"""Matriz de restrições $A \in \mathbb{R}^{m \times n}$."""

    b: Vector
    r"""Lado direito das restrições, $b \in \mathbb{R}^m$."""

    c: Vector
    r"""Vetor de custos $c \in \mathbb{R}^n$ do problema de minimização."""

    basis: tuple[int, ...]
    r"""Índices das variáveis básicas: `basis[i]` é $B(i + 1)$, a variável
    básica da linha $i + 1$ do tableau (e da coluna $i + 1$ de $B$)."""

    # ------------------------------------------------------------------
    # Validação
    # ------------------------------------------------------------------

    @model_validator(mode="after")
    def _check_dimensions(self: Self) -> Self:
        r"""Confere se as dimensões são compatíveis.

        Exige $A \in \mathbb{R}^{m \times n}$, $b \in \mathbb{R}^m$,
        $c \in \mathbb{R}^n$ e que `basis` tenha $m$ índices distintos em
        $\lbrace 0, \dots, n - 1 \rbrace$.
        """
        m, n = self.A.shape
        if self.b.shape != (m,):
            raise ValueError(f"b deve ter {m} entradas, tem {self.b.shape}.")
        if self.c.shape != (n,):
            raise ValueError(f"c deve ter {n} entradas, tem {self.c.shape}.")
        if len(self.basis) != m:
            raise ValueError(
                f"A base deve ter {m} índices (um por linha), "
                f"tem {len(self.basis)}."
            )
        if len(set(self.basis)) != m:
            raise ValueError("A base não pode ter índices repetidos.")
        if any(not 0 <= j < n for j in self.basis):
            raise ValueError(f"Índices da base devem estar entre 0 e {n - 1}.")
        return self

    @model_validator(mode="after")
    def _check_basis(self: Self) -> Self:
        r"""Confere se a base é inversível e viável.

        Inversível: $B$ tem posto $m$, ou seja, as colunas
        $A_{B(1)}, \dots, A_{B(m)}$ são linearmente independentes.
        Viável: $x_B = B^{-1} b \geq 0$, a menos da tolerância `TOLERANCE`.
        """
        if np.linalg.matrix_rank(self.B) < self.num_constraints:
            raise ValueError(
                "A matriz base B não é inversível: as colunas escolhidas "
                "para a base são linearmente dependentes."
            )
        if np.any(self.basic_solution < -TOLERANCE):
            raise ValueError(
                "A base não é viável: x_B = B^{-1} b tem entradas negativas."
            )
        return self

    # ------------------------------------------------------------------
    # Troca de base
    # ------------------------------------------------------------------

    def with_basis(self: Self, basis: Sequence[int]) -> "Tableau":
        r"""Devolve um novo tableau com os mesmos $A$, $b$ e $c$ e a base
        `basis`.

        O tableau atual não é alterado. O novo tableau é criado pelo
        construtor, então passa por todas as validações: se a nova matriz
        base $\bar{B}$ não for inversível ou a nova solução básica não for
        viável, é levantado um `pydantic.ValidationError`.

        **Parâmetros:**

        - `basis`: os índices $\bar{B}(1), \dots, \bar{B}(m)$ da nova base.
        """
        return Tableau(A=self.A, b=self.b, c=self.c, basis=tuple(basis))

    # ------------------------------------------------------------------
    # Grandezas derivadas (calculadas a partir de A, b, c e basis)
    # ------------------------------------------------------------------

    @property
    def num_constraints(self: Self) -> int:
        """Número de restrições, $m$."""
        return int(self.A.shape[0])

    @property
    def num_variables(self: Self) -> int:
        """Número de variáveis, $n$."""
        return int(self.A.shape[1])

    @property
    def non_basis(self: Self) -> tuple[int, ...]:
        """Índices das variáveis não básicas, em ordem crescente."""
        in_basis = set(self.basis)
        return tuple(j for j in range(self.num_variables) if j not in in_basis)

    @property
    def B(self: Self) -> FloatArray:  # noqa: N802
        r"""Matriz base $B \in \mathbb{R}^{m \times m}$.

        $$
        B = \begin{bmatrix} A_{B(1)} & \cdots & A_{B(m)} \end{bmatrix}.
        $$
        """
        return self.A[:, list(self.basis)]

    @property
    def basic_costs(self: Self) -> FloatArray:
        r"""Custos das variáveis básicas,
        $c_B = (c_{B(1)}, \dots, c_{B(m)})$.
        """
        return self.c[list(self.basis)]

    @property
    def basic_solution(self: Self) -> FloatArray:
        r"""Valores das variáveis básicas, $x_B = B^{-1} b$ (coluna 0 do
        tableau).

        Calculado resolvendo o sistema $B x_B = b$.
        """
        return np.linalg.solve(self.B, self.b)

    @property
    def multipliers(self: Self) -> FloatArray:
        r"""Vetor de multiplicadores do simplex $p \in \mathbb{R}^m$, com
        $p^\top = c_B^\top B^{-1}$.

        Calculado resolvendo o sistema $p^\top B = c_B^\top$, isto é,
        $B^\top p = c_B$.
        """
        return np.linalg.solve(self.B.T, self.basic_costs)

    @property
    def reduced_costs(self: Self) -> FloatArray:
        r"""Custos reduzidos de todas as variáveis (linha 0 do tableau).

        $$
        \bar{c}^\top = c^\top - c_B^\top B^{-1} A = c^\top - p^\top A,
        $$

        ou seja, $\bar{c}_j = c_j - p^\top A_j$. Os custos reduzidos das
        variáveis básicas são zero. Se $\bar{c}_j \geq 0$ para todo $j$, a
        solução básica viável atual é ótima.
        """
        return self.c - self.multipliers @ self.A

    def column(self: Self, j: int) -> FloatArray:
        r"""Coluna $j$ do tableau, $u = B^{-1} A_j$.

        Quando $x_j$ é a variável que entra na base, $u$ é a coluna pivô,
        usada no teste da razão $\theta^* = \min_{u_i > 0} x_{B(i)} / u_i$.
        Calculada resolvendo o sistema $B u = A_j$.
        """
        return np.linalg.solve(self.B, self.A[:, j])

    @property
    def solution(self: Self) -> FloatArray:
        r"""Solução básica $x \in \mathbb{R}^n$: $x_B = B^{-1} b$ e as
        variáveis não básicas iguais a zero.
        """
        x = np.zeros(self.num_variables)
        x[list(self.basis)] = self.basic_solution
        return x

    @property
    def objective_value(self: Self) -> float:
        r"""Custo da solução atual, $c^\top x = c_B^\top x_B$."""
        return float(self.basic_costs @ self.basic_solution)

    @property
    def table(self: Self) -> FloatArray:
        r"""Tableau completo, uma matriz $(m + 1) \times (n + 1)$.

        $$
        \begin{bmatrix}
        -c_B^\top x_B & \bar{c}^\top \cr
        x_B & B^{-1} A
        \end{bmatrix}.
        $$

        A linha 0 traz o negativo do custo atual e os custos reduzidos; a
        coluna 0 traz os valores das variáveis básicas. Útil para imprimir
        e conferir contas feitas à mão.
        """
        body = np.linalg.solve(self.B, np.column_stack([self.b, self.A]))
        # Somar 0.0 evita imprimir -0.0 quando o custo é zero.
        row0 = np.concatenate(
            [[-self.objective_value + 0.0], self.reduced_costs]
        )
        return np.vstack([row0, body])
