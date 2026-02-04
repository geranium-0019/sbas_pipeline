"""Step 02: Download Sentinel-1 SLC data and build SBAS network."""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict

from lib.context import Context
from lib.utils import ensure_dir, utc_now_iso

# Import the main function from tools
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
try:
    from s1_sbas_download import sbas_select_and_download
except ImportError as e:
    raise ImportError(f"Failed to import s1_sbas_download from tools: {e}")


def step_02_download_s1(cfg: Dict[str, Any], ctx: Context, logger: logging.Logger) -> Dict[str, Any]:
    """
    ② ユーザーが設定したパラメータからSBASに使うs1画像を自動ダウンロード
    - ASF検索 → SBAS対構築 → DL
    """
    logger.info("Step 02: Download Sentinel-1 SLC and build SBAS network")
    
    # Ensure data directory exists
    ensure_dir(ctx.data_dir)
    
    # Call the main sbas_select_and_download function from tools
    # This handles:
    #   1) ASF search
    #   2) Scene grouping
    #   3) SBAS pair building
    #   4) Scene selection (only pairs are downloaded)
    #   5) Download
    #   6) Write .state/sbas_pairs.json
    try:
        result = sbas_select_and_download(
            cfg,
            ctx.project_dir,
            netrc_path=Path.home() / ".netrc"
        )
    except Exception as e:
        logger.error(f"Failed to search/download S1 SLC: {e}")
        raise
    
    logger.info(f"  Total candidates: {result.get('total_candidates', 0)}")
    logger.info(f"  Selected count: {result.get('selected_count', 0)}")
    logger.info(f"  Pairs count: {result.get('pairs_count', 0)}")
    logger.info(f"  Downloaded: {result.get('downloaded', False)}")
    
    if result.get('pairs_file'):
        logger.info(f"  Pairs file: {result['pairs_file']}")
    
    # Return summary
    return {
        "searched": result.get("searched", False),
        "downloaded": result.get("downloaded", False),
        "total_candidates": result.get("total_candidates", 0),
        "selected_count": result.get("selected_count", 0),
        "pairs_count": result.get("pairs_count", 0),
        "out_dir": str(ctx.s1_slc_dir),
        "pairs_file": result.get("pairs_file"),
    }

