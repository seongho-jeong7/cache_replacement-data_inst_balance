# 2026-07-21 실험 노트: `260721_1451_w10_i20_repl_test`

이 문서는 `ChampSim_FDIP` 최신 커밋(`73980b3` "Constrain L2C replacement to partition ways") 기준으로 시작한 `260721_1451_w10_i20_repl_test`의 실행 조건과 진행 과정을 기록한다. 코드 변경 자체의 배경/구현은 `docs/exp/2026_07_21_code.md`, 그 변경이 필요했던 이유에 대한 토론은 `docs/exp/2026_07_21_analysis.md`의 토론 절 참고.

## 배경

`260716_1733_w20_i300_latency_test` 분석(`docs/exp/2026_07_21_analysis.md`) 과정에서, 현재 L2C partition 모델이 replacement/prefetcher를 어떻게 다루는지 짚어보는 토론이 있었다. 그 결과 두 가지 문제가 확인됐다:

- Partition이 꽉 찼을 때 replacement policy가 전체 set에서 victim을 먼저 고른 뒤 partition 밖이면 fallback하던 기존 방식이 LRU/RRIP state를 왜곡할 수 있다.
- L2C prefetcher(`ip_stride`)가 요청의 instruction/data origin을 전달받지 못해서, instruction-origin 접근으로 촉발된 prefetch가 origin 기본값(false, 즉 data) 때문에 data partition을 오염시킬 수 있다.

이 두 문제를 고친 커밋이 `73980b3`이다.

```
73980b3 "Constrain L2C replacement to partition ways"
- Pass victim way ranges from CACHE to replacement policies.
- Select L2C victims only within the request origin partition.
- Remove partition-outside victim fallback behavior.
- Update LRU, SRRIP, DRRIP, SHIP, and random replacement to honor candidate ranges.
- Disable the L2C ip_stride prefetcher to avoid I/D origin pollution.
```

`champsim_config.json`의 L2C `prefetcher`도 `ip_stride` → `no`로 바뀌었다. 이전까지의 모든 run(`260713_2013`부터 `260716_1733`까지)은 이 변경 이전 코드로 돌았으므로, 이 run은 replacement/prefetcher가 정리된 이후 첫 데이터다. 커밋 메시지에 "빌드는 하지 않았다(진행 중인 실험 바이너리를 건드리지 않기 위해)"라고 명시돼 있었는데, 이 시점엔 이전 장기 실행이 전부 끝난 뒤라 바로 빌드해도 안전했다.

## 실행 조건

| 항목 | 값 |
|---|---|
| Run ID | `260721_1451_w10_i20_repl_test` |
| ChampSim_FDIP | 최신 HEAD (`73980b3`, replacement partition 제약 + prefetcher 비활성화 포함) |
| Trace list | `trace_gtrace_l2c_test.txt` (8 그룹, 296 traces) — 이전 latency_test run들과 동일 |
| FTQ | `0`, `4`, `32` (`-f 0x15`) — 경향성만 빠르게 보기 위해 3개로 제한 |
| L2C 정책 | `shared`/`0i8d`/`2i6d`/`4i4d`/`6i2d` 5개(`-L2C 0x3b`) — `1i7d`/`8i0d`는 이번엔 제외 |
| warmup / simulation | `1,000,000` / `2,000,000` (=`w10`/`i20`, 스모크 테스트 스케일) |
| 병렬도 | `-p 58` |
| job 수 | 296 traces × 3 FTQ × 5 policy = **4,440** (규모가 작아 stage 분할 없이 단일 실행) |

## 빌드 및 실행

```bash
./scripts/run.sh -b -L2C 0x7f
```

(`-b`는 mask와 무관하게 7개 policy 바이너리를 전부 만든다.)

```bash
nohup ./scripts/run.sh -t -T trace_gtrace_l2c_test.txt -L2C 0x3b -f 0x15 -w 1000000 -i 2000000 -p 58 -r 260721_1451_w10_i20_repl_test > /tmp/260721_1451_w10_i20_repl_test.log 2>&1 &
```

2026-07-21 14:52:30 시작, PID `2547153`.

시간 추정: 이전 `260716_1305`(같은 `w10/i20` 스케일, `-p58`)에서 실측한 약 1.2초/job을 그대로 적용하면 4,440 × 1.2초 ≈ 5,330초 ≈ **약 1.5시간**, 완료 예상 약 16:20.

## 다음 계획

- 완료되면 summary를 생성하고(`-s 0xC0 -f 0x15 -L2C 0x3b`), `260716_1305`/`260716_1733`(replacement 제약·prefetcher 변경 이전 코드)와 dIPC 경향을 비교한다.
- 특히 `2i6d`/`4i4d`/`6i2d`처럼 실제로 두 way group을 나누는 정책에서, victim fallback 제거와 prefetcher 비활성화가 dL2D/dL2I MPKI와 dIPC를 얼마나 바꾸는지가 관심사다.
- 결과는 `docs/exp/2026_07_21_analysis.md`(또는 새 anal 문서)에 정리한다.

---

## 2026-07-21: 실행 완료

- 종료 시각: 16:16:39 (예상 16:20과 거의 일치, 총 소요 약 1시간 24분).
- 결과: 4,440 job 중 **4,438개 성공**, 실패 2건 — 둘 다 `yankee_0014`, exit 134(SIGABRT). 15개 (FTQ×policy) 조합 전부에서 `yankee_0014`가 돌았는데, 로그가 `-p 58` 병렬 실행으로 인터리빙되어 있어 실패한 정확한 2개 조합은 로그만으로는 특정 불가(추후 필요하면 `yankee_0014` 하나만 15개 조합 직렬 재실행해서 특정 가능).
- Summary 생성 완료:
  ```bash
  ./scripts/run.sh -s 0xC0 -f 0x15 -L2C 0x3b -r 260721_1451_w10_i20_repl_test
  ```
  `-s 0x40`(metrics.csv, 15개 FTQ×policy 조합 전부)과 `-s 0x80`(L2C delta grid)을 함께 생성. 산출물: `outputs/260721_1451_w10_i20_repl_test/summary/`에 `metrics.csv`(조합별), `l2c_raw_values.csv`, `l2c_delta_pct.csv`, `l2c_delta_raw.csv`, `l2c_delta_grid.png`, `l2c_delta_combined.png`, `l2c_delta_combined_v2.png`.
- 다음: 이 데이터를 `260716_1305_w10_i20_latency_test`(같은 `w10/i20` 스케일, replacement 제약/prefetcher 변경 이전 코드)와 비교해서 dIPC/MPKI 경향 변화를 분석 문서로 정리한다.
