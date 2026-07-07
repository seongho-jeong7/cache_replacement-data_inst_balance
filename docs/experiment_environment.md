# Experiment Environment

이 문서는 현재 저장소에 구축한 ChampSim 실험 환경과 문서화 환경을 정리한다.

## Directory Layout

- `ChampSim/`: 일반 ChampSim 원본 저장소를 git submodule로 연결한 위치
- `ChampSim_DPC4/`: DPC4 기반 ChampSim 위치
- `ChampSim_FDIP/`: FDIP 구현을 확인하고 비교하기 위한 별도 연구용 ChampSim 위치
- `*/champsim_config.json`: 각 ChampSim 디렉터리 안에서 직접 관리하는 설정 파일. 루트 `config/` 폴더는 더 이상 사용하지 않는다.
- `traces/`: DPC4 또는 gtrace 계열 trace를 배치하는 위치
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
- trace: `traces/gtrace_v2`
- output: `outputs/YYMMDD_HHMM/`
- raw output: `outputs/YYMMDD_HHMM/raw/fdip_<num>/`
- summary output: `outputs/YYMMDD_HHMM/summary/fdip_<num>/`
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
scripts/run.sh -f 16 -s
scripts/run.sh -f a -s
scripts/run.sh -s
scripts/run.sh -w 20000000 -i 100000000 -t
```

- `-b`: `${CHAMPSIM_DIR}/config.sh ${CHAMPSIM_DIR}/champsim_config.json`와 `make`를 수행한다.
- `-t`: trace 실행을 수행한다.
- `-p <num>`: trace 병렬 실행 개수를 지정한다. 기본값은 16이다. `-f a`를 사용할 때도 전체 `(FTQ size, trace)` 작업 중 동시에 실행할 개수의 상한으로 동작한다.
- `-f <num|a>`: FDIP FTQ size를 지정한다. `0`이면 FDIP off, `0`보다 크면 FDIP on이다. `a`를 지정하면 `2, 4, 16, 32, 64`를 같은 run 안에서 실행한다. 기본값은 16이다.
- `-w <num>`: warmup instructions 수를 지정한다. 기본값은 100000이다.
- `-i <num>`: simulation instructions 수를 지정한다. 기본값은 100000이다.
- `-s`: 최신 run 폴더에서 선택된 `-f` 값의 `metrics.csv`를 요약 테이블로 출력한다. `-f a -s`는 `fdip_2`, `fdip_4`, `fdip_16`, `fdip_32`, `fdip_64` summary를 차례대로 출력한다.

`-b`를 주지 않으면 config 설정과 build는 생략한다. `-t`를 주지 않으면 trace 실행은 생략한다.

`-t` 실행이 끝나면 현재 run 폴더의 `summary/fdip_<num>/metrics.csv`를 자동 생성한다. `-f a`를 사용하면 각 FTQ size별로 `summary/fdip_2`, `summary/fdip_4`, `summary/fdip_16`, `summary/fdip_32`, `summary/fdip_64` 아래에 각각 `metrics.csv`를 만든다. trace 중 일부가 실패해도 생성된 로그를 기준으로 `metrics.csv`를 만들고, 실패 trace는 `status=failed`와 실패 이유를 기록한다.

`-s`는 `outputs/` 아래 가장 최신 run 폴더를 대상으로 한다. 최신 run 폴더의 `summary/fdip_<num>/metrics.csv`가 없으면 `raw/fdip_<num>`을 대상으로 `parser/parse_outputs.py`를 호출해 자동 생성한 뒤 요약 테이블을 출력한다. 여기서 `<num>`은 `-f` 옵션으로 선택한 FTQ size다.

또한 `-s`는 최신 run 폴더의 `raw/fdip_*` 중 실제 존재하는 항목만 대상으로 `parser/fdip/cover/fdip_cover.py`를 실행한다. 각 FDIP cover 결과는 `summary/fdip_<num>/fdip_<num>.png`와 `summary/fdip_<num>/fdip_<num>.txt`에 저장한다. 이후 `parser/fdip/cover/make_one_g.py`를 실행해 전체 FTQ size 비교 그래프를 `summary/fdip_breakdown_combined.png`에 저장한다.

## Output Structure

실행 결과는 run 단위 폴더로 저장한다.

```text
outputs/260706_1545/
├── config.json
├── config_signature.txt
├── run.log
├── raw/
│   └── fdip_16/
│       └── gtrace_v2/
│           └── yankee/
│               └── bimodal-basic_btb-no-no-no-no-lru-1core-ftq16---yankee_0082.champsim.gz.log
└── summary/
    ├── fdip_breakdown_combined.png
    └── fdip_16/
        ├── fdip_16.png
        ├── fdip_16.txt
        └── metrics.csv
```

`config.json`에는 실행 당시 사용한 `${CHAMPSIM_DIR}/champsim_config.json`의 복사본이 저장된다. `config_signature.txt`에는 현재 config를 요약한 문자열이 저장된다. 현재 기본 설정의 signature는 다음과 같은 형태다.

```text
bimodal-basic_btb-no-no-no-no-lru-1core
```

실행 중 전체 진행 내용은 `run.log`에 저장한다. 화면에는 run log 위치와 실패 trace 등 에러성 메시지만 표시되도록 구성했다. `run.log`에는 trace 시작, 저장 위치, build 로그, 실패 메시지가 모두 남는다.

## Parser

trace별 로그를 CSV로 변환하는 파서는 다음 파일이다.

```bash
parser/parse_outputs.py outputs/260706_1545/raw/fdip_16 -o outputs/260706_1545/summary/fdip_16/metrics.csv
```

`scripts/run.sh -t`와 `scripts/run.sh -s`는 이 파서를 자동으로 호출한다. 수동으로 재생성하고 싶을 때만 위 명령을 직접 실행하면 된다.

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

FDIP cover 그래프 생성에는 `matplotlib`, `numpy`, `pandas`가 필요하다. 분석용 의존성은 다음 파일에 정리한다.

```bash
.venv/bin/python -m pip install -r setup/analysis_requirement.txt
```

summary 출력은 다음 명령으로 확인한다.

```bash
scripts/run.sh -s
```

이 명령은 `outputs/` 아래 최신 run 폴더에서 선택된 `-f` 값의 `summary/fdip_<num>/metrics.csv`를 찾아 trace group별 평균 IPC, MPKI, 실패 개수 등을 표로 보여준다.

summary 표에는 다음 값이 group 단위 평균으로 표시된다.

- 평균 IPC
- branch MPKI
- L1D/L2C/LLC MPKI
- STLB MPKI
- off-chip traffic MPKI
- 전체 trace 수, 성공 수, 실패 수

## Current Notes

`gtrace_v2`는 symlink 디렉터리일 수 있으므로 `scripts/run.sh`는 `find -L`을 사용해 실제 trace 파일을 따라간다.

이전 테스트 실행에서는 `gtrace_v2`의 343개 trace 중 338개가 정상 완료됐고, `sierra.a.4` 계열 5개 trace가 exit 139 segmentation fault로 실패했다.
