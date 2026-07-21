# 2026-07-21 실험 노트: L2C Split g2 w10/i100 Test

이 문서는 `ChampSim_L2C`의 split L2 hierarchy가 정상적으로 빌드되고 실행되는지 확인한 `260721_2005_w10_i100_l2c_split` 실험을 기록한다.

## 목적

이번 실험의 목적은 성능 결론을 바로 내리는 것보다, 새로 만든 `ChampSim_L2C` 구조가 다음 조건에서 안정적으로 동작하는지 확인하는 것이다.

- `shared`: 기존 `L2C` 구조로 실행된다.
- `0i8d`: instruction은 L2를 bypass하고 data만 `L2D`를 사용한다.
- `2i6d`, `4i4d`, `6i2d`: `L2I/L2D`가 모두 생성된다.
- `8i0d`: data는 L2를 bypass하고 instruction만 `L2I`를 사용한다.
- root `scripts/run.sh`의 `-f` 옵션은 입력되지만 `ChampSim_L2C`에서는 무시된다.

## Trace 구성

작은 규모로 빠르게 확인하기 위해 `traces/l2c_test_g2.txt`를 사용했다. `g2`는 group 2개를 의미한다.

| Trace group | 개수 |
|---|---:|
| `delta` | 4 |
| `sierra.a.6` | 18 |
| 합계 | 22 |

## 실행 조건

| 항목 | 값 |
|---|---|
| Run ID | `260721_2005_w10_i100_l2c_split` |
| ChampSim dir | `ChampSim_L2C` |
| Trace list | `l2c_test_g2.txt` |
| FTQ mask | `0x01` (`ftq0`, `ChampSim_L2C`에서는 무시) |
| L2C mask | `0x7b` |
| L2C 정책 | `shared`, `0i8d`, `2i6d`, `4i4d`, `6i2d`, `8i0d` |
| Warmup | `1,000,000` |
| Simulation | `10,000,000` |
| 병렬도 | `58` |
| 총 job 수 | 22 traces × 1 FTQ × 6 policies = 132 |

## 실행 명령

이전 `w10/i20` 테스트 output은 삭제하고, `i100` 조건으로 다시 실행했다. run id는 `날짜_시간_w#_i#_l2c_split` 형태로 맞췄다.

```bash
./scripts/run.sh -C ChampSim_L2C -t \
  -T l2c_test_g2.txt \
  -L2C 0x7b \
  -f 0x01 \
  -w 1000000 \
  -i 10000000 \
  -p 58 \
  -r 260721_2005_w10_i100_l2c_split
```

Summary는 metrics와 L2C delta grid를 함께 생성했다.

```bash
./scripts/run.sh -C ChampSim_L2C \
  -r 260721_2005_w10_i100_l2c_split \
  -f 0x01 \
  -L2C 0x7b \
  -s 0xc1
```

## 실행 결과

| Policy | Raw logs | Completed |
|---|---:|---:|
| `shared` | 22 | 22 |
| `0i8d` | 22 | 22 |
| `2i6d` | 22 | 22 |
| `4i4d` | 22 | 22 |
| `6i2d` | 22 | 22 |
| `8i0d` | 22 | 22 |
| 합계 | 132 | 132 |

모든 raw log에서 `ChampSim completed all CPUs`가 확인됐고 실패는 없었다.

## 구조 검증

각 policy별 raw log section을 확인한 결과, config parser가 의도한 hierarchy를 만들고 있었다.

| Policy | 확인된 cache section |
|---|---|
| `shared` | `cpu0_L2C` |
| `0i8d` | `cpu0_L2D` |
| `2i6d` | `cpu0_L2I`, `cpu0_L2D` |
| `4i4d` | `cpu0_L2I`, `cpu0_L2D` |
| `6i2d` | `cpu0_L2I`, `cpu0_L2D` |
| `8i0d` | `cpu0_L2I` |

즉, `0i8d`와 `8i0d`의 zero-way side는 L2 cache object를 만들지 않고 LLC로 bypass되는 구조로 실행됐다.

## 산출물

주요 산출물은 다음 위치에 생성됐다.

- `outputs/260721_2005_w10_i100_l2c_split/raw/fdip_0/<policy>/...`
- `outputs/260721_2005_w10_i100_l2c_split/summary/l2c_raw_values.csv`
- `outputs/260721_2005_w10_i100_l2c_split/summary/l2c_delta_raw.csv`
- `outputs/260721_2005_w10_i100_l2c_split/summary/l2c_delta_pct.csv`
- `outputs/260721_2005_w10_i100_l2c_split/summary/l2c_delta_grid.png`
- `outputs/260721_2005_w10_i100_l2c_split/summary/l2c_delta_combined.png`
- `outputs/260721_2005_w10_i100_l2c_split/summary/l2c_delta_combined_v2.png`

## 메모

현재 summary parser의 `L2C MPKI`는 이름이 `cpu0_L2C`인 cache section을 기준으로 계산된다. 따라서 split mode에서는 `L2C MPKI`가 `0`으로 보인다. 이는 L2 miss가 없다는 뜻이 아니라, `L2C` cache object가 `L2I/L2D`로 분리되었기 때문이다. 이후 분석에서는 `L2I/L2D`를 직접 읽도록 parser를 확장해야 한다.
