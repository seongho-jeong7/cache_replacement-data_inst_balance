# 2026-07-22 Analysis: w10/i100 L2C Split 결과

이 문서는 `260722_1449_w10_i100_champ_split` 결과를 바탕으로, `ChampSim_Split`의 shared/split L2 구조가 IPC, MPKI, stall에 어떤 영향을 주었는지 분석한다.

## 실험 요약

| 항목 | 값 |
|---|---|
| Run ID | `260722_1449_w10_i100_champ_split` |
| ChampSim dir | `ChampSim_Split` |
| Trace list | `trace_gtrace_l2c_test.txt` |
| Trace groups | `bravo`, `delta`, `merced`, `sierra.a.4`, `sierra.a.6`, `tahoe`, `tango`, `yankee` |
| L2C policies | `shared`, `0i8d`, `2i6d`, `4i4d`, `6i2d`, `8i0d` |
| Warmup / Simulation | `1,000,000` / `10,000,000` |
| 총 job 수 | 296 traces x 6 policies = 1,776 |
| 결과 | 1,776 completed, 0 failed |

이번 분석의 기준값은 `shared`이고, 나머지 policy는 모두 `shared` 대비 변화량으로 본다.

## 지표 해석

`dIPC`는 `shared` 대비 percent 변화량이다. 나머지 MPKI와 stall 지표는 `shared` 대비 raw delta다.

```text
dIPC(%) = (policy IPC / shared IPC - 1) x 100
dMPKI   = policy MPKI - shared MPKI
dStall  = policy stall% - shared stall%
```

주의할 점은 `0i8d`와 `8i0d`의 MPKI 해석이다.

- `0i8d`: instruction은 L2I를 bypass한다. 따라서 `L2I MPKI` 감소는 L2I hit-rate 개선이 아니라, L2I 자체를 거치지 않는 구조 변화다.
- `8i0d`: data는 L2D를 bypass한다. 따라서 `L2D MPKI` 감소는 data miss 개선이 아니라, L2D 자체를 거치지 않는 구조 변화다.
- `L2C MPKI`는 shared에서는 `L2C_I + L2C_D` 의미이고, split에서는 `L2I + L2D`를 합친 값으로 해석한다.

## 정책별 평균 변화

8개 trace group 평균으로 보면 가장 좋은 평균 IPC는 `0i8d`에서 나왔다. 반대로 `8i0d`는 일부 workload에서는 크게 좋아지지만, `delta`에서 크게 무너지면서 평균이 음수가 됐다.

| Policy | dIPC(%) | dL1I MPKI | dL2I MPKI | dFE Stall | dBI Stall | dL1D MPKI | dL2D MPKI | dBD Stall | dL2C MPKI |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `0i8d` | +1.87 | +0.38 | -9.87 | -1.63 | +0.04 | -0.01 | -0.94 | +0.07 | -10.81 |
| `2i6d` | -0.11 | +0.16 | +3.44 | +0.28 | -0.01 | -0.02 | -0.48 | -0.00 | +2.96 |
| `4i4d` | -0.14 | +0.02 | +0.17 | +0.05 | +0.01 | +0.05 | +0.40 | +0.04 | +0.57 |
| `6i2d` | -0.40 | -0.06 | -2.41 | -0.37 | +0.02 | +0.19 | +2.16 | +0.09 | -0.25 |
| `8i0d` | -1.35 | -0.07 | -4.10 | -0.75 | +0.00 | +1.07 | -8.87 | +1.59 | -12.98 |

해석:

- `0i8d`는 평균적으로 frontend stall을 가장 많이 줄이고 IPC도 가장 좋다.
- `2i6d`, `4i4d`, `6i2d`는 평균적으로 shared 대비 거의 중립 또는 소폭 손해다.
- `6i2d`는 L2I MPKI를 줄이지만 L2D MPKI가 증가한다. 이 trade-off는 평균 IPC에 좋게 작동하지 않았다.
- `8i0d`는 L2D를 bypass하면서 `backend data stall`이 평균 +1.59%p 증가한다. 이 증가의 대부분은 `delta`가 만든다.

