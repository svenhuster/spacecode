{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.05";
    flake-utils.url = "github:numtide/flake-utils";
  };
  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};

        # Configuration defaults
        configDefaults = {
          port = 1234;
          host = "127.0.0.1";
          debug = false;
          allowRemote = false;
          schedule = "aggressive";
          secretKey = "leetcode-srs-secret-key-change-in-production";
        };

        # Development configuration overrides
        devConfig = configDefaults // {
          port = 1235;
          debug = true;
        };

        # Convert config to environment variables
        configToEnv = config: {
          SPACEDCODE_PORT = toString config.port;
          SPACEDCODE_HOST = config.host;
          SPACEDCODE_DEBUG = if config.debug then "true" else "false";
          SPACEDCODE_ALLOW_REMOTE = if config.allowRemote then "true" else "false";
          SPACEDCODE_SCHEDULE = config.schedule;
          SECRET_KEY = config.secretKey;
        };

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

          nativeBuildInputs = [ pkgs.makeWrapper ];

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

            # Create wrapper script with proper Python environment and config
            mkdir -p $out/bin
            makeWrapper ${pkgs.python3.withPackages (ps: propagatedBuildInputs)}/bin/python3 $out/bin/spacedcode \
              --add-flags "$out/share/spacedcode/app.py" \
              --set PYTHONPATH "$out/share/spacedcode" \
              --set SPACEDCODE_PORT "${toString configDefaults.port}" \
              --set SPACEDCODE_HOST "${configDefaults.host}" \
              --set SPACEDCODE_DEBUG "${if configDefaults.debug then "true" else "false"}" \
              --set SPACEDCODE_ALLOW_REMOTE "${if configDefaults.allowRemote then "true" else "false"}" \
              --set SPACEDCODE_SCHEDULE "${configDefaults.schedule}" \
              --set SECRET_KEY "${configDefaults.secretKey}"
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
        devShells.default = pkgs.mkShell (configToEnv devConfig // {
          inherit buildInputs nativeBuildInputs;
        });

        # Home Manager module
        homeModules = {
          default = import ./module/home-manager.nix;
          spacedcode = import ./module/home-manager.nix;
        };
      });
}
