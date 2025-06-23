{
  description = "A development environment and package for py-ivm";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs { inherit system; };
        pyproject = pkgs.lib.importTOML ./pyproject.toml;
        python = pkgs.python311.override {
          self = python;
          packageOverrides = pyfinal: pyprev: {
            py-ivm-editable = pyfinal.mkPythonEditablePackage {
              pname = pyproject.project.name;
              inherit (pyproject.project) version;
              root = "$REPO_ROOT/py";
              inherit (pyproject.project) scripts;
              dependencies = with pkgs.python311Packages; [
                textual
                regex

                black
                mypy
                pytest

                pip
              ];
            };
          };
        };

        pythonEnv = python.withPackages (ps: [ ps.py-ivm-editable ]);
      in
      {
        devShells.default = pkgs.mkShell {
          packages = [ pythonEnv ];
          shellHook = ''
            export REPO_ROOT=$(git rev-parse --show-toplevel)
          '';
        };

        packages.default = pkgs.python311Packages.buildPythonApplication {
          pname = pyproject.project.name;
          inherit (pyproject.project) version;

          format = "pyproject";

          src = pkgs.lib.cleanSource ./.;
          build-systems = with pkgs.python311Packages; [
            build
            setuptools
            wheel
          ];

          nativeBuildInputs = with pkgs.python311Packages; [
            setuptools
          ];

          dependencies = with pkgs.python311Packages; [
            textual
            regex
          ];

          pythonImportCheck = [
            "ivm.runner"
          ];
        };
      }
    );
}
