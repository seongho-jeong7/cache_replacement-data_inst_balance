#!/usr/bin/env bash
set -euo pipefail

ORIGINAL_CMD="$(printf '%q ' "$0" "$@")"
ORIGINAL_CMD="${ORIGINAL_CMD% }"
echo "Command: ${ORIGINAL_CMD}"

ARGS=()
while [ "$#" -gt 0 ]; do
    case "$1" in
        -L2C)
            if [ "$#" -lt 2 ]; then
                echo "Option -L2C requires an argument."
                exit 1
            fi
            ARGS+=("-L" "$2")
            shift 2
            ;;
        -L2C=*)
            ARGS+=("-L" "${1#-L2C=}")
            shift
            ;;
        *)
            ARGS+=("$1")
            shift
            ;;
    esac
done
set -- "${ARGS[@]}"

################################################################################
# Configuration
################################################################################

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -z "${PYTHON_BIN:-}" ]; then
    if [ -x "${REPO_ROOT}/.venv/bin/python" ]; then
        PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"
    else
        PYTHON_BIN="python3"
    fi
fi
export MPLCONFIGDIR="${MPLCONFIGDIR:-/tmp/matplotlib-${USER:-user}}"
mkdir -p "${MPLCONFIGDIR}"
CHAMPSIM_DIR="${REPO_ROOT}/ChampSim_FDIP"
CONFIG_FILE="${CHAMPSIM_DIR}/champsim_config.json"
TRACES_ROOT="${REPO_ROOT}/traces"
OUTPUT_DIR="${REPO_ROOT}/outputs"
DEFAULT_TRACE_LIST="trace_gtrace_v2_all.txt"
TRACE_LIST="${DEFAULT_TRACE_LIST}"
DEFAULT_FTQ_SIZE=16
ALL_FTQ_SIZES=(2 4 16 32 64)
FTQ_SIZE="${DEFAULT_FTQ_SIZE}"
FTQ_SIZES=("${FTQ_SIZE}")
FTQ_SIZE_OPTION_GIVEN="N"
RUN_ID_OPTION_GIVEN="N"
BASE_CONFIG_SIGNATURE=""
CONFIG_SIGNATURE=""
L2C_POLICY_MASK="0x1"
L2C_POLICY_MASK_OPTION_GIVEN="N"
SELECTED_L2C_POLICIES=()
declare -A L2C_POLICY_BITS=(
    [shared]=1
    [2i6d]=2
    [4i4d]=4
    [6i2d]=8
)
declare -A L2C_POLICY_PARTITION=(
    [shared]=shared
    [2i6d]=static
    [4i4d]=static
    [6i2d]=static
)
declare -A L2C_POLICY_IWAYS=(
    [shared]=4
    [2i6d]=2
    [4i4d]=4
    [6i2d]=6
)
declare -A L2C_POLICY_DWAYS=(
    [shared]=4
    [2i6d]=6
    [4i4d]=4
    [6i2d]=2
)
declare -A L2C_POLICY_SIGNATURES=()
L2C_POLICY_ORDER=(shared 2i6d 4i4d 6i2d)

# Only needed when actually building/running against CHAMPSIM_DIR (i.e. not -s-only
# invocations), so -s can work even if CHAMPSIM_DIR doesn't exist right now.
check_champsim_dir() {
    if [ ! -d "${CHAMPSIM_DIR}" ]; then
        echo "ChampSim directory not found: ${CHAMPSIM_DIR}"
        exit 1
    fi

    if [ ! -f "${CONFIG_FILE}" ]; then
        echo "Config file not found: ${CONFIG_FILE}"
        exit 1
    fi

    BASE_CONFIG_SIGNATURE=""
    if [ "${#FTQ_SIZES[@]}" -gt 1 ]; then
        CONFIG_SIGNATURE="ftqall"
    else
        CONFIG_SIGNATURE="ftq${FTQ_SIZES[0]}"
    fi
}

