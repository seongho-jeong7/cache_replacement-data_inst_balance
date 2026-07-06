#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHAMPSIM_DIR="${REPO_ROOT}/ChampSim"

cd "${REPO_ROOT}"
git submodule update --init

cd "${CHAMPSIM_DIR}"
vcpkg/bootstrap-vcpkg.sh
vcpkg/vcpkg install
