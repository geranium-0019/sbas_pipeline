"""Step 03: Download DEM data."""

import json
import logging
import math
from pathlib import Path
from typing import Any, Dict

from lib.context import Context
from lib.utils import run_cmd


def step_03_download_dem(cfg: Dict[str, Any], ctx: Context, logger: logging.Logger) -> Dict[str, Any]:
    """
    ③ sbas_pairs.jsonからselected_bboxを読み込み、DEMをダウンロードする
    """
    logger.info("Step 03: Download DEM")

    # Step 02 (tools/s1_sbas_download.py) writes sbas_pairs.json to: <project_dir>/.state/sbas_pairs.json
    sbas_pairs_path = ctx.state_dir / "sbas_pairs.json"
    if not sbas_pairs_path.exists():
        msg = (
            "sbas_pairs.json not found. Expected at: "
            f"{sbas_pairs_path}. Please run step 02 first."
        )
        logger.error(msg)
        raise FileNotFoundError(msg)

    with sbas_pairs_path.open("r", encoding="utf-8") as f:
        sbas_pairs = json.load(f)

    bbox = sbas_pairs.get("selected_bbox")
    if not bbox:
        raise ValueError("`selected_bbox` not found in sbas_pairs.json")

    # dem.pyのbbox形式（南、北、西、東）に変換し、整数に丸める
    # MintPy bbox: min_lon, min_lat, max_lon, max_lat
    # dem.py -b: S N W E (min_lat max_lat min_lon max_lon)
    min_lat = math.floor(bbox[1])
    max_lat = math.ceil(bbox[3])
    min_lon = math.floor(bbox[0])
    max_lon = math.ceil(bbox[2])

    dem_url = cfg.get("dem", {}).get("url", "https://step.esa.int/auxdata/dem/SRTMGL1/")

    cmd = [
        "dem.py", "-a", "stitch",
        "-b", str(min_lat), str(max_lat), str(min_lon), str(max_lon),
        "-r", "-s", "1", "-c", "-f",
        "-d", str(ctx.dem_dir),
        "-u", dem_url,
    ]
    
    run_cmd(cmd, cwd=ctx.project_dir, dry_run=ctx.dry_run, logger=logger)

    return {"dem_dir": str(ctx.dem_dir), "bbox": [min_lat, max_lat, min_lon, max_lon]}
