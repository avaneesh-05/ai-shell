# commands/fix_command.py
"""
The `ai fix` command — diagnoses failed shell commands and suggests fixes.

Usage:
  ai fix                         Auto-detects last failed command and suggests a fix
  ai fix "error message here"    Diagnose a pasted error
  some_command 2>&1 | ai fix     Pipe error output directly
"""
import sys
import os
import subprocess
import typer
import questionary
import textwrap
from pathlib import Path
from typing import List, Optional
from typing_extensions import Annotated
from rich.console import Console
from rich.panel import Panel

from helpers.config import get_config
from helpers.completion import get_gemini_llm, get_os_details, get_shell_details, strip_code_fences
from helpers.error import KnownError
from helpers.i18n import _, set_language
from helpers.shell_history import get_history_file, append_to_shell_history
from helpers.security import is_risky_command, verify_identity

fix_app = typer.Typer(
    help="Diagnose and fix shell command errors.",
    invoke_without_command=True,
)
console = Console()


def _get_last_command() -> str:
    """
    Gets the most recent non-ai command from the shell history file.
    Walks backwards through the file to skip blank lines and 'ai ...' commands.
    """
    history_file = os.environ.get("HISTFILE") or get_history_file()

    if not history_file or not os.path.exists(history_file):
        return ""

    try:
        with open(history_file, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        for line in reversed(lines):
            cmd = line.strip()
            # Handle zsh extended history format: ": timestamp:0;command"
            if cmd.startswith(": ") and ";" in cmd:
                cmd = cmd.split(";", 1)[1].strip()
            if cmd and not cmd.startswith("ai "):
                return cmd

    except Exception:
        pass

    return ""


def _capture_error(command: str) -> tuple[int, str]:
    """
    Runs a command silently and returns (exit_code, combined_error_output).
    Merges stderr + stdout so nothing is missed.
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            executable=os.environ.get("SHELL", "/bin/bash"),
            timeout=30,
        )
        output = (result.stderr + result.stdout).strip()
        return result.returncode, output
    except subprocess.TimeoutExpired:
        return -1, "Command timed out after 30 seconds."
    except Exception as e:
        return -1, str(e)


def _diagnose_and_fix(error_context: str, key: str, model: str) -> str:
    """Uses the LLM to diagnose an error and suggest a fix."""
    llm = get_gemini_llm(key, model)

    prompt = textwrap.dedent(f"""
        You are an expert shell/DevOps engineer diagnosing a command error.

        {error_context}

        OS: {get_os_details()}
        Shell: {get_shell_details()}

        Provide your response in this EXACT format (each section on its own line):

        DIAGNOSIS: [1-2 sentence explanation of what went wrong]

        FIX: [the corrected command — ONLY the raw command, no backticks, no markdown]

        EXPLANATION: [Brief explanation of what was changed and why]
    """)

    response = llm.complete(prompt).text.strip()
    return response


def _parse_fix_response(response: str) -> dict:
    """Parses the structured LLM response into diagnosis, fix command, and explanation."""
    result = {"diagnosis": "", "fix": "", "explanation": "", "raw": response}

    current_key = None
    for line in response.split("\n"):
        line_stripped = line.strip()
        upper = line_stripped.upper()

        if upper.startswith("DIAGNOSIS:"):
            current_key = "diagnosis"
            result[current_key] = line_stripped.split(":", 1)[1].strip()
        elif upper.startswith("FIX:"):
            current_key = "fix"
            result[current_key] = line_stripped.split(":", 1)[1].strip()
        elif upper.startswith("EXPLANATION:"):
            current_key = "explanation"
            result[current_key] = line_stripped.split(":", 1)[1].strip()
        elif current_key and line_stripped:
            result[current_key] += " " + line_stripped

    # Clean up the fix command (remove any code fences the LLM might add)
    result["fix"] = strip_code_fences(result["fix"]).strip()

    return result


@fix_app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    error_words: Annotated[
        Optional[List[str]],
        typer.Argument(help="Error text or command to diagnose. If omitted, auto-detects last command."),
    ] = None,
):
    """
    Diagnose a failed command and suggest a fix.

    Examples:
      ai fix                              Auto-detect last failed command
      ai fix lsg                          Diagnose a specific command
      ai fix \"ModuleNotFoundError: ...\"   Diagnose a pasted error
      npm run build 2>&1 | ai fix         Pipe error output
    """
    if ctx.invoked_subcommand is not None:
        return

    config = get_config()
    set_language(config.get("LANGUAGE", "en"))
    key = config.get("GOOGLE_API_KEY")
    model = config.get("MODEL", "gemini-1.5-flash")

    if not key:
        raise KnownError(
            _("Please set your Google Gemini API key via `ai config set GOOGLE_API_KEY=<your_token>`")
        )

    error_context = ""
    piped_mode = not sys.stdin.isatty()

    # ── Priority 1: Piped input (e.g., command 2>&1 | ai fix) ──
    if piped_mode:
        error_text = sys.stdin.read().strip()
        if error_text:
            error_context = f"ERROR OUTPUT:\n{error_text[:3000]}"
        else:
            console.print("[yellow]No error received from pipe.[/yellow]")
            return

    # ── Priority 2: User provided a command/error as argument ──
    elif error_words:
        user_input = " ".join(error_words)
        # If it looks like a command (no spaces or looks like a shell command), try running it
        exit_code, output = _capture_error(user_input)
        if exit_code != 0:
            error_context = (
                f"COMMAND: {user_input}\n"
                f"EXIT CODE: {exit_code}\n"
                f"ERROR OUTPUT:\n{output[:2000]}"
            )
        else:
            # Treated as a plain error/context description
            error_context = f"ERROR/CONTEXT: {user_input}"

    # ── Priority 3: Auto-detect last command from history, re-run to capture error ──
    else:
        last_cmd = _get_last_command()
        if not last_cmd:
            console.print("[yellow]Could not read shell history.[/yellow]")
            console.print('[dim]Tip: ai fix <command>  — e.g. ai fix lsg[/dim]')
            return

        console.print(f"[dim]Detected:[/dim] [bold yellow]{last_cmd}[/bold yellow]")
        console.print("[dim]Running to capture error...[/dim]\n")

        exit_code, output = _capture_error(last_cmd)

        if exit_code == 0:
            console.print("[green]✔ That command ran successfully — nothing to fix![/green]")
            console.print(f"[dim]If you meant a different command, run: ai fix <command>[/dim]")
            return

        error_context = (
            f"COMMAND: {last_cmd}\n"
            f"EXIT CODE: {exit_code}\n"
            f"ERROR OUTPUT:\n{output[:2000]}"
        )

    if not error_context:
        console.print("[yellow]No error to diagnose.[/yellow]")
        return

    # ── Diagnose with LLM ──
    console.print(f"\n[bold cyan]🔍 Diagnosing...[/bold cyan]\n")

    with console.status("[cyan]Analyzing...[/cyan]"):
        response = _diagnose_and_fix(error_context, key, model)
        parsed = _parse_fix_response(response)

    # ── Display results ──
    if parsed["diagnosis"]:
        console.print(Panel(parsed["diagnosis"], title="🔍 Diagnosis", border_style="yellow"))

    if parsed["fix"]:
        console.print(
            Panel(
                f"[bold yellow]{parsed['fix']}[/bold yellow]",
                title="🔧 Suggested Fix",
                border_style="green",
            )
        )

    if parsed["explanation"]:
        console.print(Panel(parsed["explanation"], title="💡 Explanation", border_style="dim"))

    # ── Offer to run the fix ──
    if not piped_mode and parsed["fix"]:
        action = questionary.select(
            "What would you like to do?",
            choices=[
                questionary.Choice("✅ Run the fix", value="run"),
                questionary.Choice("📝 Edit before running", value="edit"),
                questionary.Choice("📋 Copy to clipboard", value="copy"),
                questionary.Choice("❌ Cancel", value="cancel"),
            ],
        ).ask()

        if action == "run":
            _run_fix(parsed["fix"])
        elif action == "edit":
            edited = questionary.text("Edit command:", default=parsed["fix"]).ask()
            if edited:
                _run_fix(edited)
        elif action == "copy":
            import pyperclip
            pyperclip.copy(parsed["fix"])
            console.print("[green]✔ Copied to clipboard![/green]")
        else:
            console.print("[yellow]Cancelled.[/yellow]")


def _run_fix(command: str):
    """Runs a fix command with security check."""
    if is_risky_command(command):
        if not verify_identity():
            return

    console.print(f"\n[dim]{_('Running')}: {command}[/dim]\n")
    try:
        subprocess.run(command, shell=True, check=True, executable=os.environ.get("SHELL"))
        append_to_shell_history(command)
        console.print("\n[green]✔ Fix applied successfully![/green]")
    except subprocess.CalledProcessError:
        console.print("[red]✖ Fix command also failed. You may need to debug further.[/red]")
    except Exception as e:
        console.print(f"[red]✖ Failed to run fix: {e}[/red]")
