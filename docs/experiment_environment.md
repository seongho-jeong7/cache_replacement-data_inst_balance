# Experiment Environment

이 문서는 현재 저장소에 구축한 ChampSim 실험 환경과 문서화 환경을 정리한다.

## Directory Layout

- `ChampSim/`: 일반 ChampSim 원본 저장소를 git submodule로 연결한 위치
- `ChampSim_DPC4/`: DPC4 기반 ChampSim 위치
- `ChampSim_FDIP/`: FDIP 구현을 확인하고 비교하기 위한 별도 연구용 ChampSim 위치
- `*/champsim_config.json`: 각 ChampSim 디렉터리 안에서 직접 관리하는 설정 파일. 루트 `config/` 폴더는 더 이상 사용하지 않는다.
- `traces/`: DPC4 또는 gtrace 계열 trace를 배치하는 위치. `scripts/run.sh`가 실행할 trace 목록을 적어두는 `trace_*.txt` 파일도 이 폴더 바로 아래에 둔다(`-T`가 참조하는 위치)
- `scripts/`: 환경 준비와 실험 실행 스크립트 위치
- `outputs/`: 실험 결과 로그와 파싱 결과가 저장되는 위치
- `parser/`: ChampSim 출력 로그를 CSV와 summary로 변환하는 파서 위치
- `docs/daily/`: 일별 연구 노트 작성 공간
- `docs/`: 연구 관련 문서 작성 공간

## Documentation

Sphinx와 MyST Markdown을 사용한다. 루트의 `index.md`는 `README.md`를 include하므로, README 수정 내용이 문서 대문에 자동 반영된다.

문서 환경 의존성은 `setup/sphinx_requierment.txt`에 둔다.

```bash
make setup
make html
```

빌드 결과는 `html/`에 생성된다. 현재 정적 문서는 `screen` 세션으로 9179 포트에서 확인할 수 있도록 구성했다.

## ChampSim Setup

ChampSim 의존성 준비용 스크립트는 다음 파일이다.

```bash
scripts/setup_champsim.sh -C <champsim_dir>
```

`-C`는 필수다. setup 대상 ChampSim 디렉터리를 명시적으로 지정해야 한다.

```bash
scripts/setup_champsim.sh -C ChampSim
scripts/setup_champsim.sh -C ChampSim_FDIP
scripts/setup_champsim.sh -C ChampSim_FDIP_ideal
scripts/setup_champsim.sh -C ChampSim_FDIP_dirty
```

동작은 다음과 같다.

- 선택한 ChampSim 디렉터리에서 `git submodule update --init`을 실행한다.
- 선택한 디렉터리에 `vcpkg/`가 있으면 그 vcpkg를 직접 사용한다.
- 선택한 디렉터리에 `vcpkg/`가 없으면 `ChampSim/vcpkg`를 먼저 준비하고, 선택한 디렉터리의 `vcpkg`로 symbolic link를 만든다.
- 마지막으로 선택한 디렉터리에서 `vcpkg/vcpkg install`을 실행해 해당 디렉터리의 `vcpkg.json` manifest를 기준으로 dependency를 설치한다.

실험 실행 스크립트는 루트 `config/` 폴더의 복사본이 아니라, `CHAMPSIM_DIR/champsim_config.json`을 직접 사용한다.

## Run Script

실험 실행 스크립트는 다음 파일이다.

```bash
scripts/run.sh
```

현재 기본값과 상세 경로는 다음 명령으로 확인한다.

```bash
scripts/run.sh -D
```

현재 주요 기본값은 다음과 같다.

- ChampSim directory: `ChampSim_FDIP`
- config: `${CHAMPSIM_DIR}/champsim_config.json`
- traces root: `traces/` (고정)
- trace list: `traces/trace_gtrace_v2_all.txt` (기본값, `-T`로 다른 목록 파일 지정 가능)
- run id: 현재 타임스탬프 (`YYMMDD_HHMM`)
- output: `outputs/<run id>/`
- raw output: `outputs/<run id>/raw/fdip_<num>/<l2c_policy>/<trace_root>/<trace_group>/`
- summary output: `outputs/<run id>/summary/fdip_<num>/<l2c_policy>/` (`-s <mask>`를 실행해야 생성됨)
- warmup instructions: `100000`
- simulation instructions: `100000`
- parallel jobs: `16`
- default FTQ mask: `0xff` (현재 정의된 FTQ 전체)
- default L2C policy mask: `0x1` (`shared`)

