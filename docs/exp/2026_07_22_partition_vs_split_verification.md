# 2026-07-22 Verification: split vs partition

## 비교 불가 이유

`260721_1707_w10_i20_latency_revert_test`(FDIP, partition)와 `260721_2005_w10_i100_champ_split_2g`(ChampSim_Split, split)는 다음 조건이 서로 달라서 직접 비교할 수 없었다.

- **Simulation instruction 수**: FDIP는 `i=2,000,000`, Split은 `i=10,000,000`으로 5배 차이.
- **L1D/L2 prefetcher**: FDIP는 L1D `ip_stride`/L2C `no`, Split은 L1D `next_line`/L2C `ip_stride`.
- **L2C/LLC 실효 latency**: FDIP는 `hit_latency`/`fill_latency` 명시값(L2C 8/1, LLC 16/1), Split은 단일 `latency` 필드(L2C 10, LLC 20)를 `cache_builder`의 `fill=(latency+1)/2, hit=latency-fill` 공식으로 유도(L2C 5/5, LLC 10/10) — 스타일이 달라서 우연히도 같은 값이 아니었다.

`shared`(partition 로직이 아예 없는 baseline)조차 이 차이들 때문에 trace별로 최대 ±0.41 IPC 차이가 났다.

## 조치: latency 차이를 수정해서 커밋

`inc/l2c_latency_toggle.h`를 만들어 `CHAMPSIM_L2C_WAY_LATENCY` 매크로를 단일 소스로 두고, `config.sh`가 이 값을 읽어 매크로가 꺼져 있으면(기본값) L2C/LLC에 Split과 동일한 단일 `latency` 필드(10/20)를 생성하도록 했다. `src/cache.cc`의 `effective_l2c_search_latency()`는 다시 `HIT_LATENCY`만 읽도록 단순화했다. `champsim_config.json`의 이제 무의미해진 `hit_latency`/`fill_latency` 명시값은 지웠다.

- 커밋 `98d3bd6` "Make L2C/LLC latency style follow the way-latency toggle"

L1D/L2 prefetcher를 Split 기준으로 맞춘 것은 별도 변경(uncommitted), `-f` 미지정 시 FDIP off로 동작하게 한 것도 별도 커밋(`d589b1b`)이다. 남은 confound는 simulation instruction 수뿐이며, 아래에서 조건을 맞춰 재검증한다.

---

## 비교 대상

| 항목 | `260722_1449_w10_i100_champ_split` (split, 완료) | `260722_1646_w10_i100_fdip_partition_comp_champ_split` (partition, 이번 실행) |
|---|---|---|
| ChampSim dir | `ChampSim_Split` | `ChampSim_FDIP` |
| Trace list | `trace_gtrace_l2c_test.txt` (296) | 동일 |
| L2C mask | `0x7b` (`shared`/`0i8d`/`2i6d`/`4i4d`/`6i2d`/`8i0d`) | 동일 |
| FTQ | 미지정(`ChampSim_Split`는 FDIP 없음) | 미지정(FDIP off로 동작) |
| Warmup / Simulation | 1,000,000 / 10,000,000 | 동일 |
| 병렬도 | 58 | 58 |
| L1D / L2 prefetcher | `next_line` / `ip_stride` | 동일(맞춤 완료) |
| L2C/LLC latency | `latency:10` / `latency:20` (단일 필드) | 동일(맞춤 완료, `CHAMPSIM_L2C_WAY_LATENCY` 기본 off) |

## 빌드 및 실행

빌드(7개 정책 바이너리 전체, 최신 latency toggle + prefetcher 설정 반영):

```bash
./scripts/run.sh -b -L2C 0x7f
```

실행(`-f` 미지정 → FDIP off, `260722_1449`와 동일 조건):

```bash
./scripts/run.sh -t -T trace_gtrace_l2c_test.txt -L2C 0x7b -w 1000000 -i 10000000 -p 58 -r 260722_1646_w10_i100_fdip_partition_comp_champ_split
```

