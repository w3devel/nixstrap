"""
Nix integration layer for nixstrap.

nixstrap uses Nix as its package provider — exactly the way VLC uses FFmpeg
underneath.  When nixstrap needs ``debootstrap``, ``dnf``, ``zypper``, or
``pacstrap``, it does not require those tools to be pre-installed on the host.
Instead it calls ``nix-shell -p <pkg> --run <cmd>`` so that Nix fetches and
provides every dependency at bootstrap time.

This module is the single place that knows about Nix; the rest of the code
just calls :func:`run_in_nix_shell` or :func:`nix_run`.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import Optional


def _require_nix() -> None:
    """Raise :class:`RuntimeError` when Nix is not available on ``$PATH``."""
    if not shutil.which("nix-shell") and not shutil.which("nix"):
        raise RuntimeError(
            "Nix is not installed or not on PATH.\n"
            "Install it from https://nixos.org/download and try again."
        )


def run_in_nix_shell(
    packages: tuple[str, ...] | list[str],
    command: str,
    *,
    pure: bool = False,
    extra_env: Optional[dict[str, str]] = None,
    check: bool = True,
    capture_output: bool = False,
) -> subprocess.CompletedProcess:
    """
    Run *command* inside a ``nix-shell`` that provides *packages*.

    This is the primary nix wrapper used by nixstrap backends.  It mirrors the
    way a media player like VLC calls ``ffmpeg``: the high-level tool (nixstrap)
    invokes a lower-level nix primitive to do the heavy lifting.

    Parameters
    ----------
    packages:
        nixpkgs attribute names to make available (e.g. ``["debootstrap"]``).
    command:
        Shell command string to run inside the nix-shell.
    pure:
        When *True*, pass ``--pure`` to nix-shell so the host environment is
        not inherited.  Useful for reproducible builds; disabled by default so
        the host ``/dev``, ``/proc``, etc. are visible during bootstrapping.
    extra_env:
        Additional environment variables to set inside the shell.
    check:
        Re-raise :class:`subprocess.CalledProcessError` on non-zero exit.
    capture_output:
        Capture stdout/stderr instead of printing them to the terminal.
    """
    _require_nix()

    cmd: list[str] = ["nix-shell"]
    if pure:
        cmd.append("--pure")
    for pkg in packages:
        cmd.extend(["-p", pkg])
    cmd.extend(["--run", command])

    env_args: dict = {}
    if extra_env:
        import os
        merged = os.environ.copy()
        merged.update(extra_env)
        env_args["env"] = merged

    return subprocess.run(
        cmd,
        check=check,
        capture_output=capture_output,
        **env_args,
    )


def nix_run(
    flake_attr: str,
    args: list[str],
    *,
    check: bool = True,
    capture_output: bool = False,
) -> subprocess.CompletedProcess:
    """
    Execute ``nix run nixpkgs#<flake_attr> -- <args>``.

    This is an alternative to :func:`run_in_nix_shell` for tools that work
    well as standalone flake apps.

    Parameters
    ----------
    flake_attr:
        The nixpkgs attribute to run (e.g. ``"debootstrap"``).
    args:
        Arguments forwarded to the tool after ``--``.
    """
    _require_nix()

    cmd = ["nix", "run", f"nixpkgs#{flake_attr}", "--"] + args
    return subprocess.run(cmd, check=check, capture_output=capture_output)


def nix_available() -> bool:
    """Return ``True`` when a usable Nix installation is found on ``$PATH``."""
    return bool(shutil.which("nix-shell") or shutil.which("nix"))
