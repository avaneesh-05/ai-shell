# helpers/tracked_llm.py
"""
TrackedLLM — a thin wrapper around the GoogleGenAI LLM that automatically
records every API call (tokens, estimated cost) via usage_tracker.

Drop-in replacement: wherever you use `GoogleGenAI`, use `TrackedLLM` instead.
All calls to `.complete()`, `.stream_chat()`, and `.chat()` are tracked.
"""
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.core.llms import ChatMessage, CompletionResponse, ChatResponse
from typing import Sequence, Generator, Any

from .usage_tracker import track_usage


class TrackedLLM:
    """
    Wraps a GoogleGenAI instance and transparently tracks API usage
    for every call to complete(), chat(), and stream_chat().
    """

    def __init__(self, model: str, api_key: str):
        self._model_name = model
        self._llm = GoogleGenAI(model=model, api_key=api_key)

    # ── complete() ──────────────────────────────────────────────────────
    def complete(self, prompt: str, **kwargs) -> CompletionResponse:
        """Calls the underlying LLM's complete() and tracks usage."""
        response = self._llm.complete(prompt, **kwargs)
        track_usage(
            model=self._model_name,
            input_text=prompt,
            output_text=response.text or "",
        )
        return response

    # ── chat() ──────────────────────────────────────────────────────────
    def chat(self, messages: Sequence[ChatMessage], **kwargs) -> ChatResponse:
        """Calls the underlying LLM's chat() and tracks usage."""
        response = self._llm.chat(messages, **kwargs)
        input_text = " ".join(m.content or "" for m in messages)
        output_text = response.message.content or "" if response.message else ""
        track_usage(
            model=self._model_name,
            input_text=input_text,
            output_text=output_text,
        )
        return response

    # ── stream_chat() ───────────────────────────────────────────────────
    def stream_chat(
        self, messages: Sequence[ChatMessage], **kwargs
    ) -> Generator[Any, None, None]:
        """
        Wraps the underlying stream_chat() generator.
        Collects all delta chunks and records usage when the stream is exhausted.
        """
        input_text = " ".join(m.content or "" for m in messages)
        collected_output = []

        for chunk in self._llm.stream_chat(messages, **kwargs):
            collected_output.append(chunk.delta or "")
            yield chunk

        # Stream finished — record the aggregated output
        track_usage(
            model=self._model_name,
            input_text=input_text,
            output_text="".join(collected_output),
        )

    # ── Proxy everything else to the underlying LLM ─────────────────────
    def __getattr__(self, name):
        """Forward any other attribute access to the wrapped LLM."""
        return getattr(self._llm, name)
