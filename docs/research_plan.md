# Research Plan: L2C I/D Partition and FDIP Interaction

## Current State

현재 연구 질문은 L2C를 instruction/data가 함께 사용할 때 서로 간섭이 발생하는지, 그리고 FDIP/FTQ가 이 간섭을 줄이거나 오히려 키우는지를 확인하는 것이다.

지금까지 구현한 핵심 실험 장치는 다음과 같다.

- L2C static I/D partition
  - `shared`
  - `0i8d`
  - `2i6d`
  - `4i4d`
  - `6i2d`
- FDIP FTQ size sweep
  - `ftq0`
  - `ftq2`
  - `ftq4`
  - `ftq16`
  - `ftq32`
  - `ftq64`
- trace group 기반 workload selection
  - 현재 L2C test set은 `bravo`, `delta`, `merced`, `sierra.a.4`, `sierra.a.6`, `tahoe`, `tango`, `yankee`로 구성한다.

아래 그림은 기존 5개 workload group(`bravo`, `sierra.a.3`, `sierra.a.4`, `sierra.a.6`, `tango`)에 대해 `shared` 대비 L2C policy 변화량을 보여준다.

```{image} image/l2c_delta_combined.png
:alt: L2C partition delta versus shared
:width: 100%
```

그림을 읽을 때 중요한 점은 다음과 같다.

- 파란색 `dIPC`가 최종 성능 변화다.
- 빨간 계열은 MPKI 변화다.
  - data block: `dL1D`, `dL2D`
  - instruction block: `dL1I`, `dL2I`
- 초록 계열은 stall 변화다.
  - data block: backend data stall
  - instruction block: frontend stall, backend instruction stall
- `0i8d`는 instruction을 L2C에 넣지 않고 LLC로 보내는 control policy다.

## Current Observation

가장 눈에 띄는 결과는 `FTQ=32`에서 `0i8d`가 여러 workload의 IPC를 크게 개선한다는 점이다.

- `tango`, `sierra.a.3`, `sierra.a.4`, `sierra.a.6`에서 `FTQ=32` + `0i8d` 조합의 IPC 개선이 크다.
- 이때 L2D MPKI가 감소하는 경향이 있다.
- 즉 instruction line을 L2C에서 제거하면 data line이 L2C capacity를 더 많이 사용할 수 있고, 이 data-side 이득이 IPC로 이어질 수 있다.

하지만 `0i8d`가 항상 좋은 것은 아니다.

- `FTQ=0`에서 `sierra.a.6`는 `0i8d` 적용 시 IPC가 크게 떨어진다.
- 이 경우 instruction이 L2C를 전혀 사용하지 못하면서 frontend stall이 증가한다.
- 따라서 "L2I를 그냥 없애면 된다"가 아니라, FTQ/FDIP가 instruction miss를 충분히 숨길 수 있는 상황에서만 L2C instruction bypass가 유리하다고 보는 것이 맞다.

현재 해석은 다음과 같다.

> FDIP가 충분히 강하면 instruction working set을 L2C에 보관하지 않아도 frontend 손실이 작아진다. 이때 L2C capacity를 data에 더 많이 주면 IPC가 개선될 수 있다. 반대로 FDIP가 약하거나 FTQ가 작으면 instruction을 L2C에서 제거하는 비용이 frontend stall로 바로 드러난다.

## Candidate Solutions

### 1. FTQ-Aware L2I Bypass

FTQ size 또는 FDIP effectiveness에 따라 L2C instruction bypass 여부를 바꾸는 방식이다.

- FTQ가 충분히 크면 instruction을 L2C에서 bypass한다.
- FTQ가 작거나 frontend stall이 크면 instruction을 L2C에 허용한다.

예상 정책:

```text
small FTQ  -> shared or 2i6d
large FTQ  -> 0i8d or data-favored policy
```

이 방식은 현재 그래프와 가장 직접적으로 맞는다. `FTQ=32`에서는 `0i8d`가 좋아 보이지만, `FTQ=0`에서는 위험하기 때문이다.

### 2. Dynamic I/D Way Partition