2026-07-22 16:46 시작. 빌드는 16:41~16:42에 완료해뒀다. `260722_1449_w10_i100_champ_split`는 이미 완료된 상태라 방해되지 않는다.

---

## 결과 분석

`260722_1646_w10_i100_fdip_partition_comp_champ_split`은 1,776 job 중 1,775개 성공(`yankee_0014` 1건 exit 134 — 이전에도 병렬 실행 중 산발적으로 재현되던 것과 같은 실패). Summary 생성 후 `260722_1449_w10_i100_champ_split`와 6개 policy 전부(`shared`/`0i8d`/`2i6d`/`4i4d`/`6i2d`/`8i0d`) 공통 trace 기준으로 비교했다.

### Config "서명"은 일치하지만, 실제로는 코어 파이프라인 크기가 다르다

`config_signature.txt`의 `shared` 서명은 두 run에서 문자 그대로 같다.

```text
bimodal-basic_btb-no-next_line-ip_stride-l2cshared-no-lru-1core
```

instruction 수도 거의 완전히 일치(최대 오차 4개, 평균 0.01개 — warmup 경계 반올림 수준)했고, **branch MPKI는 모든 policy에서 소수점까지 정확히 일치**(평균 차이 −0.0001 이하)했다. 하지만 이 서명은 `branch_predictor`/`btb`/prefetcher 이름만 담고 있고, **OoO 코어 파이프라인 크기는 전혀 검증하지 않는다.** 두 base config의 `ooo_cpu`를 직접 비교하면 다음이 다르다.

| 항목 | FDIP | Split |
|---|---:|---:|
| `fetch_width` | 8 | 6 |
| `decode_width` | 4 | 6 |
| `decode_buffer_size` | 192 | 32 |
| `dispatch_width` | 5 | 6 |
| `execute_width` | 10 | 4 |
| `execute_latency` | 1 | 0 |
| `register_file_size` | 280 | 128 |
| `scheduler_size` | 160 | 128 |

**이게 진짜 원인이다.** `ChampSim_FDIP`는 훨씬 넓고 공격적인 코어(fetch 8-wide, execute 10-wide, decode buffer 192)인 반면 `ChampSim_Split`는 훨씬 좁은 코어(fetch 6-wide, execute 4-wide, decode buffer 32)다. 코어 폭이 다르면 추측 실행 깊이·wrong-path 메모리 접근·MSHR 압박이 전부 달라지고, 이게 L1I/L1D miss 패턴을 바꾼다 — L2C partition이나 split 방식과는 무관하게, 두 시뮬레이터가 애초에 다른 CPU를 모델링하고 있었던 것이다. branch predictor는 fetch-width와 무관하게 매 사이클 동일하게 예측하므로 정확히 일치했던 것도 이걸로 설명된다.

### L1I/L1D MPKI는 policy와 무관하게 일정한 차이가 난다(코어 폭 차이의 증거)

| policy | 평균 dL1I MPKI | 평균 dL1D MPKI | 평균 dBranch MPKI |
|---|---:|---:|---:|
| `shared` | +2.751 | +3.348 | ≈0 |
| `0i8d` | +2.847 | +3.364 | ≈0 |
| `2i6d` | +2.801 | +3.338 | ≈0 |
| `4i4d` | +2.751 | +3.351 | ≈0 |
| `6i2d` | +2.713 | +3.372 | ≈0 |
| `8i0d` | +2.692 | +3.290 | ≈0 |

