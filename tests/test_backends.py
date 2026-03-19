"""
Tests for nixstrap backends — verifying that each backend constructs the
correct nix-shell command for its distro family.

All calls to :func:`nixstrap.nix.run_in_nix_shell` are mocked so no real
bootstrapping is attempted.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, call, MagicMock

import pytest

from nixstrap.backends.debootstrap import DebootstrapBackend
from nixstrap.backends.dnf import DnfBackend
from nixstrap.backends.zypper import ZypperBackend
from nixstrap.backends.pacstrap import PacstrapBackend
from nixstrap.backends.tarball import TarballBackend


_REPO = "http://example.com/repo"
_TARGET = Path("/tmp/nixstrap-test-rootfs")


def _mock_nix(monkeypatch):
    """Patch run_in_nix_shell across all backends and return the mock."""
    mock = MagicMock(return_value=MagicMock(returncode=0))
    for mod in (
        "nixstrap.backends.debootstrap",
        "nixstrap.backends.dnf",
        "nixstrap.backends.zypper",
        "nixstrap.backends.pacstrap",
        "nixstrap.backends.tarball",
    ):
        monkeypatch.setattr(f"{mod}.run_in_nix_shell", mock)
    return mock


# ---------------------------------------------------------------------------
# DebootstrapBackend
# ---------------------------------------------------------------------------

class TestDebootstrapBackend:
    def test_uses_debootstrap_package(self, tmp_path, monkeypatch):
        mock = _mock_nix(monkeypatch)
        b = DebootstrapBackend(_REPO, tmp_path, codename="bookworm")
        b.bootstrap()
        pkgs = mock.call_args.kwargs.get("packages") or mock.call_args[1].get("packages") or mock.call_args[0][0]
        assert "debootstrap" in pkgs

    def test_command_includes_codename(self, tmp_path, monkeypatch):
        mock = _mock_nix(monkeypatch)
        b = DebootstrapBackend(_REPO, tmp_path, codename="bookworm")
        b.bootstrap()
        cmd = mock.call_args[1].get("command") or mock.call_args[0][1]
        assert "bookworm" in cmd

    def test_command_includes_target(self, tmp_path, monkeypatch):
        mock = _mock_nix(monkeypatch)
        b = DebootstrapBackend(_REPO, tmp_path, codename="stable")
        b.bootstrap()
        cmd = mock.call_args[1].get("command") or mock.call_args[0][1]
        assert str(tmp_path) in cmd

    def test_command_includes_repo_url(self, tmp_path, monkeypatch):
        mock = _mock_nix(monkeypatch)
        b = DebootstrapBackend(_REPO, tmp_path, codename="stable")
        b.bootstrap()
        cmd = mock.call_args[1].get("command") or mock.call_args[0][1]
        assert _REPO in cmd

    def test_arch_option_forwarded(self, tmp_path, monkeypatch):
        mock = _mock_nix(monkeypatch)
        b = DebootstrapBackend(_REPO, tmp_path, codename="stable", arch="arm64")
        b.bootstrap()
        cmd = mock.call_args[1].get("command") or mock.call_args[0][1]
        assert "--arch" in cmd
        assert "arm64" in cmd

    def test_variant_option_forwarded(self, tmp_path, monkeypatch):
        mock = _mock_nix(monkeypatch)
        b = DebootstrapBackend(_REPO, tmp_path, codename="stable", variant="minbase")
        b.bootstrap()
        cmd = mock.call_args[1].get("command") or mock.call_args[0][1]
        assert "--variant" in cmd
        assert "minbase" in cmd

    def test_default_codename_used_when_none(self, tmp_path, monkeypatch):
        mock = _mock_nix(monkeypatch)
        b = DebootstrapBackend(_REPO, tmp_path)
        b.bootstrap()
        cmd = mock.call_args[1].get("command") or mock.call_args[0][1]
        assert "stable" in cmd


# ---------------------------------------------------------------------------
# DnfBackend
# ---------------------------------------------------------------------------

class TestDnfBackend:
    def test_uses_dnf_package(self, tmp_path, monkeypatch):
        mock = _mock_nix(monkeypatch)
        b = DnfBackend(_REPO, tmp_path, codename="39")
        b.bootstrap()
        pkgs = mock.call_args[1].get("packages") or mock.call_args[0][0]
        assert "dnf" in pkgs

    def test_command_includes_installroot(self, tmp_path, monkeypatch):
        mock = _mock_nix(monkeypatch)
        b = DnfBackend(_REPO, tmp_path, codename="39")
        b.bootstrap()
        cmd = mock.call_args[1].get("command") or mock.call_args[0][1]
        assert "--installroot" in cmd
        assert str(tmp_path) in cmd

    def test_command_includes_releasever(self, tmp_path, monkeypatch):
        mock = _mock_nix(monkeypatch)
        b = DnfBackend(_REPO, tmp_path, releasever="39")
        b.bootstrap()
        cmd = mock.call_args[1].get("command") or mock.call_args[0][1]
        assert "--releasever" in cmd
        assert "39" in cmd

    def test_command_includes_repo_url(self, tmp_path, monkeypatch):
        mock = _mock_nix(monkeypatch)
        b = DnfBackend(_REPO, tmp_path)
        b.bootstrap()
        cmd = mock.call_args[1].get("command") or mock.call_args[0][1]
        assert _REPO in cmd


# ---------------------------------------------------------------------------
# ZypperBackend
# ---------------------------------------------------------------------------

class TestZypperBackend:
    def test_uses_zypper_package(self, tmp_path, monkeypatch):
        mock = _mock_nix(monkeypatch)
        b = ZypperBackend(_REPO, tmp_path)
        b.bootstrap()
        pkgs = mock.call_args[1].get("packages") or mock.call_args[0][0]
        assert "zypper" in pkgs

    def test_command_includes_root(self, tmp_path, monkeypatch):
        mock = _mock_nix(monkeypatch)
        b = ZypperBackend(_REPO, tmp_path)
        b.bootstrap()
        cmd = mock.call_args[1].get("command") or mock.call_args[0][1]
        assert "--root" in cmd
        assert str(tmp_path) in cmd

    def test_command_includes_addrepo(self, tmp_path, monkeypatch):
        mock = _mock_nix(monkeypatch)
        b = ZypperBackend(_REPO, tmp_path)
        b.bootstrap()
        cmd = mock.call_args[1].get("command") or mock.call_args[0][1]
        assert "addrepo" in cmd
        assert _REPO in cmd

    def test_command_includes_install(self, tmp_path, monkeypatch):
        mock = _mock_nix(monkeypatch)
        b = ZypperBackend(_REPO, tmp_path)
        b.bootstrap()
        cmd = mock.call_args[1].get("command") or mock.call_args[0][1]
        assert "install" in cmd


# ---------------------------------------------------------------------------
# PacstrapBackend
# ---------------------------------------------------------------------------

class TestPacstrapBackend:
    def test_uses_arch_install_scripts(self, tmp_path, monkeypatch):
        mock = _mock_nix(monkeypatch)
        b = PacstrapBackend(_REPO, tmp_path)
        b.bootstrap()
        pkgs = mock.call_args[1].get("packages") or mock.call_args[0][0]
        assert "arch-install-scripts" in pkgs

    def test_command_includes_pacstrap(self, tmp_path, monkeypatch):
        mock = _mock_nix(monkeypatch)
        b = PacstrapBackend(_REPO, tmp_path)
        b.bootstrap()
        cmd = mock.call_args[1].get("command") or mock.call_args[0][1]
        assert "pacstrap" in cmd

    def test_command_includes_target(self, tmp_path, monkeypatch):
        mock = _mock_nix(monkeypatch)
        b = PacstrapBackend(_REPO, tmp_path)
        b.bootstrap()
        cmd = mock.call_args[1].get("command") or mock.call_args[0][1]
        assert str(tmp_path) in cmd

    def test_command_includes_repo_url(self, tmp_path, monkeypatch):
        mock = _mock_nix(monkeypatch)
        b = PacstrapBackend(_REPO, tmp_path)
        b.bootstrap()
        cmd = mock.call_args[1].get("command") or mock.call_args[0][1]
        assert _REPO in cmd


# ---------------------------------------------------------------------------
# TarballBackend
# ---------------------------------------------------------------------------

class TestTarballBackend:
    def test_uses_curl_and_tar(self, tmp_path, monkeypatch):
        mock = _mock_nix(monkeypatch)
        b = TarballBackend(_REPO, tmp_path)
        b.bootstrap()
        pkgs = mock.call_args[1].get("packages") or mock.call_args[0][0]
        assert "curl" in pkgs

    def test_command_includes_curl(self, tmp_path, monkeypatch):
        mock = _mock_nix(monkeypatch)
        b = TarballBackend(_REPO, tmp_path)
        b.bootstrap()
        cmd = mock.call_args[1].get("command") or mock.call_args[0][1]
        assert "curl" in cmd

    def test_command_includes_repo_url(self, tmp_path, monkeypatch):
        mock = _mock_nix(monkeypatch)
        b = TarballBackend(_REPO, tmp_path)
        b.bootstrap()
        cmd = mock.call_args[1].get("command") or mock.call_args[0][1]
        assert _REPO in cmd

    def test_command_pipes_to_tar(self, tmp_path, monkeypatch):
        mock = _mock_nix(monkeypatch)
        b = TarballBackend(_REPO, tmp_path)
        b.bootstrap()
        cmd = mock.call_args[1].get("command") or mock.call_args[0][1]
        assert "tar" in cmd
        assert str(tmp_path) in cmd
