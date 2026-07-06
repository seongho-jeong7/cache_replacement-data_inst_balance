# Experiment Environment

이 문서는 현재 저장소에 구축한 ChampSim 실험 환경과 문서화 환경을 정리한다.

## Directory Layout

- `ChampSim/`: ChampSim 원본 저장소를 git submodule로 연결한 위치
- `config/`: 실험에 사용할 ChampSim 설정 파일을 관리하는 위치
- `config/config_default.json`: `ChampSim/champsim_config.json`에서 복사한 기본 설정
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

스크립트는 저장소 루트에서 submodule을 초기화한 뒤 `ChampSim/` 안에서 vcpkg bootstrap과 install을 수행한다.

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

- config: `config/config_default.json`
- trace: `traces/gtrace_v2`
- output: `outputs/YYMMDD_HHMM/`
- warmup instructions: `100000`
- simulation instructions: `100000`
- parallel jobs: `16`

주요 옵션은 다음과 같다.

```bash
scripts/run.sh -h
scripts/run.sh -b
scripts/run.sh -t
scripts/run.sh -b -t
scripts/run.sh -p 8 -t
scripts/run.sh -s
```

- `-b`: `./config.sh <config>`와 `make`를 수행한다.
- `-t`: trace 실행을 수행한다.
- `-p <num>`: trace 병렬 실행 개수를 지정한다. 기본값은 16이다.
- `-s`: 최신 `metrics.csv`를 요약 테이블로 출력한다.

`-b`를 주지 않으면 config 설정과 build는 생략한다. `-t`를 주지 않으면 trace 실행은 생략한다.

`-t` 실행이 끝나면 현재 run 폴더에 `metrics.csv`를 자동 생성한다. trace 중 일부가 실패해도 생성된 로그를 기준으로 `metrics.csv`를 만들고, 실패 trace는 `status=failed`와 실패 이유를 기록한다.

`-s`는 `outputs/` 아래 가장 최신 run 폴더를 대상으로 한다. 최신 run 폴더에 `metrics.csv`가 없으면 `parser/parse_outputs.py`를 호출해 자동 생성한 뒤 요약 테이블을 출력한다.

## Output Structure

실행 결과는 run 단위 폴더로 저장한다.

```text
outputs/260706_1545/
├── config.json
├── config_signature.txt
├── run.log
├── metrics.csv
└── gtrace_v2/
    └── yankee/
        └── bimodal-basic_btb-no-no-no-no-lru-1core---yankee_0082.champsim.gz.log
```

`config_signature.txt`에는 현재 config를 요약한 문자열이 저장된다. 현재 기본 설정의 signature는 다음과 같은 형태다.

```text
bimodal-basic_btb-no-no-no-no-lru-1core
```

실행 중 전체 진행 내용은 `run.log`에 저장한다. 화면에는 run log 위치와 실패 trace 등 에러성 메시지만 표시되도록 구성했다. `run.log`에는 trace 시작, 저장 위치, build 로그, 실패 메시지가 모두 남는다.

## Parser

trace별 로그를 CSV로 변환하는 파서는 다음 파일이다.

```bash
parser/parse_outputs.py outputs/260706_1545 -o outputs/260706_1545/metrics.csv
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

summary 출력은 다음 명령으로 확인한다.

```bash
scripts/run.sh -s
```

이 명령은 `outputs/` 아래 최신 run 폴더의 `metrics.csv`를 찾아 trace group별 평균 IPC, MPKI, 실패 개수 등을 표로 보여준다.

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
