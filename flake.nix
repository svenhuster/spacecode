{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.05";
    flake-utils.url = "github:numtide/flake-utils";
  };
  outputs = { self, nixpkgs, flake-utils }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};

      version = "0.1.0";

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
        devShells.${system}.default = pkgs.mkShell {
          inherit buildInputs nativeBuildInputs;

		CFLAGS="-Wall -Wextra -pedantic -std=c23 -ftrapv -Wconversion -Wsign-conversion -Wfloat-conversion -fsanitize=undefined -Wcast-qual -g -O2 -Wfatal-errors -Wno-cpp -fsanitize=signed-integer-overflow";
		CXXFLAGS="-Wall -Wextra -pedantic -std=c++23 -ftrapv -Wconversion -Wsign-conversion -Wfloat-conversion -fsanitize=undefined -Wcast-qual -g -O2 -Wfatal-errors -Wno-cpp -fsanitize=signed-integer-overflow";
		LDFLAGS="-fsanitize=address -g";
        };
      };
}
