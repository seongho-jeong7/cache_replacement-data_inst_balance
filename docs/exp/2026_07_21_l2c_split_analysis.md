# 2026-07-21 Analysis: L2C Split g2 w10/i100 결과

이 문서는 `260721_2005_w10_i100_champ_split_2g` 결과를 바탕으로, `ChampSim_Split`의 실제 `L2I/L2D` 분리 구조가 어떤 경향을 보였는지 정리한다.

## 요약

- `ChampSim_Split`의 split hierarchy 자체는 정상 동작했다.
- `shared`, `0i8d`, `2i6d`, `4i4d`, `6i2d`, `8i0d` 총 132개 job이 모두 완료됐다.
- `delta`는 instruction way를 늘리는 방향(`2i6d -> 4i4d -> 6i2d`)에서 IPC가 조금씩 좋아졌지만, data L2를 완전히 없앤 `8i0d`에서는 IPC가 크게 하락했다.
- `sierra.a.6`은 극단적인 `0i8d`, `8i0d`에서 IPC가 좋아지고, 중간 partition에서는 거의 중립 또는 소폭 하락했다.
- 현재 combined summary의 `L2C MPKI=0`은 split mode에서 `L2C` object가 없기 때문에 생기는 parser 표현 문제다. split mode 분석에는 `L2I/L2D` section을 직접 집계해야 한다.

## IPC와 MPKI 변화

아래 표의 변화량은 모두 `shared` 대비 값이다. `dIPC`는 percent 변화량이고, MPKI 변화량은 raw delta다.

| Trace | Policy | IPC | dIPC(%) | dL1I MPKI | dL1D MPKI | dL2C MPKI |
|---|---|---:|---:|---:|---:|---:|
| delta | shared | 0.5891 | 0.000 | 0.000 | 0.000 | 0.000 |
| delta | 0i8d | 0.5911 | +0.344 | +0.069 | +0.112 | -10.927 |
| delta | 2i6d | 0.5902 | +0.199 | -0.020 | +0.174 | -10.927 |
| delta | 4i4d | 0.5933 | +0.726 | -0.032 | +0.163 | -10.927 |
| delta | 6i2d | 0.5959 | +1.167 | -0.032 | +0.237 | -10.927 |
| delta | 8i0d | 0.4561 | -22.566 | -0.031 | +4.969 | -10.927 |
| sierra.a.6 | shared | 0.4576 | 0.000 | 0.000 | 0.000 | 0.000 |
| sierra.a.6 | 0i8d | 0.4761 | +4.035 | +1.419 | -0.110 | -30.630 |
| sierra.a.6 | 2i6d | 0.4553 | -0.510 | +1.078 | -0.174 | -30.630 |
| sierra.a.6 | 4i4d | 0.4555 | -0.458 | +0.324 | -0.042 | -30.630 |
| sierra.a.6 | 6i2d | 0.4550 | -0.563 | -0.177 | +0.208 | -30.630 |
| sierra.a.6 | 8i0d | 0.4764 | +4.111 | -0.233 | +0.393 | -30.630 |

`dL2C MPKI`가 split policy에서 모두 `-100%` 또는 raw delta 음수로 표시되는 것은 주의가 필요하다. split mode에서는 `cpu0_L2C`가 없어지고 `cpu0_L2I`, `cpu0_L2D`가 생기기 때문에, 기존 parser가 `L2C` section을 찾지 못한 결과다. 이 값은 성능 개선 지표로 해석하면 안 된다.

## Delta 해석

`delta`는 `6i2d`까지 instruction side 비중을 높일수록 IPC가 조금씩 좋아졌다.

- `2i6d`: +0.20%
- `4i4d`: +0.73%
- `6i2d`: +1.17%

동시에 L1D MPKI는 조금 증가했지만 증가폭이 작다. 이 범위에서는 data side capacity 감소보다 instruction path 변화의 이득이 더 커 보인다.

반대로 `8i0d`는 IPC가 -22.57%로 크게 하락했다. L1I MPKI는 거의 변하지 않지만 L1D MPKI가 +4.97 증가했다. 즉, data L2를 완전히 제거하면 data miss path가 LLC로 바로 내려가고, 이 비용이 IPC를 크게 깎는다. `delta`는 data side L2가 반드시 필요한 workload로 보는 것이 자연스럽다.

## Sierra.a.6 해석

`sierra.a.6`은 `0i8d`와 `8i0d`에서 IPC가 각각 약 +4% 좋아졌다.

- `0i8d`: +4.04%
- `8i0d`: +4.11%
- `2i6d`, `4i4d`, `6i2d`: -0.5% 안팎

이 결과는 단순히 instruction/data way를 균형 있게 나누면 좋아진다는 가설과는 맞지 않는다. 오히려 극단적인 bypass 구조가 traffic 또는 latency path를 바꾸면서 이득을 준 것으로 보인다. 다만 이번 실험은 `w10/i100`의 짧은 확인 run이므로, 긴 run에서 같은 경향이 유지되는지 확인해야 한다.

특히 `0i8d`는 L1I MPKI가 +1.42 증가했는데도 IPC가 좋아졌다. 이 경우 instruction MPKI 자체보다 data path, queue pressure, LLC interaction 같은 다른 요인이 더 크게 작용했을 가능성이 있다.

## 구조 검증 관점의 결론

이번 결과에서 가장 중요한 것은 성능값보다 구조 검증이다.

| Policy | 구조 검증 결과 |
|---|---|
| `shared` | 기존처럼 `cpu0_L2C`만 생성 |
| `0i8d` | `cpu0_L2D`만 생성, instruction은 L2 bypass |
| `2i6d`, `4i4d`, `6i2d` | `cpu0_L2I`, `cpu0_L2D`가 모두 생성 |
| `8i0d` | `cpu0_L2I`만 생성, data는 L2 bypass |

따라서 `ChampSim_Split`의 config-driven split hierarchy는 의도대로 적용됐다고 볼 수 있다.

## Parser 한계

현재 `l2c_delta_*` CSV는 기존 `L2C` 중심 분석에서 출발했기 때문에 split mode의 핵심 지표를 충분히 보여주지 못한다.

- split mode에서는 `L2C MPKI`가 0처럼 보인다.
- `L2I MPKI`, `L2D MPKI` column은 있지만 이번 combined 결과에서는 비어 있다.
- raw log에는 `cpu0_L2I`, `cpu0_L2D` section이 존재하므로 parser가 이를 읽도록 보강해야 한다.

다음 분석부터는 다음 형태가 필요하다.

| Trace | Policy | IPC | L1I MPKI | L2I MPKI | L1D MPKI | L2D MPKI | LLC I MPKI | LLC D MPKI |
|---|---:|---:|---:|---:|---:|---:|---:|---:|

이렇게 해야 `0i8d`와 `8i0d`가 실제로 어떤 path 비용을 늘리고 줄였는지 더 분명하게 볼 수 있다.

## 다음 단계

- split mode용 parser를 보강해서 `L2I/L2D` section을 직접 집계한다.
- `delta`, `sierra.a.6` 외에 기존 후보 workload를 추가해 같은 경향이 반복되는지 확인한다.
- 짧은 `w10/i100` 결과가 안정적인지 더 긴 instruction 조건에서 재확인한다.
- 단일 L2C way partition 모델과 실제 split L2I/L2D 모델의 차이를 분리해서 비교한다.