주요 옵션은 다음과 같다.

```bash
scripts/run.sh -h
scripts/run.sh -D
scripts/run.sh -b
scripts/run.sh -t
scripts/run.sh -b -t
scripts/run.sh -p 8 -t
scripts/run.sh -f 0x01 -t
scripts/run.sh -f 0xff -t
scripts/run.sh -L2C 0x7f -t
scripts/run.sh -f 0x15 -L2C 0x7f -t
scripts/run.sh -f 0x15 -L2C 0x7f -s 0x40
scripts/run.sh -f 0x15 -L2C 0x7f -s 0xC0
scripts/run.sh -w 20000000 -i 100000000 -t
scripts/run.sh -r my_run -t
scripts/run.sh -r my_run -f 0xff -L2C 0x7f -s 0xC0
scripts/run.sh -T trace_gtrace_yankee.txt -t
scripts/run.sh -C ChampSim_FDIP -b -t
```

- `-h`: help를 출력한다.
- `-D`: 현재 default path와 output 구조를 출력한다.
- `-C <dir>`: 사용할 ChampSim directory를 지정한다. 상대경로는 repository root 기준으로 해석하고, 절대경로도 사용할 수 있다. 기본값은 `ChampSim_FDIP`이다.
- `-b`: `${CHAMPSIM_DIR}/config.sh ${CHAMPSIM_DIR}/champsim_config.json`와 `make`를 수행한다. 현재 스크립트 구조상 build 단계에서는 `shared`, `0i8d`, `1i7d`, `2i6d`, `4i4d`, `6i2d`, `8i0d` policy별 binary를 준비한다.
- `-t`: trace 실행을 수행한다.
- `-p <num>`: trace 병렬 실행 개수를 지정한다. 기본값은 16이다. 전체 `(FTQ size, L2C policy, trace)` job 중 동시에 실행할 개수의 상한으로 동작한다.
- `-f <mask>`: FDIP FTQ size set을 16진 bitmask로 지정한다. `0x` prefix가 필수다. 기존의 `-f 0`, `-f 16`, `-f a` 방식은 더 이상 사용하지 않는다.
- `-L2C <mask>`: L2C instruction/data partition policy set을 bitmask로 지정한다.
- `-w <num>`: warmup instructions 수를 지정한다. 기본값은 100000이다.
- `-i <num>`: simulation instructions 수를 지정한다. 기본값은 100000이다.
- `-r <id>`: run id를 지정한다. 기본값은 실행 시점의 타임스탬프(`YYMMDD_HHMM`)다. 이미 존재하는 run id를 다시 지정하면 `run.log`를 덮어쓰지 않고 이어서 기록한다. `-s`와 같이 쓰면 `-s`도 최신 run 대신 이 run id를 대상으로 한다.
- `-T <file>`: 실행할 trace 목록 파일을 지정한다. `traces/` 바로 아래에 있는 파일명만 받는다(예: `-T trace_gtrace_yankee.txt` → 실제로는 `traces/trace_gtrace_yankee.txt`를 읽음). 생략하면 기본값 `trace_gtrace_v2_all.txt`를 사용한다. 파일은 한 줄에 하나씩, `traces/` 기준 상대경로로 trace를 적는다(예: `gtrace_v2/yankee/yankee_0035.champsim.gz`).
- `-s <mask>`: 선택된 run(`-r` 지정 시 해당 run, 아니면 `outputs/` 아래 가장 최신 run)에서 선택된 `-f`/`-L2C` 값의 summary를 생성한다. `mask`는 비트마스크 필수 인자로, 10진수 또는 `0x` 붙인 16진수 둘 다 받는다. 정의되지 않은 상위 비트는 무시한다. 값을 생략하거나 잘못 주면 에러와 함께 비트 의미를 다시 안내한다. 각 표의 정확한 컬럼 구성과 계산식은 [`docs/champsim_summary_analysis.md`](champsim_summary_analysis.md)에 정리했다.

FTQ mask는 다음과 같다.

