"""`python -m vitalprobe` entry point — the same Typer app as the installed script.

The dashboard's trigger-run form spawns the CLI through this module, so it must
stay a plain re-dispatch with no logic of its own.
"""

from vitalprobe.cli import app

if __name__ == "__main__":
    app()
