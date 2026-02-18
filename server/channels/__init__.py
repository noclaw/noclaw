"""Channel plugin auto-discovery."""

import importlib
import inspect
import logging
import pkgutil
from pathlib import Path

from .base import Channel

logger = logging.getLogger(__name__)


def discover_channels() -> list:
    """Find all Channel subclasses whose required env vars are configured.

    Scans server/channels/ for modules, imports them, and checks is_configured().
    Channels with missing dependencies (ImportError) are silently skipped.
    """
    channels = []
    package_dir = Path(__file__).parent

    for _, module_name, _ in pkgutil.iter_modules([str(package_dir)]):
        if module_name.startswith("_") or module_name == "base":
            continue
        try:
            module = importlib.import_module(f".{module_name}", package=__package__)
        except ImportError as e:
            logger.debug(f"Skipping channel {module_name}: {e}")
            continue

        for _, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, Channel) and obj is not Channel and obj.is_configured():
                channels.append(obj)

    return channels
