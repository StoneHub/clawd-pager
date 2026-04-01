#!/usr/bin/env python3
"""
OpenClaw Usage Calculator
Parses OpenClaw session JSONL files and calculates token usage and costs.
"""

import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from collections import defaultdict

# Model pricing (per 1M tokens)
MODEL_PRICING = {
    # Anthropic Claude
    "claude-sonnet-4-5": {"input": 3.0, "output": 15.0},
    "claude-sonnet-4": {"input": 3.0, "output": 15.0},
    "claude-opus-4-6": {"input": 15.0, "output": 75.0},
    "claude-opus-4": {"input": 15.0, "output": 75.0},
    "claude-haiku": {"input": 0.25, "output": 1.25},
    
    # Google Gemini (free tier)
    "gemini-3-flash-preview": {"input": 0.0, "output": 0.0},
    "gemini-2.0-flash-exp": {"input": 0.0, "output": 0.0},
    
    # OpenAI
    "gpt-4o": {"input": 2.5, "output": 10.0},
    "gpt-4-turbo": {"input": 10.0, "output": 30.0},
    "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
    
    # Default fallback
    "default": {"input": 1.0, "output": 5.0},
}


def get_model_pricing(model_id: str) -> Dict[str, float]:
    """Get pricing for a model, with fallback."""
    # Try exact match
    if model_id in MODEL_PRICING:
        return MODEL_PRICING[model_id]
    
    # Try partial match (e.g., "claude-sonnet-4-5" matches "claude-sonnet")
    for key, pricing in MODEL_PRICING.items():
        if key in model_id or model_id in key:
            return pricing
    
    # Default pricing
    return MODEL_PRICING["default"]


