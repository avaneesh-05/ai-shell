import random
import subprocess
import typer
import questionary
import os
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.spinner import Spinner
from typing_extensions import Annotated
from typing import List

import pyperclip
from helpers.config import get_config
from helpers.constants import project_name
from helpers.completion import (
    get_script_and_info,
    get_explanation,
    get_revision,
    read_stream_and_print,
)
from helpers.i18n import _, set_language
from helpers.shell_history import append_to_shell_history
from helpers.error import KnownError

# Create a dedicated Typer app for the 'prompt' command
prompt_app = typer.Typer(
    help="Generate a shell command from a natural language prompt.",
    no_args_is_help=True
)
console = Console()

EXAMPLES = [
    _("delete all log files"),
    _("list js files"),
    _("fetch me a random joke"),
    _("list all commits"),
]

def _execute_prompt(use_prompt: str = "", silent_mode: bool = False):
    """
    The main prompt command logic. (Internal function)
    """
    try:
        config = get_config()
        set_language(config.get("LANGUAGE", "en"))
        key = config.get("GOOGLE_API_KEY")
        model = config.get("MODEL", "gemini-1.5-flash")
        skip_explanation = silent_mode or config.get("SILENT_MODE", False)

        if not key:
            raise KnownError(_("Please set your Google Gemini API key via `ai config set GOOGLE_API_KEY=<your_token>`"))

        console.print(Panel(f"[bold cyan]{project_name}[/bold cyan]", expand=False, border_style="dim"))

        the_prompt = use_prompt
        if not the_prompt or the_prompt.strip() == "":
            console.print(f"[yellow]{_('Goodbye!')}[/yellow]")
            return

        with console.status(f"[cyan]{_('Loading...')}[/cyan]") as status:
            script = get_script_and_info(prompt=the_prompt, key=key, model=model)
            status.update(f"[bold green]{_('Your script')}:[/bold green]")
            console.print(f"\n[bold yellow]{script}[/bold yellow]\n")

            if not skip_explanation and script:
                status.update(f"[cyan]{_('Getting explanation...')}[/cyan]")
                explanation_stream = get_explanation(script=script, key=key, model=model)
                status.update(f"[bold green]{_('Explanation')}:[/bold green]")
                print()
                read_stream_and_print(explanation_stream)
                print("\n")
        
        run_or_revise_flow(script, key, model, skip_explanation)

    except (KeyboardInterrupt):
        console.print(f"\n[yellow]{_('Goodbye!')}[/yellow]")

@prompt_app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    prompt_words: Annotated[
        List[str],
        typer.Argument(
            help="The prompt for the AI. All text after 'prompt' will be treated as the prompt.",
            show_default=False,
        ),
    ],
    silent: Annotated[
        bool,
        typer.Option("--silent", "-s", help="Less verbose, skip printing the command explanation."),
    ] = False,
):
    """
    The entry point for the 'ai prompt' command.
    """
    if ctx.invoked_subcommand is None:
        prompt_text = " ".join(prompt_words) if prompt_words else ""
        _execute_prompt(use_prompt=prompt_text, silent_mode=silent)


def run_script(script: str):
    console.print(f"\n[dim]{_('Running')}: {script}[/dim]\n")
    try:
        subprocess.run(script, shell=True, check=True, executable=os.environ.get("SHELL"))
        append_to_shell_history(script)
    except subprocess.CalledProcessError:
        console.print("[red]✖ Script finished with a non-zero exit code.[/red]")
    except Exception as e:
        console.print(f"[red]✖ Failed to run script: {e}[/red]")

def run_or_revise_flow(script: str, key: str, model: str, silent_mode: bool):
    """Handles the user's choice to run, edit, revise, or copy the script."""
    while True:
        empty_script = not script.strip()
        message = _("Revise this script?") if empty_script else _("Run this script?")

        choices = []
        if not empty_script:
            choices.extend([
                questionary.Choice(title=f"✅ {_('Yes')}", value="yes"),
                questionary.Choice(title=f"📝 {_('Edit')}", value="edit"),
            ])
        
        choices.extend([
            questionary.Choice(title=f"🔁 {_('Revise')}", value="revise"),
            questionary.Choice(title=f"📋 {_('Copy')}", value="copy"),
            questionary.Choice(title=f"❌ {_('Cancel')}", value="cancel"),
        ])

        action = questionary.select(message, choices=choices).ask()

        if action == "yes":
            run_script(script)
            break
        elif action == "edit":
            new_script = questionary.text(_("you can edit script here"), default=script).ask()
            if new_script:
                run_script(new_script)
            break
        elif action == "revise":
            revision_prompt = questionary.text(_("What would you like me to change in this script?")).ask()
            if not revision_prompt:
                continue

            with console.status(f"[cyan]{_('Loading...')}[/cyan]") as status:
                script = get_revision(prompt=revision_prompt, code=script, key=key, model=model)
                status.update(f"[bold green]{_('Your new script')}:[/bold green]")
                console.print(f"\n[bold yellow]{script}[/bold yellow]\n")

                if not silent_mode and script:
                    status.update(f"[cyan]{_('Getting explanation...')}[/cyan]")
                    explanation_stream = get_explanation(script=script, key=key, model=model)
                    status.update(f"[bold green]{_('Explanation')}:[/bold green]")
                    print()
                    read_stream_and_print(explanation_stream)
                    print("\n")
        elif action == "copy":
            pyperclip.copy(script)
            console.print(f"[green]✔ {_('Copied to clipboard!')}[/green]")
            break
        elif action == "cancel" or action is None:
            console.print(f"[yellow]{_('Goodbye!')}[/yellow]")
            break
