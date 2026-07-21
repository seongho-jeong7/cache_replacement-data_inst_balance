# 2026-07-21 코드 노트: L2C Way 기반 Latency 모델 제거 — FTQ0, Latency 제거 Test

`ChampSim_FDIP`에서 `c19adac`(Way별 L2C search latency 모델, `docs/exp/2026_07_15_code_analysis.md` 참고)를 다시 되돌린 working-tree 변경사항 정리. 아직 커밋되지 않은 상태(HEAD는 `73980b3` "Constrain L2C replacement to partition ways")에서 `champsim_config.json`/`src/cache.cc`만 로컬로 수정해 테스트하는 중이다.

## 배경

`docs/exp/2026_07_21_analysis.md`에서 확인했듯, `c19adac`가 도입한 "L2C search latency = partition way 수에 비례" 모델이 `260714_2030`↔`260716_1733` 사이 dIPC 부호 반전의 근본 원인이었다. `73980b3`(replacement를 partition 안으로 제약)의 효과를 latency 모델과 분리해서 순수하게 보기 위해, latency 모델을 끄고(=원래의 고정 latency로 되돌리고) 다시 테스트한다.

## 변경 내용

### `champsim_config.json`

L2C/LLC 각각에서 `hit_latency`/`fill_latency` 두 필드를 없애고 단일 `latency` 필드로 되돌림.

```diff
 L2C:
-        "hit_latency": 8,
-        "fill_latency": 1,
+        "latency": 10,

 LLC:
-        "hit_latency": 16,
-        "fill_latency": 1,
+        "latency": 20,
```

### `src/cache.cc`

`CACHE::effective_l2c_search_latency()`가 partition way 수 기반 계산 대신 고정 `HIT_LATENCY`를 반환하도록, 컴파일타임 매크로로 토글 가능하게 함(기본값 0 = 꺼짐 = 이번 테스트 상태).

```diff
+#ifndef CHAMPSIM_L2C_WAY_LATENCY
+#define CHAMPSIM_L2C_WAY_LATENCY 0
+#endif
+
 ...
 auto CACHE::effective_l2c_search_latency(bool is_instr_fetch) const -> champsim::chrono::clock::duration
 {
   if (bypasses_l2c_access(is_instr_fetch))
     return champsim::chrono::clock::duration{};

+#if CHAMPSIM_L2C_WAY_LATENCY
   const auto search_ways = is_instr_fetch ? std::min(l2c_instruction_ways, NUM_WAY) : std::min(l2c_data_ways, NUM_WAY);
   return clock_period * search_ways;
+#else
+  return HIT_LATENCY;
+#endif
 }
```

`l2c_victim_way_range()`(partition 제약 victim 선택, `73980b3`)는 그대로 유지된다 — 이번 변경은 latency 모델만 되돌리고, replacement가 partition 밖을 건드리지 않는 동작은 그대로 남긴다.

## 이번 테스트에서 보고 싶은 것

- Way 기반 latency 모델이 꺼진 상태에서, `2i6d`/`6i2d`처럼 way를 실제로 나누는 정책이 `shared` 대비 여전히 이득/손해를 보이는지 — 만약 latency 모델 없이도 경향이 비슷하다면, 이전 분석에서 확인한 "MPKI 경향은 거의 동일, dIPC 부호만 latency 모델이 뒤집었다"는 결론을 다시 한번 교차 검증하는 셈이다.
- FDIP는 이번 테스트에서 끔(FTQ 0 고정) — replacement/latency 변경 자체의 순수 효과만 보기 위해 FDIP 변수를 제거했다.

관련 문서: `docs/exp/2026_07_21_latency_off_experiment.md`(이번 실행 조건), `docs/exp/2026_07_21_analysis.md`(latency 모델 도입 전후 비교), `docs/exp/2026_07_21_code.md`(`73980b3` replacement 제약 코드 노트).
