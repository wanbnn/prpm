from __future__ import annotations

import os
import sys


class Console:
    def __init__(self) -> None:
        self.color = sys.stdout.isatty() and os.getenv("NO_COLOR") is None

    def _paint(self, code: str, text: str) -> str:
        return f"\033[{code}m{text}\033[0m" if self.color else text

    def info(self, message: str) -> None:
        print(f"{self._paint('36', '->')} {message}", flush=True)

    def success(self, message: str) -> None:
        print(f"{self._paint('32', 'ok')} {message}", flush=True)

    def warn(self, message: str) -> None:
        print(f"{self._paint('33', '!')} {message}", flush=True)

    def error(self, message: str) -> None:
        print(f"{self._paint('31', 'error:')} {message}", file=sys.stderr, flush=True)


console = Console()
