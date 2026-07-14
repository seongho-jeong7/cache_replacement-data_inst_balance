# 2026-07-14 실험 노트: FTQ와 L2C I/D Partition 비교

이 문서는 2026-07-14에 진행하는 토론, 분석, 실험 결정을 실시간으로 기록한다. Daily는 나중에 별도로 요약하고, 여기에는 진행 과정과 판단 근거를 자세히 남긴다.

## 운영 방식

오늘부터 Codex와 논의하면서 나온 답변은 이 문서에도 함께 정리한다. 즉, 대화에서는 해석과 결론을 바로 설명하고, 문서에는 같은 내용을 실험 로그 형태로 누적한다.

## `260713_2013_l2c_test` 결과 상태 확인

2026-07-13에 시작한 L2C instruction/data partition 실험 결과가 `outputs/260713_2013_l2c_test`에 추가되어 있었다.

확인된 실험 축:

| 축 | 값 |
|---|---|
| Workload group | bravo, sierra.a.3, sierra.a.4, sierra.a.6, tango |
| FTQ size | 0, 4, 32 |
| L2C policy | shared, 2i6d, 4i4d, 6i2d |
| Raw logs | 1164개 |
| 상태 | 각 조합 97 traces, 97 ok, 0 failed |

`fdip_4`, `fdip_32` summary가 아직 없어서 `scripts/run.sh -s 0x21`로 생성했고, `fdip_0` summary도 새 raw 결과 기준으로 다시 생성했다.

사용한 summary 명령:

```bash
./scripts/run.sh -s 0x21 -f 0  -L2C 0xf -r 260713_2013_l2c_test
./scripts/run.sh -s 0x21 -f 4  -L2C 0xf -r 260713_2013_l2c_test
./scripts/run.sh -s 0x21 -f 32 -L2C 0xf -r 260713_2013_l2c_test
```

## FTQ별, Trace별, L2C Policy별 비교

아래 표는 각 `FTQ x trace group x L2C policy` 조합의 평균값이다. `dIPC`는 같은 FTQ와 trace group 안에서 `shared` 대비 IPC 변화율이다.

| FTQ | Trace | L2C | IPC | dIPC | L1I MPKI | L2I MPKI | L2D MPKI | L1I Stall% |
|---:|---|---|---:|---:|---:|---:|---:|---:|
| 0 | bravo | shared | 0.416 | +0.00% | 27.22 | 9.22 | 10.20 | 25.53 |
| 0 | bravo | 2i6d | 0.410 | -1.40% | 27.09 | 13.94 | 10.38 | 26.87 |
| 0 | bravo | 4i4d | 0.410 | -1.31% | 27.10 | 9.46 | 11.35 | 25.80 |
| 0 | bravo | 6i2d | 0.409 | -1.52% | 27.22 | 7.04 | 12.57 | 24.83 |
| 0 | sierra.a.3 | shared | 0.475 | +0.00% | 32.56 | 12.70 | 10.83 | 27.11 |
| 0 | sierra.a.3 | 2i6d | 0.470 | -0.88% | 32.63 | 17.95 | 9.86 | 28.63 |
| 0 | sierra.a.3 | 4i4d | 0.473 | -0.40% | 32.46 | 12.29 | 11.16 | 27.34 |
| 0 | sierra.a.3 | 6i2d | 0.473 | -0.41% | 32.51 | 8.73 | 13.10 | 25.95 |
| 0 | sierra.a.4 | shared | 0.303 | +0.00% | 30.91 | 15.43 | 14.73 | 32.55 |
| 0 | sierra.a.4 | 2i6d | 0.300 | -0.98% | 30.82 | 18.95 | 14.70 | 33.23 |
| 0 | sierra.a.4 | 4i4d | 0.299 | -1.29% | 30.76 | 15.65 | 16.25 | 32.65 |
| 0 | sierra.a.4 | 6i2d | 0.298 | -1.67% | 30.85 | 13.36 | 18.05 | 32.01 |
| 0 | sierra.a.6 | shared | 0.432 | +0.00% | 59.33 | 18.27 | 11.81 | 29.70 |
| 0 | sierra.a.6 | 2i6d | 0.425 | -1.75% | 59.54 | 31.60 | 8.97 | 33.49 |
| 0 | sierra.a.6 | 4i4d | 0.432 | +0.01% | 59.15 | 18.43 | 10.99 | 30.51 |
| 0 | sierra.a.6 | 6i2d | 0.434 | +0.48% | 59.33 | 10.96 | 14.79 | 27.29 |
| 0 | tango | shared | 0.435 | +0.00% | 21.29 | 9.52 | 9.80 | 22.76 |
| 0 | tango | 2i6d | 0.433 | -0.57% | 21.27 | 11.89 | 9.57 | 23.76 |
| 0 | tango | 4i4d | 0.432 | -0.64% | 21.23 | 8.71 | 10.66 | 22.81 |
| 0 | tango | 6i2d | 0.433 | -0.56% | 21.28 | 6.44 | 11.86 | 21.68 |
| 4 | bravo | shared | 0.474 | +0.00% | 12.59 | 0.82 | 10.28 | 11.70 |
| 4 | bravo | 2i6d | 0.469 | -0.85% | 12.65 | 1.43 | 10.75 | 12.19 |
| 4 | bravo | 4i4d | 0.468 | -1.21% | 12.41 | 0.77 | 11.73 | 11.67 |
| 4 | bravo | 6i2d | 0.465 | -1.80% | 12.26 | 0.48 | 12.81 | 11.25 |
| 4 | sierra.a.3 | shared | 0.547 | +0.00% | 16.05 | 2.13 | 10.99 | 13.87 |
| 4 | sierra.a.3 | 2i6d | 0.546 | -0.12% | 16.17 | 2.63 | 10.53 | 14.48 |
| 4 | sierra.a.3 | 4i4d | 0.543 | -0.60% | 15.57 | 1.62 | 11.95 | 13.73 |
| 4 | sierra.a.3 | 6i2d | 0.540 | -1.13% | 15.34 | 0.99 | 13.60 | 13.00 |
| 4 | sierra.a.4 | shared | 0.362 | +0.00% | 14.50 | 1.31 | 14.82 | 15.57 |
| 4 | sierra.a.4 | 2i6d | 0.359 | -0.81% | 14.55 | 1.71 | 15.42 | 15.87 |
| 4 | sierra.a.4 | 4i4d | 0.357 | -1.39% | 14.26 | 1.19 | 16.92 | 15.52 |
| 4 | sierra.a.4 | 6i2d | 0.355 | -1.93% | 14.08 | 0.87 | 18.44 | 15.18 |
| 4 | sierra.a.6 | shared | 0.498 | +0.00% | 29.88 | 4.04 | 12.15 | 15.90 |
| 4 | sierra.a.6 | 2i6d | 0.500 | +0.53% | 30.43 | 5.70 | 10.04 | 17.47 |
| 4 | sierra.a.6 | 4i4d | 0.498 | +0.10% | 29.18 | 3.00 | 12.40 | 15.67 |
| 4 | sierra.a.6 | 6i2d | 0.493 | -1.00% | 28.69 | 1.62 | 15.71 | 14.04 |
| 4 | tango | shared | 0.488 | +0.00% | 9.63 | 1.10 | 9.89 | 10.48 |
| 4 | tango | 2i6d | 0.486 | -0.34% | 9.69 | 1.32 | 10.11 | 10.82 |
| 4 | tango | 4i4d | 0.484 | -0.87% | 9.42 | 0.83 | 11.09 | 10.44 |
| 4 | tango | 6i2d | 0.482 | -1.19% | 9.22 | 0.53 | 12.07 | 9.97 |
| 32 | bravo | shared | 0.499 | +0.00% | 0.63 | 0.01 | 10.31 | 3.95 |
| 32 | bravo | 2i6d | 0.495 | -0.77% | 0.57 | 0.05 | 10.77 | 3.96 |
| 32 | bravo | 4i4d | 0.493 | -1.30% | 0.61 | 0.02 | 11.74 | 3.91 |
| 32 | bravo | 6i2d | 0.490 | -1.94% | 0.60 | 0.01 | 12.77 | 3.83 |
| 32 | sierra.a.3 | shared | 0.581 | +0.00% | 1.20 | 0.10 | 11.04 | 4.96 |
| 32 | sierra.a.3 | 2i6d | 0.583 | +0.25% | 1.12 | 0.16 | 10.60 | 5.03 |
| 32 | sierra.a.3 | 4i4d | 0.577 | -0.68% | 1.07 | 0.09 | 12.02 | 4.88 |
| 32 | sierra.a.3 | 6i2d | 0.572 | -1.57% | 1.11 | 0.05 | 13.64 | 4.76 |
| 32 | sierra.a.4 | shared | 0.391 | +0.00% | 1.05 | 0.04 | 14.86 | 5.13 |
| 32 | sierra.a.4 | 2i6d | 0.388 | -0.60% | 0.92 | 0.09 | 15.39 | 5.14 |
| 32 | sierra.a.4 | 4i4d | 0.385 | -1.38% | 0.95 | 0.05 | 16.92 | 5.04 |
| 32 | sierra.a.4 | 6i2d | 0.383 | -2.10% | 0.98 | 0.03 | 18.48 | 4.96 |
| 32 | sierra.a.6 | shared | 0.530 | +0.00% | 2.10 | 0.18 | 12.32 | 5.25 |
| 32 | sierra.a.6 | 2i6d | 0.538 | +1.60% | 2.03 | 0.30 | 10.30 | 5.47 |
| 32 | sierra.a.6 | 4i4d | 0.530 | +0.03% | 1.94 | 0.15 | 12.71 | 5.20 |
| 32 | sierra.a.6 | 6i2d | 0.520 | -1.93% | 1.98 | 0.06 | 15.94 | 4.96 |
| 32 | tango | shared | 0.509 | +0.00% | 0.48 | 0.02 | 9.91 | 3.64 |
| 32 | tango | 2i6d | 0.508 | -0.15% | 0.44 | 0.04 | 10.15 | 3.64 |
| 32 | tango | 4i4d | 0.504 | -0.85% | 0.45 | 0.02 | 11.13 | 3.58 |
| 32 | tango | 6i2d | 0.502 | -1.36% | 0.47 | 0.01 | 12.11 | 3.51 |

