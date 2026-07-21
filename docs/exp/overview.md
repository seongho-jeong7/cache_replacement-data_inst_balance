# Experiment Overview

`outputs/` 아래 지금까지 진행한 실험 run을 시간순으로 정리한 표. 각 실험 환경(trace, FTQ, L2C 정책, warmup/simulation 길이)과, **바로 이전 실험 대비 어떤 코드 변경이 있었는지**를 같이 적는다. 커밋 해시는 `ChampSim_FDIP` 기준이다. 각 run의 상세 과정은 개별 `docs/exp/*.md`에 있고, 여기서는 한눈에 비교하기 위한 요약만 다룬다.

## 현재 기본 실험 설정

현재 `ChampSim_FDIP/champsim_config.json` 기준의 주요 policy/config 요약이다. L2C partition을 켜도 L2I/L2D가 별도 cache로 생성되는 것은 아니며, 하나의 `cpu0_L2C`에서 request origin에 따라 way 범위만 나눠 쓴다.

| 항목 | 설정 |
|---|---|
| Core / frontend | 1 core, branch predictor `bimodal`, BTB `basic_btb` |
| L1I | 64 sets, 8 ways, latency 4, prefetcher `no`, replacement `lru`(default) |
| L1D | 64 sets, 12 ways, latency 5, prefetcher `ip_stride`, replacement `lru`(default) |
| L2C | 1024 sets, 8 ways, prefetcher `no`, replacement `lru`(default) |
| L2C partition | `shared`, `0i8d`, `1i7d`, `2i6d`, `4i4d`, `6i2d`, `8i0d` 실험 |
| LLC | 2048 sets, 16 ways, prefetcher `no`, replacement `lru` |
| DRAM | 1 channel, data rate 3200, tCAS/tRCD/tRP 12.5 |

참고: config상 L1I prefetcher는 `no`지만, FDIP는 별도 frontend path에서 L1I prefetch를 발행한다.
L2C prefetcher는 I/D origin을 구분하지 못해 partition 실험을 오염시킬 수 있으므로 현재는 `no`로 둔다.

## Run ID / 목적 요약

"실험 목적"에는 이 run에서 새로 추가된 기능(없으면 스케일업/재실행이라고 명시)만 적는다. 버그 수정은 기능이 아니므로 "관련 문서" 다음 열에 따로 적는다.

| Run ID | 실험 목적 (기능 추가 / 스케일업) | 관련 문서 (Exp / Anal / Code) | 버그 수정 |
|---|---|---|---|
| `260707_2245_w500_i2000` | **기능 추가**<br>- FDIP ideal model 최초 이식(`5c19229`) | — | — |
| `260708_0856_w20_i100` | **스케일업**<br>- 코드 변경 없음, `w20/i100`으로 짧게 재실행 | — | — |
| `260713_1300_w1_i5_frontend_stall_test` | **기능 추가**<br>- L2C/LLC I/D origin 통계 분리(`11f08dc`)<br>- `fdip_enabled()` 조건 변경(`526782c`) | Exp: `2026_07_13_experiment.md` | — |
| `260713_2013_w20_i100_l2c_partition` | **기능 추가**<br>- L2C I/D static partition 최초 구현(`8de3d7b`)<br>- instruction bypass mode `0i8d` 추가(`6a6c4bd`) | Exp: `2026_07_13_experiment.md`, `2026_07_14_experiment.md`<br>Anal: `2026_07_14_analysis.md` | — |
| `260714_2030_w20_i300_l2c_partition` | **스케일업**<br>- 코드는 `260713_2013`와 동일<br>- trace 5-group→8-group, FTQ 전체, 실행 길이 확장 | Exp: `2026_07_15_experiment.md`<br>Anal: `2026_07_15_analysis.md`<br>Code: `2026_07_15_code_analysis.md` | - `f6602de` PTW MSHR pressure<br>- `yankee`/`sierra.a.4` 실패로 원인 발견, 이 run엔 미반영 |
| `260716_1305_w10_i20_latency_test` | **기능 추가**<br>- L2C way 기반 search latency 모델링(`c19adac`)<br>- `1i7d`/`8i0d` 정책 추가 | Exp: `2026_07_16_experiment.md`<br>Anal: `2026_07_16_analysis.md` | - `f6602de` 반영 상태로 시작<br>- `15d240d` L2C bypass response handling — `8i0d` 100% 실패를 발견·수정·재실행 완료 |
| `260716_1733_w20_i300_latency_test` | **스케일업**<br>- 코드는 `260716_1305`와 동일<br>- 길이만 `260714_2030`과 맞춤(`w20/i300`) | Exp: `2026_07_16_experiment.md`<br>Anal: `2026_07_21_analysis.md` | - `df0f567` PTW MSHR completion move — `yankee`/`sierra.a.4` 재발 실패 10건을 발견·수정·재실행 완료 |
| `0721_1438` | **기능/설정 변경**<br>- L2C replacement victim 후보를 partition 내부 way로 제한<br>- L2C prefetcher를 `ip_stride`에서 `no`로 변경 | Anal: `2026_07_21_analysis.md` | - L2C prefetcher가 I/D origin을 구분하지 못해 instruction-triggered prefetch가 data partition에 들어갈 수 있는 문제를 피하기 위한 설정 변경 |

