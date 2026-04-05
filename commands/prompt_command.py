# import random
# import subprocess
# import typer
# import questionary
# import os
# from rich.console import Console
# from rich.panel import Panel
# from rich.text import Text
# from rich.spinner import Spinner
# from typing_extensions import Annotated
# from typing import List
# from llama_index.llms.google_genai import GoogleGenAI

# import pyperclip
# from helpers.config import get_config
# from helpers.constants import project_name
# from helpers.completion import (
#     get_script_and_info,
#     get_explanation,
#     get_revision,
#     read_stream_and_print,
# )
# from helpers.i18n import _, set_language
# from helpers.shell_history import append_to_shell_history
# from helpers.error import KnownError
# from helpers.email_workflow import handle_email_intent
# from helpers.security import is_risky_command, verify_identity

# # Create a dedicated Typer app for the 'prompt' command
# prompt_app = typer.Typer(
#     help="Generate a shell command from a natural language prompt.",
#     no_args_is_help=True
# )
# console = Console()

# EXAMPLES = [
#     _("delete all log files"),
#     _("list js files"),
#     _("fetch me a random joke"),
#     _("list all commits"),
# ]

# def _execute_prompt(use_prompt: str = "", silent_mode: bool = False):
#     """
#     The main prompt command logic. (Internal function)
#     """
#     try:
#         config = get_config()
#         set_language(config.get("LANGUAGE", "en"))
#         key = config.get("GOOGLE_API_KEY")
#         model = config.get("MODEL", "gemini-1.5-flash")
#         skip_explanation = silent_mode or config.get("SILENT_MODE", False)

#         if not key:
#             raise KnownError(_("Please set your Google Gemini API key via `ai config set GOOGLE_API_KEY=<your_token>`"))

#         # === 1. INTENT DETECTION (New Feature) ===
#         # Before generating a shell script, we check if the user wants to send an email.
#         if use_prompt and use_prompt.strip():
#             # Quick check: using a small LLM call to classify intent
#             # This class is now properly imported
#             classifier_llm = GoogleGenAI(model=model, api_key=key)
            
#             # We ask the AI to classify the intent strictly
#             classification = classifier_llm.complete(
#                 f"Analyze this user request: '{use_prompt}'.\n"
#                 "Does the user explicitly want to draft or send an email/mail?\n"
#                 "Reply ONLY with 'YES_EMAIL' or 'NO'."
#             ).text.strip().upper()

#             if "YES_EMAIL" in classification:
#                 # Divert to the email workflow and exit this function upon completion
#                 handle_email_intent(use_prompt)
#                 return
#         # =========================================

#         console.print(Panel(f"[bold cyan]{project_name}[/bold cyan]", expand=False, border_style="dim"))

#         the_prompt = use_prompt
#         if not the_prompt or the_prompt.strip() == "":
#             console.print(f"[yellow]{_('Goodbye!')}[/yellow]")
#             return

#         with console.status(f"[cyan]{_('Loading...')}[/cyan]") as status:
#             script = get_script_and_info(prompt=the_prompt, key=key, model=model)
#             status.update(f"[bold green]{_('Your script')}:[/bold green]")
#             console.print(f"\n[bold yellow]{script}[/bold yellow]\n")

#             if not skip_explanation and script:
#                 status.update(f"[cyan]{_('Getting explanation...')}[/cyan]")
#                 explanation_stream = get_explanation(script=script, key=key, model=model)
#                 status.update(f"[bold green]{_('Explanation')}:[/bold green]")
#                 print()
#                 read_stream_and_print(explanation_stream)
#                 print("\n")
        
#         run_or_revise_flow(script, key, model, skip_explanation)

#     except (KeyboardInterrupt):
#         console.print(f"\n[yellow]{_('Goodbye!')}[/yellow]")