## 현재 해석

FTQ를 키우면 대부분 workload에서 L1I MPKI와 L1I stall 비율이 크게 줄고 IPC가 상승한다. 특히 `fdip_32`에서는 L2I MPKI가 대부분 0에 가까워져 instruction fetch miss의 L2C 압력이 거의 제거된다.

하지만 L2C를 정적으로 나눴을 때는 전반적으로 `shared`가 가장 안정적이다. `6i2d`처럼 instruction way를 많이 주면 L2I MPKI는 낮아지지만 L2D MPKI가 크게 증가하면서 IPC가 감소하는 경우가 많다. 반대로 `2i6d`는 data 쪽을 보호하지만 instruction 쪽 L2I MPKI를 악화시키는 경우가 있다.

현재 가장 눈에 띄는 예외는 `sierra.a.6`이다. `FTQ=32`에서 `2i6d`가 shared 대비 IPC를 `+1.60%` 개선한다. 이 경우는 FTQ가 instruction fetch 문제를 충분히 줄인 뒤, L2C data capacity를 더 보장하는 쪽이 유리하게 작동한 후보로 보인다.

반면 `bravo`, `sierra.a.4`, `tango`는 shared 대비 partition 정책이 대부분 IPC를 낮춘다. 이들은 static partition으로 얻는 이득보다 capacity 분할로 인한 손실이 더 큰 쪽으로 보인다.

## Shared 대비 L2C Partition 변화량

절대값 표는 전체 규모를 보기에는 좋지만, L2C partition 자체의 효과를 보려면 같은 FTQ와 trace group 안에서 `shared` 대비 변화량을 보는 편이 더 명확하다. 아래 표에서 `dIPC`는 shared 대비 비율 변화이고, 나머지 값은 shared 대비 절대 변화량이다.

### FTQ=0

| Trace | L2C | dIPC | dL1I MPKI | dL2I MPKI | dL2D MPKI | dL1I Stall%p |
|---|---|---:|---:|---:|---:|---:|
| bravo | 2i6d | -1.40% | -0.13 | +4.73 | +0.18 | +1.34 |
| bravo | 4i4d | -1.31% | -0.12 | +0.24 | +1.15 | +0.27 |
| bravo | 6i2d | -1.52% | -0.00 | -2.18 | +2.37 | -0.70 |
| sierra.a.3 | 2i6d | -0.88% | +0.07 | +5.25 | -0.97 | +1.51 |
| sierra.a.3 | 4i4d | -0.40% | -0.10 | -0.41 | +0.32 | +0.22 |
| sierra.a.3 | 6i2d | -0.41% | -0.06 | -3.97 | +2.27 | -1.17 |
| sierra.a.4 | 2i6d | -0.98% | -0.09 | +3.52 | -0.03 | +0.67 |
| sierra.a.4 | 4i4d | -1.29% | -0.15 | +0.23 | +1.52 | +0.10 |
| sierra.a.4 | 6i2d | -1.67% | -0.06 | -2.07 | +3.32 | -0.55 |
| sierra.a.6 | 2i6d | -1.75% | +0.21 | +13.33 | -2.84 | +3.79 |
| sierra.a.6 | 4i4d | +0.01% | -0.17 | +0.16 | -0.81 | +0.81 |
| sierra.a.6 | 6i2d | +0.48% | +0.00 | -7.31 | +2.98 | -2.42 |
| tango | 2i6d | -0.57% | -0.02 | +2.37 | -0.23 | +1.00 |
| tango | 4i4d | -0.64% | -0.06 | -0.81 | +0.86 | +0.05 |
| tango | 6i2d | -0.56% | -0.01 | -3.08 | +2.06 | -1.08 |

### FTQ=4

| Trace | L2C | dIPC | dL1I MPKI | dL2I MPKI | dL2D MPKI | dL1I Stall%p |
|---|---|---:|---:|---:|---:|---:|
| bravo | 2i6d | -0.85% | +0.07 | +0.60 | +0.47 | +0.49 |
| bravo | 4i4d | -1.21% | -0.18 | -0.05 | +1.45 | -0.03 |
| bravo | 6i2d | -1.80% | -0.32 | -0.35 | +2.53 | -0.44 |
| sierra.a.3 | 2i6d | -0.12% | +0.12 | +0.50 | -0.46 | +0.62 |
| sierra.a.3 | 4i4d | -0.60% | -0.49 | -0.51 | +0.95 | -0.13 |
| sierra.a.3 | 6i2d | -1.13% | -0.72 | -1.15 | +2.61 | -0.87 |
| sierra.a.4 | 2i6d | -0.81% | +0.05 | +0.40 | +0.60 | +0.30 |
| sierra.a.4 | 4i4d | -1.39% | -0.24 | -0.11 | +2.10 | -0.04 |
| sierra.a.4 | 6i2d | -1.93% | -0.42 | -0.44 | +3.62 | -0.39 |
| sierra.a.6 | 2i6d | +0.53% | +0.55 | +1.66 | -2.11 | +1.57 |
| sierra.a.6 | 4i4d | +0.10% | -0.70 | -1.04 | +0.25 | -0.23 |
| sierra.a.6 | 6i2d | -1.00% | -1.18 | -2.42 | +3.56 | -1.86 |
| tango | 2i6d | -0.34% | +0.05 | +0.22 | +0.21 | +0.34 |
| tango | 4i4d | -0.87% | -0.21 | -0.27 | +1.20 | -0.05 |
| tango | 6i2d | -1.19% | -0.42 | -0.57 | +2.18 | -0.51 |

### FTQ=32

| Trace | L2C | dIPC | dL1I MPKI | dL2I MPKI | dL2D MPKI | dL1I Stall%p |
|---|---|---:|---:|---:|---:|---:|
| bravo | 2i6d | -0.77% | -0.06 | +0.04 | +0.46 | +0.00 |
| bravo | 4i4d | -1.30% | -0.03 | +0.01 | +1.43 | -0.05 |
| bravo | 6i2d | -1.94% | -0.03 | -0.01 | +2.46 | -0.12 |
| sierra.a.3 | 2i6d | +0.25% | -0.08 | +0.06 | -0.44 | +0.07 |
| sierra.a.3 | 4i4d | -0.68% | -0.13 | -0.01 | +0.98 | -0.07 |
| sierra.a.3 | 6i2d | -1.57% | -0.09 | -0.06 | +2.60 | -0.20 |
| sierra.a.4 | 2i6d | -0.60% | -0.14 | +0.05 | +0.53 | +0.01 |
| sierra.a.4 | 4i4d | -1.38% | -0.10 | +0.01 | +2.06 | -0.09 |
| sierra.a.4 | 6i2d | -2.10% | -0.07 | -0.01 | +3.62 | -0.17 |
| sierra.a.6 | 2i6d | +1.60% | -0.07 | +0.12 | -2.03 | +0.23 |
| sierra.a.6 | 4i4d | +0.03% | -0.15 | -0.04 | +0.39 | -0.04 |
| sierra.a.6 | 6i2d | -1.93% | -0.12 | -0.12 | +3.62 | -0.28 |
| tango | 2i6d | -0.15% | -0.05 | +0.02 | +0.24 | +0.01 |
| tango | 4i4d | -0.85% | -0.03 | +0.00 | +1.21 | -0.06 |
| tango | 6i2d | -1.36% | -0.02 | -0.01 | +2.19 | -0.13 |

### 변화량 기준 해석

`6i2d`는 거의 모든 trace와 FTQ에서 `dL2I MPKI`를 낮추지만, 동시에 `dL2D MPKI`를 크게 증가시킨다. 이 증가폭은 `bravo`, `sierra.a.4`, `tango`에서 IPC 하락으로 바로 이어진다. 즉 instruction 쪽 L2C miss를 줄이는 이득보다 data 쪽 capacity 손실이 더 큰 경우가 많다.

`2i6d`는 반대로 data 쪽을 보호한다. `sierra.a.6`에서는 이 효과가 가장 뚜렷하다. 특히 `FTQ=32`에서 `dL2D MPKI=-2.03`, `dIPC=+1.60%`가 함께 나타난다. FTQ가 이미 instruction miss를 충분히 줄인 상태에서는, 추가 instruction way보다 data way 확보가 더 유리한 후보로 볼 수 있다.

`4i4d`는 shared와 가장 비슷한 정책이지만, 그래도 static partition이라는 제약 때문에 shared를 확실히 넘지는 못한다. 대체로 변화가 작고, `sierra.a.6` 일부 조건에서만 거의 동률이다.

## IPC 이득 여부에 대한 중간 결론

결과적으로 현재 실험 범위에서는 L2C I/D static partition이 IPC에 이득을 주는 경우가 거의 없다.

전체 조합은 `3 FTQ sizes x 5 trace groups x 3 partition policies = 45`개이다. 이 중 shared 대비 IPC가 증가한 경우는 아래 정도다.

| FTQ | Trace | L2C | dIPC |
|---:|---|---|---:|
| 0 | sierra.a.6 | 4i4d | +0.01% |
| 0 | sierra.a.6 | 6i2d | +0.48% |
| 4 | sierra.a.6 | 2i6d | +0.53% |
| 4 | sierra.a.6 | 4i4d | +0.10% |
| 32 | sierra.a.3 | 2i6d | +0.25% |
| 32 | sierra.a.6 | 2i6d | +1.60% |
| 32 | sierra.a.6 | 4i4d | +0.03% |

하지만 이 중 대부분은 `+0.5%` 이하라 실질적인 개선이라고 보기 어렵다. 의미 있게 볼 수 있는 후보는 사실상 `sierra.a.6 + 2i6d`이고, 특히 `FTQ=32`에서 `+1.60%`가 가장 뚜렷하다.

따라서 현재 데이터가 말하는 방향은 다음과 같다.

