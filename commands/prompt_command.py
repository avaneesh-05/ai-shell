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
    get_gemini_llm,
    get_execution_plan,
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

prompt_app = typer.Typer(
    help="Generate shell commands from natural language.",
    no_args_is_help=True
)
console = Console()

# Keywords that suggest the user might want an email or github action.
# If NONE of these appear, we skip the LLM intent classification entirely (saves 1-3 seconds).
# If any match, the LLM still makes the final decision to avoid false positives
# (e.g., "what .py files relate to email" triggers keywords but LLM correctly says NO_LISTING).
EMAIL_HINT_KEYWORDS = ["email", "e-mail", "mail", "draft", "compose", "smtp"]
GITHUB_HINT_KEYWORDS = ["clone", "github", "gitlab", "repo", "repository"]


def _needs_intent_classification(prompt: str) -> bool:
    """
    Quick keyword check to determine if an LLM intent classification call is needed.
    Returns True only if the prompt contains email or github-related keywords.
    This avoids an expensive LLM call for the majority of simple shell commands.
    """
    prompt_lower = prompt.lower()
    has_email_hint = any(kw in prompt_lower for kw in EMAIL_HINT_KEYWORDS)
    has_github_hint = any(kw in prompt_lower for kw in GITHUB_HINT_KEYWORDS)
    return has_email_hint or has_github_hint


def _execute_prompt(use_prompt: str = "", silent_mode: bool = False):
    """The main prompt command logic."""
    try:
        config = get_config()
        set_language(config.get("LANGUAGE", "en"))
        key = config.get("GOOGLE_API_KEY")
        model = config.get("MODEL", "gemini-1.5-flash")
        skip_explanation = silent_mode or config.get("SILENT_MODE", False)

        if not key:
            raise KnownError(_("Please set your Google Gemini API key via `ai config set GOOGLE_API_KEY=<your_token>`"))

        # Create a single LLM instance — reused across classification, planning, explanation, and revision
        llm = get_gemini_llm(key, model)

        # Intent Detection — only if keywords suggest email/github (saves an LLM call otherwise)
        if use_prompt and use_prompt.strip() and _needs_intent_classification(use_prompt):
            classification = llm.complete(
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
            # NO_LISTING and NO both fall through to the execution plan

        console.print(Panel(f"[bold cyan]{project_name}[/bold cyan]", expand=False, border_style="dim"))

        if not use_prompt:
            return

        with console.status(f"[cyan]{_('Planning tasks...')}[/cyan]"):
            plan = get_execution_plan(prompt=use_prompt, key=key, model=model, llm=llm)

            if not plan:
                console.print("[red]Could not generate a plan.[/red]")
                return

        # Execute Plan
        total_steps = len(plan)
        console.print(f"\n[bold green]AI has generated a {total_steps}-step plan:[/bold green]\n")

        for i, step in enumerate(plan, 1):
            script = step.get('command', '')
            desc = step.get('description', 'Execute command')

            console.print(Panel(f"[bold]Step {i}/{total_steps}:[/bold] {desc}", style="blue"))
            console.print(f"[bold yellow]{script}[/bold yellow]\n")

            # Show explanation for each step (unless silent mode)
            if not skip_explanation and script:
                console.print(f"[bold green]{_('Explanation')}:[/bold green]")
                explanation_stream = get_explanation(script=script, key=key, model=model, llm=llm)
                read_stream_and_print(explanation_stream)
                print("\n")

            # Run/Revise flow
            if not run_or_revise_flow(script, key, model, skip_explanation, step_index=i, total=total_steps, llm=llm):
                console.print("[yellow]Plan aborted by user.[/yellow]")
                break

    except KeyboardInterrupt:
        console.print(f"\n[yellow]{_('Goodbye!')}[/yellow]")


@prompt_app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    prompt_words: Annotated[List[str], typer.Argument(help="The prompt.")],
    silent: Annotated[bool, typer.Option("--silent", "-s")] = False,
):
    """Generate a shell command from a natural language prompt."""
    if ctx.invoked_subcommand is None:
        prompt_text = " ".join(prompt_words) if prompt_words else ""
        _execute_prompt(use_prompt=prompt_text, silent_mode=silent)


def run_script(script: str) -> bool:
    """Runs a shell script. Returns True if successful, False if failed."""
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


def run_or_revise_flow(script: str, key: str, model: str, silent_mode: bool, step_index: int, total: int, llm=None) -> bool:
    """
    Interactive menu for running, editing, revising, copying, or skipping a command.
    Returns True to proceed to the next step, False to abort the plan.
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
            console.print(f"[yellow]New command queued: {script}[/yellow]")

        elif action == "revise":
            instruction = questionary.text(_("How should I change this step?")).ask()
            with console.status("[cyan]Revising...[/cyan]"):
                script = get_revision(instruction, script, key, model, llm=llm)
            console.print(f"\n[bold yellow]{script}[/bold yellow]\n")

        elif action == "copy":
            pyperclip.copy(script)
            console.print(f"[green]✔ {_('Copied to clipboard!')}[/green]")
            return True  # Continue to next step — user copied it, plan should proceed

        elif action == "skip":
            console.print("[dim]Skipping step...[/dim]")
            return True

        elif action == "cancel" or action is None:
            return False