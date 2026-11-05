"""Teste rápido de viabilidade do problema da dieta do almoço.

Monta o PL a partir dos modelos (:class:`Food`, :class:`Nutrient` e
:class:`GroupLimit`), resolve com ``scipy.optimize.linprog`` (HiGHS, simplex
dual) e imprime o custo ótimo, as porções escolhidas e a quantidade obtida de
cada nutriente.

Uso::

    python -m bandejao.feasibility_check [--data-dir PASTA] [--skip NUTRIENTE ...]

``--skip`` retira nutrientes das restrições (por exemplo ``--skip calcio``),
para testar quais metas tornam o problema inviável. Aceita tanto o nome do
nutriente (``calcio``) quanto o nome da coluna no CSV (``calcio_mg``).
"""

import argparse
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import numpy.typing as npt
from scipy.optimize import linprog

from bandejao.models.food import Food, GroupLimit, load_foods, load_group_limits
from bandejao.models.nutrient import Nutrient, load_nutrients
from bandejao.settings import Settings

FloatArray = npt.NDArray[np.float64]


@dataclass(frozen=True)
class LinearProgram:
    """PL na forma aceita por ``linprog``: min ``c @ x`` s.a. ``A_ub @ x <= b_ub``.

    Atributos:
        c: custo de cada alimento por grama (coeficientes da função objetivo).
        a_ub: matriz das restrições de desigualdade (uma linha por restrição).
        b_ub: lado direito das restrições de desigualdade.
        bounds: limites ``(mínimo, máximo)`` da porção de cada alimento, em g.
    """

    c: FloatArray
    a_ub: FloatArray
    b_ub: FloatArray
    bounds: list[tuple[float | None, float | None]]


def build_lp(
    foods: Sequence[Food],
    nutrients: Iterable[Nutrient],
    group_limits: Iterable[GroupLimit],
) -> LinearProgram:
    """Monta o PL da dieta de custo mínimo.

    A variável ``x[j]`` é a massa (g) do alimento ``foods[j]`` no prato.
    Restrições de ``≥`` são multiplicadas por -1 para ficarem na forma ``≤``.

    Args:
        foods: alimentos disponíveis no cardápio (variáveis de decisão).
        nutrients: metas nutricionais; cada extremo definido vira uma restrição.
        group_limits: faixas de massa total por grupo de alimentos.
    """
    rows: list[FloatArray] = []
    rhs: list[float] = []

    def add_range(
        coefs: FloatArray, minimum: float | None, maximum: float | None
    ) -> None:
        """Adiciona ``minimum <= coefs @ x <= maximum`` (extremos opcionais)."""
        if minimum is not None:
            rows.append(-coefs)
            rhs.append(-minimum)
        if maximum is not None:
            rows.append(coefs)
            rhs.append(maximum)

    for nutrient in nutrients:
        coefs = np.array([f.nutrient_per_gram(nutrient.type) for f in foods])
        add_range(coefs, nutrient.limit.minimum, nutrient.limit.maximum)

    for group_limit in group_limits:
        in_group = np.array(
            [float(f.group == group_limit.group) for f in foods]
        )
        add_range(in_group, group_limit.mass.minimum, group_limit.mass.maximum)

    return LinearProgram(
        c=np.array([f.cost_per_gram for f in foods]),
        a_ub=np.array(rows),
        b_ub=np.array(rhs),
        bounds=[(f.portion.minimum, f.portion.maximum) for f in foods],
    )


def _is_skipped(nutrient: Nutrient, skipped: set[str]) -> bool:
    """Indica se o nutriente foi pedido em ``--skip`` (por nome ou coluna)."""
    return nutrient.type in skipped or nutrient.column in skipped


def main(argv: Sequence[str] | None = None) -> None:
    """Lê os dados, resolve o PL e imprime o resultado."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Settings().root_dir / "data",
        help="pasta com os CSVs (padrão: data/ na raiz do projeto)",
    )
    parser.add_argument(
        "--skip",
        nargs="*",
        default=[],
        metavar="NUTRIENTE",
        help="nutrientes a retirar das restrições (ex.: calcio)",
    )
    args = parser.parse_args(argv)
    data_dir: Path = args.data_dir
    skipped = set(args.skip)

    foods = load_foods(data_dir / "alimentos_estimados.csv")
    all_nutrients = load_nutrients(data_dir / "metas_dri_almoco.csv")
    nutrients = [n for n in all_nutrients if not _is_skipped(n, skipped)]
    group_limits = load_group_limits(data_dir / "grupos.csv")

    lp = build_lp(foods, nutrients, group_limits)
    result = linprog(
        lp.c, A_ub=lp.a_ub, b_ub=lp.b_ub, bounds=lp.bounds, method="highs-ds"
    )

    print(result.status, result.message)
    x = result.x
    if result.status != 0 or x is None:
        return
    print(f"custo R$ {result.fun:.2f}")
    for food, grams in zip(foods, x, strict=True):
        if grams > 1e-6:
            print(f"  {food.description}: {grams:.0f} g")
    for nutrient in all_nutrients:
        coefs = np.array([f.nutrient_per_gram(nutrient.type) for f in foods])
        amount = float(coefs @ x)
        status = "ok" if nutrient.is_met(amount) else "fora da meta"
        print(f"  {nutrient.column}: {amount:.1f} ({status})")


if __name__ == "__main__":
    main()
