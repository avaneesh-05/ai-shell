# commands/chat_command.py
import typer
import questionary
from rich.console import Console
from rich.spinner import Spinner
from llama_index.core.llms import ChatMessage

from helpers.config import get_config
from helpers.completion import get_gemini_llm
from helpers.error import KnownError
from helpers.i18n import _
from helpers.email_workflow import handle_email_intent

# Keywords that hint this might be an email request
EMAIL_HINT_KEYWORDS = ["email", "e-mail", "mail", "draft", "compose", "smtp"]

chat_app = typer.Typer(help="Start a new chat session.", invoke_without_command=True)
console = Console()


def _might_be_email(text: str) -> bool:
    """Quick keyword check to decide if LLM classification is needed."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in EMAIL_HINT_KEYWORDS)


@chat_app.callback()
def main():
    """Starts an interactive chat session with the AI model."""
    try:
        config = get_config()
        key = config.get("GOOGLE_API_KEY")
        model = config.get("MODEL", "gemini-1.5-flash")

        if not key:
            raise KnownError(_("Please set your Google Gemini API key via `ai config set GOOGLE_API_KEY=<your_token>`"))

        # Single LLM instance, reused for both chat and intent classification
        llm = get_gemini_llm(key, model)
        chat_history = []

        console.print(f"\n[bold cyan]{_('Starting new conversation')}[/bold cyan]")
        console.print(_("send a message ('exit' to quit)"))

        while True:
            prompt = questionary.text(f"{_('You')}:").ask()

            if not prompt or prompt.lower() == 'exit':
                console.print(f"[yellow]{_('Goodbye!')}[/yellow]")
                break

            chat_history.append(ChatMessage(role="user", content=prompt))

            # Keyword pre-filter: only call the LLM classifier when email keywords are present
            if _might_be_email(prompt):
                is_email = llm.complete(
                    f"History: {chat_history[-5:]}\nUser: {prompt}\n"
                    "Is the user asking to send an email right now? Reply YES or NO."
                ).text.strip()

                if "YES" in is_email.upper():
                    handle_email_intent(prompt)
                    chat_history.append(ChatMessage(role="assistant", content="[Initiated Email Workflow]"))
                    continue

            with console.status(Spinner("dots", text=f"[cyan]{_('THINKING...')}[/cyan]")):
                response_stream = llm.stream_chat(chat_history)

            console.print("\n[bold green]AI Shell:[/bold green]")
            full_response = ""
            for r in response_stream:
                print(r.delta, end="", flush=True)
                full_response += r.delta

            print("\n")
            chat_history.append(ChatMessage(role="assistant", content=full_response))

    except KeyboardInterrupt:
        console.print(f"\n[yellow]{_('Goodbye!')}[/yellow]")
    except KnownError:
        raise
    except Exception as e:
        raise KnownError(f"A chat error occurred: {e}")