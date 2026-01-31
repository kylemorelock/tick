"""Entry point with lazy imports for fast --help response."""

import sys


def main() -> int:
    # Heavy imports are deferred to command execution.
    from tick.cli.app import app

    return app()


if __name__ == "__main__":
    sys.exit(main())
