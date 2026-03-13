"""
Debian / Ubuntu / Kali / Raspbian backend.

Uses ``debootstrap`` (provided by Nix) to create the rootfs directory.

Official documentation:
  https://wiki.debian.org/Debootstrap
  https://help.ubuntu.com/community/DebootstrapChroot
"""

from __future__ import annotations

import shlex
from pathlib import Path

from nixstrap.backends.base import BaseBackend
from nixstrap.nix import run_in_nix_shell

# Default codename used when the caller has not supplied one and we could not
# detect it from the repository metadata.
_DEFAULT_CODENAME = "stable"


class DebootstrapBackend(BaseBackend):
    """Bootstrap a Debian-family rootfs with ``debootstrap``."""

    name = "debootstrap"

    def __init__(
        self,
        repo_url: str,
        target: Path,
        codename: str | None = None,
        arch: str | None = None,
        variant: str | None = None,
    ) -> None:
        super().__init__(repo_url, target, codename)
        self.arch = arch          # e.g. "amd64", "arm64" — None means host arch
        self.variant = variant    # e.g. "minbase", "buildd" — None means default

    def bootstrap(self) -> None:
        """
        Run::

            nix-shell -p debootstrap --run \\
                "debootstrap [--arch ARCH] [--variant VARIANT] CODENAME TARGET REPO_URL"
        """
        self.prepare_target()

        codename = self.codename or _DEFAULT_CODENAME
        target_str = shlex.quote(str(self.target))
        repo_str = shlex.quote(self.repo_url)
        codename_str = shlex.quote(codename)

        parts = ["debootstrap"]
        if self.arch:
            parts.extend(["--arch", shlex.quote(self.arch)])
        if self.variant:
            parts.extend(["--variant", shlex.quote(self.variant)])
        parts += [codename_str, target_str, repo_str]

        run_in_nix_shell(
            packages=("debootstrap",),
            command=" ".join(parts),
        )
