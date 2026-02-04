"""Step 05: Configure and run stackSentinel."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from lib.context import Context
from lib.utils import ensure_dir, run_cmd, utc_now_iso


def _snwe_str_from_wsen_bbox(wsen: List[float]) -> str:
    """Convert [W,S,E,N] into stackSentinel -b 'S N W E' string."""
    if not wsen or len(wsen) != 4:
        raise ValueError(f"Invalid bbox (expected [W,S,E,N]): {wsen!r}")
    w, s, e, n = wsen
    return f"{s} {n} {w} {e}"


def _find_dem_file(dem_dir: Path) -> Path:
    """Pick a DEM file path for stackSentinel.py -d from a DEM directory."""
    if dem_dir.is_file():
        return dem_dir
    if not dem_dir.exists():
        raise FileNotFoundError(f"DEM directory not found: {dem_dir}")

    # Prefer common outputs from ISCE2 dem.py
    patterns = [
        "*.dem.wgs84",
        "*.dem",
        "*.wgs84.vrt",
        "*.vrt",
        "*.hgt",
    ]
    for pat in patterns:
        hits = sorted(dem_dir.glob(pat))
        if hits:
            return hits[0]

    # Fallback: any file
    for p in sorted(dem_dir.iterdir()):
        if p.is_file():
            return p

    raise FileNotFoundError(f"No DEM file found under: {dem_dir}")


def _extract_yyyymmdd_from_scene_id(scene_id: str) -> Optional[str]:
    """Extract YYYYMMDD from ASF scene id like S1A_..._20200107T...."""
    if not scene_id:
        return None
    # look for *_YYYYMMDDT*
    for i in range(len(scene_id) - 8):
        chunk = scene_id[i : i + 8]
        if chunk.isdigit():
            # heuristic: next char often 'T'
            if i + 8 < len(scene_id) and scene_id[i + 8] == "T":
                return chunk
    return None


def _choose_reference_date_auto(selected_ids: Iterable[str]) -> Optional[str]:
    """Choose a reference date (YYYYMMDD) from selected scene ids."""
    dates: List[str] = []
    for sid in selected_ids:
        d = _extract_yyyymmdd_from_scene_id(str(sid))
        if d:
            dates.append(d)
    if not dates:
        return None
    dates = sorted(set(dates))
    return dates[len(dates) // 2]


def _cfg_get(cfg: Dict[str, Any], path: Tuple[str, ...], default: Any = None) -> Any:
    cur: Any = cfg
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def _maybe_add(cmd: List[str], flag: str, value: Any) -> None:
    if value is None:
        return
    if isinstance(value, str) and not value.strip():
        return
    cmd += [flag, str(value)]


def step_05_config_stack(cfg: Dict[str, Any], ctx: Context, logger: logging.Logger) -> Dict[str, Any]:
    """
    ⑤ stackSentinel.py のパラメータ設定 & 実行

    自動で割り当てる（Step01-04成果物）:
      -s: ctx.s1_slc_dir
      -o: ctx.orbit_dir
      -a: ctx.aux_dir
      -w: ctx.isce2_dir
      -d: ctx.dem_dir 内の DEM ファイルを自動検出

    設定可能な重要パラメータ（config.yaml）:
      isce2:
        workflow: interferogram|slc|correlation|offset
        bbox: [S, N, W, E]   # 省略時: .state/sbas_pairs.json の selected_bbox から推定
        swath_num: "1 2 3"   # or "1 3"
        polarization: vv|vh|hh|hv
        coregistration: NESD|geometry
        reference_date: "auto"|"YYYYMMDD"
        snr_misreg_threshold: 10
        esd_coherence_threshold: 0.85
        num_overlap_connections: 3
        num_connections: 2
        range_looks: 9
        azimuth_looks: 3
        filter_strength: 0.5
        unw_method: snaphu|icu
        rm_filter: false
        num_proc: 8
        num_proc4topo: 4
        text_cmd: "source ~/.bashrc;"
        virtual_merge: true|false
    """
    logger.info("Step 05: configure & run stackSentinel")

    # Basic checks
    if not ctx.s1_slc_dir.exists():
        raise FileNotFoundError(f"SLC directory not found: {ctx.s1_slc_dir}")
    if not ctx.orbit_dir.exists():
        raise FileNotFoundError(f"Orbit directory not found: {ctx.orbit_dir}")
    if not ctx.dem_dir.exists():
        raise FileNotFoundError(f"DEM directory not found: {ctx.dem_dir}")

    ensure_dir(ctx.aux_dir)
    ensure_dir(ctx.isce2_dir)

    dem_file = _find_dem_file(ctx.dem_dir)

    # Try to use sbas_pairs.json for reference date auto
    sbas_pairs_path = ctx.state_dir / "sbas_pairs.json"
    sbas_meta: Dict[str, Any] = {}
    if sbas_pairs_path.exists():
        try:
            sbas_meta = json.loads(sbas_pairs_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"  Failed to read sbas_pairs.json: {e}")

    isce2_cfg: Dict[str, Any] = cfg.get("isce2", {}) or {}

    # BBOX: prefer explicit isce2.bbox; else use config aoi_bbox ([W,S,E,N]); else omit -b
    # NOTE: sbas_pairs.json selected_bbox is a UNION bbox and often extends beyond the common overlap,
    # which can lead to "dates covering the bbox (0)" in stackSentinel.
    bbox_snwe: Optional[str] = None
    cfg_bbox = isce2_cfg.get("bbox")
    if cfg_bbox and isinstance(cfg_bbox, (list, tuple)) and len(cfg_bbox) == 4:
        # already SNWE
        bbox_snwe = " ".join(str(x) for x in cfg_bbox)
    elif cfg.get("aoi_bbox") and isinstance(cfg.get("aoi_bbox"), (list, tuple)) and len(cfg["aoi_bbox"]) == 4:
        try:
            bbox_snwe = _snwe_str_from_wsen_bbox(list(cfg["aoi_bbox"]))
        except Exception as e:
            logger.warning(f"  Could not derive bbox from aoi_bbox: {e}")

    # Reference date
    ref_date = str(isce2_cfg.get("reference_date", "auto")).strip()
    if not ref_date or ref_date.lower() == "auto":
        ref_date = _choose_reference_date_auto(sbas_meta.get("selected_ids", []) or []) or ""

    # Build command
    cmd: List[str] = [
        "stackSentinel.py",
        "-s",
        str(ctx.s1_slc_dir),
        "-o",
        str(ctx.orbit_dir),
        "-a",
        str(ctx.aux_dir),
        "-d",
        str(dem_file),
        "-w",
        str(ctx.isce2_dir),
    ]

    # Workflow / AOI
    _maybe_add(cmd, "-W", isce2_cfg.get("workflow", "interferogram"))
    _maybe_add(cmd, "-n", isce2_cfg.get("swath_num"))
    if bbox_snwe:
        _maybe_add(cmd, "-b", bbox_snwe)

    # Dates of interest (optional)
    _maybe_add(cmd, "--start_date", isce2_cfg.get("start_date"))
    _maybe_add(cmd, "--stop_date", isce2_cfg.get("stop_date"))
    _maybe_add(cmd, "-x", isce2_cfg.get("exclude_dates"))
    _maybe_add(cmd, "-i", isce2_cfg.get("include_dates"))

    # Coregistration
    _maybe_add(cmd, "-C", isce2_cfg.get("coregistration", "NESD"))
    if ref_date:
        _maybe_add(cmd, "-m", ref_date)
    _maybe_add(cmd, "--snr_misreg_threshold", isce2_cfg.get("snr_misreg_threshold", 10))
    _maybe_add(cmd, "-e", isce2_cfg.get("esd_coherence_threshold", 0.85))
    _maybe_add(cmd, "-O", isce2_cfg.get("num_overlap_connections", 3))

    # Interferogram network / looks / filter
    num_connections = isce2_cfg.get("num_connections")
    if num_connections is None:
        # fallback: use SBAS k_neighbors if present
        num_connections = _cfg_get(cfg, ("sbas", "k_neighbors"), 1)
    _maybe_add(cmd, "-c", num_connections)
    _maybe_add(cmd, "-r", isce2_cfg.get("range_looks", 9))
    _maybe_add(cmd, "-z", isce2_cfg.get("azimuth_looks", 3))
    _maybe_add(cmd, "-f", isce2_cfg.get("filter_strength", 0.5))

    # Unwrap
    _maybe_add(cmd, "-u", isce2_cfg.get("unw_method", "snaphu"))
    if bool(isce2_cfg.get("rm_filter", False)):
        cmd.append("--rmFilter")

    # Compute
    if bool(isce2_cfg.get("use_gpu", False)):
        cmd.append("--useGPU")
    if isce2_cfg.get("num_proc") is not None:
        _maybe_add(cmd, "--num_proc", isce2_cfg.get("num_proc"))
    if isce2_cfg.get("num_proc4topo") is not None:
        _maybe_add(cmd, "--num_proc4topo", isce2_cfg.get("num_proc4topo"))
    _maybe_add(cmd, "-t", isce2_cfg.get("text_cmd"))

    if isce2_cfg.get("virtual_merge") is not None:
        _maybe_add(cmd, "-V", isce2_cfg.get("virtual_merge"))

    # Optional
    _maybe_add(cmd, "-p", isce2_cfg.get("polarization"))

    commands_log = ctx.isce2_dir / "commands.log"
    with commands_log.open("a", encoding="utf-8") as f:
        f.write(f"[{utc_now_iso()}] {' '.join(cmd)}\n")

    logger.info(f"  DEM file: {dem_file}")
    if bbox_snwe:
        logger.info(f"  bbox(SNWE): {bbox_snwe}")
    if ref_date:
        logger.info(f"  reference_date: {ref_date}")

    # Execute stackSentinel
    run_cmd(cmd, cwd=ctx.project_dir, dry_run=ctx.dry_run, logger=logger)

    return {
        "ran": True,
        "command": " ".join(cmd),
        "dem_file": str(dem_file),
        "bbox_snwe": bbox_snwe,
        "reference_date": ref_date or None,
        "isce2_work_dir": str(ctx.isce2_dir),
        "commands_log": str(commands_log),
    }

