import typer
import questionary
from rich.console import Console
from rich.spinner import Spinner
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.core.llms import ChatMessage

from helpers.config import get_config
from helpers.error import KnownError
from helpers.i18n import _

# This `invoke_without_command=True` is the critical fix
chat_app = typer.Typer(
    help="Start a new chat session.",
    invoke_without_command=True
)
console = Console()

@chat_app.callback()
def main():
    """
    Starts an interactive chat session with the AI model.
    """
    try:
        config = get_config()
        key = config.get("GOOGLE_API_KEY")
        model = config.get("MODEL", "gemini-1.5-flash")

        if not key:
            raise KnownError(_("Please set your Google Gemini API key via `ai config set GOOGLE_API_KEY=<your_token>`"))

        llm = GoogleGenAI(model=model, api_key=key)
        chat_history = []

        console.print(f"\n[bold cyan]{_('Starting new conversation')}[/bold cyan]")
        console.print(_("send a message ('exit' to quit)"))

        while True:
            prompt = questionary.text(f"{_('You')}:").ask()

            if not prompt or prompt.lower() == 'exit':
                console.print(f"[yellow]{_('Goodbye!')}[/yellow]")
                break
            
            chat_history.append(ChatMessage(role="user", content=prompt))

            with console.status(Spinner("dots", text=f"[cyan]{_('THINKING...')}[/cyan]")):
                response_stream = llm.stream_chat(chat_history)
            
            console.print("\n[bold green]AI Shell:[/bold green]")
            
            full_response = ""
            for r in response_stream:
                chunk = r.delta
                print(chunk, end="", flush=True)
                full_response += chunk
            
            print("\n") # Newline after response
            chat_history.append(ChatMessage(role="assistant", content=full_response))

    except (KeyboardInterrupt):
        console.print(f"\n[yellow]{_('Goodbye!')}[/yellow]")
    except Exception as e:
        raise KnownError(f"A chat error occurred: {e}")

