# ChampSim 로그 분석 가이드

`scripts/run.sh -t`로 실행한 raw 로그(`outputs/<run id>/raw/fdip_<num>/...`)에는 캐시/TLB 레벨별로 다음과 같은 표가 찍힌다.

```text
cpu0->LLC TOTAL        ACCESS:      51831 HIT:      15464 MISS:      36367 MSHR_MERGE:       1653
cpu0->LLC LOAD         ACCESS:       6694 HIT:        871 MISS:       5823 MSHR_MERGE:        388
cpu0->LLC RFO          ACCESS:      15083 HIT:         11 MISS:      15072 MSHR_MERGE:          0
cpu0->LLC PREFETCH     ACCESS:      14153 HIT:        275 MISS:      13878 MSHR_MERGE:       1265
cpu0->LLC WRITE        ACCESS:      14323 HIT:      14279 MISS:         44 MSHR_MERGE:          0
cpu0->LLC TRANSLATION  ACCESS:       1578 HIT:         28 MISS:       1550 MSHR_MERGE:          0
```

이 문서는 이 표에서 `TOTAL` 아래 각 줄(`LOAD`/`RFO`/`PREFETCH`/`WRITE`/`TRANSLATION`)이 **어떤 상황에서 생기는 접근인지**를 정리한다. HIT/MISS/MSHR_MERGE 자체의 의미(맞았다/틀렸다/합쳐졌다)는 설명하지 않는다 — 여기서 다루는 건 "이 줄에 왜 숫자가 찍히는가"다.

## 전체 트래픽 흐름

```text
L1I --(LOAD: demand fetch, PREFETCH: FDIP)--> L2C --> LLC --> MEM
L1D --(LOAD: load 명령어, WRITE: store 명령어, PREFETCH: ip_stride)--> L2C --> LLC --> MEM
ITLB --(LOAD)--> STLB --> PTW --(TRANSLATION)--> L1D --> L2C --> LLC --> MEM
DTLB --(LOAD)--> STLB --> PTW --(TRANSLATION)--> L1D --> L2C --> LLC --> MEM
```

L1I/L1D가 위 레벨에서 miss한 트래픽만 L2C로 내려가고, L2C에서도 miss한 것만 LLC로 내려간다 — 즉 아래 레벨로 갈수록 "위에서 다 걸러지고 miss한 것만 남은" 트래픽이라는 점이 핵심이다.

## cpu0_L1I (명령어 캐시)

- **LOAD**: 코어가 다음 명령어를 가져오려는 demand fetch. 매 fetch 시도가 여기 찍힌다.
- **RFO**: 항상 0. L1I는 쓰기(store)를 아예 하지 않는다.
- **PREFETCH**: FDIP가 앞으로 필요할 것으로 예측해 미리 당겨오는 명령어 prefetch.
- **WRITE**: 항상 0. 명령어 캐시 라인은 dirty가 될 수 없어서 writeback도 없다.
- **TRANSLATION**: 항상 0. L1I 자신은 주소 변환 요청을 처리하지 않는다 (ITLB가 별도로 담당).

## cpu0_L1D (데이터 캐시)

- **LOAD**: load 명령어의 데이터 읽기 demand 요청.
- **RFO**: 항상 0. RFO는 L1D가 miss해서 **하위 레벨로 내려갈 때만** 생기는 타입이라, L1D 자신이 RFO 요청을 받는 일은 없다.
- **PREFETCH**: L1D 자체 prefetcher(`ip_stride`)가 쏘는 데이터 prefetch.
- **WRITE**: store 명령어의 쓰기 시도. hit이면 그 자리에서 dirty 처리하고 끝나고, miss면 RFO로 변환되어 L2C로 나간다 — 이 ACCESS 수치는 "L1D에서 시도된 store 전체"를 센 것이다.
- **TRANSLATION**: PTW(page table walker)가 페이지 테이블 엔트리를 읽으러 오는 트래픽. STLB까지 miss나서 PTW가 동작하면, PTW의 최종 목적지가 L1D라서 여기에 찍힌다 (명령어/데이터 요청과는 무관한 별도 트래픽).

## cpu0_L2C (공유 L2)

- **LOAD**: L1I의 LOAD miss + L1D의 LOAD miss가 섞여서 올라온 것. (이 둘을 구분하려고 만든 게 이번에 추가한 `LOAD_I`/`LOAD_D` 분리 통계다.)
- **RFO**: L1D의 store가 L1D에서 miss해서 RFO로 변환되어 온 것. L2C 자신은 RFO를 만들어내지 않고, L1D에서 이미 변환된 것만 받는다.
- **PREFETCH**: L1I의 FDIP prefetch miss + L1D의 prefetch miss + **L2C 자신의 `ip_stride` prefetcher가 스스로 쏘는 prefetch**, 이 셋이 섞인다. 다른 타입과 달리 PREFETCH는 L2C 자체적으로도 발생시키는 유일한 타입이다.
- **WRITE**: L1D가 dirty line을 축출(evict)해서 내려보낸 writeback.
- **TRANSLATION**: L1D가 처리하던 PTW 트래픽이 L1D에서도 miss해서 넘어온 것.

## LLC (공유 최하위 캐시)