L1I/L1D prefetcher는 `no`/`next_line`로 완전히 동일한데도, Split 쪽 L1I MPKI가 항상 +2.7~+2.85, L1D MPKI가 항상 +3.29~+3.37 더 높다. **6개 policy 전부에서 거의 같은 크기**라는 점이 핵심이다 — L2C partition을 얼마나 공격적으로 나누는지(`0i8d`/`8i0d` 극단 vs `4i4d` 균등)와 무관하게 갭이 똑같다면, 이건 L2C partition vs split 아키텍처 차이가 아니라 **두 코드베이스 자체의 다른 baseline 차이**(L1I/L1D보다 하위 계층에서 오는 게 아니라, L1 자체 접근 패턴을 만드는 파이프라인/타이밍 로직 차이)라는 뜻이다. `ChampSim_FDIP`는 FDIP 관련 frontend/파이프라인 수정이 많이 들어간 fork라, FDIP가 꺼져 있어도(`ftq` 미지정) 그 수정들이 남긴 타이밍 차이가 L1 miss 패턴에 영향을 주는 것으로 보인다.

### IPC / L2C MPKI 비교

| policy | n | 평균 dIPC | 최대 abs dIPC | 평균 dL2C MPKI |
|---|---:|---:|---:|---:|
| `shared` | 296 | −0.0290 | 0.352 | −0.488 |
| `0i8d` | 296 | −0.0236 | 0.352 | −0.262 |
| `2i6d` | 296 | −0.0287 | 0.354 | −0.299 |
| `4i4d` | 296 | −0.0291 | 0.354 | −0.288 |
| `6i2d` | 296 | −0.0295 | 0.352 | −0.308 |
| `8i0d` | 295 | −0.0293 | 0.500 | −0.014 |

평균 dIPC도 policy 전체에서 −0.024~−0.030으로 거의 일정하다 — L1I/L1D 갭과 같은 방향·같은 크기로 나타나는 것으로 보아, IPC 차이의 대부분도 L2C partition 방식 차이가 아니라 위에서 확인한 baseline L1 miss 갭이 하류로 전파된 결과로 해석하는 게 맞다.

예외: `8i0d`의 `tahoe_0029`(FDIP IPC 1.109 vs Split IPC 0.609, 거의 2배 차이), `delta_0002`(0.843 vs 0.396)처럼 개별 trace 단위로는 평균보다 훨씬 큰 편차가 있다.

### Trace × policy 전체 비교 (평균 없이)

1,775개 (trace × policy) 조합 전체를 평균 내지 않고 정렬/필터할 수 있는 표: [partition vs split — core 맞추기 전 (trace × policy 차이)](html_diffs/diff_pre_core_match.html)

### dIPC 부호(FDIP vs Split, 절대 비교)는 일치하지 않는다

`d_ipc = IPC_split − IPC_fdip`의 부호를 (trace, policy) 조합 1,775개 전체에서 세어보면, **81.4%(1,445개)는 음수(FDIP가 더 빠름)**, **18.5%(329개)는 양수(Split이 더 빠름)**로 한쪽으로 완전히 쏠려있지 않다. Policy별로도 78~84% 범위로 방향은 비슷하지만 부호가 항상 같지는 않다. 다만 이건 코어 폭이 다른 두 시뮬레이터를 직접 비교한 값이라, "넓은 코어 vs 좁은 코어" 신호가 섞여 있는 상태의 결과다.

### 코드베이스 내부에서 shared 대비 delta는 대체로 일치한다

코어 폭 confound를 없애려면, FDIP는 FDIP 안에서(`policy − shared`), Split은 Split 안에서(`policy − shared`) 각각 계산한 뒤 그 두 delta를 비교하면 된다. 이러면 "같은 코어 안에서 L2C policy만 바꿨을 때의 효과"끼리 비교하는 셈이라 코어 폭 차이가 상쇄된다.

| policy | 부호 일치율 | 상관계수(r) | 평균 dIPC (FDIP) | 평균 dIPC (Split) |
|---|---:|---:|---:|---:|
| `0i8d` | 95.3% | 0.712 | +0.0028 | +0.0082 |
| `2i6d` | 76.0% | 0.702 | −0.0007 | −0.0005 |
| `4i4d` | 86.8% | 0.925 | −0.0009 | −0.0011 |
| `6i2d` | 90.2% | 0.984 | −0.0024 | −0.0030 |
| `8i0d` | 90.8% | 0.588 | +0.0030 | +0.0027 |

