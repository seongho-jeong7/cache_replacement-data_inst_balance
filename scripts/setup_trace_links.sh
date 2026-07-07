#!/usr/bin/env bash
set -euo pipefail

################################################################################
# Trace link configuration
################################################################################

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Edit these paths when the shared trace location changes.
TRACE_SOURCE_ROOT="/home/seongho/shared/trace_for_champsim"
GTRACE_SOURCE_DIR="${TRACE_SOURCE_ROOT}/google"
GRAPH_SOURCE_DIR="${TRACE_SOURCE_ROOT}/Graph"

LOCAL_TRACE_DIR="${REPO_ROOT}/traces"
LOCAL_GTRACE_DIR="${LOCAL_TRACE_DIR}/gtrace_v2"
LOCAL_GRAPH_DIR="${LOCAL_TRACE_DIR}/Graph"

FORCE="N"

################################################################################
# Helpers
################################################################################

print_help() {
    echo "Link external trace directories into this repository."
    echo ""
    echo "Usage:"
    echo "  scripts/setup_trace_links.sh"
    echo "  scripts/setup_trace_links.sh --force"
    echo ""
    echo "Configured sources:"
    echo "  gtrace_v2 <- ${GTRACE_SOURCE_DIR}"
    echo "  Graph     <- ${GRAPH_SOURCE_DIR}"
    echo ""
    echo "Local targets:"
    echo "  ${LOCAL_GTRACE_DIR}"
    echo "  ${LOCAL_GRAPH_DIR}"
}

link_children() {
    local source_dir="$1"
    local target_dir="$2"

    if [ ! -d "${source_dir}" ]; then
        echo "Source directory not found: ${source_dir}" >&2
        return 1
    fi

    mkdir -p "${target_dir}"

    find "${source_dir}" -mindepth 1 -maxdepth 1 -type d | sort | while read -r source_child; do
        local name
        local target_child

        name="$(basename "${source_child}")"
        target_child="${target_dir}/${name}"

        if [ -L "${target_child}" ]; then
            if [ "${FORCE}" = "Y" ]; then
                rm "${target_child}"
            else
                echo "Skip existing symlink: ${target_child} -> $(readlink "${target_child}")"
                continue
            fi
        elif [ -e "${target_child}" ]; then
            echo "Skip existing path: ${target_child}" >&2
            echo "  Use --force only for existing symlinks; real files/directories are never removed." >&2
            continue
        fi

        ln -s "${source_child}" "${target_child}"
        echo "Linked: ${target_child} -> ${source_child}"
    done
}

################################################################################
# Main
################################################################################

while [ "$#" -gt 0 ]; do
    case "$1" in
        -h|--help)
            print_help
            exit 0
            ;;
        --force)
            FORCE="Y"
            ;;
        *)
            echo "Unknown option: $1" >&2
            print_help
            exit 1
            ;;
    esac
    shift
done

link_children "${GTRACE_SOURCE_DIR}" "${LOCAL_GTRACE_DIR}"
link_children "${GRAPH_SOURCE_DIR}" "${LOCAL_GRAPH_DIR}"
