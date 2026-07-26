<div align="center">

# PRPM

### O package manager do ecossistema PyReact.

[![CI](https://github.com/wanbnn/prpm/actions/workflows/ci.yml/badge.svg)](https://github.com/wanbnn/prpm/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PyReact](https://img.shields.io/badge/PyReact-1.0.5%2B-7C5CFF)](https://github.com/wanbnn/pyreact)

Crie projetos, instale dependências isoladas, trave versões e execute scripts
com uma única ferramenta.

</div>

## Por que PRPM?

Projetos PyReact são projetos Python. O PRPM aproveita esse ecossistema em vez
de criar um registro incompatível:

- usa o `pyproject.toml` padrão como manifesto;
- resolve pacotes no PyPI (incluindo `pyreact-framework`);
- cria uma `.venv` isolada automaticamente;
- gera `prpm.lock` com as versões resolvidas;
- oferece uma experiência familiar para quem usa npm;
- continua compatível com `pip`, build backends e editores Python.

## Instalação

Requer Python 3.9 ou mais recente.

```bash
python -m pip install git+https://github.com/wanbnn/prpm.git
```

Para desenvolver o próprio PRPM:

```bash
git clone https://github.com/wanbnn/prpm.git
cd prpm
python -m pip install -e ".[dev]"
```

## Início rápido

Crie e prepare uma aplicação PyReact:

```bash
prpm create minha-app
cd minha-app
prpm run dev
```

O comando cria a estrutura recomendada pelo PyReact, instala
`pyreact-framework` em `.venv` e grava o lockfile.

Em um projeto existente, como o
[Agentic Flow](https://github.com/wanbnn/agenticflow):

```bash
git clone https://github.com/wanbnn/agenticflow.git
cd agenticflow
prpm install
prpm exec agentic-flow
```

O PRPM lê as dependências que já estão em `[project].dependencies`.

## Comandos

| Comando | Descrição |
| --- | --- |
| `prpm create <nome>` | Cria e instala uma aplicação PyReact |
| `prpm init [-y]` | Inicializa um `pyproject.toml` |
| `prpm install` / `prpm i` | Resolve, instala e atualiza `prpm.lock` |
| `prpm install --frozen` | Instala exatamente o lockfile; ideal para CI |
| `prpm add <pacote>` | Instala e salva uma dependência |
| `prpm add -D <pacote>` | Instala e salva em `dev` |
| `prpm remove <pacote>` | Remove uma dependência |
| `prpm update [pacotes]` | Atualiza todas ou algumas dependências |
| `prpm list [--all]` | Lista dependências diretas ou todas |
| `prpm run [script]` | Lista ou executa scripts |
| `prpm exec <comando>` | Executa um binário dentro da `.venv` |
| `prpm test` | Atalho para o script `test` |
| `prpm info <pacote>` | Consulta metadados no PyPI |
| `prpm lock [--check]` | Gera ou verifica o lockfile |
| `prpm doctor` | Mostra o estado do ambiente |

Aliases disponíveis: `i`, `rm`, `up` e `ls`.

### Dependências

Especificadores seguem o padrão Python:

```bash
prpm add httpx
prpm add "fastapi>=0.115,<1"
prpm add -D "pytest>=8"
prpm add "componente @ git+https://github.com/usuario/componente.git"
```

Quando nenhuma versão é informada, o PRPM salva a versão mínima resolvida, por
exemplo `httpx>=0.28.1`.

### Scripts

Declare scripts no manifesto:

```toml
[tool.prpm.scripts]
dev = "pyreact dev"
build = "pyreact build"
test = "python -m pytest"
serve = ["python", "-m", "meu_app"]
```

Execute-os sem ativar manualmente a `.venv`:

```bash
prpm run build
prpm test -q
prpm exec python --version
```

## Manifesto e lockfile

O manifesto continua sendo um `pyproject.toml` válido:

```toml
[project]
name = "minha-app"
version = "0.1.0"
requires-python = ">=3.9"
dependencies = ["pyreact-framework>=1.0.5"]

[project.optional-dependencies]
dev = ["pytest>=8"]
```

O `prpm.lock` deve ser versionado. Ele registra a versão exata de cada pacote,
a origem e os hashes fornecidos pelo índice. Em CI, use:

```bash
prpm install --frozen
prpm test
```

Se o manifesto e o lock divergirem, o modo congelado falha antes de instalar.

## Desenvolvimento

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m prpm --help
```

Consulte [CONTRIBUTING.md](CONTRIBUTING.md) para o fluxo de contribuição.

## Licença

MIT. Veja [LICENSE](LICENSE).

