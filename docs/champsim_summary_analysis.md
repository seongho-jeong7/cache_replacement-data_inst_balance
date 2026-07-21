# ChampSim Summary 분석 가이드

이 문서는 `scripts/run.sh -s <mask>`가 생성하거나 출력하는 summary 결과를 읽는 방법을 정리한다. 원본 ChampSim 로그의 각 항목 의미는 [`champsim_log_analysis.md`](champsim_log_analysis.md)에 따로 정리하고, 여기서는 `parser/parse_outputs.py`가 만든 `metrics.csv`와 그 위에서 동작하는 summary/plot 옵션을 다룬다.

## metrics.csv

`metrics.csv`는 trace 로그를 trace당 한 줄로 압축한 기본 분석 데이터다.

생성 위치:

```text
outputs/<run_id>/summary/fdip_<ftq>/<l2c_policy>/metrics.csv
```

예:

```bash
scripts/run.sh -r 260713_2013_l2c_partition -f 0xff -L2C 0x1f -s 0x40
```

`-s 0x01`, `0x08`, `0x10`, `0x20`, `0x80`은 `metrics.csv`를 읽어서 표나 그림을 만든다. **이 옵션들은 metrics를 자동 생성하지 않는다.** 따라서 새 run을 분석할 때는 보통 `0x40`을 함께 켠다.

예:

```bash
# metrics 생성 + 기본 summary 출력
scripts/run.sh -r <run_id> -s 0x41

# metrics 생성 + L2C delta 그래프 생성
scripts/run.sh -r <run_id> -L2C 0x1f -s 0xC0
```

## 용어 설명

### MPKI

**MPKI**는 **Misses Per Kilo-Instruction**의 약자다. 실행 명령어 1000개당 miss가 몇 번 발생했는지 나타낸다.

```text
MPKI = miss / instructions * 1000
```

값이 낮을수록 해당 cache/TLB 계층이 요청을 더 잘 처리했다는 뜻이다. 다만 모든 MPKI가 같은 종류의 요청을 세는 것은 아니므로, 어떤 access type을 분자로 쓰는지 확인해야 한다.

### Demand MPKI

주요 cache MPKI는 demand traffic을 보기 위해 `LOAD miss + RFO miss`만 사용한다.

```text
demand MPKI = (LOAD miss + RFO miss) / instructions * 1000
```

대상 컬럼:

- `l1d_mpki`
- `l2c_mpki`
- `llc_mpki`

`PREFETCH`, `WRITE`, `TRANSLATION` miss는 제외한다. 즉 이 값은 코어가 직접 필요로 한 load/store 계열 demand miss를 보는 지표다.

### L1I MPKI

`l1i_mpki`는 다음처럼 계산한다.

```text
l1i_mpki = L1I LOAD miss / instructions * 1000
```

L1I는 RFO를 쓰지 않으므로 사실상 LOAD miss만 본다.

주의할 점은 `l1i_mpki`와 FDIP breakdown의 `L1I Miss`는 다른 지표라는 것이다.

- `l1i_mpki`: 명령어 실행량 대비 L1I miss 빈도
- FDIP `L1I Miss`: L1I demand access 중 prefetch 도움을 받지 못한 요청 비율

둘은 분자와 분모가 모두 다르므로 서로 대체할 수 없다.

### L2I/L2D, LLI/LLD MPKI

`ChampSim_FDIP`에는 L2C/LLC 요청이 instruction-fetch 기원인지 data 기원인지 구분하는 계측이 들어 있다. 이 계측이 있는 로그에서는 다음 컬럼을 만들 수 있다.

- `l2i_mpki`: instruction-fetch 기원의 L2C demand MPKI
- `l2d_mpki`: data 기원의 L2C demand MPKI
- `lli_mpki`: instruction-fetch 기원의 LLC demand MPKI
- `lld_mpki`: data 기원의 LLC demand MPKI

계산식은 일반 demand MPKI와 동일하게 `LOAD + RFO` miss를 사용한다.

이 계측이 없는 오래된 바이너리/로그에서는 해당 값이 비어 있을 수 있다.

참고로 실험 코드가 같은 기준으로 split을 기록했다면 일반적으로 아래 관계를 기대할 수 있다.

```text
l2i_mpki + l2d_mpki ~= l2c_mpki
lli_mpki + lld_mpki ~= llc_mpki
```

