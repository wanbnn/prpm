# Exact environment synchronization

`prpm install` installs the dependency graph recorded in `prpm.lock`, but it intentionally does not remove packages that were installed manually or left behind by an older dependency graph.

Use `prpm sync` when the virtual environment must match an existing current lockfile exactly:

```bash
prpm sync
```

`sync` requires a current lockfile. It installs the exact locked graph using the same frozen-install path as `prpm install --frozen`. Only after that succeeds does it inspect `.venv` and uninstall packages that are not part of the selected lock scope.

This ordering is deliberate: if installation fails, PRPM does not remove anything from the previously working environment.

If the manifest changed and the lockfile must be regenerated first, run `prpm install` once and then `prpm sync`.

## Production-only synchronization

To remove development-only packages as well as unrelated packages:

```bash
prpm sync --production
```

The project package itself is protected when it has been installed into its own `.venv`, so editable project installs are not removed as orphans.

## CI and reproducible environments

For CI or deployment environments with a committed current lockfile that must contain no undeclared Python packages, a single command is enough:

```bash
prpm sync --production
```

When hash verification is enabled with `PRPM_VERIFY_HASHES=1`, `sync` reuses the same verified frozen-install path before removing extras:

```bash
PRPM_VERIFY_HASHES=1 prpm sync --production
```

## Difference between install and sync

- `prpm install` resolves or consumes the lockfile and installs the selected locked packages, but preserves unrelated packages already present in `.venv`.
- `prpm sync` requires an up-to-date lockfile and reconciles `.venv` to it by removing unrelated packages after the locked graph has been installed successfully.

This separation keeps normal development installs non-destructive while providing an explicit exact-state operation for CI, deployment and environment recovery.