- `shared` L2C가 대부분의 workload에서 가장 안정적이다.
- static partition은 한쪽 miss를 줄여도 다른 쪽 capacity 손실을 만든다.
- `6i2d`는 L2I MPKI를 줄이지만 L2D MPKI 증가 때문에 IPC가 자주 하락한다.
- `2i6d`는 data capacity를 보호하므로, instruction miss가 이미 FTQ로 충분히 줄어든 workload에서만 이득 가능성이 있다.
- 현재 후보 workload는 `sierra.a.6`이며, 나머지 workload에서는 partition의 일반적 이득을 주장하기 어렵다.

이 결과만 놓고 보면 연구 방향은 "L2C를 단순히 정적으로 나누면 좋아진다"가 아니라, **instruction/data pressure와 FTQ 효과를 보고 일부 workload에서만 data-protect partition이 유효한지 찾는 방향**이 더 타당해 보인다.

## Backend Stall을 함께 봐야 하는 이유

앞선 표의 `dL1I Stall%p`는 backend stall이 아니다. 이것은 새로 추가한 Frontend Stall Breakdown 중 `frontend_stall_l1i_miss_pct`의 변화량이며, L1I miss 때문에 fetch-to-decode 승격이 막힌 비율을 의미한다.

data 쪽이 나빠져서 IPC에 악영향을 주는지 보려면 `dL2D MPKI`와 함께 기존 Backend Stall Breakdown의 `ROB/LQ/SQ` stall 변화도 같이 봐야 한다.

용어를 다시 정리하면:

- `dFF-L1I%p`: L1I miss 때문에 frontend가 막힌 비율 변화
- `dBF-ROB%p`: ROB full 때문에 dispatch가 막힌 비율 변화
- `dBF-LQ%p`: Load Queue full 때문에 dispatch가 막힌 비율 변화
- `dBF-SQ%p`: Store Queue full 때문에 dispatch가 막힌 비율 변화

### FTQ=0: data-side 영향과 backend stall 변화

| Trace | L2C | dIPC | dL2I | dL2D | dFF-L1I%p | dBF-ROB%p | dBF-LQ%p | dBF-SQ%p |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| bravo | 2i6d | -1.40% | +4.73 | +0.18 | +1.34 | -0.09 | +0.00 | -0.05 |
| bravo | 4i4d | -1.31% | +0.24 | +1.15 | +0.27 | +0.00 | -0.01 | +0.01 |
| bravo | 6i2d | -1.52% | -2.18 | +2.37 | -0.70 | +0.04 | +0.00 | +0.05 |
| sierra.a.3 | 2i6d | -0.88% | +5.25 | -0.97 | +1.51 | -0.00 | -0.00 | -0.04 |
| sierra.a.3 | 4i4d | -0.40% | -0.41 | +0.32 | +0.22 | +0.04 | +0.00 | +0.00 |
| sierra.a.3 | 6i2d | -0.41% | -3.97 | +2.27 | -1.17 | +0.06 | +0.00 | +0.04 |
| sierra.a.4 | 2i6d | -0.98% | +3.52 | -0.03 | +0.67 | +0.01 | -0.00 | -0.02 |
| sierra.a.4 | 4i4d | -1.29% | +0.23 | +1.52 | +0.10 | +0.05 | -0.00 | -0.00 |
| sierra.a.4 | 6i2d | -1.67% | -2.07 | +3.32 | -0.55 | +0.07 | -0.00 | +0.01 |
| sierra.a.6 | 2i6d | -1.75% | +13.33 | -2.84 | +3.79 | -0.06 | -0.00 | -0.09 |
| sierra.a.6 | 4i4d | +0.01% | +0.16 | -0.81 | +0.81 | -0.01 | +0.00 | -0.02 |
| sierra.a.6 | 6i2d | +0.48% | -7.31 | +2.98 | -2.42 | +0.04 | +0.00 | +0.06 |
| tango | 2i6d | -0.57% | +2.37 | -0.23 | +1.00 | -0.01 | -0.00 | -0.02 |
| tango | 4i4d | -0.64% | -0.81 | +0.86 | +0.05 | +0.04 | -0.00 | -0.00 |
| tango | 6i2d | -0.56% | -3.08 | +2.06 | -1.08 | +0.09 | -0.00 | +0.02 |

### FTQ=4: data-side 영향과 backend stall 변화

| Trace | L2C | dIPC | dL2I | dL2D | dFF-L1I%p | dBF-ROB%p | dBF-LQ%p | dBF-SQ%p |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| bravo | 2i6d | -0.85% | +0.60 | +0.47 | +0.49 | -0.02 | -0.01 | -0.01 |
| bravo | 4i4d | -1.21% | -0.05 | +1.45 | -0.03 | +0.01 | -0.00 | +0.01 |
| bravo | 6i2d | -1.80% | -0.35 | +2.53 | -0.44 | +0.03 | -0.00 | +0.03 |
| sierra.a.3 | 2i6d | -0.12% | +0.50 | -0.46 | +0.62 | +0.03 | -0.00 | -0.02 |
| sierra.a.3 | 4i4d | -0.60% | -0.51 | +0.95 | -0.13 | +0.05 | -0.00 | -0.00 |
| sierra.a.3 | 6i2d | -1.13% | -1.15 | +2.61 | -0.87 | +0.05 | +0.00 | +0.00 |
| sierra.a.4 | 2i6d | -0.81% | +0.40 | +0.60 | +0.30 | +0.04 | -0.00 | -0.01 |
| sierra.a.4 | 4i4d | -1.39% | -0.11 | +2.10 | -0.04 | +0.05 | -0.00 | -0.00 |
| sierra.a.4 | 6i2d | -1.93% | -0.44 | +3.62 | -0.39 | +0.08 | -0.00 | +0.01 |
| sierra.a.6 | 2i6d | +0.53% | +1.66 | -2.11 | +1.57 | -0.01 | -0.00 | -0.04 |
| sierra.a.6 | 4i4d | +0.10% | -1.04 | +0.25 | -0.23 | +0.01 | -0.00 | +0.01 |
| sierra.a.6 | 6i2d | -1.00% | -2.42 | +3.56 | -1.86 | +0.02 | -0.00 | +0.08 |
| tango | 2i6d | -0.34% | +0.22 | +0.21 | +0.34 | +0.03 | -0.00 | -0.01 |
| tango | 4i4d | -0.87% | -0.27 | +1.20 | -0.05 | +0.05 | -0.00 | +0.00 |
| tango | 6i2d | -1.19% | -0.57 | +2.18 | -0.51 | +0.07 | -0.00 | +0.01 |

### FTQ=32: data-side 영향과 backend stall 변화

| Trace | L2C | dIPC | dL2I | dL2D | dFF-L1I%p | dBF-ROB%p | dBF-LQ%p | dBF-SQ%p |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| bravo | 2i6d | -0.77% | +0.04 | +0.46 | +0.00 | -0.02 | +0.01 | +0.01 |
| bravo | 4i4d | -1.30% | +0.01 | +1.43 | -0.05 | +0.02 | +0.00 | +0.03 |
| bravo | 6i2d | -1.94% | -0.01 | +2.46 | -0.12 | +0.02 | +0.00 | +0.03 |
| sierra.a.3 | 2i6d | +0.25% | +0.06 | -0.44 | +0.07 | +0.04 | -0.00 | -0.00 |
| sierra.a.3 | 4i4d | -0.68% | -0.01 | +0.98 | -0.07 | +0.05 | -0.00 | -0.00 |
| sierra.a.3 | 6i2d | -1.57% | -0.06 | +2.60 | -0.20 | +0.05 | +0.00 | -0.01 |
| sierra.a.4 | 2i6d | -0.60% | +0.05 | +0.53 | +0.01 | +0.04 | -0.00 | +0.00 |
| sierra.a.4 | 4i4d | -1.38% | +0.01 | +2.06 | -0.09 | +0.06 | -0.01 | +0.00 |
| sierra.a.4 | 6i2d | -2.10% | -0.01 | +3.62 | -0.17 | +0.06 | -0.01 | +0.00 |
| sierra.a.6 | 2i6d | +1.60% | +0.12 | -2.03 | +0.23 | +0.02 | +0.00 | -0.02 |
| sierra.a.6 | 4i4d | +0.03% | -0.04 | +0.39 | -0.04 | +0.01 | -0.00 | -0.01 |
| sierra.a.6 | 6i2d | -1.93% | -0.12 | +3.62 | -0.28 | -0.01 | -0.00 | +0.01 |
| tango | 2i6d | -0.15% | +0.02 | +0.24 | +0.01 | +0.04 | -0.00 | +0.00 |
| tango | 4i4d | -0.85% | +0.00 | +1.21 | -0.06 | +0.06 | -0.00 | +0.00 |
| tango | 6i2d | -1.36% | -0.01 | +2.19 | -0.13 | +0.05 | -0.00 | -0.00 |

### Backend stall 포함 후 해석

`dL2D MPKI`가 증가하는 경우 IPC가 떨어지는 패턴은 꽤 분명하다. 예를 들어 `FTQ=32`에서 `6i2d`는 `bravo`, `sierra.a.4`, `sierra.a.6`, `tango` 모두 `dL2D MPKI`가 크게 증가하고 IPC가 하락한다.

하지만 기존 Backend Stall Breakdown의 `ROB/LQ/SQ` 변화량은 대체로 매우 작다. 대부분 `dBF-ROB%p`가 `+0.0x` 수준이고, `dBF-LQ%p`와 `dBF-SQ%p`는 거의 0에 가깝다. 따라서 현재 계측만 보면 data miss 증가가 "ROB/LQ/SQ full stall"로 크게 드러난다고 말하기는 어렵다.

현재 더 정확한 표현은 다음과 같다.

- L2C partition으로 data side가 나빠지는 것은 `dL2D MPKI`에서 보인다.
- 그 결과 IPC가 하락하는 경향도 보인다.
- 그러나 그 원인이 기존 backend full stall counter에 크게 반영되지는 않는다.
- data-side 악화가 실제로 어디서 cycles를 잃는지 보려면 load miss latency, outstanding miss/MLP, load completion delay, ROB head blocking 같은 더 직접적인 memory-stall 계측이 추가로 필요하다.

## Data Miss는 어느 단계에서 멈추는가