RUN_ID="$(date +%y%m%d_%H%M)"
RUN_OUTPUT_DIR="${OUTPUT_DIR}/${RUN_ID}"
RUN_LOG="${RUN_OUTPUT_DIR}/run.log"
WARMUP_INSTRUCTIONS=100000
SIMULATION_INSTRUCTIONS=100000
NUM_THREAD=16
BUILD="N"
RUN_TRACES="N"
SUMMARY="N"
SUMMARY_MASK=""
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
    echo " -f [num|a]: set FDIP FTQ size (default: ${DEFAULT_FTQ_SIZE}, use 0 for FDIP off, a for 2/4/16/32/64)"
    echo " -L2C [mask]: select L2C I/D partition binaries to run (default: 0x1). 0x1=shared, 0x2=2:6, 0x4=4:4, 0x8=6:2, 0xf=all"
    echo " -w [num]: set warmup instructions (default: ${WARMUP_INSTRUCTIONS})"
    echo " -i [num]: set simulation instructions (default: ${SIMULATION_INSTRUCTIONS})"
    echo " -r [id]: set run id (default: current timestamp, e.g. ${RUN_ID}). Reusing an id appends to its run.log. With -s, targets that run id instead of the latest one"
    echo " -T [file]: trace list file under ${TRACES_ROOT} to run (one path per line, relative to ${TRACES_ROOT}). Default: ${DEFAULT_TRACE_LIST}"
    echo " -b: configure and build ChampSim"
    echo " -t: run traces"
    echo " -s [mask]: generate summary for the selected -f value. mask is a decimal or 0x-prefixed hex bitmask (1=summary table [MPKIs], 2=fdip cover, 4=hit map, 8=minimal summary table [Trace Set/Group/Total/OK/Fail/Avg IPC/L1I MPKI/L1D MPKI only], 0x10=fdip summary table [Trace Set/Group/Total/OK/Fail/FDIP Cov/L1I Miss only], 0x20=frontend stall summary table [Trace Set/Group/Total/OK/Fail/Avg IPC/L1I MPKI/L1I Stall%/NoFetch%/BackendFull% only]; e.g. 7=1+2+4, -s 0x10). Unknown higher bits are ignored"
    echo ""
    echo "Defaults:"
    echo " champsim dir: ${CHAMPSIM_DIR}"
    echo " config: ${CONFIG_FILE}"
    echo " config signature: ${CONFIG_SIGNATURE}"
    echo " ftq size: ${FTQ_SIZE}"
    echo " run id: ${RUN_ID}"
    echo " traces root: ${TRACES_ROOT}"
    echo " trace list: ${TRACE_LIST}"
    echo " output: ${OUTPUT_DIR}/YYMMDD_HHMM/raw/fdip_<num>/<l2c_policy>/<trace_root>/<trace_group>/<config_signature>-ftq<num>-<l2c_policy>---<trace_file>.log"
    echo " metrics: ${OUTPUT_DIR}/YYMMDD_HHMM/summary/fdip_<num>/<l2c_policy>/metrics.csv"
    exit
}

################################################################################
# Functions
################################################################################

find_traces() {
    grep -v '^[[:space:]]*$' "${TRACES_ROOT}/${TRACE_LIST}"
}

select_l2c_policies() {
    if ! [[ "${L2C_POLICY_MASK}" =~ ^(0[xX][0-9a-fA-F]+|[0-9]+)$ ]] || [ "$(( L2C_POLICY_MASK ))" -eq 0 ]; then
        echo "Invalid L2C policy mask: ${L2C_POLICY_MASK}"
        echo "Use -L2C <mask>: 0x1=shared, 0x2=2:6, 0x4=4:4, 0x8=6:2, 0xf=all."
        exit 1
    fi

    SELECTED_L2C_POLICIES=()
    for policy in "${L2C_POLICY_ORDER[@]}"; do
        if [ $(( L2C_POLICY_MASK & L2C_POLICY_BITS[${policy}] )) -ne 0 ]; then
            SELECTED_L2C_POLICIES+=("${policy}")
        fi
    done
}

policy_label() {
    case "$1" in
        shared) echo "shared" ;;
        2i6d) echo "2:6" ;;
        4i4d) echo "4:4" ;;
        6i2d) echo "6:2" ;;
        *) echo "$1" ;;
    esac
}

