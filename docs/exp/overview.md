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
| `260721_1451_w10_i20_fix_repl_bug` | **기능/설정 변경**<br>- L2C replacement victim 후보를 partition 내부 way로 제한(`73980b3`)<br>- L2C prefetcher를 `ip_stride`에서 `no`로 변경 | Exp: `2026_07_21_experiment.md`<br>Code: `2026_07_21_code.md`<br>Anal: `2026_07_21_analysis.md` | — |
| `260721_1707_w10_i20_latency_revert_test` | **설정 변경**<br>- L2C way 기반 search latency 모델을 컴파일타임 토글(`CHAMPSIM_L2C_WAY_LATENCY`, 기본 off)로 되돌려 원래 고정 latency와 비교 가능하게 함 | Code: `2026_07_21_latency_off_code.md`<br>Exp: `2026_07_21_latency_off_experiment.md` | — |
| `260721_2005_w10_i100_champ_split_2g` | **기능 추가**<br>- 새 서브모듈 `ChampSim_L2C`(이후 `ChampSim_Split`으로 개명) 추가 — L1I/L1D가 하나의 `L2C` way를 나눠 쓰는 대신 `L2I`/`L2D`를 별도 cache object로 물리 분리(`38a1489`)<br>- `run.sh`가 `-f`/`-L2C` 미지정 시 ChampSim에 아예 안 넘기도록 변경 | Code: `2026_07_21_l2c_split_code.md`<br>Exp: `2026_07_21_l2c_split_experiment.md` | - `-L2C` 미지정 시 L2I/L2D 8-way 분리가 기본값이 되던 버그를 base config `partition:"shared"` 추가로 수정(`8625dc5`) |
| `260721_2130_w10_i100_champ_hard_config_2g`/`260722_1228_w10_i100_champ_hard_config_matched_prefetch_2g` | **검증**<br>- `ChampSim_Split shared` 결과가 원본 `ChampSim`과 완전히 동일한지 검증<br>- 별도 구현체 `ChampSim_split_L2`(L2IC/L2DC 명명)와 `ChampSim_Split`의 `2i6d`/`4i4d`가 동일한지 교차 검증 | Verif.: `2026_07_21_l2c_split_verification.md` | - `ChampSim_split_L2`의 PTW lower level이 `L2DC`로 바로 연결돼 있던 것을 `L1D` 경유로 수정<br>- parser에 `L2IC`/`L2DC` → `L2I`/`L2D` alias 추가 |
| `260722_1449_w10_i100_champ_split` | **재실행**<br>- `260721_2121`의 shared 로그에서 `LOAD_I`/`LOAD_D` origin-split 줄이 안 찍히던 문제를 확인한 뒤, 이를 포함해 전체 `l2c_test` set으로 재실행(진행 중) | Exp: `2026_07_22_l2c_split_experiment.md` | - parser가 split-L2에서 완전히 bypass된 쪽(`0i8d`/`8i0d`)의 `l2i_mpki`/`l2d_mpki`를 blank 대신 `0.0`으로 채우도록 수정 |
| `260722_1646`/`260722_1943`/`260722_2252_w10_i100_partition_comp_split_*` | **검증**<br>- `ChampSim_FDIP`(partition)와 `ChampSim_Split`(split)이 config를 다 맞춰도 동일한지 3단계로 검증(원래 → core 폭 매칭 → DRAM 타이밍 매칭) | Verif.: `2026_07_22_partition_vs_split_verification.md` | - FDIP prefetcher를 Split 기준(L1D `next_line`, L2C `ip_stride`)으로 맞춤<br>- `inc/l2c_latency_toggle.h` 도입해 L2C/LLC latency 스타일을 macro로 토글<br>- 최종 결론: L1D MPKI 잔차는 `ChampSim_FDIP`만 구현한 store-to-load forwarding(`LSQ_ENTRY.forwarded`) 차이 때문 — config로 못 고치는 코드 차이 |
| `260722_1830_w10_i100_dpc4_split_2g`/`260722_1953_w10_i100_dpc4_hard_config_comp_split_2g` | **검증**<br>- `ChampSim_DPC4`에 split 구조를 수동으로 반영한 결과가 `ChampSim_DPC4_Split`의 parser-generated 결과와 동일한지 검증(shared/2i6d/4i4d) | Verif.: `2026_07_22_dpc4_split_verification.md` | — |
| `260723_1351_w10_i100_dpc4_split_berti_pythia` | **기능 추가**<br>- `ChampSim_DPC4_Split`에서 L1D `berti`, L2C `pythia` 프리페처로 전체 `l2c_test` set(296) × 6 policy 실행 | Exp: `2026_07_23_experiment.md`<br>Anal: `2026_07_23_dpc4_split_berti_pythia_analysis.md` | — |

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
| `260721_1451_w10_i20_fix_repl_bug` | 07-21 | `trace_gtrace_l2c_test.txt` (296) | 0,4,32 | `shared`/`0i8d`/`2i6d`/`4i4d`/`6i2d` | 1,000,000 / 2,000,000 | replacement 제약 + prefetcher 제거 효과를 짧게 확인 | `73980b3` replacement가 partition 내부 way에서만 victim을 고르도록 API 확장, partition-outside fallback 제거. L2C prefetcher `ip_stride`→`no` |
| `260721_1707_w10_i20_latency_revert_test` | 07-21 | `trace_gtrace_l2c_test.txt` (296) | 0만 | `shared`/`0i8d`/`2i6d`/`6i2d` | 1,000,000 / 2,000,000 | way 기반 latency 모델을 끈 상태에서 replacement 제약만의 효과를 순수하게 확인 | `effective_l2c_search_latency()`가 `CHAMPSIM_L2C_WAY_LATENCY` 매크로로 way 기반/고정 `HIT_LATENCY`를 토글하도록 변경(기본 off = 고정 latency) |
| `260721_2005_w10_i100_champ_split_2g` | 07-21 | `l2c_test_g2.txt` (22, delta+sierra.a.6) | 미지정(FDIP 없음) | `shared`/`0i8d`/`2i6d`/`4i4d`/`6i2d`/`8i0d` | 1,000,000 / 10,000,000 | 새 물리 분리 L2 서브모듈(`ChampSim_L2C`→`ChampSim_Split`)이 정상 빌드/실행되는지 스모크 테스트 | `38a1489` config-driven split L2 hierarchy(정적 partition이면 `L1I→L2I`, `L1D→L2D` 물리 분리, 0-way는 LLC로 bypass) 최초 추가 |
| `260721_2130_w10_i100_champ_hard_config_2g`/`260722_1228_w10_i100_champ_hard_config_matched_prefetch_2g` | 07-21~07-22 | `l2c_test_g2.txt` (22) | 0만 | 원본 `ChampSim` shared, `ChampSim_split_L2` 2i6d/4i4d 강제 설정 | 1,000,000 / 10,000,000 | `ChampSim_Split`의 shared/split 결과가 참조 구현들과 정확히 일치하는지 검증(성능 실험 아님) | 원본 `ChampSim`/`ChampSim_split_L2`에 `--ftq_size` 호환 옵션 추가 후 제거, `ChampSim_split_L2`의 PTW lower level을 `L2DC`에서 `L1D`로 수정, parser에 `L2IC/L2DC` alias 추가 |
| `260722_1449_w10_i100_champ_split` | 07-22 | `trace_gtrace_l2c_test.txt` (296) | 미지정(FDIP 없음) | `shared`/`0i8d`/`2i6d`/`4i4d`/`6i2d`/`8i0d` | 1,000,000 / 10,000,000 | `260721_2121`(shared I/D 로그 누락으로 삭제) 재실행 | `ChampSim_Split`가 `shared`에서도 FDIP처럼 `TOTAL_I`/`LOAD_I`/`TOTAL_D`/`LOAD_D`를 찍는지 확인. parser의 split-L2 bypass MPKI 0-fill 수정 반영 |
| `260722_1646`/`260722_1943`/`260722_2252_w10_i100_partition_comp_split_*` | 07-22 | `trace_gtrace_l2c_test.txt` (296) 또는 `l2c_test_g2.txt` (22) | 미지정 | `shared`/`0i8d`/`2i6d`/`4i4d`/`6i2d`/`8i0d` | 1,000,000 / 10,000,000 | `ChampSim_FDIP`(partition) vs `ChampSim_Split`(split) 동등성 검증 — config를 3단계로 점점 더 맞춰가며 재실행 | 각 단계에서 FDIP의 `champsim_config.json`(prefetcher/L2C·LLC latency/`ooo_cpu` 코어 폭/`physical_memory` DRAM 타이밍)을 Split과 동일하게 수정. `98d3bd6` L2C/LLC latency 토글 도입 |
| `260722_1830_w10_i100_dpc4_split_2g`/`260722_1953_w10_i100_dpc4_hard_config_comp_split_2g` | 07-22 | `l2c_test_g2.txt` (22) | 미지정 | `shared`/`2i6d`/`4i4d` | 1,000,000 / 10,000,000 | `ChampSim_DPC4` vs `ChampSim_DPC4_Split` 동등성 검증(성능 실험 아님) | `ChampSim_DPC4`에 `L2IC`/`L2DC` 물리 분리 구조를 수동 반영해서 `ChampSim_DPC4_Split`의 config-driven split(`b70492b`)과 비교 |
| `260723_1351_w10_i100_dpc4_split_berti_pythia` | 07-23 | `trace_gtrace_l2c_test.txt` (296) | 미지정(FDIP 없음) | `shared`/`0i8d`/`2i6d`/`4i4d`/`6i2d`/`8i0d` | 1,000,000 / 10,000,000 | `ChampSim_DPC4_Split`에서 L1D `berti`/L2C `pythia` 프리페처로 L2C partition 정책 전체를 처음 정식 실행. 1,776/1,776 완료, 실패 0. `8i0d`의 shared 대비 이득이 `next_line`/`ip_stride` 대비 3배 이상 커짐(+0.98%→+3.23%) | `ChampSim_DPC4_Split`의 `4615b7d`(split cache logging stats) 반영된 상태. prefetcher를 `next_line`/`ip_stride`가 아닌 `berti`/`pythia`로 변경 |

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
| `73980b3` | 07-21 | L2C replacement victim 후보를 partition 내부 way로 제한, partition-outside fallback 제거. L2C prefetcher `ip_stride`→`no` |
| `44c61bb` | 07-21 | L2C way 기반 search latency 모델을 `CHAMPSIM_L2C_WAY_LATENCY` 컴파일타임 토글로 감쌈(기본 off = 고정 latency) |
| `d589b1b` | 07-22 | `FTQ_SIZE` 기본값을 32→0으로 변경 — `--ftq_size` 미지정 시 FDIP off로 동작 |
| `98d3bd6` | 07-22 | `inc/l2c_latency_toggle.h` 도입, `config.sh`가 이 값을 읽어 L2C/LLC latency를 명시값(way 기반)/단일 필드(고정) 중 하나로 생성하도록 변경 |

