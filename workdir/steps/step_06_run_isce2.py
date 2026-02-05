"""Step 06: Run ISCE2 stack processing.

This step executes the generated run scripts under:
    <project_dir>/isce2/run_files/run_*
in sorted order.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List
import re

from lib.context import Context
from lib.utils import ensure_dir
from lib.utils import run_cmd


def _patch_multilook_tool_isce(config_path: Path, *, logger: logging.Logger) -> bool:
    """Ensure `multilook_tool` is set to `isce` in a config_merge_* file.

    Returns True if the file was modified.
    """
    if not config_path.exists():
        logger.warning(f"Config not found (skip): {config_path}")
        return False

    text = config_path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)

    # Match e.g.: "multilook_tool : gdal" / "multilook_tool: gdal" / extra spaces.
    pat = re.compile(r"^(\s*multilook_tool\s*:\s*)(\S+)(\s*)$", re.IGNORECASE)
    changed = False
    for i, line in enumerate(lines):
        m = pat.match(line.rstrip("\n"))
        if not m:
            continue
        prefix, value, suffix = m.group(1), m.group(2), m.group(3)
        if value.lower() == "isce":
            return False
        lines[i] = f"{prefix}isce{suffix}\n"
        changed = True
        break

    if changed:
        config_path.write_text("".join(lines), encoding="utf-8")
        logger.info(f"Patched multilook_tool to isce: {config_path.name}")
        return True

    logger.info(f"No multilook_tool line found: {config_path.name}")
    return False


def _prepatch_isce_merge_configs(ctx: Context, logger: logging.Logger) -> Dict[str, Any]:
    """Patch known merge config files before running ISCE2 scripts."""
    configs_dir = ctx.isce2_dir / "configs"
    targets = [
        "config_merge_hgt",
        "config_merge_incLocal",
        "config_merge_lat",
        "config_merge_lon",
        "config_merge_los",
    ]

    modified: List[str] = []
    for name in targets:
        p = configs_dir / name
        if _patch_multilook_tool_isce(p, logger=logger):
            modified.append(str(p))

    return {"patched_merge_configs": modified, "patched_count": len(modified)}


def _list_run_scripts(run_dir: Path) -> List[Path]:
        scripts = sorted([p for p in run_dir.glob("run_*") if p.is_file()])
        return scripts


def step_06_run_isce2(cfg: Dict[str, Any], ctx: Context, logger: logging.Logger) -> Dict[str, Any]:
    """
    ⑥ ISCE2 を実行

    step_05 により <isce2_dir>/run_files に生成された run_* を順番に実行する。
    """
    logger.info("Step 06: run ISCE2 stack (run_files)")

    # Before running, patch merge configs to use ISCE multilook (not GDAL).
    prepatch = _prepatch_isce_merge_configs(ctx, logger)

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
        **prepatch,
    }
