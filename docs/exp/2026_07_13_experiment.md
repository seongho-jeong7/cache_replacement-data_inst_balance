# 2026-07-13 실험 노트: Frontend Stall Breakdown으로 L1I MPKI vs IPC 괴리 설명하기

이 문서는 2026-07-13에 진행한 분석과 계측 작업을 기록한다. 계속 진행하면서 내용을 이어서 추가한다.

## 출발점: L1I MPKI가 100배 줄어도 IPC는 왜 10%만 오르나

`260707_2245` run(warmup 5천만 + simulation 2억 instructions, ftq_size 2/4/16/32/64)의 `-s 0x19` 결과를 보면, `merced` 그룹 기준으로:

| ftq | L1I MPKI | L1D MPKI | Br MPKI | IPC |
|---|---|---|---|---|
| 2 | 9.50 | 16.91 | 15.14 | 0.597 |
| 4 | 6.67 | 16.94 | 15.14 | 0.630 |
| 16 | 1.95 | 16.96 | 15.14 | 0.655 |
| 32 | 0.66 | 16.95 | 15.14 | 0.658 |
| 64 | 0.09 | 16.95 | 15.14 | 0.659 |

FDIP의 FTQ size를 키울수록 L1I MPKI는 100배 넘게 줄어드는데(9.50→0.09), IPC는 겨우 10% 정도(0.597→0.659)만 개선된다. L1D MPKI(~16.9)와 Br MPKI(15.14)는 ftq와 무관하게 완전히 고정이라, 애초에 L1I보다 L1D/branch 쪽 부담이 더 컸을 가능성, 그리고 MPKI(발생한 miss 횟수)와 실제 파이프라인 stall 사이클이 1:1로 대응하지 않을 가능성 두 가지를 의심했다.

이걸 검증하려면 "L1I miss 때문에 파이프라인이 실제로 몇 사이클을 멈췄는지"를 재는 계측이 필요했다 — MPKI만으로는 답할 수 없는 질문이었다.

## Frontend Stall Breakdown 계측 추가

`ChampSim_FDIP`에는 이미 `@Minchan`이 만들어둔 **Backend Stall Breakdown**(`inc/core_stats.h`의 `StallType`, `src/ooo_cpu.cc`의 `dispatch_instruction()`)이 있었다 — ROB full / LQ full / SQ full 때문에 dispatch가 못 넘어가는 사이클을 집계하는 프레임워크다. 여기에 짝을 이루는 **Frontend Stall Breakdown**(fetch→decode 승격이 막히는 사이클)이 없다는 걸 확인하고, 같은 스타일로 추가했다.

### 계측 지점: `O3_CPU::promote_to_decode()`

이 함수는 매 사이클 호출되며, `IFETCH_BUFFER` 맨 앞 명령어가 `fetch_completed`가 아니면 이번 사이클은 진행이 0이다. 이 지점에서 사이클을 3가지로 분류한다(우선순위 순):

1. **`NoInstrToFetch`**: `IFETCH_BUFFER`가 비어있음 — 애초에 fetch할 게 없는 상태(FTQ/분기예측 등 상류 문제, L1I와 무관)
2. **`L1IMiss`**: `IFETCH_BUFFER` 맨 앞이 `fetch_completed==false` — L1I miss/진행 중이라 못 넘어가는 사이클(우리가 찾던 지표)
3. **`BackendFull`**: `DIB_HIT_BUFFER`/`DECODE_BUFFER`가 꽉 차서 못 넘어감 — L1I와 무관한 후단(decode) 정체

### 변경 파일

- `ChampSim_FDIP/inc/core_stats.h`: `FrontendStallType` enum + `cpu_stats::frontend_stall_cycles[]` 배열
- `ChampSim_FDIP/inc/instruction.h`: `frontend_stall_type_names` 라벨 배열
- `ChampSim_FDIP/src/ooo_cpu.cc`: `promote_to_decode()` 맨 앞에 분류 로직
- `ChampSim_FDIP/src/plain_printer.cc`: `====Frontend Stall Breakdown====` 섹션 출력 (기존 `====Backend Stall Breakdown====` 바로 아래)
- `ChampSim_FDIP/src/core_stats.cc`: `operator-`에 새 필드 diff 추가 (일관성 유지용, 기존처럼 미사용 함수)

`O3_CPU::end_phase()`는 `roi_stats = sim_stats;`로 통째로 복사하는 구조라 별도 수정이 필요 없었다.

### 파서/요약 지원

- `parser/parse_outputs.py`: `====Frontend Stall Breakdown====` 섹션 파싱, `frontend_stall_{l1i_miss,no_instr_to_fetch,backend_full}`(raw count) + `_pct`(전체 ROI 사이클 대비 비율) 필드를 `metrics.csv`에 추가.
- `parser/summary.py`: `--frontend` 모드 추가 — Avg IPC / L1I MPKI / L2I MPKI / L2D MPKI / L1I Stall% / NoFetch% / BackendFull%.
- `scripts/run.sh`: `-s 0x20` 비트로 frontend stall summary table 노출.

### 검증

`frontend_stall_test` run(343 trace × ftq 2/4/16/32/64, warmup 100000 + simulation 500000, `-p 50`)으로 전체 검증. 343/343 성공 × 5 ftq, 실패 0개.

## 핵심 발견: BackendFull%와 IPC 개선폭의 상관관계

`arizona_0000` 하나로 먼저 확인한 결과, L1I_MISS stall cycle 자체는 ftq 2→64 사이에 크게 줄지 않고(6479→5556, -14%), 대부분의 stall이 `NoInstrToFetch`(애초에 fetch할 게 없음)에서 나왔다. 343개 trace 전체·12개 trace group에 대해 이 패턴을 group별로 집계했다.

### BackendFull%(ftq=2) 오름차순 정렬, ftq별 BackendFull%와 IPC gain(ftq=2 대비)

| Group | BF%@2 | BF%@4 | BF%@16 | BF%@32 | BF%@64 | Gain@4 | Gain@16 | Gain@32 | Gain@64 |
|---|---|---|---|---|---|---|---|---|---|
| yankee | 2.59 | 2.75 | 2.90 | 2.95 | 2.97 | 4.7% | 8.9% | 9.8% | 10.5% |
| tango | 3.64 | 3.79 | 3.93 | 3.99 | 4.02 | 6.2% | 12.4% | 14.0% | 15.0% |
| bravo | 3.69 | 3.86 | 4.09 | 4.12 | 4.20 | 3.7% | 7.8% | 8.1% | 9.5% |
| merced | 4.04 | 4.20 | 4.35 | 4.40 | 4.43 | 3.9% | 7.4% | 8.1% | 8.6% |
| sierra.a.6 | 4.20 | 4.27 | 4.40 | 4.43 | 4.46 | 4.8% | 10.0% | 11.0% | 11.2% |
| sierra.a.4 | 4.97 | 5.14 | 5.33 | 5.39 | 5.45 | 8.3% | 17.4% | 19.8% | **21.5%** |
| charlie | 5.60 | 5.80 | 6.01 | 6.04 | 6.10 | 4.5% | 8.5% | 9.4% | 10.2% |
| sierra.a.3 | 7.33 | 7.53 | 7.74 | 7.78 | 7.81 | 3.4% | 7.6% | 8.7% | 9.3% |
| tahoe | 7.69 | 7.96 | 8.26 | 8.35 | 8.43 | 4.2% | 8.3% | 9.4% | 10.1% |
| arizona | 13.92 | 14.27 | 14.44 | 14.58 | 14.58 | 0.8% | 1.9% | 2.1% | 2.3% |
| whiskey | 15.60 | 16.00 | 16.38 | 16.59 | 16.65 | 2.0% | 3.7% | 4.5% | 4.7% |
| delta | 19.51 | 19.56 | 19.93 | 19.80 | 19.97 | 0.9% | 1.5% | 1.8% | **1.7%** |

BackendFull%가 낮은 위쪽 9개 그룹(BF% 2.6~8.4)은 ftq=64에서 IPC gain이 최소 8.6%~최대 21.5%로 뚜렷하게 개선되는 반면, BackendFull%가 높은 아래쪽 3개(arizona/whiskey/delta, BF% 14~20)는 2.3% 이하로 뭉쳐 있다. 표에서 경계가 육안으로 보인다.

### 상관계수 (BackendFull%@ftq=2 vs IPC gain@해당 ftq)

| 대상 ftq | Gain@4 | Gain@16 | Gain@32 | Gain@64 |
|---|---|---|---|---|
| Pearson r | -0.765 | -0.757 | -0.728 | -0.733 |

ftq=4처럼 FDIP 효과가 아직 작을 때부터 이미 r≈-0.77이고, ftq=64까지 가도 r≈-0.73 언저리에서 크게 안 흔들린다 — 특정 ftq 값에서 우연히 나온 상관관계가 아니라 **ftq를 얼마나 키우든 일관되게 유지되는 패턴**이다.

**참고**: `BackendFull%`와 IPC를 "증가율"이 아니라 "절대값"으로 비교하면 오히려 양의 상관(r≈+0.5, ftq=2 기준)이 나온다. 이건 arizona/delta처럼 원래 IPC 자체가 높은 워크로드가 backend 포화도도 같이 높기 때문에 생기는 착시다(단순/짧은 의존성 사슬을 가진 workload일수록 IPC도 높고 ROB도 빨리 참). 그 워크로드 "자체의 개선 여지"를 보려면 절대 IPC가 아니라 gain%로 봐야 위 상관관계가 의미를 가진다.

## 해석

- **delta/arizona/whiskey** (BackendFull% 14~20%): FDIP로 L1I 문제를 없애도 IPC가 거의 안 오른다(1.7~4.7%). 이 trace들은 애초에 **backend(ROB/decode buffer)가 병목**이라, L1I를 고쳐도 다음 병목이 바로 그 자리를 채운다.
- **sierra.a.4/tango/sierra.a.6** (BackendFull% 3~5%, L1I stall%은 애초에 높았던 그룹): FDIP 효과가 가장 크다(11~21.5%). 이 trace들은 backend 여유가 있어서, L1I 병목을 없애면 그 이득이 실제로 IPC로 전환된다.

즉 **"FDIP가 얼마나 도움이 되는가"는 L1I MPKI 자체보다, 그 trace의 backend(ROB) 여유도(`BackendFull%`)로 훨씬 잘 예측된다.**

L2C/LLC 공유 간섭 연구 관점에서 보면: backend가 이미 포화된 workload(delta/arizona/whiskey류)에서는 L1I/L1D 캐시 자원 배분을 아무리 손봐도 IPC 개선 여지가 작다는 뜻이다. 이런 trace는 "간섭 완화 효과가 안 보이는 workload"로 따로 분류해서 볼 필요가 있다 — 앞으로 L2C/LLC 자원 배분 실험을 설계할 때, `BackendFull%`가 높은 workload와 낮은 workload를 나눠서 비교해야 진짜 효과를 놓치지 않을 것으로 보인다.

## 부수 작업 (오늘 진행한 하우스키핑)

- `260707_2245` run에서 트레이스 오류로 실패했던 21개(sierra.a.4 segfault 5개 + tahoe/tango SIGTERM 16개)를 트레이스 파일 수정 후 재실행 → 전부 성공, ftq=2가 343/343 완주.
- `scripts/run.sh`의 `CHAMPSIM_DIR` 존재 체크를 `-s`(summary-only) 모드에서는 건너뛰도록 수정 — summary만 뽑을 때는 ChampSim 바이너리가 없어도 동작해야 하는데 기존엔 무조건 체크했음.
- `ChampSim_FDIP_new`(디스포저블 빌드 복사본) 삭제, `scripts/run.sh`의 `CHAMPSIM_DIR`를 다시 `ChampSim_FDIP`로 직접 지정.
- `-s`의 `OnChip MPKI`/`OffChip MPKI`를 FDIP table(`-s 0x10`)에 추가.

## 추가 논의: 상관계수(r≈-0.73)의 의미, 그리고 BackendFull%로 3그룹 나눠서 다시 보기

앞서 계산한 전체 상관계수(r≈-0.73~-0.77)는 12개 trace group을 통째로 하나의 산점도로 본 것이다. 이게 "ftq를 얼마나 밀어붙이든 유지되는" 이유는, `Gain@4`/`Gain@16`/`Gain@32`/`Gain@64` 각각을 Y축으로 따로 두고 X축(`BackendFull%@ftq=2`, 워크로드마다 고정된 값)과의 상관계수를 **독립적으로 재계산**했기 때문이다 — 만약 ftq를 조금 올렸을 때만 상관관계가 보이고 많이 올리면 사라진다면 "우연한 관측"으로 의심해야 하는데, 4개 지점 모두 -0.73 근방에서 크게 안 흔들리는 걸 확인했다(자세한 설명은 위 섹션 참고).

다음 질문: 이 전체 상관관계가 "모든 구간에서 고르게" 성립하는지, 아니면 특정 구간(예: BackendFull%가 아주 높은 워크로드들 사이)에서만 강하게 나타나고 나머지 구간에서는 약한지 궁금해서, `BackendFull%@ftq=2` 기준으로 12개 trace group을 4개씩 3그룹(LOW/MID/HIGH)으로 나눠 그룹 내에서 상관계수를 다시 계산했다.

