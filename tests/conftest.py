"""Problemas de exemplo usados nos testes do tableau e do solver.

Todos estão na forma padrão: min c^T x, Ax = b, x >= 0.
"""

# O Tableau aceita listas em A, b e c (o pydantic converte para arrays),
# mas o pyright só vê o tipo declarado (np.ndarray) e reclamaria aqui.
# pyright: reportArgumentType=false

import numpy as np
import pytest

from simplex.tableau import Tableau


@pytest.fixture
def small() -> Tableau:
    """Exemplo pequeno, na base das folgas.

    min -x1 - 2 x2
    s.a. x1 +   x2 + s1      = 4
         x1 + 3 x2      + s2 = 6

    Variáveis (índices do código): x1 = 0, x2 = 1, s1 = 2, s2 = 3.
    Ótimo: x1 = 3, x2 = 1, custo -5, base {0, 1}.
    """
    return Tableau(
        A=[[1, 1, 1, 0], [1, 3, 0, 1]],
        b=[4, 6],
        c=[-1, -2, 0, 0],
        basis=(2, 3),
    )


@pytest.fixture
def unbounded() -> Tableau:
    """Problema ilimitado.

    min -x1
    s.a. x1 - x2 + s = 1

    x1 e x2 podem crescer juntos sem limite: o custo ótimo é -infinito.
    """
    return Tableau(A=[[1, -1, 1]], b=[1], c=[-1, 0, 0], basis=(2,))


@pytest.fixture
def beale() -> Tableau:
    """Exemplo de Beale (Bertsimas e Tsitsiklis, exemplo 3.6).

    Com a regra do maior custo reduzido negativo e desempate pelo menor
    índice, o simplex cicla neste problema. As folgas são as três
    primeiras colunas, então as linhas do tableau inicial são
    lexicograficamente positivas.

    Ótimo: custo -5/4, em x = (3/4, 0, 0, 1, 0, 1, 0).
    """
    return Tableau(
        A=[
            [1, 0, 0, 1 / 4, -8, -1, 9],
            [0, 1, 0, 1 / 2, -12, -1 / 2, 3],
            [0, 0, 1, 0, 0, 1, 0],
        ],
        b=[0, 0, 1],
        c=[0, 0, 0, -3 / 4, 20, -1 / 2, 6],
        basis=(0, 1, 2),
    )


@pytest.fixture
def aula21() -> Tableau:
    """Tableau do exemplo da regra lexicográfica da aula 21.

    As linhas do tableau (coluna 0 e colunas 1 a 3) são

        1 | 0  5   3
        2 | 4  6  -1
        3 | 0  7   9

    e a coluna pivô é a terceira (índice 2 no código), com u = (3, -1, 9).
    Há empate no teste da razão entre a primeira e a terceira linhas
    (1/3 = 3/9). As colunas da identidade ficam no fim, com
    basis = (3, 4, 5), para não interferirem no desempate.
    """
    a = np.array(
        [
            [0, 5, 3, 1, 0, 0],
            [4, 6, -1, 0, 1, 0],
            [0, 7, 9, 0, 0, 1],
        ]
    )
    return Tableau(A=a, b=[1, 2, 3], c=[0, 0, -1, 0, 0, 0], basis=(3, 4, 5))


@pytest.fixture
def aula21_reversed() -> Tableau:
    """Mesmo tableau de `aula21`, mas com a variável básica da primeira
    linha de índice maior que a da terceira linha (basis = (5, 4, 3)).

    No empate entre a primeira e a terceira linhas, Bland escolhe a de
    menor B(l), que agora é a terceira.
    """
    a = np.array(
        [
            [0, 5, 3, 0, 0, 1],
            [4, 6, -1, 0, 1, 0],
            [0, 7, 9, 1, 0, 0],
        ]
    )
    return Tableau(A=a, b=[1, 2, 3], c=[0, 0, -1, 0, 0, 0], basis=(5, 4, 3))
