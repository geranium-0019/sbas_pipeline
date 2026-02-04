"""Step 06: Run ISCE2 stack processing.

This step executes the generated run scripts under:
    <project_dir>/isce2/run_files/run_*
in sorted order.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List

from lib.context import Context
from lib.utils import ensure_dir
from lib.utils import run_cmd


def _list_run_scripts(run_dir: Path) -> List[Path]:
        scripts = sorted([p for p in run_dir.glob("run_*") if p.is_file()])
        return scripts


def step_06_run_isce2(cfg: Dict[str, Any], ctx: Context, logger: logging.Logger) -> Dict[str, Any]:
    """
    ⑥ ISCE2 を実行

    step_05 により <isce2_dir>/run_files に生成された run_* を順番に実行する。
    """
    logger.info("Step 06: run ISCE2 stack (run_files)")

    run_dir = ctx.isce2_dir / "run_files"
    if not run_dir.exists():
        raise FileNotFoundError(
            f"run_files directory not found: {run_dir}. Run step 05 (stackSentinel) first."
        )

    scripts = _list_run_scripts(run_dir)
    if not scripts:
        raise FileNotFoundError(f"No run_* scripts found under: {run_dir}")

    # Optional: keep logs under isce2/logs/<timestamp>/
    # (stackSentinel itself writes lots of logs; this is just a top-level runner log.)
    logs_dir = ctx.isce2_dir / "logs"
    ensure_dir(logs_dir)

    logger.info(f"  run_files: {run_dir}")
    logger.info(f"  scripts : {len(scripts)}")

    ran: List[str] = []
    for i, script in enumerate(scripts, 1):
        logger.info(f"  [{i}/{len(scripts)}] {script.name}")
        run_cmd(["bash", str(script)], cwd=ctx.isce2_dir, dry_run=ctx.dry_run, logger=logger)
        ran.append(str(script))

    return {
        "ran": True,
        "run_dir": str(run_dir),
        "count": len(ran),
        "scripts": ran,
        "dry_run": bool(ctx.dry_run),
    }
