"""Entry point with lazy imports for fast --help response."""

import sys
from typing import cast


def main() -> int:
    # Heavy imports are deferred to command execution.
    from tick.cli.app import app

    return cast(int, app())


if __name__ == "__main__":
    sys.exit(main())
