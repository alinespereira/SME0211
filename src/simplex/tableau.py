"""Tableau do método simplex para problemas na forma padrão.

.. include:: ../../docs/modulos/simplex.tableau.md
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

from simplex.defaults import TOLERANCE

__all__ = ["FloatArray", "Matrix", "Tableau", "Vector"]

type FloatArray = npt.NDArray[np.float64]
"""Array do numpy com entradas `float64` (de qualquer dimensão)."""


def _as_float_array(value: object) -> FloatArray:
    """Copia `value` para um array de `float64` somente leitura."""
    array = np.array(value, dtype=np.float64)
    array.setflags(write=False)
    return array


def _check_ndim(*, ndim: int, name: str) -> AfterValidator:
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
    FloatArray,
    BeforeValidator(_as_float_array),
    _check_ndim(ndim=2, name="uma matriz"),
]
"""Matriz de reais. Aceita listas de listas e converte para `FloatArray`."""

type Vector = Annotated[
    FloatArray,
    BeforeValidator(_as_float_array),
    _check_ndim(ndim=1, name="um vetor"),
]
"""Vetor de reais. Aceita listas e converte para `FloatArray`."""


class Tableau(BaseModel):
    """Estado do simplex em uma iteração: $A$, $b$, $c$ e a base (veja o
    módulo).
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

    names: tuple[str, ...] | None = None
    """Nome de cada variável (coluna de $A$), usado só para exibir o
    tableau (veja `simplex.display`). Se `None`, os nomes são `x1`, ...,
    `xn` (veja `variable_names`)."""

    # ------------------------------------------------------------------
    # Validação
    # ------------------------------------------------------------------

    @model_validator(mode="after")
    def _check_dimensions(self: Self) -> Self:
        """Confere as dimensões de $A$, $b$, $c$, `basis` e `names`."""
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
        if self.names is not None:
            if len(self.names) != n:
                raise ValueError(
                    f"names deve ter {n} nomes, tem {len(self.names)}."
                )
            if len(set(self.names)) != n:
                raise ValueError("names não pode ter nomes repetidos.")
        return self

    @model_validator(mode="after")
    def _check_basis(self: Self) -> Self:
        r"""Confere se $B$ é inversível e $x_B \geq 0$."""
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

    def with_basis(self: Self, *, basis: Sequence[int]) -> "Tableau":
        """Novo tableau com os mesmos dados e a base `basis` (validada)."""
        return Tableau(
            A=self.A,
            b=self.b,
            c=self.c,
            basis=tuple(basis),
            names=self.names,
        )

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
    def variable_names(self: Self) -> tuple[str, ...]:
        """`names`, ou `x1`, ..., `xn` se não foram dados."""
        if self.names is not None:
            return self.names
        return tuple(f"x{j + 1}" for j in range(self.num_variables))

    @property
    def non_basis(self: Self) -> tuple[int, ...]:
        """Índices das variáveis não básicas, em ordem crescente."""
        in_basis = set(self.basis)
        return tuple(j for j in range(self.num_variables) if j not in in_basis)

    @property
    def B(self: Self) -> FloatArray:  # noqa: N802
        r"""Matriz base $B = [A_{B(1)} \cdots A_{B(m)}] \in \mathbb{R}^{m \times m}$."""
        return self.A[:, list(self.basis)]

    @property
    def basic_costs(self: Self) -> FloatArray:
        r"""Custos das variáveis básicas, $c_B \in \mathbb{R}^m$."""
        return self.c[list(self.basis)]

    @property
    def basic_solution(self: Self) -> FloatArray:
        r"""Valores das variáveis básicas, $x_B = B^{-1} b \in \mathbb{R}^m$ (só as
        $m$ básicas; o vetor completo é `solution`)."""
        return np.linalg.solve(self.B, self.b)

    @property
    def multipliers(self: Self) -> FloatArray:
        r"""Vetor multiplicador $p \in \mathbb{R}^m$, $p^\top = c_B^\top B^{-1}$."""
        return np.linalg.solve(self.B.T, self.basic_costs)

    @property
    def reduced_costs(self: Self) -> FloatArray:
        r"""Custos reduzidos, $\bar{c}^\top = c^\top - p^\top A \in \mathbb{R}^n$, com
        $p^\top = c_B^\top B^{-1}$ (vetor multiplicador)."""
        return self.c - self.multipliers @ self.A

    def column(self: Self, *, j: int) -> FloatArray:
        """Coluna $j$ do tableau, $u = B^{-1} A_j$."""
        return np.linalg.solve(self.B, self.A[:, j])

    @property
    def solution(self: Self) -> FloatArray:
        r"""Solução atual $x \in \mathbb{R}^n$: $x_B = B^{-1}b \in \mathbb{R}^m$ nas
        básicas e $x_N = 0$."""
        x = np.zeros(self.num_variables)
        x[list(self.basis)] = self.basic_solution
        return x

    @property
    def objective_value(self: Self) -> float:
        r"""Custo da solução atual, $c^\top x = c_B^\top x_B$."""
        return float(self.basic_costs @ self.basic_solution)

    @property
    def table(self: Self) -> FloatArray:
        r"""Tableau completo, uma matriz $(m + 1) \times (n + 1)$."""
        body = np.linalg.solve(self.B, np.column_stack([self.b, self.A]))
        # Somar 0.0 evita imprimir -0.0 quando o custo é zero.
        row0 = np.concatenate(
            [[-self.objective_value + 0.0], self.reduced_costs]
        )
        return np.vstack([row0, body])
