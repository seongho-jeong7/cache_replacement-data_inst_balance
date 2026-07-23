# 2026-07-23 Experiment: Berti/Pythia Prefetcher Split L2 Test

## 목적

`ChampSim_DPC4_Split`에서 data-side prefetcher를 더 공격적으로 설정했을 때 L2 split 정책별 성능 변화를 확인한다.

이전 실험에서는 L2 partition/split의 way 배분 자체를 중심으로 봤다. 이번 실험은 prefetcher 구성을 바꿔서, data cache pressure가 커지거나 줄어들 때 L2I/L2D 분리 정책이 어떤 영향을 주는지 확인하는 것이 목적이다.

## 설정

대상 코드:

```text
ChampSim_DPC4_Split
```

prefetcher 설정:

| cache | prefetcher | 의도 |
|---|---|---|
| L1I | `no` | instruction 쪽 L1 prefetch 영향 제거 |
| L1D | `berti` | data-side L1 prefetch 강화 |
| L2C | `pythia` | shared mode에서 unified L2C data/instruction 요청에 Pythia 적용 |
| L2D | `pythia` | split mode에서 data-side L2에 Pythia 적용 |
| L2I | `no` | split mode에서 instruction-side L2 prefetch 제거 |
| LLC | `no` | LLC prefetch 영향 제거 |

parser 수정은 필요하지 않다. 현재 `config/parse.py`는 다음과 같이 동작한다.

- `shared`: `L2C` 설정이 우선 적용되므로 `L2C=pythia`
- `static split`: `L2I`, `L2D` 설정이 `L2C` 공통 설정보다 우선하므로 `L2I=no`, `L2D=pythia`

## Trace 및 실행 조건

trace list:

```text
traces/trace_gtrace_l2c_test.txt
```

이 trace list는 296개 trace, 8개 workload group을 포함한다.

| group | trace count |
|---|---:|
| bravo | 3 |
| delta | 4 |
| merced | 89 |
| sierra.a.4 | 24 |
| sierra.a.6 | 18 |
| tahoe | 40 |
| tango | 35 |
| yankee | 83 |

실험 조건:

| 항목 | 값 |
|---|---:|
| warmup | 1,000,000 |
| simulation | 10,000,000 |
| parallel jobs | 58 |
| FTQ | 없음/non-FDIP, output bucket은 `fdip_0` |
| L2C policy mask | `0x7b` |

`0x7b`는 `1i7d`를 제외한 다음 policy를 의미한다.

| bit | policy |
|---:|---|
| `0x01` | shared |
| `0x02` | 0i8d |
| `0x08` | 2i6d |
| `0x10` | 4i4d |
| `0x20` | 6i2d |
| `0x40` | 8i0d |

## 실행 명령

run id:

```text
260723_1351_w10_i100_dpc4_split_berti_pythia
```

빌드:

```bash
./scripts/run.sh \
  -C ChampSim_DPC4_Split \
  -b \
  -L2C 0x7b \
  -r 260723_1351_w10_i100_dpc4_split_berti_pythia
```

trace 실행:

```bash
./scripts/run.sh \
  -C ChampSim_DPC4_Split \
  -t \
  -L2C 0x7b \
  -T trace_gtrace_l2c_test.txt \
  -w 1000000 \
  -i 10000000 \
  -p 58 \
  -r 260723_1351_w10_i100_dpc4_split_berti_pythia
```

summary 생성 예정:

```bash
./scripts/run.sh \
  -C ChampSim_DPC4_Split \
  -s 0xc1 \
  -L2C 0x7b \
  -T trace_gtrace_l2c_test.txt \
  -r 260723_1351_w10_i100_dpc4_split_berti_pythia
```

## 진행 상태 (최초 시도, 중단됨)

- `ChampSim_DPC4_Split/champsim_config.json`에 `L1D=berti`, `L2C=pythia`, `L2D=pythia`, `L2I=no`를 반영했다.
- `-L2C 0x7b`로 필요한 policy binary를 빌드했다.
- trace 실행을 시작했지만, 사용자 interrupt로 실행이 중단되었다(당시 `shared` 58개 log만 생성, 나머지 0개).

---

## 2026-07-23: 같은 run id로 재실행, 완료

같은 run id(`260723_1351_w10_i100_dpc4_split_berti_pythia`)로 trace 실행을 다시 시작해서 완료했다.

| 항목 | 결과 |
|---|---:|
| 총 job 수 | 1,776 (296 trace × 6 policy) |
| 성공 | 1,776 |
| 실패 | 0 |

Summary 생성:

```bash
./scripts/run.sh -C ChampSim_DPC4_Split -r 260723_1351_w10_i100_dpc4_split_berti_pythia -L2C 0x7b -s 0xc1
```

`-s 0x40`(metrics.csv, 6개 policy 전부)과 `-s 0x80`(L2C delta grid)을 함께 생성했다. 산출물: `outputs/260723_1351_w10_i100_dpc4_split_berti_pythia/summary/`에 `metrics.csv`(policy별), `l2c_raw_values.csv`, `l2c_delta_pct.csv`, `l2c_delta_raw.csv`, `l2c_delta_grid.png`, `l2c_delta_combined.png`, `l2c_delta_combined_v2.png`.

결과 분석은 `docs/exp/2026_07_23_dpc4_split_berti_pythia_analysis.md` 참고.

## 다음 단계

- 완료 후에는 `shared` 대비 각 split policy의 IPC, L1D/L2D/LLD MPKI, L1I/L2I/LLI MPKI, backend/data stall 변화를 비교한다.
- prefetcher 변경(next_line/ip_stride → berti/pythia) 전후로 L2C partition 정책의 유불리 경향이 바뀌는지, `260722_1449_w10_i100_champ_split`(`ChampSim_Split`, berti/pythia 적용 전 마지막 8-group 전체 실행)과 비교한다.