## IPC 개선 상위/하위 케이스

IPC가 가장 좋아진 케이스는 `sierra.a.6`의 `8i0d`, `0i8d`다. 두 경우 모두 frontend stall이 줄고 L2C aggregate MPKI가 크게 줄었다.

| Trace | Policy | dIPC(%) | dL2I MPKI | dL2D MPKI | dFE Stall | dBD Stall |
|---|---|---:|---:|---:|---:|---:|
| `sierra.a.6` | `8i0d` | +4.11 | -13.64 | -10.46 | -1.67 | +0.08 |
| `sierra.a.6` | `0i8d` | +4.04 | -20.17 | -3.17 | -3.17 | +0.07 |
| `tango` | `8i0d` | +3.34 | -5.27 | -8.39 | -0.39 | +0.16 |
| `bravo` | `8i0d` | +2.50 | -3.41 | -8.39 | -0.31 | +0.07 |
| `tango` | `0i8d` | +2.22 | -10.00 | -0.99 | -2.18 | +0.10 |

IPC가 가장 나빠진 케이스는 압도적으로 `delta`의 `8i0d`다.

| Trace | Policy | dIPC(%) | dL1D MPKI | dL2D MPKI | dFE Stall | dBD Stall |
|---|---|---:|---:|---:|---:|---:|
| `delta` | `8i0d` | -22.57 | +4.97 | -8.89 | -3.25 | +11.14 |
| `tahoe` | `8i0d` | -0.94 | +0.72 | -7.86 | -0.29 | +0.68 |
| `merced` | `6i2d` | -0.74 | +0.31 | +2.47 | -0.42 | +0.05 |
| `yankee` | `6i2d` | -0.74 | +0.16 | +1.86 | -0.11 | +0.04 |
| `bravo` | `6i2d` | -0.64 | +0.15 | +2.09 | -0.16 | +0.07 |

`delta-8i0d`는 frontend stall이 줄었는데도 IPC가 크게 하락했다. 즉, instruction side는 좋아졌지만 data side가 너무 크게 악화된 케이스다. `backend data stall`이 +11.14%p 증가한 것이 핵심 신호다.

## Trace별 상세 변화량

아래 표는 shared 대비 각 policy의 주요 변화량이다. `dIPC`만 percent이고, MPKI/stall은 raw delta다.