```text
0x01 ftq0/off
0x02 ftq2
0x04 ftq4
0x08 ftq16
0x10 ftq32
0x20 ftq64
0x1f ftq0/2/4/16/32
0x3f all
0xff all
```

주의: 현재 `ftq8`은 정의되어 있지 않다. `ftq8`을 돌리려면 `scripts/run.sh`의 FTQ mask table과 ChampSim build/config 생성 경로에 FTQ 8을 추가해야 한다.

L2C policy mask는 다음과 같다.

```text
0x01 shared
0x02 0i8d
0x04 1i7d
0x08 2i6d
0x10 4i4d
0x20 6i2d
0x40 8i0d
0x7f all
```

`0i8d`는 instruction-origin access가 L2C search/fill을 bypass하고 LLC로 바로 가는 control policy다. `8i0d`는 data-origin access에 같은 bypass를 적용한다. `1i7d`, `2i6d`, `4i4d`, `6i2d`는 L2C 8-way를 instruction/data way 범위로 정적으로 나누며, 현재 모델에서는 자기 partition way 수만큼 search latency를 지불한다.

Summary mask는 다음과 같다.

```text
0x01 summary table (MPKIs)
0x02 FDIP cover analysis
0x04 hit map
0x08 minimal summary table
0x10 FDIP summary table
0x20 frontend stall summary table
0x40 (re)generate metrics.csv
0x80 L2C partition delta-vs-shared grid
```

중요한 변경점:

- `0x40`은 `metrics.csv`를 생성/재생성하는 비트다.
- `0x01`, `0x08`, `0x10`, `0x20`, `0x80`은 `metrics.csv`를 읽어 사용한다.
- 따라서 summary 표나 L2C delta 그래프를 처음 만들 때는 먼저 `0x40`을 포함하는 것이 안전하다.
- 예: `-s 0xC0`은 `metrics.csv` 재생성과 L2C delta 그래프 생성을 함께 수행한다.

`-b`를 주지 않으면 config 설정과 build는 생략한다. `-t`를 주지 않으면 trace 실행은 생략한다.

`-t`는 `-T`로 지정한(또는 기본) trace 목록 파일에 적힌 trace만 실행하고 `raw/fdip_<num>/<l2c_policy>/<trace_root>/<trace_group>/` 아래에 로그를 남긴다. 여기서 `<trace_root>`와 `<trace_group>`은 목록 파일에 적힌 경로를 `/`로 나눠서 정한다 — 첫 세그먼트가 `<trace_root>`(예: `gtrace_v2`), 그 다음이 파일 바로 위 디렉터리인 `<trace_group>`(예: `yankee`, `sierra.a.4`)이다. `summary/`는 이 시점에는 만들어지지 않는다 — metrics 집계와 그래프 생성은 `-s`를 실행할 때만 이루어진다. trace 중 일부가 실패해도 나머지 trace는 계속 진행하고, 실패한 trace는 `run.log`에 `Failed trace: ...`로 기록된다.

`-s`는 대상 run의 `raw/fdip_<num>/<l2c_policy>/`을 기준으로 `summary/fdip_<num>/<l2c_policy>/`을 생성하며, `mask`에 따라 다음을 선택적으로 수행한다.

- **summary table (bit `0x01`)**: `summary/fdip_<num>/<l2c_policy>/metrics.csv`를 읽어 `parser/summary.py`로 그룹별 요약 표를 출력한다.
- **FDIP cover (bit `0x02`)**: `parser/fdip/cover/fdip_cover.py`를 실행해 `summary/fdip_<num>/<l2c_policy>/fdip_<num>_<l2c_policy>.png`/`.txt`를 생성한다. 모든 FTQ/policy 처리가 끝나면 `parser/fdip/cover/make_one_g.py`로 `summary/fdip_breakdown_combined.png`도 만든다.
- **hit map (bit `0x04`)**: 대상 run의 `raw/fdip_<num>/<l2c_policy>/` 아래 suite(trace_root) 디렉터리마다 `parser/fdip/hit_map.py`를 실행해 suite 단위 hit map을 만든다.
- **minimal summary (bit `0x08`)**: Trace Set/Group/Total/OK/Fail/Avg IPC/L1I MPKI/L1D MPKI 중심의 축소 표를 출력한다.
- **FDIP summary (bit `0x10`)**: FDIP coverage와 L1I miss 중심 표를 출력한다.
- **frontend stall summary (bit `0x20`)**: Avg IPC, L1I MPKI, L1I Stall%, NoFetch%, BackendFull% 중심 표를 출력한다.
- **metrics generation (bit `0x40`)**: `parser/parse_outputs.py`를 호출해 `metrics.csv`를 생성/재생성한다.
- **L2C delta grid (bit `0x80`)**: `parser/l2c/delta_grid.py`를 호출해 shared 대비 L2C partition 변화량 CSV/그래프를 만든다. `-L2C 0x7f`처럼 shared 외 policy가 같이 선택되어 있어야 의미가 있다.

