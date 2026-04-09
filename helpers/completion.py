# helpers/completion.py
import os
import json
import textwrap
from typing import Generator, List, Dict, Any
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.core.llms import ChatMessage
from rich.console import Console

from .os_detect import detect_shell
from .i18n import _, set_language
from .config import get_config
from .error import KnownError
from .context import get_current_directory_context
from .tracked_llm import TrackedLLM


def get_gemini_llm(key: str, model: str) -> TrackedLLM:
    """Initializes and returns a TrackedLLM instance (wraps GoogleGenAI with usage tracking)."""
    if not key:
        raise KnownError(
            _("Please set your Google Gemini API key via `ai config set GOOGLE_API_KEY=<your_token>`")
        )
    return TrackedLLM(model=model, api_key=key)


def get_os_details() -> str:
    import platform
    return platform.system()


def get_shell_details() -> str:
    shell = detect_shell()
    return f"The target shell is {shell}"


def get_execution_plan(prompt: str, key: str, model: str, llm: GoogleGenAI = None) -> List[Dict[str, str]]:
    """
    Generates a multi-step execution plan in JSON format.
    Accepts an optional pre-initialized LLM instance to avoid redundant initialization.
    """
    if llm is None:
        llm = get_gemini_llm(key, model)

    # Gather filesystem context for awareness
    fs_context = get_current_directory_context()

    full_prompt = textwrap.dedent(f"""
        You are an expert DevOps engineer with exceptional context awareness.
        
        USER REQUEST: "{prompt}"
        
        SYSTEM AWARENESS (Files actually on this computer):
        {fs_context}
        
        CRITICAL CONTEXT ANALYSIS (READ THIS FIRST):
        =============================================
        BEFORE generating a plan, determine the REQUEST TYPE:
        
        REQUEST TYPE A: FILE LISTING / INSPECTION QUERIES
        - User asks: "what files", "which files", "list files", "show files", "what .py files", etc.
        - User wants: A list of files matching certain criteria (e.g., related to email, containing keywords)
        - YOUR ACTION: Generate a single grep/find command that lists matching files
        - EXAMPLE: User: "what .py files are related to email?"
                   Response: [{{ "description": "Find email-related Python files", "command": "find . -name '*.py' | xargs grep -l 'email\\\\|smtp\\\\|send_email' | grep -v __pycache__" }}]
        - DO NOT trigger any email workflows, config UI, or auxiliary features
        - Return clean, working commands with proper escaping
        
        REQUEST TYPE B: TASK EXECUTION / MODIFICATIONS
        - User asks: "delete files", "create a script", "install package", "modify config", "send email", etc.
        - User wants: Multi-step execution plan to accomplish a specific task
        - YOUR ACTION: Generate step-by-step plan with descriptions and commands
        
        REQUEST TYPE C: CODE/PROJECT ANALYSIS
        - User asks: "analyze this feature", "explain how this works", "refactor this code", etc.
        - User wants: Understanding of code structure, not execution
        - YOUR ACTION: Return a description with relevant file paths and no shell commands
        
        RULES FOR FILE MATCHING:
        1. IF the user mentions a file loosely (e.g. "hello", "script") AND you see a matching file in System Awareness (e.g. "hello.txt", "script.py"), YOU MUST USE THE EXISTING FILENAME.
        2. Do not create new files if a file with a similar name already exists, unless explicitly asked.
        3. Correct user typos based on the directory list (e.g. "dekstop" -> "Desktop").
        
        INSTRUCTIONS:
        1. Identify REQUEST TYPE from the user request above.
        2. Generate appropriate response based on type.
        3. Return a JSON LIST of steps (even for single-step operations).
        4. Ensure shell commands are properly escaped and will run without syntax errors.
        
        FORMAT:
        [
            {{
                "description": "Brief text describing this step",
                "command": "shell command or result"
            }}
        ]
        
        - OS: {get_os_details()}
        - Shell: {get_shell_details()}
        - Return ONLY valid JSON. No markdown, no explanations outside JSON.
    """)

    response = llm.complete(full_prompt).text.strip()
    cleaned_response = strip_code_fences(response)

    try:
        plan = json.loads(cleaned_response)
        if isinstance(plan, list):
            return plan
        # If LLM returns a single object instead of a list
        if isinstance(plan, dict):
            return [plan]
        raise ValueError("Invalid JSON format")
    except Exception:
        # Fallback: If JSON parsing fails, treat the whole response as one command
        return [{"description": "Execute command", "command": cleaned_response}]


def get_explanation(script: str, key: str, model: str, llm: GoogleGenAI = None) -> Generator[str, None, None]:
    """Generates a streaming explanation for a given script."""
    if llm is None:
        llm = get_gemini_llm(key, model)

    config = get_config()
    set_language(config.get("LANGUAGE", "en"))

    prompt = textwrap.dedent(f"""
        Explain this command briefly, outlining each step in a short list:
        {script}
    """)
    response_stream = llm.stream_chat([ChatMessage(role="user", content=prompt)])
    for r in response_stream:
        yield r.delta


def get_revision(prompt: str, code: str, key: str, model: str, llm: GoogleGenAI = None) -> str:
    """Generates a revised script based on user feedback."""
    if llm is None:
        llm = get_gemini_llm(key, model)

    full_prompt = textwrap.dedent(f"""
        Original Script: {code}
        User Change Request: {prompt}
        {get_shell_details()}
        Return ONLY the updated shell command.
    """)
    response = llm.complete(full_prompt)
    return strip_code_fences(response.text)


def strip_code_fences(text: str) -> str:
    """Removes markdown code fences and JSON markers."""
    text = text.replace("```json", "").replace("```", "").strip()
    return text


def read_stream_and_print(stream: Generator[str, None, None]) -> str:
    """Reads a generator stream, prints it to the console, and returns the full string."""
    full_response = ""
    for chunk in stream:
        print(chunk, end="", flush=True)
        full_response += chunk
    return full_response