| Trace | Policy | dIPC(%) | dL1I | dL2I | dFE Stall | dBI Stall | dL1D | dL2D | dBD Stall | dL2C |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bravo | 0i8d | +1.62 | +0.44 | -8.51 | -1.54 | +0.05 | +0.02 | -0.48 | +0.07 | -9.00 |
| bravo | 2i6d | -0.16 | +0.05 | +3.76 | +0.27 | -0.01 | -0.01 | -0.09 | +0.01 | +3.67 |
| bravo | 4i4d | -0.35 | -0.03 | -0.39 | +0.19 | +0.01 | +0.06 | +0.59 | +0.01 | +0.20 |
| bravo | 6i2d | -0.64 | -0.03 | -2.18 | -0.16 | +0.03 | +0.15 | +2.09 | +0.07 | -0.09 |
| bravo | 8i0d | +2.50 | -0.04 | -3.41 | -0.31 | +0.02 | +0.10 | -8.39 | +0.07 | -11.80 |
| delta | 0i8d | +0.34 | +0.07 | -2.03 | -0.59 | +0.01 | +0.11 | -0.12 | +0.15 | -2.16 |
| delta | 2i6d | +0.20 | -0.02 | -0.21 | -0.11 | +0.01 | +0.17 | +0.10 | +0.03 | -0.11 |
| delta | 4i4d | +0.73 | -0.03 | -1.22 | -0.84 | +0.03 | +0.16 | +0.40 | +0.28 | -0.82 |
| delta | 6i2d | +1.17 | -0.03 | -1.48 | -1.52 | +0.04 | +0.24 | +0.93 | +0.48 | -0.55 |
| delta | 8i0d | -22.57 | -0.03 | -1.58 | -3.25 | -0.15 | +4.97 | -8.89 | +11.14 | -10.48 |
| merced | 0i8d | +1.30 | +0.15 | -5.93 | -1.15 | +0.01 | -0.04 | -0.43 | +0.05 | -6.36 |
| merced | 2i6d | -0.11 | +0.01 | +0.97 | +0.11 | +0.01 | -0.01 | -0.04 | -0.01 | +0.93 |
| merced | 4i4d | -0.27 | -0.02 | -0.41 | -0.04 | +0.03 | +0.10 | +0.70 | +0.01 | +0.29 |
| merced | 6i2d | -0.74 | -0.03 | -1.16 | -0.42 | +0.06 | +0.31 | +2.47 | +0.05 | +1.31 |
| merced | 8i0d | +0.08 | -0.04 | -1.67 | -0.74 | +0.04 | +1.12 | -6.34 | +0.29 | -8.01 |
| sierra.a.4 | 0i8d | +2.18 | +0.35 | -15.72 | -1.72 | +0.07 | -0.01 | -1.20 | +0.05 | -16.91 |
| sierra.a.4 | 2i6d | -0.01 | +0.07 | +2.99 | -0.03 | -0.00 | -0.05 | -0.55 | +0.01 | +2.44 |
| sierra.a.4 | 4i4d | -0.03 | -0.03 | -0.17 | -0.06 | -0.00 | +0.06 | +0.57 | +0.01 | +0.40 |
| sierra.a.4 | 6i2d | -0.62 | -0.08 | -2.34 | -0.10 | -0.01 | +0.24 | +2.84 | +0.04 | +0.49 |
| sierra.a.4 | 8i0d | +1.54 | -0.10 | -3.55 | +0.43 | -0.00 | +0.46 | -12.86 | +0.15 | -16.42 |
| sierra.a.6 | 0i8d | +4.04 | +1.42 | -20.17 | -3.17 | +0.07 | -0.11 | -3.17 | +0.07 | -23.34 |
| sierra.a.6 | 2i6d | -0.51 | +1.08 | +15.19 | +1.52 | -0.05 | -0.17 | -2.47 | -0.02 | +12.72 |
| sierra.a.6 | 4i4d | -0.46 | +0.32 | +4.62 | +0.78 | -0.03 | -0.04 | -0.43 | -0.01 | +4.19 |
| sierra.a.6 | 6i2d | -0.56 | -0.18 | -6.60 | -0.72 | +0.03 | +0.21 | +3.63 | +0.00 | -2.97 |
| sierra.a.6 | 8i0d | +4.11 | -0.23 | -13.64 | -1.67 | +0.07 | +0.39 | -10.46 | +0.08 | -24.10 |
| tahoe | 0i8d | +1.52 | +0.24 | -7.91 | -1.29 | +0.03 | -0.01 | -0.49 | +0.06 | -8.40 |
| tahoe | 2i6d | -0.16 | +0.02 | +1.42 | +0.18 | -0.00 | -0.02 | -0.16 | -0.01 | +1.26 |
| tahoe | 4i4d | -0.20 | -0.02 | -0.38 | +0.10 | -0.00 | +0.02 | +0.41 | +0.00 | +0.04 |
| tahoe | 6i2d | -0.44 | -0.04 | -1.38 | -0.00 | -0.00 | +0.11 | +1.59 | +0.01 | +0.21 |
| tahoe | 8i0d | -0.94 | -0.05 | -2.21 | -0.29 | -0.03 | +0.72 | -7.86 | +0.68 | -10.06 |
| tango | 0i8d | +2.22 | +0.25 | -10.00 | -2.18 | +0.03 | -0.02 | -0.99 | +0.10 | -10.99 |
| tango | 2i6d | -0.12 | +0.06 | +2.47 | +0.23 | -0.01 | -0.03 | -0.45 | -0.01 | +2.02 |
| tango | 4i4d | -0.31 | -0.02 | -0.48 | +0.22 | +0.00 | +0.03 | +0.41 | +0.01 | -0.08 |
| tango | 6i2d | -0.63 | -0.06 | -3.15 | +0.04 | +0.00 | +0.14 | +1.87 | +0.03 | -1.28 |
| tango | 8i0d | +3.34 | -0.06 | -5.27 | -0.39 | +0.04 | +0.34 | -8.39 | +0.16 | -13.66 |
| yankee | 0i8d | +1.77 | +0.11 | -8.73 | -1.42 | +0.02 | -0.03 | -0.61 | +0.04 | -9.34 |
| yankee | 2i6d | -0.03 | +0.03 | +0.94 | +0.05 | +0.00 | -0.02 | -0.14 | -0.00 | +0.80 |
| yankee | 4i4d | -0.20 | -0.01 | -0.24 | +0.06 | +0.00 | +0.04 | +0.57 | +0.00 | +0.33 |
| yankee | 6i2d | -0.74 | -0.02 | -0.96 | -0.11 | +0.01 | +0.16 | +1.86 | +0.04 | +0.90 |
| yankee | 8i0d | +1.14 | -0.03 | -1.50 | +0.23 | +0.01 | +0.46 | -7.79 | +0.17 | -9.29 |

