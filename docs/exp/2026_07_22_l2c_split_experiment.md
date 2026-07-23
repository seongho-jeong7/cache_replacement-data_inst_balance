# 2026-07-22 실험 노트: L2C Split shared I/D 로그 재실행

## 목적

`ChampSim_Split`에서 shared L2C 모드로 실행할 때도 FDIP에서 사용하던 것과 같은 의미의 instruction/data 분리 로그가 출력되는지 확인한다.

이번 재실행의 핵심은 다음 두 가지다.

- `shared` 정책에서는 단일 `cpu0_L2C` cache object 안에서 `TOTAL_I`, `LOAD_I`, `TOTAL_D`, `LOAD_D`처럼 I/D origin별 통계가 출력되어야 한다.
- split 정책에서는 별도 cache object인 `cpu0_L2I`, `cpu0_L2D`의 `TOTAL`, `LOAD` 통계를 사용한다.

따라서 이후 parser/summary에서는 shared와 split을 다음처럼 의미상 대응시킬 수 있어야 한다.

| 구조 | Instruction 통계 | Data 통계 |
|---|---|---|
| shared | `cpu0->cpu0_L2C TOTAL_I`, `LOAD_I` | `cpu0->cpu0_L2C TOTAL_D`, `LOAD_D` |
| split | `cpu0->cpu0_L2I TOTAL`, `LOAD` | `cpu0->cpu0_L2D TOTAL`, `LOAD` |

## 재시험 이유

`260721_2121_w10_i100_l2c_split` 결과를 분석하는 과정에서, `shared` 정책의 raw log에 `L2C LOAD_I`/`LOAD_D`(origin-split) 줄이 아예 출력되지 않는다는 것을 확인했다.

```text
cpu0->cpu0_L2C TOTAL ...
cpu0->cpu0_L2C LOAD ...
cpu0->cpu0_L2C RFO ...
```

`shared`는 단일 `cpu0_L2C` object라 I/D를 나눠 보려면 이 origin-split 줄이 있어야 하는데, 없다 보니 `shared` row의 `l2i_mpki`/`l2d_mpki`가 계속 blank로 나왔다. 그 결과 `l2c_delta_raw.csv`/`l2c_delta_pct.csv`가 shared를 기준으로 변화량을 계산할 때 비교할 baseline이 없어서, `d_l2i_mpki`/`d_l2d_mpki`가 대부분 blank로 남았다(`l2c_delta_raw.csv`/`l2c_delta_pct.csv` 둘 다 40행 중 8행만 값이 있었다). split 정책(`0i8d`/`2i6d`/`4i4d`/`6i2d`/`8i0d`) 쪽은 물리적으로 분리된 `L2I`/`L2D` object 통계가 있어서 문제없었다.

이번 재실행은 `shared`가 FDIP처럼 `TOTAL_I`/`LOAD_I`/`TOTAL_D`/`LOAD_D`를 제대로 찍는지 확인하기 위한 것이다.

## 기준 실험

비교 기준은 기존 전체 trace 실험인 `260721_2121_w10_i100_l2c_split`이다.

기존 실행 조건은 다음과 같았다.

```bash
./scripts/run.sh -C ChampSim_L2C -t \
  -T trace_gtrace_l2c_test.txt \
  -L2C 0x7b \
  -f 0x01 \
  -w 1000000 \
  -i 10000000 \
  -p 58 \
  -r 260721_2121_w10_i100_l2c_split
```

## 이번 실행 조건

폴더명은 `ChampSim_L2C`에서 `ChampSim_Split`으로 변경됐고, 이번에는 요청대로 `-f` 옵션을 제외했다. `run.sh`는 `-f`가 주어지지 않으면 `--ftq_size`를 ChampSim binary에 넘기지 않고 binary의 기본 동작을 사용한다.

| 항목 | 값 |
|---|---|
| Run ID | `260722_1449_w10_i100_champ_split` |
| ChampSim dir | `ChampSim_Split` |
| Trace list | `trace_gtrace_l2c_test.txt` |
| L2C mask | `0x7b` |
| L2C policies | `shared`, `0i8d`, `2i6d`, `4i4d`, `6i2d`, `8i0d` |
| FTQ option | 미지정 |
| Warmup | `1,000,000` |
| Simulation | `10,000,000` |
| 병렬도 | `58` |

실행 명령은 다음과 같다.

```bash
./scripts/run.sh -C ChampSim_Split -b \
  -L2C 0x7b \
  -r 260722_1449_w10_i100_champ_split

./scripts/run.sh -C ChampSim_Split -t \
  -T trace_gtrace_l2c_test.txt \
  -L2C 0x7b \
  -w 1000000 \
  -i 10000000 \
  -p 58 \
  -r 260722_1449_w10_i100_champ_split
```

## 진행 상황

