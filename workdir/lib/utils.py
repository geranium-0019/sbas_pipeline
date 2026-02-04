"""Utility functions for the pipeline."""

import json
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def utc_now_iso() -> str:
    """Return current UTC time in ISO format."""
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def ensure_dir(p: Path) -> None:
    """Create directory recursively if it doesn't exist."""
    p.mkdir(parents=True, exist_ok=True)


def load_yaml(path: Path) -> Dict[str, Any]:
    """Load YAML file and return as dict."""
    import yaml
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def dump_json(path: Path, obj: Dict[str, Any]) -> None:
    """Write dict to JSON file atomically."""
    ensure_dir(path.parent)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    tmp.replace(path)


def read_json(path: Path) -> Dict[str, Any]:
    """Read JSON file and return as dict."""
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def run_cmd(
    cmd: List[str],
    *,
    cwd: Optional[Path] = None,
    env: Optional[Dict[str, str]] = None,
    check: bool = True,
    dry_run: bool = False,
    logger: Optional[logging.Logger] = None,
) -> subprocess.CompletedProcess:
    """Run a shell command and return the result."""
    msg = f"$ {' '.join(cmd)}"
    if cwd:
        msg = f"(cwd={cwd}) " + msg
    if logger:
        logger.info(msg)
    else:
        print(msg)

    if dry_run:
        # Fake a successful result
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    cp = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        text=True,
        capture_output=True,
    )

    if logger:
        if cp.stdout:
            logger.info(cp.stdout.rstrip())
        if cp.stderr:
            logger.warning(cp.stderr.rstrip())

    if check and cp.returncode != 0:
        raise RuntimeError(f"Command failed (code={cp.returncode}): {' '.join(cmd)}")

    return cp