## 주요 해석

### 0i8d: 평균적으로 가장 안정적인 개선

`0i8d`는 instruction side가 L2I를 bypass하고 data가 L2D 8 ways를 모두 사용한다. 평균 IPC는 +1.87%로 가장 좋다.

흥미로운 점은 L1I MPKI는 평균 +0.38 증가하지만 frontend stall은 -1.63%p 줄었다는 점이다. 즉, 단순히 L1I MPKI만으로 설명되지 않는다. L2I를 거치지 않고 LLC로 바로 내려가는 구조가 일부 instruction miss의 지연 또는 queue interaction을 바꾸면서 frontend stall을 줄인 것으로 보인다.

data side는 L1D MPKI가 거의 변하지 않고, L2D MPKI는 평균 -0.94 감소했다. `0i8d`는 data side를 보호하면서 instruction side는 L2I를 우회하는 형태라, 이번 run에서는 가장 안정적인 선택으로 보인다.

### 2i6d/4i4d/6i2d: 중간 partition은 큰 이득이 없음

중간 partition은 평균 IPC가 거의 중립 또는 소폭 하락이다.

- `2i6d`: -0.11%
- `4i4d`: -0.14%
- `6i2d`: -0.40%

`2i6d`는 특히 `sierra.a.6`에서 L2I MPKI가 +15.19 증가하고 frontend stall도 +1.52%p 증가한다. instruction에 2 ways만 주는 것은 instruction working set이 큰 workload에는 부족할 수 있다.

`6i2d`는 instruction 쪽 MPKI를 줄이지만 data 쪽 L2D MPKI를 평균 +2.16 증가시킨다. data side capacity 감소가 IPC에 부정적으로 작용한다.

### 8i0d: workload 의존성이 매우 큼

`8i0d`는 data가 L2D를 bypass하고 instruction이 L2I 전체를 사용한다.

일부 workload에서는 좋다.

- `sierra.a.6`: +4.11%
- `tango`: +3.34%
- `bravo`: +2.50%

하지만 `delta`에서는 -22.57%로 크게 무너진다. 이때 L1D MPKI가 +4.97 증가하고 backend data stall이 +11.14%p 증가한다. data L2가 없는 구조에서 data miss가 LLC로 바로 내려가면서 backend가 data wait에 묶인 것으로 해석된다.