policy_binary() {
    echo "${CHAMPSIM_DIR}/bin/champsim_l2c$1"
}

prepare_policy_config() {
    local policy="$1"
    local config_out="$2"
    local executable="champsim_l2c${policy}"
    local partition="${L2C_POLICY_PARTITION[${policy}]}"
    local iways="${L2C_POLICY_IWAYS[${policy}]}"
    local dways="${L2C_POLICY_DWAYS[${policy}]}"

    "${PYTHON_BIN}" - "${CONFIG_FILE}" "${config_out}" "${executable}" "${partition}" "${iways}" "${dways}" <<'PY'
import json
import re
import sys
from pathlib import Path

config_in, config_out, executable, partition, iways, dways = sys.argv[1:]
iways = int(iways)
dways = int(dways)

with open(config_in, encoding="utf-8") as fp:
    cfg = json.load(fp)

cfg["executable_name"] = executable
l2c = cfg.setdefault("L2C", {})
l2c["partition"] = partition
l2c["instruction_ways"] = iways
l2c["data_ways"] = dways

Path(config_out).write_text(json.dumps(cfg, indent=4) + "\n", encoding="utf-8")

cpu = (cfg.get("ooo_cpu") or [{}])[0]
l2c_partition_sig = f"l2c{iways}i{dways}d" if partition == "static" else "l2cshared"
parts = [
    cpu.get("branch_predictor", "no"),
    cpu.get("btb", "no"),
    cfg.get("L1I", {}).get("prefetcher", "no"),
    cfg.get("L1D", {}).get("prefetcher", "no"),
    l2c.get("prefetcher", "no"),
    l2c_partition_sig,
    cfg.get("LLC", {}).get("prefetcher", "no"),
    cfg.get("LLC", {}).get("replacement", "no"),
    f"{cfg.get('num_cores', 1)}core",
]

signature = "-".join(str(part) for part in parts)
print(re.sub(r"[^A-Za-z0-9_.-]+", "_", signature))
PY
}

prepare_selected_policy_configs() {
    local config_dir="${RUN_OUTPUT_DIR}/configs"
    mkdir -p "${config_dir}"
    for policy in "${SELECTED_L2C_POLICIES[@]}"; do
        local generated_config="${config_dir}/champsim_l2c${policy}.json"
        L2C_POLICY_SIGNATURES["${policy}"]="$(prepare_policy_config "${policy}" "${generated_config}")"
    done
}

prepare_all_policy_configs() {
    local config_dir="${RUN_OUTPUT_DIR}/configs"
    mkdir -p "${config_dir}"
    for policy in "${L2C_POLICY_ORDER[@]}"; do
        local generated_config="${config_dir}/champsim_l2c${policy}.json"
        L2C_POLICY_SIGNATURES["${policy}"]="$(prepare_policy_config "${policy}" "${generated_config}")"
    done
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

while getopts ":hvp:f:L:w:i:r:T:bts:" opt; do
    case "${opt}" in
        h) print_help ;;
        v) VERBOSE="Y" ;;
        p) NUM_THREAD="${OPTARG}" ;;
        f)
            FTQ_SIZE="${OPTARG}"
            FTQ_SIZE_OPTION_GIVEN="Y"
            if [ "${FTQ_SIZE}" = "a" ]; then
                CONFIG_SIGNATURE="${BASE_CONFIG_SIGNATURE}-ftqall"
            else
                CONFIG_SIGNATURE="${BASE_CONFIG_SIGNATURE}-ftq${FTQ_SIZE}"
            fi
            ;;
        L)
            L2C_POLICY_MASK="${OPTARG}"
            L2C_POLICY_MASK_OPTION_GIVEN="Y"
            ;;
        w) WARMUP_INSTRUCTIONS="${OPTARG}" ;;
        i) SIMULATION_INSTRUCTIONS="${OPTARG}" ;;
        r)
            RUN_ID="${OPTARG}"
            RUN_ID_OPTION_GIVEN="Y"
            ;;
        T) TRACE_LIST="${OPTARG}" ;;
        b) BUILD="Y" ;;
        t) RUN_TRACES="Y" ;;
        s)
            SUMMARY="Y"
            SUMMARY_MASK="${OPTARG}"
            ;;
        :)
            case "${OPTARG}" in
                s)
                    echo "Option -s requires a mask argument: 1=summary table, 2=fdip cover, 4=hit map (e.g. -s 7 for all, -s 3 for summary+cover)."
                    ;;
                *)
                    echo "Option -${OPTARG} requires an argument."
                    ;;
            esac
            exit 1
            ;;
        *) print_help ;;
    esac