현재 용어가 조금 헷갈릴 수 있어서 pipeline 단계 기준으로 다시 정리한다.

### Frontend stall

현재 `frontend_stall_*`은 `O3_CPU::promote_to_decode()`에서 센다. 즉 instruction이 fetch/decode 쪽으로 넘어가는 단계다.

- `FF-L1I`: instruction fetch가 아직 완료되지 않아서 `IFETCH_BUFFER.front().fetch_completed == false`인 경우
- `FF-NoFetch`: `IFETCH_BUFFER`에 올릴 instruction 자체가 없는 경우
- `FF-Decode` 또는 기존 이름 `frontend_stall_backend_full`: decode 쪽 buffer가 꽉 차서 fetch된 instruction이 더 못 넘어가는 경우

따라서 frontend stall은 instruction stream이 앞단에서 준비되지 않거나, decode 직전이 막힌 상태를 본다.

### Backend stall

현재 `backend_stall_*`은 `O3_CPU::dispatch_instruction()`에서 센다. 즉 instruction이 `DISPATCH_BUFFER`에서 ROB/LQ/SQ로 들어가려는 순간의 자원 부족이다.

- `BF-ROB`: ROB가 꽉 차서 dispatch 불가
- `BF-LQ`: load가 들어갈 LQ entry가 부족해서 dispatch 불가
- `BF-SQ`: store가 들어갈 SQ entry가 부족해서 dispatch 불가

따라서 이 backend stall은 "instruction이 backend로 못 들어가는 상황"에 가깝다. 이미 backend 안에 들어간 load가 data를 기다리는 시간을 직접 세는 지표는 아니다.

### Data가 준비되지 않을 때

Data miss가 발생하면 load는 LQ entry와 ROB entry를 가진 상태로 남는다. `execute_load()`가 L1D read를 issue하고, data가 돌아오면 `handle_memory_return()`에서 해당 LQ entry를 찾아 `finish()`를 호출한다. 이때 ROB entry의 `completed_mem_ops`가 증가한다.

그 instruction은 `complete_inflight_instruction()`에서 아래 조건을 만족해야 completed가 된다.

```cpp
rob_it->executed &&
!rob_it->completed &&
rob_it->ready_time <= current_time &&
rob_it->completed_mem_ops == rob_it->num_mem_ops()
```

즉 data가 아직 안 왔다면 `completed_mem_ops != num_mem_ops()`라서 instruction은 completed가 되지 못한다.

그 결과:

- 해당 load 또는 그 load에 의존하는 instruction이 ROB 안에서 기다린다.
- ROB head 근처의 오래 걸리는 load가 completed되지 않으면 `retire_rob()`가 그 뒤 instruction까지 retire하지 못한다.
- retire가 막히면 ROB occupancy가 올라가고, 시간이 지나면 dispatch 단계에서 `BF-ROB`로 보일 수 있다.
- outstanding load가 많으면 LQ가 차서 dispatch 단계에서 `BF-LQ`로 보일 수 있다.

하지만 중요한 점은, data miss가 발생한 그 순간을 현재 backend stall counter가 직접 세는 것은 아니라는 점이다. 현재 counter는 그 결과가 ROB/LQ/SQ full로 번진 경우만 본다.

따라서 L2D MPKI 증가가 IPC 하락으로 이어지는 원인을 더 정확히 보려면 다음 계측이 필요하다.

- load miss가 issue된 cycle과 return된 cycle 사이 latency
- load miss 때문에 ROB head가 retire를 막은 cycle
- LQ entry가 memory return을 기다린 cycle
- outstanding load miss 개수 또는 MLP
- completed되지 않은 memory op 때문에 instruction completion이 지연된 cycle

현재 데이터에서 `dL2D MPKI`와 IPC 하락이 같이 움직이는데 `dBF-ROB/LQ/SQ` 변화는 작게 보이는 이유는, data miss penalty가 ROB/LQ/SQ full이라는 "입구 막힘"으로만 나타나지 않고, ROB 내부의 completion/retirement 지연으로 흩어져 있을 가능성이 크기 때문이다.

## Backend Stall 중 Data Stall 비율

따라서 앞으로 중요한 것은 단순한 backend stall 총량보다, **backend stall 중 data/memory stall이 차지하는 비율**이다.

현재 ChampSim_FDIP 로그에는 두 단계의 backend 관련 breakdown이 있다.

### 1차: Backend Stall Breakdown

`O3_CPU::dispatch_instruction()`에서 instruction이 backend로 들어가려는 순간의 구조적 stall을 센다.

| 항목 | 의미 | data 관련성 |
|---|---|---|
| `ROB_STALL` | ROB가 꽉 차서 dispatch 불가 | 간접적. ROB가 왜 찼는지는 추가 분해 필요 |
| `LQ_STALL` | load queue entry 부족 | data/memory structural stall |
| `SQ_STALL` | store queue entry 부족 | data/memory structural stall |

`LQ_STALL`과 `SQ_STALL`은 data/memory 계열로 보는 것이 자연스럽다. 하지만 `ROB_STALL`은 그 자체만으로는 data stall인지 아닌지 알 수 없다. ROB가 찬 이유가 오래 걸리는 load일 수도 있고, branch/compute/retire bandwidth 등 다른 이유일 수도 있다.

### 2차: ROB Stall Breakdown

`ROB_STALL`이 발생했을 때, 코드가 ROB head 상태를 보고 더 세부적으로 나눈다.

| 항목 | 코드 기준 의미 | 해석 |
|---|---|---|
| `ADDR_TRANS` | `ROB.front().stlb_miss && !ROB.front().translated` | address translation 대기. memory/data-side stall에 가까움 |
| `REPLAY_LOAD` | `ROB.front().stlb_miss && ROB.front().translated` | translation 이후 replay/load 관련 대기. data-side stall 후보 |
| `NON_REPLAY_LOAD` | `!ROB.front().stlb_miss` | STLB miss/replay-load가 아닌 ROB full. data stall이 아닐 수 있음 |

따라서 현재 로그에서 data stall 후보를 잡는다면:

```text
data-related backend stall
~= LQ_STALL + SQ_STALL + ROB_STALL 중 ADDR_TRANS/REPLAY_LOAD
```

반대로 data stall이 아닌 후보는:

```text
non-data backend stall
~= ROB_STALL 중 NON_REPLAY_LOAD
```

다만 주의할 점이 있다. `NON_REPLAY_LOAD`라는 이름은 "확실히 data와 무관하다"는 뜻이라기보다, 현재 코드가 `stlb_miss/replay-load`로 분류하지 못한 나머지 ROB full stall이다. 이 안에는 branch, non-memory instruction, retire bandwidth, 일반 dependency chain, 혹은 별도로 태깅되지 않은 memory 지연이 섞일 수 있다.

### 현재 parser의 한계

현재 `parser/parse_outputs.py`는 `====Backend Stall Breakdown====`의 `ROB_STALL/LQ_STALL/SQ_STALL`만 파싱한다. 로그에는 `====ROB Stall Breakdown====`도 출력되지만, 아직 CSV에는 `ADDR_TRANS/REPLAY_LOAD/NON_REPLAY_LOAD`가 들어가지 않는다.

따라서 다음 분석을 위해서는 parser에 아래 필드를 추가하는 것이 좋다.

```text
rob_stall_addr_trans
rob_stall_replay_load
rob_stall_non_replay_load
rob_stall_addr_trans_pct
rob_stall_replay_load_pct
rob_stall_non_replay_load_pct
backend_data_stall_pct = backend_stall_lq_pct + backend_stall_sq_pct + rob_stall_addr_trans_pct + rob_stall_replay_load_pct
backend_non_data_stall_pct = rob_stall_non_replay_load_pct
```

이렇게 해야 L2D MPKI 증가가 실제로 data-related backend pressure를 키웠는지, 아니면 IPC 하락이 ROB 내부의 completion/retirement 지연처럼 현재 counter가 잘 못 보는 영역에서 생기는지 더 명확하게 판단할 수 있다.

## CSV에 Combined Stall 지표 추가

`parser/parse_outputs.py`에 `====ROB Stall Breakdown====`의 `== Total ==` 섹션 파싱을 추가했다. 이제 `metrics.csv`에는 기존 `ROB_STALL/LQ_STALL/SQ_STALL` 외에 ROB stall의 세부 항목도 포함된다.

추가된 raw/pct 필드:

```text
rob_stall_addr_trans
rob_stall_replay_load
rob_stall_non_replay_load
rob_stall_addr_trans_pct
rob_stall_replay_load_pct
rob_stall_non_replay_load_pct
```

그리고 현재 논의 기준에 맞춰 아래 combined stall 지표를 추가했다.

```text
frontend_instruction_fetch_stall
frontend_instruction_fetch_stall_pct
backend_instruction_stall
backend_instruction_stall_pct
backend_data_stall
backend_data_stall_pct
```

정의:

```text
frontend_instruction_fetch_stall = frontend_stall_l1i_miss
backend_instruction_stall = backend_stall_lq + backend_stall_sq + rob_stall_addr_trans + rob_stall_replay_load
backend_data_stall = rob_stall_non_replay_load
```

주의: 이 이름은 오늘 논의의 실험적 분류를 따른 것이다. 코드 의미만 보면 `LQ/SQ + ADDR_TRANS/REPLAY_LOAD`는 memory/data-related backend pressure에 가깝고, `NON_REPLAY_LOAD`는 ROB full 중 STLB miss/replay-load로 분류되지 않은 나머지다. 따라서 최종 논문/문서 용어로 쓰기 전에는 이름을 다시 다듬을 필요가 있다.

기존 `260713_2013_l2c_test`의 `fdip_0`, `fdip_4`, `fdip_32` summary CSV를 새 parser 기준으로 다시 생성했다.

### Combined stall 변화량 요약

아래 표는 shared 대비 변화량이다. `dFE-IFetch%p`는 `frontend_instruction_fetch_stall_pct`, `dBE-Inst%p`는 `backend_instruction_stall_pct`, `dBE-Data%p`는 `backend_data_stall_pct`의 변화량이다.

#### FTQ=0

