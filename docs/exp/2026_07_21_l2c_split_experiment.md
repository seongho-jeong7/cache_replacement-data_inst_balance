# 2026-07-21 실험 노트: L2C Split g2 w10/i100 Test

이 문서는 `ChampSim_Split`의 split L2 hierarchy가 정상적으로 빌드되고 실행되는지 확인한 `260721_2005_w10_i100_champ_split_2g` 실험을 기록한다.

## 목적

이번 실험의 목적은 성능 결론을 바로 내리는 것보다, 새로 만든 `ChampSim_Split` 구조가 다음 조건에서 안정적으로 동작하는지 확인하는 것이다.

- `shared`: 기존 `L2C` 구조로 실행된다.
- `0i8d`: instruction은 L2를 bypass하고 data만 `L2D`를 사용한다.
- `2i6d`, `4i4d`, `6i2d`: `L2I/L2D`가 모두 생성된다.
- `8i0d`: data는 L2를 bypass하고 instruction만 `L2I`를 사용한다.
- root `scripts/run.sh`의 `-f` 옵션은 입력되지만 `ChampSim_Split`에서는 무시된다.

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
| Run ID | `260721_2005_w10_i100_champ_split_2g` |
| ChampSim dir | `ChampSim_Split` |
| Trace list | `l2c_test_g2.txt` |
| FTQ mask | `0x01` (`ftq0`, `ChampSim_Split`에서는 무시) |
| L2C mask | `0x7b` |
| L2C 정책 | `shared`, `0i8d`, `2i6d`, `4i4d`, `6i2d`, `8i0d` |
| Warmup | `1,000,000` |
| Simulation | `10,000,000` |
| 병렬도 | `58` |
| 총 job 수 | 22 traces × 1 FTQ × 6 policies = 132 |

## 실행 명령

이전 `w10/i20` 테스트 output은 삭제하고, `i100` 조건으로 다시 실행했다. run id는 `날짜_시간_w#_i#_l2c_split` 형태로 맞췄다.

```bash
./scripts/run.sh -C ChampSim_Split -t \
  -T l2c_test_g2.txt \
  -L2C 0x7b \
  -f 0x01 \
  -w 1000000 \
  -i 10000000 \
  -p 58 \
  -r 260721_2005_w10_i100_champ_split_2g
```

Summary는 metrics와 L2C delta grid를 함께 생성했다.

```bash
./scripts/run.sh -C ChampSim_Split \
  -r 260721_2005_w10_i100_champ_split_2g \
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

- `outputs/260721_2005_w10_i100_champ_split_2g/raw/fdip_0/<policy>/...`
- `outputs/260721_2005_w10_i100_champ_split_2g/summary/l2c_raw_values.csv`
- `outputs/260721_2005_w10_i100_champ_split_2g/summary/l2c_delta_raw.csv`
- `outputs/260721_2005_w10_i100_champ_split_2g/summary/l2c_delta_pct.csv`
- `outputs/260721_2005_w10_i100_champ_split_2g/summary/l2c_delta_grid.png`
- `outputs/260721_2005_w10_i100_champ_split_2g/summary/l2c_delta_combined.png`
- `outputs/260721_2005_w10_i100_champ_split_2g/summary/l2c_delta_combined_v2.png`

## 메모

현재 summary parser의 `L2C MPKI`는 이름이 `cpu0_L2C`인 cache section을 기준으로 계산된다. 따라서 split mode에서는 `L2C MPKI`가 `0`으로 보인다. 이는 L2 miss가 없다는 뜻이 아니라, `L2C` cache object가 `L2I/L2D`로 분리되었기 때문이다. 이후 분석에서는 `L2I/L2D`를 직접 읽도록 parser를 확장해야 한다.

---

## 후속 실행: `260721_2121_w10_i100_l2c_split` (전체 l2c_test set)

스모크 테스트(`260721_2005`, 22 traces)가 132/132 성공한 것을 확인한 뒤, 같은 조건으로 trace 규모만 전체 `l2c_test` set(296 traces, 8 그룹)으로 확장해서 실행했다.

| 항목 | 값 |
|---|---|
| Run ID | `260721_2121_w10_i100_l2c_split` |
| Trace list | `trace_gtrace_l2c_test.txt` (296) |
| L2C mask | `0x7b` (`shared`/`0i8d`/`2i6d`/`4i4d`/`6i2d`/`8i0d`, `1i7d` 제외는 이전과 동일) |
| FTQ | `0`만(`-f 0x01`, `ChampSim_Split`에서는 무시됨) |
| Warmup / Simulation | `1,000,000` / `10,000,000` |
| 병렬도 | `58` |
| 총 job 수 | 296 × 1 × 6 = **1,776** |
| 시작 | 21:22, ETA ≈ 23:37 |

```bash
./scripts/run.sh -C ChampSim_Split -t -T trace_gtrace_l2c_test.txt -L2C 0x7b -f 0x01 -w 1000000 -i 10000000 -p 58 -r 260721_2121_w10_i100_l2c_split
```

완료되면 summary 생성 후, split L2I/L2D 구조에서의 dIPC/MPKI 경향을 확인한다. `L2C MPKI` 관련 parser 제약(위 메모 참고)은 이 run에도 동일하게 적용된다.

### 결과 폴더 삭제

1,776 job 전부 완료(296/296, 실패 0)까지는 됐지만, `shared` 정책 로그에 `L2C LOAD_I`/`LOAD_D`(origin-split) 줄이 정상적으로 출력되지 않아 I/D 분해 분석에 이 결과를 쓸 수 없었다. 그래서 `outputs/260721_2121_w10_i100_l2c_split` 결과 폴더는 삭제했다. 이 문제를 고친 뒤의 재실행은 `docs/exp/2026_07_22_l2c_split_experiment.md` 참고.
