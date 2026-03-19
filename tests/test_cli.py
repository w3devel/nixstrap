"""
Tests for the nixstrap CLI (nixstrap.cli).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from nixstrap.cli import main
from nixstrap.detect import Distro, PackageFormat, BootstrapMethod, RepoProfile


_DEBIAN_PROFILE = RepoProfile(
    distro=Distro.DEBIAN,
    package_format=PackageFormat.DEB,
    bootstrap_method=BootstrapMethod.DEBOOTSTRAP,
    nix_packages=("debootstrap",),
    codename="bookworm",
)

_UNKNOWN_PROFILE = RepoProfile(
    distro=Distro.UNKNOWN,
    package_format=PackageFormat.TARBALL,
    bootstrap_method=BootstrapMethod.TARBALL,
    nix_packages=("curl", "tar"),
)


class TestCli:
    def _runner(self):
        return CliRunner()

    def test_help_exits_zero(self):
        result = self._runner().invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "REPO_URL" in result.output

    def test_version_flag(self):
        result = self._runner().invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_missing_args_shows_help(self):
        result = self._runner().invoke(main, [])
        assert result.exit_code != 0

    def test_nix_not_available_exits_with_error(self, tmp_path):
        with patch("nixstrap.cli.nix_available", return_value=False):
            result = self._runner().invoke(main, ["http://deb.debian.org/debian", str(tmp_path)])
        assert result.exit_code == 1
        assert "Nix" in result.output or "nix" in result.output.lower()

    def test_successful_bootstrap_debian(self, tmp_path):
        with patch("nixstrap.cli.nix_available", return_value=True), \
             patch("nixstrap.cli.detect", return_value=_DEBIAN_PROFILE), \
             patch("nixstrap.backends.debootstrap.run_in_nix_shell") as mock_nix:
            mock_nix.return_value = MagicMock(returncode=0)
            result = self._runner().invoke(
                main,
                ["http://deb.debian.org/debian", str(tmp_path)],
            )
        assert result.exit_code == 0
        assert "Done" in result.output

    def test_no_probe_flag_passed_to_detect(self, tmp_path):
        with patch("nixstrap.cli.nix_available", return_value=True), \
             patch("nixstrap.cli.detect", return_value=_DEBIAN_PROFILE) as mock_detect, \
             patch("nixstrap.backends.debootstrap.run_in_nix_shell", return_value=MagicMock(returncode=0)):
            self._runner().invoke(
                main,
                ["http://deb.debian.org/debian", str(tmp_path), "--no-probe"],
            )
        mock_detect.assert_called_once()
        _, kwargs = mock_detect.call_args
        assert kwargs.get("probe") is False

    def test_codename_override(self, tmp_path):
        with patch("nixstrap.cli.nix_available", return_value=True), \
             patch("nixstrap.cli.detect", return_value=_DEBIAN_PROFILE), \
             patch("nixstrap.backends.debootstrap.run_in_nix_shell") as mock_nix:
            mock_nix.return_value = MagicMock(returncode=0)
            result = self._runner().invoke(
                main,
                ["http://deb.debian.org/debian", str(tmp_path), "--codename", "trixie"],
            )
        assert result.exit_code == 0
        # The overridden codename should appear in the debootstrap command
        cmd = mock_nix.call_args[1].get("command") or mock_nix.call_args[0][1]
        assert "trixie" in cmd

    def test_output_shows_detected_distro(self, tmp_path):
        with patch("nixstrap.cli.nix_available", return_value=True), \
             patch("nixstrap.cli.detect", return_value=_DEBIAN_PROFILE), \
             patch("nixstrap.backends.debootstrap.run_in_nix_shell", return_value=MagicMock(returncode=0)):
            result = self._runner().invoke(
                main,
                ["http://deb.debian.org/debian", str(tmp_path)],
            )
        assert "debian" in result.output.lower()
        assert "debootstrap" in result.output.lower()
