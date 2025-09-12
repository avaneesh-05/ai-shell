import typer
from rich.console import Console
import questionary
from typing_extensions import Annotated

from helpers.config import get_config, set_configs, has_own, DEFAULT_CONFIG
from helpers.error import KnownError
from helpers.i18n import _

# The `invoke_without_command=True` is the key fix.
# It tells Typer that `ai config` can be run without needing another subcommand.
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
    key_values: Annotated[list[str], typer.Argument(help="Key-value pairs to set, e.g., 'MODEL=gemini-pro'.")] = None,
):
    """
    Manages CLI configuration. Defaults to UI mode if no mode is specified.
    """
    if ctx.invoked_subcommand is not None:
        return

    if mode == 'ui':
        run_config_ui()
    elif mode == 'get':
        if not key_values:
            raise KnownError(f"{_('Error')}: {_('Missing required parameter')} 'key'")
        config_get(key_values)
    elif mode == 'set':
        if not key_values:
            raise KnownError(f"{_('Error')}: {_('Missing required parameter')} 'key=value'")

        pairs = []
        for kv in key_values:
            if '=' not in kv:
                raise KnownError(f"Invalid format for 'set'. Use 'key=value'.")
            pairs.append(tuple(kv.split('=', 1)))

        config_set(pairs)
    else:
        raise KnownError(f"{_('Invalid mode')}: {mode}")

def config_get(keys: list[str]):
    config = get_config()
    for key in keys:
        key_upper = key.upper()
        if has_own(config, key_upper):
            console.print(f"{key_upper}={config[key_upper]}")
        else:
            raise KnownError(f"{_('Invalid config property')}: {key}")

def config_set(pairs: list[tuple[str, str]]):
    set_configs(pairs)
    console.print("[green]✔ Config updated.[/green]")

def run_config_ui():
    """An interactive UI for setting configuration."""
    config = get_config()

    try:
        api_key = questionary.text(
            _('Enter your Google Gemini API key'),
            default=config.get("GOOGLE_API_KEY") or "",
        ).ask()

        model = questionary.text(
            _('Enter the model you want to use'),
            default=config.get("MODEL", DEFAULT_CONFIG["MODEL"]),
        ).ask()

        silent_mode = questionary.confirm(
            _('Enable silent mode?'),
            default=config.get("SILENT_MODE", DEFAULT_CONFIG["SILENT_MODE"]),
        ).ask()

        language = questionary.text(
            _('Enter the language you want to use'),
            default=config.get("LANGUAGE", DEFAULT_CONFIG["LANGUAGE"]),
        ).ask()

        if api_key is not None and model is not None and silent_mode is not None and language is not None:
             set_configs([
                ("GOOGLE_API_KEY", api_key),
                ("MODEL", model),
                ("SILENT_MODE", str(silent_mode)),
                ("LANGUAGE", language),
            ])
             console.print("[green]✔ Config saved.[/green]")
        else:
            console.print(f"\n[yellow]{_('Goodbye!')}[/yellow]")


    except (KeyboardInterrupt):
        console.print(f"\n[yellow]{_('Goodbye!')}[/yellow]")