### 그룹 분할 (BackendFull%@ftq=2 오름차순, 4개씩)

| 그룹 | trace groups | BF%@2 범위 |
|---|---|---|
| LOW | yankee, tango, bravo, merced | 2.59 ~ 4.04 |
| MID | sierra.a.6, sierra.a.4, charlie, sierra.a.3 | 4.20 ~ 7.33 |
| HIGH | tahoe, arizona, whiskey, delta | 7.69 ~ 19.51 |

### 그룹별 Pearson r (BackendFull%@ftq=2 vs IPC gain@해당 ftq)

| 그룹 | Gain@4 | Gain@16 | Gain@32 | Gain@64 |
|---|---|---|---|---|
| LOW | -0.185 | -0.122 | -0.126 | -0.098 |
| MID | -0.520 | -0.485 | -0.445 | -0.410 |
| HIGH | -0.846 | -0.891 | -0.880 | **-0.896** |

### 그룹별 상세 (ftq=64 기준 gain%)

- **LOW** (BF% 2.6~4.0): yankee 10.5%, tango **15.0%**, bravo 9.5%, merced 8.6% — gain이 전부 8~15% 사이로 고르게 높고, BF%와의 상관은 약하다(r≈-0.10). 이 구간에서는 backend 여유가 다들 충분해서 BackendFull% 자체는 gain을 잘 설명하지 못하고, 다른 요인(tango가 유독 좋은 이유 등)이 더 크게 작용하는 것으로 보인다.
- **MID** (BF% 4.2~7.3): sierra.a.6 11.2%, **sierra.a.4 21.5%**, charlie 10.2%, sierra.a.3 9.3% — sierra.a.4가 이 구간 안에서도 압도적으로 높은 이상치라 상관관계가 중간 정도(r≈-0.41~-0.52)로 나온다. sierra.a.4는 BF%는 그룹 내에서 중간 수준이지만 애초에 L1I stall%가 전체 12개 그룹 중 가장 높았던 workload라(29.17%@ftq=2), backend 여유 + 원래 L1I 부담이 컸다는 두 조건이 겹쳐서 gain이 특히 큰 것으로 보인다.
- **HIGH** (BF% 7.7~19.5): tahoe 10.1%, arizona 2.3%, whiskey 4.7%, delta **1.7%** — 이 구간에서 상관관계가 가장 강하다(r≈-0.85~-0.90). tahoe(BF% 8.4)는 이 그룹 안에서 BF%가 가장 낮아 gain도 가장 높고(10.1%), delta(BF% 20.0)는 BF%가 가장 높아 gain도 가장 낮다(1.7%) — 이 구간 안에서는 BackendFull%가 gain을 거의 선형적으로 설명한다.

### 해석

세 그룹으로 나눠보니 전체 상관관계(r≈-0.73)가 "모든 구간에서 고르게 성립하는 선형 관계"라기보다는, **BackendFull%가 어느 문턱(대략 8~10% 근방)을 넘어서면 그때부터 gain이 급격히, 그리고 아주 예측 가능하게(r≈-0.85~-0.90) 줄어드는 구조**에 더 가까워 보인다.

- BF% < 8 (LOW+MID 합친 구간, 8개 그룹)에서는 gain이 대체로 8% 이상으로 나쁘지 않고, BF% 자체는 gain을 잘 설명하지 못한다 — 이 구간에서는 backend가 진짜 병목이 아니라서, L1I 문제를 없애면 거의 다 이득으로 돌아간다.
- BF% > 8 (HIGH 구간, 4개 그룹)부터는 BF%가 gain을 아주 강하게(거의 선형적으로) 설명한다 — 이 구간에서는 backend가 진짜 병목이라서, L1I를 아무리 고쳐도 그 이득의 상당 부분이 backend congestion에 흡수된다.

L2C/LLC 공유 간섭 실험을 설계할 때, 단순히 "BackendFull%가 낮다/높다"로 두 그룹만 나누기보다, **BF%≈8~10%를 문턱으로 삼아 그 이하/이상으로 나누는 것**이 이 데이터에서는 더 타당해 보인다. 다만 각 그룹이 4개 trace뿐이라 표본이 매우 작다는 점은 감안해야 한다.

## 추가 논의: 진짜 Backend stall(BF)까지 같이 보기, L2I/L2D MPKI 추가

지금까지 "BF"라고 불렀던 `frontend_stall_backend_full_pct`는 사실 오늘 새로 만든 **Frontend Stall Breakdown** 안의 한 항목(DIB_HIT_BUFFER/DECODE_BUFFER가 꽉 차서 fetch→decode 승격이 막히는 비율)이다. 이건 이름과 달리 여전히 파이프라인의 **frontend(fetch~decode) 단계**에서 일어나는 정체다.

원래 `ChampSim_FDIP`에는 이거와 별개로, `@Minchan`이 예전에 만든 진짜 **Backend Stall Breakdown**(ROB/LQ/SQ가 꽉 차서 dispatch가 못 넘어가는 비율, `dispatch_instruction()`에서 계측)이 있었다 — 이 로그 섹션은 항상 찍히고 있었지만 지금까지 `parse_outputs.py`가 파싱하지 않고 있었다. 오늘부터는 용어를 이렇게 정리한다:

- **BF (진짜 Backend stall)** = `backend_stall_rob_pct` 등, `@Minchan`의 기존 Backend Stall Breakdown(ROB_STALL/LQ_STALL/SQ_STALL) — dispatch 이후 실행 자원이 꽉 찬 비율.
- **FF (Frontend stall)** = 오늘 만든 Frontend Stall Breakdown 3종(`frontend_stall_l1i_miss_pct`, `frontend_stall_no_instr_to_fetch_pct`, `frontend_stall_backend_full_pct`) — fetch→decode 승격이 막히는 비율. 이 중 `frontend_stall_backend_full_pct`는 계속 지금 이름 그대로 쓰되, 이 섹션부터는 "FF-Decode%"로 표기해서 진짜 BF와 헷갈리지 않게 한다.

이번 기회에 `parser/parse_outputs.py`에 `====Backend Stall Breakdown====` 섹션 파싱을 추가했다(`backend_stall_{rob,lq,sq}` raw + `_pct`, ROI 사이클 대비 비율). 여기에 더해 앞서 이미 계측해 둔 `l2i_mpki`/`l2d_mpki`(L2C 접근 중 instruction-fetch 기원 vs data 기원 MPKI)도 같이 놓고 봤다.

### 12개 trace group, ftq=2 시점 값 vs IPC gain(ftq=2→64)

| group | IPC gain% | BF-ROB% | FF-L1I% | FF-NoFetch% | FF-Decode% | L2I MPKI | L2D MPKI |
|---|---|---|---|---|---|---|---|
| arizona | 2.3 | 8.23 | 9.92 | 48.89 | 13.92 | 0.70 | 10.65 |
| bravo | 9.5 | 4.06 | 19.64 | 70.27 | 3.69 | 2.51 | 8.59 |
| charlie | 10.2 | 4.74 | 18.07 | 66.53 | 5.60 | 1.39 | 12.38 |
| delta | 1.7 | 20.32 | 4.66 | 56.34 | 19.51 | 0.27 | 4.90 |
| merced | 8.6 | 4.27 | 18.11 | 69.92 | 4.04 | 2.93 | 10.46 |
| sierra.a.3 | 9.3 | 7.71 | 22.20 | 60.54 | 7.33 | 4.82 | 11.43 |
| sierra.a.4 | **21.5** | 4.94 | **29.17** | 60.83 | 4.97 | 6.62 | 13.68 |
| sierra.a.6 | 11.2 | 4.63 | 22.32 | 63.70 | 4.20 | 7.75 | 12.88 |
| tahoe | 10.1 | 6.26 | 20.41 | 63.94 | 7.69 | 2.79 | 10.33 |
| tango | 15.0 | 4.02 | 24.02 | 66.90 | 3.64 | 4.15 | 11.38 |
| whiskey | 4.7 | 6.39 | 8.41 | 70.57 | 15.60 | 0.86 | 49.84 |
| yankee | 10.5 | 2.55 | 19.53 | 70.58 | 2.59 | 2.87 | 11.45 |

### 각 지표와 IPC gain(2→64)의 상관계수 (ftq=2 시점 값 기준)

| 지표 | 의미 | r |
|---|---|---|
| **FF-L1I%** | L1I miss로 fetch→decode가 막힌 비율 | **+0.929** |
| **L2I MPKI** | L2C 접근 중 instruction-fetch 기원 demand MPKI | **+0.755** |
| FF-Decode% | decode 버퍼가 꽉 찬 비율(frontend 내부 정체) | -0.733 |
| BF-ROB% | 진짜 backend(ROB)가 꽉 찬 비율 | -0.583 |
| FF-NoFetch% | 애초에 fetch할 게 없는 비율 | +0.302 |
| L2D MPKI | L2C 접근 중 data 기원 demand MPKI | -0.144 |

참고로 **BF-ROB%와 FF-Decode%는 서로 r=+0.832로 강하게 상관**되어 있다 — ROB가 꽉 차면 그 바로 앞 단계인 decode buffer도 같이 밀리는 게 파이프라인 구조상 당연하므로, 이 둘은 사실상 "같은 backend 정체 현상을 서로 다른 지점에서 관측한 것"에 가깝다.

### 해석

1. **FF-L1I%(r=+0.929)가 가장 강한 예측 변수다** — 당연하다면 당연한 얘기지만(L1I 문제가 클수록 그걸 고쳤을 때 얻을 게 많다), 정량적으로 확인된 건 의미가 있다. `sierra.a.4`(FF-L1I% 29.17, gain 21.5%)가 가장 극단적인 예다.
2. **L2I MPKI(r=+0.755)도 거의 그만큼 강하다** — L1I miss가 L2C까지 넘어가는 양(=L2I MPKI)이 많을수록 FDIP 효과가 크다는 뜻이라, **L2I MPKI 하나만으로도 frontend stall 계측 없이 "이 trace가 FDIP 혜택을 얼마나 볼지" 어느 정도 가늠할 수 있다** — 이미 갖고 있던 L2C/LLC I/D split 계측만으로도 상당한 예측력이 있었던 셈이다.
3. **BF-ROB%/FF-Decode%(둘 다 backend 정체, r=-0.58~-0.73)는 "브레이크" 역할**이다 — FF-L1I%가 아무리 높아도(즉 고칠 거리가 많아도), backend가 이미 포화돼 있으면(`delta`: FF-L1I% 4.66로 낮고 BF-ROB% 20.32로 제일 높음 → gain 1.7%로 최저) 그 이득이 IPC로 전환되지 못한다.
4. **두 요인을 같이 보면 가장 잘 설명된다**: gain이 가장 큰 `sierra.a.4`/`tango`는 FF-L1I%가 높으면서 동시에 BF-ROB%/FF-Decode%가 낮다(둘 다 좋은 조건이 겹침). gain이 가장 작은 `delta`/`arizona`는 반대로 FF-L1I%가 낮으면서 BF-ROB%/FF-Decode%가 높다(둘 다 나쁜 조건이 겹침). `whiskey`는 FF-L1I%도 낮고(8.41) backend도 어느 정도 막혀있어서(FF-Decode% 15.60) gain이 낮다(4.7%) — 일관된 패턴이다.
5. **L2D MPKI는 거의 무관하다(r=-0.144)** — data 쪽 트래픽량 자체는 FDIP 효과와 별 상관이 없다는 뜻으로, L2C/LLC 간섭 연구에서 "data 압박이 큰 workload일수록 instruction 개선 효과가 죽는다" 같은 단순한 가설은 이 데이터로는 지지되지 않는다.

**한 줄 요약**: FDIP(또는 L1I 자원 확충)가 실제로 IPC를 얼마나 끌어올릴지는 "L1I가 원래 얼마나 아팠는지(FF-L1I%, L2I MPKI)"와 "backend에 그 이득을 받아낼 여유가 있는지(BF-ROB%, FF-Decode%)" 두 축의 조합으로 결정된다. L2C/LLC 공유 자원 배분 실험을 설계할 때도 이 두 축으로 trace를 미리 분류해두면, "간섭 완화가 실제로 IPC 개선으로 이어질 workload"와 "애초에 backend 병목이라 캐시를 아무리 손봐도 소용없는 workload"를 구분해서 볼 수 있을 것으로 보인다.

## 현재 진행 상태 확인 (Codex, 2026-07-13)

이 문서를 오늘 실험 일지의 중심 문서로 삼기로 했다. 앞으로 Codex와 토론하면서 나오는 분석, 가설, 검증 결과는 이 파일에 계속 추가하고, 하루 작업이 끝난 뒤 별도의 daily note로 요약한다.

### `frontend_stall_test` run 상태

현재 확인한 `outputs/frontend_stall_test` 구조:

```text
outputs/frontend_stall_test/
├── raw/
│   ├── fdip_2/
│   ├── fdip_4/
│   ├── fdip_16/
│   ├── fdip_32/
│   └── fdip_64/
└── summary/
    ├── fdip_2/
    ├── fdip_4/
    ├── fdip_16/
    ├── fdip_32/
    └── fdip_64/
```

