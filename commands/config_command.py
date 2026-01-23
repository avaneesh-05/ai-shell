import typer
from rich.console import Console
from rich.panel import Panel
import questionary
from typing_extensions import Annotated

from helpers.config import get_config, set_configs, has_own, DEFAULT_CONFIG
from helpers.error import KnownError
from helpers.i18n import _

config_app = typer.Typer(
    help="Configure the CLI.",
    no_args_is_help=True,
    invoke_without_command=True
)
console = Console()

@config_app.callback()
def main(
    ctx: typer.Context,
    mode: Annotated[str, typer.Argument(help="The mode: 'get', 'set', or 'ui'.")] = "ui",
    key_values: Annotated[list[str], typer.Argument(help="Key-value pairs.")] = None,
):
    if ctx.invoked_subcommand is not None:
        return

    if mode == 'ui':
        run_config_ui()
    elif mode == 'get':
        if not key_values:
            raise KnownError("Missing parameter 'key'")
        config_get(key_values)
    elif mode == 'set':
        if not key_values:
            raise KnownError("Missing parameter 'key=value'")
        pairs = [tuple(kv.split('=', 1)) for kv in key_values if '=' in kv]
        config_set(pairs)

def config_get(keys: list[str]):
    config = get_config()
    for key in keys:
        key_upper = key.upper()
        if has_own(config, key_upper):
            console.print(f"{key_upper}={config[key_upper]}")
        else:
            raise KnownError(f"Invalid property: {key}")

def config_set(pairs: list[tuple[str, str]]):
    set_configs(pairs)
    console.print("[green]✔ Config updated.[/green]")

def run_config_ui():
    """Interactive UI for configuration (API, Email, Security)."""
    config = get_config()

    try:
        console.print(Panel("[bold]AI Shell Configuration[/bold]", style="blue"))

        # 1. API & General
        api_key = questionary.text("Google Gemini API Key:", default=config.get("GOOGLE_API_KEY") or "").ask()
        model = questionary.text("Model:", default=config.get("MODEL", "gemini-1.5-flash")).ask()
        
        # 2. Email Config
        configure_email = questionary.confirm("Configure Email settings?", default=False).ask()
        email_user = config.get("EMAIL_USER")
        email_pass = config.get("EMAIL_PASSWORD")
        
        if configure_email:
            email_user = questionary.text("Email Address:", default=config.get("EMAIL_USER") or "").ask()
            email_pass = questionary.password("Email App Password:", default=config.get("EMAIL_PASSWORD") or "").ask()

        # 3. Security Config (PIN Change)
        change_pin = questionary.confirm("Change Security PIN?", default=False).ask()
        new_pin_val = config.get("SECURITY_PIN", "1234")

        if change_pin:
            current_stored = str(config.get("SECURITY_PIN", "1234"))
            entered_old = questionary.password("Enter Current PIN:").ask()
            
            if entered_old == current_stored:
                p1 = questionary.password("Enter New PIN:").ask()
                p2 = questionary.password("Confirm New PIN:").ask()
                if p1 == p2 and p1:
                    new_pin_val = p1
                    console.print("[green]✔ PIN updated in memory (save to apply).[/green]")
                else:
                    console.print("[red]✖ PINs do not match. Keeping old PIN.[/red]")
            else:
                console.print("[red]✖ Incorrect Current PIN. Cannot change.[/red]")

        # Save All
        if api_key:
             set_configs([
                ("GOOGLE_API_KEY", api_key),
                ("MODEL", model),
                ("EMAIL_USER", email_user),
                ("EMAIL_PASSWORD", email_pass),
                ("SECURITY_PIN", new_pin_val)
            ])
             console.print("\n[green]✔ Configuration successfully saved![/green]")

    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled.[/yellow]")