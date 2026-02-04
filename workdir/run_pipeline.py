#!/usr/bin/env python3
"""ISCE2 + MintPy SBAS pipeline orchestrator."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml  # pip install pyyaml
except ImportError as e:
    print("[ERROR] Missing dependency: pyyaml. Install with: pip install pyyaml", file=sys.stderr)
    raise

from lib.context import Context, build_context
from lib.logger import setup_logger
from lib.state import is_step_done, mark_step_done
from lib.utils import load_yaml, ensure_dir
from steps import Step
from steps.step_01_prepare import step_01_prepare
from steps.step_02_download_s1 import step_02_download_s1
from steps.step_03_download_dem import step_03_download_dem
from steps.step_04_download_orbits import step_04_download_orbits
from steps.step_05_config_stack import step_05_config_stack
from steps.step_06_run_isce2 import step_06_run_isce2
from steps.step_07_run_mintpy import step_07_run_mintpy


def normalize_step_id(value: str) -> str:
    """Normalize CLI step selector values to canonical step ids.

    Accepts either a step id (e.g. "04_download_orbits") or a filename
    (e.g. "step_04_download_orbits.py").
    """
    v = (value or "").strip()
    if not v:
        return v

    # Allow passing a python filename
    if v.endswith(".py"):
        v = Path(v).name[:-3]

    # Allow passing module filename prefix
    if v.startswith("step_"):
        v = v[len("step_") :]

    return v


def steps_def() -> List[Step]:
    """Define all pipeline steps in order."""
    return [
        Step("01_prepare", "Prepare directories & snapshot config", step_01_prepare),
        Step("02_download_s1", "Download Sentinel-1 SLC", step_02_download_s1),
        Step("03_download_dem", "Download DEM", step_03_download_dem),
        Step("04_download_orbits", "Download precise orbits", step_04_download_orbits),
        Step("05_config_stack", "Configure stackSentinel", step_05_config_stack),
        Step("06_run_isce2", "Run ISCE2 stack", step_06_run_isce2),
        Step("07_run_mintpy", "Run MintPy", step_07_run_mintpy),
    ]


def select_steps(all_steps: List[Step], ctx: Context) -> List[Step]:
    """Select steps to run based on context options."""
    ids = [s.id for s in all_steps]

    # --only-steps has priority
    if ctx.only_steps:
        wanted = []
        for raw in ctx.only_steps:
            sid = normalize_step_id(raw)
            if sid not in ids:
                raise ValueError(
                    f"Unknown step id in --only-steps: {raw} (normalized: {sid}). Valid: {ids}"
                )
            wanted.append(all_steps[ids.index(sid)])
        return wanted

    # from/until slicing
    start_idx = 0
    end_idx = len(all_steps) - 1
    if ctx.from_step:
        raw = ctx.from_step
        sid = normalize_step_id(raw)
        if sid not in ids:
            raise ValueError(f"Unknown --from-step: {raw} (normalized: {sid}). Valid: {ids}")
        start_idx = ids.index(sid)
    if ctx.until_step:
        raw = ctx.until_step
        sid = normalize_step_id(raw)
        if sid not in ids:
            raise ValueError(f"Unknown --until-step: {raw} (normalized: {sid}). Valid: {ids}")
        end_idx = ids.index(sid)

    if start_idx > end_idx:
        raise ValueError("--from-step is after --until-step")

    return all_steps[start_idx : end_idx + 1]


def run_pipeline(cfg: Dict[str, Any], ctx: Context, logger: logging.Logger) -> None:
    """Execute the pipeline with selected steps."""
    all_steps = steps_def()
    selected = select_steps(all_steps, ctx)

    logger.info("========================================")
    logger.info("Pipeline start")
    logger.info(f"Project: {ctx.project_dir}")
    logger.info(f"Config : {ctx.config_path}")
    logger.info(f"Dry-run: {ctx.dry_run}")
    logger.info(f"Force  : {ctx.force}")
    logger.info("Steps  : " + ", ".join([s.id for s in selected]))
    logger.info("========================================")

    for i, step in enumerate(selected, start=1):
        done = is_step_done(ctx, step.id)
        if done and not ctx.force:
            logger.info(f"[{i}/{len(selected)}] {step.id} SKIP (already done)")
            continue

        logger.info(f"[{i}/{len(selected)}] {step.id} START - {step.title}")
        ensure_dir(ctx.state_dir)

        payload = step.fn(cfg, ctx, logger) or {}
        mark_step_done(ctx, step.id, payload)

        logger.info(f"[{i}/{len(selected)}] {step.id} DONE")

    logger.info("========================================")
    logger.info("Pipeline finished")
    logger.info("========================================")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    p = argparse.ArgumentParser(description="ISCE2 + MintPy SBAS pipeline orchestrator")
    p.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    p.add_argument("--dry-run", action="store_true", help="Print commands without executing")
    p.add_argument("--force", action="store_true", help="Run steps even if marked done")

    p.add_argument(
        "--only-steps",
        nargs="+",
        help=(
            "Run only specified step ids (e.g., 02_download_s1 03_download_dem) "
            "or step filenames (e.g., step_04_download_orbits.py)"
        ),
    )
    p.add_argument(
        "--from-step",
        help="Start from this step id (e.g., 04_download_orbits) or filename (step_04_download_orbits.py)",
    )
    p.add_argument(
        "--until-step",
        help="Stop after this step id (e.g., 04_download_orbits) or filename (step_04_download_orbits.py)",
    )

    return p.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()
    config_path = Path(args.config).expanduser().resolve()
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")

    cfg = load_yaml(config_path)
    ctx = build_context(cfg, config_path, args)
    logger = setup_logger(ctx.logs_dir)

    # Basic validation (minimal; extend later)
    required = ["project_dir"]
    missing = [k for k in required if k not in cfg or not cfg.get(k)]
    if missing:
        raise ValueError(f"Missing required config keys: {missing}")

    run_pipeline(cfg, ctx, logger)


if __name__ == "__main__":
    main()
