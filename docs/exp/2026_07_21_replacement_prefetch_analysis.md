# 2026-07-21 Analysis: Replacement Bug 수정 및 L2C Prefetcher 제거 결과

이 문서는 `260721_1451_w10_i20_repl_test` 결과를 이전 짧은 latency test인 `260716_1305_w10_i20_latency_test`와 비교한다. 비교 목적은 L2C partition replacement bug 수정 이후 결과가 어떻게 달라졌는지 확인하는 것이다.

## 비교 대상

| 항목 | 이전 결과 | 수정 후 결과 |
|---|---|---|
| Run ID | `260716_1305_w10_i20_latency_test` | `260721_1451_w10_i20_repl_test` |
| Trace list | `trace_gtrace_l2c_test.txt` | `trace_gtrace_l2c_test.txt` |
| Warmup / Simulation | `1,000,000` / `2,000,000` | `1,000,000` / `2,000,000` |
| FTQ | `0`, `2`, `4`, `16`, `32`, `64` | `0`, `4`, `32` |
| L2C policy | `shared`, `0i8d`, `1i7d`, `2i6d`, `4i4d`, `6i2d`, `8i0d` | `shared`, `0i8d`, `2i6d`, `4i4d`, `6i2d` |
| L2C prefetcher | `ip_stride` | `no` |
| 완료 상태 | 12,432 / 12,432 OK | 4,438 / 4,440 OK |

주의할 점은 두 run의 조건이 완전히 같지 않다는 점이다. `260721_1451`은 replacement bug 수정뿐 아니라 L2C prefetcher를 `ip_stride`에서 `no`로 바꾼 상태다. 따라서 아래 비교는 **replacement fix 단독 효과**가 아니라 **replacement fix + L2C prefetcher 제거 효과**로 해석해야 한다.

## 실패 항목

`260721_1451_w10_i20_repl_test`에서는 2개 job이 실패했다.

| FTQ | L2C policy | Trace |
|---:|---|---|
| 0 | `0i8d` | `yankee_0014.champsim.gz` |
| 0 | `6i2d` | `yankee_0014.champsim.gz` |

이전 `260716_1305`에서는 같은 trace set 기준 실패가 없었다. 따라서 `yankee_0014`는 별도 확인이 필요하다.

## 절대 수치 비교

공통 조건(`ftq=0/4/32`, `shared/0i8d/2i6d/4i4d/6i2d`)만 놓고 보면, 수정 후 결과는 이전보다 평균 IPC가 약간 낮다.

| L2C policy | 평균 IPC 변화 |
|---|---:|
| `shared` | -0.0118 |
| `0i8d` | -0.0107 |
| `2i6d` | -0.0107 |
| `4i4d` | -0.0098 |
| `6i2d` | -0.0105 |

중요한 점은 `shared`까지 같이 낮아졌다는 것이다. `shared`는 partition victim range 수정의 직접 영향을 거의 받지 않아야 하므로, 절대 IPC 감소는 L2C prefetcher 제거 또는 실행 binary/config 차이의 영향이 섞인 것으로 보는 편이 자연스럽다.

## Shared 대비 partition 효과 비교

절대 IPC는 낮아졌지만, `shared`를 기준으로 한 partition의 상대 IPC delta는 수정 후가 더 좋아졌다.

| L2C policy | 260716 dIPC | 260721 dIPC | 변화 |
|---|---:|---:|---:|
| `0i8d` | +0.327% | +0.537% | +0.210%p |
| `2i6d` | +1.023% | +1.268% | +0.245%p |
| `4i4d` | +1.554% | +1.962% | +0.408%p |
| `6i2d` | +1.868% | +2.139% | +0.271%p |

이 결과는 replacement bug 수정이 partition 결과를 더 긍정적인 방향으로 정리했음을 보여준다. 특히 `4i4d`의 개선 폭이 가장 크다.

## MPKI 변화

Shared 대비 delta 기준으로 보면, 수정 후에는 `2i6d`, `4i4d`, `6i2d`에서 L2D MPKI penalty가 크게 줄었다.