| Trace | L2C | dIPC | dL2D | dFE-IFetch%p | dBE-Inst%p | dBE-Data%p |
|---|---|---:|---:|---:|---:|---:|
| bravo | 2i6d | -1.40% | +0.18 | +1.34 | -0.08 | -0.05 |
| bravo | 4i4d | -1.31% | +1.15 | +0.27 | -0.01 | +0.02 |
| bravo | 6i2d | -1.52% | +2.37 | -0.70 | +0.05 | +0.04 |
| sierra.a.3 | 2i6d | -0.88% | -0.97 | +1.51 | -0.06 | +0.02 |
| sierra.a.3 | 4i4d | -0.40% | +0.32 | +0.22 | -0.00 | +0.05 |
| sierra.a.3 | 6i2d | -0.41% | +2.27 | -1.17 | +0.04 | +0.07 |
| sierra.a.4 | 2i6d | -0.98% | -0.03 | +0.67 | -0.03 | +0.02 |
| sierra.a.4 | 4i4d | -1.29% | +1.52 | +0.10 | +0.00 | +0.04 |
| sierra.a.4 | 6i2d | -1.67% | +3.32 | -0.55 | +0.03 | +0.05 |
| sierra.a.6 | 2i6d | -1.75% | -2.84 | +3.79 | -0.12 | -0.02 |
| sierra.a.6 | 4i4d | +0.01% | -0.81 | +0.81 | -0.03 | -0.00 |
| sierra.a.6 | 6i2d | +0.48% | +2.98 | -2.42 | +0.07 | +0.02 |
| tango | 2i6d | -0.57% | -0.23 | +1.00 | -0.04 | +0.01 |
| tango | 4i4d | -0.64% | +0.86 | +0.05 | -0.01 | +0.05 |
| tango | 6i2d | -0.56% | +2.06 | -1.08 | +0.03 | +0.08 |

#### FTQ=4

| Trace | L2C | dIPC | dL2D | dFE-IFetch%p | dBE-Inst%p | dBE-Data%p |
|---|---|---:|---:|---:|---:|---:|
| bravo | 2i6d | -0.85% | +0.47 | +0.49 | -0.04 | +0.00 |
| bravo | 4i4d | -1.21% | +1.45 | -0.03 | -0.00 | +0.02 |
| bravo | 6i2d | -1.80% | +2.53 | -0.44 | +0.02 | +0.04 |
| sierra.a.3 | 2i6d | -0.12% | -0.46 | +0.62 | -0.03 | +0.03 |
| sierra.a.3 | 4i4d | -0.60% | +0.95 | -0.13 | -0.00 | +0.05 |
| sierra.a.3 | 6i2d | -1.13% | +2.61 | -0.87 | +0.00 | +0.05 |
| sierra.a.4 | 2i6d | -0.81% | +0.60 | +0.30 | -0.01 | +0.04 |
| sierra.a.4 | 4i4d | -1.39% | +2.10 | -0.04 | +0.01 | +0.03 |
| sierra.a.4 | 6i2d | -1.93% | +3.62 | -0.39 | +0.02 | +0.06 |
| sierra.a.6 | 2i6d | +0.53% | -2.11 | +1.57 | -0.05 | -0.00 |
| sierra.a.6 | 4i4d | +0.10% | +0.25 | -0.23 | +0.01 | +0.01 |
| sierra.a.6 | 6i2d | -1.00% | +3.56 | -1.86 | +0.08 | +0.02 |
| tango | 2i6d | -0.34% | +0.21 | +0.34 | -0.01 | +0.04 |
| tango | 4i4d | -0.87% | +1.20 | -0.05 | -0.01 | +0.06 |
| tango | 6i2d | -1.19% | +2.18 | -0.51 | +0.00 | +0.08 |

#### FTQ=32

| Trace | L2C | dIPC | dL2D | dFE-IFetch%p | dBE-Inst%p | dBE-Data%p |
|---|---|---:|---:|---:|---:|---:|
| bravo | 2i6d | -0.77% | +0.46 | +0.00 | +0.00 | -0.01 |
| bravo | 4i4d | -1.30% | +1.43 | -0.05 | +0.02 | +0.03 |
| bravo | 6i2d | -1.94% | +2.46 | -0.12 | +0.03 | +0.03 |
| sierra.a.3 | 2i6d | +0.25% | -0.44 | +0.07 | -0.01 | +0.05 |
| sierra.a.3 | 4i4d | -0.68% | +0.98 | -0.07 | -0.01 | +0.06 |
| sierra.a.3 | 6i2d | -1.57% | +2.60 | -0.20 | -0.02 | +0.07 |
| sierra.a.4 | 2i6d | -0.60% | +0.53 | +0.01 | -0.00 | +0.04 |
| sierra.a.4 | 4i4d | -1.38% | +2.06 | -0.09 | +0.00 | +0.05 |
| sierra.a.4 | 6i2d | -2.10% | +3.62 | -0.17 | +0.00 | +0.06 |
| sierra.a.6 | 2i6d | +1.60% | -2.03 | +0.23 | -0.00 | +0.01 |
| sierra.a.6 | 4i4d | +0.03% | +0.39 | -0.04 | -0.01 | +0.01 |
| sierra.a.6 | 6i2d | -1.93% | +3.62 | -0.28 | -0.00 | +0.01 |
| tango | 2i6d | -0.15% | +0.24 | +0.01 | +0.01 | +0.04 |
| tango | 4i4d | -0.85% | +1.21 | -0.06 | -0.01 | +0.07 |
| tango | 6i2d | -1.36% | +2.19 | -0.13 | -0.02 | +0.07 |

### Combined stall 기준 해석

새 combined stall 지표를 보아도 IPC 하락과 가장 직접적으로 같이 움직이는 것은 여전히 `dL2D`다. `6i2d`는 대체로 `dL2D`가 증가하고 IPC가 하락한다.

반면 `dBE-Inst%p`와 `dBE-Data%p` 변화량은 대부분 매우 작다. 특히 `FTQ=32`에서는 `6i2d`가 `sierra.a.4`에서 `dL2D=+3.62`, `dIPC=-2.10%`를 보이지만 `dBE-Inst%p=+0.00`, `dBE-Data%p=+0.06` 정도에 그친다.

따라서 현재 combined stall 지표는 CSV에서 비교 가능한 형태로 만들어졌지만, data miss penalty의 cycle 손실을 충분히 직접적으로 포착하지는 못한다. 다음 계측은 `load miss latency`, `ROB head blocking`, `memory op completion delay`, `MLP/outstanding miss` 쪽이 더 필요하다.

## Trace-FTQ-L2C 계층별 전체 변화량 표

아래 표는 `Trace -> FTQ -> L2C` 순서로 정렬했다. 각 trace와 FTQ 안에서 `shared`를 기준선으로 두고, shared 행은 변화량을 0으로 표시했다.

포함한 값:

- `IPC`: 해당 조합의 평균 IPC
- `dIPC`: 같은 trace/FTQ의 shared 대비 IPC 변화율
- `dL1I MPKI`, `dL2I MPKI`: instruction-side 변화량
- `dFrontend Stall%p`: `frontend_instruction_fetch_stall_pct` 변화량
- `dBackend Inst Stall%p`: `backend_instruction_stall_pct` 변화량
- `dL1D MPKI`, `dL2D MPKI`: data-side 변화량
- `dBackend Data Stall%p`: `backend_data_stall_pct` 변화량
- `dL2C MPKI`: 전체 L2C MPKI 변화량

