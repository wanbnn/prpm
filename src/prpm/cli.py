from __future__ import annotations

import argparse
import getpass
import json
import os
import platform
import shlex
import sys
from pathlib import Path

from packaging.requirements import Requirement

from prpm import __version__
from prpm.auth import delete_token, has_token, save_token
from prpm.console import console
from prpm.environment import ProjectEnvironment
from prpm.errors import PrpmError
from prpm.lockfile import Lockfile
from prpm.manager import PackageManager, package_info
from prpm.manifest import MANIFEST_NAME, Manifest, make_manifest
from prpm.publisher import publish
from prpm.release import build_release
from prpm.repository import get_repository
from prpm.scaffold import create_project
from prpm.signing import generate_identity, load_identity
from prpm.verification import verify_local, verify_remote


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="prpm",
        description="Gerenciador de pacotes e projetos para PyReact.",
    )
    parser.add_argument("--version", action="version", version=f"prpm {__version__}")
    commands = parser.add_subparsers(dest="command", metavar="comando")

    init = commands.add_parser("init", help="Cria um pyproject.toml")
    init.add_argument("name", nargs="?", help="Nome do projeto")
    init.add_argument("-y", "--yes", action="store_true", help="Aceita os padrões")
    init.add_argument("--force", action="store_true", help="Sobrescreve o manifesto")

    create = commands.add_parser("create", help="Cria uma aplicação PyReact")
    create.add_argument("name", help="Nome/diretório do projeto")
    create.add_argument("--no-install", action="store_true", help="Não instala dependências")

    install = commands.add_parser("install", aliases=["i"], help="Instala as dependências")
    install.add_argument("--frozen", action="store_true", help="Exige o lockfile atual")
    install.add_argument("--production", action="store_true", help="Ignora dependências dev")

    add = commands.add_parser("add", help="Adiciona dependências")
    add.add_argument("packages", nargs="+")
    add.add_argument("-D", "--dev", action="store_true")

    remove = commands.add_parser("remove", aliases=["rm"], help="Remove dependências")
    remove.add_argument("packages", nargs="+")
    remove.add_argument("-D", "--dev", action="store_true")

    update = commands.add_parser("update", aliases=["up"], help="Atualiza dependências")
    update.add_argument("packages", nargs="*")
    update.add_argument("--production", action="store_true")

    listing = commands.add_parser("list", aliases=["ls"], help="Lista pacotes instalados")
    listing.add_argument("--all", action="store_true", help="Inclui transitivas")
    listing.add_argument("--json", action="store_true")

    run = commands.add_parser("run", help="Executa um script do projeto")
    run.add_argument("script", nargs="?", help="Nome do script")
    run.add_argument("args", nargs=argparse.REMAINDER)

    execute = commands.add_parser("exec", help="Executa na .venv")
    execute.add_argument("args", nargs=argparse.REMAINDER)

    test = commands.add_parser("test", help="Atalho para `prpm run test`")
    test.add_argument("args", nargs=argparse.REMAINDER)

    info = commands.add_parser("info", help="Consulta um pacote no PyPI")
    info.add_argument("package")
    info.add_argument("--json", action="store_true")

    lock = commands.add_parser("lock", help="Gera ou verifica prpm.lock")
    lock.add_argument("--check", action="store_true")

    login = commands.add_parser("login", help="Guarda um token do PyPI com segurança")
    login.add_argument(
        "--repository", choices=["pypi", "testpypi"], default="pypi"
    )
    login.add_argument(
        "--token-stdin",
        action="store_true",
        help="Lê o token da entrada padrão",
    )

    logout = commands.add_parser("logout", help="Remove a credencial guardada")
    logout.add_argument(
        "--repository", choices=["pypi", "testpypi"], default="pypi"
    )

    whoami = commands.add_parser("whoami", help="Mostra identidade e autenticação")
    whoami.add_argument(
        "--repository", choices=["pypi", "testpypi"], default="pypi"
    )
    whoami.add_argument("--json", action="store_true")

    key = commands.add_parser("key", help="Gerencia a chave de assinatura")
    key_commands = key.add_subparsers(dest="key_command", metavar="ação")
    key_commands.add_parser("show", help="Exibe a chave pública")
    key_commands.add_parser("generate", help="Gera a chave se estiver ausente")
    key_commands.add_parser("rotate", help="Substitui a chave atual")

    pack = commands.add_parser("pack", help="Constrói e assina uma release")
    pack.add_argument("--out-dir", default="dist")
    pack.add_argument("--force", action="store_true")
    pack.add_argument("--json", action="store_true")

    publishing = commands.add_parser("publish", help="Publica uma release no PyPI")
    publishing.add_argument(
        "--repository", choices=["pypi", "testpypi"], default="pypi"
    )
    publishing.add_argument("--dist-dir", default="dist")
    publishing.add_argument(
        "--no-build",
        action="store_true",
        help="Usa uma release já criada por `prpm pack`",
    )
    publishing.add_argument("--skip-existing", action="store_true")
    publishing.add_argument("--dry-run", action="store_true")
    publishing.add_argument("--json", action="store_true")

    verification = commands.add_parser("verify", help="Verifica pacote ou release")
    verification.add_argument("target", help="Caminho, pacote ou pacote==versão")
    verification.add_argument(
        "--repository", choices=["pypi", "testpypi"], default="pypi"
    )
    verification.add_argument("--json", action="store_true")

    commands.add_parser("doctor", help="Verifica o ambiente")
    return parser


