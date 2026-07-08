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
- `daily/`: 일별 연구 노트 작성 공간
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
scripts/setup_champsim.sh
```

현재 `scripts/setup_champsim.sh`는 `ChampSim/` 디렉터리를 대상으로 submodule 초기화, vcpkg bootstrap, vcpkg install을 수행한다. `ChampSim_DPC4/` 또는 `ChampSim_FDIP/`를 대상으로 준비 작업을 할 때는 각 디렉터리의 구성에 맞게 별도로 확인해야 한다.

실험 실행 스크립트는 루트 `config/` 폴더의 복사본이 아니라, `CHAMPSIM_DIR/champsim_config.json`을 직접 사용한다.

```bash
git submodule update --init
vcpkg/bootstrap-vcpkg.sh
vcpkg/vcpkg install
```

## Run Script

실험 실행 스크립트는 다음 파일이다.

```bash
scripts/run.sh
```

기본값은 스크립트 상단에 정의한다.

- ChampSim directory: `scripts/run.sh` 상단의 `CHAMPSIM_DIR`
- config: `${CHAMPSIM_DIR}/champsim_config.json`
- traces root: `traces/` (고정)
- trace list: `traces/trace_gtrace_v2_all.txt` (기본값, `-T`로 다른 목록 파일 지정 가능)
- run id: 현재 타임스탬프 (`YYMMDD_HHMM`)
- output: `outputs/<run id>/`
- raw output: `outputs/<run id>/raw/fdip_<num>/<trace_root>/<trace_group>/`
- summary output: `outputs/<run id>/summary/fdip_<num>/` (`-s <mask>`를 실행해야 생성됨)
- warmup instructions: `100000`
- simulation instructions: `100000`
- parallel jobs: `16`
- default FTQ size: `16`

주요 옵션은 다음과 같다.

```bash
scripts/run.sh -h
scripts/run.sh -b
scripts/run.sh -t
scripts/run.sh -b -t
scripts/run.sh -p 8 -t
scripts/run.sh -f 0 -t
scripts/run.sh -f a -t
scripts/run.sh -f 16 -s 7
scripts/run.sh -f a -s 7
scripts/run.sh -s 7
scripts/run.sh -w 20000000 -i 100000000 -t
scripts/run.sh -r my_run -t
scripts/run.sh -r my_run -s 7
scripts/run.sh -T trace_gtrace_yankee.txt -t
scripts/run.sh -s 4
```

- `-b`: `${CHAMPSIM_DIR}/config.sh ${CHAMPSIM_DIR}/champsim_config.json`와 `make`를 수행한다.
- `-t`: trace 실행을 수행한다.
- `-p <num>`: trace 병렬 실행 개수를 지정한다. 기본값은 16이다. `-f a`를 사용할 때도 전체 `(FTQ size, trace)` 작업 중 동시에 실행할 개수의 상한으로 동작한다.
- `-f <num|a>`: FDIP FTQ size를 지정한다. `0`이면 FDIP off, `0`보다 크면 FDIP on이다. `a`를 지정하면 `2, 4, 16, 32, 64`를 같은 run 안에서 실행한다. 기본값은 16이다.
- `-w <num>`: warmup instructions 수를 지정한다. 기본값은 100000이다.
- `-i <num>`: simulation instructions 수를 지정한다. 기본값은 100000이다.
- `-r <id>`: run id를 지정한다. 기본값은 실행 시점의 타임스탬프(`YYMMDD_HHMM`)다. 이미 존재하는 run id를 다시 지정하면 `run.log`를 덮어쓰지 않고 이어서 기록한다. `-s`와 같이 쓰면 `-s`도 최신 run 대신 이 run id를 대상으로 한다.
- `-T <file>`: 실행할 trace 목록 파일을 지정한다. `traces/` 바로 아래에 있는 파일명만 받는다(예: `-T trace_gtrace_yankee.txt` → 실제로는 `traces/trace_gtrace_yankee.txt`를 읽음). 생략하면 기본값 `trace_gtrace_v2_all.txt`를 사용한다. 파일은 한 줄에 하나씩, `traces/` 기준 상대경로로 trace를 적는다(예: `gtrace_v2/yankee/yankee_0035.champsim.gz`).
- `-s <mask>`: 선택된 run(`-r` 지정 시 해당 run, 아니면 `outputs/` 아래 가장 최신 run)에서 선택된 `-f` 값의 summary를 생성한다. `mask`는 비트마스크 필수 인자다 — `1`=summary table(`metrics.csv`+표), `2`=FDIP cover, `4`=hit map. 여러 개를 합치려면 더하면 된다(`3`=summary+cover, `7`=전부). 정의되지 않은 상위 비트는 무시한다(`15`를 줘도 `7`과 동일). 값을 생략하거나 잘못 주면(`0`, 숫자가 아닌 값 등) 에러와 함께 비트 의미를 다시 안내한다. `-f a -s 7`은 `fdip_2`, `fdip_4`, `fdip_16`, `fdip_32`, `fdip_64` summary를 차례대로 생성/출력한다.

`-b`를 주지 않으면 config 설정과 build는 생략한다. `-t`를 주지 않으면 trace 실행은 생략한다.

`-t`는 `-T`로 지정한(또는 기본) trace 목록 파일에 적힌 trace만 실행하고 `raw/fdip_<num>/<trace_root>/<trace_group>/` 아래에 로그를 남긴다. 여기서 `<trace_root>`와 `<trace_group>`은 목록 파일에 적힌 경로를 `/`로 나눠서 정한다 — 첫 세그먼트가 `<trace_root>`(예: `gtrace_v2`, `gtrace_v2_new`), 그 다음이 파일 바로 위 디렉터리인 `<trace_group>`(예: `yankee`, `sierra.a.4`)이다. `summary/`는 이 시점에는 만들어지지 않는다 — metrics 집계와 그래프 생성은 `-s`를 실행할 때만 이루어진다. trace 중 일부가 실패해도 나머지 trace는 계속 진행하고, 실패한 trace는 `run.log`에 `Failed trace: ...`로 기록된다.

`-s`는 대상 run의 `raw/fdip_<num>/`을 기준으로 `summary/fdip_<num>/`을 생성하며, `mask`에 따라 다음을 선택적으로 수행한다.

- **summary table (bit `1`)**: `summary/fdip_<num>/metrics.csv`가 없으면 `parser/parse_outputs.py`를 호출해 생성한 뒤, `parser/summary.py`로 그룹별 요약 표를 출력한다.
- **FDIP cover (bit `2`)**: `parser/fdip/cover/fdip_cover.py`를 실행해 `summary/fdip_<num>/fdip_<num>.png`/`.txt`를 생성한다. 모든 FTQ size 처리가 끝나면 `parser/fdip/cover/make_one_g.py`로 `summary/fdip_breakdown_combined.png`(FTQ size 비교 그래프)도 만든다.
- **hit map (bit `4`)**: 대상 run의 `raw/fdip_<num>/` 바로 아래에 있는 suite(trace_root) 디렉터리마다(현재는 보통 `gtrace_v2` 하나) `parser/fdip/hit_map.py`를 실행해 그 suite에 속한 모든 trace를 하나로 합친 `summary/fdip_<num>/<suite>_hitmap.png`/`.txt`를 생성한다. 개별 trace나 FTQ size별이 아니라 suite 전체(=한 trace_root 아래 모든 trace_group) 총합이라는 점에 유의한다.

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
        └── gtrace_v2/
            └── yankee/
                └── bimodal-basic_btb-no-no-no-no-lru-1core-ftq16---yankee_0082.champsim.gz.log
```