| Trace | FTQ | L2C | IPC | dIPC | dL1I MPKI | dL2I MPKI | dFrontend Stall%p | dBackend Inst Stall%p | dL1D MPKI | dL2D MPKI | dBackend Data Stall%p | dL2C MPKI |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bravo | 0 | shared | 0.416 | +0.00% | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 |
| bravo | 0 | 2i6d | 0.410 | -1.40% | -0.13 | +4.73 | +1.34 | -0.08 | +0.01 | +0.18 | -0.05 | +4.91 |
| bravo | 0 | 4i4d | 0.410 | -1.31% | -0.12 | +0.24 | +0.27 | -0.01 | +0.07 | +1.15 | +0.02 | +1.39 |
| bravo | 0 | 6i2d | 0.409 | -1.52% | -0.00 | -2.18 | -0.70 | +0.05 | +0.15 | +2.37 | +0.04 | +0.19 |
| bravo | 4 | shared | 0.474 | +0.00% | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 |
| bravo | 4 | 2i6d | 0.469 | -0.85% | +0.07 | +0.60 | +0.49 | -0.04 | +0.03 | +0.47 | +0.00 | +1.08 |
| bravo | 4 | 4i4d | 0.468 | -1.21% | -0.18 | -0.05 | -0.03 | -0.00 | +0.10 | +1.45 | +0.02 | +1.40 |
| bravo | 4 | 6i2d | 0.465 | -1.80% | -0.32 | -0.35 | -0.44 | +0.02 | +0.14 | +2.53 | +0.04 | +2.18 |
| bravo | 32 | shared | 0.499 | +0.00% | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 |
| bravo | 32 | 2i6d | 0.495 | -0.77% | -0.06 | +0.04 | +0.00 | +0.00 | +0.03 | +0.46 | -0.01 | +0.50 |
| bravo | 32 | 4i4d | 0.493 | -1.30% | -0.03 | +0.01 | -0.05 | +0.02 | +0.10 | +1.43 | +0.03 | +1.43 |
| bravo | 32 | 6i2d | 0.490 | -1.94% | -0.03 | -0.01 | -0.12 | +0.03 | +0.13 | +2.46 | +0.03 | +2.46 |
| sierra.a.3 | 0 | shared | 0.475 | +0.00% | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 |
| sierra.a.3 | 0 | 2i6d | 0.470 | -0.88% | +0.07 | +5.25 | +1.51 | -0.06 | -0.06 | -0.97 | +0.02 | +4.28 |
| sierra.a.3 | 0 | 4i4d | 0.473 | -0.40% | -0.10 | -0.41 | +0.22 | -0.00 | +0.02 | +0.32 | +0.05 | -0.08 |
| sierra.a.3 | 0 | 6i2d | 0.473 | -0.41% | -0.06 | -3.97 | -1.17 | +0.04 | +0.14 | +2.27 | +0.07 | -1.71 |
| sierra.a.3 | 4 | shared | 0.547 | +0.00% | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 |
| sierra.a.3 | 4 | 2i6d | 0.546 | -0.12% | +0.12 | +0.50 | +0.62 | -0.03 | -0.01 | -0.46 | +0.03 | +0.04 |
| sierra.a.3 | 4 | 4i4d | 0.543 | -0.60% | -0.49 | -0.51 | -0.13 | -0.00 | +0.09 | +0.95 | +0.05 | +0.44 |
| sierra.a.3 | 4 | 6i2d | 0.540 | -1.13% | -0.72 | -1.15 | -0.87 | +0.00 | +0.17 | +2.61 | +0.05 | +1.46 |
| sierra.a.3 | 32 | shared | 0.581 | +0.00% | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 |
| sierra.a.3 | 32 | 2i6d | 0.583 | +0.25% | -0.08 | +0.06 | +0.07 | -0.01 | -0.02 | -0.44 | +0.05 | -0.38 |
| sierra.a.3 | 32 | 4i4d | 0.577 | -0.68% | -0.13 | -0.01 | -0.07 | -0.01 | +0.07 | +0.98 | +0.06 | +0.96 |
| sierra.a.3 | 32 | 6i2d | 0.572 | -1.57% | -0.09 | -0.06 | -0.20 | -0.02 | +0.15 | +2.60 | +0.07 | +2.54 |
| sierra.a.4 | 0 | shared | 0.303 | +0.00% | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 |
| sierra.a.4 | 0 | 2i6d | 0.300 | -0.98% | -0.09 | +3.52 | +0.67 | -0.03 | +0.04 | -0.03 | +0.02 | +3.49 |
| sierra.a.4 | 0 | 4i4d | 0.299 | -1.29% | -0.15 | +0.23 | +0.10 | +0.00 | +0.18 | +1.52 | +0.04 | +1.75 |
| sierra.a.4 | 0 | 6i2d | 0.298 | -1.67% | -0.06 | -2.07 | -0.55 | +0.03 | +0.30 | +3.32 | +0.05 | +1.25 |
| sierra.a.4 | 4 | shared | 0.362 | +0.00% | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 |
| sierra.a.4 | 4 | 2i6d | 0.359 | -0.81% | +0.05 | +0.40 | +0.30 | -0.01 | +0.08 | +0.60 | +0.04 | +1.00 |
| sierra.a.4 | 4 | 4i4d | 0.357 | -1.39% | -0.24 | -0.11 | -0.04 | +0.01 | +0.21 | +2.10 | +0.03 | +1.98 |
| sierra.a.4 | 4 | 6i2d | 0.355 | -1.93% | -0.42 | -0.44 | -0.39 | +0.02 | +0.29 | +3.62 | +0.06 | +3.18 |
| sierra.a.4 | 32 | shared | 0.391 | +0.00% | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 |
| sierra.a.4 | 32 | 2i6d | 0.388 | -0.60% | -0.14 | +0.05 | +0.01 | -0.00 | +0.08 | +0.53 | +0.04 | +0.58 |
| sierra.a.4 | 32 | 4i4d | 0.385 | -1.38% | -0.10 | +0.01 | -0.09 | +0.00 | +0.20 | +2.06 | +0.05 | +2.07 |
| sierra.a.4 | 32 | 6i2d | 0.383 | -2.10% | -0.07 | -0.01 | -0.17 | +0.00 | +0.29 | +3.62 | +0.06 | +3.61 |
| sierra.a.6 | 0 | shared | 0.432 | +0.00% | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 |
| sierra.a.6 | 0 | 2i6d | 0.425 | -1.75% | +0.21 | +13.33 | +3.79 | -0.12 | -0.19 | -2.84 | -0.02 | +10.49 |
| sierra.a.6 | 0 | 4i4d | 0.432 | +0.01% | -0.17 | +0.16 | +0.81 | -0.03 | -0.04 | -0.81 | -0.00 | -0.65 |
| sierra.a.6 | 0 | 6i2d | 0.434 | +0.48% | +0.00 | -7.31 | -2.42 | +0.07 | +0.21 | +2.98 | +0.02 | -4.33 |
| sierra.a.6 | 4 | shared | 0.498 | +0.00% | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 |
| sierra.a.6 | 4 | 2i6d | 0.500 | +0.53% | +0.55 | +1.66 | +1.57 | -0.05 | -0.15 | -2.11 | -0.00 | -0.45 |
| sierra.a.6 | 4 | 4i4d | 0.498 | +0.10% | -0.70 | -1.04 | -0.23 | +0.01 | +0.02 | +0.25 | +0.01 | -0.79 |
| sierra.a.6 | 4 | 6i2d | 0.493 | -1.00% | -1.18 | -2.42 | -1.86 | +0.08 | +0.22 | +3.56 | +0.02 | +1.13 |
| sierra.a.6 | 32 | shared | 0.530 | +0.00% | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 |
| sierra.a.6 | 32 | 2i6d | 0.538 | +1.60% | -0.07 | +0.12 | +0.23 | -0.00 | -0.11 | -2.03 | +0.01 | -1.91 |
| sierra.a.6 | 32 | 4i4d | 0.530 | +0.03% | -0.15 | -0.04 | -0.04 | -0.01 | +0.05 | +0.39 | +0.01 | +0.36 |
| sierra.a.6 | 32 | 6i2d | 0.520 | -1.93% | -0.12 | -0.12 | -0.28 | -0.00 | +0.22 | +3.62 | +0.01 | +3.49 |
| tango | 0 | shared | 0.435 | +0.00% | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 |
| tango | 0 | 2i6d | 0.433 | -0.57% | -0.02 | +2.37 | +1.00 | -0.04 | +0.01 | -0.23 | +0.01 | +2.14 |
| tango | 0 | 4i4d | 0.432 | -0.64% | -0.06 | -0.81 | +0.05 | -0.01 | +0.09 | +0.86 | +0.05 | +0.05 |
| tango | 0 | 6i2d | 0.433 | -0.56% | -0.01 | -3.08 | -1.08 | +0.03 | +0.17 | +2.06 | +0.08 | -1.03 |
| tango | 4 | shared | 0.488 | +0.00% | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 |
| tango | 4 | 2i6d | 0.486 | -0.34% | +0.05 | +0.22 | +0.34 | -0.01 | +0.04 | +0.21 | +0.04 | +0.43 |
| tango | 4 | 4i4d | 0.484 | -0.87% | -0.21 | -0.27 | -0.05 | -0.01 | +0.10 | +1.20 | +0.06 | +0.93 |
| tango | 4 | 6i2d | 0.482 | -1.19% | -0.42 | -0.57 | -0.51 | +0.00 | +0.16 | +2.18 | +0.08 | +1.60 |
| tango | 32 | shared | 0.509 | +0.00% | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 |
| tango | 32 | 2i6d | 0.508 | -0.15% | -0.05 | +0.02 | +0.01 | +0.01 | +0.05 | +0.24 | +0.04 | +0.26 |
| tango | 32 | 4i4d | 0.504 | -0.85% | -0.03 | +0.00 | -0.06 | -0.01 | +0.11 | +1.21 | +0.07 | +1.21 |
| tango | 32 | 6i2d | 0.502 | -1.36% | -0.02 | -0.01 | -0.13 | -0.02 | +0.16 | +2.19 | +0.07 | +2.18 |

## L2C I/D Split 검산

L2C partition 설정은 run output의 config에 정상적으로 저장되어 있다.

| Config | partition | instruction_ways | data_ways |
|---|---|---:|---:|
| `champsim_l2cshared.json` | shared | 4 | 4 |
| `champsim_l2c2i6d.json` | static | 2 | 6 |
| `champsim_l2c4i4d.json` | static | 4 | 4 |
| `champsim_l2c6i2d.json` | static | 6 | 2 |

그리고 현재 parser가 사용하는 demand MPKI 기준에서는 아래 관계가 성립한다.

```text
L2C MPKI = L2I MPKI + L2D MPKI
```

전체 `260713_2013_l2c_test` summary CSV를 대상으로 확인한 결과, 최대 차이는 `7.1e-15` 수준이었다. 이는 부동소수점 연산 오차라서 사실상 완전히 일치한다고 보면 된다.

주의할 점은 ChampSim raw log의 `L2C TOTAL`과 parser의 `L2C MPKI`가 같은 의미가 아니라는 것이다.

Raw log 예시:

```text
cpu0->cpu0_L2C TOTAL        ACCESS ... MISS ...
cpu0->cpu0_L2C LOAD         ACCESS ... MISS ...
cpu0->cpu0_L2C RFO          ACCESS ... MISS ...
cpu0->cpu0_L2C PREFETCH     ACCESS ... MISS ...
cpu0->cpu0_L2C WRITE        ACCESS ... MISS ...
cpu0->cpu0_L2C TRANSLATION  ACCESS ... MISS ...

cpu0->cpu0_L2C TOTAL_I      ...
cpu0->cpu0_L2C LOAD_I       ...
cpu0->cpu0_L2C RFO_I        ...
cpu0->cpu0_L2C PREFETCH_I   ...

cpu0->cpu0_L2C TOTAL_D      ...
cpu0->cpu0_L2C LOAD_D       ...
cpu0->cpu0_L2C RFO_D        ...
cpu0->cpu0_L2C PREFETCH_D   ...
```

`TOTAL_I + TOTAL_D = TOTAL`은 전체 request class 기준으로 맞지만, 여기에는 demand뿐 아니라 `PREFETCH`, `WRITE`, `TRANSLATION`도 포함된다.

반면 parser의 현재 MPKI 정의는 demand cache miss만 본다.

```text
L2C MPKI = (L2C LOAD miss + L2C RFO miss) / instructions * 1000
L2I MPKI = (L2C LOAD_I miss + L2C RFO_I miss) / instructions * 1000
L2D MPKI = (L2C LOAD_D miss + L2C RFO_D miss) / instructions * 1000
```

