{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.05";
    flake-utils.url = "github:numtide/flake-utils";
  };
  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};

        # Package definition for SpaceCode
        spacecode = pkgs.python3.pkgs.buildPythonApplication rec {
          pname = "spacecode";
          version = "1.0.0";
          format = "other";

          src = ./.;

          propagatedBuildInputs = with pkgs.python3.pkgs; [
            flask
            flask-sqlalchemy
            sqlalchemy
            alembic
          ];

          dontBuild = true;

          installPhase = ''
            mkdir -p $out/share/spacecode

            # Copy all source files including templates and static assets
            cp -r . $out/share/spacecode/

            # Remove development artifacts
            rm -rf $out/share/spacecode/.git $out/share/spacecode/.direnv $out/share/spacecode/__pycache__ $out/share/spacecode/result || true

            # Copy other important files
            for file in requirements.txt .gitignore README.md; do
              [ -f "$file" ] && cp "$file" $out/share/spacecode/ || true
            done

            # Create wrapper script that runs from the current directory
            mkdir -p $out/bin
            cat > $out/bin/spacecode << EOF
#!/usr/bin/env bash
# Check if we're in a spacecode project directory
if [[ -f "./app.py" && -f "./alembic.ini" ]]; then
  # Run from current directory (development mode)
  exec ${pkgs.python3}/bin/python3 ./app.py "\$@"
else
  # Run from Nix store (packaged mode)
  exec ${pkgs.python3}/bin/python3 $out/share/spacecode/app.py "\$@"
fi
EOF
            chmod +x $out/bin/spacecode
          '';

          meta = with pkgs.lib; {
            description = "SpaceCode - A Flask app for practicing LeetCode problems with spaced repetition";
            homepage = "https://github.com/example/spacecode";
            license = licenses.mit;
            maintainers = [ ];
            platforms = platforms.unix;
          };
        };

        # Development dependencies
        nativeBuildInputs = with pkgs; [
          makeWrapper
          pkg-config
          linuxPackages.perf
        ];

        buildInputs = with pkgs; [
          python312
          python312Packages.flask
          python312Packages.flask-sqlalchemy
          python312Packages.requests
          python312Packages.python-dateutil
          python312Packages.alembic
          sqlite
        ];
      in
      {
        # Package outputs
        packages = {
          default = spacecode;
          spacecode = spacecode;
        };

        # App outputs for easy running
        apps = {
          default = {
            type = "app";
            program = "${spacecode}/bin/spacecode";
          };
        };

        # Development shell
        devShells.default = pkgs.mkShell {
          inherit buildInputs nativeBuildInputs;
        };
      });
}
