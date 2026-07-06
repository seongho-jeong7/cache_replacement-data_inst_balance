#!/usr/bin/env bash
set -euo pipefail

################################################################################
# Configuration
################################################################################

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHAMPSIM_DIR="${REPO_ROOT}/ChampSim"
CONFIG_FILE="${REPO_ROOT}/config/config_default.json"
TRACE_DIR="${REPO_ROOT}/traces/gtrace_v2"
OUTPUT_DIR="${REPO_ROOT}/outputs"
CONFIG_SIGNATURE="$(python3 - "${CONFIG_FILE}" <<'PY'
import json
import re
import sys

with open(sys.argv[1], encoding="utf-8") as fp:
    cfg = json.load(fp)

cpu = (cfg.get("ooo_cpu") or [{}])[0]

parts = [
    cpu.get("branch_predictor", "no"),
    cpu.get("btb", "no"),
    cfg.get("L1I", {}).get("prefetcher", "no"),
    cfg.get("L1D", {}).get("prefetcher", "no"),
    cfg.get("L2C", {}).get("prefetcher", "no"),
    cfg.get("LLC", {}).get("prefetcher", "no"),
    cfg.get("LLC", {}).get("replacement", "no"),
    f"{cfg.get('num_cores', 1)}core",
]

signature = "-".join(str(part) for part in parts)
print(re.sub(r"[^A-Za-z0-9_.-]+", "_", signature))
PY
)"
RUN_ID="$(date +%y%m%d_%H%M)"
RUN_OUTPUT_DIR="${OUTPUT_DIR}/${RUN_ID}"
RUN_LOG="${RUN_OUTPUT_DIR}/run.log"
WARMUP_INSTRUCTIONS=100000
SIMULATION_INSTRUCTIONS=100000
NUM_THREAD=16
BUILD="N"
RUN_TRACES="N"
SUMMARY="N"
VERBOSE="N"

################################################################################
# Help
################################################################################

print_help() {
    echo "Run ChampSim"
    echo "Options:"
    echo " -h: help"
    echo " -v: verbose mode"
    echo " -p [num]: run using [num] threads (default: 16)"
    echo " -b: configure and build ChampSim"
    echo " -t: run traces"
    echo " -s: summarize the latest metrics.csv"
    echo ""
    echo "Defaults:"
    echo " config: ${CONFIG_FILE}"
    echo " config signature: ${CONFIG_SIGNATURE}"
    echo " traces: ${TRACE_DIR}"
    echo " output: ${OUTPUT_DIR}/YYMMDD_HHMM/<trace_root>/<trace_group>/<config_signature>---<trace_file>.log"
    exit
}

################################################################################
# Functions
################################################################################

find_traces() {
    if [ -d "${TRACE_DIR}" ]; then
        find -L "${TRACE_DIR}" -type f | sort
        return
    fi

    if [ -f "${TRACE_DIR}" ]; then
        printf '%s\n' "${TRACE_DIR}"
    fi
}

log() {
    echo "$@" >> "${RUN_LOG}"
}

error() {
    echo "$@" | tee -a "${RUN_LOG}" >&2
}

################################################################################
# Parse Options
################################################################################

while getopts ":hvp:bts" opt; do
    case "${opt}" in
        h) print_help ;;
        v) VERBOSE="Y" ;;
        p) NUM_THREAD="${OPTARG}" ;;
        b) BUILD="Y" ;;
        t) RUN_TRACES="Y" ;;
        s) SUMMARY="Y" ;;
        *) print_help ;;
    esac
done

################################################################################
# Body
################################################################################

if ! [[ "${NUM_THREAD}" =~ ^[1-9][0-9]*$ ]]; then
    echo "Invalid thread count: ${NUM_THREAD}"
    exit 1
fi

if [ "${SUMMARY}" = "Y" ]; then
    latest_run="$(find "${OUTPUT_DIR}" -mindepth 1 -maxdepth 1 -type d | sort | tail -n 1)"
    if [ "${latest_run}" = "" ]; then
        echo "No run directory found under ${OUTPUT_DIR}"
        exit 1
    fi
    latest_metrics="${latest_run}/metrics.csv"
    if [ ! -f "${latest_metrics}" ]; then
        echo "Generating missing metrics: ${latest_metrics}"
        "${REPO_ROOT}/parser/parse_outputs.py" "${latest_run}" -o "${latest_metrics}"
    fi
    "${REPO_ROOT}/parser/summary.py" "${latest_metrics}"
    exit