이 상태에서 `scripts/run.sh -r 260706_1545 -s 7`(또는 같은 세션이라 최신 run이라면 `scripts/run.sh -s 7`)를 실행하면 `summary/`가 추가된다.

```text
outputs/260706_1545/
├── ...
└── summary/
    ├── fdip_breakdown_combined.png
    └── fdip_16/
        ├── fdip_16.png
        ├── fdip_16.txt
        ├── gtrace_v2_hitmap.png
        ├── gtrace_v2_hitmap.txt
        └── metrics.csv
```

`config.json`에는 실행 당시 사용한 `${CHAMPSIM_DIR}/champsim_config.json`의 복사본이 저장된다. `config_signature.txt`에는 현재 config를 요약한 문자열이 저장된다. 현재 기본 설정의 signature는 다음과 같은 형태다.

```text
bimodal-basic_btb-no-no-no-no-lru-1core
```

실행 중 전체 진행 내용은 `run.log`에 저장한다. 화면에는 실행 커맨드, run log 위치, 실패 trace 등 에러성 메시지만 표시되도록 구성했다. `run.log`에는 실행 커맨드, trace 시작, 저장 위치, build 로그, 실패 메시지가 모두 남는다. 같은 run id로 다시 실행하면 `run.log`는 덮어쓰지 않고 이어서 기록된다 — 즉 `-r`로 같은 run id를 재사용해 trace를 추가로 돌리거나 이어서 실행할 수 있다.

