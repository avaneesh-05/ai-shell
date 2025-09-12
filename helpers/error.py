import sys
import traceback
from rich.console import Console
from rich.text import Text

from .constants import project_name, __version__, repo_url
from .i18n import _

class KnownError(Exception):
    """A custom exception for known error states."""
    pass

def handle_cli_error(error: Exception):
    """
    Handles errors gracefully, printing user-friendly messages for known errors
    and detailed stack traces for unexpected ones.
    """
    console = Console()
    if isinstance(error, KnownError):
        console.print(f"[red]✖ {error}[/red]")
    else:
        console.print(f"[red]✖ An unexpected error occurred: {error}[/red]")
        console.print(f"\n[dim]{project_name} v{__version__}[/dim]")
        console.print(f"[dim]{_('Please open a Bug report with the information above')}:[/dim]")
        console.print(f"[dim]{repo_url}/issues/new[/dim]\n")
        traceback.print_exc()

    sys.exit(1)