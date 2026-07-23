# Overview Verification: ChampSim 계열 간 shared/split 비교

`ChampSim`/`ChampSim_DPC4`/`ChampSim_FDIP`와 이들의 L2 split 파생 fork(`ChampSim_Split`/`ChampSim_DPC4_Split`/`ChampSim_split_L2`) 사이에서, config를 최대한 맞춘 뒤 결과가 실제로 동일한지 검증한 것들을 모아 정리한다. 각 항목의 상세 절차/수치는 링크된 문서에 있다.

## 비교 결과 요약

| 비교 | 결과 | 근거 문서 |
|---|---|---|
| `ChampSim`(강제설정) vs `ChampSim_Split` | **일치** | [`2026_07_21_l2c_split_verification.md`](2026_07_21_l2c_split_verification) — shared 기준 metrics.csv 완전 일치(22 trace, numeric diff 0) |
| `ChampSim_Split`(2i6d/4i4d) vs `ChampSim_split_L2`(2i6d/4i4d, 또 다른 독립 구현체) | PTW lower level을 `L1D`로 맞추면 **일치** | [`2026_07_21_l2c_split_verification.md`](2026_07_21_l2c_split_verification) — 처음엔 PTW가 `L2DC`로 바로 연결돼 있어 불일치, 고친 뒤 exact match |
| `ChampSim`(강제설정) vs `ChampSim_DPC4_Split` | **불일치** | [`2026_07_22_dpc4_split_verification.md`](2026_07_22_dpc4_split_verification) "검증 배경" — base 코드 자체가 다르고(vanilla `ChampSim` vs DPC4 계열), `2i6d`/`4i4d`도 `DPC4_Split`의 parser가 아니라 수동 강제 설정이라 비교 자체가 잘못됨 — 검증 근거로 폐기 |
| `ChampSim_DPC4`(강제설정) vs `ChampSim_DPC4_Split` | **일치** | [`2026_07_22_dpc4_split_verification.md`](2026_07_22_dpc4_split_verification) — shared/2i6d/4i4d 전부 exact match(22 trace, numeric diff 0) |
| `ChampSim_Split` vs `ChampSim_DPC4_Split` | **불일치** | [`2026_07_23_champ_split_vs_dpc4_split_verification.md`](2026_07_23_champ_split_vs_dpc4_split_verification) — 같은 config signature/g2 trace여도 base 코드 계열 차이로 exact match 아님 |
| `ChampSim_FDIP`(partition) vs `ChampSim_Split` | **불일치** | [`2026_07_22_partition_vs_split_verification.md`](2026_07_22_partition_vs_split_verification) |

## 비교에 사용한 폴더

위 요약의 각 비교가 실제로 몇 회차(round)로 진행됐는지, 그리고 매 회차마다 정확히 어떤 두 폴더를 비교했는지 정리한다. 2~3번 다시 비교한 경우 재비교했던 조합을 전부 적는다.

