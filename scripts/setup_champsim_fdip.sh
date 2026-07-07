#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FDIP_DIR="${REPO_ROOT}/ChampSim_FDIP_ideal"

find_vcpkg_root() {
    for candidate in "${REPO_ROOT}/ChampSim_DPC4/vcpkg" "${REPO_ROOT}/ChampSim/vcpkg"; do
        if [ -d "${candidate}" ]; then
            printf '%s\n' "${candidate}"
            return
        fi
    done
}

VCPKG_ROOT="$(find_vcpkg_root)"

if [ -z "${VCPKG_ROOT}" ]; then
    echo "vcpkg directory not found. Initialize ChampSim or ChampSim_DPC4 first."
    exit 1
fi

if [ ! -f "${FDIP_DIR}/vcpkg.json" ]; then
    echo "FDIP vcpkg manifest not found: ${FDIP_DIR}/vcpkg.json"
    exit 1
fi

if [ ! -x "${VCPKG_ROOT}/vcpkg" ]; then
    "${VCPKG_ROOT}/bootstrap-vcpkg.sh"
fi

cd "${FDIP_DIR}"
"${VCPKG_ROOT}/vcpkg" install
