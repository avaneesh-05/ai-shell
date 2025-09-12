import random
import subprocess
import typer
import questionary
import os
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.spinner import Spinner

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

console = Console()

EXAMPLES = [
    _("delete all log files"),
    _("list js files"),
    _("fetch me a random joke"),
    _("list all commits"),
]

def prompt_command(use_prompt: str = "", silent_mode: bool = False):
    """
    The main prompt command logic.
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

        if not use_prompt:
            the_prompt = questionary.text(
                _("What would you like me to do?"),
                default=f"{_('e.g.')} {random.choice(EXAMPLES)}",
            ).ask()
        else:
            the_prompt = use_prompt

        if not the_prompt or the_prompt.strip() == "":
            console.print(f"[yellow]{_('Goodbye!')}[/yellow]")
            return

        with console.status(f"[cyan]{_('Loading...')}[/cyan]") as status:
            script = get_script_and_info(prompt=the_prompt, key=key, model=model)
            
            # This is the corrected syntax
            status.update(f"[bold green]{_('Your script')}:[/bold green]")
            console.print(f"\n[bold yellow]{script}[/bold yellow]\n")

            if not skip_explanation and script:
                # Corrected syntax
                status.update(f"[cyan]{_('Getting explanation...')}[/cyan]")
                explanation_stream = get_explanation(script=script, key=key, model=model)
                # Corrected syntax
                status.update(f"[bold green]{_('Explanation')}:[/bold green]")
                print() # newline before stream
                read_stream_and_print(explanation_stream)
                print("\n")
        
        run_or_revise_flow(script, key, model, skip_explanation)

    except (KeyboardInterrupt):
        console.print(f"\n[yellow]{_('Goodbye!')}[/yellow]")

def run_script(script: str):
    console.print(f"\n[dim]{_('Running')}: {script}[/dim]\n")
    try:
        # Using shell=True for convenience, similar to execa's behavior
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
                # Corrected syntax
                status.update(f"[bold green]{_('Your new script')}:[/bold green]")
                console.print(f"\n[bold yellow]{script}[/bold yellow]\n")

                if not silent_mode and script:
                    # Corrected syntax
                    status.update(f"[cyan]{_('Getting explanation...')}[/cyan]")
                    explanation_stream = get_explanation(script=script, key=key, model=model)
                    # Corrected syntax
                    status.update(f"[bold green]{_('Explanation')}:[/bold green]")
                    print()
                    read_stream_and_print(explanation_stream)
                    print("\n")
            # Loop back to the beginning of this function with the new script
        elif action == "copy":
            pyperclip.copy(script)
            console.print(f"[green]✔ {_('Copied to clipboard!')}[/green]")
            break
        elif action == "cancel" or action is None:
            console.print(f"[yellow]{_('Goodbye!')}[/yellow]")
            break