def command_init(args: argparse.Namespace) -> int:
    path = Path.cwd() / MANIFEST_NAME
    if path.exists() and not args.force:
        raise PrpmError("pyproject.toml já existe (use --force para sobrescrever).")
    name = args.name or Path.cwd().name
    description = ""
    if not args.yes and sys.stdin.isatty():
        entered = input(f"Nome do projeto ({name}): ").strip()
        name = entered or name
        description = input("Descrição: ").strip()
    path.write_text(make_manifest(name, description), encoding="utf-8")
    console.success(f"Criado {path.name}")
    return 0


def command_create(args: argparse.Namespace) -> int:
    destination = Path(args.name).resolve()
    create_project(destination, Path(args.name).name)
    console.success(f"Projeto criado em {destination}")
    if not args.no_install:
        PackageManager(Manifest(destination)).install()
    print(f"\n  cd {Path(args.name)}\n  prpm run dev")
    return 0


def _manager() -> PackageManager:
    return PackageManager(Manifest.discover())


def _run_script(name: str, extra: list[str]) -> int:
    manifest = Manifest.discover()
    scripts = manifest.scripts()
    if name not in scripts:
        available = ", ".join(sorted(scripts)) or "nenhum"
        raise PrpmError(f"Script '{name}' não existe. Disponíveis: {available}")
    value = scripts[name]
    command = list(value) if isinstance(value, list) else shlex.split(str(value), posix=True)
    if extra and extra[0] == "--":
        extra = extra[1:]
    console.info(f"{name}: {' '.join(command + extra)}")
    return ProjectEnvironment(manifest.root).run([*command, *extra])


def _project_path(manifest: Manifest, value: str) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (manifest.root / path).resolve()