`run.log` 마지막 줄 기준으로 trace run은 완료되었다.

```text
Trace run complete. Use -s to generate the summary.
```

각 ftq summary의 `metrics.csv`도 모두 생성되어 있고, 전부 343개 trace가 정상 완료되었다.

| ftq | metrics.csv 상태 |
|---|---|
| 2 | 343 total / 343 ok / 0 fail |
| 4 | 343 total / 343 ok / 0 fail |
| 16 | 343 total / 343 ok / 0 fail |
| 32 | 343 total / 343 ok / 0 fail |
| 64 | 343 total / 343 ok / 0 fail |

따라서 지금 분석에 사용하는 `frontend_stall_test` 데이터는 raw log와 summary 양쪽 모두 완주 상태로 봐도 된다.

### 현재 작업 트리 상태

root repository에는 오늘 실험/분석을 위한 변경이 남아 있다.

```text
 m ChampSim_FDIP
 M index.md
 M parser/parse_outputs.py
 M parser/summary.py
 M scripts/run.sh
 D traces/trace_gtrace_sierra.a.4_err.txt
 D traces/trace_gtrace_yankee_err.txt
?? docs/exp/2026_07_13_experiment.md
?? traces/trace_260707_2245_retry_21.txt
```

`ChampSim_FDIP` 내부 변경 파일:

```text
M inc/core_stats.h
M inc/instruction.h
M src/core_stats.cc
M src/ooo_cpu.cc
M src/plain_printer.cc
```

이 변경들은 오늘 frontend/backend stall breakdown 분석을 위해 추가한 계측과 출력 관련 수정으로 보인다. 아직 커밋 전이므로, 분석이 더 진행된 뒤 parser/run script 변경과 함께 어떤 단위로 커밋할지 결정해야 한다.

### 오늘 문서 운영 원칙

- 이 파일은 "실험 진행 일지"로 사용한다.
- 중간 계산, 가설, 반례, 해석 변경을 지우지 말고 누적한다.
- daily note는 나중에 별도로 작성한다.
- 지금은 결론을 빨리 고정하기보다, 어떤 지표가 FDIP 효과와 L2C/LLC I/D 간섭을 잘 설명하는지 추적한다.

## 질문: FF-Decode와 ROB_STALL 값은 왜 다른가?

오늘 `./scripts/run.sh -s 0x20 -r frontend_stall_test -f a`로 frontend stall summary를 찍어보면서, `FF-Decode`(`frontend_stall_backend_full_pct`)와 기존 `ROB_STALL`(`backend_stall_rob_pct`) 값이 비슷하게 움직이지만 완전히 같지는 않다는 점을 확인했다. 이름만 보면 둘 다 "뒤가 막힘"처럼 보이지만, 실제 계측 위치와 조건이 다르다.

### 계측 위치가 다르다

파이프라인의 관련 흐름을 단순화하면 다음과 같다.

```text
IFETCH_BUFFER
  -> DIB_HIT_BUFFER / DECODE_BUFFER
  -> DISPATCH_BUFFER
  -> ROB / LQ / SQ
```

- **FF-Decode**는 `O3_CPU::promote_to_decode()`에서 잰다.
  - IFETCH buffer 맨 앞 명령어가 fetch 완료 상태인데,
  - `DIB_HIT_BUFFER` 또는 `DECODE_BUFFER`에 빈 공간이 없어서,
  - fetch→decode 승격을 못 하는 cycle을 센다.
  - 즉 계측 위치는 **frontend의 decode 진입부**다.

- **ROB_STALL**은 `O3_CPU::dispatch_instruction()`에서 잰다.
  - `DISPATCH_BUFFER` 맨 앞 명령어가 dispatch 준비 상태인데,
  - ROB가 꽉 차서,
  - dispatch→ROB 삽입을 못 하는 cycle을 센다.
  - 즉 계측 위치는 **backend/dispatch 진입부**다.

따라서 FF-Decode는 ROB 자체를 직접 보지 않는다. decode 쪽 buffer가 꽉 찼는지만 본다. ROB_STALL은 decode buffer를 보지 않고 ROB가 꽉 찼는지만 본다.

### 중간 buffer 때문에 같은 현상이 시간차를 두고 보인다

ROB가 막히면 dispatch가 막히고, dispatch가 막히면 `DISPATCH_BUFFER`가 차고, 그 앞의 `DECODE_BUFFER`/`DIB_HIT_BUFFER`도 eventually 차면서 FF-Decode가 증가한다. 그래서 두 값은 강하게 상관될 수 있다.

하지만 중간 buffer들이 있기 때문에 같은 cycle에 반드시 동시에 증가하지는 않는다.

예를 들어:

- ROB가 꽉 찼지만 `DISPATCH_BUFFER.front()`가 아직 ready가 아니면 `ROB_STALL`은 안 잡힐 수 있다.
- decode buffer가 이미 꽉 차 있으면 `FF-Decode`는 증가하지만, 그 cycle에 ROB가 실제로 full인지와는 별개다.
- `promote_to_decode()`의 frontend stall 분류는 우선순위가 있다.
  - `IFETCH_BUFFER`가 비어 있으면 `NoInstrToFetch`
  - 맨 앞 instruction이 아직 fetch 완료가 아니면 `L1IMiss`
  - 그 다음에야 decode-side full을 `BackendFull`로 센다.
  - 따라서 decode buffer가 꽉 차 있어도 앞 조건이 먼저 걸리면 FF-Decode로 집계되지 않는다.

### 실제 예: arizona_0000, ftq=2

`outputs/frontend_stall_test/raw/fdip_2/gtrace_v2/arizona/...arizona_0000...log`에서는 다음처럼 나온다.

```text
====Backend Stall Breakdown====
ROB_STALL: 56815
LQ_STALL: 0
SQ_STALL: 4

====Frontend Stall Breakdown====
L1I_MISS: 6479
NO_INSTR_TO_FETCH: 178504
BACKEND_FULL: 56598
```

이 trace에서는 `ROB_STALL=56815`, `FF-Decode=56598`로 매우 가깝다. 이것은 decode-side full이 대부분 ROB pressure에서 온다는 뜻으로 해석할 수 있다. 하지만 완전히 같지는 않다. 위에서 말한 것처럼 두 지표가 서로 다른 stage에서, 서로 다른 조건으로, 중간 buffer를 사이에 두고 측정되기 때문이다.

### 정리

`FF-Decode`와 `ROB_STALL`은 같은 병목을 서로 다른 위치에서 관찰한 proxy일 수는 있지만, 같은 counter는 아니다.

- `ROB_STALL`: ROB가 꽉 차서 dispatch가 못 나간 cycle
- `FF-Decode`: decode 쪽 buffer가 꽉 차서 fetch 결과가 decode로 못 올라간 cycle

따라서 두 값이 강하게 상관되는 것은 자연스럽지만, 값이 반드시 같아야 한다고 보면 안 된다. 분석에서는 `ROB_STALL`을 진짜 backend pressure 지표로, `FF-Decode`를 그 pressure가 frontend까지 역류한 backpressure 지표로 구분해서 쓰는 것이 좋다.

## 분석: FF-Decode가 큰 그룹은 L1I MPKI 개선이 IPC로 잘 전환되지 않는다

`./scripts/run.sh -s 0x20 -r frontend_stall_test -f a`로 만든 frontend stall summary를 바탕으로, ftq=2에서 ftq=64로 키웠을 때의 group별 변화를 다시 정리했다. 여기서는 `FF-Decode%@2`를 기준으로 오름차순 정렬했다.

| Group | FF-Decode%@2 | BF-ROB%@2 | FF-L1I%@2 | L1I MPKI 2→64 | L1I↓ | IPC 2→64 | IPC Gain | 판단 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| yankee | 2.59 | 2.55 | 19.53 | 13.26→0.11 | 99.2% | 0.415→0.459 | 10.5% | 개선 큼 |
| tango | 3.64 | 4.02 | 24.02 | 21.20→0.17 | 99.2% | 0.307→0.353 | 15.0% | 개선 큼 |
| bravo | 3.69 | 4.06 | 19.64 | 28.24→0.08 | 99.7% | 0.376→0.412 | 9.5% | 중간 |
| merced | 4.04 | 4.27 | 18.11 | 15.94→0.17 | 98.9% | 0.438→0.475 | 8.6% | 중간 |
| sierra.a.6 | 4.20 | 4.63 | 22.32 | 40.95→0.46 | 98.9% | 0.490→0.545 | 11.2% | 개선 큼 |
| sierra.a.4 | 4.97 | 4.94 | 29.17 | 32.50→0.26 | 99.2% | 0.261→0.317 | 21.5% | 개선 큼 |
| charlie | 5.60 | 4.74 | 18.07 | 8.68→0.06 | 99.4% | 0.550→0.606 | 10.2% | 개선 큼 |
| sierra.a.3 | 7.33 | 7.71 | 22.20 | 21.79→0.24 | 98.9% | 0.515→0.562 | 9.3% | 중간 |
| tahoe | 7.69 | 6.26 | 20.41 | 13.35→0.11 | 99.2% | 0.414→0.456 | 10.1% | 개선 큼 |
| arizona | 13.92 | 8.23 | 9.92 | 4.62→0.06 | 98.7% | 1.258→1.288 | 2.3% | 개선 낮음 |
| whiskey | 15.60 | 6.39 | 8.41 | 5.35→0.05 | 99.1% | 0.225→0.235 | 4.7% | 개선 낮음 |
| delta | 19.51 | 20.32 | 4.66 | 2.84→0.02 | 99.2% | 0.895→0.910 | 1.7% | 개선 낮음 |

패턴은 뚜렷하다.

- `FF-Decode%@2`가 낮은 그룹들은 L1I MPKI를 줄였을 때 IPC gain이 대체로 8~21%까지 나온다.
- `FF-Decode%@2`가 13% 이상으로 높은 `arizona`, `whiskey`, `delta`는 L1I MPKI가 98~99% 줄어도 IPC gain이 5% 미만이다.
- 즉 이 세 그룹에서는 FDIP가 L1I miss를 없애는 데는 성공하지만, 그 이득이 IPC로 전환되지 못한다.

해석하면, `FF-Decode`가 높다는 것은 fetch 결과가 decode 쪽으로 올라가려 해도 `DIB_HIT_BUFFER`/`DECODE_BUFFER`가 이미 차 있어서 막히는 cycle이 많다는 뜻이다. 이 경우 L1I miss를 줄여서 더 많은 instruction을 가져와도, 바로 뒤쪽 buffer가 막혀 있어서 frontend 병목 제거 효과가 IPC로 잘 이어지지 않는다.

반대로 `FF-Decode`가 낮고 `FF-L1I%`가 높은 그룹은 아직 decode/back-end 쪽 여유가 있다. 이 경우 L1I MPKI를 줄이면 실제로 fetch→decode 흐름이 좋아지고 IPC가 오른다. `sierra.a.4`, `tango`, `sierra.a.6`이 대표적이다.

## IPC 개선이 낮은 그룹의 추가 병목 분석

IPC gain이 5% 미만인 그룹을 따로 보면, 세 그룹 모두 "L1I가 주 병목이 아니다"는 점은 같지만, 구체적인 원인은 조금 다르다.

| Group | Gain@64 | FF-L1I%@2 | FF-Decode%@2 | BF-ROB%@2 | NoFetch%@2 | L1D MPKI | L2D MPKI | Br MPKI | STLB MPKI | OffChip MPKI |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| arizona | 2.3% | 9.92 | 13.92 | 8.23 | 48.89 | 7.77 | 10.65 | 8.89 | 1.45 | 18.79 |
| whiskey | 4.7% | 8.41 | 15.60 | 6.39 | 70.57 | 20.66 | 49.84 | 14.62 | 5.24 | 56.22 |
| delta | 1.7% | 4.66 | 19.51 | 20.32 | 56.34 | 18.78 | 4.90 | 10.40 | 1.52 | 17.70 |

### arizona

- L1I MPKI는 ftq=2에서도 4.62로 상대적으로 낮다.
- `FF-L1I%@2`도 9.92%로, FDIP 효과가 큰 그룹들(대략 18~29%)보다 낮다.
- 반면 `FF-Decode%@2`는 13.92%, `BF-ROB%@2`는 8.23%로 꽤 높다.
- IPC는 이미 1.258로 높아서, L1I를 고쳐도 추가로 개선될 headroom이 작다.

정리하면 `arizona`는 **이미 잘 흘러가는 workload인데, 남은 정체는 L1I보다 decode/backend backpressure 쪽**에 가깝다. FDIP는 L1I MPKI를 거의 없애지만, IPC gain은 2.3%에 그친다.

### whiskey

- `FF-L1I%@2`는 8.41%로 낮다.
- `FF-Decode%@2`는 15.60%로 높지만, `BF-ROB%@2`는 6.39%로 `delta`만큼 높지는 않다.
- 대신 data-side 지표가 매우 크다.
  - `L1D MPKI=20.66`
  - `L2D MPKI=49.84`
  - `OffChip MPKI=56.22`
  - `STLB MPKI=5.24`
- `NoFetch%@2`도 70.57%로 매우 높다.