따라서 `8i0d`는 instruction 중심 workload에는 이득이 있을 수 있지만, data miss latency에 민감한 workload에는 위험하다.

## Workload별 특징

### Instruction-side 우회/강화가 이득인 그룹

`sierra.a.6`, `tango`, `bravo`는 `8i0d` 또는 `0i8d`에서 IPC 개선이 크다.

- `sierra.a.6`: `0i8d`, `8i0d` 모두 +4% 수준
- `tango`: `8i0d` +3.34%, `0i8d` +2.22%
- `bravo`: `8i0d` +2.50%, `0i8d` +1.62%

이 그룹은 L2C를 I/D로 균등하게 나누는 것보다, 한쪽을 우회하거나 한쪽에 강하게 몰아주는 극단 정책이 더 좋은 결과를 냈다.

### Data L2가 반드시 필요한 그룹

`delta`는 `8i0d`에서 IPC가 크게 하락한다.

| Policy | IPC | L2I MPKI | L2D MPKI | Backend Data Stall |
|---|---:|---:|---:|---:|
| `shared` | 0.589 | 2.03 | 8.89 | 42.79 |
| `8i0d` | 0.456 | 0.45 | 0.00 | 53.93 |

`8i0d`에서는 L2D가 없기 때문에 L2D MPKI가 0으로 보이지만, 이것은 data miss가 사라진 것이 아니다. data request가 L2D를 bypass해서 LLC로 내려가는 구조다. backend data stall이 크게 증가한 것을 보면, 이 workload는 data L2가 IPC 유지에 매우 중요하다.

### Data way 감소에 약한 그룹

`merced`, `yankee`, `tahoe`, `sierra.a.4`는 `6i2d`에서 IPC가 소폭 하락한다. 공통적으로 L2D MPKI가 증가한다.

- `merced`: dL2D +2.47, dIPC -0.74%
- `yankee`: dL2D +1.86, dIPC -0.74%
- `tahoe`: dL2D +1.59, dIPC -0.44%
- `sierra.a.4`: dL2D +2.84, dIPC -0.62%

즉, instruction way를 늘리는 대가로 data way가 줄어들면 data side pressure가 IPC를 갉아먹는 경향이 있다.

## 결론

이번 `w10/i100` run에서 가장 중요한 결론은 다음과 같다.

- shared 대비 평균적으로는 `0i8d`가 가장 좋았다.
- 균형 partition인 `4i4d`는 거의 중립이며, 뚜렷한 이득을 주지 못했다.
- instruction way를 많이 주는 `6i2d`, `8i0d`는 일부 workload에서는 좋지만 data side 악화 위험이 있다.
- 특히 `delta`는 data L2 bypass에 매우 취약하다.
- IPC 변화는 L1/L2 MPKI 하나만으로 설명되지 않고, frontend stall과 backend data stall을 함께 봐야 한다.

연구 방향 관점에서는 단순 static partition보다 workload 특성에 따라 다음 중 하나를 선택하는 adaptive policy가 더 가능성이 있어 보인다.

- data-sensitive workload: shared 또는 data-heavy policy 유지
- frontend/instruction-sensitive workload: `0i8d` 또는 instruction-heavy policy 고려
- data backend stall이 빠르게 증가하는 workload: `8i0d` 금지

## 다음 질문

- `0i8d`의 IPC 개선이 L2I bypass 때문인지, L2D 8 ways 확보 때문인지 분리해야 한다.
- `8i0d`에서 좋아지는 workload와 무너지는 workload를 구분하는 online 지표가 필요하다.
- 후보 지표는 `backend_data_stall_pct`, `L1D MPKI`, `LLD MPKI`, `frontend_instruction_fetch_stall_pct`다.
- 더 긴 run에서 `0i8d`의 평균 우위가 유지되는지 확인해야 한다.
