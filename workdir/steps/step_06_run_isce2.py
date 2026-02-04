"""Step 06: Run ISCE2 stack processing."""

import logging
from typing import Any, Dict

from lib.context import Context
from lib.utils import run_cmd


def step_06_run_isce2(cfg: Dict[str, Any], ctx: Context, logger: logging.Logger) -> Dict[str, Any]:
    """
    ⑥ ISCE2 を実行
    - step_05で組んだ stackSentinel.py をここで実行するのが自然
    """
    logger.info("Step 06: run ISCE2 stack (stub).")

    # Placeholder: actually run stackSentinel
    # cmd = ... (build from cfg and ctx)
    cmd = ["echo", "ISCE2 would run here"]

    run_cmd(cmd, cwd=ctx.isce2_dir, dry_run=ctx.dry_run, logger=logger)
    return {"note": "not implemented", "ran": True}
