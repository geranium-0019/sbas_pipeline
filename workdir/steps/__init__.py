"""Pipeline steps module."""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List
import logging

from lib.context import Context

StepFn = Callable[[Dict[str, Any], Context, logging.Logger], Dict[str, Any]]


@dataclass(frozen=True)
class Step:
    """Represents a single pipeline step."""
    id: str
    title: str
    fn: StepFn