정리하면 `whiskey`는 **L1I보다 data-side memory/TLB pressure가 더 강한 workload**로 보인다. FDIP로 instruction miss를 없애도 data miss/off-chip traffic이 지배적이라 IPC가 4.7% 정도만 개선된다.

### delta

- `FF-L1I%@2`가 4.66%로 가장 낮다. 즉 애초에 L1I miss 때문에 막히는 시간이 거의 없다.
- `FF-Decode%@2`는 19.51%, `BF-ROB%@2`는 20.32%로 가장 높다.
- `L2D MPKI=4.90`, `OffChip MPKI=17.70`으로 whiskey처럼 data miss가 압도적인 케이스는 아니다.

정리하면 `delta`는 **명확한 backend/ROB 병목 workload**다. L1I MPKI는 2.84→0.02로 거의 사라지지만, 애초에 L1I stall 비중이 작고 ROB/decode pressure가 커서 IPC gain은 1.7%에 그친다.

### 결론

ftq를 키워도 IPC 개선이 작은 workload는 한 종류가 아니다.

- `delta`: backend/ROB 포화가 주 문제
- `whiskey`: data-side memory/TLB/off-chip pressure가 주 문제
- `arizona`: L1I 병목 자체가 작고, decode/backend backpressure와 높은 baseline IPC 때문에 개선 여지가 작음

따라서 "FDIP가 효과 없는 workload"를 하나로 묶으면 안 된다. 앞으로는 최소한 다음 3종으로 나눠서 봐야 한다.

1. **Backend-limited**: `delta`형
2. **Data/memory-limited**: `whiskey`형
3. **Low-headroom / weak-L1I-limited**: `arizona`형

이 분류는 L2C/LLC I/D 간섭 연구에서도 중요하다. 특히 data-side pressure가 큰 `whiskey`형은 instruction prefetch가 data working set을 밀어내는지 확인할 좋은 후보이고, backend-limited인 `delta`형은 cache 정책을 바꿔도 IPC 개선이 작게 보일 가능성이 높다.

## 12개 trace group 전체를 4개 병목 유형으로 분류

앞 섹션에서는 IPC gain이 낮은 3개 group(`arizona`, `whiskey`, `delta`)을 각각 다른 원인으로 분류했다. 여기에 나머지 9개 group을 **Frontend-limited**로 추가하면, 12개 group 전체를 4개 유형으로 나눌 수 있다.

분류 기준은 다음처럼 잡는다.

- **Frontend-limited**
  - `FF-L1I%@2`가 높고, `FF-Decode%@2`/`BF-ROB%@2`가 충분히 낮다.
  - ftq를 키워 L1I MPKI를 줄이면 IPC gain이 실제로 나타난다.
- **Low-headroom / weak-L1I-limited**
  - baseline IPC가 이미 높거나, `FF-L1I%@2`가 낮아서 L1I를 개선해도 얻을 여지가 작다.
  - 동시에 `FF-Decode`도 높아 L1I 개선분이 쉽게 막힌다.
- **Data/memory-limited**
  - L1I보다 data-side miss, TLB miss, off-chip traffic이 더 큰 문제다.
  - FDIP가 instruction miss를 줄여도 data-side 병목 때문에 IPC gain이 작다.
- **Backend-limited**
  - `BF-ROB%@2`와 `FF-Decode%@2`가 매우 높다.
  - backend/ROB가 주 병목이라 L1I MPKI를 줄여도 IPC로 전환되지 않는다.

### 전체 분류표

| 분류 | Group | IPC Gain@64 | FF-L1I%@2 | FF-Decode%@2 | BF-ROB%@2 | L2I MPKI@2 | L2D MPKI@2 | OffChip MPKI@2 | 판단 근거 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| Frontend-limited | bravo | 9.5% | 19.64 | 3.69 | 4.06 | 2.51 | 8.59 | 22.42 | FF-L1I가 높고 FF-Decode/BF가 낮아 FDIP gain이 IPC로 전환됨 |
| Frontend-limited | charlie | 10.2% | 18.07 | 5.60 | 4.74 | 1.39 | 12.38 | 24.80 | FF-L1I가 높고 FF-Decode/BF가 낮아 FDIP gain이 IPC로 전환됨 |
| Frontend-limited | merced | 8.6% | 18.11 | 4.04 | 4.27 | 2.93 | 10.46 | 24.64 | FF-L1I가 높고 FF-Decode/BF가 낮아 FDIP gain이 IPC로 전환됨 |
| Frontend-limited | sierra.a.3 | 9.3% | 22.20 | 7.33 | 7.71 | 4.82 | 11.43 | 25.20 | FF-L1I가 높고 gain이 유지됨. 다만 backend pressure는 frontend-limited group 안에서 높은 편 |
| Frontend-limited | sierra.a.4 | 21.5% | 29.17 | 4.97 | 4.94 | 6.62 | 13.68 | 34.30 | 가장 강한 frontend-limited case. FF-L1I와 L2I가 모두 높고 backend 여유도 있음 |
| Frontend-limited | sierra.a.6 | 11.2% | 22.32 | 4.20 | 4.63 | 7.75 | 12.88 | 17.95 | FF-L1I/L2I가 높고 backend pressure가 낮아 gain이 잘 나옴 |
| Frontend-limited | tahoe | 10.1% | 20.41 | 7.69 | 6.26 | 2.79 | 10.33 | 27.68 | frontend-limited지만 FF-Decode가 경계에 가까운 case |
| Frontend-limited | tango | 15.0% | 24.02 | 3.64 | 4.02 | 4.15 | 11.38 | 27.45 | FF-L1I가 높고 FF-Decode/BF가 낮아 gain이 큼 |
| Frontend-limited | yankee | 10.5% | 19.53 | 2.59 | 2.55 | 2.87 | 11.45 | 26.73 | backend pressure가 가장 낮은 frontend-limited case |
| Low-headroom / weak-L1I-limited | arizona | 2.3% | 9.92 | 13.92 | 8.23 | 0.70 | 10.65 | 18.79 | baseline IPC가 높고 FF-L1I/L2I가 낮아 L1I 개선 여지가 작음 |
| Data/memory-limited | whiskey | 4.7% | 8.41 | 15.60 | 6.39 | 0.86 | 49.84 | 56.22 | data-side MPKI/off-chip/STLB pressure가 커서 FDIP gain이 제한됨 |
| Backend-limited | delta | 1.7% | 4.66 | 19.51 | 20.32 | 0.27 | 4.90 | 17.70 | ROB/FF-Decode가 가장 높고 FF-L1I가 가장 낮아 backend가 주 병목 |

### 해석

12개 group 중 9개는 넓은 의미의 **Frontend-limited**로 볼 수 있다. 이들은 `FF-L1I%@2`가 18~29% 수준으로 높고, ftq를 키워 L1I MPKI를 줄이면 IPC가 8.6~21.5% 개선된다. 즉 FDIP가 겨냥하는 병목이 실제로 존재하고, backend가 그 이득을 받아낼 정도의 여유도 있다.

반면 `arizona`, `whiskey`, `delta`는 모두 IPC gain이 낮지만 이유가 다르다.

- `arizona`: L1I 병목이 약하고 baseline IPC가 높아서 headroom이 작다.
- `whiskey`: data/memory pressure가 커서 instruction-side 개선이 전체 성능으로 잘 이어지지 않는다.
- `delta`: backend/ROB 병목이 강해서 L1I를 고쳐도 뒤쪽에서 막힌다.

따라서 앞으로의 실험에서는 단순히 "FDIP gain이 큰 그룹/작은 그룹"으로 나누기보다, 위 4분류를 기준으로 각 정책의 효과를 따로 보는 것이 좋다. 특히 L2C/LLC I/D 간섭을 보려면 `Frontend-limited`와 `Data/memory-limited`를 비교하는 것이 중요하다. `Backend-limited`는 cache 정책 효과가 IPC로 잘 보이지 않는 음성 대조군처럼 사용할 수 있다.

## 재검토: FF-Decode HIGH 그룹이 모두 backend-limited인가?

앞의 LOW/MID/HIGH 표는 `FF-Decode%@ftq=2`를 기준으로 12개 group을 4개씩 잘라 본 것이다.

| 그룹 | trace groups | FF-Decode%@2 범위 |
|---|---|---|
| LOW | yankee, tango, bravo, merced | 2.59 ~ 4.04 |
| MID | sierra.a.6, sierra.a.4, charlie, sierra.a.3 | 4.20 ~ 7.33 |
| HIGH | tahoe, arizona, whiskey, delta | 7.69 ~ 19.51 |

이 표만 보면 HIGH에 4개가 있으므로 "backend 문제가 있는 workload가 4개, 혹은 더 많다"처럼 보일 수 있다. 하지만 여기서 주의해야 할 점은, **FF-Decode가 높다는 것과 최종적으로 backend-limited라는 것은 같은 말이 아니라는 것**이다.

`FF-Decode`는 backend/decode 쪽 backpressure를 보는 지표다. 하지만 FDIP의 IPC gain은 적어도 두 축의 조합으로 결정된다.

1. **고칠 거리**: 원래 L1I 때문에 얼마나 막혔는가? (`FF-L1I%`, `L2I MPKI`)
2. **이득을 받아낼 여유**: backend/decode 쪽이 얼마나 막혀 있는가? (`FF-Decode%`, `BF-ROB%`)

따라서 `FF-Decode`가 높아도 `FF-L1I%`가 충분히 높으면 FDIP gain이 여전히 크게 나올 수 있다. 반대로 `FF-Decode`가 높고 `FF-L1I%`가 낮으면, L1I를 고쳐도 IPC가 거의 오르지 않는다.

### HIGH 그룹 내부 재해석

| Group | FF-Decode%@2 | FF-L1I%@2 | BF-ROB%@2 | IPC Gain@64 | 해석 |
|---|---:|---:|---:|---:|---|
| tahoe | 7.69 | 20.41 | 6.26 | 10.1% | FF-Decode는 높지만 FF-L1I도 높아서 FDIP gain이 유지됨 |
| arizona | 13.92 | 9.92 | 8.23 | 2.3% | L1I 병목이 약하고 baseline IPC가 높아 개선 여지가 작음 |
| whiskey | 15.60 | 8.41 | 6.39 | 4.7% | L1I보다 data/memory pressure가 큼 |
| delta | 19.51 | 4.66 | 20.32 | 1.7% | 명확한 backend/ROB 병목 |

이렇게 보면 HIGH 그룹 중에서 **순수하게 backend-limited라고 부를 수 있는 것은 `delta`가 가장 명확하다.** `arizona`는 backend/decode pressure가 꽤 있지만, 더 정확히는 "L1I 병목 자체가 약하고 baseline IPC가 높아 headroom이 작은" 케이스다. `whiskey`는 FF-Decode도 높지만 data-side/off-chip pressure가 훨씬 두드러진다. `tahoe`는 HIGH 그룹에 들어가긴 하지만 `FF-L1I%`가 20.41%로 높기 때문에 FDIP gain이 10.1%까지 나온다.

### 결론

질문에 대한 답은 다음과 같다.

- `FF-Decode` 기준 HIGH 그룹은 4개다.
- 하지만 "ftq를 늘려도 IPC 개선이 미미한 그룹"은 `arizona`, `whiskey`, `delta` 3개다.
- 그중에서도 **진짜 backend-limited로 가장 명확한 것은 `delta`**다.
- `arizona`와 `whiskey`는 backend 영향도 있지만, 각각 low-headroom/weak-L1I, data/memory-limited 성격이 더 중요하다.
- `tahoe`는 FF-Decode가 높아 보이지만, FF-L1I도 높기 때문에 frontend-limited 그룹에 남기는 것이 맞다.

따라서 앞으로는 `FF-Decode` 하나만으로 병목 유형을 결정하지 말고, `FF-L1I%`와 실제 IPC gain을 함께 보면서 분류해야 한다.

## 질문: 앞서 만든 LOW/MID/HIGH 3그룹 분할, 기준이 어떤 값이었나?

이전에 "BackendFull%@ftq=2 오름차순, 4개씩 3그룹(LOW/MID/HIGH)" 섹션에서 쓴 기준값을 다시 확인해달라는 질문이 있었다. 그 표의 숫자(yankee 2.59 ~ delta 19.51)를 지금 metrics.csv의 `backend_stall_rob_pct`/`frontend_stall_backend_full_pct`와 대조해보면, `frontend_stall_backend_full_pct`(이 문서 뒷부분에서 `FF-Decode`로 다시 부른 값)와 정확히 일치한다. 즉 그 3그룹 분할은 **`FF-Decode`(frontend 내부 decode buffer 정체) 기준**이었고, 진짜 `ROB_STALL`(backend) 기준이 아니었다.

`FF-Decode`와 `ROB_STALL`이 서로 다른 지점을 재는 별개 counter라는 게 바로 위 섹션에서 확인됐으니, 같은 3그룹 분할을 `ROB_STALL` 기준으로도 다시 해서 결과가 얼마나 달라지는지 확인했다.

### `ROB_STALL%@ftq=2` 기준 재정렬

