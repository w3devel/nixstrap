"""
Fedora / RHEL / CentOS / Rocky / AlmaLinux backend.

Uses ``dnf`` (provided by Nix) to install packages into a rootfs directory.
This mirrors the ``--installroot`` approach that Fedora's own tooling uses to
create minimal container or VM images.

Official documentation:
  https://dnf.readthedocs.io/en/latest/command_ref.html  (--installroot)
  https://fedoraproject.org/wiki/Minimal_install
"""

from __future__ import annotations

import shlex
from pathlib import Path

from nixstrap.backends.base import BaseBackend
from nixstrap.nix import run_in_nix_shell

# Minimal package set installed by default (mirrors Fedora's @minimal-environment).
_DEFAULT_PACKAGES = ("bash", "coreutils", "dnf", "glibc-minimal-langpack")


class DnfBackend(BaseBackend):
    """Bootstrap a Fedora-family rootfs with ``dnf --installroot``."""

    name = "dnf"

    def __init__(
        self,
        repo_url: str,
        target: Path,
        codename: str | None = None,
        releasever: str | None = None,
        packages: tuple[str, ...] | list[str] | None = None,
    ) -> None:
        super().__init__(repo_url, target, codename)
        # 'releasever' is Fedora's release version variable (e.g. "39").
        # When not given we use the codename as a fallback.
        self.releasever = releasever or codename or "rawhide"
        self.packages = tuple(packages) if packages else _DEFAULT_PACKAGES

    def bootstrap(self) -> None:
        """
        Run::

            nix-shell -p dnf --run \\
                "dnf install --installroot TARGET --releasever VER \\
                             --repo REPO_URL --assumeyes PACKAGES..."
        """
        self.prepare_target()

        target_str = shlex.quote(str(self.target))
        releasever_str = shlex.quote(self.releasever)

        parts = [
            "dnf", "install",
            "--installroot", target_str,
            "--releasever", releasever_str,
            "--repofrompath", f"nixstrap-repo,{shlex.quote(self.repo_url)}",
            "--repo", "nixstrap-repo",
            "--assumeyes",
            "--setopt=install_weak_deps=False",
        ]
        parts += [shlex.quote(p) for p in self.packages]

        run_in_nix_shell(
            packages=("dnf",),
            command=" ".join(parts),
        )
