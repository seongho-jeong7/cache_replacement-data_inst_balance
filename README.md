# Balanced L2 Cache

## Current Status
- `ChampSim/`: [ChampSim](https://github.com/ChampSim/ChampSim) 저장소를 git submodule로 연결
- `ChampSim_DPC4/`: [CMU-SAFARI/champsim](https://github.com/CMU-SAFARI/champsim) 기반 DPC4 ChampSim
- `ChampSim_FDIP/`: [seongho-jeong7/ChampSim_FDIP](https://github.com/seongho-jeong7/ChampSim_FDIP.git) 저장소를 git submodule로 연결, ChampSim `ae8924d` base
- `ChampSim_FDIP_ideal/`: [FDIP_for_experiment](https://github.com/inwookan/FDIP_for_experiment.git) 저장소를 git submodule로 연결, ChampSim `ae8924d` base, made by [@inwookan](https://github.com/inwookan)
- `ChampSim_FDIP_dirty/`: [FDIP_260204](https://github.com/inwookan/FDIP_260204.git) 저장소를 git submodule로 연결, forked from DPC4 `6513c5c`, made by [@inwookan](https://github.com/inwookan)
- `ChampSim_Split/`: 최신 ChampSim 계열에 L2I/L2D split 구조를 적용한 submodule. FDIP 구현/버그 영향 없이 L2 분리 자체의 효과를 보기 위해 만들었다.
- `ChampSim_DPC4_Split/`: DPC4 계열에 같은 split 구조를 적용한 submodule. Berti/Pythia 등 DPC4 쪽 prefetcher를 함께 실험하기 위해 사용한다.
- `scripts/run.sh`: ChampSim build/run/summary를 관리하는 메인 실행 스크립트. 기본 ChampSim 디렉터리는 `ChampSim_FDIP`이며, `-C`로 변경할 수 있다. `-f <mask>`로 FDIP FTQ 후보, `-L2C <mask>`로 L2C I/D policy 후보, `-w`/`-i`로 warmup/simulation instruction 수, `-r`로 run id, `-T`로 trace 목록 파일(`traces/` 기준)을 지정한다. `-f`/`-L2C`를 생략하면 해당 옵션을 binary/config에 넘기지 않고 현재 ChampSim 설정 그대로 실행한다.
- `outputs/`: 실험 결과 저장 위치. run id(`-r` 미지정 시 타임스탬프)별로 `outputs/<run id>/raw/fdip_<ftq>/<l2c_policy>/`에 trace 로그가 쌓이고, `scripts/run.sh -s <mask>` 실행 시 `outputs/<run id>/summary/fdip_<ftq>/<l2c_policy>/`에 metrics와 분석 결과가 생성된다. `-f`/`-L2C`를 생략한 실행은 `fdip_0/default` 아래에 저장된다.
- `docs/daily/`: 일별 연구 노트 작성 공간
- `docs/`: 연구 관련 문서 작성 공간
- `traces/`: ChampSim trace 파일을 배치하는 위치. 실제 trace는 `traces/gtrace_v2/...`, `traces/Graph/...`처럼 하위 폴더에 두고, 실행할 trace 목록은 `traces/trace_*.txt` 파일로 작성한다. `trace_*.txt`에는 `traces/` 기준 상대경로를 한 줄에 하나씩 적고, `scripts/run.sh -T <file>`로 선택한다

## Quick Start

```bash
scripts/setup_champsim.sh -C ChampSim_FDIP
scripts/run.sh -b -t
scripts/run.sh -s 0x41
```

- `scripts/setup_champsim.sh -C ChampSim_FDIP`: 지정한 ChampSim 디렉터리의 submodule/vcpkg 의존성을 준비한다. `-C`는 필수다.
- `scripts/setup_champsim.sh -C ChampSim_FDIP_ideal`: 지정한 ChampSim 디렉터리를 준비한다. 대상에 `vcpkg/`가 없으면 `ChampSim/vcpkg`를 준비한 뒤 symlink로 연결한다.
- `scripts/run.sh -b`: 선택된 ChampSim 디렉터리의 `champsim_config.json`로 configure/build한다.
- `scripts/run.sh -t`: trace 목록을 실행한다. 기본 trace 목록은 `traces/trace_gtrace_v2_all.txt`다.
- `scripts/run.sh -C ChampSim_FDIP -b -t`: 사용할 ChampSim 디렉터리를 명시한다.
- `scripts/run.sh -f 0xff -L2C 0x7f -t`: 모든 FTQ 후보와 모든 L2C policy 후보를 실행한다.
- `scripts/run.sh -T trace_gtrace_l2c_test.txt -f 0x31 -L2C 0x7f -t`: L2C 실험용 trace 목록에서 `ftq0/32/64`와 모든 L2C policy를 실행한다.
- `scripts/run.sh -r <run_id> -s 0x41`: 지정한 run의 `metrics.csv`를 생성하고 summary table을 출력한다.
- `scripts/run.sh -r <run_id> -L2C 0x7f -s 0xC0`: L2C policy 비교용 metrics와 delta graph/csv를 생성한다.

자세한 옵션은 아래 명령으로 확인한다.

```bash
scripts/run.sh -h
scripts/run.sh -D
```

## Traces

`scripts/run.sh`는 trace 디렉터리를 자동 스캔하지 않고, `traces/` 아래의 trace list txt 파일을 읽어서 실행한다.

준비해야 하는 것:

1. 실제 ChampSim trace 파일을 `traces/` 아래에 둔다.
2. 실행할 trace 목록을 `traces/trace_*.txt` 파일로 만든다.
3. 목록 파일에는 `traces/` 기준 상대경로를 한 줄에 하나씩 적는다.

예:

```text
gtrace_v2/yankee/yankee_0000.champsim.gz
gtrace_v2/yankee/yankee_0001.champsim.gz
gtrace_v2/arizona/arizona_0000.champsim.gz
```

실행:

```bash
scripts/run.sh -T trace_gtrace_l2c_test.txt -t
```

## Docs

Sphinx 기반 문서 환경을 사용합니다.

```bash
make setup
make html
```

빌드 결과는 `html/` 폴더에 생성됩니다.

## Ref
- ChampSim: <https://github.com/ChampSim/ChampSim>
- CMU-SAFARI/champsim: <https://github.com/CMU-SAFARI/champsim>
- DPC4: <https://github.com/CMU-SAFARI/DPC4>
- DPC4_traces: <https://console.cloud.google.com/storage/browser/dpc4-all-traces>
- ChampSim_FDIP: <https://github.com/seongho-jeong7/ChampSim_FDIP.git>
- FDIP_for_experiment: <https://github.com/inwookan/FDIP_for_experiment.git> (made by [@inwookan](https://github.com/inwookan))
- FDIP_260204: <https://github.com/inwookan/FDIP_260204.git> (made by [@inwookan](https://github.com/inwookan))
- ChampSim_Split: <https://github.com/seongho-jeong7/ChampSim_Split.git>
- ChampSim_DPC4_Split: <https://github.com/seongho-jeong7/ChampSim_DPC4_Split.git>
