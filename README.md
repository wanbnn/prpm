<div align="center">

# PRPM

### O package manager do ecossistema PyReact.

[![CI](https://github.com/wanbnn/prpm/actions/workflows/ci.yml/badge.svg)](https://github.com/wanbnn/prpm/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/prpm?logo=pypi&logoColor=white)](https://pypi.org/project/prpm/)
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
python -m pip install prpm
```

Para instalar diretamente a versão de desenvolvimento do GitHub:

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

O comando cria um dashboard SSR completo, estruturado em componentes PyReact,
instala `pyreact-framework` em `.venv` e grava o lockfile. O boilerplate inclui
servidor de desenvolvimento, API interativa, tema claro/escuro, build estático
e testes prontos.

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
| `prpm login` / `logout` | Guarda ou remove um token no keyring |
| `prpm whoami` | Mostra a credencial e chave ativas |
| `prpm key <ação>` | Gera, mostra ou rotaciona a chave Ed25519 |
| `prpm pack` | Constrói, valida e assina wheel/sdist |
| `prpm publish` | Empacota e publica no PyPI |
| `prpm verify <alvo>` | Verifica uma release local ou publicada |
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

## Publicando pacotes

O PRPM utiliza o PyPI como registry. Crie um token em
<https://pypi.org/manage/account/token/> e faça login:

```bash
prpm login
prpm whoami
```

O token é solicitado sem eco no terminal e armazenado pelo keyring do sistema
(Credential Manager no Windows, Keychain no macOS e Secret Service no Linux).
Ele nunca é escrito no projeto ou passado na linha de comando.

O primeiro login também cria uma identidade Ed25519:

```bash
prpm key show
prpm key rotate
```

Prepare uma release sem publicá-la:

```bash
prpm pack
prpm verify dist
```

O diretório `dist/` passa a conter:

```text
pacote-1.0.0-py3-none-any.whl
pacote-1.0.0.tar.gz
prpm-manifest.json
prpm-manifest.sig
```

`prpm-manifest.json` registra hashes SHA-256, tamanhos, dependências e a chave
pública. `prpm-manifest.sig` contém a assinatura Ed25519 do manifesto.

Publique com um único comando:

```bash
prpm publish
```

O comando reconstrói os artefatos, executa `twine check`, valida a assinatura,
publica wheel/sdist e consulta a API do PyPI para comparar os hashes remotos.
Para publicar uma release já empacotada:

```bash
prpm publish --no-build
```

Teste todo o fluxo sem fazer upload:

```bash
prpm publish --dry-run
```

TestPyPI também é suportado:

```bash
prpm login --repository testpypi
prpm publish --repository testpypi
```

Em CI, evite login interativo e use uma variável secreta:

```bash
PRPM_PYPI_TOKEN=pypi-... prpm publish
```

Se o ambiente não oferecer um keyring (comum em runners headless), o `pack`
gera uma chave Ed25519 efêmera para aquela release; a assinatura continua
verificável pelo manifesto, mas a chave não persiste para o próximo build.

No PowerShell:

```powershell
$env:PRPM_PYPI_TOKEN = "pypi-..."
prpm publish
```

Verifique qualquer pacote publicado:

```bash
prpm verify prpm
prpm verify "prpm==0.3.0"
```

A verificação remota compara os arquivos com os SHA-256 publicados pela API do
PyPI e valida cada entrada do `RECORD` dentro do wheel. A assinatura PRPM local
prova que o manifesto e os artefatos continuam associados à mesma chave; nesta
fase, a autorização do mantenedor e do nome do pacote continua sendo fornecida
pelo próprio PyPI.

## Desenvolvimento

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m prpm --help
```

Consulte [CONTRIBUTING.md](CONTRIBUTING.md) para o fluxo de contribuição.

## Licença

MIT. Veja [LICENSE](LICENSE).
