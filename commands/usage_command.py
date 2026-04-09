# commands/usage_command.py
"""
The `ai usage` command — displays API usage statistics and estimated costs.
"""
import typer
import questionary
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from helpers.usage_tracker import get_usage_summary, reset_usage

usage_app = typer.Typer(
    help="View API usage and estimated costs.",
    invoke_without_command=True,
)
console = Console()


@usage_app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """Show API usage statistics and estimated costs."""
    if ctx.invoked_subcommand is not None:
        return

    summary = get_usage_summary()
    today = summary["today"]
    total = summary["all_time"]

    table = Table(title="📊 AI Shell — API Usage Summary", border_style="dim")
    table.add_column("Period", style="cyan", justify="left")
    table.add_column("API Calls", style="green", justify="right")
    table.add_column("Input Tokens", style="yellow", justify="right")
    table.add_column("Output Tokens", style="yellow", justify="right")
    table.add_column("Est. Cost (USD)", style="bold magenta", justify="right")

    table.add_row(
        "Today",
        str(today["calls"]),
        f"{today['input_tokens']:,}",
        f"{today['output_tokens']:,}",
        f"${today['estimated_cost_usd']:.4f}",
    )
    table.add_row(
        "All Time",
        str(total["calls"]),
        f"{total['input_tokens']:,}",
        f"{total['output_tokens']:,}",
        f"${total['estimated_cost_usd']:.4f}",
    )

    console.print()
    console.print(table)
    console.print()
    console.print("[dim]Note: Token counts and costs are estimates (~4 chars/token).[/dim]")
    console.print()


@usage_app.command("reset")
def reset_cmd():
    """Reset all usage tracking data."""
    confirm = questionary.confirm("Are you sure you want to reset all usage data?", default=False).ask()
    if confirm:
        reset_usage()
        console.print("[green]✔ Usage data has been reset.[/green]")
    else:
        console.print("[yellow]Cancelled.[/yellow]")
