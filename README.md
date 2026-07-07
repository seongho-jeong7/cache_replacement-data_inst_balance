# cache_replacement-data_inst_balance

## Current Status
- `ChampSim/`: [ChampSim](https://github.com/ChampSim/ChampSim) 저장소를 git submodule로 연결
- `ChampSim_DPC4/`: [CMU-SAFARI/champsim](https://github.com/CMU-SAFARI/champsim) 기반 DPC4 ChampSim
- `ChampSim_FDIP/`: [seongho-jeong7/ChampSim_FDIP](https://github.com/seongho-jeong7/ChampSim_FDIP.git) 저장소를 git submodule로 연결, ChampSim `ae8924d` base
- `ChampSim_FDIP_ideal/`: [FDIP_for_experiment](https://github.com/inwookan/FDIP_for_experiment.git) 저장소를 git submodule로 연결, ChampSim `ae8924d` base, made by @inwookan
- `ChampSim_FDIP_dirty/`: [FDIP_260204](https://github.com/inwookan/FDIP_260204.git) 저장소를 git submodule로 연결, forked from DPC4 `6513c5c`, made by @indookan
- `scripts/run.sh`: 상단의 `CHAMPSIM_DIR` 안에 있는 `champsim_config.json`을 사용해 실행
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
- ChampSim: https://github.com/ChampSim/ChampSim
- CMU-SAFARI/champsim: https://github.com/CMU-SAFARI/champsim
- DPC4: https://github.com/CMU-SAFARI/DPC4
- DPC4_traces: https://console.cloud.google.com/storage/browser/dpc4-all-traces
- ChampSim_FDIP: https://github.com/seongho-jeong7/ChampSim_FDIP.git
- FDIP_for_experiment: https://github.com/inwookan/FDIP_for_experiment.git (made by @inwookan)
- FDIP_260204: https://github.com/inwookan/FDIP_260204.git (made by @indookan)
