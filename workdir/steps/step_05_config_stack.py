"""Step 05: Configure stackSentinel parameters."""

import logging
from typing import Any, Dict

from lib.context import Context
from lib.utils import ensure_dir, utc_now_iso


def step_05_config_stack(cfg: Dict[str, Any], ctx: Context, logger: logging.Logger) -> Dict[str, Any]:
    """
    ⑤ stackSentinel.py のパラメータ設定
    """
    logger.info("Step 05: build stackSentinel command")

    ensure_dir(ctx.isce2_dir)
    
    # Example: build command list
    cmd = [
        "stackSentinel.py",
        "-s", str(ctx.s1_slc_dir),
        "-o", str(ctx.orbit_dir),
        "-d", str(ctx.dem_dir),
        "-w", str(ctx.isce2_dir),
    ]

    commands_log = ctx.isce2_dir / "commands.log"
    ensure_dir(commands_log.parent)
    with commands_log.open("a", encoding="utf-8") as f:
        f.write(f"[{utc_now_iso()}] {' '.join(cmd)}\n")

    return {
        "command": " ".join(cmd),
        "isce2_work_dir": str(ctx.isce2_dir),
        "commands_log": str(commands_log),
    }