- **LOAD**: L2C의 LOAD miss.
- **RFO**: L2C의 RFO miss (= L1D의 store가 L1D도, L2C도 둘 다 miss한 경우).
- **PREFETCH**: L2C의 PREFETCH miss. 원인이 L1I든 L1D든 L2C 자체 prefetcher든 상관없이, L2C에서 한 번 더 miss난 것만 여기로 온다.
- **WRITE**: L2C가 dirty line을 축출해서 내려보낸 writeback.
- **TRANSLATION**: L2C의 TRANSLATION miss (PTW 트래픽이 L1D도 L2C도 둘 다 miss한 경우).

## cpu0_ITLB / cpu0_DTLB

- **LOAD**: 각각 명령어 fetch / 데이터 접근 전에 필요한 가상→물리 주소 변환 요청. TLB 요청은 항상 `access_type::LOAD`로 만들어진다.
- **RFO / PREFETCH / WRITE / TRANSLATION**: 항상 0. TLB는 주소 변환 조회만 하지 자기 스스로 store를 하거나 prefetch를 만들지 않는다.

## cpu0_STLB (ITLB/DTLB가 공유하는 2차 TLB)

- **LOAD**: ITLB miss + DTLB miss가 합쳐져서 올라온 것. 둘 다 LOAD 타입으로 온다.
- **나머지**: 항상 0 (ITLB/DTLB와 같은 이유).

## 참고: PREFETCH REQUESTED / ISSUED / USEFUL / USELESS 줄

```text
cpu0->cpu0_L2C PREFETCH REQUESTED:      15531 ISSUED:      15531 USEFUL:       7095 USELESS:        326
```

이 줄은 위의 ACCESS/HIT/MISS 표와 성격이 다르다 — "이 캐시 **자신의** prefetcher가 얼마나 활동했는지"를 나타내는 지표다.

- **REQUESTED**: prefetcher가 예측해서 요청한 횟수.
- **ISSUED**: 그중 실제로 prefetch queue에 들어가서 발행된 횟수 (큐가 꽉 차 있으면 REQUESTED보다 작을 수 있다 — 예: `cpu0_L1D REQUESTED: 92473 ISSUED: 48371`).
- **USEFUL**: 그 prefetch가 나중에 실제 demand 요청에 의해 사용된 횟수.
- **USELESS**: prefetch된 라인이 한 번도 안 쓰이고 축출된 횟수.

이 값은 각 캐시가 **직접 발행한** prefetch에 대한 것이라, 상위 레벨에서 miss해서 내려온 PREFETCH 타입 트래픽(위 ACCESS/HIT/MISS 표의 `PREFETCH` 줄)과는 별개다. 이 실험 설정에서는 ITLB/DTLB/STLB/LLC에 prefetcher가 꺼져 있어서 전부 0으로 찍힌다.

### REQUESTED/ISSUED와 hit/miss/USEFUL/USELESS는 타이밍이 다르다

`REQUESTED`/`ISSUED`는 prefetcher가 "이 주소를 prefetch하자"고 **결정한 시점**에 곧바로 집계된다 — 그 요청이 나중에 실제로 hit할지 miss할지는 아직 모르는 상태다. hit/miss는 그 요청이 큐에서 뽑혀서 실제로 tag check를 받는 **다음 사이클 이후**에 결정되는 별개의 이벤트다.

```cpp
bool CACHE::prefetch_line(...)
{
  ++sim_stats.pf_requested;         // prefetcher가 요청을 결정한 순간, 무조건 카운트
  if (PQ 꽉참) return false;         // 여기서 실패하면 ISSUED는 못 늘어남
  internal_PQ.emplace_back(...);
  ++sim_stats.pf_issued;            // PQ에 들어가면 카운트 (아직 hit/miss 모름!)
  ...
}
// tag check(hit/miss 판정)는 이 함수가 끝난 뒤, 나중 사이클에 따로 일어난다.
```

| 결과 | REQUESTED | ISSUED | ACCESS/HIT/MISS 표 | USEFUL/USELESS |
|---|---|---|---|---|
| PQ가 꽉 차서 못 나감 | ✅ | ❌ | 안 잡힘 | 해당 없음 |
| 나가서 tag check했더니 **hit** (이미 캐시에 있었음) | ✅ | ✅ | `PREFETCH HIT`로 잡힘 | 둘 다 ❌ (그냥 끝) |
| 나가서 tag check했더니 **miss** (진짜로 fetch 진행) | ✅ | ✅ | `PREFETCH MISS`로 잡힘 | 나중에 **USEFUL**(demand가 써먹음) 또는 **USELESS**(안 쓰이고 축출) 둘 중 하나로 갈릴 수 있음 |

즉 **REQUESTED/ISSUED는 hit/miss 결과와 무관하게 항상 잡힌다.** "이미 캐시에 있는 걸 prefetch하려 한" 경우는 `PREFETCH ACCESS`/`PREFETCH HIT`에는 잡히지만(낭비된 PQ 슬롯 하나 쓴 hit), `USEFUL`/`USELESS` 어느 쪽에도 잡히지 않고 조용히 끝난다 — `USEFUL`은 "예전에 깔아둔 prefetch 라인을 나중에 진짜 demand 요청이 와서 잡아먹었을 때"만 세는 지표라서, prefetch 요청 자신이 즉시 hit한 경우는 그 정의에 해당하지 않기 때문이다(`useful_prefetch = (hit && way->prefetch && !handle_pkt.prefetch_from_this)`에서 자기 자신이 쏜 요청은 `prefetch_from_this == true`라 조건이 성립하지 않는다). `USELESS`도 나중에 **축출될 때** "한 번도 안 쓰였다"를 판정하는 거라, 즉시 hit해서 fill 자체가 없었던 경우엔 해당되지 않는다.
