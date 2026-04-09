# commands/explain_command.py
"""
The `ai explain` command — explains any shell command in plain English.
Usage: ai explain "find . -name '*.py' -exec grep -l 'import os' {} +"
"""
import typer
from typing import List
from typing_extensions import Annotated
from rich.console import Console
from rich.panel import Panel

from helpers.config import get_config
from helpers.completion import get_gemini_llm, get_explanation, read_stream_and_print
from helpers.error import KnownError
from helpers.i18n import _, set_language

explain_app = typer.Typer(
    help="Explain a shell command in plain English.",
    no_args_is_help=True,
)
console = Console()


@explain_app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    command_words: Annotated[
        List[str],
        typer.Argument(help="The command to explain. Wrap in quotes for complex commands."),
    ],
):
    """
    Explain what a shell command does in plain English.

    Examples:
      ai explain "find . -name '*.py'"
      ai explain ls -la /tmp
      ai explain "docker compose up -d"
    """
    if ctx.invoked_subcommand is not None:
        return

    command_text = " ".join(command_words).strip()
    if not command_text:
        console.print("[yellow]Please provide a command to explain.[/yellow]")
        return

    try:
        config = get_config()
        set_language(config.get("LANGUAGE", "en"))
        key = config.get("GOOGLE_API_KEY")
        model = config.get("MODEL", "gemini-1.5-flash")

        if not key:
            raise KnownError(
                _("Please set your Google Gemini API key via `ai config set GOOGLE_API_KEY=<your_token>`")
            )

        llm = get_gemini_llm(key, model)

        console.print(
            Panel(
                f"[bold yellow]{command_text}[/bold yellow]",
                title="🔍 Explaining",
                border_style="cyan",
                expand=False,
            )
        )
        console.print()

        explanation_stream = get_explanation(script=command_text, key=key, model=model, llm=llm)
        read_stream_and_print(explanation_stream)
        print("\n")

    except KeyboardInterrupt:
        console.print(f"\n[yellow]{_('Goodbye!')}[/yellow]")
