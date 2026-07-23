# 2026-07-22 Verification: ChampSim_DPC4_Split 동작 검증

이 문서는 `ChampSim_DPC4_Split`의 split L2 구현이 `ChampSim_DPC4` 기준 동작과 일치하는지 검증하기 위한 절차와 결과를 정리한다.

## 목적

`ChampSim_DPC4_Split`은 DPC4 계열 ChampSim에 L2 split 기능을 추가한 저장소다. 검증 목표는 다음과 같다.

- `shared` mode가 원래 `ChampSim_DPC4`와 동일하게 동작하는지 확인한다.
- `2i6d`, `4i4d` 등 split mode는 같은 DPC4 code base 위에서 비교한다.
- `ChampSim_DPC4_Split`의 `L2C.partition=static` parser path가 만든 hierarchy와, `ChampSim_DPC4`에 같은 hierarchy를 수동으로 반영한 결과가 동일한지 확인한다.

## 검증 배경

처음에는 `260722_1228_w10_i100_champ_hard_config_matched_prefetch_2g` 결과를 `ChampSim_DPC4_Split` 결과와 비교하려고 했다. 하지만 이 비교에는 두 가지 문제가 있었다.

`260722_1228_w10_i100_champ_hard_config_matched_prefetch_2g`의 의미:

- `shared`: 원본 `ChampSim`으로 생성
- `2i6d`, `4i4d`: 원본 `ChampSim` config를 강제로 바꿔 생성
- 따라서 `ChampSim_DPC4_Split`과 직접 비교하기에는 base 코드가 다르다.

문제점:

- `shared` baseline은 최신 원본 `ChampSim` 계열 결과였고, `ChampSim_DPC4_Split`은 DPC4 계열이었다.
- `2i6d`, `4i4d` baseline은 config를 직접 강제 구성한 결과였고, `ChampSim_DPC4_Split`의 `L2C.partition=static` parser path와 같은 방식으로 생성된 결과가 아니었다.

이 때문에 결과 차이가 발생했고, 차이의 원인은 split 구현 자체라기보다 `ChampSim`과 `ChampSim_DPC4`의 기본 코드/config 차이로 판단했다.

따라서 검증 방향을 다음과 같이 수정했다.

1. `ChampSim_DPC4` 기준으로 shared 결과를 다시 만든다.
2. `ChampSim_DPC4`에 split 구조를 강제로 반영해 `2i6d`, `4i4d` 결과를 만든다.
3. 이 결과를 `ChampSim_DPC4_Split`에서 `-L2C` 옵션으로 생성한 결과와 비교한다.
4. 두 결과가 완전히 동일하면, `ChampSim_DPC4_Split`의 config-driven split 생성이 수동 split 설정과 동일하게 동작한다고 볼 수 있다.

기존 문서에 있던 `260722_1228` 기준 `2i6d`, `4i4d` 수치 비교와 원인 분석은 검증 근거로 사용하지 않는다. 해당 결과와 분석은 잘못된 base 비교였기 때문이다.

## 구현 기준

`ChampSim_DPC4_Split`의 split 기능은 `L2C.partition` 값을 기준으로 hierarchy를 해석한다.

| mode | parser 동작 | 기대 hierarchy |
|---|---|---|
| `shared` | `L2C.partition=shared`를 읽고 원래 `L2C` cache object 유지 | `L1I/L1D -> L2C -> LLC` |
| `static` | `L2C.instruction_ways`, `L2C.data_ways`를 읽어 `L2I`, `L2D` cache object 생성 | `L1I -> L2I -> LLC`, `L1D -> L2D -> LLC` |

반면 `ChampSim_DPC4` 검증용 baseline은 `ChampSim_split_L2`에서 검증했던 split 구조 diff를 참고해 `L2IC/L2DC`를 직접 만든다. 즉 `ChampSim_DPC4_Split`의 parser 기능 자체를 또 구현하는 것이 아니라, 같은 DPC4 base 위에서 결과가 같아야 하는 수동 static split baseline을 만드는 것이다.

현재 `ChampSim_DPC4`에 반영한 핵심 파일:

- `champsim_config.json`
- `config/defaults.py`
- `config/parse.py`
- `inc/defaults.hpp`

주의: `ChampSim_DPC4/bin/champsim_l2c2i6d`는 이전 빌드 산물이 남아 있을 수 있다. `2i6d` 검증을 실행하기 전에는 반드시 현재 config 상태로 `champsim_l2c2i6d`를 다시 빌드해야 한다.

## 비교 대상

### 기준: ChampSim_DPC4_Split

`ChampSim_DPC4_Split`은 DPC4 계열에 split L2 기능을 parser/config 기반으로 추가한 코드다.