```text
yankee      2.55
tango       4.02
bravo       4.06
merced      4.27
sierra.a.6  4.63
charlie     4.74
sierra.a.4  4.94
tahoe       6.26
whiskey     6.39
sierra.a.3  7.71
arizona     8.23
delta       20.32
```

`FF-Decode` 기준 정렬과 순서가 꽤 다르다 — 특히 `tahoe`(FF-Decode 기준으로는 HIGH 그룹, ROB_STALL 기준으로는 MID)와 `sierra.a.3`/`whiskey`/`arizona`(FF-Decode 기준으로는 MID 근처, ROB_STALL 기준으로는 HIGH)의 위치가 바뀐다.

### ROB_STALL% 기준 3그룹 재분할 및 그룹 내 상관계수

| 그룹 | trace groups | ROB_STALL%@2 범위 | r(Gain@4) | r(Gain@16) | r(Gain@32) | r(Gain@64) |
|---|---|---|---|---|---|---|
| LOW | yankee, tango, bravo, merced | 2.55 ~ 4.27 | -0.110 | -0.030 | -0.043 | 0.002 |
| MID | sierra.a.6, charlie, sierra.a.4, tahoe | 4.63 ~ 6.26 | -0.297 | -0.295 | -0.263 | -0.233 |
| HIGH | whiskey, sierra.a.3, arizona, delta | 6.39 ~ 20.32 | -0.494 | -0.525 | -0.526 | -0.557 |

`FF-Decode` 기준으로 했을 때(LOW r≈-0.10, MID r≈-0.41~-0.52, HIGH r≈-0.85~-0.90)와 비교하면:

- LOW 구간은 두 기준 모두 상관관계가 거의 없다(r≈-0.1 근방) — 어느 지표로 보든 결론이 같다.
- MID 구간은 두 기준이 비슷한 수준(-0.23~-0.52)으로, 큰 차이는 없다.
- **HIGH 구간에서 차이가 크다**: `FF-Decode` 기준으로는 r≈-0.85~-0.90로 거의 선형에 가까웠는데, `ROB_STALL` 기준으로는 r≈-0.49~-0.56으로 훨씬 약해진다. 원인은 `sierra.a.3`이다 — `ROB_STALL%`로는 HIGH 그룹에 속하지만(7.71%), 실제 gain은 이 그룹 안에서 가장 높다(9.3%@ftq=64, whiskey 4.7%/arizona 2.3%/delta 1.7%보다 훨씬 큼). `sierra.a.3`은 `FF-L1I%`가 22.20으로 12개 그룹 중 두 번째로 높았던 workload라(앞 섹션 상관계수 표 참고), backend pressure가 어느 정도 있어도 원래 L1I 문제가 워낙 컸던 덕에 gain이 크게 나온 것으로 보인다.

### 해석

같은 3그룹 분할이라도 어떤 지표를 기준으로 삼느냐에 따라 그룹 구성과 그룹 내 상관관계의 강도가 달라진다. 이번 비교에서는 **`FF-Decode`가 `ROB_STALL`보다 "gain을 얼마나 깨끗하게 설명하는 문턱 변수"로서는 더 낫다** — 특히 HIGH 구간에서 그렇다. 가능한 설명:

- `FF-Decode`는 fetch→decode 승격 시점에서 재기 때문에, ROB 압력이 중간 buffer(`DISPATCH_BUFFER` 등)를 거쳐 frontend까지 전파된 "누적된 backpressure"를 반영한다. 반면 `ROB_STALL`은 dispatch 시점의 순간적인 ROB full 여부만 본다.
- `promote_to_decode()`의 분류 우선순위(`NoInstrToFetch` → `L1IMiss` → `BackendFull`) 때문에, `FF-Decode`는 이미 "다른 이유로 stall이 아닌" 사이클만 걸러낸 뒤에 decode buffer full을 세므로, 노이즈가 좀 더 적을 수 있다.

다만 이 역시 그룹당 4개 trace뿐인 표본에서 나온 관찰이라, `sierra.a.3` 하나가 HIGH 그룹 상관관계를 크게 흔든 것처럼 표본이 조금만 바뀌어도 결론이 민감하게 움직일 수 있다는 점은 계속 감안해야 한다.

## 지적: "ftq=2 시점 값 vs gain" 표는 와닿지 않는다 — 지표별로 ftq 추이를 따로 보자

앞서 만든 "12개 trace group, ftq=2 시점 값 vs IPC gain(ftq=2→64)" 표는 gain은 ftq=2→64 변화량인데 나머지 지표는 ftq=2 스냅샷 하나만 보여줘서, 그 지표들이 ftq를 올리는 동안 실제로 어떻게 움직이는지가 안 보인다는 지적이 있었다. 상관관계 계산에서 유의미했던 지표(`FF-L1I%`, `L2I MPKI`, `FF-Decode%`, `BF-ROB%`)만 골라서, 각각을 ftq 5개 지점(2/4/16/32/64) 전부에 대해 group별로 펼쳐서 다시 정리한다. 정렬 기준은 `FF-Decode%@ftq=2` 오름차순(앞 섹션들과 동일)으로 통일한다.

### IPC

| group | ftq=2 | ftq=4 | ftq=16 | ftq=32 | ftq=64 |
|---|---|---|---|---|---|
| yankee | 0.415 | 0.435 | 0.452 | 0.456 | 0.459 |
| tango | 0.307 | 0.326 | 0.345 | 0.350 | 0.353 |
| bravo | 0.376 | 0.390 | 0.405 | 0.406 | 0.412 |
| merced | 0.438 | 0.455 | 0.470 | 0.473 | 0.475 |
| sierra.a.6 | 0.490 | 0.513 | 0.539 | 0.543 | 0.545 |
| sierra.a.4 | 0.261 | 0.283 | 0.307 | 0.313 | 0.317 |
| charlie | 0.550 | 0.575 | 0.597 | 0.602 | 0.606 |
| sierra.a.3 | 0.515 | 0.533 | 0.554 | 0.559 | 0.562 |
| tahoe | 0.414 | 0.431 | 0.448 | 0.453 | 0.456 |
| arizona | 1.258 | 1.268 | 1.282 | 1.285 | 1.288 |
| whiskey | 0.225 | 0.229 | 0.233 | 0.234 | 0.235 |
| delta | 0.895 | 0.904 | 0.909 | 0.911 | 0.910 |

### FF-L1I% (L1I miss로 fetch→decode가 막힌 비율 — "고칠 거리")

| group | ftq=2 | ftq=4 | ftq=16 | ftq=32 | ftq=64 |
|---|---|---|---|---|---|
| yankee | 19.53 | 13.35 | 6.67 | 5.20 | 4.46 |
| tango | 24.02 | 17.24 | 9.05 | 6.92 | 5.91 |
| bravo | 19.64 | 14.41 | 7.48 | 5.77 | 4.88 |
| merced | 18.11 | 12.68 | 6.40 | 5.12 | 4.38 |
| sierra.a.6 | 22.32 | 16.33 | 7.58 | 5.61 | 4.91 |
| sierra.a.4 | **29.17** | 21.36 | 10.76 | 8.04 | 6.46 |
| charlie | 18.07 | 12.95 | 7.28 | 5.94 | 4.98 |
| sierra.a.3 | 22.20 | 16.34 | 8.46 | 6.43 | 5.34 |
| tahoe | 20.41 | 14.59 | 7.74 | 5.99 | 4.91 |
| arizona | 9.92 | 7.31 | 4.32 | 3.28 | 2.80 |
| whiskey | 8.41 | 6.01 | 3.19 | 2.28 | 1.90 |
| delta | 4.66 | 3.38 | 1.84 | 1.30 | 1.24 |

ftq를 올려도 0까지 떨어지지 않고 `arizona`/`whiskey`/`delta`(4~10%대), 나머지 그룹(18~29%대)이라는 순서가 그대로 유지된다 — 즉 이 지표의 "그룹 간 순위"는 ftq와 무관하게 안정적이다.

### L2I MPKI (L2C 접근 중 instruction-fetch 기원 demand MPKI)

| group | ftq=2 | ftq=4 | ftq=16 | ftq=32 | ftq=64 |
|---|---|---|---|---|---|
| yankee | 2.87 | 0.79 | 0.06 | 0.02 | 0.00 |
| tango | 4.15 | 1.19 | 0.09 | 0.02 | 0.00 |
| bravo | 2.51 | 0.85 | 0.13 | 0.03 | 0.00 |
| merced | 2.93 | 0.89 | 0.07 | 0.02 | 0.00 |
| sierra.a.6 | 7.75 | 4.20 | 0.82 | 0.22 | 0.02 |
| sierra.a.4 | 6.62 | 2.34 | 0.28 | 0.06 | 0.01 |
| charlie | 1.39 | 0.31 | 0.02 | 0.00 | 0.00 |
| sierra.a.3 | 4.82 | 1.81 | 0.23 | 0.06 | 0.01 |
| tahoe | 2.79 | 0.76 | 0.05 | 0.01 | 0.00 |
| arizona | 0.70 | 0.20 | 0.01 | 0.00 | 0.00 |
| whiskey | 0.86 | 0.27 | 0.03 | 0.00 | 0.00 |
| delta | 0.27 | 0.08 | 0.01 | 0.00 | 0.00 |

`FF-L1I%`와 달리 `L2I MPKI`는 ftq=64에서 사실상 전 그룹이 0에 수렴한다 — L1I miss 자체는(`FF-L1I%`) 어느 정도 바닥이 있는데, 그중 L2C까지 넘어가는 양(`L2I MPKI`)은 FDIP가 커버할수록 거의 완전히 사라진다는 뜻이다. 즉 두 지표는 "같은 방향"이지만 감소 양상이 다르다 — `L2I MPKI`가 `FF-L1I%`보다 ftq에 더 민감하게 반응한다.

### FF-Decode% / BF-ROB% (backend 쪽 "브레이크" 두 지표, ftq와 거의 무관)

| group | FF-Decode%@2 | FF-Decode%@64 | BF-ROB%@2 | BF-ROB%@64 |
|---|---|---|---|---|
| yankee | 2.59 | 2.97 | 2.55 | 2.93 |
| tango | 3.64 | 4.02 | 4.02 | 4.41 |
| bravo | 3.69 | 4.20 | 4.06 | 4.62 |
| merced | 4.04 | 4.43 | 4.27 | 4.68 |
| sierra.a.6 | 4.20 | 4.46 | 4.63 | 4.92 |
| sierra.a.4 | 4.97 | 5.45 | 4.94 | 5.32 |
| charlie | 5.60 | 6.10 | 4.74 | 5.21 |
| sierra.a.3 | 7.33 | 7.81 | 7.71 | 8.20 |
| tahoe | 7.69 | 8.43 | 6.26 | 6.80 |
| arizona | 13.92 | 14.58 | 8.23 | 8.50 |
| whiskey | 15.60 | 16.65 | 6.39 | 6.67 |
| delta | 19.51 | 19.97 | 20.32 | 20.72 |

`FF-L1I%`/`L2I MPKI`가 ftq에 따라 몇 배~수십 배씩 바뀌는 것과 정반대로, `FF-Decode%`와 `BF-ROB%`는 ftq=2→64 동안 거의 안 움직인다(대부분 그룹에서 절대값 기준 +0.3~+1.0%p 수준). 즉 **backend 쪽 정체는 FTQ size와 상관없이 그 워크로드가 원래 갖고 있던 고유한 값**이고, ftq는 오직 frontend(`FF-L1I%`, `L2I MPKI`) 쪽 지표만 움직인다.

### 정리: 왜 "ftq=2 스냅샷 vs gain" 표가 이해하기 편한 근사였는지

- `FF-Decode%`/`BF-ROB%`는 ftq에 거의 반응하지 않으므로, ftq=2 시점 값이나 ftq=64 시점 값이나 사실상 같은 숫자다 — 어느 시점에서 재도 "이 워크로드의 backend 여유도"라는 같은 의미를 갖는다. 그래서 "ftq=2 시점 값"만 대표로 써도 정보 손실이 거의 없었다.
- 반대로 `FF-L1I%`/`L2I MPKI`는 ftq를 올릴수록 값 자체가 급격히 줄어드는 지표라서, 단일 시점 스냅샷보다는 "ftq=2에서 얼마나 컸는가(=고칠 거리가 얼마나 컸는가)"가 gain을 설명하는 데 의미 있는 것이지, ftq=64 시점 값(대부분 0에 수렴)은 gain과 비교할 대상으로 부적절하다.

즉 4개 지표를 성격별로 나누면: `FF-Decode%`/`BF-ROB%`는 "ftq와 무관한 워크로드 고유 상수"로, `FF-L1I%`/`L2I MPKI`(정확히는 그 ftq=2 값)는 "ftq가 없앨 수 있는 여유분의 크기"로 이해하는 게 정확하다. 앞서 만든 "ftq=2 값 vs gain" 표는 이 두 축을 한 시점에 모아본 것이었고, 이번에 ftq별로 펼쳐보니 그 근사가 왜 타당했는지가 확인됐다.

## 요청: FF-Decode 정렬 기준으로 IPC/L1I/L2I/L2D 변화를 함께 보기

