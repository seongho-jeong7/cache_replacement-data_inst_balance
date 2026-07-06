# cache_replacement-data_inst_balance

## Current Status
- `ChampSim/`: [ChampSim](https://github.com/ChampSim/ChampSim) 저장소를 git submodule로 연결
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
- DPC4: https://github.com/CMU-SAFARI/DPC4
- DPC4_traces: https://console.cloud.google.com/storage/browser/dpc4-all-traces
