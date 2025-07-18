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
      in
      {
        devShells.default = pkgs.mkShell {
          packages = [ pkgs.python311 ];
          shellHook = ''
            python -m venv venv
            source venv/bin/activate
            pip install textual regex types-regex pytest black mypy
            pip install -e .
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
            regex
            textual
          ];

          pythonImportCheck = [
            "ivm.runner"
          ];
        };
      }
    );
}
