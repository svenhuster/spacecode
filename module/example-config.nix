# Example home-manager configuration for SpacedCode
# Add this to your home-manager configuration

{ config, pkgs, ... }:

{
  imports = [
    # Import the SpacedCode home-manager module
    # Method 1: If using flakes, add to your flake inputs and import like:
    # inputs.spacedcode.homeManagerModules.default
    #
    # Method 2: If not using flakes, import directly:
    # /path/to/spacecode/module/home-manager.nix
  ];

  # Enable SpacedCode service
  services.spacedcode = {
    enable = true;

    # Basic configuration
    port = 1234;                    # Port to listen on (default: 1234)

    # Data storage location (optional)
    # dataDir = "${config.home.homeDirectory}/.local/share/spacedcode";  # default

    # Idle timeout (optional) - auto-shutdown after inactivity
    idleTimeout = 480;              # 8 hours in minutes (default: 480)

    # Network configuration (optional)
    # allowRemote = false;          # Allow remote connections (default: false)
    # host = "127.0.0.1";           # Host to bind to (default: 127.0.0.1)

    # Development/debugging (optional)
    # debug = false;                # Enable debug mode (default: false)

    # Package override (optional)
    # package = pkgs.callPackage /path/to/spacecode { };
  };

  # Optional: If you want to open firewall ports system-wide
  # (This only works if you have system-level firewall control)
  # services.spacedcode.openFirewall = true;
}

# Configuration Examples:

## Basic Usage (most common)
# services.spacedcode.enable = true;

## Custom port and allow remote access
# services.spacedcode = {
#   enable = true;
#   port = 8080;
#   allowRemote = true;
# };

## Custom data directory and shorter idle timeout (2 hours)
# services.spacedcode = {
#   enable = true;
#   dataDir = "${config.home.homeDirectory}/spacedcode-data";
#   idleTimeout = 120;  # 2 hours
# };

## Development setup with debug mode
# services.spacedcode = {
#   enable = true;
#   debug = true;
#   idleTimeout = 60;   # 1 hour for development
# };

# How to use:
# 1. Add this configuration to your home-manager config
# 2. Run: home-manager switch
# 3. The service will start automatically on socket activation
# 4. Access SpacedCode at: http://localhost:1234 (or your configured port)
# 5. Service will auto-shutdown after idle timeout and restart on next access

# Service management:
# - Check status: systemctl --user status spacedcode.socket
# - View logs: journalctl --user -u spacedcode.service -f
# - Restart: systemctl --user restart spacedcode.socket
# - Stop: systemctl --user stop spacedcode.socket

# Notes:
# - The service uses socket activation for efficient resource usage
# - Database and backups are stored in the configured data directory
# - All app settings (schedule profiles, etc.) are managed through the web UI
# - The service automatically creates database backups on startup and shutdown