따라서 CSV의 `L2C MPKI`와 `L2I+L2D MPKI`는 일치한다. 만약 raw log의 `L2C TOTAL MPKI` 같은 값을 따로 계산한다면, 그 값은 prefetch/write/translation까지 포함하므로 `L2I MPKI + L2D MPKI`와 다르게 보일 수 있다.

## IPC 개선/악화 Top 5

non-shared L2C policy만 대상으로 shared 대비 `dIPC`를 정렬했다.

### IPC 개선 Top 5

| Rank | Trace | FTQ | L2C | IPC | dIPC | dL1I | dL2I | dFE%p | dBE-Inst%p | dL1D | dL2D | dBE-Data%p | dL2C |
|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | sierra.a.6 | 32 | 2i6d | 0.538 | +1.60% | -0.07 | +0.12 | +0.23 | -0.00 | -0.11 | -2.03 | +0.01 | -1.91 |
| 2 | sierra.a.6 | 4 | 2i6d | 0.500 | +0.53% | +0.55 | +1.66 | +1.57 | -0.05 | -0.15 | -2.11 | -0.00 | -0.45 |
| 3 | sierra.a.6 | 0 | 6i2d | 0.434 | +0.48% | +0.00 | -7.31 | -2.42 | +0.07 | +0.21 | +2.98 | +0.02 | -4.33 |
| 4 | sierra.a.3 | 32 | 2i6d | 0.583 | +0.25% | -0.08 | +0.06 | +0.07 | -0.01 | -0.02 | -0.44 | +0.05 | -0.38 |
| 5 | sierra.a.6 | 4 | 4i4d | 0.498 | +0.10% | -0.70 | -1.04 | -0.23 | +0.01 | +0.02 | +0.25 | +0.01 | -0.79 |

가장 의미 있는 개선은 `sierra.a.6 / FTQ=32 / 2i6d`의 `+1.60%`이다. 나머지 개선은 대부분 `+0.5%` 이하라 효과가 작다. 개선 상위권은 거의 `sierra.a.6`에 집중되어 있으며, `2i6d`가 data-side MPKI를 낮출 때 IPC가 좋아지는 패턴이 보인다.

### IPC 악화 Top 5

| Rank | Trace | FTQ | L2C | IPC | dIPC | dL1I | dL2I | dFE%p | dBE-Inst%p | dL1D | dL2D | dBE-Data%p | dL2C |
|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | sierra.a.4 | 32 | 6i2d | 0.383 | -2.10% | -0.07 | -0.01 | -0.17 | +0.00 | +0.29 | +3.62 | +0.06 | +3.61 |
| 2 | bravo | 32 | 6i2d | 0.490 | -1.94% | -0.03 | -0.01 | -0.12 | +0.03 | +0.13 | +2.46 | +0.03 | +2.46 |
| 3 | sierra.a.6 | 32 | 6i2d | 0.520 | -1.93% | -0.12 | -0.12 | -0.28 | -0.00 | +0.22 | +3.62 | +0.01 | +3.49 |
| 4 | sierra.a.4 | 4 | 6i2d | 0.355 | -1.93% | -0.42 | -0.44 | -0.39 | +0.02 | +0.29 | +3.62 | +0.06 | +3.18 |
| 5 | bravo | 4 | 6i2d | 0.465 | -1.80% | -0.32 | -0.35 | -0.44 | +0.02 | +0.14 | +2.53 | +0.04 | +2.18 |

악화 상위 5개는 모두 `6i2d`이다. 공통적으로 L1I/L2I/frontend stall은 좋아지거나 거의 변하지 않는데, `dL2D`와 `dL2C`가 크게 증가한다. 즉 instruction way를 늘린 이득보다 data way 축소의 손실이 더 크게 나타난다.

## 0i8d L2C instruction bypass 검증 계획

`0i8d`는 단순히 instruction way를 0개로 제한하는 정책이 아니라, instruction-fetch origin request가 L2C를 lookup/fill 하지 않고 LLC로 바로 가도록 하는 정책으로 정의했다.

검증 목표:

- `shared`에서는 L1I miss 이후 instruction-origin request가 L2C를 조회하므로 `cpu0_L2C LOAD_I` access/miss가 관측되어야 한다.
- `0i8d`에서는 instruction-origin request가 L2C tag lookup을 건너뛰고 LLC로 forward되어야 하므로 `cpu0_L2C LOAD_I` access/miss가 0이어야 한다.
- `0i8d`에서도 LLC는 instruction-origin request를 받아야 하므로 `LLC LOAD_I` access/miss는 관측되어야 한다.

검증용 command:

```bash
./scripts/run.sh \
  -C ChampSim_FDIP \
  -T trace_gtrace_sierra.a.6_one.txt \
  -r 260714_l2c_bypass_check \
  -f 0x01 \
  -L2C 0x03 \
  -w 1000 \
  -i 5000 \
  -p 2 \
  -b \
  -t
```

설정 의미:

- `-f 0x01`: FTQ 0, FDIP off. L2C bypass 동작 자체만 보기 위해 FDIP 변수는 제거한다.
- `-L2C 0x03`: `shared`와 `0i8d`만 실행한다. 실제 검증 당시에는 old mapping에서 `0x11`을 사용했지만, 이후 L2C mask를 한 칸씩 밀어 `0x02=0i8d`로 정리했으므로 현재 기준 command는 `0x03`이다.
- `-T trace_gtrace_sierra.a.6_one.txt`: `sierra.a.6_0000` 단일 trace만 사용한다.
- 검증 후 `trace_gtrace_sierra.a.6_one.txt`는 임시 파일이므로 삭제했다.

## 0i8d L2C instruction bypass 검증 결과

실행 결과:

- run id: `260714_l2c_bypass_check`
- trace: `gtrace_v2/sierra.a.6/sierra.a.6_0000.champsim.gz`
- warmup/simulation: `1000 / 5000`
- FTQ: `0`
- L2C policies: `shared`, `0i8d`
- build/run: 성공. `run.log`에는 기존 `O3_CPU::L1I_bus` 초기화 순서 warning이 반복되지만 link와 trace 실행은 완료됐다.

생성된 raw log:

```text
outputs/260714_l2c_bypass_check/raw/fdip_0/shared/gtrace_v2/sierra.a.6/bimodal-basic_btb-no-ip_stride-ip_stride-l2cshared-no-lru-1core-ftq0-shared---sierra.a.6_0000.champsim.gz.log
outputs/260714_l2c_bypass_check/raw/fdip_0/0i8d/gtrace_v2/sierra.a.6/bimodal-basic_btb-no-ip_stride-ip_stride-l2c0i8d-no-lru-1core-ftq0-0i8d---sierra.a.6_0000.champsim.gz.log
```

확인 방법:

```bash
rg -n "cpu0->cpu0_L2C (TOTAL_I|LOAD_I)|cpu0->LLC (TOTAL_I|LOAD_I)" \
  outputs/260714_l2c_bypass_check/raw/fdip_0/{shared,0i8d}/gtrace_v2/sierra.a.6/*.log
```

Raw log 핵심 비교:

| L2C policy | cpu0_L2C TOTAL_I | cpu0_L2C LOAD_I | LLC TOTAL_I | LLC LOAD_I |
|---|---:|---:|---:|---:|
| shared | ACCESS 218 / MISS 218 | ACCESS 218 / MISS 218 | ACCESS 218 / MISS 218 | ACCESS 218 / MISS 218 |
| 0i8d | ACCESS 0 / MISS 0 | ACCESS 0 / MISS 0 | ACCESS 218 / MISS 218 | ACCESS 218 / MISS 218 |

해석:

- `shared`에서는 L1I miss 이후 instruction-origin request가 L2C에서 `LOAD_I`로 관측된다.
- `0i8d`에서는 L2C의 `TOTAL_I`, `LOAD_I`가 모두 0이다. 즉 instruction-origin request가 L2C tag lookup을 수행하지 않는다.
- 동시에 `0i8d`에서도 LLC의 `TOTAL_I`, `LOAD_I`는 `218/218`로 유지된다. 즉 instruction-origin request가 사라진 것이 아니라 L2C를 건너뛰어 LLC에 도달했다.

Summary CSV 비교:

| L2C policy | IPC | L1I MPKI | L2I MPKI | L2D MPKI | L2C MPKI | LLC MPKI |
|---|---:|---:|---:|---:|---:|---:|
| shared | 0.07678 | 54.956 | 43.565 | 31.974 | 75.540 | 75.340 |
| 0i8d | 0.07678 | 54.956 | 0.000 | 31.974 | 31.974 | 75.340 |

결론:

`0i8d`의 목적대로 instruction-fetch origin traffic은 L2C를 skip하고 LLC에서만 관측된다. `L2I MPKI`가 0으로 내려가고, `L2C MPKI`가 data-side 값만 남는 것도 이 동작과 일치한다. 이 검증은 매우 작은 instruction 수로 수행했으므로 성능 판단용이 아니라 기능 동작 확인용으로만 사용한다.

## 260713_2013_l2c_test에 0i8d 추가 실행

기존 `260713_2013_l2c_test`는 처음에는 `sierra.a.6`만 실행했지만, 이후 추가 실행을 통해 다음 5개 trace group이 포함된 상태였다.

```text
bravo
sierra.a.3
sierra.a.4
sierra.a.6
tango
```

따라서 `0i8d`도 같은 범위로 추가 실행한다. 기존 raw 결과 기준 FTQ는 `0`, `4`, `32`이므로 FTQ mask는 `0x15`이다.

새 L2C mask mapping:

```text
0x01 shared
0x02 0i8d
0x04 2i6d
0x08 4i4d
0x10 6i2d
0x1d old four modes
0x1f all
```

trace list 재생성:

```bash
find -L traces/gtrace_v2/bravo \
        traces/gtrace_v2/sierra.a.3 \
        traces/gtrace_v2/sierra.a.4 \
        traces/gtrace_v2/sierra.a.6 \
        traces/gtrace_v2/tango \
  -type f \
  | sed 's#^traces/##' \
  | sort > traces/trace_gtrace_l2c_5groups.txt
```

생성 결과:

```text
97 traces/trace_gtrace_l2c_5groups.txt
```