| 비교 | 회차 | 비교 대상 (A/B) | 회차 결과 |
|---|---|---|---|
| `ChampSim` vs `ChampSim_Split` | 1회차 (prefetcher 미정합) | - `260721_2130_w10_i100_champ_hard_config_2g` (`ChampSim`, L1D/L2C prefetcher `no`/`no`)<br>- `260721_2005_w10_i100_champ_split_2g` (`ChampSim_Split` shared, prefetcher `next_line`/`ip_stride`) | 불일치 (prefetcher config mismatch로 비교 자체가 부적합 판정, 폐기) |
| `ChampSim` vs `ChampSim_Split` | 2회차 (prefetcher 정합 후) | - `260722_1228_w10_i100_champ_hard_config_matched_prefetch_2g` (`ChampSim`, prefetcher `next_line`/`ip_stride`로 정합)<br>- `260721_2005_w10_i100_champ_split_2g` (동일, 1회차와 같은 baseline 재사용) | 일치 (numeric diff 0) |
| `ChampSim_Split` vs `ChampSim_split_L2` | 1회차 (`2i6d`, PTW→`L2DC`) | - `260722_1228_w10_i100_champ_hard_config_matched_prefetch_2g` (`ChampSim_split_L2`, `2i6d`, PTW lower level `L2DC`)<br>- `260721_2005_w10_i100_champ_split_2g` (`ChampSim_Split`, `2i6d`) | 불일치 (IPC/cycle/L1D MPKI 등 21개 column 차이) |
| `ChampSim_Split` vs `ChampSim_split_L2` | 2회차 (`2i6d`, PTW→`L1D`로 수정) | - `260722_1228_w10_i100_champ_hard_config_matched_prefetch_2g` (재빌드, `ChampSim_split_L2`, `2i6d`, PTW lower level `L1D`)<br>- `260721_2005_w10_i100_champ_split_2g` (동일) | 일치 (numeric diff 0) |
| `ChampSim_Split` vs `ChampSim_split_L2` | 3회차 (`4i4d`) | - `260722_1228_w10_i100_champ_hard_config_matched_prefetch_2g` (재빌드, `ChampSim_split_L2`, `4i4d`, PTW `L1D`)<br>- `260721_2005_w10_i100_champ_split_2g` (동일, `4i4d`) | 일치 (numeric diff 0) |
| `ChampSim`(강제설정) vs `ChampSim_DPC4_Split` | 시도(1회) | - `260722_1228_w10_i100_champ_hard_config_matched_prefetch_2g` (`ChampSim` 강제설정, shared/`2i6d`/`4i4d`)<br>- 특정 폴더로 확정 못 함 (`ChampSim_DPC4_Split`, base 코드 계열 자체가 달라 폴더 페어 확정 전에 비교 방식을 폐기, `ChampSim_DPC4` vs `ChampSim_DPC4_Split`로 재설계) | 불일치 (방법론 자체가 무효, 폐기) |
| `ChampSim_DPC4`(강제설정) vs `ChampSim_DPC4_Split` | shared | - `260722_1953_w10_i100_dpc4_hard_config_comp_split_2g` (`ChampSim_DPC4`)<br>- `260722_1830_w10_i100_dpc4_split_2g` (`ChampSim_DPC4_Split`) | 일치 (numeric diff 0) |
| `ChampSim_DPC4`(강제설정) vs `ChampSim_DPC4_Split` | `2i6d` | - `260722_1953_w10_i100_dpc4_hard_config_comp_split_2g` (재빌드, `2i6d`)<br>- `260722_1830_w10_i100_dpc4_split_2g` (동일) | 일치 (numeric diff 0) |
| `ChampSim_DPC4`(강제설정) vs `ChampSim_DPC4_Split` | `4i4d` | - `260722_1953_w10_i100_dpc4_hard_config_comp_split_2g` (재빌드, `4i4d`)<br>- `260722_1830_w10_i100_dpc4_split_2g` (동일) | 일치 (numeric diff 0) |
| `ChampSim_Split` vs `ChampSim_DPC4_Split` | `shared`/`2i6d`/`4i4d` | - `260721_2005_w10_i100_champ_split_2g` (`ChampSim_Split`, g2)<br>- `260722_1830_w10_i100_dpc4_split_2g` (`ChampSim_DPC4_Split`, g2) | 불일치 (config signature는 같지만 DPC4_Split IPC가 평균 +0.006 높고 L1D MPKI가 약 -6.9 낮음) |
| `ChampSim_FDIP`(partition) vs `ChampSim_Split` | 1회차 (원래, core 폭 불일치) | - `260722_1646_w10_i100_fdip_partition_comp_champ_split` (`ChampSim_FDIP`, 296 trace 전체)<br>- `260722_1449_w10_i100_champ_split` (`ChampSim_Split`, 296 trace 전체) | 불일치 (L1D MPKI 등 크게 벌어짐) |
| `ChampSim_FDIP`(partition) vs `ChampSim_Split` | 2회차 (core 폭 정합) | - `260722_1943_w10_i100_fdip_partition_comp_champ_split_core_matched_2g` (`ChampSim_FDIP`, g2/22 trace, `ooo_cpu` 파라미터 정합)<br>- `260721_2005_w10_i100_champ_split_2g` (`ChampSim_Split`, g2/22 trace) | 불일치 (L1I는 거의 일치, L1D gap은 유지) |
| `ChampSim_FDIP`(partition) vs `ChampSim_Split` | 3회차 (DRAM 타이밍까지 정합) | - `260722_2252_w10_i100_fdip_partition_comp_champ_split_dram_matched_2g` (`ChampSim_FDIP`, g2/22 trace, DRAM timing까지 정합)<br>- `260721_2005_w10_i100_champ_split_2g` (동일, 2회차와 같은 baseline 재사용) | 불일치 (L1D gap 변화 없음 — store-to-load forwarding 유무가 근본 원인으로 확정) |