# @prompt_app.callback(invoke_without_command=True)
# def main(
#     ctx: typer.Context,
#     prompt_words: Annotated[
#         List[str],
#         typer.Argument(
#             help="The prompt for the AI. All text after 'prompt' will be treated as the prompt.",
#             show_default=False,
#         ),
#     ],
#     silent: Annotated[
#         bool,
#         typer.Option("--silent", "-s", help="Less verbose, skip printing the command explanation."),
#     ] = False,
# ):
#     """
#     The entry point for the 'ai prompt' command.
#     """
#     if ctx.invoked_subcommand is None:
#         prompt_text = " ".join(prompt_words) if prompt_words else ""
#         _execute_prompt(use_prompt=prompt_text, silent_mode=silent)


# def run_script(script: str):
#     console.print(f"\n[dim]{_('Running')}: {script}[/dim]\n")
#     try:
#         subprocess.run(script, shell=True, check=True, executable=os.environ.get("SHELL"))
#         append_to_shell_history(script)
#     except subprocess.CalledProcessError:
#         console.print("[red]✖ Script finished with a non-zero exit code.[/red]")
#     except Exception as e:
#         console.print(f"[red]✖ Failed to run script: {e}[/red]")

# def run_or_revise_flow(script: str, key: str, model: str, silent_mode: bool):
#     """Handles the user's choice to run, edit, revise, or copy the script."""
#     while True:
#         empty_script = not script.strip()
#         message = _("Revise this script?") if empty_script else _("Run this script?")

#         choices = []
#         if not empty_script:
#             choices.extend([
#                 questionary.Choice(title=f"✅ {_('Yes')}", value="yes"),
#                 questionary.Choice(title=f"📝 {_('Edit')}", value="edit"),
#             ])
        
#         choices.extend([
#             questionary.Choice(title=f"🔁 {_('Revise')}", value="revise"),
#             questionary.Choice(title=f"📋 {_('Copy')}", value="copy"),
#             questionary.Choice(title=f"❌ {_('Cancel')}", value="cancel"),
#         ])

#         action = questionary.select(message, choices=choices).ask()

#         if action == "yes":
#             run_script(script)
#             break
#         elif action == "edit":
#             new_script = questionary.text(_("you can edit script here"), default=script).ask()
#             if new_script:
#                 run_script(new_script)
#             break
#         elif action == "revise":
#             revision_prompt = questionary.text(_("What would you like me to change in this script?")).ask()
#             if not revision_prompt:
#                 continue

#             with console.status(f"[cyan]{_('Loading...')}[/cyan]") as status:
#                 script = get_revision(prompt=revision_prompt, code=script, key=key, model=model)
#                 status.update(f"[bold green]{_('Your new script')}:[/bold green]")
#                 console.print(f"\n[bold yellow]{script}[/bold yellow]\n")

#                 if not silent_mode and script:
#                     status.update(f"[cyan]{_('Getting explanation...')}[/cyan]")
#                     explanation_stream = get_explanation(script=script, key=key, model=model)
#                     status.update(f"[bold green]{_('Explanation')}:[/bold green]")
#                     print()
#                     read_stream_and_print(explanation_stream)
#                     print("\n")
#         elif action == "copy":
#             pyperclip.copy(script)
#             console.print(f"[green]✔ {_('Copied to clipboard!')}[/green]")
#             break
#         elif action == "cancel" or action is None:
#             console.print(f"[yellow]{_('Goodbye!')}[/yellow]")
#             break

# def run_script(script: str):
#     console.print(f"\n[dim]{_('Running')}: {script}[/dim]\n")
    
#     # === SECURITY CHECK ===
#     if is_risky_command(script):
#         if not verify_identity():
#             return # Stop execution if PIN is wrong
#     # ======================

#     try:
#         subprocess.run(script, shell=True, check=True, executable=os.environ.get("SHELL"))
#         append_to_shell_history(script)
#     except subprocess.CalledProcessError:
#         console.print("[red]✖ Script finished with a non-zero exit code.[/red]")
#     except Exception as e:
#         console.print(f"[red]✖ Failed to run script: {e}[/red]")
# commands/prompt_command.py
import os
import subprocess
import typer
import questionary
from typing import List
from typing_extensions import Annotated
from rich.console import Console
from rich.panel import Panel
import pyperclip

