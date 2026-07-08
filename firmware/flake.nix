{
  description = "Holy Guacamole meltybrain firmware (RP2350 / Pico SDK)";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";

  outputs =
    { nixpkgs, ... }:
    let
      # gcc-arm-embedded is available on these systems.
      systems = [
        "aarch64-darwin"
        "aarch64-linux"
        "x86_64-linux"
      ];
      forAllSystems = nixpkgs.lib.genAttrs systems;
    in
    {
      devShells = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          # withSubmodules pulls in tinyusb, needed for USB stdio.
          picoSdk = pkgs.pico-sdk.override { withSubmodules = true; };
        in
        {
          default = pkgs.mkShell {
            packages = [
              pkgs.cmake
              pkgs.gcc-arm-embedded
              pkgs.picotool
              pkgs.python3 # pico-sdk build scripts / pioasm
              # SITL simulator deps (host builds)
              pkgs.raylib
              pkgs.box2d
            ];

            PICO_SDK_PATH = "${picoSdk}/lib/pico-sdk";

            shellHook = ''
              echo "Holy Guacamole firmware shell"
              echo "PICO_SDK_PATH=$PICO_SDK_PATH"
              echo "firmware:  cmake -B build -DPICO_PLATFORM=rp2350 -DPICO_BOARD=pico2 && cmake --build build -j"
              echo "tests:     cmake -B build-tests -S tests && ctest --test-dir build-tests"
              echo "sim:       cmake -B build-sim -S sim && cmake --build build-sim && ./build-sim/drive"
            '';
          };
        }
      );
    };
}
