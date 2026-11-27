# SME0211 — Otimização Linear: impressão em uma gráfica

Trabalho da disciplina SME0211 (ICMC-USP). O problema é uma versão relaxada
do artigo *Energy consumption optimization in a printing company* (em
`docs/`): sem as variáveis binárias de designação, o modelo decide quantas
horas cada máquina de impressão e de acabamento fica ligada para atender a
carteira de pedidos, minimizando o tempo de operação ou o consumo de
energia. Ele é resolvido com uma implementação própria do método simplex,
em duas fases.

O código está em `src/`:

- `simplex`: o método simplex, com o `Problem` (o problema como escrito
  no papel, forma padrão e Fase 1), o `Tableau` (base $B$, $x_B = B^{-1}b$,
  custos reduzidos etc.) e o `Solver`, parametrizado pela regra
  anticiclagem (Bland ou lexicográfica);
- `printing_company`: os dados do artigo, o modelo relaxado, o
  pós-processamento (tempo real com setup, energia e custo) e o comando
  `printing-company`.

## 1. Instalar o uv

O projeto usa o [uv](https://docs.astral.sh/uv/) para gerenciar o Python, o
ambiente virtual e as dependências. Não é preciso instalar o Python antes:
o uv baixa a versão indicada em `.python-version` (3.12).

**Linux e macOS**

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows** (PowerShell)

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Outras formas (por exemplo `brew install uv`, `pipx install uv` ou
`winget install --id=astral-sh.uv`) estão na
[documentação do uv](https://docs.astral.sh/uv/getting-started/installation/).

Depois de instalar, abra um terminal novo e confira:

```sh
uv --version
```

## 2. Instalar as dependências

Na raiz do projeto:

```sh
uv sync
```

Esse comando cria o ambiente virtual em `.venv/`, instala o Python se
necessário e instala as dependências do projeto (numpy, pydantic, …) e as
do grupo `dev` (pytest, pdoc, ruff, mypy), que o uv inclui por padrão. As
versões exatas vêm do `uv.lock`, então todos usam o mesmo ambiente.

Para instalar só as dependências do projeto, sem as de desenvolvimento:

```sh
uv sync --no-dev
```

Não é preciso ativar o ambiente virtual: basta prefixar os comandos com
`uv run`, que usa o `.venv/` automaticamente.

## 3. Resolver as carteiras do artigo

```sh
uv run printing-company                  # as três carteiras, minimizando o tempo
uv run printing-company -o energy        # minimizando o consumo de energia
uv run printing-company -o time -o energy   # os dois objetivos, para comparar
uv run printing-company -p 1 -p 3        # só as carteiras I e III
uv run printing-company --debug -p 1     # com o modelo e os tableaux do simplex
uv run printing-company --debug --phase-one -p 1   # inclui a Fase 1
uv run printing-company --help           # todas as opções
```

Cada carteira é resolvida com o menor número de turnos diários que a
torna viável. Para cada uma, o comando mostra uma tabela com uma linha por
máquina: a velocidade $v$, as horas de produção $t$ do modelo, o uso da
capacidade $t/T$, o tempo real $\tau$ (com um setup por máquina ligada),
os metros produzidos, a potência e a energia $E = kW \cdot \tau$. Abaixo
dela, outra tabela traz o valor ótimo do modelo, o tempo real, a energia,
o custo e quanto tempo o simplex levou para resolver o problema (Fases 1 e
2). Com mais de uma carteira, uma tabela compara todas (o custo fica só
na tabela de cada carteira, porque é proporcional à energia):

```text
                 Resumo · objetivo: tempo
┏━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━┓
┃ Carteira      ┃    ótimo ┃  τ (h) ┃   E (kWh) ┃ simplex ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━┩
│ Portfolio I   │  67,75 h │  69,17 │  3.498,43 │  4,2 ms │
│ Portfolio II  │ 162,59 h │ 165,09 │  7.607,13 │  3,9 ms │
│ Portfolio III │ 423,85 h │ 426,85 │ 19.465,85 │  4,1 ms │
└───────────────┴──────────┴────────┴───────────┴─────────┘
τ: tempo real · E: energia · simplex: duração da solução
```

Com `--debug`, cada iteração mostra o tableau com a variável que entra, a
que sai e o pivô em destaque (alargue o terminal para ver o tableau
inteiro).

## 4. Configurar (opcional)

Os parâmetros do cenário (horas de um turno e tarifa de energia) têm os
valores do artigo e podem ser trocados sem mexer no código, por uma
variável de ambiente ou por um arquivo `.env` na raiz do projeto (veja
`printing_company.settings`). A variável de ambiente vence o `.env`.

```sh
cp .env.example .env   # e edite o .env
SHIFT_HOURS=8 uv run printing-company   # ou só numa execução
```

O `.env` está no `.gitignore`. Os testes usam os valores do artigo,
então rode-os sem `.env` (ou com os valores do `.env.example`).

## 5. Rodar os testes

```sh
uv run pytest
```

Os testes ficam em `tests/`, um arquivo por módulo. O log detalhado
(nível DEBUG) de cada execução é gravado em `log/tests.log`.

### CI

A cada push na `main` e a cada pull request, o GitHub Actions
(`.github/workflows/ci.yml`) roda `uv sync`, `ruff check`,
`ruff format --check`, `mypy`, `pyright` e `pytest`.

## 6. Documentação

A documentação da API é gerada com o [pdoc](https://pdoc.dev/). As
docstrings no código são curtas; a teoria de cada módulo (os modelos em
LaTeX, os passos do método, as convenções) fica em `docs/modulos/`, um
arquivo Markdown por módulo, que a docstring do módulo inclui com
`.. include::`. As fórmulas estão em LaTeX e são renderizadas com MathJax
(opção `--math`), que é carregado da internet, então é preciso estar
conectado para ver as fórmulas. O template em `pdoc-templates/` esconde o
`= PydanticUndefined` que o pdoc mostraria nos campos obrigatórios dos
modelos pydantic.

### Com o Makefile

| Comando      | O que faz                                                                                 |
| ------------ | ----------------------------------------------------------------------------------------- |
| `make docs`  | Gera o HTML estático em `docs/api/` (abra `docs/api/index.html` no navegador).            |
| `make serve` | Gera `docs/api/` e abre um servidor local com recarga automática, em http://localhost:8080. |

O `make` já vem no Linux e no macOS. No Windows, use os comandos com
`uv run` abaixo (ou instale o `make`, por exemplo pelo Git Bash ou WSL).

### Com uv run

Os mesmos comandos, sem o Makefile:

```sh
# HTML estático em docs/api/
uv run pdoc --math -t pdoc-templates simplex printing_company -o docs/api

# servidor local com recarga automática
uv run pdoc --math -t pdoc-templates simplex printing_company
```

O servidor abre o navegador sozinho e atualiza a página quando um arquivo
é salvo; para parar, use `Ctrl+C`. Para documentar só um pacote, troque
`simplex printing_company` por `simplex`, por exemplo. A pasta `docs/api/`
é gerada e está no `.gitignore`.

## 7. Notebooks

Os exemplos de uso ficam em `notebooks/`:

- `01_simplex.ipynb`: o pacote `simplex` passo a passo (forma padrão, Fase
  1, tableau, iterações do `Solver` e regras anticiclagem);
- `02_grafica.ipynb`: as carteiras do artigo, os objetivos de tempo e de
  energia e as tabelas do comando `printing-company`.

Cada um tem um botão "Open in Colab" no topo e começa com uma célula
`!pip install` que instala o projeto direto do GitHub; localmente, com o
ambiente do `uv sync`, essa célula pode ser pulada. Para abrir localmente:

```sh
uv run --with jupyterlab jupyter lab notebooks/
```

## Estrutura

```text
docs/                  enunciado e artigo de referência (docs/api/ é gerada)
  modulos/             teoria de cada módulo, incluída na documentação do pdoc
examples/              problemas de exemplo em TOML (simplex.Problem.from_toml)
notebooks/             exemplos de uso (abrem no Colab)
pdoc-templates/        template do pdoc
src/simplex/           método simplex: problem, tableau, solver, display, logs, defaults
src/printing_company/  comando printing-company, settings e report (tabelas da saída)
  problem/             spec (máquinas e carteiras), data (artigo), model, analysis
tests/                 testes (pytest)
log/                   logs dos testes
.env.example           parâmetros do cenário (copie para .env)
```