## 실험 환경 및 코드 변경 이력

| Run ID | 날짜 | Trace (개수) | FTQ | L2C 정책 | Warmup / Simulation | 목적 | 이전 실험 대비 코드 변경 |
|---|---|---|---|---|---:|---|---|
| `260707_2245_w500_i2000` | 07-07 | `trace_gtrace_v2_all.txt` (343) | 2,4,16,32,64 | 없음(shared 고정, partition 기능 이전) | 50,000,000 / 200,000,000 | FDIP ideal model 최초 baseline | `5c19229` FDIP ideal model을 ChampSim(`ae8924d`)에 최초 이식 |
| `260708_0856_w20_i100` | 07-08 | `trace_gtrace_v2_all.txt` (343) | 2,4,16,32,64 | 없음 | 2,000,000 / 10,000,000 | 같은 baseline을 짧은 길이로 재실행 | (코드 동일) — 이 run 이후에 `526782c`(fdip_enabled 조건을 `FTQ_SIZE>0`으로 변경) / `11f08dc`(L2C·LLC I/D origin split 통계 추가)가 들어갔으나 이 run 자체엔 반영 안 됨 |
| `260713_1300_w1_i5_frontend_stall_test` | 07-13 | `trace_gtrace_v2_all.txt` (343) | 2,4,16,32,64 | 없음 | 100,000 / 500,000 | Frontend/backend stall breakdown 분석용 초단기 스모크 테스트 | `526782c`, `11f08dc` 반영된 상태에서 실행 (I/D origin split 통계를 활용한 첫 분석) |
| `260713_2013_w20_i100_l2c_partition` | 07-13 (본실행) + 07-14 (`0i8d` 추가) | 5-group set, 이후 `trace_gtrace_l2c_5groups.txt` (97) | 0,4,32 | `shared`/`2i6d`/`4i4d`/`6i2d` (본실행), `0i8d` 추가 실행 | 2,000,000 / 10,000,000 | L2C instruction/data way static partition 최초 실험 | `8de3d7b` frontend stall breakdown + L2C I/D static partition(`instruction_ways`/`data_ways`) 최초 구현; `0i8d` 결과는 다음날 `6a6c4bd`(L2C instruction bypass mode) 적용 후 추가 실행 |
| `260714_2030_w20_i300_l2c_partition` | 07-14 ~ 07-15 | `trace_gtrace_l2c_test.txt` (296, 8-group) | 0,2,4,16,32,64 (전체) | `shared`/`0i8d`/`2i6d`/`4i4d`/`6i2d` (5개) | 2,000,000 / 30,000,000 | 8-group 확장 trace set으로 L2C partition을 전체 FTQ에 걸쳐 장기 실행 | (코드는 `260713_2013`와 동일) trace set을 5-group→8-group으로 확장하고 FTQ/실행 길이를 늘림. 완료 후 발견된 `yankee_0012`/`0054`/`sierra.a.4_0014` 실패는 `f6602de`(PTW MSHR pressure)로 고쳤지만 이 run의 raw 데이터엔 반영 안 됨(재실행 안 함) |
| `260716_1305_w10_i20_latency_test` | 07-16 ~ 07-17 | `trace_gtrace_l2c_test.txt` (296) | 0,2,4,16,32,64 | 7개 전체(`shared`/`0i8d`/`1i7d`/`2i6d`/`4i4d`/`6i2d`/`8i0d`) | 1,000,000 / 2,000,000 | 최신 코드(특히 latency 모델링) 조건 검증용 스모크 테스트 | `f6602de`(PTW MSHR pressure) + `c19adac`(**L2C way 기반 search latency 모델링** — 이 실험 시리즈의 핵심 변경) 반영해 재시작. `1i7d`/`8i0d` 정책 신규 추가. `8i0d`가 100% 실패해서 `15d240d`(L2C bypass response handling)로 고친 뒤 `8i0d`만 재실행 |
| `260716_1733_w20_i300_latency_test` | 07-16 ~ 07-21 | `trace_gtrace_l2c_test.txt` (296) | 0,2,4,16,32,64 | 7개 전체 | 2,000,000 / 30,000,000 | `260714_2030`과 동일 길이로 latency 모델 효과를 caveat 없이 정식 비교 | `260716_1305`와 같은 코드로 시작(길이만 `260714_2030`과 맞춤). `yankee`/`sierra.a.4` 관련 신규 실패 10건 발견 → `df0f567`(PTW MSHR completion move)로 고친 뒤 재실행해 100% 완료 |
| `0721_1438` | 07-21 | 다음 실험 기준 설정 | 다음 실험에서 선택 | 다음 실험에서 선택 | 다음 실험에서 선택 | L2C partition 모델 정리 후 다음 실험 기준점 설정 | replacement policy가 partition 내부 way에서만 victim을 고르도록 API를 확장. L2C prefetcher는 I/D origin 오염을 피하기 위해 `ip_stride`에서 `no`로 변경 |

