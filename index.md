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
- `scripts/run.sh -b`: `scripts/run.sh` 상단의 `CHAMPSIM_DIR` 안에 있는 `champsim_config.json`로 ChampSim을 configure하고 build한다.
- `scripts/run.sh -t`: `traces/gtrace_v2`의 trace들을 병렬 실행한다.
- `scripts/run.sh -p 8 -t`: trace 실행 병렬 개수를 8개로 지정한다.
- `scripts/run.sh -f 0 -t`: FDIP를 끄고 실행한다. `-f`는 FTQ size이며 0이면 FDIP off, 0보다 크면 FDIP on이다.
- `scripts/run.sh -f a -t`: FTQ size `2, 4, 16, 32, 64`를 같은 run 안에서 실행한다.
- `scripts/run.sh -f 16 -s`: 최신 `outputs/YYMMDD_HHMM/summary/fdip_16/metrics.csv`를 요약 테이블로 보여준다. `metrics.csv`가 없으면 `raw/fdip_16`에서 자동 생성한다.

자세한 실험 환경과 결과 구조는 `docs/experiment_environment.md`에 정리한다.

```{toctree}
:maxdepth: 1
:caption: Daily

daily/2026-07-06
daily/2026-07-07
```

```{toctree}
:maxdepth: 2
:caption: Docs

docs/overview
docs/experiment_environment
docs/champsim_fdip_diff
```