- `ChampSim_Split` build는 정상 완료됐다.
- trace 실행을 시작했고, `run.log`에서 `FTQ size: 0 (not passed, ChampSim default)`와 `L2C policy: shared`가 기록되는 것을 확인했다.
- trace 실행과 summary 생성을 완료했다.

## 실행 결과

전체 실행은 정상 완료됐다.

| 항목 | 결과 |
|---|---:|
| Trace 수 | 296 |
| L2C policy 수 | 6 |
| 총 job 수 | 1,776 |
| 생성 raw log | 1,776 |
| 실패 trace | 0 |

Summary 생성 명령은 다음과 같다.

```bash
./scripts/run.sh -C ChampSim_Split \
  -r 260722_1449_w10_i100_champ_split \
  -L2C 0x7b \
  -s 0xc1
```

각 policy별 summary에서 모두 `296 total, 296 ok, 0 failed`가 확인됐다.

| Policy | Total | OK | Fail |
|---|---:|---:|---:|
| `shared` | 296 | 296 | 0 |
| `0i8d` | 296 | 296 | 0 |
| `2i6d` | 296 | 296 | 0 |
| `4i4d` | 296 | 296 | 0 |
| `6i2d` | 296 | 296 | 0 |
| `8i0d` | 296 | 296 | 0 |

## Shared L2C I/D 로그 확인

이번 실행의 핵심 확인 대상은 shared mode에서 `cpu0_L2C` 하나만 존재하더라도, 그 안에 instruction/data origin별 통계가 찍히는지였다.

대표 raw log에서 다음 section이 확인됐다.

```text
cpu0->cpu0_L2C TOTAL_I      ACCESS:     496869 HIT:     274563 MISS:     222306 MISS_MERGE:          0
cpu0->cpu0_L2C LOAD_I       ACCESS:     496869 HIT:     274563 MISS:     222306 MISS_MERGE:          0
cpu0->cpu0_L2C TOTAL_D      ACCESS:     535021 HIT:     317296 MISS:     217725 MISS_MERGE:       1208
cpu0->cpu0_L2C LOAD_D       ACCESS:     154950 HIT:      82383 MISS:      72567 MISS_MERGE:        237
```

따라서 shared mode에서는 다음 해석이 가능하다.

- `L2I` 성격의 값은 `cpu0->cpu0_L2C *_I`에서 얻는다.
- `L2D` 성격의 값은 `cpu0->cpu0_L2C *_D`에서 얻는다.
- split mode의 `cpu0->cpu0_L2I TOTAL/LOAD`, `cpu0->cpu0_L2D TOTAL/LOAD`와 의미상 대응시켜 비교할 수 있다.

## Parser 확인

`shared/metrics.csv`에도 `l2i_mpki`, `l2d_mpki` 값이 채워지는 것을 확인했다. 예를 들어 `bravo.a_0000` row는 다음처럼 shared L2C 안의 I/D origin 통계를 기반으로 split metric을 생성한다.

| Trace | L2C MPKI | L2I MPKI | L2D MPKI |
|---|---:|---:|---:|
| `bravo.a_0000` | 23.54 | 12.48 | 11.06 |
| `bravo.a_0001` | 5.51 | 2.51 | 3.00 |
| `bravo.a_0002` | 21.66 | 10.55 | 11.11 |

이로써 이전 `260721_2121_w10_i100_l2c_split`에서 shared baseline의 I/D 값이 비어 보이던 문제는, 새 로그 형식과 parser 조합에서는 해결되는 것으로 확인됐다.

## 산출물

주요 산출물은 다음 위치에 생성됐다.

- `outputs/260722_1449_w10_i100_champ_split/raw/fdip_0/<policy>/...`
- `outputs/260722_1449_w10_i100_champ_split/summary/fdip_0/<policy>/metrics.csv`
- `outputs/260722_1449_w10_i100_champ_split/summary/l2c_raw_values.csv`
- `outputs/260722_1449_w10_i100_champ_split/summary/l2c_delta_raw.csv`
- `outputs/260722_1449_w10_i100_champ_split/summary/l2c_delta_pct.csv`
- `outputs/260722_1449_w10_i100_champ_split/summary/l2c_delta_grid.png`
- `outputs/260722_1449_w10_i100_champ_split/summary/l2c_delta_combined.png`
- `outputs/260722_1449_w10_i100_champ_split/summary/l2c_delta_combined_v2.png`

## 메모

이번 run은 `-f`를 지정하지 않았다. `run.sh` 로그에는 `FTQ size: 0 (not passed, ChampSim default)`로 기록되며, `--ftq_size` 인자는 binary에 전달되지 않는다. `ChampSim_Split`은 FDIP/FTQ 기능 검증 대상이 아니라 L2 hierarchy split 기능 검증 대상이므로, 이 조건이 더 자연스럽다.
