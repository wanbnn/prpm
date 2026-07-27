# Changelog

Todas as mudanças relevantes serão registradas neste arquivo.

## 0.3.0 - 2026-07-27

- Adiciona `prpm login`, `logout` e `whoami` com tokens no keyring do sistema.
- Adiciona identidades Ed25519 geradas localmente e rotação com `prpm key`.
- Adiciona `prpm pack` para construir, validar e assinar releases.
- Adiciona `prpm publish` para publicação segura no PyPI e TestPyPI.
- Adiciona `prpm verify` para conferir manifestos, hashes do PyPI e o RECORD
  interno de wheels.
- Aceita credenciais de CI pelas variáveis `PRPM_PYPI_TOKEN` e
  `PRPM_TESTPYPI_TOKEN`.

## 0.2.1 - 2026-07-27

- Publica o PRPM no PyPI.
- Atualiza a instalação recomendada para `python -m pip install prpm`.
- Moderniza os metadados de licença do pacote.

## 0.2.0 - 2026-07-27

- Substitui a página vazia do `prpm create` por um dashboard funcional.
- Usa componentes PyReact reais e Server-Side Rendering no boilerplate.
- Adiciona servidor de desenvolvimento, API de fragmentos e build estático.
- Inclui filtros, conclusão, criação de tarefas e tema claro/escuro.
- Expande o projeto gerado com componentes, dados, assets e seis testes.

## 0.1.0 - 2026-07-26

- CLI inicial com `init`, `create`, `install`, `add`, `remove`, `update`,
  `list`, `run`, `exec`, `test`, `info`, `lock` e `doctor`.
- Ambientes `.venv` isolados por projeto.
- Integração com `pyproject.toml`, PyPI e o resolvedor do pip.
- Lockfile reprodutível com versões, URLs e hashes.
- Scaffold pronto para aplicações PyReact.