`0i8d`/`4i4d`/`6i2d`/`8i0d`는 부호 일치율 87~95%, 상관계수도 0.6~0.98로 방향성이 상당히 잘 맞는다. `2i6d`만 부호 일치율이 76%로 낮은데, 평균 효과 자체가 −0.0007/−0.0005로 거의 0에 가까워서 — 효과 크기가 원래 작다 보니 잡음 때문에 부호가 자주 뒤집히는 것으로 보인다(진짜 방향 불일치라기보다 noise). 즉 "shared 대비 각 policy의 delta가 완전히 동일하냐"는 질문에는 **완벽히 동일하지는 않지만, 코어 폭을 통제하고 나면 대부분 policy에서 방향·크기가 상당히 일관된다**가 답이다.

## 결론

- `config_signature.txt`가 같다고 해서 config가 진짜 같은 게 아니었다 — **`ChampSim_FDIP`와 `ChampSim_Split`의 base config는 OoO 코어 폭 자체가 다르다**(fetch 8 vs 6-wide, execute 10 vs 4-wide, decode buffer 192 vs 32, register file 280 vs 128, scheduler 160 vs 128). 이번 비교에서 확인된 L1I/L1D MPKI 차이(policy 무관하게 L1I +2.7~2.85, L1D +3.29~3.37)와 IPC 차이의 실질적 원인은 partition vs split L2C 아키텍처가 아니라 **이 코어 폭 불일치**로 결론 내린다.
- prefetcher/latency/replacement/trace/instruction 수는 이미 정합을 맞춰뒀으므로, 코어 폭(`fetch_width`/`decode_width`/`decode_buffer_size`/`dispatch_width`/`execute_width`/`execute_latency`/`register_file_size`/`scheduler_size`)까지 두 config에서 맞춘 뒤 재실행해야 partition vs split을 진짜로 동등 비교할 수 있다.
- L2C 관련 지표(dIPC, dL2C MPKI)가 policy 전반에서 거의 균일하게 나타나는 것 자체는 partition/split 방식 차이가 없다는 정황 증거이지만, 코어 폭 gap이 섞여 있는 지금 데이터로는 확정할 수 없다.
- 코드베이스 내부에서 `policy − shared`로 코어 폭 confound를 통제하고 비교하면, `0i8d`/`4i4d`/`6i2d`/`8i0d`는 부호 일치율 87~95%·상관계수 0.6~0.98로 방향성이 상당히 일치한다(`2i6d`만 76%로 낮지만 효과 크기 자체가 거의 0이라 noise로 보임). 절대 dIPC 부호는 81.4%만 일치(FDIP가 대체로 더 빠름)하는 것과 대조적 — **partition vs split의 상대적 효과(어떤 policy가 shared 대비 이득/손해인지)는 코어 폭을 맞추지 않고도 이미 상당히 일관되게 나타난다.**

---

## 재검증: 코어 폭을 맞춘 뒤 재비교

`ChampSim_FDIP`의 `champsim_config.json` `ooo_cpu`를 `ChampSim_Split`과 완전히 동일하게 맞춘 뒤 다시 비교했다.

| 항목 | 변경 전(FDIP) | 변경 후(Split과 동일) |
|---|---:|---:|
| `fetch_width` | 8 | 6 |
| `decode_width` | 4 | 6 |
| `decode_buffer_size` | 192 | 32 |
| `dispatch_width` | 5 | 6 |
| `execute_width` | 10 | 4 |
| `execute_latency` | 1 | 0 |
| `register_file_size` | 280 | 128 |
| `scheduler_size` | 160 | 128 |

### 실행 조건

빠르게 확인하기 위해 trace는 g2(`delta`+`sierra.a.6`, 22개)만 사용했다. 비교 기준은 같은 조건으로 이미 실행된 `260721_2005_w10_i100_champ_split_2g`(Split).

```bash
./scripts/run.sh -b -L2C 0x7f
./scripts/run.sh -t -T trace_gtrace_l2c_test_g2.txt -L2C 0x7b -w 1000000 -i 10000000 -p 30 -r 260722_1943_w10_i100_fdip_partition_comp_champ_split_core_matched_2g
```