## 폴더별 실행 바이너리와 비교 기준

폴더명은 비교 목적을 드러내도록 정리했지만, 실제로 trace를 생성한 바이너리와 비교 기준을 분리해서 읽어야 한다. 아래 표는 각 결과 폴더가 어느 ChampSim 계열로 실행됐고, 분석에서 어떤 폴더와 비교됐는지를 정리한 것이다.

| 결과 폴더 | trace 생성 바이너리 | trace 범위 | 비교 기준 폴더 | 비교 목적 |
|---|---|---|---|---|
| `outputs/260721_2005_w10_i100_champ_split_2g` | `ChampSim_Split` | g2, 22 traces | `outputs/verify/260721_2130_w10_i100_champ_hard_config_2g` 또는 `outputs/verify/260722_1228_w10_i100_champ_hard_config_matched_prefetch_2g` | `ChampSim`/`ChampSim_split_L2` 강제 설정 결과가 `ChampSim_Split`와 일치하는지 확인하는 기준 baseline |
| `outputs/260722_1449_w10_i100_champ_split` | `ChampSim_Split` | 전체, 296 traces | `outputs/verify/260722_1646_w10_i100_fdip_partition_comp_champ_split` | 전체 trace 기준 `ChampSim_FDIP` partition 결과와 `ChampSim_Split` split 결과 비교 |
| `outputs/verify/260721_2130_w10_i100_champ_hard_config_2g` | `ChampSim` | g2, 22 traces | `outputs/260721_2005_w10_i100_champ_split_2g` | 원본 `ChampSim` shared와 `ChampSim_Split shared` 비교. prefetcher config가 달라서 비교 부적합으로 폐기 |
| `outputs/verify/260722_1228_w10_i100_champ_hard_config_matched_prefetch_2g` | `ChampSim` shared, 이후 `ChampSim_split_L2` 2i6d/4i4d | g2, 22 traces | `outputs/260721_2005_w10_i100_champ_split_2g` | prefetcher까지 맞춘 `ChampSim shared` 및 독립 split 구현체(`ChampSim_split_L2`)가 `ChampSim_Split`와 일치하는지 확인 |
| `outputs/verify/260722_1646_w10_i100_fdip_partition_comp_champ_split` | `ChampSim_FDIP` | 전체, 296 traces | `outputs/260722_1449_w10_i100_champ_split` | FDIP partition과 ChampSim split의 전체 trace 비교. core 폭 불일치가 남아 있던 1차 비교 |
| `outputs/verify/260722_1943_w10_i100_fdip_partition_comp_champ_split_core_matched_2g` | `ChampSim_FDIP` | g2, 22 traces | `outputs/260721_2005_w10_i100_champ_split_2g` | `ooo_cpu` core 폭을 `ChampSim_Split`와 맞춘 뒤 FDIP partition과 ChampSim split 비교 |
| `outputs/verify/260722_2252_w10_i100_fdip_partition_comp_champ_split_dram_matched_2g` | `ChampSim_FDIP` | g2, 22 traces | `outputs/260721_2005_w10_i100_champ_split_2g` | core 폭에 더해 DRAM timing까지 맞춘 뒤 FDIP partition과 ChampSim split 비교 |
| `outputs/260722_1830_w10_i100_dpc4_split_2g` | `ChampSim_DPC4_Split` | g2, 22 traces | `outputs/verify/260722_1953_w10_i100_dpc4_hard_config_comp_split_2g` | DPC4 split parser가 만든 shared/2i6d/4i4d 결과의 기준 |
| `outputs/verify/260722_1953_w10_i100_dpc4_hard_config_comp_split_2g` | `ChampSim_DPC4` | g2, 22 traces | `outputs/260722_1830_w10_i100_dpc4_split_2g` | DPC4에 split 구조를 수동 hard-config로 반영한 결과가 `ChampSim_DPC4_Split`와 일치하는지 확인 |