## 코드 변경 커밋 타임라인 (참고)

이 프로젝트 자체의 `ChampSim_FDIP` 변경만 시간순으로 나열(업스트림 ChampSim 커밋 제외):

| 커밋 | 날짜 | 내용 |
|---|---|---|
| `5c19229` | 07-07 | FDIP ideal model을 ChampSim(`ae8924d`)에 최초 이식 |
| `526782c` | 07-08 | `fdip_enabled()`를 `FTQ_SIZE > 0` 조건으로 변경 |
| `11f08dc` | 07-08 | L2C/LLC 통계를 instruction/data origin(`is_instr_fetch`)별로 분리 |
| `8de3d7b` | 07-14 | Frontend stall breakdown 추가 + L2C instruction/data way static partition 최초 구현 |
| `6a6c4bd` | 07-14 | L2C instruction bypass mode(`0i8d`) 추가 |
| `f6602de` | 07-15 | PTW MSHR 압박으로 인한 `std::bad_alloc` 수정(Bound PTW MSHR pressure) |
| `c19adac` | 07-15 | L2C partition별 way 기반 search latency 모델링 (`1i7d`/`8i0d` 정책 포함, 7개 정책 체계 완성) |
| `15d240d` | 07-16 | L2C bypass(`0i8d`/`8i0d`) 응답 처리 버그 수정 (`8i0d` 100% 실패 해결) |
| `df0f567` | 07-20 | PTW MSHR completion을 partition/copy에서 scan-and-move로 변경 (`yankee`/`sierra.a.4` 반복 재발 실패 해결) |

## 관련 문서

- `docs/exp/2026_07_13_experiment.md` — frontend/backend stall breakdown, L2C static partition 최초 구현
- `docs/exp/2026_07_14_experiment.md`, `docs/exp/2026_07_14_analysis.md` — L2C partition delta 그래프 설계 과정
- `docs/exp/2026_07_15_experiment.md`, `docs/exp/2026_07_15_analysis.md`, `docs/exp/2026_07_15_code_analysis.md` — `260714_2030` 장기 실행, `f6602de` PTW fix, L2C way partition/latency 모델 코드 분석
- `docs/exp/2026_07_16_experiment.md`, `docs/exp/2026_07_16_analysis.md` — latency 모델링 도입 후 스모크 테스트, `8i0d` 버그 발견/수정
- `docs/exp/2026_07_21_analysis.md` — `260714_2030`과 같은 길이로 진행한 정식 비교, `8i0d` 심층 분석