이번에는 12개 group을 모두 `FF-Decode%@ftq=2` 오름차순으로 정렬한 뒤, ftq를 키울 때 IPC gain, L1I MPKI 감소율, L2I MPKI 감소율, L2D MPKI 변화를 한 번에 비교했다. 목적은 다음 두 가지다.

1. `FF-Decode`가 큰 workload에서 L1I/L2I MPKI가 개선되어도 IPC가 잘 안 오르는지 확인한다.
2. L2I를 줄이는 과정에서 L2D가 나빠지는지, 즉 instruction/data 간섭 흔적이 바로 보이는지 확인한다.

### IPC gain

| Group | FF-Decode%@2 | Gain@4 | Gain@16 | Gain@32 | Gain@64 |
|---|---:|---:|---:|---:|---:|
| yankee | 2.59 | 4.7% | 8.9% | 9.8% | 10.5% |
| tango | 3.64 | 6.2% | 12.4% | 14.0% | 15.0% |
| bravo | 3.69 | 3.7% | 7.8% | 8.1% | 9.5% |
| merced | 4.04 | 3.9% | 7.4% | 8.1% | 8.6% |
| sierra.a.6 | 4.20 | 4.8% | 10.0% | 11.0% | 11.2% |
| sierra.a.4 | 4.97 | 8.3% | 17.4% | 19.8% | 21.5% |
| charlie | 5.60 | 4.5% | 8.5% | 9.4% | 10.2% |
| sierra.a.3 | 7.33 | 3.4% | 7.6% | 8.7% | 9.3% |
| tahoe | 7.69 | 4.2% | 8.3% | 9.4% | 10.1% |
| arizona | 13.92 | 0.8% | 1.9% | 2.1% | 2.3% |
| whiskey | 15.60 | 2.0% | 3.7% | 4.5% | 4.7% |
| delta | 19.51 | 0.9% | 1.5% | 1.8% | 1.7% |

`FF-Decode%@2`가 8% 미만인 대부분의 group은 ftq=64에서 IPC가 8.6~21.5% 개선된다. 반면 `arizona`, `whiskey`, `delta`처럼 `FF-Decode%@2`가 13% 이상인 group은 IPC gain이 5% 미만이다. `tahoe`는 `FF-Decode%@2=7.69`로 경계에 있지만 `FF-L1I%@2`가 높아서 10.1% gain을 유지한다.

### L1I MPKI 감소율

| Group | L1I↓@4 | L1I↓@16 | L1I↓@32 | L1I↓@64 |
|---|---:|---:|---:|---:|
| yankee | 30.9% | 84.3% | 96.3% | 99.2% |
| tango | 30.8% | 84.7% | 96.2% | 99.2% |
| bravo | 33.0% | 85.4% | 97.2% | 99.7% |
| merced | 28.4% | 79.9% | 93.5% | 98.9% |
| sierra.a.6 | 25.8% | 79.8% | 94.4% | 98.9% |
| sierra.a.4 | 28.8% | 83.1% | 96.1% | 99.2% |
| charlie | 30.7% | 84.5% | 96.0% | 99.4% |
| sierra.a.3 | 28.6% | 83.1% | 95.6% | 98.9% |
| tahoe | 31.5% | 84.7% | 96.1% | 99.2% |
| arizona | 27.7% | 79.4% | 93.3% | 98.7% |
| whiskey | 29.0% | 82.3% | 95.9% | 99.1% |
| delta | 26.5% | 84.3% | 96.9% | 99.2% |

L1I MPKI 감소율만 보면 모든 group이 비슷하다. ftq=64에서는 거의 전부 98~99% 이상 감소한다. 따라서 "L1I MPKI를 얼마나 많이 줄였는가"만으로는 IPC gain 차이를 설명할 수 없다.

### L2I MPKI 감소율과 L2D MPKI 변화율

| Group | L2I↓@4 | L2I↓@16 | L2I↓@32 | L2I↓@64 | L2DΔ@4 | L2DΔ@16 | L2DΔ@32 | L2DΔ@64 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| yankee | 72.4% | 97.7% | 99.4% | 99.9% | +0.02% | +0.11% | +0.20% | +0.26% |
| tango | 71.4% | 97.8% | 99.5% | 99.9% | +0.71% | +0.83% | +0.94% | +0.90% |
| bravo | 66.2% | 94.9% | 98.7% | 99.9% | +2.76% | +2.49% | +4.00% | +1.61% |
| merced | 69.5% | 97.8% | 99.4% | 99.9% | +0.30% | +0.47% | +0.61% | +0.57% |
| sierra.a.6 | 45.8% | 89.4% | 97.1% | 99.7% | +1.46% | +2.49% | +2.00% | +2.64% |
| sierra.a.4 | 64.6% | 95.7% | 99.1% | 99.8% | +0.44% | +0.81% | +0.57% | +0.83% |
| charlie | 77.3% | 98.4% | 99.7% | 99.9% | +0.06% | +0.17% | +0.20% | +0.32% |
| sierra.a.3 | 62.4% | 95.2% | 98.7% | 99.7% | +0.53% | -0.01% | +0.49% | +0.37% |
| tahoe | 72.8% | 98.1% | 99.5% | 99.9% | +0.27% | +0.46% | +0.59% | +0.44% |
| arizona | 72.2% | 98.2% | 99.6% | 100.0% | +0.24% | +0.22% | +0.08% | +0.17% |
| whiskey | 68.1% | 97.0% | 99.5% | 100.0% | +0.21% | +0.17% | +0.14% | -0.30% |
| delta | 71.8% | 95.9% | 99.3% | 99.8% | +0.81% | +0.51% | +0.51% | +0.81% |

L2I MPKI 역시 ftq가 커질수록 거의 모든 group에서 99% 이상 줄어든다. 즉 FDIP는 instruction-fetch 기원 L2C demand miss를 거의 제거한다.

반면 L2D MPKI 변화는 대부분 작다. 많은 group이 +0~1% 수준이고, 상대적으로 큰 group도 `bravo`(+4.00%@32), `sierra.a.6`(+2.64%@64) 정도다. `whiskey`는 오히려 ftq=64에서 -0.30%다. 따라서 현재 데이터만 보면 **ftq 증가가 L2D MPKI를 크게 악화시켜 IPC gain을 막았다**고 보기는 어렵다.

### 해석

이 표에서 가장 중요한 점은 다음이다.

1. **L1I/L2I 개선은 전 group에서 거의 성공한다.**
   - L1I MPKI는 ftq=64에서 대부분 99% 가까이 감소한다.
   - L2I MPKI는 ftq=64에서 거의 0에 수렴한다.

2. **하지만 IPC gain은 FF-Decode가 높은 group에서만 작다.**
   - `arizona`, `whiskey`, `delta`는 L1I/L2I 개선폭이 다른 group과 비슷한데도 IPC gain이 5% 미만이다.
   - 따라서 이들의 낮은 gain은 "FDIP가 L1I/L2I를 못 줄여서"가 아니라, 줄인 효과가 다른 병목에 막혀 IPC로 전환되지 못해서 생긴다.

3. **L2D MPKI 악화는 현재로서는 주된 설명이 아니다.**
   - ftq를 키워도 L2D MPKI 변화는 작다.
   - 따라서 "instruction prefetch가 L2D를 크게 망쳐서 IPC gain이 낮다"는 가설은 이 결과만으로는 약하다.
   - 다만 L2D MPKI가 아니라 L2D latency, MSHR occupancy, off-chip contention, useful/useless prefetch 같은 다른 data-side 지표는 추가로 봐야 한다.

정리하면, 이번 표는 `FF-Decode`가 높은 workload에서 IPC gain이 낮다는 관찰을 강화한다. 동시에 L1I/L2I MPKI 자체는 잘 줄어들고 L2D MPKI 악화도 작기 때문에, 다음 분석은 **MPKI가 아니라 stall/latency/queue pressure 계열 지표**로 넘어가야 한다.

## 질문: FTQ를 늘리면 L2C에서 instruction이 차지하는 범위가 커져 L2D에 부작용을 주는가?

가설은 타당하다. FDIP/FTQ를 크게 만들면 더 먼 미래의 instruction block을 미리 가져오게 되고, 그 과정에서 L1I뿐 아니라 shared L2C/LLC 자원에도 instruction-fetch 기원 request가 더 많이 들어갈 수 있다. 이 경우 두 가지 부작용이 가능하다.

1. instruction line이 L2C capacity를 차지해서 data line을 밀어낸다.
2. instruction prefetch request가 L2C/MSHR/하위 메모리 bandwidth를 점유해서 data demand의 latency를 키운다.

다만 현재 `frontend_stall_test`의 MPKI 결과만 보면, 첫 번째 부작용이 크게 나타난다는 증거는 약하다.

| Group | L2C MPKI@2 | L2C MPKI@64 | L2CΔ | L2I miss share@2 | L2I miss share@64 | L2DΔ@64 |
|---|---:|---:|---:|---:|---:|---:|
| yankee | 14.32 | 11.48 | -19.8% | 20.0% | 0.0% | +0.3% |
| tango | 15.53 | 11.48 | -26.1% | 26.7% | 0.0% | +0.9% |
| bravo | 11.10 | 8.73 | -21.3% | 22.6% | 0.0% | +1.6% |
| merced | 13.39 | 10.52 | -21.4% | 21.9% | 0.0% | +0.6% |
| sierra.a.6 | 20.63 | 13.25 | -35.8% | 37.5% | 0.2% | +2.6% |
| sierra.a.4 | 20.30 | 13.81 | -32.0% | 32.6% | 0.1% | +0.8% |
| charlie | 13.77 | 12.42 | -9.8% | 10.1% | 0.0% | +0.3% |
| sierra.a.3 | 16.26 | 11.49 | -29.3% | 29.7% | 0.1% | +0.4% |
| tahoe | 13.12 | 10.38 | -20.9% | 21.3% | 0.0% | +0.4% |
| arizona | 11.35 | 10.67 | -6.0% | 6.2% | 0.0% | +0.2% |
| whiskey | 50.70 | 49.69 | -2.0% | 1.7% | 0.0% | -0.3% |
| delta | 5.17 | 4.94 | -4.5% | 5.2% | 0.0% | +0.8% |

관찰:

- FTQ를 2에서 64로 키우면 L2I miss share는 거의 0으로 내려간다. 즉 instruction-fetch 기원 L2C demand miss는 FDIP가 거의 제거한다.
- L2C 전체 MPKI도 대부분 감소한다. instruction miss가 사라지는 효과가 data 쪽의 작은 변화보다 훨씬 크다.
- L2D MPKI는 대부분 +0~1% 수준이고, 가장 큰 `sierra.a.6`도 +2.6% 정도다. `whiskey`는 오히려 -0.3%다.

따라서 현재까지의 결론은 다음과 같다.

**MPKI 기준으로는 FTQ 증가가 L2D를 크게 망가뜨렸다고 보기 어렵다.** 오히려 L2I miss가 줄어들면서 L2C 전체 miss pressure는 감소한다.

하지만 이것이 "부작용이 없다"는 뜻은 아니다. 현재 표는 miss count 중심이라서, 다음 문제는 아직 못 본다.

- L2C hit latency가 증가했는가?
- L2C MSHR occupancy 또는 queue occupancy가 증가했는가?
- useful/useless instruction prefetch가 L2C/LLC capacity를 얼마나 차지했는가?
- data demand request가 instruction prefetch 때문에 늦게 처리되는가?
- L2D MPKI는 그대로인데 L2D miss latency만 증가하는가?

즉 다음 단계에서는 `L2D MPKI`보다 `L2D miss latency`, `MSHR merge/return`, `pf_useful/pf_useless`, `queue occupancy`, `off-chip traffic`을 instruction/data origin별로 나눠 봐야 한다. 특히 FDIP가 IPC gain을 못 만드는 `arizona`, `whiskey`, `delta`에서는 L2D MPKI 악화보다 **backend/decode pressure 또는 data miss latency** 쪽이 더 유력한 원인으로 보인다.

## 질문: L2D/L2I 비율 조절로 좋아질 만한 workload가 있는가?

이번 질문은 FTQ 자체의 효과와는 별개로, **L2C에서 instruction-fetch traffic과 data traffic이 서로 간섭하는 workload를 찾을 수 있는가**에 가깝다.

이 관점에서는 `L2I MPKI` 하나만 크거나 `L2D MPKI` 하나만 큰 workload보다, 두 값이 모두 의미 있게 크고 L2I가 L2C miss 중 꽤 큰 비중을 차지하는 workload가 더 좋은 후보가 된다. 즉 다음 조건을 본다.

- `L2I MPKI@ftq=2`가 충분히 크다.
- `L2D MPKI@ftq=2`도 충분히 크다.
- `L2I / (L2I + L2D)` 비중이 높다.
- 가능하면 FTQ를 키웠을 때 `L2D MPKI`가 조금이라도 증가하는 흔적이 있다.

