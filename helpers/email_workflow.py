import questionary
import textwrap
import json
from rich.console import Console
from rich.panel import Panel
from .completion import get_gemini_llm

from helpers.config import get_config, set_configs
from helpers.email_sender import send_email_via_smtp
from helpers.i18n import _

console = Console()

MAX_CLARIFYING_QUESTIONS = 4

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

def extract_subject_and_body(draft_text):
    """Extract subject and body from draft text."""
    lines = draft_text.strip().split('\n')
    subject = "No Subject"
    body = draft_text
    
    for i, line in enumerate(lines):
        if line.lower().startswith("subject:"):
            subject = line.split(":", 1)[1].strip()
            body = "\n".join(lines[i+1:]).strip()
            break
    
    return subject, body

def generate_initial_draft(user_input, key, model):
    """Generate the initial email draft skeleton."""
    llm = get_gemini_llm(key, model)
    
    system_prompt = textwrap.dedent(f"""
        You are an expert email drafter.
        
        User Request: "{user_input}"
        
        Task:
        1. Create a professional email skeleton with Subject and Body.
        2. Format as: Subject: [subject line]\\n\\n[body text]
        3. Use 2-3 sentences initially as a starting point.
        4. Prepare ONE specific, actionable clarifying question to gather more details.
        
        Respond ONLY with JSON (no markdown, no code blocks):
        {{"draft": "Subject: ...\\n\\n...", "question": "Your specific question here"}}
    """)
    
    try:
        response = llm.complete(system_prompt).text.strip()
        # Remove markdown code fences if present
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
            response = response.strip()
        
        result = json.loads(response)
        return result.get("draft", ""), result.get("question", "")
    except Exception as e:
        console.print(f"[yellow]Warning: Could not parse initial draft. {str(e)}[/yellow]")
        return f"Subject: Email\n\n{user_input}", "What specific details should I include?"

def refine_draft(current_draft, user_answer, question_history, key, model, question_count):
    """Refine the draft based on user's answer to a clarifying question."""
    llm = get_gemini_llm(key, model)
    
    # Build context of previous Q&A
    context_history = "\n".join(question_history)
    
    # Determine if we should ask another question
    should_continue = question_count < (MAX_CLARIFYING_QUESTIONS - 1)
    
    system_prompt = textwrap.dedent(f"""
        You are an expert email editor and drafter.
        
        CURRENT DRAFT:
        {current_draft}
        
        CONVERSATION HISTORY:
        {context_history}
        
        USER'S LATEST ANSWER: "{user_answer}"
        QUESTIONS ASKED SO FAR: {question_count} out of {MAX_CLARIFYING_QUESTIONS}
        
        Task:
        1. Integrate the user's answer naturally into the draft.
        2. Improve clarity, tone, and completeness.
        3. Identify gaps that still need addressing.
        4. Format as: Subject: [subject line]\\n\\n[body text]
        5. Create the NEXT clarifying question (or indicate if draft is complete).
        
        CRITICAL RULES:
        - Do NOT repeat questions already asked in the conversation history
        - Focus on: tone/formality, specific details, recipient details, action items, urgency, closing style
        - Keep questions specific and actionable
        - If we've asked {MAX_CLARIFYING_QUESTIONS} questions, ask if they want any final improvements before sending
        
        Respond ONLY with JSON (no markdown, no code blocks):
        {{"draft": "Subject: ...\\n\\n...", "question": "Next question or null if ready for final review"}}
    """)
    
    try:
        response = llm.complete(system_prompt).text.strip()
        # Remove markdown code fences if present
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
            response = response.strip()
        
        result = json.loads(response)
        return result.get("draft", current_draft), result.get("question")
    except Exception as e:
        console.print(f"[yellow]Warning: Could not refine draft. {str(e)}[/yellow]")
        return current_draft, None

def apply_improvements(current_draft, improvement_request, key, model):
    """Apply user-requested improvements to the draft."""
    llm = get_gemini_llm(key, model)
    
    system_prompt = textwrap.dedent(f"""
        You are an expert email editor.
        
        CURRENT DRAFT:
        {current_draft}
        
        USER IMPROVEMENT REQUEST: "{improvement_request}"
        
        Task:
        1. Apply the improvement request to the draft.
        2. Maintain the original intent and content.
        3. Format as: Subject: [subject line]\\n\\n[body text]
        
        Respond ONLY with the improved draft (no JSON, no explanation):
        Subject: [subject]
        
        [body]
    """)
    
    try:
        response = llm.complete(system_prompt).text.strip()
        return response
    except Exception as e:
        console.print(f"[yellow]Warning: Could not apply improvements. {str(e)}[/yellow]")
        return current_draft

