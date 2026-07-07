#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHAMPSIM_DIR="${REPO_ROOT}/ChampSim_FDIP"

cd "${CHAMPSIM_DIR}"
git submodule update --init
vcpkg/bootstrap-vcpkg.sh
vcpkg/vcpkg install
