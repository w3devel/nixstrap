"""Abstract base class for nixstrap bootstrap backends."""

from __future__ import annotations

import abc
import os
from pathlib import Path


class BaseBackend(abc.ABC):
    """
    Common interface every nixstrap backend must implement.

    A *backend* knows how to bootstrap a rootfs directory for one particular
    distro family.  It delegates to :mod:`nixstrap.nix` so that the required
    bootstrap tool (debootstrap, dnf, zypper, …) is provided by Nix rather than
    requiring it to be pre-installed on the host.
    """

    #: Human-readable name shown in progress messages.
    name: str = ""

    def __init__(self, repo_url: str, target: Path, codename: str | None = None) -> None:
        self.repo_url = repo_url.rstrip("/")
        self.target = Path(target).resolve()
        self.codename = codename

    # ------------------------------------------------------------------
    # Subclass API
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def bootstrap(self) -> None:
        """Create the rootfs in :attr:`target`.  Must be implemented by subclasses."""

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def prepare_target(self) -> None:
        """Create the target directory (and any missing parents)."""
        os.makedirs(self.target, exist_ok=True)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"repo_url={self.repo_url!r}, "
            f"target={self.target!r}, "
            f"codename={self.codename!r})"
        )