132/132 성공(실패 0). Summary 생성 후 `260721_2005_w10_i100_champ_split_2g`와 6개 policy 전부 비교했다.

### 결과: L1I는 거의 완전히 맞았지만 L1D는 오히려 더 벌어졌다

| policy | 평균 dIPC | 평균 dL1I MPKI | 평균 dL1D MPKI | 평균 dBranch MPKI | 평균 dL2C MPKI |
|---|---:|---:|---:|---:|---:|
| `shared` | −0.0187 | +0.025 | +6.529 | ≈0 | −1.539 |
| `0i8d` | −0.0083 | −0.277 | +6.587 | ≈0 | −0.078 |
| `2i6d` | −0.0186 | +0.091 | +6.524 | ≈0 | −0.160 |
| `4i4d` | −0.0190 | +0.086 | +6.545 | ≈0 | −0.542 |
| `6i2d` | −0.0197 | +0.098 | +6.596 | ≈0 | −0.498 |
| `8i0d` | −0.0149 | +0.122 | +6.475 | ≈0 | −0.325 |

- **L1I MPKI 차이가 (+2.7~2.85) → (−0.28~+0.12)로 거의 사라졌다.** 코어 폭이 fetch/decode 단계 miss 패턴의 실질적 원인이었다는 뜻이다.
- **branch MPKI는 여전히 정확히 일치**한다(코어 폭과 무관하게 원래도 일치했음).
- **IPC 차이는 줄었다**(−0.024~−0.030 → −0.008~−0.020) — L1I gap이 줄어든 만큼 개선.
- **그런데 L1D MPKI 차이는 오히려 커졌다**(+3.3 → +6.5 평균). 예시로 `shared`/`delta_0000.champsim.gz`는 L1D MPKI가 32.29(FDIP) vs 53.43(Split)로 65% 차이가 난다. L1D의 config(latency/prefetcher/queue size)는 전부 동일하고, `next_line` prefetcher 모듈 코드도 두 fork에서 바이트 단위로 동일해서, L1D 자체 설정 문제는 아니다.

### 새로 찾은 confound: DRAM 타이밍이 약 2배 다르다

`physical_memory`를 비교하면 다음이 다르다.

| | FDIP | Split |
|---|---:|---:|
| `tCAS` | 12.5 | 24 |
| `tRCD` | 12.5 | 24 |
| `tRP` | 12.5 | 24 |
| `tRAS` | 25 | 52 |

메모리 접근 latency가 다르면 파이프라인 stall/backpressure 타이밍이 달라지고, OoO 투기 실행 경로가 바뀌면서 L1D miss *count* 자체에도 영향을 줄 수 있다(load/store가 DRAM 지연에 가장 민감하다) — L1D만 유독 크게 벌어진 것과 방향이 맞는다.

### Trace × policy 전체 비교 (평균 없이, 코어 맞춘 후)

132개 (trace × policy, g2 22개 trace) 조합 전체: [partition vs split — core 맞춘 후 (trace × policy 차이)](html_diffs/diff_post_core_match.html)

---

## 재검증 2: DRAM 타이밍까지 맞춘 뒤 재비교

L1D gap이 DRAM 접근 latency 차이(backpressure/타이밍 경로를 통해 miss count에 간접 영향) 때문일 수 있다는 가설을 확인하기 위해, `ChampSim_FDIP`의 `physical_memory`도 `ChampSim_Split`과 동일하게 맞췄다.

| 항목 | 변경 전(FDIP) | 변경 후(Split과 동일) |
|---|---:|---:|
| `tCAS` | 12.5 | 24 |
| `tRCD` | 12.5 | 24 |
| `tRP` | 12.5 | 24 |
| `tRAS` | 25 | 52 |

### 실행 조건

같은 g2 trace, 같은 조건으로 재실행했다.