## Parser

trace별 로그를 CSV로 변환하는 파서는 다음 파일이다.

```bash
parser/parse_outputs.py outputs/260706_1545/raw/fdip_16 -o outputs/260706_1545/summary/fdip_16/metrics.csv
```

`scripts/run.sh -s`는 이 파서를 자동으로 호출한다(`-t`는 trace 실행만 하고 파서를 호출하지 않는다). 수동으로 재생성하고 싶을 때만 위 명령을 직접 실행하면 된다.

현재 파서가 추출하는 주요 데이터는 다음과 같다.

- IPC
- instructions
- cycles
- branch accuracy
- branch MPKI
- L1D MPKI
- L2C MPKI
- LLC MPKI
- STLB MPKI
- on-chip traffic MPKI
- off-chip traffic MPKI
- L1D/L2C/LLC/STLB access와 miss count
- 실행 상태: `ok`, `failed`, `incomplete`

FDIP cover/hit map 그래프 생성에는 `matplotlib`, `numpy`, `pandas`가 필요하다. 분석용 의존성은 다음 파일에 정리한다.

```bash
.venv/bin/python -m pip install -r setup/analysis_requirement.txt
```

summary 출력은 다음 명령으로 확인한다.

```bash
scripts/run.sh -s 1
scripts/run.sh -r 260706_1545 -s 1
```

이 명령은 `-r`로 지정한 run(없으면 `outputs/` 아래 최신 run)에서 선택된 `-f` 값의 `summary/fdip_<num>/metrics.csv`를 생성(또는 재사용)해 trace group별 평균 IPC, MPKI, 실패 개수 등을 표로 보여준다.

summary 표에는 다음 값이 group 단위 평균으로 표시된다.

- 평균 IPC
- branch MPKI
- L1D/L2C/LLC MPKI
- STLB MPKI
- off-chip traffic MPKI
- 전체 trace 수, 성공 수, 실패 수

## Current Notes

`scripts/run.sh`는 더 이상 trace 디렉터리를 직접 스캔하지 않는다. `traces/` 아래의 `trace_*.txt` 목록 파일(`-T`로 선택, 기본값 `trace_gtrace_v2_all.txt`)에 적힌 경로만 실행한다. 목록 파일은 필요에 따라 직접 만들어 쓸 수 있다 — 예를 들어 실패한 trace만 모은 `trace_gtrace_yankee_err.txt`를 만들어 `-T`로 재실행하면 그 trace들만 골라서 돌릴 수 있다.

`traces/gtrace_v2/sierra.a.4/`는 원래 공유 폴더(`/home/seongho/shared/trace_for_champsim/google/sierra.a.4`) 전체를 가리키는 디렉터리 심링크였는데, 그 안의 5개 trace(`_0000/_0004/_0007/_0014/_0022`)가 0바이트로 손상돼 있었다. 지금은 이 심링크를 없애고 `traces/gtrace_v2/sierra.a.4/`를 실제 디렉터리로 바꾼 뒤, 파일 24개 각각을 개별 심링크로 걸었다 — 정상인 19개는 원래 공유 위치를 그대로 가리키고, 손상됐던 5개만 다른 공유 위치(`/home/seongho/shared/dpc4_all_traces/gtrace_v2/sierra.a.4`)의 정상 파일을 가리키도록 했다. 이후 재실행에서 24개 전부 정상 완료를 확인했다.