스크립트를 실행하면 가장 먼저 실행에 사용된 커맨드 라인 전체(`Command: scripts/run.sh ...`)를 화면과 `run.log` 맨 앞에 기록한 뒤 나머지 작업을 시작한다.

## Output Structure

실행 결과는 run id 단위 폴더로 저장한다. run id는 기본적으로 실행 시점의 타임스탬프(`YYMMDD_HHMM`)이지만, `-r <id>`로 직접 지정할 수 있다.

`-t`만 실행한 직후에는 `raw/`만 있고 `summary/`는 아직 없다. `-s`를 실행해야 `summary/`와 그 안의 ftq별 폴더가 생긴다.

```text
outputs/260706_1545/
├── config.json
├── config_signature.txt
├── ftq_sizes.txt
├── run.log
└── raw/
    └── fdip_16/
        └── shared/
            └── gtrace_v2/
                └── yankee/
                    └── bimodal-basic_btb-no-no-no-no-lru-1core-ftq16-shared---yankee_0082.champsim.gz.log
```

이 상태에서 `scripts/run.sh -r 260706_1545 -f 0x08 -L2C 0x01 -s 0x47`(metrics 생성 + summary table + FDIP cover + hit map)을 실행하면 `summary/`가 추가된다.

```text
outputs/260706_1545/
├── ...
└── summary/
    ├── fdip_breakdown_combined.png
    └── fdip_16/
        └── shared/
            ├── fdip_16_shared.png
            ├── fdip_16_shared.txt
            ├── gtrace_v2_hitmap.png
            ├── gtrace_v2_hitmap.txt
            └── metrics.csv
```

L2C partition sweep을 함께 돌리면 같은 `fdip_<num>/` 아래 policy별 폴더가 생긴다.

```text
outputs/<run_id>/
├── raw/
│   ├── fdip_0/
│   │   ├── shared/
│   │   ├── 0i8d/
│   │   ├── 1i7d/
│   │   ├── 2i6d/
│   │   ├── 4i4d/
│   │   ├── 6i2d/
│   │   └── 8i0d/
│   └── fdip_32/
│       └── ...
└── summary/
    ├── l2c_delta_combined.png
    ├── l2c_delta_grid.png
    ├── l2c_delta_pct.csv
    ├── l2c_delta_raw.csv
    ├── l2c_raw_values.csv
    └── fdip_32/
        ├── shared/
        ├── 0i8d/
        ├── 1i7d/
        ├── 2i6d/
        ├── 4i4d/
        ├── 6i2d/
        └── 8i0d/
```

`config.json`에는 실행 당시 사용한 `${CHAMPSIM_DIR}/champsim_config.json`의 복사본이 저장된다. `config_signature.txt`에는 현재 config를 요약한 문자열이 저장된다. 현재 기본 설정의 signature는 다음과 같은 형태다.

```text
bimodal-basic_btb-no-no-no-no-lru-1core
```

실행 중 전체 진행 내용은 `run.log`에 저장한다. 화면에는 실행 커맨드, run log 위치, 실패 trace 등 에러성 메시지만 표시되도록 구성했다. `run.log`에는 실행 커맨드, trace 시작, 저장 위치, build 로그, 실패 메시지가 모두 남는다. 같은 run id로 다시 실행하면 `run.log`는 덮어쓰지 않고 이어서 기록된다 — 즉 `-r`로 같은 run id를 재사용해 trace를 추가로 돌리거나 이어서 실행할 수 있다.

