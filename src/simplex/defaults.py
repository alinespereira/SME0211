r"""Valores padrão usados em todo o pacote `simplex`."""

TOLERANCE = 1e-9
r"""Tolerância $\varepsilon$ para comparações em ponto flutuante: por
exemplo, $x_B \geq 0$ é testado como $x_B \geq -\varepsilon$, e
$\bar{c}_j < 0$ como $\bar{c}_j < -\varepsilon$."""

MAX_ITERATIONS = 10_000
"""Número máximo de trocas de base numa execução do
`simplex.solver.Solver` (valor padrão de `max_iterations`)."""