def iterative_draft_update(current_draft, user_input, key, model, history_str, is_first_turn=False, mode="DRAFT", question_count=0):
    """
    Handles drafting/editing with FULL CONTEXT awareness.
    Ensures intelligent iterative refinement with multiple clarifying questions.
    """
    llm = get_gemini_llm(key, model)
    
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
            1. Draft a professional email skeleton. Use placeholders like [Recipient Name], [Specific Detail] if needed.
            2. Formulate ONE specific, actionable question to gather more details and improve the email.
            3. The question should help you understand tone, specific details, or purpose better.
            4. ALWAYS set status to "CONTINUE" - we will ask multiple questions to refine the draft.
            
            Output JSON ONLY:
            {{ "draft": "...", "question": "Your specific question here", "status": "CONTINUE" }}
        """)
    else:
        # Determine if we should continue asking or mark as complete
        # Ask at least 3-4 questions before allowing completion
        should_continue = question_count < 3
        
        system_prompt = textwrap.dedent(f"""
            You are an expert email drafter.
            
            CONTEXT HISTORY:
            {history_str}
            
            CURRENT DRAFT:
            {current_draft}
            
            LATEST USER ANSWER: "{user_input}"
            QUESTIONS ASKED SO FAR: {question_count}
            
            Task:
            1. Integrate the Latest User Answer into the draft naturally.
            2. Check for remaining gaps or improvements needed.
            3. Formulate the NEXT question to further refine the email.
            4. CRITICAL RULES:
               - DO NOT ask a question that is already answered in CONTEXT HISTORY
               - Ask questions about: tone/formality, specific details, recipient details, action items, urgency, closing style, etc.
               - Keep questions specific and actionable
            5. Set status to "CONTINUE" if there are more questions to ask OR if user's answer was brief/incomplete
            6. Set status to "COMPLETE" only if the email feels complete, personalized, and ready
            
            Output JSON ONLY:
            {{ "draft": "...", "question": "Next specific question", "status": "CONTINUE" or "COMPLETE" }}
        """)

    try:
        response = llm.complete(system_prompt).text.strip()
        if response.startswith("```"):
            response = response.strip("`").replace("json", "").strip()
        result = json.loads(response)
        
        # For first turn, ensure we always continue
        if is_first_turn:
            result["status"] = "CONTINUE"
            
        return result
    except Exception:
        return {"draft": current_draft, "question": None, "status": "COMPLETE"}


def handle_email_intent(user_prompt: str):
    """
    Main Email Workflow with Intelligent Iterative Drafting.
    Flow:
    1. Get recipient(s)
    2. Generate initial draft
    3. Ask up to 4 clarifying questions to refine draft
    4. Show final draft
    5. Allow improvements before sending
    6. Send when confirmed
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

    # ===== PHASE 1: GENERATE INITIAL DRAFT =====
    console.print(f"\n[bold cyan]📧 Drafting your email...[/bold cyan]\n")
    
    with console.status("[cyan]Generating initial draft...[/cyan]"):
        current_draft, next_question = generate_initial_draft(user_prompt, key, model)
    
    question_count = 0
    question_history = [f"User Request: {user_prompt}"]

    # ===== PHASE 2: ITERATIVE CLARIFYING QUESTIONS (Max 4) =====
    while question_count < MAX_CLARIFYING_QUESTIONS and next_question:
        question_count += 1
        
        # Show current draft
        subject, body = extract_subject_and_body(current_draft)
        console.print(Panel(
            f"[bold]To:[/bold] {recipients_display}\n[bold]Subject:[/bold] {subject}\n\n{body}",
            title=f"📝 Draft (Question {question_count}/{MAX_CLARIFYING_QUESTIONS})",
            style="dim blue"
        ))
        
        # Ask clarifying question
        console.print(f"\n[bold cyan]Question {question_count}/{MAX_CLARIFYING_QUESTIONS}:[/bold cyan]")
        user_answer = questionary.text(next_question).ask()
        
        if not user_answer or user_answer.lower() in ["skip", "done", "no"]:
            break
        
        question_history.append(f"AI Question: {next_question}")
        question_history.append(f"User Answer: {user_answer}")
        
        # Refine draft based on answer
        with console.status("[cyan]Refining draft...[/cyan]"):
            current_draft, next_question = refine_draft(
                current_draft, 
                user_answer, 
                question_history, 
                key, 
                model, 
                question_count
            )

    # ===== PHASE 3: FINAL REVIEW & IMPROVEMENT LOOP =====
    while True:
        subject, body = extract_subject_and_body(current_draft)
        
        console.print("\n" + "="*80)
        console.print(Panel(
            f"[bold]To:[/bold] {recipients_display}\n[bold]Subject:[/bold] {subject}\n\n{body}",
            title="✅ Final Email Draft",
            border_style="green"
        ))
        
        action = questionary.select(
            "\nWhat would you like to do?",
            choices=[
                questionary.Choice("🚀 Send Email Now", value="send"),
                questionary.Choice("✨ Request Improvements", value="improve"),
                questionary.Choice("📝 Manually Edit Body", value="edit_body"),
                questionary.Choice("✏️ Edit Subject", value="edit_subject"),
                questionary.Choice("❌ Cancel & Discard", value="cancel"),
            ]
        ).ask()

        if action == "send":
            # Final confirmation
            confirm_send = questionary.confirm(
                "\n🔒 Are you sure you want to send this email?",
                default=True
            ).ask()
            
            if confirm_send:
                with console.status("[cyan]Sending email...[/cyan]"):
                    send_email_via_smtp(recipient_list, subject, body, config)
                console.print(f"\n[green]✔ Email sent to {len(recipient_list)} recipient(s)![/green]")
                break
            # If not confirmed, stay in review loop
            
        elif action == "improve":
            improvement_request = questionary.text(
                "\n✨ What improvements would you like?\n(e.g., 'make it more formal', 'add humor', 'shorten it', 'emphasize urgency')"
            ).ask()
            
            if improvement_request:
                with console.status("[cyan]Applying improvements...[/cyan]"):
                    current_draft = apply_improvements(current_draft, improvement_request, key, model)
                
                console.print("[green]✔ Draft updated![/green]")
                # Loop back to show updated draft
                continue
            
        elif action == "edit_body":
            body = questionary.text(
                "Edit email body:",
                default=body,
                multiline=True
            ).ask()
            current_draft = f"Subject: {subject}\n\n{body}"
            
        elif action == "edit_subject":
            subject = questionary.text(
                "Edit subject line:",
                default=subject
            ).ask()
            current_draft = f"Subject: {subject}\n\n{body}"
            
        else:  # cancel
            console.print("[yellow]Email discarded. Goodbye![/yellow]")
            break