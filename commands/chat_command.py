# import typer
# import questionary
# from rich.console import Console
# from rich.spinner import Spinner
# from llama_index.llms.google_genai import GoogleGenAI
# from llama_index.core.llms import ChatMessage

# from helpers.config import get_config
# from helpers.error import KnownError
# from helpers.i18n import _

# # This `invoke_without_command=True` is the critical fix
# chat_app = typer.Typer(
#     help="Start a new chat session.",
#     invoke_without_command=True
# )
# console = Console()

# @chat_app.callback()
# def main():
#     """
#     Starts an interactive chat session with the AI model.
#     """
#     try:
#         config = get_config()
#         key = config.get("GOOGLE_API_KEY")
#         model = config.get("MODEL", "gemini-1.5-flash")

#         if not key:
#             raise KnownError(_("Please set your Google Gemini API key via `ai config set GOOGLE_API_KEY=<your_token>`"))

#         llm = GoogleGenAI(model=model, api_key=key)
#         chat_history = []

#         console.print(f"\n[bold cyan]{_('Starting new conversation')}[/bold cyan]")
#         console.print(_("send a message ('exit' to quit)"))

#         while True:
#             prompt = questionary.text(f"{_('You')}:").ask()

#             if not prompt or prompt.lower() == 'exit':
#                 console.print(f"[yellow]{_('Goodbye!')}[/yellow]")
#                 break
            
#             chat_history.append(ChatMessage(role="user", content=prompt))

#             with console.status(Spinner("dots", text=f"[cyan]{_('THINKING...')}[/cyan]")):
#                 response_stream = llm.stream_chat(chat_history)
            
#             console.print("\n[bold green]AI Shell:[/bold green]")
            
#             full_response = ""
#             for r in response_stream:
#                 chunk = r.delta
#                 print(chunk, end="", flush=True)
#                 full_response += chunk
            
#             print("\n") # Newline after response
#             chat_history.append(ChatMessage(role="assistant", content=full_response))

#     except (KeyboardInterrupt):
#         console.print(f"\n[yellow]{_('Goodbye!')}[/yellow]")
#     except Exception as e:
#         raise KnownError(f"A chat error occurred: {e}")

import typer
import questionary
from rich.console import Console
from rich.spinner import Spinner
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.core.llms import ChatMessage
from llama_index.core.tools import FunctionTool

from helpers.config import get_config
from helpers.error import KnownError
from helpers.i18n import _
from helpers.email_workflow import handle_email_intent

chat_app = typer.Typer(help="Start a new chat session.", invoke_without_command=True)
console = Console()

def trigger_email_flow(instruction: str):
    """
    Tool function that triggers the interactive email workflow.
    """
    console.print(f"\n[dim]AI has detected an email request: {instruction}[/dim]")
    handle_email_intent(instruction)
    return "Email flow completed."

@chat_app.callback()
def main():
    try:
        config = get_config()
        key = config.get("GOOGLE_API_KEY")
        model = config.get("MODEL", "gemini-1.5-flash")

        # Define the tool
        email_tool = FunctionTool.from_defaults(
            fn=trigger_email_flow,
            name="send_email_interactive",
            description="Use this tool if the user explicitly wants to send an email or draft a mail."
        )

        # Attach tool to LLM
        llm = GoogleGenAI(model=model, api_key=key)
        # Note: LlamaIndex GoogleGenAI doesn't support 'tools=' in constructor 
        # the same way as raw genai. But we can use the chat engine or manual checking.
        # FOR SIMPLICITY in this specific CLI structure, we will use the RAW genai logic 
        # (like your MCP code) OR a simple classification check inside the loop.
        
        # Let's use the Simple Classification inside the loop to keep it robust
        # without rewriting your entire dependency stack.
        
        chat_history = []
        console.print(f"\n[bold cyan]{_('Starting new conversation')}[/bold cyan]")

        while True:
            prompt = questionary.text(f"{_('You')}:").ask()
            if not prompt or prompt.lower() == 'exit':
                break
            
            chat_history.append(ChatMessage(role="user", content=prompt))

            # === INTENT CHECK ===
            # We peek at the intent before sending to the chat bot
            classifier = GoogleGenAI(model=model, api_key=key)
            is_email = classifier.complete(
                f"History: {chat_history[-5:]}\nUser: {prompt}\n"
                "Is the user asking to send an email right now? Reply YES or NO."
            ).text.strip()

            if "YES" in is_email.upper():
                handle_email_intent(prompt)
                chat_history.append(ChatMessage(role="assistant", content="[Initiated Email Workflow]"))
                continue
            # ====================

            with console.status(Spinner("dots", text=f"[cyan]{_('THINKING...')}[/cyan]")):
                response_stream = llm.stream_chat(chat_history)
            
            console.print("\n[bold green]AI Shell:[/bold green]")
            full_response = ""
            for r in response_stream:
                print(r.delta, end="", flush=True)
                full_response += r.delta
            
            print("\n")
            chat_history.append(ChatMessage(role="assistant", content=full_response))

    except (KeyboardInterrupt):
        console.print(f"\n[yellow]{_('Goodbye!')}[/yellow]")