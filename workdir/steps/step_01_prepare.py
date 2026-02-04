"""Step 01: Prepare project directories."""

import logging
from typing import Any, Dict

import yaml

from lib.context import Context
from lib.utils import ensure_dir


def step_01_prepare(cfg: Dict[str, Any], ctx: Context, logger: logging.Logger) -> Dict[str, Any]:
    """
    ① 環境パスの設定とディレクトリ構成の設定
    - ここでは project のディレクトリを作るだけ（パスは env.sh で source する前提）
    """
    logger.info("Preparing project directories...")
    for d in [
        ctx.project_dir,
        ctx.logs_dir,
        ctx.state_dir,
        ctx.data_dir,
        ctx.s1_slc_dir,
        ctx.dem_dir,
        ctx.orbit_dir,
        ctx.aux_dir,
        ctx.isce2_dir,
        ctx.mintpy_dir,
        ctx.mintpy_run_dir,
    ]:
        ensure_dir(d)

    # Save a resolved snapshot of config for reproducibility
    ensure_dir(ctx.project_dir)
    resolved_cfg_path = ctx.project_dir / "config.resolved.yaml"
    with resolved_cfg_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, sort_keys=False, allow_unicode=True)

    return {"created_dirs": True, "resolved_config": str(resolved_cfg_path)}
