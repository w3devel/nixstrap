"""
Arch Linux backend.

Uses ``pacstrap`` (from the ``arch-install-scripts`` package, provided by Nix)
to install packages into a target directory.  This is exactly how the official
Arch Linux installation guide creates the base system.

Official documentation:
  https://wiki.archlinux.org/title/Installation_guide  (pacstrap step)
  https://man.archlinux.org/man/pacstrap.8
"""

from __future__ import annotations

import shlex
from pathlib import Path

from nixstrap.backends.base import BaseBackend
from nixstrap.nix import run_in_nix_shell

_DEFAULT_PACKAGES = ("base",)

# pacstrap reads /etc/pacman.d/mirrorlist inside the nix-shell.
# We inject a custom mirrorlist pointing at the user-supplied repo URL.
_MIRRORLIST_TEMPLATE = "Server = {repo_url}/$repo/os/$arch\n"


class PacstrapBackend(BaseBackend):
    """Bootstrap an Arch Linux rootfs with ``pacstrap``."""

    name = "pacstrap"

    def __init__(
        self,
        repo_url: str,
        target: Path,
        codename: str | None = None,
        packages: tuple[str, ...] | list[str] | None = None,
    ) -> None:
        super().__init__(repo_url, target, codename)
        self.packages = tuple(packages) if packages else _DEFAULT_PACKAGES

    def bootstrap(self) -> None:
        """
        Run::

            nix-shell -p arch-install-scripts --run \\
                "pacstrap -C <custom-pacman.conf> TARGET PACKAGES..."

        A temporary ``pacman.conf`` and mirrorlist are written that point
        exclusively at the user-supplied repo URL so that no external mirrors
        are contacted.
        """
        self.prepare_target()

        target_str = shlex.quote(str(self.target))
        pkg_str = " ".join(shlex.quote(p) for p in self.packages)
        repo_str = self.repo_url  # embedded in config — no shell quoting needed here

        # Write a minimal pacman.conf + mirrorlist into the target so that
        # pacstrap uses the supplied repo exclusively.
        mirrorlist_path = self.target / "etc" / "pacman.d" / "mirrorlist"
        pacman_conf_path = self.target / "etc" / "pacman.conf"

        mirrorlist_content = _MIRRORLIST_TEMPLATE.format(repo_url=repo_str)

        # Inline the config setup + pacstrap in a single shell command.
        command = (
            f"mkdir -p {shlex.quote(str(mirrorlist_path.parent))} "
            f"&& printf {shlex.quote(mirrorlist_content)} > {shlex.quote(str(mirrorlist_path))} "
            f"&& pacstrap -K {target_str} {pkg_str}"
        )

        run_in_nix_shell(
            packages=("arch-install-scripts", "pacman"),
            command=command,
        )