```bash
./scripts/run.sh -b -L2C 0x7f
./scripts/run.sh -t -T trace_gtrace_l2c_test_g2.txt -L2C 0x7b -w 1000000 -i 10000000 -p 30 -r 260722_2252_w10_i100_fdip_partition_comp_champ_split_dram_matched_2g
```

132/132 성공(실패 0). 결과 파일: `outputs/verify/260722_2252_w10_i100_fdip_partition_comp_champ_split_dram_matched_2g/`(raw log, summary/metrics.csv, l2c_delta_*). 비교 기준은 동일하게 `260721_2005_w10_i100_champ_split_2g`(Split).

### 결과: 가설 기각 — L1D gap은 거의 그대로다

| policy | 평균 dIPC | 평균 dL1I MPKI | 평균 dL1D MPKI | 평균 dBranch MPKI | 평균 dL2C MPKI | 평균 dLLC MPKI |
|---|---:|---:|---:|---:|---:|---:|
| `shared` | +0.0986 | +0.025 | +6.323 | ≈0 | −1.575 | −0.281 |
| `0i8d` | +0.1104 | −0.278 | +6.361 | ≈0 | −0.107 | −0.281 |
| `2i6d` | +0.0976 | +0.083 | +6.294 | ≈0 | −0.206 | −0.290 |
| `4i4d` | +0.0977 | +0.093 | +6.320 | ≈0 | −0.435 | −0.298 |
| `6i2d` | +0.0974 | +0.093 | +6.399 | ≈0 | −0.638 | −0.278 |
| `8i0d` | +0.1026 | +0.121 | +6.376 | ≈0 | −0.340 | −0.257 |

- **L1D gap은 +6.5 → +6.3~6.4로 사실상 그대로다.** DRAM 타이밍은 L1D miss count의 원인이 아니었다 — 가설 기각.
- **IPC 부호는 뒤집혔다**(−0.008~−0.020 → +0.098~+0.110, 이번엔 Split이 더 빠름). FDIP의 DRAM을 Split만큼 느리게 맞췄으니 FDIP가 그만큼 느려진 것 — DRAM 타이밍이 IPC에는 직접 영향을 준다는 걸 확인했지만, L1D miss count와는 무관하다는 뜻이다.
- L1I/branch MPKI는 이전과 동일하게 거의 일치 상태를 유지한다.

### Trace × policy 전체 비교 (평균 없이, DRAM 맞춘 후)

132개 조합 전체: [partition vs split — DRAM 타이밍까지 맞춘 후 (trace × policy 차이)](html_diffs/diff_dram_match.html)

### 다음 단계

L1D config(latency/prefetcher/queue size)·core 폭·DRAM 타이밍을 전부 맞췄는데도 L1D MPKI만 유독 안 맞는다. Config 비교로는 더 찾을 게 없어 보이므로, 다음은 코드 레벨이다 — `ooo_cpu.cc`의 load queue/store queue 처리, `cache.cc`의 MSHR merge 로직, 또는 `ChampSim_FDIP`의 `is_instr_fetch` 계측이 data-origin 요청 처리 경로에 미치는 영향을 직접 diff해서 찾아야 한다.

---

## 경향성(shared 대비 policy 효과) 재확인 — core+DRAM 맞춘 뒤

절대값이 아니라 "같은 코드베이스 안에서 `policy − shared`"로 코어/DRAM 차이를 통제한 뒤, 5개 지표 전부에서 FDIP와 Split의 상대 효과가 같은 방향으로 움직이는지 확인했다.

| 지표 | 부호 일치율 범위 | 상관계수(r) 범위 | 비고 |
|---|---|---|---|
| IPC | 86.4~100% | 0.91~0.997 | core/DRAM 매칭 전보다 크게 개선 |
| L2C MPKI | 95.5~100% | 0.72~0.999 | 매우 잘 맞음, 크기도 근접(`0i8d`: −20.95 vs −19.49) |
| L1I MPKI | 95.5~100% | 0.63~0.99 | 매우 잘 맞음 |
| LLC MPKI | 90.9~100% | 0.61~0.99 | 잘 맞음 |
| L1D MPKI | 72.7~100% | 0.08~0.96 | 가장 약함 — `6i2d`는 상관계수 0.08 |