추가로, `outputs/260721_2005_w10_i100_champ_split_2g`와 `outputs/260722_1830_w10_i100_dpc4_split_2g`는 서로 직접 비교도 했다. 이 경우 두 폴더는 각각 자기 base(`ChampSim` 계열, DPC4 계열) 위에서 만든 split 결과이므로 exact match를 기대하지 않는다. 실제 비교에서도 config signature는 같지만 numeric result는 일치하지 않았다. 자세한 내용은 [`2026_07_23_champ_split_vs_dpc4_split_verification.md`](2026_07_23_champ_split_vs_dpc4_split_verification)에 정리했다.

## 읽는 법

3개 비교(`ChampSim` vs `Split`, `DPC4` vs `DPC4_Split`, `Split` vs `split_L2`)는 **같은 base 계열 또는 수동 hard-config로 같은 hierarchy를 만든 경우 전부 일치**했다.

`ChampSim`(강제설정) vs `ChampSim_DPC4_Split`의 불일치는 애초에 base 코드 계열이 다른 잘못된 비교였고, `ChampSim_DPC4`(강제설정) vs `ChampSim_DPC4_Split`로 base를 맞춰 다시 비교하니 바로 일치했다 — 즉 "같은 base 코드 계열 안에서는 split 구현이 원래 동작을 보존한다"는 것을 뒷받침한다.

반대로 `ChampSim_Split` vs `ChampSim_DPC4_Split`처럼 서로 다른 base 계열의 split fork를 직접 비교하면, config signature가 같아도 exact match가 아니다. 이 비교는 두 split 구현이 같은지 확인하는 검증이라기보다, vanilla ChampSim 계열과 DPC4 계열 사이의 residual base 차이를 확인하는 보조 자료로 읽어야 한다.

## `ChampSim_FDIP` vs `ChampSim_Split` 불일치 상세

이 비교만 유일하게 config를 다 맞춰도 안 맞았다. 3단계로 좁혀갔다.

1. **원래(core 폭 불일치)** — 크게 불일치.
2. **core 폭(`fetch_width`/`decode_width`/`execute_width` 등) 맞춘 뒤** — L1I는 거의 일치, L1D만 여전히 크게 벌어짐.
3. **DRAM 타이밍(`tCAS`/`tRCD`/`tRP`/`tRAS`)까지 맞춘 뒤** — L1D gap 변화 없음(가설 기각).
4. **코드 diff로 원인 확정** — `ChampSim_FDIP`만 store-to-load forwarding을 구현(`ooo_cpu.cc`의 `LSQ_ENTRY.forwarded`, `execute_load`의 `if (lq_entry.forwarded) return false;`)하고, `ChampSim_Split`은 이 로직이 아예 없다. Config로는 맞출 수 없는 진짜 코드 차이다.

자세한 수치·코드 인용은 [`2026_07_22_partition_vs_split_verification.md`](2026_07_22_partition_vs_split_verification) 참고.
