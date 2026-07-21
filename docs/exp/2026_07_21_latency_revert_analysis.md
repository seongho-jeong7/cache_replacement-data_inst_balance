# 2026-07-21 Analysis: Latency Revert Test 결과

이 문서는 `260721_1707_w10_i20_latency_revert_test` 결과를 분석한다. 이 run은 L2C way별 lookup latency 모델을 끄고, ChampSim 기본 latency 모델로 되돌린 뒤 측정한 결과다.

## 실험 조건

| 항목 | 값 |
|---|---|
| Run ID | `260721_1707_w10_i20_latency_revert_test` |
| Trace list | `trace_gtrace_l2c_test.txt` |
| Warmup / Simulation | `1,000,000` / `2,000,000` |
| FTQ | `0` |
| L2C policy | `shared`, `0i8d`, `2i6d`, `6i2d` |
| L2C prefetcher | `no` |
| 완료 상태 | 1,184 / 1,184 OK |

이번 실험의 목적은 way별 latency 모델이 partition 결과를 지배하고 있었는지 확인하는 것이다. 따라서 비교할 핵심 대상은 replacement bug 수정 이후이지만 way별 latency가 켜져 있던 `260721_1451_w10_i20_fix_repl_bug`이다.

## 평균 IPC

| L2C policy | Avg IPC |
|---|---:|
| `shared` | 0.507896 |
| `0i8d` | 0.509845 |
| `2i6d` | 0.507447 |
| `6i2d` | 0.505257 |

latency를 되돌린 뒤에는 `shared`와 partition 정책 사이의 차이가 매우 작아졌다. 특히 way별 latency 모델에서 가장 강하게 좋아 보였던 `6i2d`는 오히려 평균 IPC가 `shared`보다 낮아졌다.

## Shared 대비 변화량

| L2C policy | dIPC | dL2I MPKI | dL2D MPKI | dL2C MPKI | dFrontend Stall | dBackend Data Stall |
|---|---:|---:|---:|---:|---:|---:|
| `0i8d` | +0.588% | -9.268 | -0.924 | -10.192 | -0.102%p | -0.004%p |
| `2i6d` | -0.106% | +2.514 | -0.409 | +2.105 | +0.298%p | -0.004%p |
| `6i2d` | -0.419% | -1.643 | +2.195 | +0.552 | -0.353%p | +0.024%p |

`0i8d`는 평균적으로 가장 좋은 정책이다. instruction을 L2C에서 bypass하면서 L2C MPKI가 크게 줄고, L2D MPKI도 약간 개선된다. 다만 IPC 개선 폭은 `+0.588%`로 크지 않다.

`2i6d`는 data에 6 ways를 주지만 L2I MPKI가 증가하고 frontend stall도 증가한다. 평균 IPC는 거의 `shared`와 같지만 약간 낮다.

`6i2d`는 instruction MPKI와 frontend stall은 좋아지지만, data way가 줄어 L2D MPKI가 증가한다. 결과적으로 IPC는 평균 `-0.419%`로 감소한다.

## Way별 Latency 모델과 비교

같은 replacement fix 이후 조건에서 way별 latency가 켜져 있던 `260721_1451_w10_i20_fix_repl_bug`와 비교하면 다음과 같다.

| L2C policy | Way latency ON dIPC | Latency revert dIPC | 변화 |
|---|---:|---:|---:|
| `0i8d` | +1.097% | +0.588% | -0.509%p |
| `2i6d` | +1.824% | -0.106% | -1.930%p |
| `6i2d` | +2.390% | -0.419% | -2.809%p |

MPKI 변화는 두 run에서 거의 비슷하다. 예를 들어 `6i2d`는 두 run 모두 L2D MPKI가 증가하고 L2I MPKI가 감소한다. 그런데 way별 latency가 켜져 있을 때는 `6i2d`가 크게 좋아졌고, latency를 되돌리면 오히려 나빠진다.

이 차이는 이전 결과의 큰 IPC 개선이 capacity 변화만으로 설명되지 않는다는 뜻이다. way별 latency 모델은 partition policy가 자기 way만 검색한다고 가정하면서 `6i2d`의 data lookup latency를 크게 줄였다. 이 latency 이득이 L2D MPKI 증가 손해를 압도하면서 `6i2d`가 좋아 보인 것이다.

latency를 ChampSim 기본값으로 되돌리면 이 효과가 사라진다. 따라서 `6i2d`가 강하게 좋아졌던 이전 결과는 L2C partition의 capacity 효과라기보다, way별 latency 모델이 만든 효과로 해석하는 것이 맞다.

## Workload별 경향

평균 dIPC 기준으로 보면 workload group별 차이는 다음과 같다.

| Trace group | 평균 dIPC | 가장 좋은 policy |
|---|---:|---|
| `bravo` | -0.147% | `6i2d` |
| `delta` | +0.374% | `6i2d` |
| `merced` | -0.002% | `0i8d` |
| `sierra.a.4` | +0.192% | `0i8d` |
| `sierra.a.6` | -0.272% | `0i8d` |
| `tahoe` | -0.097% | `0i8d` |
| `tango` | +0.187% | `0i8d` |
| `yankee` | +0.036% | `0i8d` |

대부분의 workload에서는 `0i8d`가 가장 좋은 정책이다. 다만 개선 폭은 작고, 일부 trace에서는 frontend stall 증가 때문에 `0i8d`가 크게 나빠지는 경우도 있다.

대표적으로 `tahoe_0024`는 `0i8d`에서 dIPC가 `-6.697%`까지 떨어진다. 이 경우 L2I/L2D MPKI 변화는 크지 않지만 frontend stall이 `+11.34%p` 증가한다. 즉 instruction을 L2C에서 완전히 제거하는 정책은 평균적으로는 좋아 보여도, 특정 trace에서는 instruction fetch latency를 크게 악화시킬 수 있다.

반대로 `merced_0034`는 `0i8d`에서 dIPC가 `+6.170%`로 가장 크게 좋아진다. 이 경우 L2I MPKI와 L2D MPKI가 모두 감소한다. 이런 trace는 instruction을 L2C에 보관하지 않는 것이 data-side와 전체 cache traffic 모두에 유리하게 작동한 케이스다.

## 결론

latency를 되돌린 결과는 이전 해석을 명확하게 정리해 준다.

- way별 latency 모델이 켜져 있을 때 보였던 큰 partition 이득은 대부분 latency 모델 효과였다.
- ChampSim 기본 latency로 되돌리면 L2C partition의 평균 IPC 효과는 작아진다.
- `0i8d`는 여전히 평균적으로 가장 좋은 후보지만, 개선 폭은 `+0.588%` 수준이다.
- `2i6d`, `6i2d`는 평균적으로 `shared`보다 좋지 않다.
- 특정 trace에서는 `0i8d`가 frontend stall을 크게 늘릴 수 있으므로, instruction bypass는 workload/phase에 따라 조심스럽게 적용해야 한다.

따라서 앞으로의 연구 방향은 way별 latency 모델을 기본으로 삼지 않고, ChampSim 기본 latency 조건에서 prefetcher가 instruction/data pressure를 어떻게 바꾸는지 확인하는 쪽으로 가는 것이 맞다. 특히 `FTQ=0` baseline에서 partition-only 효과를 다시 보고, 이후 L1D/L2D/L1I prefetcher 조합으로 cache pressure를 조절하는 실험이 필요하다.
