# Research Plan 2: Prefetcher Pressure and L2C I/D Balance

## Research Plan 1 이후 결론

첫 번째 research plan에서는 L2C를 instruction/data가 함께 사용할 때 발생하는 간섭과, FDIP/FTQ가 이 간섭을 어떻게 바꾸는지를 중심으로 실험했다. 핵심 관찰은 `FTQ`가 충분히 커질수록 instruction miss 비용이 어느 정도 숨겨지고, 그 결과 L2C에서 data가 차지하는 공간의 가치가 더 크게 드러날 수 있다는 점이었다.

다만 후속 실험에서 L2C way partition을 단순히 capacity만 나누는 것이 아니라, way 수에 따라 lookup latency까지 바꾸는 모델을 적용해 보았다. 이 모델은 `shared`에서는 전체 8-way를 검색하고, partition에서는 자기에게 할당된 way만 검색하도록 하여 latency를 조절하는 방식이었다.

이 접근은 직관적으로는 유용했지만, 실제 cache 동작 관점에서는 너무 강한 가정이라는 결론을 내렸다.

- 실제 cache lookup latency는 way 수에 비례해서 단순히 선형 증가한다고 보기 어렵다.
- set-associative cache는 tag 비교를 병렬로 수행하는 구조가 일반적이다.
- 따라서 `2i6d`의 instruction lookup이 2-cycle, data lookup이 6-cycle처럼 직접 바뀌는 모델은 물리적으로 자연스럽지 않다.
- 결과적으로 way별 latency 모델은 기본 연구 방향에서 제외하고, 필요하면 별도 define으로만 남겨 비교용 옵션으로 사용한다.

현재 기본 모델은 ChampSim의 원래 latency 해석으로 되돌린다. 즉 L2C partition은 **latency를 바꾸는 실험**이 아니라, **L2C capacity와 cache residency를 instruction/data 사이에서 어떻게 나눌지 보는 실험**으로 정리한다.

## 현재 연구 방향

다음 단계에서는 L2C의 instruction/data partition 자체보다, **prefetcher가 instruction 또는 data cache pressure를 어떻게 바꾸는지**를 중심으로 본다.

특히 현재 관심사는 다음이다.

- L2C에서 instruction line이 data line을 밀어내는가?
- 반대로 data-side prefetch가 instruction residency를 방해하는가?
- FTQ/FDIP가 켜져 있을 때 instruction cache pressure가 줄어드는가, 아니면 prefetch traffic으로 L2C 오염이 커지는가?
- L1D/L2D prefetcher를 강하게 만들면 data pressure가 증가하고, 이때 L2C partition 정책의 효과가 달라지는가?
- L1I prefetcher를 추가하면 instruction side pressure가 어떻게 바뀌는가?

이제 실험은 “way 수에 따른 latency 변화”가 아니라, **prefetcher 조합에 따라 I/D traffic pressure를 만들고 그때 partition의 효과를 보는 방향**으로 진행한다.

## 다음 실험 계획

### 1. FTQ off 상태에서 L2C partition만 측정

먼저 `FTQ=0`으로 FDIP를 끄고 L2C partition 효과만 다시 측정한다.

목적은 FDIP가 없는 baseline에서 instruction/data partition이 IPC와 MPKI에 어떤 영향을 주는지 확인하는 것이다.

확인할 항목:

- `shared` 대비 `0i8d`, `1i7d`, `2i6d`, `4i4d`, `6i2d`, `8i0d`의 IPC 변화
- L1I/L2I MPKI 변화
- L1D/L2D MPKI 변화
- frontend stall 변화
- backend data stall 변화

이 실험은 이후 prefetcher를 켰을 때의 변화가 FDIP 때문인지, data prefetcher 때문인지, instruction prefetcher 때문인지 구분하기 위한 기준점이 된다.

### 2. L1D Berti + L2D Pythia 적용

두 번째는 data-side prefetch pressure를 키우는 실험이다.

설정 방향:

- L1D prefetcher: `berti`
- L2D prefetcher: `pythia`
- FDIP/FTQ는 우선 별도 sweep 또는 `ftq0` baseline에서 시작
- L2C partition은 동일하게 유지

목적은 data prefetcher가 강하게 동작할 때 L2C data occupancy가 더 중요해지는지 확인하는 것이다.

예상 질문:

- data prefetch가 많아지면 `0i8d` 또는 data-favored partition이 더 좋아지는가?
- data prefetch가 오히려 L2C/LLC traffic을 늘려 IPC를 낮추는 workload가 있는가?
- L2D MPKI가 줄어도 backend data stall이 줄지 않는 경우가 있는가?
- data prefetch traffic이 instruction line을 밀어내는 현상이 관찰되는가?

이 실험은 “data pressure가 클수록 instruction way를 줄이는 것이 유리한가”를 확인하는 데 초점을 둔다.

### 3. L1I EIP 적용

세 번째는 instruction-side prefetch pressure를 조절하는 실험이다.

설정 방향:

- L1I prefetcher: `eip`
- L1D/L2D prefetcher는 우선 기본 또는 `no`에서 시작
- 이후 Berti/Pythia 조합과 함께 비교

목적은 L1I prefetcher가 FDIP와 유사하게 instruction miss를 줄이는지, 그리고 그 결과 L2C instruction residency의 가치가 낮아지는지 확인하는 것이다.

예상 질문:

- EIP가 L1I MPKI를 줄이면 `0i8d`의 손해가 줄어드는가?
- EIP가 만든 instruction prefetch traffic이 L2C data capacity를 오염시키는가?
- FDIP와 EIP를 동시에 쓰면 instruction pressure가 줄어드는가, 아니면 prefetch traffic만 늘어나는가?

이 실험은 “instruction을 L2C에 유지해야 하는가, 아니면 prefetcher가 충분히 숨길 수 있는가”를 판단하는 데 필요하다.

## 우선순위

1. `FTQ=0`에서 L2C partition-only baseline 재측정
2. L1D `berti` + L2D `pythia`로 data pressure 증가 실험
3. L1I `eip`로 instruction pressure 변화 실험
4. FDIP/FTQ와 data/instruction prefetcher 조합 비교
5. workload별로 instruction-sensitive/data-sensitive 그룹 분류

## 현재 가설

현재 가설은 다음과 같다.

> L2C I/D partition의 효과는 partition 자체보다, prefetcher가 만들어내는 instruction/data pressure에 의해 크게 달라질 가능성이 높다. FTQ 또는 L1I prefetcher가 instruction miss 비용을 숨기면 data-favored L2C가 유리해질 수 있고, 반대로 data prefetcher가 L2C를 강하게 압박하면 instruction/data 간섭이 더 명확하게 드러날 수 있다.

따라서 다음 연구는 L2C way 비율을 고정적으로 찾는 것보다, **prefetcher 조합에 따라 L2C가 어느 쪽 traffic을 보호해야 하는지**를 판단하는 방향으로 진행한다.