`ChampSim_L2C`/`ChampSim_Split`(같은 서브모듈, 도중에 개명됨) 자체 변경:

| 커밋 | 날짜 | 내용 |
|---|---|---|
| `38a1489` | 07-21 | config-driven split L2 hierarchy 최초 추가 — `static` partition이면 `L1I→L2I`/`L1D→L2D` 물리 분리, 0-way는 LLC로 bypass |
| `b6c2fc3` | 07-21 | `--ftq_size` no-op 호환 옵션 제거(`run.sh`가 `-f` 미지정 시 아예 안 넘기도록 바뀌어 더 이상 필요 없음) |
| `8625dc5` | 07-21 | base config에 `partition:"shared"` 추가 — `-L2C` 미지정 시 L2I/L2D 8-way 분리가 기본값이 되던 버그 수정 |

`ChampSim_DPC4_Split`(DPC4 계열에 같은 split L2 개념을 이식한 별도 서브모듈) 자체 변경:

| 커밋 | 날짜 | 내용 |
|---|---|---|
| `b70492b` | — | config-driven split L2 hierarchy 추가(`ChampSim_L2C`의 `38a1489`와 같은 개념을 DPC4 base 위에 이식) |
| `4615b7d` | — | split cache logging stats 추가 |

## 관련 문서

