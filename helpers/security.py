import questionary
from rich.console import Console
from helpers.config import get_config
from helpers.i18n import _

console = Console()

# Commands that trigger the security check
RISKY_KEYWORDS = [
    "rm ", "rmdir", "del ",       # Deletion
    "sudo ", "su ",               # Privilege escalation
    "chmod ", "chown ",           # Permissions
    "dd ", "format ", "mkfs",     # Disk formatting
    "mv ",                        # Moving (can overwrite)
    "kill", "pkill",              # Stopping processes
    "shutdown", "reboot"          # System power
]

def is_risky_command(script: str) -> bool:
    """Returns True if the script contains potentially dangerous operations."""
    script_lower = script.lower()
    # Check if any risky keyword exists in the script
    return any(keyword in script_lower for keyword in RISKY_KEYWORDS)

def verify_identity() -> bool:
    """Prompts for the PIN and verifies it against config."""
    config = get_config()
    stored_pin = str(config.get("SECURITY_PIN", "1234"))

    # Ask for PIN (masked)
    entered_pin = questionary.password(
        _("🔒 RISKY COMMAND DETECTED. Enter Security PIN to proceed:"),
        validate=lambda text: True if text else "PIN cannot be empty"
    ).ask()

    if entered_pin == stored_pin:
        return True
    
    console.print("[bold red]❌ ACCESS DENIED. Incorrect PIN.[/bold red]")
    return False