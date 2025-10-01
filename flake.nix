{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.05";
    flake-utils.url = "github:numtide/flake-utils";
  };
  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};

        # Package definition for SpacedCode
        spacedcode = pkgs.python3.pkgs.buildPythonApplication rec {
          pname = "spacedcode";
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
            mkdir -p $out/share/spacedcode

            # Copy all source files including templates and static assets
            cp -r . $out/share/spacedcode/

            # Remove development artifacts
            rm -rf $out/share/spacedcode/.git $out/share/spacedcode/.direnv $out/share/spacedcode/__pycache__ $out/share/spacedcode/result || true

            # Copy other important files
            for file in requirements.txt .gitignore README.md; do
              [ -f "$file" ] && cp "$file" $out/share/spacedcode/ || true
            done

            # Create wrapper script that always runs the installed version
            mkdir -p $out/bin
            cat > $out/bin/spacedcode << EOF
#!/usr/bin/env bash
# Always run the installed version from Nix store (production mode)
exec ${pkgs.python3}/bin/python3 $out/share/spacedcode/app.py "\$@"
EOF
            chmod +x $out/bin/spacedcode
          '';

          meta = with pkgs.lib; {
            description = "SpacedCode - A Flask app for practicing LeetCode problems with spaced repetition";
            homepage = "https://github.com/example/spacedcode";
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
          # Python and packages needed for development
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
          default = spacedcode;
          spacedcode = spacedcode;
        };

        # App outputs for easy running
        apps = {
          default = {
            type = "app";
            program = "${spacedcode}/bin/spacedcode";
          };
        };

        # Development shell
        devShells.default = pkgs.mkShell {
          inherit buildInputs nativeBuildInputs;
        };
      });
}
