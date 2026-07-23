# 2026-07-23 Verification: ChampSim_Split vs ChampSim_DPC4_Split 비교

## 목적

`ChampSim_Split`와 `ChampSim_DPC4_Split`은 둘 다 L2를 `L2I`/`L2D`로 물리 분리할 수 있도록 만든 split 계열 fork다. 지금까지는 각각을 자기 base와 비교했다.

- `ChampSim_Split`는 원본 `ChampSim` 및 `ChampSim_split_L2`와 비교했다.
- `ChampSim_DPC4_Split`는 `ChampSim_DPC4` 수동 hard-config 결과와 비교했다.

하지만 `ChampSim_Split`와 `ChampSim_DPC4_Split`을 직접 비교한 문서는 없었다. 이 문서는 두 split fork가 같은 config signature와 같은 g2 trace에서 얼마나 가까운 결과를 내는지 확인한다.

중요한 점은, 이 비교는 exact match를 기대하는 검증이 아니다. 두 코드는 서로 다른 base 계열(`ChampSim` vs `ChampSim_DPC4`)에서 출발했기 때문에, 같은 config처럼 보여도 내부 구현 차이가 남아 있을 수 있다.

## 비교 대상

| 항목 | ChampSim_Split | ChampSim_DPC4_Split |
|---|---|---|
| 결과 폴더 | `outputs/260721_2005_w10_i100_champ_split_2g` | `outputs/260722_1830_w10_i100_dpc4_split_2g` |
| trace list | `l2c_test_g2.txt` / `trace_gtrace_l2c_test_g2.txt` | `trace_gtrace_l2c_test_g2.txt` |
| trace 범위 | g2, 22 traces (`delta` + `sierra.a.6`) | 동일 |
| warmup / simulation | 1,000,000 / 10,000,000 | 동일 |
| 비교 policy | `shared`, `2i6d`, `4i4d` | 동일 |

`ChampSim_Split` 결과에는 `0i8d`/`6i2d`/`8i0d`도 있지만, `ChampSim_DPC4_Split`의 `260722_1830` 결과에는 `shared`/`2i6d`/`4i4d`만 있으므로 공통 policy 3개만 비교했다.

## Config 정합성

두 결과의 `config_signature.txt`는 공통 policy에서 동일하다.

| policy | config signature |
|---|---|
| `shared` | `bimodal-basic_btb-no-next_line-ip_stride-l2cshared-no-lru-1core` |
| `2i6d` | `bimodal-basic_btb-no-next_line-ip_stride-l2c2i6d-no-lru-1core` |
| `4i4d` | `bimodal-basic_btb-no-next_line-ip_stride-l2c4i4d-no-lru-1core` |

주요 config snapshot도 동일하게 보인다.

| 항목 | 값 |
|---|---|
| Core | fetch/decode/dispatch 6-wide, execute 4-wide, ROB 352, LQ 128, SQ 72 |
| L1I | 64 sets, 8 ways, latency 4, prefetcher `no` |
| L1D | 64 sets, 12 ways, latency 5, prefetcher `next_line` |
| L2C/L2I/L2D | 1024 sets, latency 10, prefetcher `ip_stride` |
| LLC | 2048 sets, 16 ways, latency 20, prefetcher `no`, replacement `lru` |
| DRAM | tCAS/tRCD/tRP 24, tRAS 52 |

따라서 아래 차이는 command/config mismatch 때문이라기보다, base 코드 계열 차이 또는 두 fork의 내부 구현 차이에서 온 것으로 봐야 한다.

## 비교 결과

공통 trace row는 policy마다 22개이며, 누락 row는 없다. 하지만 numeric value는 exact match가 아니다.

| policy | rows | 평균 dIPC<br>(DPC4 - Champ) | 최대 abs dIPC | 평균 dL1I MPKI | 평균 dL1D MPKI | 평균 dL2C MPKI | 평균 dLLC MPKI |
|---|---:|---:|---:|---:|---:|---:|---:|
| `shared` | 22 | +0.0060 | 0.0317 | -0.1023 | -6.9279 | -0.0672 | -0.0408 |
| `2i6d` | 22 | +0.0058 | 0.0338 | -0.0899 | -6.9214 | +0.0173 | -0.0428 |
| `4i4d` | 22 | +0.0060 | 0.0323 | -0.1314 | -6.9498 | -0.1243 | -0.0365 |

해석:

- DPC4_Split이 세 policy 모두에서 평균 IPC가 약 +0.006 높다.
- L1I MPKI는 거의 비슷하다(평균 차이 약 -0.09~-0.13).
- L1D MPKI는 DPC4_Split이 약 6.9 낮다.
- L2C/LLC MPKI 차이는 L1D만큼 크지는 않다.

가장 큰 IPC 차이는 `delta` 계열 trace에서 나온다.

| policy | trace | ChampSim_Split IPC | DPC4_Split IPC | delta |
|---|---|---:|---:|---:|
| `shared` | `delta_0002` | 0.6315 | 0.6632 | +0.0317 |
| `2i6d` | `delta_0002` | 0.6330 | 0.6668 | +0.0338 |
| `4i4d` | `delta_0002` | 0.6383 | 0.6706 | +0.0323 |

반면 `sierra.a.6` 계열은 IPC 차이가 상대적으로 작다. 즉 차이는 전체적으로 존재하지만, 특히 `delta`에서 더 뚜렷하다.

## 결론

`ChampSim_Split`와 `ChampSim_DPC4_Split`는 같은 g2 trace, 같은 instruction count, 같은 config signature로 실행해도 `metrics.csv` 기준 exact match가 아니다.

따라서 두 결과를 서로 직접 baseline으로 섞어 쓰면 안 된다. `ChampSim_Split` 결과는 원본 `ChampSim` 계열 split 연구의 기준으로, `ChampSim_DPC4_Split` 결과는 DPC4 계열 split 연구의 기준으로 분리해서 읽어야 한다.

다만 이 비교는 무의미하지 않다. 두 fork 모두에서 `shared`/`2i6d`/`4i4d` 간 상대 경향을 비교하면, base 코드 차이 위에서 split policy가 같은 방향성을 가지는지 보는 보조 자료로 사용할 수 있다. 절대 IPC나 절대 MPKI 일치 여부를 검증하는 용도로는 부적합하다.
