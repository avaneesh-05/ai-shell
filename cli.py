import typer
from typing_extensions import Annotated
from typing import List

from commands import config_command, chat_command, update_command, prompt_command
from helpers.error import handle_cli_error
from helpers.constants import __version__

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="A shell command-line interface powered by AI.",
)

# Register the subcommands. Typer will recognize these as the only valid commands.
app.add_typer(config_command.config_app, name="config")
app.add_typer(chat_command.chat_app, name="chat")
app.add_typer(update_command.update_app, name="update")

def version_callback(value: bool):
    if value:
        print(f"AI Shell Version: {__version__}")
        raise typer.Exit()

@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    # This is the corrected way to handle the prompt.
    # It tells Typer to collect all non-command text into this list.
    prompt_words: Annotated[
        List[str],
        typer.Argument(
            help="The prompt for the AI. All text that isn't a subcommand will be treated as the prompt.",
            show_default=False,
        ),
    ] = None,
    silent: Annotated[
        bool,
        typer.Option("--silent", "-s", help="Less verbose, skip printing the command explanation."),
    ] = False,
    version: Annotated[
        bool,
        typer.Option("--version", callback=version_callback, is_eager=True, help="Show the version and exit."),
    ] = False,
):
    """
    Main entry point for the AI Shell CLI.
    """
    try:
        # If the user runs a valid subcommand (e.g., `ai chat`), this block is skipped.
        # If the user provides a prompt, this block will execute.
        if ctx.invoked_subcommand is None:
            prompt_text = " ".join(prompt_words) if prompt_words else ""
            prompt_command.prompt_command(use_prompt=prompt_text, silent_mode=silent)

    except Exception as e:
        handle_cli_error(e)