- `docs/exp/2026_07_13_experiment.md` — frontend/backend stall breakdown, L2C static partition 최초 구현
- `docs/exp/2026_07_14_experiment.md`, `docs/exp/2026_07_14_analysis.md` — L2C partition delta 그래프 설계 과정
- `docs/exp/2026_07_15_experiment.md`, `docs/exp/2026_07_15_analysis.md`, `docs/exp/2026_07_15_code_analysis.md` — `260714_2030` 장기 실행, `f6602de` PTW fix, L2C way partition/latency 모델 코드 분석
- `docs/exp/2026_07_16_experiment.md`, `docs/exp/2026_07_16_analysis.md` — latency 모델링 도입 후 스모크 테스트, `8i0d` 버그 발견/수정
- `docs/exp/2026_07_21_analysis.md` — `260714_2030`과 같은 길이로 진행한 정식 비교, `8i0d` 심층 분석
- `docs/exp/2026_07_21_experiment.md`, `docs/exp/2026_07_21_code.md` — `73980b3` replacement 제약 + prefetcher 제거, `260721_1451_w10_i20_fix_repl_bug` 실행
- `docs/exp/2026_07_21_latency_off_code.md`, `docs/exp/2026_07_21_latency_off_experiment.md` — L2C way 기반 latency 모델을 컴파일타임 토글로 되돌린 `260721_1707_w10_i20_latency_revert_test`
- `docs/exp/2026_07_21_l2c_split_code.md`, `docs/exp/2026_07_21_l2c_split_experiment.md` — `ChampSim_L2C`(→`ChampSim_Split`) 물리 분리 L2 서브모듈 최초 도입과 스모크 테스트
- `docs/exp/2026_07_21_l2c_split_verification.md` — 원본 `ChampSim`·`ChampSim_split_L2`와의 shared/split 동일성 교차 검증
- `docs/exp/2026_07_22_l2c_split_experiment.md` — shared 로그 I/D origin-split 누락 확인 후 `260722_1449_w10_i100_champ_split` 재실행
- `docs/exp/2026_07_22_partition_vs_split_verification.md` — `ChampSim_FDIP`(partition) vs `ChampSim_Split`(split) 동등성 검증, config를 다 맞춰도 남는 L1D MPKI 차이의 코드 레벨 원인(store-to-load forwarding) 분석
- `docs/exp/2026_07_22_dpc4_split_verification.md` — `ChampSim_DPC4` vs `ChampSim_DPC4_Split` shared/split 동일성 검증
- `docs/exp/overview_verification.md` — 위 두 검증을 포함해 `ChampSim` 계열 fork 간 shared/split 비교 결과를 한 표로 요약
- `docs/exp/2026_07_23_experiment.md`, `docs/exp/2026_07_23_dpc4_split_berti_pythia_analysis.md` — `ChampSim_DPC4_Split`에 `berti`/`pythia` 프리페처 적용, `260722_1449_w10_i100_champ_split`(prefetcher 변경 전) 대비 L2C partition 경향 변화 분석