| L2C policy | dL2I MPKI 변화 | dL2D MPKI 변화 | dL2C MPKI 변화 |
|---|---:|---:|---:|
| `0i8d` | +0.000 | +0.529 | +0.287 |
| `2i6d` | -25.256 | -5.867 | -5.159 |
| `4i4d` | -12.081 | -9.537 | -7.780 |
| `6i2d` | -10.651 | -5.851 | -5.260 |

이전 구현에서는 partition 내부 invalid way를 찾은 뒤, invalid way가 없으면 replacement policy가 전체 set에서 victim을 골랐다. 그 victim이 partition 밖이면 partition의 첫 way로 fallback했다. 이 방식은 hard partition 경계는 유지하지만, partition 내부 LRU 순서를 깨뜨릴 수 있다.

수정 후에는 replacement policy에 victim 후보 way range를 직접 전달한다. 따라서 `2i6d`에서는 instruction fill이 way `0~1`, data fill이 way `2~7` 안에서만 victim을 고른다. `4i4d`, `6i2d`도 같은 방식으로 각 partition 내부에서 replacement가 동작한다.

## 가장 크게 좋아진 케이스

Shared 대비 dIPC가 가장 크게 좋아진 대표 케이스는 다음과 같다.

| Trace | FTQ | L2C policy | 260716 dIPC | 260721 dIPC | 변화 |
|---|---:|---|---:|---:|---:|
| `yankee` | 4 | `0i8d` | -0.934% | +0.717% | +1.651%p |
| `sierra.a.4` | 4 | `0i8d` | -0.416% | +0.838% | +1.254%p |
| `merced` | 32 | `4i4d` | +0.833% | +1.831% | +0.998%p |
| `merced` | 4 | `4i4d` | +0.916% | +1.761% | +0.845%p |
| `sierra.a.6` | 32 | `4i4d` | +1.468% | +2.276% | +0.807%p |

## 가장 나빠진 케이스

일부 케이스에서는 shared 대비 dIPC가 이전보다 나빠졌다.

| Trace | FTQ | L2C policy | 260716 dIPC | 260721 dIPC | 변화 |
|---|---:|---|---:|---:|---:|
| `delta` | 0 | `2i6d` | +1.951% | +1.443% | -0.509%p |
| `tango` | 32 | `0i8d` | +0.905% | +0.534% | -0.371%p |
| `sierra.a.4` | 32 | `0i8d` | +0.557% | +0.279% | -0.278%p |
| `delta` | 32 | `0i8d` | +0.235% | -0.024% | -0.259%p |
| `sierra.a.6` | 32 | `0i8d` | +0.897% | +0.660% | -0.236%p |

특히 `delta`는 수정 후에도 partition 자체는 대체로 양수지만, 이전 대비 개선 폭이 줄어든 케이스가 있다. `delta`는 L2I/L2D 변화와 IPC 변화의 관계를 별도로 확인할 필요가 있다.

## 해석

이번 결과에서 가장 중요한 관찰은 두 가지다.

첫째, 절대 IPC는 수정 후가 약간 낮다. 하지만 이 감소는 `shared`에도 동일하게 나타나므로, partition replacement 수정 자체보다는 L2C prefetcher 제거 효과가 섞였을 가능성이 높다.

둘째, shared 대비 partition 효과는 수정 후 더 좋아졌다. 특히 `2i6d`, `4i4d`, `6i2d`에서 L2D MPKI penalty가 줄고, partition 상대 IPC가 개선됐다. 이는 기존 fallback 방식이 partition 내부 replacement 순서를 왜곡하고 있었을 가능성을 지지한다.

결론적으로 replacement bug 수정은 partition 실험을 더 합리적인 모델로 만든다. 다만 L2C prefetcher를 동시에 제거했기 때문에, replacement fix의 순수 효과를 분리하려면 다음 중 하나가 필요하다.

- 이전 코드 조건에서 L2C prefetcher만 `no`로 맞춘 재실험
- 수정 후 코드에서 L2C prefetcher를 다시 `ip_stride`로 둔 비교 실험

현재 연구 방향에서는 L2C prefetcher origin 오염 가능성이 있기 때문에 `no`를 유지하는 것이 더 안전하다. 따라서 앞으로의 partition 실험 baseline은 `L2C prefetcher = no`, replacement range-aware 구현 기준으로 통일하는 것이 좋다.