from helpers.config import get_config
from helpers.constants import project_name
from helpers.completion import (
    get_execution_plan,  # <--- CHANGED FROM get_script_and_info
    get_explanation,
    get_revision,
    read_stream_and_print,
)
from helpers.i18n import _, set_language
from helpers.shell_history import append_to_shell_history
from helpers.error import KnownError
from helpers.email_workflow import handle_email_intent
from helpers.github_workflow import handle_github_intent
from helpers.security import is_risky_command, verify_identity
from llama_index.llms.google_genai import GoogleGenAI

prompt_app = typer.Typer(
    help="Generate shell commands from natural language.",
    no_args_is_help=True
)
console = Console()

def _execute_prompt(use_prompt: str = "", silent_mode: bool = False):
    try:
        config = get_config()
        set_language(config.get("LANGUAGE", "en"))
        key = config.get("GOOGLE_API_KEY")
        model = config.get("MODEL", "gemini-1.5-flash")

        if not key:
            raise KnownError(_("Please set your Google Gemini API key via `ai config set GOOGLE_API_KEY=<your_token>`"))

        # 1. Intent Detection (Email) - but avoid triggering on file-listing/inspection queries
        if use_prompt and use_prompt.strip():
            classifier_llm = GoogleGenAI(model=model, api_key=key)
            classification = classifier_llm.complete(
                f"""Analyze this user request: "{use_prompt}"
                
CONTEXT: The user is asking a CLI assistant (ai-shell) to perform a task.

Your task: Determine the REQUEST INTENT and answer strictly with one of: YES_EMAIL, YES_GITHUB, NO_LISTING, or NO.

- Reply YES_EMAIL ONLY if the user explicitly wants to DRAFT or SEND an email/mail message.
- Reply YES_GITHUB if the user wants to CLONE, DOWNLOAD, or GET a GitHub or GitLab repository (e.g., "clone this repo", "download github repo", "get me the gitlab repo", "clone gitlab.com/...").
- Reply NO_LISTING if the user is asking to LIST/SEARCH/FIND files (e.g., "what .py files", "list files related to", "show me files", "find all").
- Reply NO for all other requests (create files, run commands, general tasks, etc).

Examples:
  "what .py files related to email" → NO_LISTING
  "show me all email functions" → NO_LISTING
  "send an email to john@example.com" → YES_EMAIL
  "draft a professional email" → YES_EMAIL
  "clone https://github.com/user/repo" → YES_GITHUB
  "download github repo user/repo" → YES_GITHUB
  "get me the repo at github.com/user/repo" → YES_GITHUB
  "clone https://gitlab.com/org/project" → YES_GITHUB
  "download gitlab repo org/project" → YES_GITHUB
  "get the gitlab repo org/tool" → YES_GITHUB
  "list all .py files" → NO_LISTING
  "find files in project" → NO_LISTING
  "delete all .tmp files" → NO
  
Respond ONLY with: YES_EMAIL or YES_GITHUB or NO_LISTING or NO"""
            ).text.strip().upper()

            if "YES_EMAIL" in classification:
                handle_email_intent(use_prompt)
                return

            if "YES_GITHUB" in classification:
                handle_github_intent(use_prompt)
                return
            # If it's a file-listing query, just let it go through to execution plan
            # (the LLM will handle it better now with improved prompts)

        console.print(Panel(f"[bold cyan]{project_name}[/bold cyan]", expand=False, border_style="dim"))

        if not use_prompt:
            return

        with console.status(f"[cyan]{_('Planning tasks...')}[/cyan]") as status:
            # GET PLAN INSTEAD OF SINGLE SCRIPT
            plan = get_execution_plan(prompt=use_prompt, key=key, model=model)
            
            if not plan:
                console.print("[red]Could not generate a plan.[/red]")
                return

        # EXECUTE PLAN LOOP
        total_steps = len(plan)
        console.print(f"\n[bold green]AI has generated a {total_steps}-step plan:[/bold green]\n")

        for i, step in enumerate(plan, 1):
            script = step.get('command', '')
            desc = step.get('description', 'Execute command')

            console.print(Panel(f"[bold]Step {i}/{total_steps}:[/bold] {desc}", style="blue"))
            console.print(f"[bold yellow]{script}[/bold yellow]\n")

            # Explanation (Optional)
            if not silent_mode and not config.get("SILENT_MODE", False):
                # We skip live streaming explanation for multi-step to keep it fast, 
                # unless requested. For now, let's keep it simple.
                pass

            # Loop for Run/Revise logic
            if not run_or_revise_flow(script, key, model, silent_mode, step_index=i, total=total_steps):
                console.print("[yellow]Plan aborted by user.[/yellow]")
                break

    except (KeyboardInterrupt):
        console.print(f"\n[yellow]{_('Goodbye!')}[/yellow]")