done

################################################################################
# Body
################################################################################

if [ "${SUMMARY}" != "Y" ]; then
    check_champsim_dir
fi

if ! [[ "${NUM_THREAD}" =~ ^[1-9][0-9]*$ ]]; then
    echo "Invalid thread count: ${NUM_THREAD}"
    exit 1
fi

if ! [[ "${WARMUP_INSTRUCTIONS}" =~ ^[0-9]+$ ]]; then
    echo "Invalid warmup instructions: ${WARMUP_INSTRUCTIONS}"
    exit 1
fi

if ! [[ "${SIMULATION_INSTRUCTIONS}" =~ ^[0-9]+$ ]]; then
    echo "Invalid simulation instructions: ${SIMULATION_INSTRUCTIONS}"
    exit 1
fi

if ! [[ "${RUN_ID}" =~ ^[A-Za-z0-9_.-]+$ ]]; then
    echo "Invalid run id: ${RUN_ID}"
    exit 1
fi
RUN_OUTPUT_DIR="${OUTPUT_DIR}/${RUN_ID}"
RUN_LOG="${RUN_OUTPUT_DIR}/run.log"

if [ ! -f "${TRACES_ROOT}/${TRACE_LIST}" ]; then
    echo "Trace list file not found: ${TRACES_ROOT}/${TRACE_LIST}"
    exit 1
fi

if [ "${SUMMARY}" = "Y" ]; then
    if ! [[ "${SUMMARY_MASK}" =~ ^(0[xX][0-9a-fA-F]+|[0-9]+)$ ]] || [ "$(( SUMMARY_MASK ))" -eq 0 ]; then
        echo "Invalid summary mask: ${SUMMARY_MASK}"
        echo "Use -s <mask> where mask is a decimal or 0x-prefixed hex bitmask: 1=summary table, 2=fdip cover, 4=hit map, 8=minimal summary table (Trace Set/Group/Total/OK/Fail/Avg IPC/L1I MPKI/L1D MPKI only), 0x10=fdip summary table (Trace Set/Group/Total/OK/Fail/FDIP Cov/L1I Miss only), 0x20=frontend stall summary table (Trace Set/Group/Total/OK/Fail/Avg IPC/L1I MPKI/L1I Stall%/NoFetch%/BackendFull% only) (e.g. -s 7 for 1+2+4, -s 0x10 for fdip table). Bits above 0x20 are ignored."
        exit 1
    fi
    do_summary_table=$(( SUMMARY_MASK & 1 ))
    do_cover=$(( SUMMARY_MASK & 2 ))
    do_hitmap=$(( SUMMARY_MASK & 4 ))
    do_minimal_table=$(( SUMMARY_MASK & 8 ))
    do_fdip_table=$(( SUMMARY_MASK & 0x10 ))
    do_frontend_table=$(( SUMMARY_MASK & 0x20 ))
    echo "Summary mask: ${SUMMARY_MASK} (summary table: $([ "${do_summary_table}" -ne 0 ] && echo on || echo off), fdip cover: $([ "${do_cover}" -ne 0 ] && echo on || echo off), hit map: $([ "${do_hitmap}" -ne 0 ] && echo on || echo off), minimal summary table: $([ "${do_minimal_table}" -ne 0 ] && echo on || echo off), fdip summary table: $([ "${do_fdip_table}" -ne 0 ] && echo on || echo off), frontend stall summary table: $([ "${do_frontend_table}" -ne 0 ] && echo on || echo off))"
fi