실행 command:

```bash
./scripts/run.sh -C ChampSim_FDIP -b -t \
  -T trace_gtrace_l2c_5groups.txt \
  -f 0x15 \
  -L2C 0x02 \
  -w 2000000 \
  -i 10000000 \
  -r 260713_2013_l2c_test \
  -p 50
```

예상 job 수:

```text
97 traces x 3 FTQ settings x 1 L2C policy = 291 jobs
```

주의:

- `-b`를 포함하므로 현재 스크립트 구조상 L2C policy 바이너리 전체를 다시 build한다.
- 실제 실행은 `-L2C 0x02`, 즉 `0i8d`만 수행한다.

실행 결과:

```text
raw/fdip_0/0i8d  : 97 logs
raw/fdip_4/0i8d  : 97 logs
raw/fdip_32/0i8d : 97 logs
total            : 291 logs
```

실행 시간:

```text
build 포함 기준:
  2026-07-14 19:39:13 ~ 2026-07-14 20:06:34
  약 27분 21초

raw 결과 생성 기준:
  2026-07-14 19:42:00 ~ 2026-07-14 20:06:34
  약 24분 35초
```

job당 평균 처리 시간:

```text
build 포함 wall time / 291 jobs = 약 5.64초/job
raw 생성 wall time / 291 jobs  = 약 5.07초/job
```

이 값은 `-p 50` 병렬 실행의 전체 처리량을 job 수로 나눈 값이다. 단일 job 하나가 실제로 5초 만에 끝난다는 의미는 아니고, 병렬 처리된 전체 wall-clock throughput 기준이다. 대략적인 단일 job 평균 실행시간은 `5.07초 x 50 ~= 253초`, 즉 4분대 정도로 추정된다.

## 전체 FDIP x L2C x trace 장기 실행 시간 추정

질문:

```text
모든 FDIP, 모든 L2C, 모든 traces에 대해
w=20000000, i=100000000, -p56으로 돌리면 얼마나 걸릴까?
```

job 수:

```text
343 traces x 6 FTQ settings x 5 L2C policies = 10290 jobs
```

비교 기준:

```text
기준 실행: w=2000000, i=10000000, -p50
291 jobs raw 생성 시간: 약 24분 35초 = 1475초
처리량 기준: 1475 / 291 = 약 5.07초/job
```

새 설정은 warmup과 simulation instruction이 모두 10배이므로, 단순 선형 스케일링을 적용한다.

```text
5.07초/job x 10 x (50 / 56) = 약 45.3초/job
10290 jobs x 45.3초/job = 약 466000초
```

추정 결과:

```text
약 129시간
약 5.4일
```

주의:

- 이 값은 이전 5개 trace group의 처리량을 전체 trace set에 그대로 적용한 추정치이다.
- trace별 실행시간 차이가 있으므로 실제로는 4~7일 정도의 범위로 보는 것이 안전하다.
- build 시간은 수십 분 이하로 전체 시간에 비해 작아서 추정에서 큰 비중을 차지하지 않는다.

### 기존 5개 trace group만 장기 실행할 경우

대상은 `260713_2013_l2c_test`에서 사용한 5개 trace group이다.

```text
bravo
sierra.a.3
sierra.a.4
sierra.a.6
tango
```

trace 수:

```text
97 traces
```

job 수:

```text
97 traces x 6 FTQ settings x 5 L2C policies = 2910 jobs
```

동일하게 `w=20000000`, `i=100000000`, `-p56` 기준으로 추정한다.

```text
45.3초/job x 2910 jobs = 약 131800초
```

추정 결과:

```text
약 36.6시간
약 1.5일
```

즉 기존 5개 trace group만 대상으로 모든 FDIP x 모든 L2C 조합을 길게 돌리면 약 하루 반 정도가 예상된다. trace 편차를 고려하면 1.2~2일 정도 범위로 보는 것이 안전하다.

## L2C test trace list 재구성

초기 L2C test 후보는 다음 5개였다.

```text
bravo
sierra.a.3
sierra.a.4
sierra.a.6
tango
```

이 조합은 `sierra.*` 계열이 많아서 instruction-side pressure가 강한 쪽을 잘 본다. 그래서 workload 다양성을 늘리기 위해 다음과 같이 조정한다.

- 제거:
  - `sierra.a.3`
- 추가:
  - `delta`
  - `merced`
  - `tahoe`
  - `yankee`

최종 `l2c_test` trace group:

```text
bravo
delta
merced
sierra.a.4
sierra.a.6
tahoe
tango
yankee
```

trace 수:

| group | traces |
|---|---:|
| bravo | 3 |
| delta | 4 |
| merced | 89 |
| sierra.a.4 | 24 |
| sierra.a.6 | 18 |
| tahoe | 40 |
| tango | 35 |
| yankee | 83 |
| total | 296 |

trace list 파일명도 의미가 고정된 `5groups`보다 일반적인 이름으로 바꾼다.

```text
old: traces/trace_gtrace_l2c_5groups.txt
new: traces/trace_gtrace_l2c_test.txt
```

재생성 command:

```bash
find -L traces/gtrace_v2/bravo \
        traces/gtrace_v2/delta \
        traces/gtrace_v2/merced \
        traces/gtrace_v2/sierra.a.4 \
        traces/gtrace_v2/sierra.a.6 \
        traces/gtrace_v2/tahoe \
        traces/gtrace_v2/tango \
        traces/gtrace_v2/yankee \
  -type f \
  | sed 's#^traces/##' \
  | sort > traces/trace_gtrace_l2c_test.txt
```

선정 이유:

- `delta`
  - data-heavy control case로 적합하다.
  - `ftq2` 기준 L1D MPKI가 약 41로 매우 높고, L1I MPKI는 약 3.7로 낮다.
  - L2C를 instruction에 더 주는 정책이 data-side를 얼마나 망가뜨리는지 확인하기 좋다.
  - trace 수는 4개로 작지만, 성격이 뚜렷해서 control workload로 가치가 있다.

- `merced`
  - trace 수가 89개로 커서 통계적으로 안정적인 대표 workload 역할을 할 수 있다.
  - L1I/L1D/L2C가 모두 중간 이상이라 특정 한쪽에만 치우치지 않은 mixed case다.
  - FTQ를 키웠을 때 IPC 개선도 약 8.8%로 충분히 있어, frontend 개선과 L2C partition trade-off를 함께 보기 좋다.

- `tahoe`
  - memory/off-chip pressure가 있는 mixed case다.
  - `ftq2` 기준 off-chip traffic MPKI가 약 20.3으로 높고, L2C/LLC MPKI도 작지 않다.
  - FTQ 증가에 따른 IPC 개선도 약 11.4%로 관찰되어, instruction-side 개선 여지가 있으면서도 data/memory 간섭을 같이 볼 수 있다.

- `yankee`
  - trace 수가 83개로 많아 통계적으로 안정적이다.
  - FTQ 증가에 따른 IPC 개선이 크고, 기존 5개 group에 없는 큰 대표 group 역할을 할 수 있다.
  - `merced`와 함께 large-sample mixed workload 축을 만든다.

최종 추가 workload 비교:

| 후보 | 역할 | trace 수 | 특징 |
|---|---:|---:|---|
| delta | data-heavy control | 4 | L1D MPKI가 매우 높고 L1I MPKI는 낮음 |
| merced | representative mixed | 89 | trace 수가 많고 I/D/L2C가 균형적 |
| tahoe | memory/off-chip mixed | 40 | off-chip pressure와 FTQ IPC 개선이 모두 있음 |
| yankee | large mixed / stable sample | 83 | trace 수가 많고 FTQ 반응이 큼 |

결론:

최종 `l2c_test`는 `bravo`, `delta`, `merced`, `sierra.a.4`, `sierra.a.6`, `tahoe`, `tango`, `yankee`의 8개 group으로 진행한다. 이렇게 하면 instruction-heavy 후보군에 data-heavy, representative mixed, memory/off-chip mixed, large-sample mixed case가 붙어서 L2C I/D partition의 손익을 더 균형 있게 볼 수 있다.

장기 실행 시간 추정:

```text
296 traces x 6 FTQ settings x 5 L2C policies = 8880 jobs
45.3초/job x 8880 jobs = 약 402000초
```

```text
약 112시간
약 4.7일
```

즉 새 `l2c_test` set 전체를 `w=20000000`, `i=100000000`, `-p56`으로 돌리면 약 4.7일 정도로 예상된다.

### 새 l2c_test set에서 FTQ 0/8/32/64만 장기 실행할 경우

질문:

```text
trace: trace_gtrace_l2c_test.txt
L2C: all 5 policies
FTQ: 0, 8, 32, 64
warmup: 20000000
simulation: 300000000
parallel: -p56 가정
```

주의:

현재 `scripts/run.sh`의 FTQ 후보는 `0`, `2`, `4`, `16`, `32`, `64`이고 `8`은 없다. 실제로 `ftq8`을 돌리려면 FTQ 8을 스크립트/빌드 설정에 추가해야 한다. 아래 추정은 FTQ 값이 4개라는 기준으로 계산한다.

job 수:

```text
296 traces x 4 FTQ settings x 5 L2C policies = 5920 jobs
```

기준 처리량:

```text
w=2000000, i=10000000, -p50
raw 생성 기준: 약 5.07초/job
```

새 instruction 설정은 기준 대비 다음과 같이 커진다.

```text
기준 total instructions: 2M + 10M = 12M
새 total instructions: 20M + 300M = 320M
scale = 320 / 12 = 약 26.67배
```

`-p56`으로 병렬도가 50에서 56으로 늘어난 효과를 반영하면:

```text
5.07초/job x 26.67 x (50 / 56) = 약 120.7초/job
5920 jobs x 120.7초/job = 약 714000초
```

추정 결과:

```text
약 198.5시간
약 8.3일
```

즉 새 `l2c_test` set에서 L2C 전체, FTQ 4개, `w20/i300`, `-p56` 기준으로 돌리면 약 8일 정도가 예상된다. trace별 편차와 장기 실행 변동을 고려하면 7~10일 정도 범위로 보는 것이 안전하다.