@prompt_app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    prompt_words: Annotated[List[str], typer.Argument(help="The prompt.")],
    silent: Annotated[bool, typer.Option("--silent", "-s")] = False,
):
    if ctx.invoked_subcommand is None:
        prompt_text = " ".join(prompt_words) if prompt_words else ""
        _execute_prompt(use_prompt=prompt_text, silent_mode=silent)

def run_script(script: str) -> bool:
    """Returns True if successful, False if failed."""
    
    # Security Check
    if is_risky_command(script):
        if not verify_identity():
            return False

    console.print(f"\n[dim]{_('Running')}: {script}[/dim]\n")
    try:
        subprocess.run(script, shell=True, check=True, executable=os.environ.get("SHELL"))
        append_to_shell_history(script)
        return True
    except subprocess.CalledProcessError:
        console.print("[red]✖ Script finished with a non-zero exit code.[/red]")
        return False
    except Exception as e:
        console.print(f"[red]✖ Failed to run script: {e}[/red]")
        return False

def run_or_revise_flow(script: str, key: str, model: str, silent_mode: bool, step_index: int, total: int) -> bool:
    """
    Returns True if we should proceed to the next step, False to abort.
    """
    while True:
        # Dynamic button text based on whether it's the last step
        next_label = "Run & Next" if step_index < total else "Run & Finish"
        
        action = questionary.select(
            "Select action:",
            choices=[
                questionary.Choice(title=f"✅ {next_label}", value="yes"),
                questionary.Choice(title=f"📝 {_('Edit')}", value="edit"),
                questionary.Choice(title=f"🔁 {_('Revise')}", value="revise"),
                questionary.Choice(title=f"📋 {_('Copy')}", value="copy"),
                questionary.Choice(title=f"⏭️  Skip Step", value="skip"),
                questionary.Choice(title=f"❌ Abort Plan", value="cancel"),
            ]
        ).ask()

        if action == "yes":
            success = run_script(script)
            if not success:
                # If script failed, ask user if they want to continue anyway
                return questionary.confirm("Command failed. Continue to next step anyway?").ask()
            return True
            
        elif action == "edit":
            script = questionary.text(_("Edit command:"), default=script).ask()
            # Loop back to menu with new script
            console.print(f"[yellow]New command queued: {script}[/yellow]")
            
        elif action == "revise":
            instruction = questionary.text(_("How should I change this step?")).ask()
            with console.status("[cyan]Revising...[/cyan]"):
                script = get_revision(instruction, script, key, model)
            console.print(f"\n[bold yellow]{script}[/bold yellow]\n")
            
        elif action == "copy":
            pyperclip.copy(script)
            console.print(f"[green]✔ {_('Copied!')}[/green]")
            return False # Break loop, effectively acting like a skip/cancel logic depending on preference. 
                         # Actually, usually copy implies "I'll run it myself", so maybe return True?
                         # Let's return False to stop auto-execution, user took control.
            
        elif action == "skip":
            console.print("[dim]Skipping step...[/dim]")
            return True
            
        elif action == "cancel" or action is None:
            return False