| Group | L2I@2 | L2D@2 | L2I share@2 | L2DΔ@64 | LLC I share@2 | LLDΔ@64 | IPC gain@64 | 판단 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| sierra.a.6 | 7.75 | 12.88 | 37.5% | +2.6% | 10.0% | +0.1% | 11.2% | 가장 강한 후보 |
| sierra.a.4 | 6.62 | 13.68 | 32.6% | +0.8% | 21.6% | +0.0% | 21.5% | 강한 후보 |
| sierra.a.3 | 4.82 | 11.43 | 29.7% | +0.4% | 17.7% | -0.0% | 9.3% | 후보 |
| tango | 4.15 | 11.38 | 26.7% | +0.9% | 18.5% | -0.0% | 15.0% | 후보 |
| bravo | 2.51 | 8.59 | 22.6% | +1.6% | 14.5% | -0.0% | 9.5% | 약한 후보 |
| merced | 2.93 | 10.46 | 21.9% | +0.6% | 18.5% | +0.2% | 8.6% | 약한 후보 |
| tahoe | 2.79 | 10.33 | 21.3% | +0.4% | 18.5% | +0.0% | 10.1% | 약한 후보 |
| yankee | 2.87 | 11.45 | 20.0% | +0.3% | 17.5% | +0.1% | 10.5% | 약한 후보 |
| charlie | 1.39 | 12.38 | 10.1% | +0.3% | 9.4% | +0.2% | 10.2% | data 중심 |
| arizona | 0.70 | 10.65 | 6.2% | +0.2% | 5.3% | +0.0% | 2.3% | I/D 간섭 후보 아님 |
| delta | 0.27 | 4.90 | 5.2% | +0.8% | 4.6% | +0.3% | 1.7% | I/D 간섭 후보 아님 |
| whiskey | 0.86 | 49.84 | 1.7% | -0.3% | 1.6% | +0.0% | 4.7% | data-dominant |

현재 데이터에서 가장 그럴듯한 I/D 간섭 후보는 `sierra.a.6`, `sierra.a.4`, `sierra.a.3`, `tango`다.

- `sierra.a.6`: L2I share가 37.5%로 가장 높고, L2D도 12.88로 충분히 크다. FTQ=64에서 L2D MPKI가 +2.6% 늘어나는 흔적도 있어서, L2C 내 I/D 간섭을 찾기 위한 1순위 후보로 보인다.
- `sierra.a.4`: L2I와 L2D가 모두 크고, LLC에서도 instruction share가 21.6%로 높다. IPC gain이 21.5%로 매우 커서 instruction 쪽을 줄이면 손해가 클 수 있지만, 반대로 L2C I/D 자원 배분의 민감도를 보기에는 좋은 workload다.
- `sierra.a.3`, `tango`: L2I share가 26~30% 수준이고 L2D도 11대라서 후보군에 넣을 만하다.
- `bravo`: L2I share는 22.6%로 조금 낮지만, L2DΔ가 +1.6%라서 약한 후보로 볼 수 있다.

반대로 `whiskey`는 L2D MPKI가 압도적으로 크지만 L2I share가 1.7%밖에 안 된다. 이 경우는 I/D 간섭이라기보다 **data-side dominant workload**다. L2I/L2D 비율을 조절해도 instruction 쪽을 줄여서 얻을 여지가 작고, data latency/off-chip 쪽을 봐야 한다.

정리하면, I/D 간섭으로 인한 부작용을 찾는다면 우선순위는 다음이 좋아 보인다.

1. `sierra.a.6`
2. `sierra.a.4`
3. `sierra.a.3`
4. `tango`
5. `bravo` 또는 `merced`

다음 실험에서는 이 후보들에 대해 L2C replacement 또는 partitioning을 바꿔서, instruction line을 보호하는 정책과 data line을 보호하는 정책을 비교하면 좋다. 단순 MPKI보다 더 중요한 확인 지표는 `L2D miss latency`, `L2C eviction victim origin(I/D)`, `MSHR occupancy`, `pf_useful/pf_useless(I/D)`, `IPC`다.

## 질문: instruction L2C와 data L2C를 나누면 효과가 있을까?

가능성은 있지만, 모든 workload에서 좋아질 것 같지는 않다. 현재 데이터 기준으로는 **L2C I/D partitioning은 전체 평균 최적화라기보다 특정 workload의 간섭을 확인하기 위한 실험 장치**로 보는 것이 맞다.

효과가 있을 수 있는 경우:

- L2I와 L2D가 둘 다 크다.
- L2I share가 25~30% 이상으로 높다.
- data도 충분히 커서 instruction line이 data line을 밀어낼 여지가 있다.
- L2C/LLC에서 I/D miss, hit, prefetch usefulness가 동시에 의미 있게 나온다.

이 기준에서는 `sierra.a.6`, `sierra.a.4`, `sierra.a.3`, `tango`가 후보가 된다.

반대로 효과가 작을 가능성이 큰 경우:

- `whiskey`처럼 L2D가 압도적으로 크고 L2I share가 거의 없는 경우. 이 경우 instruction/data partition을 해도 instruction 쪽을 조절해서 얻을 것이 적다.
- `delta`, `arizona`처럼 IPC gain을 막는 원인이 L2C I/D 간섭보다 backend/decode pressure 또는 낮은 L1I headroom에 가까운 경우.
- `charlie`처럼 L2D는 크지만 L2I share가 낮은 경우. data 보호는 의미가 있을 수 있지만, instruction/data 균형 조절 효과는 제한적일 수 있다.

나눴을 때 기대할 수 있는 방향은 두 가지다.

1. **Data 보호 partition**
   - instruction prefetch/line이 data line을 밀어내는 것을 막는다.
   - L2D MPKI 또는 L2D miss latency가 줄면 성공이다.
   - 단점은 L2I/FF-L1I가 다시 늘어 IPC가 떨어질 수 있다는 점이다.

2. **Instruction 보호 partition**
   - instruction line을 더 오래 보존해서 frontend miss를 줄인다.
   - `sierra.a.4`처럼 frontend-limited workload에서는 IPC가 더 좋아질 수 있다.
   - 단점은 data miss가 늘어날 수 있다는 점이다.

따라서 좋은 실험은 단순히 L2C를 반반으로 나누는 것이 아니라, 여러 비율을 sweep하는 것이다.

- shared baseline
- I:D = 25:75
- I:D = 50:50
- I:D = 75:25
- optional: dynamic partitioning 또는 insertion priority 조절

성공 여부는 `IPC` 하나만 보면 부족하다. 같이 봐야 할 지표:

- L2I/L2D MPKI
- L2I/L2D miss latency
- L2C victim origin: instruction line이 data를 밀어냈는가, data line이 instruction을 밀어냈는가
- L2C MSHR occupancy / queue occupancy
- instruction/data prefetch useful/useless
- FF-L1I, FF-Decode, BF-ROB

현재 판단: **I/D partitioning 실험은 해볼 가치가 있다.** 다만 기대 후보는 `sierra.a.*`와 `tango`이고, `whiskey`는 오히려 data-dominant control case로 두는 것이 좋다. `whiskey`에서 partitioning이 좋아진다면 L2I/L2D 비율 때문이 아니라 data 보호 또는 latency 개선 때문일 가능성이 크다.

## 구현 계획: sierra.a.6 전용 trace와 L2C I/D static partition

첫 실험 대상은 `sierra.a.6`으로 잡았다. 이유는 L2I share가 37.5%로 가장 높고, L2D MPKI도 12.88로 충분히 커서 L2C I/D 간섭을 관찰하기 좋은 후보이기 때문이다.

구현 방향:

- `traces/trace_gtrace_sierra.a.6.txt`를 추가해서 `sierra.a.6` trace 18개만 실행할 수 있게 한다.
- `ChampSim_FDIP/champsim_config.json`의 `L2C`에 partition 설정을 추가한다.
  - `"partition": "static"`
  - `"instruction_ways": 4`
  - `"data_ways": 4`
- `partition`이 `"shared"`이면 기존 L2C와 동일하게 동작한다.
- `partition`이 `"static"`이면 L2C 8-way set을 instruction-origin fill과 data-origin fill이 서로 다른 way 범위에 채우도록 제한한다.

현재 구현은 물리적으로 L2C cache 객체를 두 개 만드는 방식이 아니라, **하나의 L2C 안에서 way partition을 적용하는 방식**이다. 따라서 L2C latency, queue, MSHR 등은 공유하고, capacity victim 선택만 I/D로 분리한다. 이 방식이 지금 연구 질문, 즉 "같은 L2C capacity 안에서 instruction/data line이 서로 밀어내는가"를 보기에는 더 직접적이다.

예상 실행:

```bash
./scripts/run.sh -b -t -T trace_gtrace_sierra.a.6.txt -f a -r sierra_a6_l2c_id_partition
./scripts/run.sh -s 0x3f -T trace_gtrace_sierra.a.6.txt -f a -r sierra_a6_l2c_id_partition
```

비교를 위해서는 같은 trace list로 `partition: "shared"` 설정도 한 번 돌려야 한다. 두 run을 비교해서 `IPC`, `L2I/L2D MPKI`, `L2I/L2D miss latency`, `pf_useful/pf_useless(I/D)`, `FF-L1I`, `FF-Decode` 변화를 확인한다.

## 실험 결과: sierra.a.6, FDIP off, L2C I:D way partition sweep

`sierra.a.6` trace 18개만 대상으로 `-f 0`(FDIP off) 상태에서 L2C shared baseline과 static partition 2:6, 4:4, 6:2를 비교했다.

명령 형태:

```bash
./scripts/run.sh -b -t -T trace_gtrace_sierra.a.6.txt -f 0 -r sierra_a6_l2c_shared_ftq0 -p 16
./scripts/run.sh -s 0x21 -T trace_gtrace_sierra.a.6.txt -f 0 -r sierra_a6_l2c_shared_ftq0

./scripts/run.sh -b -t -T trace_gtrace_sierra.a.6.txt -f 0 -r sierra_a6_l2c_<ratio>_ftq0 -p 16
./scripts/run.sh -s 0x21 -T trace_gtrace_sierra.a.6.txt -f 0 -r sierra_a6_l2c_<ratio>_ftq0
```

결과:

| Policy | IPC | L1I MPKI | L1D MPKI | L2C MPKI | L2I MPKI | L2D MPKI | LLC MPKI | LLI MPKI | LLD MPKI | OffChip | FF-L1I% | NoFetch% | FF-Dec% | BF-ROB% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| shared | 0.5794 | 60.31 | 26.94 | 37.66 | 26.61 | 13.26 | 17.54 | 10.43 | 8.15 | 24.34 | 35.90 | 43.88 | 5.68 | 5.79 |
| 2:6 | 0.5811 | 60.42 | 26.71 | 43.20 | 35.57 | 10.17 | 17.54 | 10.43 | 8.15 | 24.34 | 37.69 | 42.11 | 5.62 | 5.72 |
| 4:4 | 0.5837 | 60.12 | 26.86 | 34.46 | 23.99 | 12.49 | 17.54 | 10.43 | 8.14 | 24.35 | 35.65 | 44.08 | 5.62 | 5.74 |
| 6:2 | 0.5826 | 60.29 | 27.05 | 32.80 | 17.96 | 16.77 | 17.54 | 10.43 | 8.14 | 24.35 | 33.83 | 45.91 | 5.58 | 5.72 |

shared 대비 변화:

| Policy | IPCΔ | L2IΔ | L2DΔ | L2CΔ | FF-L1IΔ | NoFetchΔ |
|---|---:|---:|---:|---:|---:|---:|
| shared | +0.00% | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 |
| 2:6 | +0.30% | +8.95 | -3.09 | +5.54 | +1.78 | -1.77 |
| 4:4 | +0.75% | -2.62 | -0.77 | -3.20 | -0.25 | +0.20 |
| 6:2 | +0.55% | -8.65 | +3.51 | -4.85 | -2.07 | +2.03 |

해석:

- static partition은 shared보다 IPC가 모두 조금 좋다.
  - 2:6: +0.30%
  - 4:4: +0.75%
  - 6:2: +0.55%
  - 차이는 작지만, `sierra.a.6`에서는 shared보다 static partition이 약간 유리하게 나온다.
- partition 비율은 L2I/L2D trade-off를 명확히 만든다.
  - I way를 줄인 2:6은 L2D가 좋아진다(12.49 -> 10.17) 대신 L2I가 크게 나빠진다(23.99 -> 35.57).
  - I way를 늘린 6:2는 L2I가 좋아진다(23.99 -> 17.96) 대신 L2D가 크게 나빠진다(12.49 -> 16.77).
- IPC는 4:4가 가장 좋지만 차이는 작다.
  - shared 대비 4:4가 +0.75%로 가장 좋다.
  - 6:2는 L2I를 가장 많이 줄이지만 L2D가 늘어서 4:4보다 낮다.
  - 2:6은 L2D를 가장 많이 줄이지만 L2I가 크게 늘어서 4:4보다 낮다.
- LLC/OffChip은 거의 변하지 않는다.
  - L2C 내부의 I/D victim 선택은 L2I/L2D MPKI를 바꾸지만, 이 짧은 실험에서는 하위 LLC/off-chip pressure까지 크게 바꾸지는 않았다.
- `FF-L1I%`는 I way가 많을수록 줄어든다.
  - 2:6: 37.69%
  - 4:4: 35.65%
  - 6:2: 33.83%
