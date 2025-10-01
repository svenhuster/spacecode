{ config, lib, pkgs, ... }:

with lib;

let
  cfg = config.services.spacedcode;
in
{
  options.services.spacedcode = {
    enable = mkEnableOption "SpacedCode LeetCode Spaced Repetition System";

    package = mkOption {
      type = types.package;
      default = pkgs.callPackage ../. { };
      defaultText = literalExpression "pkgs.callPackage ../. { }";
      description = "The SpacedCode package to use.";
    };

    port = mkOption {
      type = types.port;
      default = 1234;
      description = "Port to listen on.";
    };

    host = mkOption {
      type = types.str;
      default = "127.0.0.1";
      description = "Host to bind to.";
    };

    dataDir = mkOption {
      type = types.str;
      default = "${config.home.homeDirectory}/.local/share/spacedcode";
      defaultText = literalExpression "\"\${config.home.homeDirectory}/.local/share/spacedcode\"";
      description = "Directory to store SpacedCode data (database, backups).";
    };

    idleTimeout = mkOption {
      type = types.int;
      default = 480; # 8 hours in minutes
      description = "Idle timeout in minutes before auto-shutdown (default: 480 = 8 hours).";
    };

    allowRemote = mkOption {
      type = types.bool;
      default = false;
      description = "Allow remote connections (bind to 0.0.0.0 instead of localhost).";
    };

    debug = mkOption {
      type = types.bool;
      default = false;
      description = "Enable debug mode.";
    };

    openFirewall = mkOption {
      type = types.bool;
      default = false;
      description = "Open firewall port for SpacedCode (only works with system-level firewall).";
    };
  };

  config = mkIf cfg.enable {
    # Create data directory
    home.file."${removePrefix config.home.homeDirectory cfg.dataDir}/.keep".text = "";

    # Socket activation
    systemd.user.sockets.spacedcode = {
      Unit = {
        Description = "SpacedCode socket";
        Documentation = "https://github.com/example/spacedcode";
      };
      Socket = {
        ListenStream = "${cfg.host}:${toString cfg.port}";
        Accept = false;
        SocketUser = config.home.username;
        SocketMode = "0600";
      };
      Install = {
        WantedBy = [ "sockets.target" ];
      };
    };

    # Service configuration
    systemd.user.services.spacedcode = {
      Unit = {
        Description = "SpacedCode LeetCode Spaced Repetition System";
        Documentation = "https://github.com/example/spacedcode";
        Requires = [ "spacedcode.socket" ];
        After = [ "spacedcode.socket" ];
      };
      Service = {
        Type = "notify";
        ExecStart = "${cfg.package}/bin/spacedcode";
        Restart = "on-failure";
        RestartSec = "5s";
        StandardOutput = "journal";
        StandardError = "journal";

        # Environment variables
        Environment = [
          "SPACEDCODE_PORT=${toString cfg.port}"
          "SPACEDCODE_HOST=${if cfg.allowRemote then "0.0.0.0" else cfg.host}"
          "SPACEDCODE_DATA_DIR=${cfg.dataDir}"
          "SPACEDCODE_IDLE_TIMEOUT=${toString cfg.idleTimeout}"
          "SPACEDCODE_ALLOW_REMOTE=${if cfg.allowRemote then "true" else "false"}"
          "SPACEDCODE_DEBUG=${if cfg.debug then "true" else "false"}"
          "SPACEDCODE_SOCKET_ACTIVATION=true"
        ];

        # Security settings
        PrivateTmp = true;
        ProtectHome = "read-only";
        ProtectSystem = "strict";
        ReadWritePaths = [ cfg.dataDir ];
        NoNewPrivileges = true;
        ProtectKernelTunables = true;
        ProtectKernelModules = true;
        ProtectControlGroups = true;
        RestrictRealtime = true;
        RestrictNamespaces = true;
        LockPersonality = true;
        MemoryDenyWriteExecute = true;
        RestrictAddressFamilies = [ "AF_INET" "AF_INET6" "AF_UNIX" ];
        SystemCallFilter = [ "@system-service" "~@privileged" ];

        # Resource limits
        MemoryMax = "512M";
        TasksMax = 50;
      };
    };

    # Optional: Open firewall (requires system-level configuration)
    # This is just a placeholder - actual firewall rules need to be set at system level
    warnings = optional (cfg.openFirewall && !cfg.allowRemote)
      "services.spacedcode.openFirewall is enabled but allowRemote is false. The firewall port will be opened but the service only binds to localhost.";
  };

  meta.maintainers = with lib.maintainers; [ ];
}