{
  description = "nixstrap — bootstrap a Linux rootfs from any distro's software repo using Nix";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python3;
      in {
        packages.default = python.pkgs.buildPythonApplication {
          pname = "nixstrap";
          version = "0.1.0";
          src = ./.;
          format = "pyproject";

          nativeBuildInputs = [ pkgs.python3Packages.setuptools ];
          propagatedBuildInputs = [
            python.pkgs.click
          ];

          meta = {
            description = "Bootstrap a Linux rootfs from any distro's software repo using Nix";
            license = pkgs.lib.licenses.mit;
            mainProgram = "nixstrap";
          };
        };

        apps.default = {
          type = "app";
          program = "${self.packages.${system}.default}/bin/nixstrap";
        };

        devShells.default = pkgs.mkShell {
          packages = [
            python
            python.pkgs.click
            python.pkgs.pytest
            python.pkgs.pytest-cov
            python.pkgs.responses
          ];
        };
      });
}
