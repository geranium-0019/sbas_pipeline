"""State management for pipeline steps."""

from pathlib import Path
from typing import Any, Dict, Optional

from lib.context import Context
from lib.utils import dump_json, read_json, utc_now_iso


def state_path(ctx: Context, step_id: str) -> Path:
    """Get the state file path for a step."""
    return ctx.state_dir / f"{step_id}.json"


def is_step_done(ctx: Context, step_id: str) -> bool:
    """Check if a step has been completed."""
    p = state_path(ctx, step_id)
    if not p.exists():
        return False
    obj = read_json(p)
    return obj.get("done", False) is True


def mark_step_done(ctx: Context, step_id: str, payload: Optional[Dict[str, Any]] = None) -> None:
    """Mark a step as completed and save payload."""
    obj = {
        "done": True,
        "step": step_id,
        "timestamp": utc_now_iso(),
        "payload": payload or {},
    }
    dump_json(state_path(ctx, step_id), obj)
