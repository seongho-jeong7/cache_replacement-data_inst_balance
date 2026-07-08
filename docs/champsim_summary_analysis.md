# ChampSim Summary(metrics.csv) 분석 가이드

`scripts/run.sh -s <mask>`가 만들어내는 요약 결과(`metrics.csv`, 표 형태 출력)를 어떻게 읽는지 정리한다. 원본 로그 한 줄 한 줄(`cpu0->LLC LOAD ACCESS: ...` 같은)의 의미는 [`docs/champsim_log_analysis.md`](champsim_log_analysis.md)에 정리했고, 이 문서는 그걸 `parser/parse_outputs.py`가 trace당 한 줄로 집계한 `metrics.csv`, 그리고 `parser/summary.py`가 trace_set/trace_group별로 평균낸 표를 다룬다.

## MPKI란

**Misses Per Kilo-Instruction** — 명령어 1000개를 실행하는 동안 miss가 몇 번 났는지. 값이 낮을수록 그 레벨의 캐시가 일을 잘하고 있다는 뜻이다.

## 각 MPKI의 계산식

- **`branch_mpki`**: 우리가 계산하는 게 아니라, champsim이 로그에 직접 찍어주는 branch predictor 통계 줄을 그대로 파싱한 값이다.
- **`l1i_mpki`** (이번에 새로 추가): `L1I LOAD miss / instructions × 1000`. L1I는 RFO를 절대 안 쓰므로(WRITE 자체를 안 함) 사실상 LOAD miss만 센다. **이건 표준 ACCESS/HIT/MISS 표의 L1I LOAD 행에서 온 값이지, 아래에서 설명할 FDIP breakdown의 "L1I Miss"와는 계산식이 다르다** — 헷갈리기 쉬운 부분이라 주의.
- **`l1d_mpki` / `l2c_mpki` / `llc_mpki`**: `(LOAD miss + RFO miss) / instructions × 1000`. PREFETCH/WRITE/TRANSLATION miss는 일부러 제외한다 — 코어가 직접 요청한 demand 트래픽(load/store)만 반영하는, 문헌에서 흔히 쓰는 "demand MPKI" 방식이다.
- **`stlb_mpki`**: `STLB TOTAL miss / instructions × 1000`. STLB는 LOAD 타입만 쓰므로 TOTAL이나 LOAD나 사실상 같다.
- **`l2i_mpki` / `l2d_mpki`, `lli_mpki` / `lld_mpki`** (이번에 새로 추가): L2C/LLC 접근을 요청 출처(L1I 기원 vs L1D 기원)로 나눈 demand MPKI. `ChampSim_FDIP`의 `is_instr_fetch` 계측(로그의 `LOAD_I`/`RFO_I`/`LOAD_D`/`RFO_D` 줄)이 있어야 계산되고, 계산식은 `l2c_mpki`/`llc_mpki`와 동일한 방식(LOAD+RFO miss만, PREFETCH/WRITE/TRANSLATION 제외)을 origin별로 나눈 것이다 — 즉 `l2i_mpki + l2d_mpki == l2c_mpki`, `lli_mpki + lld_mpki == llc_mpki`가 항상 성립한다. **이 계측이 없는(옛날 바이너리로 만든) 로그에서는 빈 값(`-`)으로 표시된다** — `l2c_mpki`/`llc_mpki`는 항상 계산되지만 `l2i_mpki`/`l2d_mpki`/`lli_mpki`/`lld_mpki`는 로그에 해당 줄이 있을 때만 채워진다.
- **`on_chip_traffic_mpki` / `off_chip_traffic_mpki`**: `LLC TOTAL access(또는 miss) / instructions × 1000`. 위의 `l2c_mpki`/`llc_mpki`와 달리 **모든 access_type(LOAD/RFO/PREFETCH/WRITE/TRANSLATION)을 다 포함**한다 — "LLC까지 도달한 트래픽 총량" / "메모리까지 나간 트래픽 총량"을 보는 지표라 스코프가 다르다. `-s 0x10`(FDIP table)의 `OnChip MPKI`/`OffChip MPKI` 컬럼으로 노출된다.

## FDIP Cov / L1I Miss (FDIP breakdown 기반)

로그의 `==== L1I Demand Access Breakdown ====` 섹션에 있는 5개 값을 전부 더한 것(`fdip_total`)을 분모로 비율을 낸다.

```
fdip_total = fdip_l1i_hit_covered + fdip_l1i_hit_non_prefetch
           + fdip_l1i_late_prefetch_merge + fdip_l1i_merge_non_prefetch
           + fdip_l1i_miss

FDIP Cov  = fdip_l1i_hit_covered / fdip_total × 100
L1I Miss  = fdip_l1i_miss        / fdip_total × 100
```

- **FDIP Cov**: L1I demand fetch 중, FDIP가 미리 prefetch해서 깔아둔 라인에 맞아떨어진 비율.
- **L1I Miss**: L1I demand fetch 중, 어떤 prefetch의 도움도 못 받고 완전히 새로 MSHR을 할당해야 했던 비율(`cache.cc`의 `handle_miss()`에서 `NAME=="cpu0_L1I"`일 때만 세는 커스텀 카운터).

**주의**: 이 "L1I Miss"(%)는 위쪽 `l1i_mpki`(1000 명령어당 miss 횟수)와 분자·분모가 둘 다 다른 완전히 별개의 지표다. `l1i_mpki`는 "명령어 실행량 대비 miss 빈도", FDIP의 "L1I Miss"는 "L1I 요청 중 FDIP 도움을 전혀 못 받은 비율"이라, 서로 대체하는 지표가 아니라 같이 봐야 의미가 있다.

## `-s` 비트마스크로 나오는 표들

`scripts/run.sh -s <mask>`는 `mask`의 각 비트에 따라 서로 다른 표를 만든다. 여러 비트를 동시에 켜면 표가 여러 개 순서대로 출력된다. 10진수, `0x` 붙인 16진수 둘 다 된다(`-s 16`과 `-s 0x10`은 동일).

| 비트 | 값 | 표 내용 |
|---|---|---|
| 1 | `0x1` | 기본 summary table: Trace Set/Group/Total/OK/Fail/Avg IPC/Br MPKI/L1I MPKI/L1D MPKI/L2C MPKI/LLC MPKI/STLB MPKI |
| 2 | `0x2` | FDIP cover 그래프 생성 (표 아님, `parser/fdip/cover/fdip_cover.py`) |
| 4 | `0x4` | hit map 생성 (표 아님, `parser/fdip/hit_map.py`) |
| 8 | `0x8` | 축소 table: Trace Set/Group/Total/OK/Fail/Avg IPC/L1I MPKI/L1D MPKI/L2I MPKI/L2D MPKI/LLI MPKI/LLD MPKI만 — I/D MPKI 비교에 집중할 때 |
| 16 | `0x10` | FDIP table: Trace Set/Group/Total/OK/Fail/FDIP Cov/L1I Miss/OnChip MPKI/OffChip MPKI만 — FDIP 자체 효율 + 온칩/오프칩 트래픽 부담을 같이 볼 때 |

예: `-s 0x19`(=1+8+0x10)를 주면 기본 table, 축소 table, FDIP table이 순서대로 다 출력된다.

`FDIP Cov`/`L1I Miss`/`OnChip MPKI`/`OffChip MPKI`는 더 이상 기본 summary table(`-s 1`)에 안 나온다 — 전부 `0x10` FDIP table로 옮겼다.
