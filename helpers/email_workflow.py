import questionary
import textwrap
import json
from rich.console import Console
from rich.panel import Panel
from llama_index.llms.google_genai import GoogleGenAI

from helpers.config import get_config, set_configs
from helpers.email_sender import send_email_via_smtp
from helpers.i18n import _

console = Console()

def ensure_email_config():
    """Checks configuration. If exists, asks user to confirm or switch."""
    config = get_config()
    current_user = config.get("EMAIL_USER")
    current_pass = config.get("EMAIL_PASSWORD")

    if current_user and current_pass:
        # FIX: We print the styled text using Rich first, then use a simple prompt.
        # This prevents "[bold cyan]" from appearing as raw text in the prompt.
        console.print(f"Current Email Account: [bold cyan]{current_user}[/bold cyan]")
        use_existing = questionary.confirm(
            "Do you want to send with this account?",
            default=True
        ).ask()
        
        if use_existing:
            return config
        else:
            console.print("[dim]Okay, let's configure a new account.[/dim]")

    console.print(Panel(_("Configure Email Sender"), style="yellow"))
    
    email_user = questionary.text(_("Enter your Email Address:")).ask()
    console.print("[dim]Note: For Gmail, use an 'App Password', not your login password.[/dim]")
    email_pass = questionary.password(_("Enter your Email Password:")).ask()
    
    set_configs([
        ("EMAIL_USER", email_user),
        ("EMAIL_PASSWORD", email_pass),
        ("SMTP_SERVER", "smtp.gmail.com"), 
        ("SMTP_PORT", "465"),
    ])
    
    console.print("[green]✔ New credentials saved![/green]\n")
    return get_config()

def iterative_draft_update(current_draft, user_input, key, model, history_str, is_first_turn=False, mode="DRAFT"):
    """
    Handles drafting/editing with FULL CONTEXT awareness.
    """
    llm = GoogleGenAI(model=model, api_key=key)
    
    if mode == "EDIT":
        system_prompt = textwrap.dedent(f"""
            You are an expert email editor.
            Current Draft:
            {current_draft}
            
            User Instruction: "{user_input}"
            
            Task:
            1. Edit the draft strictly following the instruction.
            2. Return the JSON with the updated draft and status COMPLETE.
            
            Output JSON ONLY:
            {{ "draft": "...", "question": null, "status": "COMPLETE" }}
        """)
    elif is_first_turn:
        system_prompt = textwrap.dedent(f"""
            You are an expert email drafter.
            User Request: "{user_input}"
            
            Task:
            1. Draft a professional email. Use placeholders like [Date] if details are missing.
            2. Formulate ONE critical question to fill the biggest gap.
            
            Output JSON ONLY:
            {{ "draft": "...", "question": "Question text", "status": "CONTINUE" }}
        """)
    else:
        system_prompt = textwrap.dedent(f"""
            You are an expert email drafter.
            
            CONTEXT HISTORY:
            {history_str}
            
            CURRENT DRAFT:
            {current_draft}
            
            LATEST USER ANSWER: "{user_input}"
            
            Task:
            1. Update the draft with the Latest User Answer.
            2. Check for remaining placeholders (e.g., [Name], [Date]).
            3. Formulate the NEXT question.
            4. CRITICAL RULE: DO NOT ask a question that is already in the CONTEXT HISTORY.
            5. If no important details are missing, set status to COMPLETE.
            
            Output JSON ONLY:
            {{ "draft": "...", "question": "Next question", "status": "CONTINUE" or "COMPLETE" }}
        """)

    try:
        response = llm.complete(system_prompt).text.strip()
        if response.startswith("```"):
            response = response.strip("`").replace("json", "").strip()
        return json.loads(response)
    except Exception:
        return {"draft": current_draft, "question": None, "status": "COMPLETE"}

def handle_email_intent(user_prompt: str):
    """
    Main Flow with History Tracking and Live Previews.
    """
    config = ensure_email_config()
    key = config.get("GOOGLE_API_KEY")
    model = config.get("MODEL")

    console.print("[dim]Tip: You can enter multiple emails separated by commas.[/dim]")
    recipients_input = questionary.text(_("To:")).ask()
    
    if not recipients_input:
        console.print("[yellow]Aborted.[/yellow]")
        return
    
    recipient_list = [r.strip() for r in recipients_input.split(',') if r.strip()]
    recipients_display = ", ".join(recipient_list)

    # State Variables
    current_draft = ""
    next_question = None
    status = "CONTINUE"
    user_input = user_prompt
    is_first = True
    history = [] 

    console.print(f"\n[bold cyan]Drafting your email...[/bold cyan]")

    while status == "CONTINUE":
        history_str = "\n".join(history)
        
        with console.status("[cyan]Updating draft...[/cyan]"):
            result = iterative_draft_update(current_draft, user_input, key, model, history_str, is_first, mode="DRAFT")
        
        current_draft = result.get("draft", "")
        next_question = result.get("question")
        status = result.get("status", "COMPLETE")
        
        # Log Interaction
        if is_first:
            history.append(f"User Request: {user_input}")
        else:
            history.append(f"User Answer: {user_input}")
        is_first = False

        if status == "COMPLETE" or not next_question:
            break

        # Log Question
        history.append(f"AI Question: {next_question}")

        # === NEW: Show the Rough Draft ===
        # This panel shows the user exactly what the AI has written so far
        console.print(Panel(current_draft, title="Current Working Draft", style="dim blue"))
        # =================================

        # Ask the user
        user_input = questionary.text(f"❓ {next_question}").ask()
        if not user_input or user_input.lower() in ["skip", "done"]:
            status = "COMPLETE"

    # Final Review Loop
    while True:
        lines = current_draft.strip().split('\n')
        subject = "No Subject"
        body = current_draft
        for i, line in enumerate(lines):
            if line.lower().startswith("subject:"):
                subject = line.split(":", 1)[1].strip()
                body = "\n".join(lines[i+1:]).strip()
                break

        console.print(Panel(f"[bold]To:[/bold] {recipients_display}\n[bold]Subject:[/bold] {subject}\n\n{body}", title="Final Review", border_style="green"))
        
        action = questionary.select(
            "What next?",
            choices=[
                questionary.Choice("✅ Send Email", value="send"),
                questionary.Choice("✨ AI Edit / Refine", value="ai_edit"),
                questionary.Choice("📝 Manual Edit Body", value="edit_body"),
                questionary.Choice("✏️ Manual Edit Subject", value="edit_subject"),
                questionary.Choice("❌ Cancel", value="cancel"),
            ]
        ).ask()

        if action == "send":
            with console.status("[cyan]Sending...[/cyan]"):
                send_email_via_smtp(recipient_list, subject, body, config)
            console.print(f"[green]✔ Email sent to {len(recipient_list)} recipient(s)![/green]")
            break
            
        elif action == "ai_edit":
            instruction = questionary.text("What should I change?").ask()
            if instruction:
                with console.status("[cyan]Refining draft...[/cyan]"):
                    full_text = f"Subject: {subject}\n\n{body}"
                    result = iterative_draft_update(full_text, instruction, key, model, "", mode="EDIT")
                    current_draft = result.get("draft", current_draft)
                    
        elif action == "edit_body":
            body = questionary.text("Edit Body:", default=body, multiline=True).ask()
            current_draft = f"Subject: {subject}\n\n{body}"
            
        elif action == "edit_subject":
            subject = questionary.text("Edit Subject:", default=subject).ask()
            current_draft = f"Subject: {subject}\n\n{body}"
            
        else:
            console.print("[yellow]Cancelled.[/yellow]")
            break