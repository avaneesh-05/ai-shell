import typer
import sys
from typing_extensions import Annotated

# Import your command modules
from commands import config_command, chat_command, update_command, prompt_command, explain_command, fix_command, usage_command
from helpers.error import handle_cli_error
from helpers.constants import __version__

app = typer.Typer(
    invoke_without_command=True,
    add_completion=False,
    help="A shell command-line interface powered by AI.",
    context_settings={"allow_extra_args": True, "allow_interspersed_args": False},
)

# Register subcommands
app.add_typer(config_command.config_app, name="config", help="Configure the CLI settings.")
app.add_typer(chat_command.chat_app, name="chat", help="Start an interactive chat session.")
app.add_typer(prompt_command.prompt_app, name="prompt", help="Generate a shell command from a prompt.")
app.add_typer(update_command.update_app, name="update", help="Update the AI Shell.")
app.add_typer(explain_command.explain_app, name="explain", help="Explain a shell command in plain English.")
app.add_typer(fix_command.fix_app, name="fix", help="Diagnose and fix shell command errors.")
app.add_typer(usage_command.usage_app, name="usage", help="View API usage and estimated costs.")


def version_callback(value: bool):
    if value:
        print(f"AI Shell Version: {__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Annotated[
        bool,
        typer.Option("--version", callback=version_callback, is_eager=True, help="Show the version and exit."),
    ] = False,
    silent: Annotated[
        bool,
        typer.Option("--silent", "-s", help="Skip printing command explanations."),
    ] = False,
):
    """
    AI Shell: A CLI powered by Google Gemini.

    Usage:
      ai "your prompt here"       Direct prompt (shortcut)
      ai prompt "your prompt"     Explicit prompt command
      ai chat                     Interactive chat session
      ai config                   Configure settings
    """
    if ctx.invoked_subcommand is None:
        # No subcommand matched — check for direct prompt arguments
        if ctx.args:
            prompt_text = " ".join(ctx.args)
            prompt_command._execute_prompt(use_prompt=prompt_text, silent_mode=silent)
        else:
            # No args at all — show help
            print(ctx.get_help())
            raise typer.Exit()


if __name__ == "__main__":
    app()
