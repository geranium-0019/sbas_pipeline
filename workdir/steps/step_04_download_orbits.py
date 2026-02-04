"""Step 04: Download precise orbits."""

import logging
from pathlib import Path
from typing import Any, Dict

from lib.context import Context
from lib.utils import ensure_dir, run_cmd


def step_04_download_orbits(cfg: Dict[str, Any], ctx: Context, logger: logging.Logger) -> Dict[str, Any]:
    """
    ④ dloadOrbits.py を使用してOrbitをダウンロード
    """
    logger.info("Step 04: Download precise orbits")
    
    # Get date range from config
    date_start = cfg.get("date_start", "")
    date_end = cfg.get("date_end", "")
    
    if not date_start or not date_end:
        logger.warning("  date_start or date_end not set in config; skipping orbit download")
        return {
            "orbits_downloaded": False,
            "reason": "date_start or date_end not set",
            "orbit_dir": str(ctx.orbit_dir),
        }
    
    # Ensure orbit directory exists
    ensure_dir(ctx.orbit_dir)
    
    # Find dloadOrbits.py
    dload_orbits_path = Path(__file__).parent.parent / "tools" / "dloadOrbits.py"
    if not dload_orbits_path.exists():
        logger.error(f"  dloadOrbits.py not found at {dload_orbits_path}")
        raise FileNotFoundError(f"dloadOrbits.py not found at {dload_orbits_path}")
    
    logger.info(f"  Using dloadOrbits from: {dload_orbits_path}")
    
    # Build command
    cmd = [
        "python", str(dload_orbits_path),
        "--start", date_start,
        "--end", date_end,
        "--dir", str(ctx.orbit_dir),
    ]
    
    logger.info(f"  Downloading orbits for {date_start} to {date_end}")
    
    try:
        run_cmd(cmd, dry_run=ctx.dry_run, logger=logger)
        logger.info("  Orbit download complete")
        return {
            "orbits_downloaded": True,
            "date_start": date_start,
            "date_end": date_end,
            "orbit_dir": str(ctx.orbit_dir),
        }
    except Exception as e:
        logger.error(f"  Failed to download orbits: {e}")
        raise
