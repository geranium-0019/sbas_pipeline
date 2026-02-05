"""Step 07: Run MintPy processing.

Workflow (as requested):
  1) smallbaselineApp.py -g
  2) modify ONLY mintpy/smallbaselineApp.cfg (path settings) using workdir/smallbaselineApp.cfg as reference
  3) smallbaselineApp.py smallbaselineApp.cfg
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Mapping, Tuple, Optional

from lib.context import Context
from lib.utils import ensure_dir, run_cmd


# Only patch these keys in mintpy/smallbaselineApp.cfg (path settings).
# Source-of-truth values come from: <repo>/workdir/smallbaselineApp.cfg
_PATH_KEYS: List[str] = [
    "mintpy.load.metaFile",
    "mintpy.load.baselineDir",
    "mintpy.load.unwFile",
    "mintpy.load.corFile",
    "mintpy.load.connCompFile",
    "mintpy.load.demFile",
    "mintpy.load.lookupYFile",
    "mintpy.load.lookupXFile",
    "mintpy.load.incAngleFile",
    "mintpy.load.azAngleFile",
    "mintpy.load.shadowMaskFile",
]


_EXTRA_KEYS: List[str] = [
    # Explicit request: always set tropospheric correction OFF
    "mintpy.troposphericDelay.method",
]


_CFG_KEYS_TO_PATCH: List[str] = [*_PATH_KEYS, *_EXTRA_KEYS]


_GLOB_CHARS = set("*?[")


def _looks_like_path_value(value: str) -> bool:
    v = (value or "").strip()
    if not v:
        return False
    vlow = v.lower()
    if vlow in {"auto", "no", "none"}:
        return False
    return True


def _path_dir_hint(value: str) -> Optional[str]:
    """Return a directory-ish part of a path pattern for existence checking.

    Examples:
      ../reference/IW*.xml -> ../reference
      ../merged/interferograms/*/filt_*.unw -> ../merged/interferograms
      ../merged/geom_reference/los.rdr -> ../merged/geom_reference
    """
    v = (value or "").strip()
    if not _looks_like_path_value(v):
        return None

    # Chop at first glob char to get a stable prefix.
    first_glob = None
    for i, ch in enumerate(v):
        if ch in _GLOB_CHARS:
            first_glob = i
            break
    prefix = v if first_glob is None else v[:first_glob]

    # Use directory part of the prefix
    if "/" in prefix:
        d = prefix.rsplit("/", 1)[0]
        return d if d else None
    return None


def _choose_reference_base_dir(
    ctx: Context,
    ref_values: Mapping[str, str],
    *,
    logger: logging.Logger,
) -> Path:
    """Choose how to interpret relative paths in the reference cfg.

    We try several candidate bases and score them by how many referenced directories exist.
    """
    candidates: List[Path] = [
        ctx.mintpy_dir,
        ctx.project_dir,
        ctx.isce2_dir,
        ctx.isce2_dir / "mintpy",
    ]

    best = candidates[0]
    best_score = -1

    for base in candidates:
        score = 0
        for key in _PATH_KEYS:
            v = ref_values.get(key, "")
            hint = _path_dir_hint(v)
            if not hint:
                continue
            abs_dir = Path(os.path.normpath(str(base / hint)))
            if abs_dir.exists():
                score += 1
        if score > best_score:
            best_score = score
            best = base

    logger.info(f"Reference path base selected: {best} (score={best_score})")
    return best


def _relativize_pattern(
    value: str,
    *,
    reference_base_dir: Path,
    target_base_dir: Path,
) -> str:
    """Convert a (possibly relative) path/pattern into one relative to target_base_dir.

    Keeps globbing parts intact by relativizing only the non-glob prefix.
    """
    v = (value or "").strip()
    if not _looks_like_path_value(v):
        return v

    # Absolute path: just make it relative
    if v.startswith("/"):
        rel = os.path.relpath(v, str(target_base_dir))
        return rel.replace(os.sep, "/")

    # Find first glob char position
    first_glob = None
    for i, ch in enumerate(v):
        if ch in _GLOB_CHARS:
            first_glob = i
            break

    if first_glob is None:
        abs_path = Path(os.path.normpath(str(reference_base_dir / v)))
        rel = os.path.relpath(str(abs_path), str(target_base_dir))
        return rel.replace(os.sep, "/")

    prefix = v[:first_glob]
    suffix = v[first_glob:]

    # Split prefix into dir + (possibly partial) filename prefix
    if "/" in prefix:
        dir_part, file_prefix = prefix.rsplit("/", 1)
        abs_dir = Path(os.path.normpath(str(reference_base_dir / dir_part)))
        rel_dir = os.path.relpath(str(abs_dir), str(target_base_dir)).replace(os.sep, "/")
        if rel_dir == ".":
            rel_dir = ""
        if rel_dir:
            return f"{rel_dir}/{file_prefix}{suffix}"
        return f"{file_prefix}{suffix}"

    # No directory component; relativize reference_base_dir itself
    rel_base = os.path.relpath(str(reference_base_dir), str(target_base_dir)).replace(os.sep, "/")
    if rel_base == ".":
        return f"{prefix}{suffix}"
    return f"{rel_base}/{prefix}{suffix}"


def _split_value_and_comment(rhs: str) -> Tuple[str, str, str]:
    """Split 'value [ws]#comment' into (value, ws_before_hash, comment_with_hash)."""
    if "#" not in rhs:
        return rhs.strip(), "", ""

    idx = rhs.find("#")
    comment = rhs[idx:].rstrip("\n")

    # capture the whitespace immediately before '#'
    j = idx - 1
    while j >= 0 and rhs[j].isspace():
        j -= 1
    ws = rhs[j + 1 : idx]
    value = rhs[: j + 1].strip()
    return value, ws, comment


def _parse_cfg_kv(path: Path) -> Dict[str, str]:
    """Parse a MintPy cfg-like file into key->value (comments ignored)."""
    out: Dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in raw:
            continue
        left, right = raw.split("=", 1)
        key = left.strip()
        value, _, _ = _split_value_and_comment(right)
        if key and value:
            out[key] = value
    return out


def _patch_cfg_paths(
    target_cfg: Path,
    *,
    reference_values: Mapping[str, str],
    reference_base_dir: Path,
    target_base_dir: Path,
    keys: List[str],
    logger: logging.Logger,
) -> Dict[str, Tuple[str, str]]:
    """Update only selected keys in target_cfg, preserving existing comments/format as much as possible."""
    if not target_cfg.exists():
        raise FileNotFoundError(f"MintPy cfg not found: {target_cfg}")

    target_lines = target_cfg.read_text(encoding="utf-8").splitlines(keepends=True)
    changed: Dict[str, Tuple[str, str]] = {}

    ref_missing = [k for k in keys if k not in reference_values]
    if ref_missing:
        raise KeyError("Reference cfg is missing required key(s): " + ", ".join(ref_missing))

    key_set = set(keys)
    for i, raw in enumerate(target_lines):
        stripped = raw.lstrip()
        if not stripped or stripped.startswith("#") or "=" not in raw:
            continue

        left, right = raw.split("=", 1)
        key = left.strip()
        if key not in key_set:
            continue

        old_value, ws, comment = _split_value_and_comment(right)
        new_value_raw = str(reference_values[key]).strip()
        new_value = _relativize_pattern(
            new_value_raw,
            reference_base_dir=reference_base_dir,
            target_base_dir=target_base_dir,
        )

        if old_value != new_value:
            newline = "\n" if raw.endswith("\n") else ""
            target_lines[i] = f"{left.rstrip()} = {new_value}{ws}{comment}{newline}"
            changed[key] = (old_value, new_value)

    if changed:
        target_cfg.write_text("".join(target_lines), encoding="utf-8")
        logger.info(f"Patched {len(changed)} path keys in: {target_cfg}")
    else:
        logger.info(f"No path-key changes needed in: {target_cfg}")

    return changed


def step_07_run_mintpy(cfg: Dict[str, Any], ctx: Context, logger: logging.Logger) -> Dict[str, Any]:
    """⑦ MintPy を実行"""
    logger.info("Step 07: run MintPy")

    ensure_dir(ctx.mintpy_dir)

    # MintPy runs directly under mintpy/ (no mintpy/run)
    mintpy_workdir = ctx.mintpy_dir
    mintpy_cfg_path = mintpy_workdir / "smallbaselineApp.cfg"

    # Reference cfg shipped in this repo/workdir/
    repo_workdir = Path(__file__).resolve().parents[1]
    reference_cfg_path = repo_workdir / "smallbaselineApp.cfg"

    if ctx.dry_run:
        logger.info("DRY RUN: would run MintPy template generation and processing.")
        logger.info(f"  (cwd={mintpy_workdir}) $ smallbaselineApp.py -g")
        logger.info(f"  patch only: {mintpy_cfg_path}")
        logger.info(f"  reference : {reference_cfg_path}")
        logger.info(f"  (cwd={mintpy_workdir}) $ smallbaselineApp.py smallbaselineApp.cfg")
        return {
            "ran": False,
            "dry_run": True,
            "mintpy_dir": str(mintpy_workdir),
            "cfg_path": str(mintpy_cfg_path),
            "reference_cfg": str(reference_cfg_path),
        }

    if not reference_cfg_path.exists():
        raise FileNotFoundError(f"Reference cfg not found: {reference_cfg_path}")

    # 1) Generate template
    logger.info("1) Generate smallbaselineApp.cfg via: smallbaselineApp.py -g")
    cp = run_cmd(
        ["smallbaselineApp.py", "-g"],
        cwd=mintpy_workdir,
        check=False,  # some MintPy versions may return non-zero if file already exists
        dry_run=ctx.dry_run,
        logger=logger,
    )
    if cp.returncode != 0 and not mintpy_cfg_path.exists():
        raise RuntimeError("smallbaselineApp.py -g failed and did not create smallbaselineApp.cfg")

    # 2) Patch selected keys in mintpy/smallbaselineApp.cfg using reference
    # - Path-related keys are normalized to be relative to mintpy_workdir.
    # - Also force mintpy.troposphericDelay.method = no.
    logger.info("2) Patch mintpy/smallbaselineApp.cfg (paths + requested overrides)")
    ref_values = _parse_cfg_kv(reference_cfg_path)
    ref_values.setdefault("mintpy.troposphericDelay.method", "no")

    # This is a pipeline with a stable directory layout, so we do not need to
    # score/search for the reference base dir on every run.
    # The reference cfg paths (e.g. ../reference, ../merged/...) are meant to be
    # interpreted relative to: <project>/isce2/mintpy
    preferred_reference_base_dir = ctx.isce2_dir / "mintpy"
    if preferred_reference_base_dir.exists():
        reference_base_dir = preferred_reference_base_dir
        logger.info(f"Reference path base fixed: {reference_base_dir}")
    else:
        # Fallback (should be rare): keep the old heuristic.
        reference_base_dir = _choose_reference_base_dir(ctx, ref_values, logger=logger)

    changed = _patch_cfg_paths(
        mintpy_cfg_path,
        reference_values=ref_values,
        reference_base_dir=reference_base_dir,
        target_base_dir=mintpy_workdir,
        keys=_CFG_KEYS_TO_PATCH,
        logger=logger,
    )

    # 3) Run MintPy
    logger.info("3) Run MintPy via: smallbaselineApp.py smallbaselineApp.cfg")
    run_cmd(
        ["smallbaselineApp.py", "smallbaselineApp.cfg"],
        cwd=mintpy_workdir,
        dry_run=ctx.dry_run,
        logger=logger,
    )

    return {
        "ran": True,
        "dry_run": bool(ctx.dry_run),
        "mintpy_dir": str(mintpy_workdir),
        "cfg_path": str(mintpy_cfg_path),
        "reference_cfg": str(reference_cfg_path),
        "reference_path_base": str(reference_base_dir),
        "patched_keys": {k: {"from": v[0], "to": v[1]} for k, v in changed.items()},
        "patched_count": len(changed),
    }
