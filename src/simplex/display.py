r"""Exibição do tableau, com destaque para o pivô de uma iteração.

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

As marcas aparecem no texto puro (`Text.plain`, que vai para arquivos de
log e para os doctests) e as cores só no terminal (veja `simplex.logs`).
"""

from rich.text import Text

from simplex.defaults import TOLERANCE
from simplex.tableau import Tableau

__all__ = [
    "ENTERING_STYLE",
    "LEAVING_STYLE",
    "PIVOT_STYLE",
    "format_number",
    "render_tableau",
]

ENTERING_STYLE = "bold cyan"
"""Estilo (do `rich`) da coluna da variável que entra."""

LEAVING_STYLE = "bold magenta"
"""Estilo (do `rich`) da linha da variável que sai."""

PIVOT_STYLE = "bold black on yellow"
"""Estilo (do `rich`) do elemento pivô."""

_HEADER_STYLE = "bold"
_SEPARATOR = " │"


def format_number(*, value: float) -> str:
    """Formata uma entrada do tableau com até 4 algarismos significativos.

    Valores com módulo até `simplex.defaults.TOLERANCE` (resíduos de ponto
    flutuante, como `-2.22e-16`) aparecem como `0`, e somar `0.0` evita
    imprimir `-0`.

    >>> format_number(value=2 / 3)
    '0.6667'
    >>> format_number(value=-0.0)
    '0'
    >>> format_number(value=-2.22e-16)
    '0'
    >>> format_number(value=1500.0)
    '1500'
    """
    if abs(value) <= TOLERANCE:
        value = 0.0
    return f"{value + 0.0:.4g}"


def render_tableau(
    *,
    tableau: Tableau,
    entering: int | None = None,
    leaving: int | None = None,
) -> Text:
    r"""Monta o tableau completo como texto, destacando a variável que
    entra, a que sai e o pivô.

    **Parâmetros:**

    - `tableau`: o tableau a exibir; os nomes vêm de
      `simplex.tableau.Tableau.variable_names`.
    - `entering`: o índice $j$ da variável que entra, ou `None`.
    - `leaving`: o índice da linha $\ell$ da variável que sai (como em
      `simplex.solver.Solver.leaving_row`, a partir de 0), ou `None`.

    O pivô só é destacado quando `entering` e `leaving` são dados.

    **Exemplo:** o problema do exemplo de `simplex.tableau.Tableau`, em que
    $x_2$ entra e a folga $s_2$ sai, com pivô $3$.

    >>> t = Tableau(
    ...     A=[[1, 1, 1, 0], [1, 3, 0, 1]],
    ...     b=[4, 6],
    ...     c=[-1, -2, 0, 0],
    ...     basis=(2, 3),
    ...     names=("x1", "x2", "s1", "s2"),
    ... )
    >>> print(render_tableau(tableau=t, entering=1, leaving=1).plain)
            │ x1  x2 ↓ s1  s2
    ────────┼─────────────────
      -z 0  │ -1   -2   0   0
    ────────┼─────────────────
      s1 4  │  1    1   1   0
    → s2 6  │  1   [3]  0   1

    Sem `entering` e `leaving`, nada é destacado:

    >>> print(render_tableau(tableau=t.with_basis(basis=(0, 1))).plain)
            │ x1  x2    s1    s2
    ────────┼────────────────────
      -z 5  │  0   0   0.5   0.5
    ────────┼────────────────────
      x1 3  │  1   0   1.5  -0.5
      x2 1  │  0   1  -0.5   0.5
    """
    names = tableau.variable_names
    basic_names = [names[j] for j in tableau.basis]

    # As linhas do tableau são a linha 0 (custos reduzidos) e as linhas
    # i = 0, ..., m - 1 do corpo; usamos i = None para a linha 0. As
    # colunas são a coluna 0 (x_B) e as variáveis j = 0, ..., n - 1; usamos
    # j = None para a coluna 0.
    row_ids: list[int | None] = [None, *range(tableau.num_constraints)]
    col_ids: list[int | None] = [None, *range(tableau.num_variables)]

    def is_leaving(i: int | None) -> bool:
        return leaving is not None and i == leaving

    def is_entering(j: int | None) -> bool:
        return entering is not None and j == entering

    def style_of(*, i: int | None, j: int | None) -> str | None:
        if is_leaving(i) and is_entering(j):
            return PIVOT_STYLE
        if is_entering(j):
            return ENTERING_STYLE
        if is_leaving(i):
            return LEAVING_STYLE
        return None

    # Textos das células. Os números têm um espaço de cada lado, e o pivô
    # troca esses espaços por colchetes, para não desalinhar a coluna.
    labels = [
        ("→ " if is_leaving(i) else "  ")
        + ("-z" if i is None else basic_names[i])
        for i in row_ids
    ]
    headers = [
        "" if j is None else f" {names[j]}" + (" ↓" if is_entering(j) else " ")
        for j in col_ids
    ]
    cells = [
        [
            (
                f"[{format_number(value=float(value))}]"
                if is_leaving(i) and is_entering(j)
                else f" {format_number(value=float(value))} "
            )
            for j, value in zip(col_ids, row, strict=True)
        ]
        for i, row in zip(row_ids, tableau.table, strict=True)
    ]

    label_width = max(len(label) for label in labels)
    widths = [
        max(len(headers[k]), *(len(row[k]) for row in cells))
        for k in range(len(col_ids))
    ]

    def line(*, label: str, texts: list[str], i: int | None) -> Text:
        header = texts is headers
        out = Text()
        out.append(
            label.ljust(label_width),
            style=LEAVING_STYLE if is_leaving(i) else _HEADER_STYLE,
        )
        for k, (j, content) in enumerate(zip(col_ids, texts, strict=True)):
            if k == 1:
                out.append(_SEPARATOR)
            style = style_of(i=i, j=j)
            out.append(" " * (widths[k] - len(content)))
            out.append(
                content, style=style or (_HEADER_STYLE if header else None)
            )
        out.rstrip()
        return out

    rule = Text("─" * (label_width + widths[0]) + "─┼" + "─" * sum(widths[1:]))
    lines = [line(label="", texts=headers, i=None), rule]
    for r, (i, row) in enumerate(zip(row_ids, cells, strict=True)):
        lines.append(line(label=labels[r], texts=row, i=i))
        if i is None:
            lines.append(rule)
    return Text("\n").join(lines)
