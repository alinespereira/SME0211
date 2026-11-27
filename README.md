# SME0211 — Otimização Linear: impressão em uma gráfica

Trabalho da disciplina SME0211 (ICMC-USP). O problema é uma versão relaxada
do artigo *Energy consumption optimization in a printing company* (em
`docs/`), focada no tempo de impressão, resolvida com uma implementação
própria do método simplex.

O código está em `src/`:

- `simplex`: o método simplex, com o `Tableau` (base, $B^{-1}b$, custos
  reduzidos etc.) e o `Solver`, parametrizado pela regra anticiclagem
  (Bland ou lexicográfica);
- `printing_company`: o modelo do problema da gráfica.

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

## 3. Rodar os testes

```sh
uv run pytest
```

Os testes ficam em `tests/`. O log detalhado (nível DEBUG) de cada execução
é gravado em `log/tests.log`.

## 4. Documentação

A documentação da API é gerada com o [pdoc](https://pdoc.dev/) a partir
das docstrings. As fórmulas estão em LaTeX e são renderizadas com MathJax
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

## Estrutura

```text
docs/              enunciado e artigo de referência (docs/api/ é gerada)
pdoc-templates/    template do pdoc
src/simplex/       método simplex (Tableau, Solver)
src/printing_company/  modelo do problema da gráfica
tests/             testes (pytest)
log/               logs dos testes
```
