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
            flask-cors
            flask-sqlalchemy
            sqlalchemy
          ];

          dontBuild = true;

          installPhase = ''
            mkdir -p $out/share/spacecode

            # Copy source files, excluding development artifacts
            find . -name "*.py" -o -name "*.html" -o -name "*.css" -o -name "*.js" -o -name "*.sql" | \
              xargs -I {} cp --parents {} $out/share/spacecode/

            # Copy other important files
            for file in requirements.txt .gitignore README.md; do
              [ -f "$file" ] && cp "$file" $out/share/spacecode/ || true
            done

            # Create wrapper script
            mkdir -p $out/bin
            cat > $out/bin/spacecode << EOF
#!/usr/bin/env bash
exec ${pkgs.python3}/bin/python3 $out/share/spacecode/app.py "\$@"
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
          python312Packages.flask-cors
          python312Packages.requests
          python312Packages.python-dateutil
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
      }) // {
        # Home Manager module (system-independent)
        homeManagerModules.default = { config, lib, pkgs, ... }:
          let
            spacecodePackage = self.packages.${pkgs.system}.spacecode;
            cfg = config.services.spacecode;
          in
          {
            options.services.spacecode = {
              enable = lib.mkEnableOption "SpaceCode LeetCode Spaced Repetition System";

              port = lib.mkOption {
                type = lib.types.port;
                default = 1234;
                description = "Port to run the SpaceCode server on";
              };

              dataDir = lib.mkOption {
                type = lib.types.str;
                default = "${config.home.homeDirectory}/.local/share/spacecode";
                description = "Directory to store SpaceCode data";
              };

              debug = lib.mkOption {
                type = lib.types.bool;
                default = false;
                description = "Enable debug mode";
              };

              allowRemote = lib.mkOption {
                type = lib.types.bool;
                default = false;
                description = "Allow remote connections (bind to all interfaces instead of localhost only)";
              };

              openFirewall = lib.mkOption {
                type = lib.types.bool;
                default = false;
                description = "Whether to open the firewall for the SpaceCode port";
              };
            };

            config = lib.mkIf cfg.enable {
              home.packages = [ spacecodePackage ];

              systemd.user.services.spacecode = {
                Unit = {
                  Description = "SpaceCode LeetCode Spaced Repetition System";
                  After = [ "network.target" ];
                };

                Service = {
                  Type = "simple";
                  ExecStart = "${spacecodePackage}/bin/spacecode";
                  Restart = "always";
                  RestartSec = 5;

                  Environment = [
                    "SPACECODE_PORT=${toString cfg.port}"
                    "SPACECODE_DATA_DIR=${cfg.dataDir}"
                    "SPACECODE_DEBUG=${if cfg.debug then "true" else "false"}"
                    "SPACECODE_ALLOW_REMOTE=${if cfg.allowRemote then "true" else "false"}"
                  ];

                  # Security settings
                  NoNewPrivileges = true;
                  ProtectSystem = "strict";
                  ProtectHome = "read-only";
                  ReadWritePaths = [ cfg.dataDir ];
                  PrivateTmp = true;
                  ProtectKernelTunables = true;
                  ProtectKernelModules = true;
                  ProtectControlGroups = true;
                };

                Install = {
                  WantedBy = [ "default.target" ];
                };
              };

              # Create data directory
              home.activation.spacecode-data-dir = lib.hm.dag.entryAfter ["writeBoundary"] ''
                $DRY_RUN_CMD mkdir -p "${cfg.dataDir}"
                $DRY_RUN_CMD chmod 755 "${cfg.dataDir}"
              '';
            };
          };
      };
}