def calculate_cost(model_id: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost for a model's token usage."""
    pricing = get_model_pricing(model_id)
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return input_cost + output_cost


def parse_session_file(file_path: Path) -> List[Dict]:
    """Parse a session JSONL file and extract usage data."""
    usage_records = []
    
    try:
        with open(file_path, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    
                    # Look for message entries with usage data
                    if entry.get("type") == "message" and "message" in entry:
                        msg = entry["message"]
                        if "usage" in msg and msg["usage"]:
                            usage = msg["usage"]
                            
                            # Extract data
                            timestamp = entry.get("timestamp", "")
                            model = msg.get("model", "unknown")
                            input_tokens = usage.get("input", 0)
                            output_tokens = usage.get("output", 0)
                            cache_read = usage.get("cacheRead", 0)
                            cache_write = usage.get("cacheWrite", 0)
                            
                            # Calculate cost (use provided cost if available, otherwise calculate)
                            if "cost" in usage and usage["cost"].get("total", 0) > 0:
                                cost = usage["cost"]["total"]
                            else:
                                cost = calculate_cost(model, input_tokens, output_tokens)
                            
                            usage_records.append({
                                "timestamp": timestamp,
                                "model": model,
                                "input_tokens": input_tokens,
                                "output_tokens": output_tokens,
                                "cache_read": cache_read,
                                "cache_write": cache_write,
                                "cost": cost,
                            })
                            
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    # Skip malformed entries
                    continue
                    
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    
    return usage_records


def get_monthly_usage(months_back: int = 4) -> Dict:
    """
    Calculate monthly token usage from OpenClaw session files.
    
    Args:
        months_back: Number of historical months to include
    
    Returns:
        Dict with current_month, historical, and by_model breakdowns
    """
    openclaw_dir = Path.home() / ".openclaw" / "agents"
    
    if not openclaw_dir.exists():
        return {
            "current_month": {
                "month": datetime.now().strftime("%Y-%m"),
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_tokens": 0,
                "cost": 0.0,
            },
            "historical": [],
            "by_model": {},
        }
    
    # Find all session files
    session_files = []
    for agent_dir in openclaw_dir.iterdir():
        if agent_dir.is_dir():
            sessions_dir = agent_dir / "sessions"
            if sessions_dir.exists():
                session_files.extend(sessions_dir.glob("*.jsonl"))
    
    # Parse all sessions
    all_usage = []
    for session_file in session_files:
        all_usage.extend(parse_session_file(session_file))
    
    # Organize by month
    monthly_data = defaultdict(lambda: {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_tokens": 0,
        "cost": 0.0,
    })
    
    model_data = defaultdict(lambda: {
        "tokens": 0,
        "cost": 0.0,
    })
    
    # Current month model data (FIXED: was accumulating all-time data)
    current_month_str = datetime.now().strftime("%Y-%m")
    current_month_model_data = defaultdict(lambda: {
        "tokens": 0,
        "cost": 0.0,
    })
    
    for record in all_usage:
        try:
            dt = datetime.fromisoformat(record["timestamp"].replace("Z", "+00:00"))
            month = dt.strftime("%Y-%m")
            
            monthly_data[month]["input_tokens"] += record["input_tokens"]
            monthly_data[month]["output_tokens"] += record["output_tokens"]
            monthly_data[month]["cache_tokens"] += record["cache_read"] + record["cache_write"]
            monthly_data[month]["cost"] += record["cost"]
            
            # By-model breakdown (all-time)
            model = record["model"]
            model_data[model]["tokens"] += record["input_tokens"] + record["output_tokens"]
            model_data[model]["cost"] += record["cost"]
            
            # Current month by-model breakdown (FIXED)
            if month == current_month_str:
                current_month_model_data[model]["tokens"] += record["input_tokens"] + record["output_tokens"]
                current_month_model_data[model]["cost"] += record["cost"]
            
        except Exception as e:
            continue
    
    # Build response
    current_month = datetime.now().strftime("%Y-%m")
    
    # Get historical months (FIXED: include all months, even with 0 data)
    historical = []
    for i in range(months_back, 0, -1):
        month_date = datetime.now() - timedelta(days=30 * i)
        month = month_date.strftime("%Y-%m")
        
        # Include month even if no data (fixes empty chart issue)
        data = monthly_data.get(month, {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_tokens": 0,
            "cost": 0.0,
        })
        historical.append({
            "month": month,
            **data
        })
    
    # Current month data
    current_data = monthly_data.get(current_month, {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_tokens": 0,
        "cost": 0.0,
    })
    
    # FIXED: Sort by_model by cost descending
    sorted_models = sorted(
        current_month_model_data.items(), 
        key=lambda x: x[1]["cost"], 
        reverse=True
    )
    
    return {
        "current_month": {
            "month": current_month,
            **current_data
        },
        "historical": historical,
        # FIXED: Use current month data only, sorted by cost
        "by_model": {k: dict(v) for k, v in sorted_models if v["tokens"] > 0},
    }


def main():
    """CLI tool for testing."""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--json":
        # Output JSON
        usage = get_monthly_usage()
        print(json.dumps(usage, indent=2))
    else:
        # Human-readable output
        usage = get_monthly_usage()
        
        print("OpenClaw Token Usage Report")
        print("=" * 60)
        print()
        
        current = usage["current_month"]
        print(f"Current Month: {current['month']}")
        print(f"  Input tokens:  {current['input_tokens']:,}")
        print(f"  Output tokens: {current['output_tokens']:,}")
        print(f"  Cache tokens:  {current['cache_tokens']:,}")
        print(f"  Cost:          ${current['cost']:.2f}")
        print()
        
        if usage["historical"]:
            print("Historical (last 3 months):")
            for hist in usage["historical"][-3:]:
                print(f"  {hist['month']}: {hist['input_tokens']:,} in / {hist['output_tokens']:,} out = ${hist['cost']:.2f}")
            print()
        
        if usage["by_model"]:
            print("By Model:")
            for model, data in sorted(usage["by_model"].items(), key=lambda x: x[1]["cost"], reverse=True):
                print(f"  {model:30s}: {data['tokens']:>10,} tokens = ${data['cost']:>6.2f}")


if __name__ == "__main__":
    main()