`L1D`의 `6i2d`가 유독 낮은 이유는 효과 크기 자체가 둘 다 거의 0이기 때문(FDIP +0.138, Split +0.214 — 절대적으로 작은 값끼리라 잡음에 취약)이다. `8i0d`는 반대로 효과가 크고(FDIP +1.17, Split +1.23) 상관계수도 0.961로 아주 잘 맞는다.

**결론**: "shared 대비 policy 효과의 방향"이라는 의미의 경향성은 IPC/L2C/L1I/LLC에서 거의 대부분 강하게 일치한다(부호 일치율 90%+, r 0.9대가 흔함). L1D만 효과가 작은 정책에서 노이즈 때문에 약하게 나타난다. 절대값 수준의 baseline L1D +6.3 offset은 여전히 안 맞지만, "정책을 바꿨을 때 어느 방향으로 얼마나 움직이는가"라는 경향성 자체는 partition과 split이 상당히 일관되게 보여준다.

---

## 코드 레벨 원인 분석: 왜 L1D만 다른가

Config(latency/prefetcher/core 폭/DRAM 타이밍)를 전부 맞췄는데도 L1D MPKI만 policy와 무관하게 +6.3 정도 남는 이유를 찾기 위해, `ChampSim_FDIP`와 `ChampSim_Split`의 `ooo_cpu.cc`/`ptw.cc`/`cache.cc`를 직접 diff했다.

### 시도했지만 기각된 가설: PTW MSHR pressure bound

`ptw.cc`를 diff하면 `ChampSim_FDIP`에만 있는 코드가 두 개 보인다.

- `f6602de`(Bound PTW MSHR pressure): `PageTableWalker::operate()`에서 `active_mshrs >= MSHR_SIZE`면 새 PTW 요청을 거부하는 gate. `ChampSim_Split`에는 이 gate가 없어서 PTW MSHR이 설정된 크기(5) 이상으로 무제한 쌓일 수 있다.
- `df0f567`(Fix PTW MSHR completion move): MSHR 완료 처리를 `std::partition`/`std::partition_copy`에서 scan-and-move loop로 변경. `ChampSim_Split`은 여전히 예전 `std::partition`/`std::partition_copy` 방식이다.

두 커밋 다 `std::bad_alloc` 크래시를 막기 위한 FDIP 전용 버그 수정이라 L1D 쪽 `TRANSLATION HIT`(FDIP 4024 vs Split 39848, `delta_0000`/`shared` 기준) 차이의 원인일 가능성이 있어 직접 검증했다.

**검증 방법**: `ChampSim_FDIP/src/ptw.cc`의 MSHR bound gate를 임시로 제거하고 `champsim_l2cshared`만 재빌드, 같은 trace(`delta_0000`, `shared`)를 다시 돌려서 비교했다.

| | bound 있음(원래 FDIP) | bound 제거(임시) |
|---|---:|---:|
| TRANSLATION ACCESS | 73,831 | 73,836 |
| TRANSLATION HIT | 4,024 | 4,022 |
| LOAD ACCESS | 1,781,979 | 1,782,488 |

**거의 변화 없음 — 가설 기각.** 검증 후 `git checkout -- src/ptw.cc`로 즉시 원복했다(이 gate는 실제 크래시를 막는 버그 수정이라 제거된 채로 두면 안 된다).

### 확정 원인: store-to-load forwarding 구현 여부

`ooo_cpu.cc`에서 함수 목록 자체는 `predict_future_blocks`/`process_ftq`(FDIP의 FTQ 전용 함수) 말고는 거의 동일하다. 그런데 LSQ 관련 함수 내부 로직을 direct diff하면 결정적인 차이가 나온다.

**`ChampSim_FDIP`는 store-to-load forwarding을 구현한다:**

