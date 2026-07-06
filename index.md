```{include} README.md
```

## Quick Start

ChampSim 실험 설정, 실행, 결과 요약은 `scripts/run.sh`를 사용한다.

```bash
scripts/setup_champsim.sh
scripts/run.sh -b -t
scripts/run.sh -s
```

- `scripts/setup_champsim.sh`: ChampSim submodule과 vcpkg 의존성을 준비한다.
- `scripts/run.sh -b`: `config/config_default.json`로 ChampSim을 configure하고 build한다.
- `scripts/run.sh -t`: `traces/gtrace_v2`의 trace들을 병렬 실행한다.
- `scripts/run.sh -p 8 -t`: trace 실행 병렬 개수를 8개로 지정한다.
- `scripts/run.sh -s`: 최신 `outputs/YYMMDD_HHMM/metrics.csv`를 요약 테이블로 보여준다. `metrics.csv`가 없으면 자동 생성한다.

자세한 실험 환경과 결과 구조는 `docs/experiment_environment.md`에 정리한다.

```{toctree}
:maxdepth: 2
:caption: Contents

daily/index
docs/index
```