## Parser

trace별 로그를 CSV로 변환하는 파서는 다음 파일이다.

```bash
parser/parse_outputs.py \
  outputs/260706_1545/raw/fdip_16/shared \
  -o outputs/260706_1545/summary/fdip_16/shared/metrics.csv
```

`scripts/run.sh -s 0x40`은 이 파서를 자동으로 호출한다(`-t`는 trace 실행만 하고 파서를 호출하지 않는다). 수동으로 재생성하고 싶을 때만 위 명령을 직접 실행하면 된다.

현재 파서가 추출하는 주요 데이터는 다음과 같다.

- IPC
- instructions
- cycles
- branch accuracy
- branch MPKI
- L1I MPKI
- L1D MPKI
- L2I/L2D split MPKI
- L2C MPKI
- LLI/LLD split MPKI
- LLC MPKI
- STLB MPKI
- on-chip traffic MPKI
- off-chip traffic MPKI
- L1I/L1D/L2C/LLC/STLB access와 miss count
- L2C/LLC instruction/data origin split count
- FDIP coverage 관련 count와 percentage
- frontend stall breakdown
- ROB/LQ/SQ/backend stall breakdown
- `frontend_instruction_fetch_stall`
- `backend_instruction_stall`
- `backend_data_stall`
- 실행 상태: `ok`, `failed`, `incomplete`

FDIP cover/hit map 그래프 생성에는 `matplotlib`, `numpy`, `pandas`가 필요하다. 분석용 의존성은 다음 파일에 정리한다.

```bash
.venv/bin/python -m pip install -r setup/analysis_requirement.txt
```

summary 출력은 다음 명령으로 확인한다.

```bash
scripts/run.sh -s 0x41
scripts/run.sh -r 260706_1545 -f 0x08 -L2C 0x01 -s 0x41
```

이 명령은 `-r`로 지정한 run(없으면 `outputs/` 아래 최신 run)에서 선택된 `-f`/`-L2C` 값의 `metrics.csv`를 생성하고, trace group별 평균 IPC, MPKI, 실패 개수 등을 표로 보여준다.

summary 표에는 다음 값이 group 단위 평균으로 표시된다.

- 평균 IPC
- branch MPKI
- L1I/L1D/L2C/LLC MPKI
- L2I/L2D, LLI/LLD split MPKI
- STLB MPKI
- off-chip traffic MPKI
- 전체 trace 수, 성공 수, 실패 수

## Current Notes

`scripts/run.sh`는 더 이상 trace 디렉터리를 직접 스캔하지 않는다. `traces/` 아래의 `trace_*.txt` 목록 파일(`-T`로 선택, 기본값 `trace_gtrace_v2_all.txt`)에 적힌 경로만 실행한다. 목록 파일은 필요에 따라 직접 만들어 쓸 수 있다 — 예를 들어 실패한 trace만 모은 `trace_gtrace_yankee_err.txt`를 만들어 `-T`로 재실행하면 그 trace들만 골라서 돌릴 수 있다.

현재 L2C partition 실험용 trace list는 `traces/trace_gtrace_l2c_test.txt`다. 이 파일은 `bravo`, `delta`, `merced`, `sierra.a.4`, `sierra.a.6`, `tahoe`, `tango`, `yankee` 8개 group의 296개 trace를 포함한다.

`traces/gtrace_v2/sierra.a.4/`는 원래 공유 폴더(`/home/seongho/shared/trace_for_champsim/google/sierra.a.4`) 전체를 가리키는 디렉터리 심링크였는데, 그 안의 5개 trace(`_0000/_0004/_0007/_0014/_0022`)가 0바이트로 손상돼 있었다. 지금은 이 심링크를 없애고 `traces/gtrace_v2/sierra.a.4/`를 실제 디렉터리로 바꾼 뒤, 파일 24개 각각을 개별 심링크로 걸었다 — 정상인 19개는 원래 공유 위치를 그대로 가리키고, 손상됐던 5개만 다른 공유 위치(`/home/seongho/shared/dpc4_all_traces/gtrace_v2/sierra.a.4`)의 정상 파일을 가리키도록 했다. 이후 재실행에서 24개 전부 정상 완료를 확인했다.
