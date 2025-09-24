import typer
from typing_extensions import Annotated
from typing import List
import sys

# Import your command modules
from commands import config_command, chat_command, update_command, prompt_command
from helpers.error import handle_cli_error
from helpers.constants import __version__

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="A shell command-line interface powered by AI.",
)

# Register the specific subcommands that should be recognized
app.add_typer(config_command.config_app, name="config", help="Configure the CLI settings.")
app.add_typer(chat_command.chat_app, name="chat", help="Start an interactive chat session.")
app.add_typer(prompt_command.prompt_app, name="prompt", help="Generate a shell command from a prompt.")
# Assuming you have an update_command module
# app.add_typer(update_command.update_app, name="update", help="Update the AI Shell.")

def version_callback(value: bool):
    if value:
        print(f"AI Shell Version: {__version__}")
        raise typer.Exit()

@app.callback()
def main(
    ctx: typer.Context,
    version: Annotated[
        bool,
        typer.Option("--version", callback=version_callback, is_eager=True, help="Show the version and exit."),
    ] = False,
):
    """
    AI Shell: A CLI powered by Google Gemini.
    Run 'ai prompt' to generate commands, or use 'config' and 'chat'.
    """
    pass

# This part is just to make the script runnable for testing, can be omitted if using an entrypoint
if __name__ == "__main__":
    app()