기준 결과:

```text
outputs/260722_1830_w10_i100_dpc4_split_2g
```

비교 대상 summary:

```text
outputs/260722_1830_w10_i100_dpc4_split_2g/summary/fdip_0/shared/metrics.csv
outputs/260722_1830_w10_i100_dpc4_split_2g/summary/fdip_0/2i6d/metrics.csv
outputs/260722_1830_w10_i100_dpc4_split_2g/summary/fdip_0/4i4d/metrics.csv
```

### 검증: ChampSim_DPC4

`ChampSim_DPC4`에 같은 hierarchy를 직접 반영해서 실행한 결과를 비교한다.

검증 결과 폴더:

```text
outputs/verify/260722_1953_w10_i100_dpc4_hard_config_comp_split_2g
```

현재 유효한 결과:

```text
outputs/verify/260722_1953_w10_i100_dpc4_hard_config_comp_split_2g/summary/fdip_0/shared/metrics.csv
```

앞서 잘못 생성했던 `2i6d`, `4i4d` 결과는 base와 config 적용 방식이 틀렸으므로 삭제했다. 이후 `ChampSim_split_L2`의 diff를 기준으로 `ChampSim_DPC4`에 split 구조를 다시 반영한 뒤, `2i6d`부터 재실행한다.

## Shared 검증 결과

`ChampSim_DPC4` shared 결과와 `ChampSim_DPC4_Split` shared 결과는 완전히 일치했다.

비교 파일:

```text
outputs/verify/260722_1953_w10_i100_dpc4_hard_config_comp_split_2g/summary/fdip_0/shared/metrics.csv
outputs/260722_1830_w10_i100_dpc4_split_2g/summary/fdip_0/shared/metrics.csv
```

비교 결과:

| 항목 | 결과 |
|---|---:|
| `ChampSim_DPC4` shared rows | 22 |
| `ChampSim_DPC4_Split` shared rows | 22 |
| common rows | 22 |
| missing rows | 0 |
| status/reason 차이 | 0 |
| numeric columns | 32 |
| numeric changed cells | 0 |
| max numeric delta | 0 |

결론적으로 `shared` mode에서는 `ChampSim_DPC4_Split`이 `ChampSim_DPC4`와 동일하게 동작한다. 즉 split 기능이 꺼진 상태에서는 원래 DPC4 hierarchy를 유지한다고 볼 수 있다.

## 2i6d 재검증

현재 목적은 `ChampSim_DPC4`를 수동 split 구조로 빌드했을 때의 `2i6d` 결과가 `ChampSim_DPC4_Split`의 `-L2C 0x8` 결과와 완전히 동일한지 확인하는 것이다.

적용할 구조:

| 항목 | 설정 |
|---|---|
| L1I lower level | L2IC |
| L1D lower level | L2DC |
| L2IC ways | 2 |
| L2DC ways | 6 |
| L2IC lower level | LLC |
| L2DC lower level | LLC |
| PTW path | 기존 DPC4 구조 유지 |

실행 대상 trace:

```text
traces/trace_gtrace_l2c_test_g2.txt
```

실행 조건:

| 항목 | 값 |
|---|---:|
| warmup | 1,000,000 |
| simulation | 10,000,000 |
| parallel jobs | 28 |
| FTQ option | 미지정 |
| output bucket | `fdip_0` |
| L2C policy folder | `2i6d` |

실행 명령:

빌드:

```bash
./scripts/run.sh \
  -C ChampSim_DPC4 \
  -b \
  -L2C 0x8 \
  -r 260722_1953_w10_i100_dpc4_hard_config_comp_split_2g
```

실행:

```bash
./scripts/run.sh \
  -C ChampSim_DPC4 \
  -t \
  -L2C 0x8 \
  -T trace_gtrace_l2c_test_g2.txt \
  -w 1000000 \
  -i 10000000 \
  -p 28 \
  -r 260722_1953_w10_i100_dpc4_hard_config_comp_split_2g
```

실행 후 생성될 비교 대상:

```text
outputs/verify/260722_1953_w10_i100_dpc4_hard_config_comp_split_2g/summary/fdip_0/2i6d/metrics.csv
outputs/260722_1830_w10_i100_dpc4_split_2g/summary/fdip_0/2i6d/metrics.csv
```

실행 결과:

| 항목 | 결과 |
|---|---:|
| traces | 22 |
| ok | 22 |
| failed | 0 |
| `delta` Avg IPC | 0.607 |
| `sierra.a.6` Avg IPC | 0.459 |

비교 결과:

| 항목 | 결과 |
|---|---:|
| `ChampSim_DPC4` 2i6d rows | 22 |
| `ChampSim_DPC4_Split` 2i6d rows | 22 |
| common rows | 22 |
| missing rows | 0 |
| status/reason 차이 | 0 |
| numeric columns | 34 |
| numeric changed cells | 0 |
| max numeric delta | 0 |

결론적으로 `2i6d`에서도 `ChampSim_DPC4`에 수동으로 만든 split hierarchy와 `ChampSim_DPC4_Split`의 `-L2C 0x8` parser path가 완전히 동일한 결과를 냈다.

이는 `ChampSim_DPC4_Split`의 `L2C.partition=static`, `instruction_ways=2`, `data_ways=6` 설정이 의도한 `L1I -> L2I -> LLC`, `L1D -> L2D -> LLC` 구조를 정확히 생성한다는 강한 근거다.

## 4i4d 재검증

`2i6d` 검증 후 `ChampSim_DPC4/champsim_config.json`의 way 수만 `4i4d`로 변경했다.

변경한 설정:

| 항목 | 2i6d | 4i4d |
|---|---:|---:|
| L2IC ways | 2 | 4 |
| L2DC ways | 6 | 4 |

빌드:

```bash
./scripts/run.sh \
  -C ChampSim_DPC4 \
  -b \
  -L2C 0x10 \
  -r 260722_1953_w10_i100_dpc4_hard_config_comp_split_2g
```

실행:

```bash
./scripts/run.sh \
  -C ChampSim_DPC4 \
  -t \
  -L2C 0x10 \
  -T trace_gtrace_l2c_test_g2.txt \
  -w 1000000 \
  -i 10000000 \
  -p 28 \
  -r 260722_1953_w10_i100_dpc4_hard_config_comp_split_2g
```

summary 생성:

```bash
./scripts/run.sh \
  -C ChampSim_DPC4 \
  -s 0x41 \
  -L2C 0x10 \
  -T trace_gtrace_l2c_test_g2.txt \
  -r 260722_1953_w10_i100_dpc4_hard_config_comp_split_2g
```

실행 결과:

| 항목 | 결과 |
|---|---:|
| traces | 22 |
| ok | 22 |
| failed | 0 |
| `delta` Avg IPC | 0.609 |
| `sierra.a.6` Avg IPC | 0.459 |

비교 파일:

```text
outputs/verify/260722_1953_w10_i100_dpc4_hard_config_comp_split_2g/summary/fdip_0/4i4d/metrics.csv
outputs/260722_1830_w10_i100_dpc4_split_2g/summary/fdip_0/4i4d/metrics.csv
```

비교 결과:

| 항목 | 결과 |
|---|---:|
| `ChampSim_DPC4` 4i4d rows | 22 |
| `ChampSim_DPC4_Split` 4i4d rows | 22 |
| common rows | 22 |
| missing rows | 0 |
| status/reason 차이 | 0 |
| numeric columns | 34 |
| numeric changed cells | 0 |
| max numeric delta | 0 |

`4i4d`도 `ChampSim_DPC4` 수동 split baseline과 `ChampSim_DPC4_Split`의 parser-generated split 결과가 완전히 동일했다.

## 현재 결론

`shared`, `2i6d`, `4i4d` 세 경우 모두 `ChampSim_DPC4` 기준 결과와 `ChampSim_DPC4_Split` 결과가 exact match였다.

| policy | rows | status diff | numeric changed cells | 결론 |
|---|---:|---:|---:|---|
| shared | 22 | 0 | 0 | exact match |
| 2i6d | 22 | 0 | 0 | exact match |
| 4i4d | 22 | 0 | 0 | exact match |

따라서 현재 범위에서는 `ChampSim_DPC4_Split`의 `shared`와 `static split` parser path가 DPC4 기준 동작을 보존하며, `instruction_ways`/`data_ways` 설정을 의도한 L2I/L2D way 수로 정확히 반영한다고 판단한다.

## 판정 기준

trace별로 다음 항목이 모두 동일해야 한다.

- `status`, `reason`
- `ipc`, `instructions`, `cycles`
- `branch_mpki`
- `l1i_mpki`, `l1d_mpki`
- `l2c_mpki`, `l2i_mpki`, `l2d_mpki`
- `llc_mpki`, `lli_mpki`, `lld_mpki`
- 주요 access/miss counter

완전히 동일하면 `ChampSim_DPC4_Split`의 parser/config 기반 split 생성이 수동 split 설정과 동등하다고 판단한다. 차이가 있으면 config 생성 차이, hierarchy 연결 차이, prefetcher/replacement 설정 차이를 우선 확인한다.