고정 partition 대신 runtime 지표를 보고 L2C way 비율을 바꾸는 방식이다.

- frontend stall 또는 L2I MPKI가 높으면 instruction way를 늘린다.
- L2D MPKI 또는 backend data stall이 높으면 data way를 늘린다.
- workload마다 최적점이 다르므로 static policy보다 유연하다.

가능한 입력 지표:

- L2I MPKI
- L2D MPKI
- frontend instruction fetch stall
- backend data stall
- FDIP coverage

### 3. Low-Priority Instruction Insertion

instruction line을 L2C에 넣기는 하지만 data보다 낮은 priority로 삽입하는 방식이다.

- data fill은 MRU에 가깝게 삽입한다.
- instruction fill은 LRU에 가깝게 삽입한다.
- instruction line이 data line을 오래 밀어내지 못하게 한다.

이 방식은 `0i8d`보다 부드럽다. instruction을 완전히 제거하지 않으므로 FTQ가 작을 때의 frontend 손실을 줄일 수 있다.

### 4. FDIP Prefetch-Only Bypass

모든 instruction access를 bypass하지 않고, FDIP가 만든 instruction prefetch만 L2C에서 bypass하는 방식이다.

- demand I-cache miss는 L2C에 저장한다.
- FDIP prefetch는 L2C를 bypass하거나 low-priority로 삽입한다.

이 방식이 특히 중요해 보인다. 현재 `0i8d`가 좋아 보이는 이유가 "instruction line이 전혀 필요 없다"가 아니라, "FDIP prefetch traffic이 L2C data capacity를 오염시킨다"일 수 있기 때문이다.

우선순위는 이 방향이 가장 높다.

### 5. Small Instruction Buffer Beside L2C

L2C main ways는 data 중심으로 두고, instruction은 별도 작은 buffer에 저장하는 방식이다.

- L2C data capacity를 보호한다.
- 반복되는 instruction miss 일부만 작은 buffer에서 흡수한다.
- 완전한 L2I split보다는 가벼운 구조다.

다만 구현 복잡도가 더 높으므로, 먼저 bypass/priority 정책을 확인한 뒤 검토하는 것이 좋다.

### 6. Set-Dueling Policy Selection

일부 set은 `0i8d`, 일부 set은 `shared` 또는 `2i6d`로 운영하고, 성능 proxy를 비교해 전체 정책을 선택하는 방식이다.

- workload별 최적 정책이 다를 때 유용하다.
- 고정 threshold보다 adaptive하다.
- proxy metric 설계가 중요하다.

## Next Plan

우선순위는 다음과 같다.

1. FDIP prefetch-only L2C bypass 구현
   - demand instruction은 L2C 허용
   - FDIP prefetch instruction은 L2C bypass
   - `0i8d`와 비교

2. Low-priority instruction insertion 구현
   - instruction fill을 LRU 쪽에 삽입
   - data fill은 기존 방식 유지
   - `0i8d`, `shared`, static partition과 비교

3. FTQ-aware bypass rule 실험
   - FTQ가 작을 때는 instruction L2C 허용
   - FTQ가 클 때는 instruction bypass
   - 우선은 static threshold로 시작

4. Dynamic partition 후보 지표 탐색
   - L2I/L2D MPKI
   - frontend stall
   - backend data stall
   - FDIP coverage

5. 확장 workload 실험
   - 기존 5개 group 결과로 정책 후보를 줄인다.
   - 이후 `trace_gtrace_l2c_test.txt`의 8개 group으로 확장한다.

## Working Hypothesis

현재 가장 강한 가설은 다음이다.

> FDIP가 instruction fetch latency를 충분히 숨기는 구간에서는 L2C instruction residency의 가치가 작아지고, data capacity 보호의 가치가 커진다. 따라서 L2C는 data 중심으로 운영하되, demand instruction 또는 FDIP가 약한 구간에만 제한적으로 instruction을 허용하는 정책이 유리할 가능성이 높다.

이 가설을 검증하기 위해 다음 실험은 "모든 instruction 제거"가 아니라 **FDIP prefetch traffic만 L2C에서 분리**하는 방향으로 시작한다.