def _print_report(report: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return
    scope = report.get("scope")
    if scope == "repository":
        console.success(
            f"{report['name']}@{report['version']}: "
            f"{len(report['files'])} artefato(s) verificado(s) em {report['repository']}"
        )
    elif scope == "release":
        console.success(
            f"{report['name']}@{report['version']}: assinatura e "
            f"{len(report['artifacts'])} artefato(s) válidos"
        )
        print(f"Chave       {report['keyId']}")
    elif scope == "file":
        console.success(f"{report['filename']}: arquivo válido")
        print(f"SHA-256     {report['sha256']}")
    else:
        print(json.dumps(report, indent=2, ensure_ascii=False))


def dispatch(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    command = args.command
    if command is None:
        parser.print_help()
        return 0
    if command == "init":
        return command_init(args)
    if command == "create":
        return command_create(args)
    if command in {"install", "i"}:
        _manager().install(not args.production, args.frozen)
    elif command == "add":
        _manager().add(args.packages, args.dev)
    elif command in {"remove", "rm"}:
        _manager().remove(args.packages, True if args.dev else None)
    elif command in {"update", "up"}:
        _manager().update(args.packages, not args.production)
    elif command in {"list", "ls"}:
        packages = _manager().list_packages(1 if args.all else 0)
        if args.json:
            print(json.dumps(packages, indent=2))
        else:
            for package in sorted(packages, key=lambda item: item["name"].lower()):
                print(f"{package['name']}@{package['version']}")
    elif command == "run":
        manifest = Manifest.discover()
        if args.script is None:
            for name, value in sorted(manifest.scripts().items()):
                shown = " ".join(value) if isinstance(value, list) else value
                print(f"{name:12} {shown}")
        else:
            return _run_script(args.script, args.args)
    elif command == "exec":
        if not args.args:
            raise PrpmError("Informe um comando depois de `prpm exec`.")
        return _manager().environment.run(args.args)
    elif command == "test":
        return _run_script("test", args.args)
    elif command == "info":
        payload = package_info(args.package)
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            info = payload["info"]
            print(f"{info['name']}@{info['version']}")
            print(info.get("summary") or "Sem descrição")
            print(info.get("project_url") or info.get("package_url"))
    elif command == "lock":
        manager = _manager()
        requirements = manager.manifest.all_dependencies(True)
        if args.check:
            if not manager.lockfile.is_current(requirements):
                raise PrpmError("prpm.lock está ausente ou desatualizado.")
            console.success("prpm.lock está atualizado")
        else:
            manager._refresh_lock()
            console.success("prpm.lock gerado")
    elif command == "login":
        repository = get_repository(args.repository)
        if args.token_stdin:
            token = sys.stdin.read().strip()
        elif os.getenv(repository.token_env):
            token = os.environ[repository.token_env]
        elif sys.stdin.isatty():
            token = getpass.getpass(f"Token de {repository.name}: ")
        else:
            raise PrpmError(
                f"Use --token-stdin ou defina {repository.token_env}."
            )
        save_token(repository, token)
        identity = generate_identity()
        console.success(f"Credencial de {repository.name} guardada no keyring")
        print(f"Chave       {identity.key_id}")
        if not identity.persistent:
            console.warn(
                "O keyring não aceitou a chave; esta identidade é efêmera."
            )
        console.warn("A credencial será validada pelo PyPI durante a publicação.")
    elif command == "logout":
        repository = get_repository(args.repository)
        removed = delete_token(repository)
        if removed:
            console.success(f"Credencial de {repository.name} removida")
        else:
            console.warn(f"Nenhuma credencial guardada para {repository.name}")
    elif command == "whoami":
        repository = get_repository(args.repository)
        authenticated, source = has_token(repository)
        identity = load_identity(required=False)
        report = {
            "repository": repository.name,
            "authenticated": authenticated,
            "credentialSource": source,
            "keyId": identity.key_id if identity else None,
        }
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print(f"Repositório  {repository.name}")
            print(f"Autenticado  {'sim' if authenticated else 'não'}")
            print(f"Credencial   {source or '-'}")
            print(f"Chave        {report['keyId'] or '-'}")
    elif command == "key":
        if args.key_command is None:
            raise PrpmError("Use `prpm key show`, `generate` ou `rotate`.")
        if args.key_command == "show":
            identity = load_identity()
        else:
            identity = generate_identity(force=args.key_command == "rotate")
        console.success(f"Chave ativa: {identity.key_id}")
        if not identity.persistent:
            console.warn("Chave efêmera: o keyring do sistema não está disponível.")
    elif command == "pack":
        manifest = Manifest.discover()
        bundle = build_release(
            manifest,
            _project_path(manifest, args.out_dir),
            force=args.force,
        )
        report = verify_local(bundle.directory)
        _print_report(report, args.json)
        if not args.json:
            print(f"Diretório    {bundle.directory}")
    elif command == "publish":
        manifest = Manifest.discover()
        report = publish(
            manifest,
            get_repository(args.repository),
            directory=_project_path(manifest, args.dist_dir),
            build=not args.no_build,
            skip_existing=args.skip_existing,
            dry_run=args.dry_run,
        )
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        elif report.get("dryRun"):
            console.success("Release validada; nenhuma publicação foi realizada")
        else:
            remote = report["remote"]
            console.success(
                f"Publicado {remote['name']}@{remote['version']} em "
                f"{remote['repository']}"
            )
    elif command == "verify":
        path = Path(args.target)
        if path.exists():
            report = verify_local(path)
        else:
            report = verify_remote(args.target, get_repository(args.repository))
        _print_report(report, args.json)
    elif command == "doctor":
        print(f"PRPM       {__version__}")
        print(f"Python     {platform.python_version()}")
        print(f"Plataforma {platform.system()} {platform.machine()}")
        try:
            manifest = Manifest.discover()
        except PrpmError:
            console.warn("Nenhum projeto encontrado")
        else:
            environment = ProjectEnvironment(manifest.root)
            print(f"Projeto     {manifest.root}")
            print(f".venv       {'ok' if environment.python.is_file() else 'não criada'}")
            lock = Lockfile(manifest.root)
            print(f"Lockfile    {'ok' if lock.exists() else 'ausente'}")
        identity = load_identity(required=False)
        print(f"Assinatura  {identity.key_id if identity else 'não configurada'}")
        for repository_name in ("pypi", "testpypi"):
            configured, source = has_token(get_repository(repository_name))
            state = source if configured else "não configurado"
            print(f"{repository_name:11} {state}")
        console.success("Diagnóstico concluído")
    return 0


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    try:
        args, unknown = parser.parse_known_args(argv)
        if unknown:
            if args.command in {"run", "exec", "test"}:
                args.args.extend(unknown)
            else:
                parser.error(f"argumentos não reconhecidos: {' '.join(unknown)}")
        code = dispatch(args, parser)
    except (PrpmError, ValueError) as exc:
        console.error(str(exc))
        code = 1
    except KeyboardInterrupt:
        console.error("Operação cancelada.")
        code = 130
    raise SystemExit(code)
