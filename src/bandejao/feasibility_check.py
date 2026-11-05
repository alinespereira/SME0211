"""Teste rápido de viabilidade do problema da dieta do almoço.

Monta e resolve o PL com ``scipy.optimize.linprog`` (HiGHS, simplex dual) a
partir dos CSVs de dados e imprime o custo ótimo, as porções escolhidas e a
quantidade obtida de cada nutriente.

Uso::

    python feasibility_check.py <pasta_dos_dados> [nutriente_ignorado ...]

Os nutrientes listados depois da pasta (por exemplo ``calcio_mg``) são
retirados das restrições, para testar quais metas tornam o problema inviável.

Observação: os nomes de colunas e de nutrientes continuam em português,
pois vêm dos cabeçalhos dos CSVs em ``data/``.
"""

import sys

import numpy as np
import pandas as pd
from scipy.optimize import linprog

data_dir = sys.argv[1]
skipped = set(sys.argv[2:])
foods = pd.read_csv(f"{data_dir}/alimentos_estimados.csv")
targets = pd.read_csv(f"{data_dir}/metas_dri_almoco.csv")
groups = pd.read_csv(f"{data_dir}/grupos.csv")

# Custo por grama de alimento pronto (R$/kg -> R$/g).
cost = foods["preco_pronto_R$kg"].values / 1000

# Restrições na forma A_ub @ x <= b_ub.
rows = []
rhs = []
for _, target in targets.iterrows():
    if target.nutriente in skipped:
        continue
    # Tabela TACO dá valores por 100 g.
    per_gram = foods[target.nutriente].values / 100
    if not np.isnan(target.minimo):
        rows.append(-per_gram)
        rhs.append(-target.minimo)
    if not np.isnan(target.maximo):
        rows.append(per_gram)
        rhs.append(target.maximo)
for _, group in groups.iterrows():
    in_group = (foods.grupo == group.grupo).astype(float).values
    rows.append(-in_group)
    rhs.append(-group.massa_min_g)
    rows.append(in_group)
    rhs.append(group.massa_max_g)

result = linprog(
    cost,
    A_ub=np.array(rows),
    b_ub=rhs,
    bounds=list(zip(foods.porcao_min_g, foods.porcao_max_g, strict=True)),
    method="highs-ds",
)
print(result.status, result.message)
if result.status == 0:
    print("custo R$ %.2f" % result.fun)
    for name, grams in zip(foods.alimento, result.x, strict=True):
        if grams > 1e-6:
            print(f"  {name}: {grams:.0f} g")
    for nutrient in targets.nutriente:
        amount = (foods[nutrient].values / 100) @ result.x
        print(f"  {nutrient}: {amount:.1f}")