fi

mkdir -p "${RUN_OUTPUT_DIR}"
cp "${CONFIG_FILE}" "${RUN_OUTPUT_DIR}/config.json"
printf '%s\n' "${CONFIG_SIGNATURE}" > "${RUN_OUTPUT_DIR}/config_signature.txt"
: > "${RUN_LOG}"
echo "Run log: ${RUN_LOG}"
log "Run log: ${RUN_LOG}"

if [ "${BUILD}" = "Y" ]; then
    log "Configuring ChampSim with ${CONFIG_FILE}"
    cd "${CHAMPSIM_DIR}"
    ./config.sh "${CONFIG_FILE}" >> "${RUN_LOG}" 2>&1
    make >> "${RUN_LOG}" 2>&1
    cd "${REPO_ROOT}"
else
    log "Skipping configure/build. Use -b to configure and build ChampSim."
fi

if [ "${RUN_TRACES}" = "Y" ]; then
    mapfile -t TRACE_FILES < <(find_traces)

    if [ "${#TRACE_FILES[@]}" -eq 0 ]; then
        error "Trace files not found: ${TRACE_DIR}"
        exit 1
    fi

    log "Running ${#TRACE_FILES[@]} trace(s) with ${NUM_THREAD} thread(s)."
    log "Output directory: ${RUN_OUTPUT_DIR}"
    log "Config signature: ${CONFIG_SIGNATURE}"
    export CHAMPSIM_DIR TRACE_DIR RUN_OUTPUT_DIR RUN_LOG CONFIG_SIGNATURE WARMUP_INSTRUCTIONS SIMULATION_INSTRUCTIONS
    trace_status=0
    printf '%s\0' "${TRACE_FILES[@]}" | xargs -0 -n 1 -P "${NUM_THREAD}" bash -c '
        trace_file="$1"
        trace_name="$(basename "${trace_file}")"
        trace_name="${trace_name//[^A-Za-z0-9_.-]/_}"
        trace_root="$(basename "${TRACE_DIR}")"
        trace_parent="$(dirname "${trace_file}")"
        trace_group="${trace_parent#${TRACE_DIR}/}"

        if [ "${trace_group}" = "${trace_parent}" ] || [ "${trace_group}" = "." ]; then
            trace_group="${trace_name%%_*}"
            trace_group="${trace_group%%.*}"
        fi

        trace_root="${trace_root//[^A-Za-z0-9_.-]/_}"
        trace_group="${trace_group//[^A-Za-z0-9_.-]/_}"
        output_dir="${RUN_OUTPUT_DIR}/${trace_root}/${trace_group}"
        output_file="${output_dir}/${CONFIG_SIGNATURE}---${trace_name}.log"
        mkdir -p "${output_dir}"

        echo "Running trace: ${trace_file}" >> "${RUN_LOG}"
        "${CHAMPSIM_DIR}/bin/champsim" \
            --warmup-instructions "${WARMUP_INSTRUCTIONS}" \
            --simulation-instructions "${SIMULATION_INSTRUCTIONS}" \
            "${trace_file}" > "${output_file}" 2>&1
        status=$?
        if [ "${status}" -ne 0 ]; then
            message="Failed trace: ${trace_file} (exit ${status})"
            echo "${message}" | tee -a "${RUN_LOG}" >&2
            echo "${message}" >> "${output_file}"
            exit "${status}"
        fi
        echo "Saved output to ${output_file}" >> "${RUN_LOG}"
    ' _ || trace_status=$?

    log "Generating metrics: ${RUN_OUTPUT_DIR}/metrics.csv"
    "${REPO_ROOT}/parser/parse_outputs.py" "${RUN_OUTPUT_DIR}" -o "${RUN_OUTPUT_DIR}/metrics.csv"

    if [ "${trace_status}" -ne 0 ]; then
        error "One or more traces failed. See ${RUN_LOG} and ${RUN_OUTPUT_DIR}/metrics.csv"
        exit "${trace_status}"
    fi
else
    log "Skipping trace execution. Use -t to run traces."
fi