- `inc/ooo_cpu.h:99` — `LSQ_ENTRY`에 `bool forwarded = false;` 필드가 있다.
- `src/ooo_cpu.cc:643`(`do_memory_scheduling`) — load를 스케줄할 때 SQ(store queue)에서 같은 가상주소를 쓰는 직전 store를 찾는다. 찾으면 `forwarded = true`로 표시하고, 그 store가 이미 실행됐으면 즉시 `finish()`, 아직이면 `lq_depend_on_me`에 등록해서 store가 끝날 때 같이 끝나게 한다(`src/ooo_cpu.cc:726` `do_finish_store`가 `lq_depend_on_me`의 load들을 직접 `finish()`한다).
- `src/ooo_cpu.cc:760-762`(`execute_load`) — `if (lq_entry.forwarded) return false;`로, forwarding된 load는 **L1D에 아예 요청을 보내지 않는다.**

**`ChampSim_Split`은 이 메커니즘이 통째로 없다:**

- `LSQ_ENTRY`에 `forwarded` 필드 자체가 없다(`inc/ooo_cpu.h:66-80`).
- `do_memory_scheduling`이 SQ를 스캔해서 forwarding 가능한 store를 찾는 코드가 없다 — load는 무조건 LQ에 들어가서 나중에 `execute_load`가 무조건 L1D에 read를 issue한다(`if (lq_entry.forwarded)` 체크 자체가 없음).

**즉 `ChampSim_Split`에서는 store가 이미 같은 주소에 쓴 값을 읽는 load조차 매번 L1D 캐시를 실제로 찾아간다.** `ChampSim_FDIP`는 이런 load를 캐시 근처에도 안 보내고 store에서 직접 값을 받는다. 이게 L1D `ACCESS`/`MISS` 카운트 자체의 절대적인 차이를 만든다(`delta_0000`/`shared` 기준 LOAD ACCESS: FDIP 1,781,979 vs Split 2,573,310, +44%). 이 차이는:

- **L1D에만 영향**: forwarding은 load/store 사이의 데이터 경로 문제라 instruction fetch(L1I)·분기예측·L2C/LLC 자체 구조와 무관하다 — L1I/branch MPKI가 계속 정확히 일치했던 것과 정확히 들어맞는다.
- **policy와 무관하게 균일**: forwarding 여부는 L2C partition 방식이 아니라 O3_CPU/LSQ 레벨에서 결정되므로, `shared`/`0i8d`/`2i6d`/`4i4d`/`6i2d`/`8i0d` 전부에서 똑같은 크기로 나타난다 — 실제로 관측된 L1D gap이 정확히 그랬다.
- **core 폭·DRAM 타이밍을 맞춰도 안 사라짐**: forwarding 유무는 애초에 이런 파라미터와 무관한 별개의 코드 경로이기 때문이다.
- L1D 트래픽이 늘어나면 L2C/LLC로 내려가는 트래픽과 타이밍도 같이 바뀌므로, 남아있던 작은 L2C/LLC/`TRANSLATION` hit-rate 차이도 이 L1D 트래픽 증가의 하류 효과로 설명된다.

### 결론

partition(FDIP)과 split(Split)의 L2C 처리 방식 차이가 아니라, **두 코드베이스가 store-to-load forwarding을 구현했는지 여부가 다른 것**이 지금 남은 L1D 차이의 실질적 원인이다. 이건 config로 맞출 수 있는 파라미터가 아니라 `ooo_cpu.cc`/`ooo_cpu.h`의 LSQ 스케줄링 로직 자체의 차이이므로, 완전히 없애려면 `ChampSim_Split`에 forwarding 로직을 이식하거나(코드 변경), 또는 앞으로의 partition vs split 비교에서 L1D MPKI는 "두 코드베이스 사이에 항상 존재하는 baseline 차이"로 감안하고 L2C/L1I/IPC의 상대적 경향(위 "경향성 재확인" 절)에 더 무게를 두는 방식으로 해석해야 한다.
