# Cache Replacement Policy 연구: L2의 Data, Instruction 크기 Balance

## Current Status
- `ChampSim/`: [ChampSim](https://github.com/ChampSim/ChampSim) 저장소를 git submodule로 연결
- `ChampSim_DPC4/`: [CMU-SAFARI/champsim](https://github.com/CMU-SAFARI/champsim) 기반 DPC4 ChampSim
- `ChampSim_FDIP/`: [seongho-jeong7/ChampSim_FDIP](https://github.com/seongho-jeong7/ChampSim_FDIP.git) 저장소를 git submodule로 연결, ChampSim `ae8924d` base
- `ChampSim_FDIP_ideal/`: [FDIP_for_experiment](https://github.com/inwookan/FDIP_for_experiment.git) 저장소를 git submodule로 연결, ChampSim `ae8924d` base, made by @inwookan
- `ChampSim_FDIP_dirty/`: [FDIP_260204](https://github.com/inwookan/FDIP_260204.git) 저장소를 git submodule로 연결, forked from DPC4 `6513c5c`, made by @indookan
- `scripts/run.sh`: 상단의 `CHAMPSIM_DIR` 안에 있는 `champsim_config.json`을 사용해 실행. `-w`/`-i`로 warmup/simulation instruction 수, `-r`로 run id를 지정할 수 있다. `-t`는 trace만 실행하고, `-s`를 실행해야 summary가 생성된다
- `outputs/`: 실험 결과 저장 위치. run id(`-r` 미지정 시 타임스탬프)별로 `outputs/<run id>/raw/fdip_<ftq>/`에 trace 로그가 쌓이고, `scripts/run.sh -s` 실행 시 `outputs/<run id>/summary/fdip_<ftq>/`에 metrics와 FDIP cover 그래프가 생성된다
- `daily/`: 일별 연구 노트 작성 공간
- `docs/`: 연구 관련 문서 작성 공간
- `traces/`: DPC4 traces 다운로드 필요

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
- FDIP_for_experiment: <https://github.com/inwookan/FDIP_for_experiment.git> (made by @inwookan)
- FDIP_260204: <https://github.com/inwookan/FDIP_260204.git> (made by @indookan)