다만 로그 버전, origin 계측 누락, access type 차이 때문에 문서/실험에서는 항상 실제 `metrics.csv` 값을 기준으로 확인한다.

### Traffic MPKI

`on_chip_traffic_mpki`와 `off_chip_traffic_mpki`는 demand miss가 아니라 LLC 총 traffic을 본다.

```text
on_chip_traffic_mpki  = LLC TOTAL access / instructions * 1000
off_chip_traffic_mpki = LLC TOTAL miss   / instructions * 1000
```

여기에는 `LOAD`, `RFO`, `PREFETCH`, `WRITE`, `TRANSLATION` 등 모든 access type이 포함된다. 따라서 `l2c_mpki`나 `llc_mpki`와 직접 같은 의미로 비교하면 안 된다.

### FDIP Breakdown

FDIP 관련 로그는 `==== L1I Demand Access Breakdown ====` 섹션에서 읽는다.

파싱 대상:

- `L1I Hit (FDIP Covered)`
- `L1I Hit (Non-Prefetch)`
- `L1I Late Prefetch (Merge)`
- `L1I Merge (Non-Prefetch)`
- `L1I Miss`

합계:

```text
fdip_total = fdip_l1i_hit_covered
           + fdip_l1i_hit_non_prefetch
           + fdip_l1i_late_prefetch_merge
           + fdip_l1i_merge_non_prefetch
           + fdip_l1i_miss
```

대표 비율:

```text
FDIP Cov = fdip_l1i_hit_covered / fdip_total * 100
L1I Miss = fdip_l1i_miss        / fdip_total * 100
```

`FDIP Cov`는 L1I demand fetch가 FDIP가 미리 가져온 line에 hit한 비율이다. `L1I Miss`는 L1I demand fetch가 prefetch 도움 없이 새 miss로 처리된 비율이다.

### Frontend Stall

Frontend stall은 fetch에서 decode로 instruction을 넘기지 못한 cycle을 세는 지표다. 로그의 `====Frontend Stall Breakdown====`에서 읽는다.

파싱 대상:

- `L1I_MISS`: instruction fetch가 L1I miss 때문에 막힌 cycle
- `NO_INSTR_TO_FETCH`: fetch할 instruction이 준비되지 않은 cycle
- `BACKEND_FULL`: decode/backend 쪽 queue가 가득 차서 frontend가 더 밀어 넣지 못한 cycle

비율은 전체 cycle 대비로 계산한다.

```text
frontend_stall_l1i_miss_pct          = L1I_MISS / cycles * 100
frontend_stall_no_instr_to_fetch_pct = NO_INSTR_TO_FETCH / cycles * 100
frontend_stall_backend_full_pct      = BACKEND_FULL / cycles * 100
```

현재 실험 문서에서는 `frontend_instruction_fetch_stall_pct`를 `L1I_MISS / cycles * 100`으로 사용한다. 즉 instruction이 준비되지 않아 frontend가 막힌 정도를 보는 대표값이다.

### Backend Stall

Backend stall은 dispatch 이후 instruction이 backend 자원 문제로 진행하지 못한 cycle을 보는 지표다.

로그의 `====Backend Stall Breakdown====`에서 읽는 값:

- `ROB_STALL`
- `LQ_STALL`
- `SQ_STALL`

로그의 `====ROB Stall Breakdown====` 중 `Total` block에서 읽는 값:

- `ADDR_TRANS`
- `REPLAY_LOAD`
- `NON_REPLAY_LOAD`

현재 실험용 결합 지표:

```text
backend_instruction_stall = LQ_STALL + SQ_STALL + ADDR_TRANS + REPLAY_LOAD
backend_data_stall        = NON_REPLAY_LOAD
```

비율은 전체 cycle 대비로 계산한다.

```text
backend_instruction_stall_pct = backend_instruction_stall / cycles * 100
backend_data_stall_pct        = backend_data_stall        / cycles * 100
```

이 분류는 L2C I/D partition 실험에서 instruction side와 data side의 병목 변화를 분리해서 보기 위한 working definition이다.

## 기본 Summary Table (`-s 0x01`)

명령:

```bash
scripts/run.sh -r <run_id> -s 0x41
```

