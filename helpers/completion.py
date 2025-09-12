import os
import textwrap
from typing import Generator
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.core.llms import ChatMessage
from rich.console import Console

from .os_detect import detect_shell
from .i18n import _, set_language
from .config import get_config
from .error import KnownError

SHELL_CODE_EXCLUSIONS = ["```bash", "```sh", "```zsh", "```powershell", "```", ""]

def get_gemini_llm(key: str, model: str) -> GoogleGenAI:
    """Initializes and returns the Gemini LLM instance."""
    if not key:
        raise KnownError(
            _("Please set your Google Gemini API key via `ai config set GOOGLE_API_KEY=<your_token>`")
        )
    # This is the updated, cleaner way to initialize the client.
    return GoogleGenAI(model=model, api_key=key)

def get_os_details() -> str:
    import platform
    return platform.system()

def get_shell_details() -> str:
    shell = detect_shell()
    return f"The target shell is {shell}"

def generate_completion_stream(
    prompt: str,
    key: str,
    model: str,
) -> Generator[str, None, None]:
    """Generates a streaming completion from the Gemini API."""
    try:
        llm = get_gemini_llm(key, model)
        response_stream = llm.stream_chat([ChatMessage(role="user", content=prompt)])
        for r in response_stream:
            yield r.delta
    except Exception as e:
        raise KnownError(f"Error communicating with Google Gemini API: {e}")

def get_script_and_info(prompt: str, key: str, model: str) -> str:
    """Generates just the shell script from a prompt."""
    full_prompt = textwrap.dedent(f"""
        Create a single line command that one can enter in a terminal and run, based on what is specified in the prompt.
        {get_shell_details()}
        Only reply with the single line command. It must be able to be directly run in the target shell. Do not include any other text, explanations, or code fences.
        Make sure the command runs on the {get_os_details()} operating system.
        The prompt is: {prompt}
    """)
    llm = get_gemini_llm(key, model)
    response = llm.complete(full_prompt)
    return strip_code_fences(response.text)

def get_explanation(script: str, key: str, model: str) -> Generator[str, None, None]:
    """Generates an explanation for a given script."""
    config = get_config()
    set_language(config.get("LANGUAGE", "en"))

    prompt = textwrap.dedent(f"""
        Please provide a clear, concise description of the following script, using minimal words. Outline the steps in a list format.
        Please reply in the user's language: {_('Language')}
        The script is: {script}
    """)
    return generate_completion_stream(prompt, key, model)

def get_revision(prompt: str, code: str, key: str, model: str) -> str:
    """Generates a revised script based on user feedback."""
    full_prompt = textwrap.dedent(f"""
        Update the following script based on what is asked in the following prompt.
        The script: {code}
        The prompt: {prompt}
        {get_shell_details()}
        Only reply with the single line command. It must be able to be directly run in the target shell. Do not include any other text, explanations, or code fences.
    """)
    llm = get_gemini_llm(key, model)
    response = llm.complete(full_prompt)
    return strip_code_fences(response.text)

def strip_code_fences(text: str) -> str:
    """Removes markdown code fences from a string."""
    lines = text.strip().split('\n')
    # Filter out lines that are just code fences
    filtered_lines = [line for line in lines if not line.strip().startswith("```")]
    return "\n".join(filtered_lines).strip()


def read_stream_and_print(stream: Generator[str, None, None]) -> str:
    """Reads a generator stream, prints it to the console, and returns the full string."""
    full_response = ""
    console = Console()
    for chunk in stream:
        print(chunk, end="", flush=True)
        full_response += chunk
    return full_response
