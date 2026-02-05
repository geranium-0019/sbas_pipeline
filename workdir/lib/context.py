"""Context management for the pipeline."""

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from lib.utils import load_yaml


@dataclass(frozen=True)
class Context:
    """Pipeline execution context."""
    config_path: Path
    project_dir: Path
    logs_dir: Path
    state_dir: Path
    data_dir: Path
    isce2_dir: Path
    mintpy_dir: Path

    # common subdirs
    s1_slc_dir: Path
    dem_dir: Path
    orbit_dir: Path
    aux_dir: Path
    mintpy_run_dir: Path

    dry_run: bool
    force: bool
    only_steps: Optional[List[str]]
    from_step: Optional[str]
    until_step: Optional[str]


def build_context(cfg: Dict[str, Any], config_path: Path, args: argparse.Namespace) -> Context:
    """Build Context from config and arguments."""
    project_dir = Path(cfg.get("project_dir", "")).expanduser().resolve()
    if not str(project_dir):
        raise ValueError("config.yaml must set: project_dir")

    logs_dir = project_dir / "logs"
    state_dir = project_dir / ".state"
    data_dir = project_dir / "data"
    isce2_dir = project_dir / "isce2"
    mintpy_dir = project_dir / "mintpy"

    s1_slc_dir = data_dir / "s1_slc"
    dem_dir = data_dir / "dem"
    orbit_dir = data_dir / "orbit"
    aux_dir = data_dir / "aux"

    mintpy_run_dir = mintpy_dir

    return Context(
        config_path=config_path,
        project_dir=project_dir,
        logs_dir=logs_dir,
        state_dir=state_dir,
        data_dir=data_dir,
        isce2_dir=isce2_dir,
        mintpy_dir=mintpy_dir,
        s1_slc_dir=s1_slc_dir,
        dem_dir=dem_dir,
        orbit_dir=orbit_dir,
        aux_dir=aux_dir,
        mintpy_run_dir=mintpy_run_dir,
        dry_run=bool(args.dry_run),
        force=bool(args.force),
        only_steps=args.only_steps,
        from_step=args.from_step,
        until_step=args.until_step,
    )
