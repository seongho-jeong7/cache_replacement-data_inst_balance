# 2026-07-16 실험 노트: `latency_test` 장기 실행

이 문서는 2026-07-16에 `ChampSim_FDIP` 최신 commit 기준으로 새로 시작한 `latency_test` run의 실행 조건, 진행 상황, 오류를 기록한다.

## 배경

전날(07-15) `260714_2030_w20_i300_l2c_partition`가 100% 완료됐다. 이후 `ChampSim_FDIP`에 커밋이 더 쌓였다:

- `f6602de` "Bound PTW MSHR pressure" — `yankee_0012`/`0054`/`sierra.a.4_0014` 실패를 고친 커밋 (07-15 밤에 별도 워크트리에서 검증 완료).
- `c19adac` "Model L2C lookup latency by partition" — L2C partition별 lookup latency를 모델링하는 새 기능. 그리고 L2C 정책이 `1i7d`, `8i0d` 두 개 늘어서 이제 7개(`shared`/`0i8d`/`1i7d`/`2i6d`/`4i4d`/`6i2d`/`8i0d`)가 됐다.

이번 run은 **`ChampSim_FDIP` 최신 HEAD(`c19adac`, PTW fix 포함)** 로 새로 시작하고, 늘어난 L2C 정책 7개를 전부 포함한다. 다만 본 실행 전에 조건을 먼저 짧게(`w10`/`i20`) 검증해보기로 했다.

## 실행 조건

| 항목 | 값 |
|---|---|
| Run ID | `260716_1305_w10_i20_latency_test` |
| ChampSim_FDIP | 최신 HEAD (`c19adac`, `f6602de` PTW fix 포함) |
| Trace list | `trace_gtrace_l2c_test.txt` (8 그룹, 296 traces) — 07-14 run과 동일 |
| L2C 정책 | 전체 7개: `shared`, `0i8d`, `1i7d`, `2i6d`, `4i4d`, `6i2d`, `8i0d` (`-L2C 0x7f`) |
| FTQ | 전체 6개: `0`, `2`, `4`, `16`, `32`, `64` |
| warmup / simulation | `1,000,000` / `2,000,000` (=`w10`/`i20`, 이전 `w20_i300`보다 짧은 스모크 테스트) |
| 병렬도 | `-p 58` |
| 실행 방식 | 이전과 동일하게 2단계 분할: stage 1 `-f 0x15`(FTQ `0,4,32`), stage 2 `-f 0x2a`(FTQ `2,16,64`), `stage1 && stage2` 백그라운드 체이닝 |

빌드는 `-L2C 0x7f` 여부와 무관하게 `-b`가 항상 7개 policy 바이너리를 전부 만든다.

```bash
./scripts/run.sh -b -L2C 0x7f
```

## Stage 1

```bash
nohup bash -c '
./scripts/run.sh -t -T trace_gtrace_l2c_test.txt -L2C 0x7f -f 0x15 -w 1000000 -i 2000000 -p 58 -r 260716_1305_w10_i20_latency_test && \
./scripts/run.sh -t -T trace_gtrace_l2c_test.txt -L2C 0x7f -f 0x2a -w 1000000 -i 2000000 -p 58 -r 260716_1305_w10_i20_latency_test
' > /tmp/260716_1305_w10_i20_latency_test.log 2>&1 &
```

| 시작 | 종료 | 소요 시간 |
|---|---|---:|
| 2026-07-16 13:15:07 | 2026-07-16 14:56:11 | 약 1.68시간 (1시간 41분) |

(raw 로그 mtime 기준. 사전 추정치는 약 1.9시간이었다.)

job 수: 296 traces x 3 FTQ x 7 policy = 6,216.

결과:

- `shared`/`0i8d`/`1i7d`/`2i6d`/`4i4d`/`6i2d` (6개 정책): **5,328/5,328 (100%) 성공**.
- **`8i0d`: 888/888 (100%) 실패**.

## Stage 1 오류: `8i0d`에서 100% 재현되는 assertion 실패

`8i0d`(instruction 8 way / data 0 way)의 모든 job이 예외 없이 실패했다. 샘플 로그(`sierra.a.6_0004`, ftq0):

