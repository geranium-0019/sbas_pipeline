"""Step 04: Download orbit EOF files.

This step uses /work/fetchOrbit_asf.py (or /work/tools/fetchOrbit_asf.py) to download
Sentinel-1 precise/restituted orbit files from ASF (s1qc).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from lib.context import Context
from lib.utils import ensure_dir, run_cmd


def _find_fetch_orbit_script() -> Path:
    candidates = [
        Path("/work/fetchOrbit_asf.py"),
        Path("/work/tools/fetchOrbit_asf.py"),
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(
        "fetchOrbit_asf.py not found. Expected at /work/fetchOrbit_asf.py or /work/tools/fetchOrbit_asf.py"
    )


def _iter_slc_packages(slc_dir: Path) -> List[Path]:
    if not slc_dir.exists():
        return []
    zips = sorted(slc_dir.glob("*.zip"))
    safes = sorted([p for p in slc_dir.iterdir() if p.is_dir() and p.name.endswith(".SAFE")])
    return zips + safes


def _selected_ids_from_state(state_dir: Path) -> Optional[List[str]]:
    p = state_dir / "sbas_pairs.json"
    if not p.exists():
        return None
    try:
        meta = json.loads(p.read_text(encoding="utf-8"))
        ids = meta.get("selected_ids")
        if isinstance(ids, list):
            return [str(x) for x in ids]
    except Exception:
        return None
    return None


def _filter_to_selected(slcs: List[Path], selected_ids: Optional[List[str]]) -> List[Path]:
    if not selected_ids:
        return slcs
    wanted = set(selected_ids)
    out: List[Path] = []
    for p in slcs:
        # downloaded filenames are typically <scene_id>.zip
        stem = p.name
        if stem.endswith(".zip"):
            stem = stem[:-4]
        if stem in wanted:
            out.append(p)
    return out


def step_04_download_orbits(cfg: Dict[str, Any], ctx: Context, logger: logging.Logger) -> Dict[str, Any]:
    """
    ④ fetchOrbit_asf.py を使用して Orbit EOF をダウンロード

    config.yaml options (optional):
      orbits:
        prefer: precise|restituted   # default: precise
        only_selected: true|false    # default: true (use sbas_pairs.json selected_ids)
    """
    logger.info("Step 04: Download orbits (EOF) via fetchOrbit_asf.py")

    ensure_dir(ctx.orbit_dir)

    slcs_all = _iter_slc_packages(ctx.s1_slc_dir)
    if not slcs_all:
        logger.warning(f"  No SLC packages found under: {ctx.s1_slc_dir}")
        return {
            "orbits_downloaded": False,
            "reason": "no_slc_packages",
            "orbit_dir": str(ctx.orbit_dir),
        }

    orbits_cfg: Dict[str, Any] = cfg.get("orbits", {}) or {}
    prefer = str(orbits_cfg.get("prefer", "precise")).strip().lower() or "precise"
    if prefer not in {"precise", "restituted"}:
        raise ValueError(f"orbits.prefer must be precise|restituted (got: {prefer!r})")

    only_selected = bool(orbits_cfg.get("only_selected", True))
    selected_ids = _selected_ids_from_state(ctx.state_dir) if only_selected else None
    slcs = _filter_to_selected(slcs_all, selected_ids)

    script = _find_fetch_orbit_script()
    logger.info(f"  fetchOrbit_asf.py: {script}")
    logger.info(f"  SLC packages: {len(slcs)}/{len(slcs_all)} (only_selected={only_selected})")
    logger.info(f"  Output orbit_dir: {ctx.orbit_dir}")

    downloaded = 0
    for i, slc in enumerate(slcs, 1):
        logger.info(f"  [{i}/{len(slcs)}] orbit for: {slc.name}")
        cmd = [
            "python3",
            str(script),
            "-i",
            str(slc),
            "-o",
            str(ctx.orbit_dir),
            "--prefer",
            prefer,
        ]
        run_cmd(cmd, cwd=ctx.project_dir, dry_run=ctx.dry_run, logger=logger)
        downloaded += 1

    logger.info("  Orbit download complete")
    return {
        "orbits_downloaded": True,
        "count": downloaded,
        "orbit_dir": str(ctx.orbit_dir),
        "prefer": prefer,
        "only_selected": only_selected,
    }
