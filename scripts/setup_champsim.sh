#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_VCPKG_PROVIDER="ChampSim"

CHAMPSIM_DIR=""
VCPKG_PROVIDER="${DEFAULT_VCPKG_PROVIDER}"

print_help() {
    cat <<EOF
Setup ChampSim dependencies

Usage:
  scripts/setup_champsim.sh -C <champsim_dir>

Options:
  -h              show this help
  -C <dir>        ChampSim directory to setup

Behavior:
  - Initializes submodules in the selected ChampSim directory.
  - If the selected directory has its own vcpkg directory, uses it directly.
  - If the selected directory has no vcpkg directory, initializes ${DEFAULT_VCPKG_PROVIDER}/vcpkg
    and links it into the selected directory as vcpkg.
  - Runs vcpkg install from the selected ChampSim directory so its vcpkg.json is used.
EOF
}

resolve_repo_path() {
    local path="$1"
    if [[ "${path}" = /* ]]; then
        printf '%s\n' "${path}"
    else
        printf '%s\n' "${REPO_ROOT}/${path}"
    fi
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        -h|--help)
            print_help
            exit 0
            ;;
        -C)
            if [ "$#" -lt 2 ]; then
                echo "Option -C requires an argument."
                exit 1
            fi
            CHAMPSIM_DIR="$2"
            shift 2
            ;;
        -C=*)
            CHAMPSIM_DIR="${1#-C=}"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            print_help
            exit 1
            ;;
    esac
done

if [ -z "${CHAMPSIM_DIR}" ]; then
    echo "Option -C is required. Choose the ChampSim project to setup."
    echo
    echo "Examples:"
    echo "  scripts/setup_champsim.sh -C ChampSim"
    echo "  scripts/setup_champsim.sh -C ChampSim_FDIP"
    echo "  scripts/setup_champsim.sh -C ChampSim_FDIP_ideal"
    echo "  scripts/setup_champsim.sh -C ChampSim_FDIP_dirty"
    exit 1
fi

CHAMPSIM_DIR="$(resolve_repo_path "${CHAMPSIM_DIR}")"
VCPKG_PROVIDER_DIR="$(resolve_repo_path "${VCPKG_PROVIDER}")"
TARGET_VCPKG="${CHAMPSIM_DIR}/vcpkg"
PROVIDER_VCPKG="${VCPKG_PROVIDER_DIR}/vcpkg"

if [ ! -d "${CHAMPSIM_DIR}" ]; then
    echo "ChampSim directory not found: ${CHAMPSIM_DIR}"
    exit 1
fi

if [ ! -f "${CHAMPSIM_DIR}/vcpkg.json" ]; then
    echo "vcpkg manifest not found: ${CHAMPSIM_DIR}/vcpkg.json"
    exit 1
fi

echo "Setting up ChampSim directory: ${CHAMPSIM_DIR}"

cd "${CHAMPSIM_DIR}"
git submodule update --init

if [ -L "${TARGET_VCPKG}" ]; then
    echo "Using linked vcpkg: ${TARGET_VCPKG} -> $(readlink "${TARGET_VCPKG}")"
    if [ ! -d "${TARGET_VCPKG}" ]; then
        echo "linked vcpkg target is not a directory: ${TARGET_VCPKG}"
        exit 1
    fi
elif [ ! -e "${TARGET_VCPKG}" ]; then
    if [ ! -d "${VCPKG_PROVIDER_DIR}" ]; then
        echo "vcpkg provider directory not found: ${VCPKG_PROVIDER_DIR}"
        exit 1
    fi

    echo "Selected directory has no vcpkg/. Preparing provider: ${VCPKG_PROVIDER_DIR}"
    cd "${VCPKG_PROVIDER_DIR}"
    git submodule update --init

    if [ ! -d "${PROVIDER_VCPKG}" ]; then
        echo "provider vcpkg directory not found after submodule init: ${PROVIDER_VCPKG}"
        exit 1
    fi

    echo "Linking ${TARGET_VCPKG} -> ${PROVIDER_VCPKG}"
    ln -s "${PROVIDER_VCPKG}" "${TARGET_VCPKG}"
elif [ -d "${TARGET_VCPKG}" ]; then
    echo "Using local vcpkg: ${TARGET_VCPKG}"
else
    echo "vcpkg path exists but is not a directory or symlink: ${TARGET_VCPKG}"
    exit 1
fi

if [ ! -x "${TARGET_VCPKG}/vcpkg" ]; then
    echo "Bootstrapping vcpkg: ${TARGET_VCPKG}"
    "${TARGET_VCPKG}/bootstrap-vcpkg.sh"
fi

cd "${CHAMPSIM_DIR}"
"${TARGET_VCPKG}/vcpkg" install