`0x01`은 `parser/summary.py <metrics.csv>`를 실행해 trace set/group 단위의 기본 표를 출력한다. `0x01` 자체는 `metrics.csv`를 만들지 않으므로 새 run에서는 보통 `0x40`과 함께 `0x41`로 실행한다.

출력 컬럼:

- `Trace Set`
- `Group`
- `Total`
- `OK`
- `Fail`
- `Avg IPC`
- `Br MPKI`
- `L1I MPKI`
- `L1D MPKI`
- `L2C MPKI`
- `LLC MPKI`
- `STLB MPKI`

용도:

- 전체 trace group의 실행 성공/실패 상태 확인
- 평균 IPC와 큰 cache/TLB 병목 확인
- 실험 결과를 가장 빠르게 훑어보기

## FDIP Cover Analysis (`-s 0x02`)

명령:

```bash
scripts/run.sh -r <run_id> -s 0x42
```

`0x02`는 `parser/fdip/cover/fdip_cover.py`를 실행해 L1I demand access breakdown을 그림과 텍스트로 저장한다. 새 run에서는 보통 `0x40`과 함께 실행한다.

출력 위치:

```text
outputs/<run_id>/summary/fdip_<ftq>/<l2c_policy>/fdip_<ftq>_<policy>.png
outputs/<run_id>/summary/fdip_<ftq>/<l2c_policy>/fdip_<ftq>_<policy>.txt
```

추가로 `make_one_g.py`가 전체 summary directory를 훑어 통합 그림을 만든다.

```text
outputs/<run_id>/summary/fdip_breakdown_combined.png
```

용도:

- FDIP가 L1I demand access를 얼마나 cover했는지 확인
- FTQ size별로 `FDIP hit`, `base hit`, `merge`, `miss` 비중 비교
- L2C policy별 FDIP coverage 차이 확인

## Hit Map (`-s 0x04`)

명령:

```bash
scripts/run.sh -r <run_id> -s 0x44
```

`0x04`는 `parser/fdip/hit_map.py`를 실행해 hit/miss resolution 위치를 요약한다. 새 run에서는 metrics 생성과 직접 연결되지는 않지만, 통상 같은 분석 흐름에서 `0x40`과 함께 실행할 수 있다.

출력 위치:

```text
outputs/<run_id>/summary/fdip_<ftq>/<l2c_policy>/<trace_set>_hitmap.png
outputs/<run_id>/summary/fdip_<ftq>/<l2c_policy>/<trace_set>_hitmap.txt
```

용도:

- L1I/L1D/L2C/LLC/MEM hit 위치 분포 확인
- STLB miss가 어느 cache/memory level에서 해결되는지 확인
- FDIP나 L2C partition이 hit location을 바꾸는지 확인

## Minimal Summary Table (`-s 0x08`)

명령:

```bash
scripts/run.sh -r <run_id> -s 0x48
```

`0x08`은 `parser/summary.py --minimal`을 실행한다. I/D split MPKI를 빠르게 비교하기 위한 축약 표다.

출력 컬럼:

- `Trace Set`
- `Group`
- `Total`
- `OK`
- `Fail`
- `Avg IPC`
- `L1I MPKI`
- `L1D MPKI`
- `L2I MPKI`
- `L2D MPKI`
- `LLI MPKI`
- `LLD MPKI`

용도:

- instruction side와 data side의 cache pressure 비교
- L2C/LLC I/D split 계측이 잘 들어왔는지 확인
- L2C partition 실험 전 빠른 sanity check

## FDIP Summary Table (`-s 0x10`)

명령:

```bash
scripts/run.sh -r <run_id> -s 0x50
```

`0x10`은 `parser/summary.py --fdip`을 실행한다.

출력 컬럼:

- `Trace Set`
- `Group`
- `Total`
- `OK`
- `Fail`
- `FDIP Cov`
- `L1I Miss`
- `OnChip MPKI`
- `OffChip MPKI`

용도:

- FDIP coverage와 L1I miss 비율 비교
- FDIP가 traffic을 늘리는지 확인
- instruction prefetch 효과와 on/off-chip traffic 부담을 같이 보기

주의:

- 여기의 `L1I Miss`는 FDIP breakdown 비율이다.
- `L1I MPKI`와 의미가 다르다.

## Frontend Stall Summary Table (`-s 0x20`)

명령:

```bash
scripts/run.sh -r <run_id> -s 0x60
```

