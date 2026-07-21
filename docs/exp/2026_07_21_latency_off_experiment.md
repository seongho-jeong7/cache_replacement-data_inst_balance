# 2026-07-21 실험 노트: `260721_1707_w10_i20_latency_revert_test` — FTQ0, Latency 제거 Test

`c19adac` Way 기반 L2C search latency 모델을 되돌린 뒤(코드 변경은 `docs/exp/2026_07_21_latency_off_code.md` 참고), FDIP를 끄고(FTQ 0) L2C partition 정책만 비교하는 테스트.

## 배경

`73980b3`(replacement를 partition 안으로 제약)의 효과를 latency 모델과 분리해서 보기 위해, `effective_l2c_search_latency()`가 다시 고정 `HIT_LATENCY`를 반환하도록 되돌렸다. FDIP(FTQ)까지 켜져 있으면 frontend stall 은폐 효과가 섞여 replacement/latency 변화의 순수 효과를 보기 어려우므로, 이번 테스트는 FTQ 0(FDIP 비활성)로 고정한다.

## 실행 조건

| 항목 | 값 |
|---|---|
| Run ID | `260721_1707_w10_i20_latency_revert_test` |
| ChampSim_FDIP | HEAD `73980b3` + latency 모델 되돌리기(uncommitted, `docs/exp/2026_07_21_latency_off_code.md` 참고) |
| Trace list | `trace_gtrace_l2c_test.txt` (8 그룹, 296 traces) |
| FTQ | `0`만(`-f 0x01`) — FDIP 비활성 상태에서 replacement/latency 변경 효과만 관찰 |
| L2C 정책 | `shared`/`0i8d`/`2i6d`/`6i2d` 4개(`-L2C 0x2b`) |
| warmup / simulation | `1,000,000` / `2,000,000` (`w10`/`i20`, 스모크 스케일) |
| 병렬도 | `-p 58` |
| job 수 | 296 traces × 1 FTQ × 4 policy = **1,184** |

## 빌드 및 실행

```bash
./scripts/run.sh -b -L2C 0x7f
```

```bash
nohup ./scripts/run.sh -t -T trace_gtrace_l2c_test.txt -L2C 0x2b -f 0x01 -w 1000000 -i 2000000 -p 58 -r 260721_1707_w10_i20_latency_revert_test > /tmp/260721_1707_w10_i20_latency_revert_test.log 2>&1 &
```

2026-07-21 17:09 시작. 빌드는 17:06~17:07에 전체 7개 정책 바이너리를 미리 생성해뒀다(latency 모델을 되돌린 소스로).

## 다음 계획

- 완료되면 summary 생성(`-s 0xC0 -f 0x01 -L2C 0x2b`) 후, latency 모델이 켜져 있던 `260721_1451_w10_i20_repl_test`(`docs/exp/2026_07_21_experiment.md`, 같은 `w10/i20` 스케일이지만 FTQ 0/4/32에 `4i4d` 포함/`shared` 제외)와 dIPC 경향을 비교한다.
- 특히 latency 모델이 꺼진 상태에서도 `2i6d`/`6i2d`가 `shared` 대비 이득을 보이는지가 핵심 관심사 — 그렇다면 이득의 근원이 latency 모델이 아니라 replacement 제약(`73980b3`) 자체에 있다는 뜻이다.
- 결과는 새 anal 문서에 정리한다.

---

## 2026-07-21: 실행 완료

- 종료 시각: 17:26경(로그 마지막 `Saved output to` 기준), 총 소요 약 17분.
- 결과: 1,184 job **전부 성공**(실패 0건).
- Summary 생성 완료:
  ```bash
  ./scripts/run.sh -s 0xC0 -f 0x01 -L2C 0x2b -r 260721_1707_w10_i20_latency_revert_test
  ```
  `-s 0x40`(metrics.csv, `shared`/`0i8d`/`2i6d`/`6i2d` 4개 조합 전부)과 `-s 0x80`(L2C delta grid)을 함께 생성. 산출물: `outputs/260721_1707_w10_i20_latency_revert_test/summary/`에 `metrics.csv`(조합별), `l2c_raw_values.csv`, `l2c_delta_pct.csv`, `l2c_delta_raw.csv`, `l2c_delta_grid.png`, `l2c_delta_combined.png`, `l2c_delta_combined_v2.png`.
- 다음: `260721_1451_w10_i20_repl_test`(latency 모델 켜진 상태)와 dIPC/MPKI 경향을 비교해서 latency 모델을 껐을 때도 `2i6d`/`6i2d`가 `shared` 대비 이득을 유지하는지 분석 문서로 정리한다.
