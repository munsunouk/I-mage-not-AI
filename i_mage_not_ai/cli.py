"""Compatibility module entry point for the Typer CLI."""

from .typer_cli import app


def main() -> None:
    app()


if __name__ == "__main__":
    main()
