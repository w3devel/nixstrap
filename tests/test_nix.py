"""
Tests for nixstrap.nix — the Nix integration layer.
"""

from __future__ import annotations

from unittest.mock import patch, MagicMock
import subprocess

import pytest

from nixstrap.nix import run_in_nix_shell, nix_run, nix_available, _require_nix


# ---------------------------------------------------------------------------
# nix_available()
# ---------------------------------------------------------------------------

class TestNixAvailable:
    def test_true_when_nix_shell_on_path(self):
        with patch("nixstrap.nix.shutil.which", side_effect=lambda x: "/usr/bin/nix-shell" if x == "nix-shell" else None):
            assert nix_available() is True

    def test_true_when_nix_on_path(self):
        with patch("nixstrap.nix.shutil.which", side_effect=lambda x: "/usr/bin/nix" if x == "nix" else None):
            assert nix_available() is True

    def test_false_when_neither_on_path(self):
        with patch("nixstrap.nix.shutil.which", return_value=None):
            assert nix_available() is False


# ---------------------------------------------------------------------------
# _require_nix()
# ---------------------------------------------------------------------------

class TestRequireNix:
    def test_raises_when_nix_missing(self):
        with patch("nixstrap.nix.shutil.which", return_value=None):
            with pytest.raises(RuntimeError, match="Nix is not installed"):
                _require_nix()

    def test_does_not_raise_when_nix_present(self):
        with patch("nixstrap.nix.shutil.which", return_value="/usr/bin/nix-shell"):
            _require_nix()  # should not raise


# ---------------------------------------------------------------------------
# run_in_nix_shell()
# ---------------------------------------------------------------------------

class TestRunInNixShell:
    def _mock_which(self, name):
        return "/usr/bin/nix-shell" if name == "nix-shell" else None

    def test_calls_nix_shell_with_packages(self):
        with patch("nixstrap.nix.shutil.which", side_effect=self._mock_which), \
             patch("nixstrap.nix.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            run_in_nix_shell(["debootstrap"], "debootstrap stable /mnt http://deb.debian.org/debian")
            args = mock_run.call_args[0][0]
            assert args[0] == "nix-shell"
            assert "-p" in args
            assert "debootstrap" in args
            assert "--run" in args

    def test_pure_flag_added_when_requested(self):
        with patch("nixstrap.nix.shutil.which", side_effect=self._mock_which), \
             patch("nixstrap.nix.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            run_in_nix_shell(["curl"], "curl -v", pure=True)
            args = mock_run.call_args[0][0]
            assert "--pure" in args

    def test_pure_flag_not_added_by_default(self):
        with patch("nixstrap.nix.shutil.which", side_effect=self._mock_which), \
             patch("nixstrap.nix.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            run_in_nix_shell(["curl"], "curl -v")
            args = mock_run.call_args[0][0]
            assert "--pure" not in args

    def test_multiple_packages(self):
        with patch("nixstrap.nix.shutil.which", side_effect=self._mock_which), \
             patch("nixstrap.nix.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            run_in_nix_shell(["curl", "gnutar"], "curl -fsSL http://example.com | tar xz")
            args = mock_run.call_args[0][0]
            p_indices = [i for i, a in enumerate(args) if a == "-p"]
            pkgs = [args[i + 1] for i in p_indices]
            assert "curl" in pkgs
            assert "gnutar" in pkgs

    def test_raises_on_nix_missing(self):
        with patch("nixstrap.nix.shutil.which", return_value=None):
            with pytest.raises(RuntimeError):
                run_in_nix_shell(["bash"], "echo hello")


# ---------------------------------------------------------------------------
# nix_run()
# ---------------------------------------------------------------------------

class TestNixRun:
    def _mock_which(self, name):
        return "/usr/bin/nix" if name == "nix" else None

    def test_calls_nix_run_with_correct_args(self):
        with patch("nixstrap.nix.shutil.which", side_effect=self._mock_which), \
             patch("nixstrap.nix.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            nix_run("debootstrap", ["stable", "/mnt", "http://deb.debian.org/debian"])
            args = mock_run.call_args[0][0]
            assert args[:3] == ["nix", "run", "nixpkgs#debootstrap"]
            assert "--" in args
            assert "stable" in args
            assert "/mnt" in args

    def test_raises_on_nix_missing(self):
        with patch("nixstrap.nix.shutil.which", return_value=None):
            with pytest.raises(RuntimeError):
                nix_run("debootstrap", [])