```
[cpu0_L2C_MSHR] finish_packet cannot find a matching entry! address: 0x321e892f0 v_address: 0x0
champsim_l2c8i0d: src/cache.cc:1346: void CACHE::finish_packet(const response_type&): Assertion `0' failed.
```

- `-p58`/`-p1` 재시도 없이도(실은 병렬 그대로) 888건 전부 동일한 assertion으로 실패해서, 특정 trace나 동시성 문제가 아니라 **`8i0d` 정책 자체에서 100% 재현되는 결정론적 버그**로 보인다.
- `data way = 0`인 극단 케이스라는 점에서, 이전에 고친 `0i8d`(`instruction way = 0`)의 PTW MSHR 버그와 대칭되는 반대편 극단 케이스로 추정된다. 다만 이번엔 증상이 다르다 (`std::bad_alloc`이 아니라 `finish_packet`의 MSHR 매칭 assertion) — 원인은 아직 코드 레벨로 확인 전이다.
- `c19adac`(L2C lookup latency by partition)가 이 assertion과 관련이 있는지도 아직 확인 전이다. `8i0d`가 이번에 처음 실행된 정책이라, "새 latency 모델링 코드 자체의 버그"인지 "`8i0d`처럼 한쪽 way가 0인 경우를 원래부터 처리 못 했던 기존 버그가 이번에 처음 노출된 것"인지 구분이 필요하다.

stage 1에 실패가 있었기 때문에 `stage1 && stage2` 체이닝이 이번에도 끊겼다(예상된 동작 — 07-15와 동일한 패턴). stage 2는 수동으로 다시 시작했다.

## Stage 2

```bash
nohup ./scripts/run.sh -t -T trace_gtrace_l2c_test.txt -L2C 0x7f -f 0x2a -w 1000000 -i 2000000 -p 58 -r 260716_1305_w10_i20_latency_test > /tmp/260716_1305_stage2.log 2>&1 &
```

2026-07-16 약 15:04경 PID `656473`로 시작.

| 시작 | 종료 | 소요 시간 |
|---|---|---:|
| 2026-07-16 15:33:00 | 2026-07-16 17:20:06 | 약 1.78시간 (1시간 47분) |

결과 (예상대로): `shared`/`0i8d`/`1i7d`/`2i6d`/`4i4d`/`6i2d`는 **5,328/5,328 (100%) 성공**, `8i0d`는 **888/888 (100%) 실패**(stage 1과 동일한 assertion).

`260716_1305_w10_i20_latency_test` 최종(stage1+stage2 합산): 6개 정책 **10,656/10,656 (100%) 성공**, `8i0d` **1,776/1,776 (100%) 실패**.

이 6개 정책 결과로 `docs/exp/2026_07_16_analysis.md`(0716 Anal.)를 stage1 기준 1차 작성했다 — `260714_2030`과 비교해서 dIPC 부호가 거의 다 뒤집힌 것, 그 이유가 way 기반 search latency 모델이라는 것, `6i2d`가 모든 trace에서 1등이 된 이유까지 정리함.

## `8i0d` 버그 원인과 수정

`ChampSim_FDIP`에 `8i0d` 버그를 고친 커밋이 새로 올라왔다.

```
15d240d "Fix L2C bypass response handling"
- Keep an L2C MSHR for bypassed demand/prefetch completions.
- Prevent lower-level responses from returning without a matching L2C MSHR.
- Mark bypassed writebacks as no-response requests.
- Fix 8i0d data bypass aborts without changing the original build artifacts.
```

`src/cache.cc` 8줄 변경. L2C를 bypass하는 요청(`8i0d`의 data, `0i8d`의 instruction)이 MSHR 엔트리 없이 lower-level 응답을 받으려다가 매칭 실패로 assertion에 걸리던 것을, bypass 요청도 MSHR을 하나 붙잡아두도록 고쳤다. 이전 세션 요약과 마찬가지로 "지금 도는 실험에 영향 안 가도록 원래 build artifact는 안 건드림"이 커밋 메시지에 명시돼 있다.

이번엔 다른 커밋이 섞일 걱정 없이(이미 최신 HEAD가 이 커밋 포함) 그냥 프로덕션 `ChampSim_FDIP`를 재빌드했다.

```bash
./scripts/run.sh -b -L2C 0x7f
```

`8i0d`만 6개 FTQ 전체로 재실행:

```bash
nohup ./scripts/run.sh -t -T trace_gtrace_l2c_test.txt -L2C 0x40 -f 0x3f -w 1000000 -i 2000000 -p 2 -r 260716_1305_w10_i20_latency_test > /tmp/260716_8i0d_rerun.log 2>&1 &
```

- job 수: 296 traces x 6 FTQ = 1,776.
- `-p 2`로 지정(사용자 요청 — 다른 백그라운드 작업과 리소스를 나눠 쓰기 위함으로 보임). `-p58` 기준 추정 약 35분이었지만, `-p2`로는 약 17.2시간 예상.
- 2026-07-16 17:31:40 시작, PID `738916`. 완료 예상: 2026-07-17 약 10:40경.

## `260716_1733_w20_i300_latency_test`: 정식 장기 실행 시작

`8i0d` 재실행과 별개로, 짧은 `w10/i20` 조건 검증이 끝났으니 `260714_2030`과 같은 길이(`w20`/`i300`)로 정식 장기 실행을 시작했다. `8i0d`가 이제 고쳐졌으므로 **7개 정책 전부** 포함한다.

| 항목 | 값 |
|---|---|
| Run ID | `260716_1733_w20_i300_latency_test` |
| ChampSim_FDIP | 최신 HEAD (`15d240d`, `8i0d` bypass fix 포함) |
| L2C 정책 | 전체 7개 (`-L2C 0x7f`, `8i0d` 포함) |
| warmup / simulation | `2,000,000` / `30,000,000` (=`w20`/`i300`, `260714_2030`과 동일 길이) |
| 병렬도 | `-p 56` |
| 실행 방식 | 동일하게 stage 1(`-f 0x15`, FTQ `0,4,32`) / stage 2(`-f 0x2a`, FTQ `2,16,64`) 2단계, `stage1 && stage2` 체이닝 |

```bash
nohup bash -c '
./scripts/run.sh -t -T trace_gtrace_l2c_test.txt -L2C 0x7f -f 0x15 -w 2000000 -i 30000000 -p 56 -r 260716_1733_w20_i300_latency_test && \
./scripts/run.sh -t -T trace_gtrace_l2c_test.txt -L2C 0x7f -f 0x2a -w 2000000 -i 30000000 -p 56 -r 260716_1733_w20_i300_latency_test
' > /tmp/260716_1733_w20_i300_latency_test.log 2>&1 &
```

- job 수: 296 traces x 3 FTQ x 7 policy = 6,216/stage, 총 12,432.
- 시간 추정: `260714_2030`의 실측치(4,440 jobs/stage, 5 policy, `-p58`, 약 15.35시간/stage → 12.45초/job)를 `-p56`·7-policy로 보정하면 stage당 약 22.3시간, 전체 약 44.5시간(약 1.85일).
- 2026-07-16 17:35:05 시작, PID `740508`.
- `8i0d`-only 재실행(PID `738916`, `-p2`)과 동시에 백그라운드에서 돌고 있다. 둘 다 이미 빌드된 같은 `ChampSim_FDIP/bin/` 바이너리를 읽기만 하므로 충돌 없음.

## 다음 계획 (07-16 시점)

- (완료) `8i0d` assertion 원인 파악 및 수정 — `15d240d`.
- `8i0d`-only 재실행이 끝나면(예상 07-17 약 10:40) `260716_1305_w10_i20_latency_test`가 7개 정책 전부 완성되고, `docs/exp/2026_07_16_analysis.md`를 6-FTQ x 7-policy 전체 기준으로 다시 작성한다.
- `260716_1733_w20_i300_latency_test`(정식 장기, 약 1.85일 소요 예상)가 끝나면 `260714_2030`과 같은 길이/조건으로 latency 모델링 효과를 다시 검증한다 — 이번엔 `8i0d`까지 포함한 7-정책 비교가 가능하다.

---

## 2026-07-17 진행 상황

### `8i0d` 재실행 완료

| 시작 | 종료 | 소요 시간 |
|---|---|---:|
| 2026-07-16 17:31:57 | 2026-07-17 11:17:51 | 약 17.76시간 |

- job 수: 296 traces x 6 FTQ = 1,776, `-p 2`(사전 추정 약 17.2시간과 거의 일치).
- 결과: **1,776/1,776 (100%) 성공**. 새로운 실패 없음 — 커밋 `15d240d`("Fix L2C bypass response handling")가 `8i0d` 문제를 완전히 해결한 것으로 확인됨.
- `260716_1305_w10_i20_latency_test`는 이제 **7개 정책 전부 완성**됐다. `docs/exp/2026_07_16_analysis.md`를 8-정책(`1i7d`, `8i0d` 포함) 기준으로 다시 갱신할 수 있는 상태.

### `260716_1733_w20_i300_latency_test` stage 1 완료, 새로운 실패 7건

| 시작 | 종료 | 소요 시간 |
|---|---|---:|
| 2026-07-16 17:42:57 | 2026-07-17 14:45:07 | 약 21.03시간 |

- job 수: 296 traces x 3 FTQ x 7 policy = 6,216.
- 결과: **6,209/6,216 (99.9%) 성공**, 실패 7건.

실패 상세 (전부 `exit 134`, `ftq=0`):

| Trace | Policy |
|---|---|
| yankee_0006 | shared |
| yankee_0054 | shared |
| yankee_0012 | shared |
| yankee_0012 | 0i8d |
| yankee_0027 | 1i7d |
| yankee_0057 | 1i7d |
| yankee_0012 | 8i0d |

**이전 실패들과 성격이 다르다.** `f6602de`(PTW MSHR)는 `4i4d`에서만, `15d240d`(L2C bypass)는 `8i0d`에서만 100% 재현되는 정책-특정 버그였는데, 이번엔:

- `shared`처럼 partition/bypass 로직과 무관한 정책에서도 실패한다.
- 실패한 정책이 `shared`/`0i8d`/`1i7d`/`8i0d`로 뒤섞여 있고 `2i6d`/`4i4d`/`6i2d`에서는 안 났다.
- 전부 `yankee` trace, 전부 `ftq=0`이라는 공통점은 있다.
- `yankee_0012`은 세 정책(`shared`, `0i8d`, `8i0d`)에서 각각 따로 실패했다 — 특정 trace 파일 자체의 문제일 가능성을 시사한다.

`w20/i300`처럼 긴 실행에서만 나타난다는 점에서, 원래 `f6602de`로 고쳤던 PTW MSHR 압박과 비슷한 종류(오래 걸리는 실행일수록 어떤 큐/구조가 누적되다 터지는 유형)일 가능성이 있지만, 이번엔 policy를 안 가리는 것으로 봐서 원인이 다를 수 있다. **원인 조사는 아직 안 했고, 별도 과제로 남겨둔다.**

stage 1에 실패가 있었으므로 이번에도 `stage1 && stage2` 체이닝이 끊겼다(예상된 패턴). stage 2는 수동으로 다시 시작했다.

```bash
nohup ./scripts/run.sh -t -T trace_gtrace_l2c_test.txt -L2C 0x7f -f 0x2a -w 2000000 -i 30000000 -p 56 -r 260716_1733_w20_i300_latency_test > /tmp/260716_1733_stage2.log 2>&1 &
```

2026-07-17 21:04:47 시작, PID `1194587`.

### 다음 계획 (07-17 시점)

- stage 2 완료를 기다린다(예상 약 21시간 뒤, 07-18 저녁경 — stage 1 실측 속도 기준).
- 새로 발견된 7건 실패(`yankee` + `ftq=0`, 정책 무관)의 원인을 조사한다. `f6602de`/`15d240d`처럼 정책 하나에 국한된 게 아니라서 접근 방식을 다시 생각해야 할 수 있다.
- `docs/exp/2026_07_16_analysis.md`를 `260716_1305`의 8-정책 전체 결과로 갱신한다(`1i7d`/`8i0d` 포함).
- `260716_1733_w20_i300_latency_test`가 끝나면(`8i0d` 포함 7정책, `260714_2030`과 같은 길이) 실행 길이 caveat 없이 latency 모델 비교를 완성한다.

---

## 2026-07-20: `260716_1733_w20_i300_latency_test` stage 2 완료 확인

대화가 며칠 비는 사이 stage 2도 이미 끝나 있었다. raw 로그 mtime 기준 실제 시각:

| Stage | 시작 | 종료 | 소요 시간 |
|---|---|---|---:|
| stage 1 | 2026-07-16 17:42:57 | 2026-07-17 14:45:07 | 21.03h |
| stage 2 | 2026-07-17 21:12:10 | 2026-07-18 19:11:58 | 21.99h |

즉 stage 2는 07-18 저녁에 이미 끝나 있었고(사전 추정과 거의 일치), 확인이 07-20 오후로 늦어졌을 뿐이다.

**최종 결과: 12,422 / 12,432 (99.92%) 성공, 실패 10건.**

실패 목록을 stage별로 정리(전부 `exit 134`):

**Stage 1 (7건, 전부 `ftq=0`)**

| Trace | Policy |
|---|---|
| yankee_0006 | shared |
| yankee_0054 | shared |
| yankee_0012 | shared |
| yankee_0012 | 0i8d |
| yankee_0027 | 1i7d |
| yankee_0057 | 1i7d |
| yankee_0012 | 8i0d |

**Stage 2 (3건, 전부 `ftq=2`)**

| Trace | Policy |
|---|---|
| delta_0000 | 6i2d |
| sierra.a.4_0014 | 6i2d |
| sierra.a.4_0014 | 8i0d |

**`sierra.a.4_0014`가 다시 나왔다** — 원래 `260714_2030`에서 `f6602de`(PTW MSHR)로 고쳤던 바로 그 trace인데, 이번엔 그때와 다른 정책(`6i2d`, `8i0d`)에서 재발했다. `yankee_0012`도 stage 1에서 세 정책(`shared`/`0i8d`/`8i0d`)에 걸쳐 반복 실패했다. 특정 policy 하나의 버그라기보다, **특정 trace 파일(`sierra.a.4_0014`, `yankee_0012` 등) 자체가 뭔가 pathological한 패턴을 갖고 있어서 여러 정책/여러 fix를 거쳐도 조건이 맞으면 계속 재발하는 것**으로 보인다. 아직 원인 조사는 안 했다.

### 다음 계획 (07-20 시점)

- 두 run(`260716_1305` 8-정책 전체, `260716_1733` 7-정책 x 6-FTQ, 실패 10건 결측) 모두 실질적으로 완료됐으므로 summary를 다시 생성한다.
- `sierra.a.4_0014`/`yankee_0012`처럼 여러 정책에 걸쳐 반복 재발하는 trace가 있는지 목록화해서, "policy별 버그"가 아니라 "trace별 pathological case"로 접근을 바꿔 원인을 조사한다.
- `docs/exp/2026_07_16_analysis.md`를 `260716_1305`(8-정책)와 `260716_1733`(7-정책, `260714_2030`과 같은 길이) 양쪽으로 갱신한다.

---

## 2026-07-21: 실패 10건 원인 수정 및 재실행 완료

`ChampSim_FDIP`에 이 10건을 겨냥한 패치 커밋이 새로 올라왔다.

```
df0f567 "Fix PTW MSHR completion move"
- Replace PTW MSHR partition/copy with scan-and-move completion.
- Move matching MSHR entries directly into finished/completed queues.
- Avoid large dependency-vector reallocations on long yankee traces.
- Preserve page-walk behavior while removing the bad_alloc failure path.
```

`src/ptw.cc`의 `PageTableWalker::finish_packet()`에서 MSHR 완료 처리를 `std::partition`/`std::partition_copy`(전체를 한 번에 분할·복사) 방식에서, 매칭되는 엔트리를 하나씩 순회하며 바로 `finished`/`completed` 큐로 `std::move`하는 방식으로 바꿨다. 긴 `yankee` trace에서 발생하던 큰 dependency-vector 재할당을 없애는 게 목적이라고 커밋 메시지에 명시돼 있다. 이번에도 원본 `ChampSim_FDIP`는 별도 빌드 없이 커밋만 반영된 상태였다(두 장기 실행이 이미 다 끝난 뒤라 실제로는 안전하게 바로 빌드해도 되는 시점이었다).

두 run 모두 이미 종료된 상태라 이번엔 격리 워크트리 없이 프로덕션 `ChampSim_FDIP`를 바로 재빌드했다.

```bash
./scripts/run.sh -b -L2C 0x7f
```

실패한 10건을 `(ftq, policy)` 조합별로 6개 그룹(같은 조합끼리 묶어서)으로 나눠 `260716_1733_w20_i300_latency_test`에 병렬로 재실행했다.

| 그룹 | FTQ | Policy | Trace |
|---|---:|---|---|
| 1 | 0 | shared | yankee_0006, yankee_0012, yankee_0054 |
| 2 | 0 | 0i8d | yankee_0012 |
| 3 | 0 | 1i7d | yankee_0027, yankee_0057 |
| 4 | 0 | 8i0d | yankee_0012 |
| 5 | 2 | 6i2d | delta_0000, sierra.a.4_0014 |
| 6 | 2 | 8i0d | sierra.a.4_0014 |

**10건 전부 정상 완료로 확인됐다.** `260716_1733_w20_i300_latency_test`가 이제 **12,432 / 12,432 (100%)** 완료 상태다. `df0f567`가 이 재발 실패의 실제 원인이었다는 것이 확인된 셈이다.

이후 두 run(`260716_1305`, `260716_1733`) 모두 summary를 재생성했고, `260716_1733` 결과는 `docs/exp/2026_07_21_analysis.md`에서 `260714_2030`과 같은 길이 기준 정식 비교로 분석했다.