`0x20`은 `parser/summary.py --frontend`를 실행한다.

출력 컬럼:

- `Trace Set`
- `Group`
- `Total`
- `OK`
- `Fail`
- `Avg IPC`
- `L1I MPKI`
- `L2I MPKI`
- `L2D MPKI`
- `L1I Stall%`
- `NoFetch%`
- `BackendFull%`

용도:

- IPC 변화가 frontend fetch 병목과 연결되는지 확인
- FTQ size 증가가 L1I/L2I MPKI와 frontend stall을 줄이는지 확인
- `BackendFull%`가 높아 frontend 개선이 IPC로 이어지지 않는 workload를 찾기

## Generate Metrics (`-s 0x40`)

명령:

```bash
scripts/run.sh -r <run_id> -s 0x40
```

`0x40`은 `parser/parse_outputs.py`를 실행해 `metrics.csv`를 생성하거나 재생성한다.

동작:

- 기존 `metrics.csv`가 있으면 삭제 후 다시 생성한다.
- `raw/fdip_<ftq>/<l2c_policy>/...` 아래의 `.log` 파일을 모두 파싱한다.
- 각 trace log를 한 줄로 정리한다.

출력 위치:

```text
outputs/<run_id>/summary/fdip_<ftq>/<l2c_policy>/metrics.csv
```

권장 사용:

```bash
# 기본 summary와 함께
scripts/run.sh -r <run_id> -s 0x41

# L2C delta graph 생성 전 metrics 재생성
scripts/run.sh -r <run_id> -L2C 0x1f -s 0xC0
```

## L2C Partition Delta Grid (`-s 0x80`)

명령:

```bash
scripts/run.sh -r <run_id> -L2C 0x1f -s 0xC0
```

`0x80`은 `parser/l2c/delta_grid.py`를 실행해 L2C partition별 변화량을 `shared` 대비로 계산하고 그림/CSV를 만든다. `0x80`은 `metrics.csv`를 읽으므로 보통 `0x40`과 함께 `0xC0`으로 실행한다.

입력 구조:

```text
outputs/<run_id>/summary/fdip_<ftq>/shared/metrics.csv
outputs/<run_id>/summary/fdip_<ftq>/0i8d/metrics.csv
outputs/<run_id>/summary/fdip_<ftq>/2i6d/metrics.csv
outputs/<run_id>/summary/fdip_<ftq>/4i4d/metrics.csv
outputs/<run_id>/summary/fdip_<ftq>/6i2d/metrics.csv
```

출력 파일:

```text
outputs/<run_id>/summary/l2c_delta_grid.png
outputs/<run_id>/summary/l2c_delta_combined.png
outputs/<run_id>/summary/l2c_raw_values.csv
outputs/<run_id>/summary/l2c_delta_raw.csv
outputs/<run_id>/summary/l2c_delta_pct.csv
```

비교 기준:

```text
delta = <policy value> - shared value
```

주요 metric:

- `dIPC (%)`
- `dL1I MPKI`
- `dL2I MPKI`
- `dFrontend Stall%p`
- `dBackend Inst Stall%p`
- `dL1D MPKI`
- `dL2D MPKI`
- `dBackend Data Stall%p`
- `dL2C MPKI`

용도:

- L2C I/D partition이 IPC에 실제 이득을 주는지 확인
- instruction side 개선과 data side 악화가 동시에 생기는지 확인
- `0i8d`, `2i6d`, `4i4d`, `6i2d`를 `shared` 기준으로 비교
- FTQ size별로 L2C partition 효과가 달라지는지 확인

## 자주 쓰는 조합

기본 summary:

```bash
scripts/run.sh -r <run_id> -s 0x41
```

FDIP coverage와 hit map까지 같이 생성:

```bash
scripts/run.sh -r <run_id> -s 0x47
```

Frontend stall 표 생성:

```bash
scripts/run.sh -r <run_id> -s 0x60
```

L2C partition delta graph 생성:

```bash
scripts/run.sh -r <run_id> -L2C 0x1f -s 0xC0
```

여러 표를 한 번에 출력:

```bash
scripts/run.sh -r <run_id> -s 0x79
```

`0x79`는 `0x40(metrics)` + `0x20(frontend)` + `0x10(FDIP)` + `0x08(minimal)` + `0x01(full summary)` 조합이다.
