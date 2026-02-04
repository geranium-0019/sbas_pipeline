"""Step 07: Run MintPy processing."""

import logging
from typing import Any, Dict

from lib.context import Context
from lib.utils import run_cmd


def step_07_run_mintpy(cfg: Dict[str, Any], ctx: Context, logger: logging.Logger) -> Dict[str, Any]:
    """
    ⑦ MintPy を実行
    - smallbaselineApp.cfg を自動生成して smallbaselineApp.py を呼ぶ
    """
    logger.info("Step 07: run MintPy (stub).")

    # Placeholder:
    # cfg_path = ctx.mintpy_dir / "smallbaselineApp.cfg"
    # generate_smallbaseline_cfg(...)
    # run_cmd(["smallbaselineApp.py", str(cfg_path)], cwd=ctx.mintpy_run_dir, ...)

    run_cmd(["echo", "MintPy would run here"], cwd=ctx.mintpy_run_dir, dry_run=ctx.dry_run, logger=logger)
    return {"note": "not implemented", "ran": True}
