# helpers/usage_tracker.py
"""
Tracks API usage (calls, tokens, estimated cost) across all AI Shell operations.
Data is stored in ~/.ai_shell_usage.json.
"""
import json
import os
from pathlib import Path
from datetime import datetime, date

USAGE_FILE = Path.home() / ".ai_shell_usage.json"

# Approximate pricing per million tokens (Google Gemini, as of 2025)
MODEL_PRICING = {
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    "gemini-2.0-flash-lite": {"input": 0.075, "output": 0.30},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    "gemini-2.0-pro": {"input": 1.25, "output": 5.00},
    "gemini-2.5-pro": {"input": 1.25, "output": 10.00},
    "gemini-2.5-flash": {"input": 0.15, "output": 0.60},
}

# Fallback pricing if model isn't in the table
DEFAULT_PRICING = {"input": 0.15, "output": 0.60}


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 characters per token for English text."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def track_usage(model: str, input_text: str, output_text: str):
    """
    Records an API call with estimated token usage and cost.
    Fails silently on any I/O error to avoid breaking the main workflow.
    """
    try:
        input_tokens = estimate_tokens(input_text)
        output_tokens = estimate_tokens(output_text)

        pricing = MODEL_PRICING.get(model, DEFAULT_PRICING)
        cost = (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000

        entry = {
            "timestamp": datetime.now().isoformat(),
            "date": date.today().isoformat(),
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "estimated_cost_usd": round(cost, 8),
        }

        data = _load_usage()
        data["calls"].append(entry)
        data["total_calls"] += 1
        data["total_input_tokens"] += input_tokens
        data["total_output_tokens"] += output_tokens
        data["total_estimated_cost_usd"] = round(
            data["total_estimated_cost_usd"] + cost, 8
        )

        with open(USAGE_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        # Never break the user's workflow because of tracking failures
        pass


def _load_usage() -> dict:
    """Loads the usage data file, returning a default structure if missing or corrupt."""
    if USAGE_FILE.exists():
        try:
            with open(USAGE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return _empty_usage()


def _empty_usage() -> dict:
    return {
        "calls": [],
        "total_calls": 0,
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "total_estimated_cost_usd": 0.0,
    }


def get_usage_summary() -> dict:
    """Returns usage stats aggregated by today and all-time."""
    data = _load_usage()

    today_str = date.today().isoformat()
    today_calls = [c for c in data["calls"] if c.get("date") == today_str]
    today_input = sum(c.get("input_tokens", 0) for c in today_calls)
    today_output = sum(c.get("output_tokens", 0) for c in today_calls)
    today_cost = sum(c.get("estimated_cost_usd", 0) for c in today_calls)

    return {
        "today": {
            "calls": len(today_calls),
            "input_tokens": today_input,
            "output_tokens": today_output,
            "estimated_cost_usd": round(today_cost, 6),
        },
        "all_time": {
            "calls": data.get("total_calls", 0),
            "input_tokens": data.get("total_input_tokens", 0),
            "output_tokens": data.get("total_output_tokens", 0),
            "estimated_cost_usd": data.get("total_estimated_cost_usd", 0.0),
        },
    }


def reset_usage():
    """Resets all usage data."""
    try:
        with open(USAGE_FILE, "w") as f:
            json.dump(_empty_usage(), f, indent=2)
    except Exception:
        pass
