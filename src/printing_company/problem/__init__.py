r"""Dados do problema da gráfica.

- `printing_company.problem.spec`: os modelos (máquinas de impressão e de
  acabamento, demandas e carteiras de pedidos), com a notação do artigo;
- `printing_company.problem.data`: as instâncias do artigo (Tabelas 1 a
  4): 5 impressoras, 3 máquinas de acabamento e 3 carteiras de pedidos;
- `printing_company.problem.model`: o modelo linear relaxado (tempo de
  operação), montado como um `simplex.Problem` por
  `printing_company.problem.model.build_problem`;
- `printing_company.problem.analysis`: o pós-processamento da solução
  (tempo real com setup, consumo e custo de energia).
"""
