{
  description = "DataIntegration Lab3 - integrated course management system";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.11";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
      in
      {
        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
            jdk21
            maven
            python313
            uv
          ];

          shellHook = ''
            echo "=== DataIntegration Lab3 ==="
            echo "Java:  $(java --version 2>&1 | head -1)"
            echo "Maven: $(mvn --version 2>&1 | head -1)"
            echo "Python: $(python3 --version)"
            echo ""
            echo "启动集成服务器: cd integration-server && mvn spring-boot:run"
            echo "启动系统A:      cd server-A && uv run python app.py"
          '';
        };
      });
}