- 하지만 I way를 늘리면 `NoFetch%`가 증가한다.
  - 이것은 L2I 개선이 그대로 IPC로 이어지지 않고, data-side 또는 다른 pipeline 흐름에 막히는 신호일 수 있다.

현재 결론:

**sierra.a.6에서는 L2C I/D partition이 실제로 L2I와 L2D 사이의 trade-off를 만든다.** 따라서 I/D 간섭 자체는 존재한다고 볼 수 있다. shared baseline까지 포함하면 static 4:4가 가장 좋고, shared보다 약 +0.75% IPC 개선이 있다. 다만 개선폭이 작기 때문에 더 긴 instruction count와 다른 후보 trace에서도 재현되는지 확인해야 한다.

## 실행 방식 개선: L2C partition별 multi-binary 실행

긴 실험은 `-w 2000000 -i 10000000`으로 다시 수행하기로 했다. 다만 기존 방식은 partition 비율을 바꿀 때마다 `champsim_config.json`을 수정하고 `-b`로 새로 빌드한 뒤 실행하는 구조였다. 이 방식은 shared, 2:6, 4:4, 6:2를 순서대로 직렬 실행하게 되어 전체 실험 시간이 길어지고, 여러 설정을 섞어 병렬 실행하기 어렵다.

따라서 `scripts/run.sh`를 다음 구조로 바꾸기로 했다.

- `-b` 단계에서는 L2C partition 선택 mask와 무관하게 L2C partition별 binary 4개를 모두 생성한다.
  - `bin/champsim_l2cshared`
  - `bin/champsim_l2c2i6d`
  - `bin/champsim_l2c4i4d`
  - `bin/champsim_l2c6i2d`
- 실행할 L2C partition은 `-L2C` bitmap 옵션으로 선택한다.
  - `-L2C 0x1`: shared
  - `-L2C 0x2`: 2:6
  - `-L2C 0x4`: 4:4
  - `-L2C 0x8`: 6:2
  - `-L2C 0xf`: shared, 2:6, 4:4, 6:2 전체
- 실행 job은 `(L2C policy, FTQ size, trace)` 단위로 만든다.
  - 따라서 `-L2C 0xf -p 16`처럼 실행하면 네 가지 L2C partition의 trace들이 한 번에 섞여서 16개 병렬 슬롯을 공유한다.
- 결과 저장 경로도 policy를 포함하도록 변경한다.
  - 기존: `raw/fdip_#/trace_set/group/...`
  - 변경: `raw/fdip_#/shared/trace_set/group/...`
  - 변경: `raw/fdip_#/2i6d/trace_set/group/...`
  - 변경: `raw/fdip_#/4i4d/trace_set/group/...`
  - 변경: `raw/fdip_#/6i2d/trace_set/group/...`
- 결과 파일명에도 policy를 추가한다.
  - 예: `...-1core-ftq0-shared---sierra.a.6_0000.champsim.gz.log`
  - 예: `...-1core-ftq0-2i6d---sierra.a.6_0000.champsim.gz.log`
- summary도 policy별로 저장한다.
  - `summary/fdip_0/shared/metrics.csv`
  - `summary/fdip_0/2i6d/metrics.csv`
  - `summary/fdip_0/4i4d/metrics.csv`
  - `summary/fdip_0/6i2d/metrics.csv`

현재 긴 실험은 우선 shared와 2:6까지만 진행한다. 이후 4:4, 6:2는 같은 run 구조로 추가 실행할 수 있다.

예상 명령:

```bash
# L2C binary 4개를 모두 빌드하고, shared + 2:6만 같은 병렬 pool에서 실행
./scripts/run.sh -b -t -T trace_gtrace_sierra.a.6.txt -f 0 -L2C 0x3 -w 2000000 -i 10000000 -r sierra_a6_long_l2c_ftq0 -p 16

# shared + 2:6 summary 생성
./scripts/run.sh -s 0x21 -T trace_gtrace_sierra.a.6.txt -f 0 -L2C 0x3 -r sierra_a6_long_l2c_ftq0
```

## 긴 실험 결과: sierra.a.6, FDIP off, L2C I:D partition sweep

사용자가 직접 `260713_2013_l2c_test` run을 실행했다. 조건은 다음과 같다.

- trace: `trace_gtrace_sierra.a.6.txt`
- FDIP: off (`-f 0`)
- L2C policy: `-L2C 0xf`
  - shared
  - 2:6
  - 4:4
  - 6:2
- warmup: 2,000,000
- simulation: 10,000,000
- parallelism: `-p 50`

실행 결과는 네 policy 모두 18개 trace가 정상 완료되었다.

```bash
./scripts/run.sh -s 0x21 -T trace_gtrace_sierra.a.6.txt -f 0 -L2C 0xf -r 260713_2013_l2c_test
```

결과:

| Policy | OK | IPC | L1I MPKI | L1D MPKI | L2C MPKI | L2I MPKI | L2D MPKI | LLC MPKI | LLI MPKI | LLD MPKI | OffChip | FF-L1I% | NoFetch% | BackendFull% | BF-ROB% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| shared | 18/18 | 0.432072 | 59.33 | 20.79 | 30.08 | 18.27 | 11.81 | 9.92 | 2.43 | 7.49 | 13.84 | 29.70 | 56.81 | 5.53 | 5.51 |
| 2:6 | 18/18 | 0.424528 | 59.54 | 20.61 | 40.57 | 31.60 | 8.97 | 9.88 | 2.34 | 7.54 | 13.86 | 33.49 | 53.18 | 5.49 | 5.46 |
| 4:4 | 18/18 | 0.432111 | 59.15 | 20.75 | 29.43 | 18.43 | 10.99 | 10.05 | 2.56 | 7.49 | 14.01 | 30.51 | 56.01 | 5.53 | 5.51 |
| 6:2 | 18/18 | 0.434161 | 59.33 | 21.01 | 25.75 | 10.96 | 14.79 | 10.08 | 2.64 | 7.44 | 13.98 | 27.29 | 59.16 | 5.56 | 5.55 |

shared 대비 변화:

| Policy | IPCΔ | L2IΔ | L2DΔ | L2CΔ | LLCΔ | LLIΔ | LLDΔ | OffChipΔ | FF-L1IΔ | NoFetchΔ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| shared | +0.00% | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 |
| 2:6 | -1.75% | +13.33 | -2.84 | +10.49 | -0.04 | -0.09 | +0.05 | +0.03 | +3.79 | -3.63 |
| 4:4 | +0.01% | +0.16 | -0.81 | -0.65 | +0.14 | +0.13 | +0.00 | +0.18 | +0.81 | -0.80 |
| 6:2 | +0.48% | -7.31 | +2.98 | -4.33 | +0.16 | +0.21 | -0.05 | +0.14 | -2.42 | +2.35 |

해석:

- 긴 run에서는 짧은 100k/100k 실험과 달리 **6:2가 가장 좋은 IPC**를 보였다.
  - shared 대비 +0.48%.
  - 4:4는 shared와 거의 동일하다(+0.01%).
  - 2:6은 -1.75%로 명확히 나쁘다.
- 2:6은 data way를 많이 줘서 L2D MPKI를 낮춘다.
  - L2D: 11.81 -> 8.97 (`-2.84`)
  - 하지만 L2I가 18.27 -> 31.60 (`+13.33`)으로 크게 나빠진다.
  - 이때 FF-L1I%도 +3.79%p 증가하고 IPC가 떨어진다.
  - 즉 `sierra.a.6`에서는 instruction side를 2-way로 제한하는 것이 너무 공격적이다.
- 6:2는 instruction way를 많이 줘서 L2I와 frontend stall을 줄인다.
  - L2I: 18.27 -> 10.96 (`-7.31`)
  - FF-L1I%: 29.70 -> 27.29 (`-2.42%p`)
  - 대신 L2D는 11.81 -> 14.79 (`+2.98`)로 나빠진다.
  - 그럼에도 IPC는 +0.48% 개선된다.
  - 따라서 이 workload에서는 data miss 증가보다 instruction miss 감소의 이득이 조금 더 크다.
- 4:4는 균형형이지만 shared 대비 거의 변화가 없다.
  - L2D는 약간 좋아지지만 L2I는 거의 동일하다.
  - IPC도 사실상 동일하다.
- LLC/OffChip 변화는 작다.
  - L2C 내부 I/D partition은 L2I/L2D MPKI를 크게 바꾸지만, 이번 조건에서는 하위 LLC/off-chip traffic까지 강하게 바꾸지는 않는다.

현재 결론:

**sierra.a.6에서는 L2C 내부에서 I/D capacity trade-off가 실제로 존재한다.** 다만 최적 방향은 data 보호가 아니라 instruction 보호 쪽에 가깝다. 특히 2:6은 L2D를 개선하지만 L2I를 너무 악화시켜 IPC가 떨어진다. 반대로 6:2는 L2D를 희생하지만 L2I와 FF-L1I를 줄여 IPC를 가장 좋게 만든다. 이는 `sierra.a.6`이 L2C data pressure보다 instruction-fetch pressure에 더 민감한 workload라는 근거가 된다.

### 자세한 해석

이 결과에서 가장 먼저 봐야 할 점은 `L1I MPKI`가 네 policy 사이에서 거의 변하지 않는다는 점이다.

- shared: 59.33
- 2:6: 59.54
- 4:4: 59.15
- 6:2: 59.33

즉 L2C partition은 L1I miss 자체를 크게 바꾸지는 않는다. 대신 **L1I에서 miss가 난 instruction fetch가 L2C에서 얼마나 잘 잡히는지**를 바꾼다. 이것이 `L2I MPKI`에 나타난다.

- shared: 18.27
- 2:6: 31.60
- 4:4: 18.43
- 6:2: 10.96

따라서 `sierra.a.6`의 문제는 "L1I miss가 발생하느냐"보다, **그 miss가 L2C에서도 miss가 되어 더 긴 latency를 만들고 frontend stall로 이어지느냐**에 더 가깝다. 6:2는 instruction line을 L2C에 더 오래 남겨서 L2I miss를 줄인다. 그 결과 `FF-L1I%`도 줄어든다.

- shared FF-L1I: 29.70%
- 6:2 FF-L1I: 27.29%
- 변화: -2.42%p

반대로 2:6은 data line을 보호한다. 이 정책은 L2D MPKI를 줄이는 데는 성공했다.

- shared L2D: 11.81
- 2:6 L2D: 8.97
- 변화: -2.84

하지만 이득보다 손실이 더 컸다. instruction way를 2개로 제한하면서 L2I MPKI가 18.27에서 31.60으로 급증했다. 이 변화는 L2D 개선폭보다 훨씬 크고, `FF-L1I%`도 29.70%에서 33.49%로 증가했다. 결과적으로 IPC는 -1.75% 하락했다.

이것은 중요한 신호다. **data 쪽 MPKI를 줄이는 것이 항상 IPC 개선으로 이어지지 않는다.** 특히 이 workload에서는 data miss를 줄이는 것보다 instruction fetch miss latency를 줄이는 것이 더 중요하다.

또 하나 볼 점은 `NoFetch%`다.

- shared: 56.81%
- 2:6: 53.18%
- 6:2: 59.16%

6:2에서는 `FF-L1I%`가 줄지만 `NoFetch%`는 증가한다. 이것은 instruction miss stall이 줄어들면서 frontend가 다른 형태의 fetch 제한을 더 자주 드러내는 것으로 볼 수 있다. 즉 6:2가 모든 frontend 문제를 없앤 것은 아니다. 다만 L2I miss로 인한 stall을 줄인 효과가 data miss 증가보다 커서 IPC가 조금 좋아졌다.

LLC와 OffChip 변화가 작다는 점도 중요하다.

- LLC MPKI는 shared 9.92, 6:2 10.08로 큰 변화가 없다.
- OffChip도 shared 13.84, 6:2 13.98로 거의 같다.

따라서 이번 효과는 "메모리까지 내려가는 트래픽을 크게 줄여서 좋아졌다"라기보다는, **L2C 내부에서 instruction/data line의 자리 배분이 바뀌면서 L2I와 L2D miss 위치가 재분배된 효과**에 가깝다. 즉 L2C capacity allocation 자체가 관측 가능한 영향을 만든다.

정리하면 다음과 같다.

1. `sierra.a.6`은 L2C에서 instruction/data 간 capacity trade-off가 보이는 workload다.
2. 하지만 이 workload의 최적 방향은 data 보호가 아니라 instruction 보호다.
3. 2:6은 L2D를 줄이지만 L2I를 너무 크게 늘려 손해다.
4. 6:2는 L2D를 늘리지만 L2I와 FF-L1I를 줄여 이득이다.
5. LLC/OffChip이 거의 변하지 않으므로, 효과의 주 무대는 L2C 내부다.

다음 단계에서는 이 해석을 더 강하게 검증하기 위해 다음 지표를 추가로 보는 것이 좋다.

- L2C victim이 instruction line인지 data line인지
- L2C hit latency 또는 miss latency의 I/D 분리
- L2C MSHR occupancy의 I/D 분리
- L2C prefetch useful/useless의 I/D 분리
- 같은 실험을 `sierra.a.4`, `tango`, `whiskey`에 적용했을 때 방향성이 유지되는지
