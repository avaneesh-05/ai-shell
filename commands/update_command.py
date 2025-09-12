import typer
import subprocess
from rich.console import Console
from helpers.i18n import _

# This `invoke_without_command=True` is the critical fix
update_app = typer.Typer(
    help="Update AI Shell to the latest version.",
    invoke_without_command=True
)
console = Console()

@update_app.callback()
def main():
    """
    Updates the 'ai-shell' package using pip.
    """
    command = "pip install --upgrade ai-shell"
    console.print(f"\n[dim]{_('Running')}: {command}[/dim]\n")
    try:
        subprocess.run(command, shell=True, check=True)
        console.print("\n[green]✔ Update complete.[/green]\n")
    except subprocess.CalledProcessError:
        console.print(f"\n[red]✖ Update failed. Please try running the command manually:[/red]")
        console.print(f"  {command}")