if ! [[ "${FTQ_SIZE}" =~ ^[0-9]+$ ]]; then
    if [ "${FTQ_SIZE}" = "a" ]; then
        FTQ_SIZES=("${ALL_FTQ_SIZES[@]}")
    else
        echo "Invalid FTQ size: ${FTQ_SIZE}"
        exit 1
    fi
else
    FTQ_SIZES=("${FTQ_SIZE}")
fi

select_l2c_policies

if [ "${#FTQ_SIZES[@]}" -gt 1 ]; then
    CONFIG_SIGNATURE="ftqall"
else
    CONFIG_SIGNATURE="ftq${FTQ_SIZES[0]}"
fi

if [ "${SUMMARY}" = "Y" ]; then
    if [ "${RUN_ID_OPTION_GIVEN}" = "Y" ]; then
        latest_run="${RUN_OUTPUT_DIR}"
        if [ ! -d "${latest_run}" ]; then
            echo "Run directory not found: ${latest_run}"
            exit 1
        fi
    else
        latest_run="$(find "${OUTPUT_DIR}" -mindepth 1 -maxdepth 1 -type d | sort | tail -n 1)"
        if [ "${latest_run}" = "" ]; then
            echo "No run directory found under ${OUTPUT_DIR}"
            exit 1
        fi
    fi
    if [ "${FTQ_SIZE_OPTION_GIVEN}" = "Y" ] && [ "${FTQ_SIZE}" != "a" ]; then
        SUMMARY_FTQ_SIZES=("${FTQ_SIZE}")
    else
        mapfile -t SUMMARY_FTQ_SIZES < <(
            find "${latest_run}/raw" -mindepth 1 -maxdepth 1 -type d -name 'fdip_*' 2>/dev/null \
                | sed 's#.*/fdip_##' \
                | sort -n
        )
    fi

    if [ "${#SUMMARY_FTQ_SIZES[@]}" -eq 0 ]; then
        echo "No raw fdip output found under ${latest_run}/raw"
        exit 1
    fi

    for ftq_size in "${SUMMARY_FTQ_SIZES[@]}"; do
        latest_raw="${latest_run}/raw/fdip_${ftq_size}"
        if [ ! -d "${latest_raw}" ]; then
            echo "Raw output directory not found: ${latest_raw}"
            exit 1
        fi

        policy_entries=()
        for policy in "${SELECTED_L2C_POLICIES[@]}"; do
            if [ -d "${latest_raw}/${policy}" ]; then
                policy_entries+=("${policy}:${latest_raw}/${policy}:${latest_run}/summary/fdip_${ftq_size}/${policy}")
            fi
        done
        if [ "${#policy_entries[@]}" -eq 0 ]; then
            policy_entries+=("legacy:${latest_raw}:${latest_run}/summary/fdip_${ftq_size}")
        fi

        for policy_entry in "${policy_entries[@]}"; do
            policy="${policy_entry%%:*}"
            rest="${policy_entry#*:}"
            latest_policy_raw="${rest%%:*}"
            latest_summary="${rest#*:}"
            latest_metrics="${latest_summary}/metrics.csv"
            mkdir -p "${latest_summary}"

            if [ "${do_summary_table}" -ne 0 ] || [ "${do_minimal_table}" -ne 0 ] || [ "${do_fdip_table}" -ne 0 ] || [ "${do_frontend_table}" -ne 0 ]; then
                echo "Generating metrics: ${latest_metrics}"
                "${PYTHON_BIN}" "${REPO_ROOT}/parser/parse_outputs.py" "${latest_policy_raw}" -o "${latest_metrics}"
            fi

            if [ "${do_cover}" -ne 0 ]; then
                echo "Generating FDIP cover: ${latest_summary}/fdip_${ftq_size}_${policy}.png"
                "${PYTHON_BIN}" "${REPO_ROOT}/parser/fdip/cover/fdip_cover.py" \
                    "${latest_policy_raw}" \
                    -o "fdip_${ftq_size}_${policy}" \
                    --output-dir "${latest_summary}" \
                    --quiet
            fi

            if [ "${do_hitmap}" -ne 0 ]; then
                for suite_dir in "${latest_policy_raw}"/*/; do
                    [ -d "${suite_dir}" ] || continue
                    suite_name="$(basename "${suite_dir}")"
                    echo "Generating hit map: ${latest_summary}/${suite_name}_hitmap.png"
                    "${PYTHON_BIN}" "${REPO_ROOT}/parser/fdip/hit_map.py" \
                        "${suite_dir}" \
                        -o "${suite_name}_hitmap" \
                        --output-dir "${latest_summary}" \
                        --quiet
                done
            fi

            if [ "${do_summary_table}" -ne 0 ] || [ "${do_minimal_table}" -ne 0 ] || [ "${do_fdip_table}" -ne 0 ] || [ "${do_frontend_table}" -ne 0 ]; then
                echo ""
                echo "FDIP ftq_size=${ftq_size}, L2C=$(policy_label "${policy}")"
            fi
            if [ "${do_summary_table}" -ne 0 ]; then
                "${PYTHON_BIN}" "${REPO_ROOT}/parser/summary.py" "${latest_metrics}"
            fi
            if [ "${do_minimal_table}" -ne 0 ]; then
                "${PYTHON_BIN}" "${REPO_ROOT}/parser/summary.py" "${latest_metrics}" --minimal
            fi
            if [ "${do_fdip_table}" -ne 0 ]; then
                "${PYTHON_BIN}" "${REPO_ROOT}/parser/summary.py" "${latest_metrics}" --fdip
            fi
            if [ "${do_frontend_table}" -ne 0 ]; then
                "${PYTHON_BIN}" "${REPO_ROOT}/parser/summary.py" "${latest_metrics}" --frontend
            fi
        done
    done

    if [ "${do_cover}" -ne 0 ]; then
        "${PYTHON_BIN}" "${REPO_ROOT}/parser/fdip/cover/make_one_g.py" \
            --summary-dir "${latest_run}/summary" \
            --output "${latest_run}/summary/fdip_breakdown_combined.png"
    fi
    exit
fi

mkdir -p "${RUN_OUTPUT_DIR}"
cp "${CONFIG_FILE}" "${RUN_OUTPUT_DIR}/config.json"
prepare_all_policy_configs
{
    for policy in "${L2C_POLICY_ORDER[@]}"; do
        printf '%s %s\n' "${policy}" "${L2C_POLICY_SIGNATURES[${policy}]}"
    done
} > "${RUN_OUTPUT_DIR}/config_signature.txt"
printf '%s\n' "${FTQ_SIZES[@]}" > "${RUN_OUTPUT_DIR}/ftq_sizes.txt"
touch "${RUN_LOG}"
log "Command: ${ORIGINAL_CMD}"
echo "Run log: ${RUN_LOG}"
log "Run log: ${RUN_LOG}"

if [ "${BUILD}" = "Y" ]; then
    for policy in "${L2C_POLICY_ORDER[@]}"; do
        generated_config="${RUN_OUTPUT_DIR}/configs/champsim_l2c${policy}.json"
        log "Configuring ChampSim L2C $(policy_label "${policy}") with ${generated_config}"
        cd "${CHAMPSIM_DIR}"
        ./config.sh "${generated_config}" >> "${RUN_LOG}" 2>&1
        make >> "${RUN_LOG}" 2>&1
        cd "${REPO_ROOT}"
    done
else
    log "Skipping configure/build. Use -b to configure and build ChampSim."
fi

for policy in "${SELECTED_L2C_POLICIES[@]}"; do
    binary="$(policy_binary "${policy}")"
    if [ ! -x "${binary}" ]; then
        echo "ChampSim binary not found for L2C $(policy_label "${policy}"): ${binary}"
        echo "Run with -b to build all L2C policy binaries."
        exit 1
    fi
done

if [ "${RUN_TRACES}" = "Y" ]; then
    mapfile -t TRACE_FILES < <(find_traces)

    if [ "${#TRACE_FILES[@]}" -eq 0 ]; then
        error "No traces listed in ${TRACES_ROOT}/${TRACE_LIST}"
        exit 1
    fi

    total_jobs=$((${#TRACE_FILES[@]} * ${#FTQ_SIZES[@]} * ${#SELECTED_L2C_POLICIES[@]}))
    log "Running ${#TRACE_FILES[@]} trace(s) x ${#FTQ_SIZES[@]} FTQ setting(s) x ${#SELECTED_L2C_POLICIES[@]} L2C setting(s) = ${total_jobs} job(s) with ${NUM_THREAD} thread(s)."
    for ftq_size in "${FTQ_SIZES[@]}"; do
        for policy in "${SELECTED_L2C_POLICIES[@]}"; do
            mkdir -p "${RUN_OUTPUT_DIR}/raw/fdip_${ftq_size}/${policy}"
        done
    done
    log "Run output directory: ${RUN_OUTPUT_DIR}"
    log "FTQ size(s): ${FTQ_SIZES[*]}"
    log "L2C policy mask: ${L2C_POLICY_MASK} (${SELECTED_L2C_POLICIES[*]})"
    export CHAMPSIM_DIR TRACES_ROOT RUN_OUTPUT_DIR RUN_LOG WARMUP_INSTRUCTIONS SIMULATION_INSTRUCTIONS
    trace_status=0
    {
        for policy in "${SELECTED_L2C_POLICIES[@]}"; do
            for ftq_size in "${FTQ_SIZES[@]}"; do
                for trace_file in "${TRACE_FILES[@]}"; do
                    printf "%s\t%s\t%s\t%s\0" \
                        "${policy}" \
                        "${L2C_POLICY_SIGNATURES[${policy}]}" \
                        "${ftq_size}" \
                        "${trace_file}"
                done
            done
        done
    } | xargs -0 -n 1 -P "${NUM_THREAD}" bash -c '
        job="$1"
        policy="${job%%	*}"
        rest="${job#*	}"
        base_config_signature="${rest%%	*}"
        rest="${rest#*	}"
        ftq_size="${rest%%	*}"
        trace_rel="${rest#*	}"
        trace_abs="${TRACES_ROOT}/${trace_rel}"
        trace_root="${trace_rel%%/*}"
        trace_rest="${trace_rel#*/}"
        trace_group="$(dirname "${trace_rest}")"
        trace_name="$(basename "${trace_rel}")"
        champsim_binary="${CHAMPSIM_DIR}/bin/champsim_l2c${policy}"

        trace_name="${trace_name//[^A-Za-z0-9_.-]/_}"
        trace_root="${trace_root//[^A-Za-z0-9_.-]/_}"
        trace_group="${trace_group//[^A-Za-z0-9_.-]/_}"
        config_signature="${base_config_signature}-ftq${ftq_size}-${policy}"
        output_dir="${RUN_OUTPUT_DIR}/raw/fdip_${ftq_size}/${policy}/${trace_root}/${trace_group}"
        output_file="${output_dir}/${config_signature}---${trace_name}.log"
        mkdir -p "${output_dir}"

        echo "Running trace: ${trace_abs}" >> "${RUN_LOG}"
        echo "FTQ size: ${ftq_size}" >> "${RUN_LOG}"
        echo "L2C policy: ${policy}" >> "${RUN_LOG}"
        "${champsim_binary}" \
            --warmup-instructions "${WARMUP_INSTRUCTIONS}" \
            --simulation-instructions "${SIMULATION_INSTRUCTIONS}" \
            --ftq_size "${ftq_size}" \
            "${trace_abs}" > "${output_file}" 2>&1
        status=$?
        if [ "${status}" -ne 0 ]; then
            message="Failed trace: ${trace_abs} (exit ${status})"
            echo "${message}" | tee -a "${RUN_LOG}" >&2
            echo "${message}" >> "${output_file}"
            exit "${status}"
        fi
        echo "Saved output to ${output_file}" >> "${RUN_LOG}"
    ' _ || trace_status=$?

    if [ "${trace_status}" -ne 0 ]; then
        error "One or more traces failed. See ${RUN_LOG}. Run with -s to generate a summary."
        exit "${trace_status}"
    fi
    log "Trace run complete. Use -s to generate the summary."
else
    log "Skipping trace execution. Use -t to run traces."
fi
