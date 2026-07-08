# ChampSim ae8924d vs ChampSim_FDIP_ideal Diff

이 문서는 `ChampSim` commit `ae8924d782d7d3e46dfb6ccc6a1d633bda99d02f`를 기준으로 `ChampSim_FDIP_ideal` 최신 commit `b6ef2085cc648f049da61a8e839dc04e611ee35e`의 변경점을 다시 정리한 것이다.

이전 문서는 기준을 `ChampSim_DPC4`로 잡아 잘못되었다. 여기서는 사용자가 지정한 것처럼 일반 `ChampSim ae8924d`를 base로 둔다.

## 참고 자료

- IEEE 문서: <https://ieeexplore.ieee.org/document/809439>
  - 현재 IEEE 페이지는 JavaScript/봇 검증으로 본문 접근이 막힌다.
- 공개 FDIP 설명 참고: [Fetch-Directed Instruction Prefetching Revisited](https://arxiv.org/abs/2006.13547)
  - 이 공개 문서는 FDIP가 instruction cache miss를 줄이는 데 효과적이며, 충분한 BTB가 FDIP 효과의 핵심이라고 설명한다.
  - 또한 FDIP가 branch working set과 branch target tracking 구조에 크게 의존한다고 설명한다.

## 비교 범위

주요 비교 대상:

- `src/`
- `inc/`
- `champsim_config.json`

생성물로 보이는 `compile_commands.json`는 분석 대상에서 제외한다.

변경 파일:

```text
src/cache.cc
src/cache_stats.cc
src/core_stats.cc
src/generated_environment.cc
src/json_printer.cc
src/main.cc
src/ooo_cpu.cc
src/plain_printer.cc
src/ptw.cc

inc/block.h
inc/cache.h
inc/cache_stats.h
inc/champsim.h
inc/channel.h
inc/core_stats.h
inc/event_counter.h
inc/instruction.h
inc/ooo_cpu.h
inc/ptw.h

champsim_config.json
```

## 전체 요약

`ChampSim_FDIP_ideal`의 변경은 순수 FDIP만이 아니다. 크게 세 층이 섞여 있다.

1. **FDIP 본체**
   - FTQ(Future Target Queue) 구조 추가
   - `input_queue`를 앞서 스캔해 future instruction block을 생성
   - FTQ entry를 L1I prefetch로 발행
   - branch misprediction 시 FTQ flush

2. **FDIP 효과 측정용 통계**
   - L1I demand access를 FDIP-covered hit, non-prefetch hit, late prefetch merge, normal merge, miss로 분해
   - plain output에 `==== L1I Demand Access Breakdown ====` 추가

3. **부가 instrumentation**
   - instruction pointer를 cache/channel request에 전달
   - DTLB/ITLB/STLB miss 여부와 최종 cache/memory hit level을 instruction 단위로 추적
   - backend stall / ROB stall breakdown 출력

## 핵심 Diff 1: `--ftq_size` CLI 추가

파일:

- `src/main.cc`

```diff
+extern uint32_t FTQ_SIZE;
+
 #ifndef CHAMPSIM_TEST_BUILD
 using configured_environment = champsim::configured::generated_environment<CHAMPSIM_BUILD>;
@@
   auto* json_option =
       app.add_option("--json", json_file_name, "The name of the file to receive JSON output. If no name is specified, stdout will be used")->expected(0, 1);

+  app.add_option("--ftq_size", FTQ_SIZE, "Set the FTQ size");
+
   app.add_option("traces", trace_names, "The paths to the traces")->required()->expected(NUM_CPUS)->check(CLI::ExistingFile);
```

의미:

- 실행 시 `--ftq_size N`으로 FTQ 크기를 바꿀 수 있게 한다.
- 단, 이 옵션은 `FTQ_SIZE`만 바꾼다. `ChampSim_FDIP_ideal` 최신 코드에서는 `ENABLE_FDIP`가 아래처럼 `constexpr false`라서, `--ftq_size`만으로 FDIP가 켜지지는 않는다.

## 핵심 Diff 2: FDIP enable flag, FTQ size, operate 경로

파일:

- `src/ooo_cpu.cc`

```diff
 std::chrono::seconds elapsed_time();
-
+bool flag_cpu_trace = false;
 constexpr long long STAT_PRINTING_PERIOD = 10000000;
+// inwook start
+constexpr bool ENABLE_FDIP = false; // Toggle FDIP prefetching
+constexpr bool PERFECT_BP = false; // Toggle Perfect Branch Prediction
+// inwook end UFTQ prefetching
+uint32_t FTQ_SIZE = 32;
+#define FQ_OFFSET 6
+// inwook end
```

```diff
-  progress += fetch_instruction(); // fetch
+  predict_future_blocks();         // inwook: Fill FTQ independently (Decoupled)
+  process_ftq();                   // inwook: Issue FTQ prefetches
+  progress += fetch_instruction(); // fetch
```

구현 내용:

- 매 cycle의 normal fetch 전에 FDIP 경로를 먼저 수행한다.
- `predict_future_blocks()`는 future block을 FTQ에 채운다.
- `process_ftq()`는 FTQ에 들어간 future block을 L1I prefetch로 발행한다.

검토:

- `ENABLE_FDIP = false`가 compile-time constant다. 따라서 이 최신 `ideal` 코드는 이름과 달리 기본 상태에서는 FDIP가 꺼져 있다.
- `--ftq_size`는 런타임 옵션이지만 `ENABLE_FDIP`와 연결되어 있지 않다.
- 실제 실험에서 FDIP를 켜려면 `ENABLE_FDIP`를 true로 바꾸거나, 현재 작업 repo의 `ChampSim_FDIP`처럼 `FTQ_SIZE > 0`으로 runtime 판단하도록 수정해야 한다.

## 핵심 Diff 3: FTQ 구조 추가

파일:

- `inc/ooo_cpu.h`

```diff
+struct FTQ_ENTRY {
+  champsim::address ip;
+  std::array<uint8_t, 2> asid;
+
+  bool taken = false;
+  uint8_t termination_offset = 0;
+  uint8_t branch_type = 0;
+
+  std::unordered_map<uint64_t, uint64_t> demand_issue_cycle;
+
+  // Decoupled FDIP state
+  void predict_future_blocks();
+  uint64_t ftq_last_scan_instr_id = 0;
+  uint64_t ftq_last_scan_ip = 0;
+  uint8_t ftq_current_block_count = 0;
+
+  // States: 0=Invalid, 1=Pred-Complete, 2=Wait-Fill, 3=Ready
+  uint8_t fetch_state = 0;
+  uint64_t event_cycle = 0;
+};
```

```diff
+  std::deque<FTQ_ENTRY> FTQ;
+  void process_ftq();
+  std::unordered_map<uint64_t, uint64_t> prefetch_issue_cycle;
+  std::unordered_map<uint64_t, uint64_t> demand_issue_cycle;
+
+  // Decoupled FDIP state
+  void predict_future_blocks();
+  uint64_t ftq_last_scan_instr_id = 0;
+  uint64_t ftq_last_scan_ip = 0;
+  uint8_t ftq_current_block_count = 0;
+
+  // Adaptive FTQ
+  uint64_t ftq_last_stats_version = 0;
+  uint64_t ftq_last_adjust_cycle = 0;
+  uint64_t ftq_accumulated_issued_count = 0;
```

구현 내용:

- `FTQ_ENTRY`는 future instruction cache line 또는 taken-branch-delimited block을 표현한다.
- `ip`는 prefetch할 instruction block address다.
- `termination_offset`은 해당 FTQ block이 실제 fetch stream에서 언제 소모되는지 추적하기 위한 counter다.
- `fetch_state`는 FDIP prefetch 상태를 나타낸다.
  - `1`: prediction complete / issue 가능
  - `2`: prefetch issued, fill 대기
  - `3`: fill 완료

검토:

- `FTQ_ENTRY` 안에 `predict_future_blocks()`와 `ftq_last_scan_*` 상태가 들어가 있는데, 실제 구현은 `O3_CPU::predict_future_blocks()`와 `O3_CPU` 멤버 상태를 사용한다. 즉 `FTQ_ENTRY` 내부의 decoupled state 선언은 불필요하거나 잘못 배치된 흔적으로 보인다.

## 핵심 Diff 4: future block 생성

파일:

- `src/ooo_cpu.cc`

```diff
+void O3_CPU::predict_future_blocks()
+{
+  if (!ENABLE_FDIP)
+    return;
+  if (input_queue.empty())
+    return;
+
+  int ftq_added_this_cycle = 0;
+
+  for (const auto& instr : input_queue) {
+    if (instr.instr_id <= ftq_last_scan_instr_id)
+      continue;
+
+    if (ftq_added_this_cycle >= 1) {
+      break;
+    }
+
+    uint64_t curr_ip = instr.ip.to<uint64_t>();
+    uint64_t curr_line = curr_ip >> FQ_OFFSET;
+    uint64_t last_line = ftq_last_scan_ip >> FQ_OFFSET;
+
+    if (ftq_last_scan_ip != 0 && curr_line != last_line) {
+      if (FTQ.size() >= FTQ_SIZE)
+        break;
+
+      FTQ_ENTRY new_entry;
+      new_entry.ip = champsim::address{last_line << FQ_OFFSET};
+      new_entry.taken = false;
+      new_entry.termination_offset = ftq_current_block_count - 1;
+      new_entry.fetch_state = 1;
+      new_entry.event_cycle = current_time.time_since_epoch() / clock_period;
+      std::copy(std::begin(instr.asid), std::end(instr.asid), std::begin(new_entry.asid));
+
+      FTQ.push_back(new_entry);
+      ftq_added_this_cycle++;
+      ftq_current_block_count = 0;
+    }
+
+    ftq_last_scan_ip = curr_ip;
+    ftq_current_block_count++;
+    ftq_last_scan_instr_id = instr.instr_id;
+
+    if (instr.is_branch && instr.branch_taken) {
+      if (FTQ.size() >= FTQ_SIZE)
+        break;
+
+      FTQ_ENTRY new_entry;
+      new_entry.ip = champsim::address{curr_line << FQ_OFFSET};
+      new_entry.taken = true;
+      new_entry.termination_offset = ftq_current_block_count - 1;
+      new_entry.fetch_state = 1;
+      new_entry.event_cycle = current_time.time_since_epoch() / clock_period;
+      std::copy(std::begin(instr.asid), std::end(instr.asid), std::begin(new_entry.asid));
+
+      FTQ.push_back(new_entry);
+      ftq_added_this_cycle++;
+
+      ftq_current_block_count = 0;
+      ftq_last_scan_ip = 0;
+    }
+  }
+}
```

구현 내용:

- `input_queue`를 normal fetch보다 앞서 훑으며 future block을 만든다.
- cache line이 바뀌면 sequential block을 FTQ에 넣는다.
- taken branch를 만나면 branch block을 FTQ에 넣는다.
- 한 cycle에 최대 1개 FTQ entry만 추가한다.

논문 관점 검토:

- 공개 FDIP 설명 자료는 FDIP가 BPU/BTB가 예측한 fetch path를 따라 instruction prefetch를 수행하는 구조라고 설명한다.
- 이 구현은 BTB prediction 결과가 아니라 trace의 실제 `instr.branch_taken`을 사용한다.
- 따라서 이것은 실제 하드웨어형 FDIP라기보다 **oracle/perfect-path FDIP** 모델에 가깝다.
- `PERFECT_BP` 옵션은 branch prediction을 perfect로 만들 수 있지만, `predict_future_blocks()`는 `PERFECT_BP`와 무관하게 실제 branch outcome을 사용한다.

## 핵심 Diff 5: FTQ prefetch 발행

파일:

- `src/ooo_cpu.cc`

```diff
+void O3_CPU::process_ftq()
+{
+  if (std::empty(FTQ)) {
+    return;
+  }
+
+  if (!ENABLE_FDIP) {
+    return;
+  }
+
+  for (auto it = std::next(FTQ.begin()); it != FTQ.end(); ++it) {
+    if (it->fetch_state == 1) {
+      bool success = l1i->prefetch_line(it->ip, true, 0);
+      if (success) {
+        it->fetch_state = 2;
+        ftq_accumulated_issued_count++;
+      } else {
+        break;
+      }
+    }
+  }
+}
```

구현 내용:

- FTQ head는 현재 demand fetch에 가깝다고 보고 건너뛴다.
- tail 쪽 future block에 대해 L1I `prefetch_line()`을 호출한다.
- L1I PQ/MSHR 등이 막혀 `prefetch_line()`이 실패하면 그 cycle의 FDIP issue를 중단한다.

검토:

- `CacheBus::issue_prefetch()`도 추가되어 있지만, FDIP 발행 경로는 실제로 `l1i->prefetch_line()`을 사용한다.
- 따라서 `CacheBus::issue_prefetch()`는 현재 구현에서는 사실상 dead code 또는 이전 구현 흔적으로 보인다.

## 핵심 Diff 6: FTQ drain과 misprediction flush

파일:

- `src/ooo_cpu.cc`

```diff
+  // Drain FTQ as instructions leave IFETCH_BUFFER
+  for (auto it = window_begin; it != window_end; ++it) {
+    if (!std::empty(FTQ)) {
+      bool pop_required = false;
+
+      if (it->is_branch && it->branch_taken) {
+        pop_required = true;
+      }
+      else if (FTQ.front().termination_offset == 0) {
+        pop_required = true;
+      } else {
+        if (FTQ.front().termination_offset > 0)
+          FTQ.front().termination_offset--;
+      }
+
+      if (pop_required) {
+        FTQ.pop_front();
+      }
+    }
+  }
```

```diff
+        this->FTQ.clear(); // inwook: Clear FTQ on misprediction
+        this->ftq_last_scan_instr_id = 0;
+        this->ftq_current_block_count = 0;
+        this->ftq_last_scan_ip = 0;
```

```diff
+    FTQ.clear();
+    ftq_last_scan_instr_id = 0;
+    ftq_current_block_count = 0;
+    ftq_last_scan_ip = 0;
```

구현 내용:

- IFETCH buffer에서 instruction이 decode/promote되며 실제 stream이 전진할 때 FTQ head를 drain한다.
- taken branch 또는 `termination_offset` 종료 조건에 도달하면 FTQ entry를 pop한다.
- decode/execute 단계에서 branch misprediction이 감지되면 FTQ를 clear하고 scan state를 초기화한다.

검토:

- wrong-path prefetch를 줄이려는 처리는 들어 있다.
- 그러나 FTQ 생성 자체가 actual future trace 기반이라, “wrong path를 branch predictor가 얼마나 만들었는가”를 재현하는 모델은 아니다.

## 핵심 Diff 7: instruction pointer를 cache/channel request로 전파

파일:

- `inc/channel.h`
- `inc/cache.h`
- `inc/instruction.h`
- `src/ooo_cpu.cc`
- `src/cache.cc`

```diff
 struct request {
   bool forward_checked = false;
   bool is_translated = true;
+  bool trans_hit_L1D = false;
+  bool trans_hit_L2C = false;
+  bool trans_hit_LLC = false;
+  bool trans_hit_MEM = false;
   bool response_requested = true;

+  uint8_t access_offset;
   uint8_t asid[2] = {std::numeric_limits<uint8_t>::max(), std::numeric_limits<uint8_t>::max()};
   access_type type{access_type::LOAD};
@@
   uint64_t instr_id = 0;
   champsim::address ip{};
+  ooo_model_instr* instr = nullptr;

   std::vector<uint64_t> instr_depend_on_me{};
 };
```

```diff
 struct ooo_model_instr {
@@
   bool executed = false;
   bool completed = false;

+  bool translated = false;
+  bool stlb_miss = false;
+  bool dtlb_miss = false;
+  bool itlb_miss = false;
+  bool stlb_miss_L1D_hit = false;
+  bool stlb_miss_L2C_hit = false;
+  bool stlb_miss_LLC_hit = false;
+  bool stlb_miss_MEM_hit = false;
+
+  bool mem_access_completed = false;
+  bool replay = false;
```

```diff
-    q_entry->emplace(smem, instr.instr_id, instr.ip, instr.asid);
+    q_entry->emplace(&instr, smem, instr.instr_id, instr.ip, instr.asid);
@@
   data_packet.ip = lq_entry.ip;
+  data_packet.instr = lq_entry.instr;
+  data_packet.instr_depend_on_me.push_back(lq_entry.instr_id);
```

구현 내용:

- cache/TLB 요청이 어떤 ROB instruction에서 왔는지 추적하기 위해 `ooo_model_instr*`를 request에 실어 보낸다.
- 이후 cache/TLB hit/miss 결과를 원래 instruction object의 flag에 기록한다.
- FDIP 자체보다 분석/계측을 위한 기반 변경에 가깝다.

검토:

- `ooo_model_instr*`는 `ROB`, `IFETCH_BUFFER` 등 deque 내부 object를 가리킨다. deque는 push/pop 시 참조 안정성이 비교적 좋지만, instruction이 retire/erase된 뒤 지연 응답이 돌아오면 dangling pointer 위험을 검토해야 한다.
- 현재 코드가 `instr_depend_on_me`와 함께 쓰이므로 보통은 생존 기간 안에 처리될 가능성이 높지만, 안전한 설계라면 raw pointer보다 `instr_id` 기반 lookup이 더 견고하다.

## 핵심 Diff 8: L1I FDIP coverage 통계

파일:

- `inc/cache_stats.h`
- `src/cache.cc`
- `src/cache_stats.cc`
- `src/plain_printer.cc`

```diff
+  uint64_t fdip_l1i_hit = 0;               // Demand hit on prefetched line
+  uint64_t fdip_l1i_hit_non_pf = 0;        // Demand hit on non-prefetched line
+  uint64_t fdip_l1i_mshr_merge = 0;        // Demand merge into prefetch MSHR
+  uint64_t fdip_l1i_mshr_merge_non_pf = 0; // Demand merge into non-prefetch MSHR
+  uint64_t fdip_l1i_miss = 0;              // Demand miss
+  uint64_t fdip_l1i_total_access = 0;      // Total Demand Accesses to L1I
```

```diff
+    if (NAME == "cpu0_L1I" && handle_pkt.type == access_type::LOAD && !warmup) {
+      ++sim_stats.fdip_l1i_total_access;
+      if (way->prefetch) {
+        ++sim_stats.fdip_l1i_hit;
+      } else {
+        ++sim_stats.fdip_l1i_hit_non_pf;
+      }
+    }
```

```diff
+      if (NAME == "cpu0_L1I" && handle_pkt.type == access_type::LOAD && !warmup) {
+        ++sim_stats.fdip_l1i_mshr_merge;
+      }
+    } else {
+      if (NAME == "cpu0_L1I" && handle_pkt.type == access_type::LOAD && !warmup) {
+        ++sim_stats.fdip_l1i_mshr_merge_non_pf;
+      }
+    }
@@
+    if (NAME == "cpu0_L1I" && handle_pkt.type == access_type::LOAD && !warmup) {
+      ++sim_stats.fdip_l1i_miss;
+    }
```

```diff
+    lines.emplace_back("==== L1I Demand Access Breakdown ====");
+    print_line("L1I Hit (FDIP Covered)", l1i_hit, l1i_total);
+    print_line("L1I Hit (Non-Prefetch)", l1i_hit_non_pf, l1i_total);
+    print_line("L1I Late Prefetch (Merge)", l1i_merge, l1i_total);
+    print_line("L1I Merge (Non-Prefetch)", l1i_merge_non_pf, l1i_total);
+    print_line("L1I Miss", l1i_miss, l1i_total);
+    lines.push_back(fmt::format("{:<30} : {:10}", "TOTAL (Direct Count)", l1i_total));
+    lines.push_back(fmt::format("{:<30} : {:10} (Check Sum)", "Sum of Components", l1i_sum));
```

구현 내용:

- FDIP가 L1I demand miss를 얼마나 덮었는지 보기 위한 breakdown이다.
- `Hit (FDIP Covered)`는 demand fetch가 prefetch bit가 켜진 line에 hit한 경우다.
- `Late Prefetch (Merge)`는 demand miss가 이미 inflight인 prefetch MSHR에 merge된 경우다.
- `Miss`는 FDIP가 제때 덮지 못한 demand miss다.

검토:

- `way->prefetch` bit는 useful demand hit 시 false로 reset된다. 따라서 같은 line의 후속 demand hits는 `FDIP Covered`가 아니라 `Non-Prefetch`로 분류된다. “FDIP가 최초 miss를 제거했는가”를 보려는 지표라면 타당하지만, “그 line의 모든 후속 hit까지 FDIP 효과로 볼 것인가”와는 정의가 다르다.
- MSHR full로 `handle_miss()`가 false를 반환하는 경우는 accepted access가 아니므로 breakdown total에 들어가지 않는다.

## 핵심 Diff 9: TLB/cache hit-map instrumentation

파일:

- `inc/cache_stats.h`
- `src/cache.cc`
- `src/plain_printer.cc`
- `inc/channel.h`
- `inc/instruction.h`

대표 diff:

```diff
+  uint64_t dtlb_hit_L1I_hit = 0;
+  uint64_t dtlb_hit_L1D_hit = 0;
+  uint64_t dtlb_hit_L2C_hit = 0;
+  uint64_t dtlb_hit_LLC_hit = 0;
+  uint64_t dtlb_hit_MEM_hit = 0;
+  ...
+  uint64_t itlb_miss_stlb_miss_MEM_hit_MEM_hit = 0;
```

```diff
+  if (NAME == "cpu0_STLB" && !hit && !warmup) {
+    if (handle_pkt.instr)
+      handle_pkt.instr->stlb_miss = true;
+  }
+  if (NAME == "cpu0_DTLB" && !hit && !warmup) {
+    if (handle_pkt.instr)
+      handle_pkt.instr->dtlb_miss = true;
+  }
+  if (NAME == "cpu0_ITLB" && !hit && !warmup) {
+    if (handle_pkt.instr)
+      handle_pkt.instr->itlb_miss = true;
+  }
```

구현 내용:

- FDIP 논문 구현이라기보다 실험 분석용 추가 계측이다.
- TLB hit/miss와 최종 cache/memory level을 cross-tabulate한다.
- `docs/champsim_log_analysis.md`와 `parser/fdip/hit_map.py`에서 분석하는 값과 연결된다.

## 핵심 Diff 10: `champsim_config.json`

파일:

- `champsim_config.json`

```diff
   "ooo_cpu": [
     {
       "frequency": 4000,
       "ifetch_buffer_size": 64,
-      "decode_buffer_size": 32,
+      "_note_ifetch": "inwook_ch_Original value was 64",
+      "decode_buffer_size": 192,
       "dispatch_buffer_size": 32,
-      "register_file_size": 128,
+      "register_file_size": 280,
       "rob_size": 352,
       "lq_size": 128,
       "sq_size": 72,
-      "fetch_width": 6,
-      "decode_width": 6,
-      "dispatch_width": 6,
-      "execute_width": 4,
+      "fetch_width": 8,
+      "decode_width": 4,
+      "dispatch_width": 5,
+      "execute_width": 10,
@@
-      "scheduler_size": 128,
+      "scheduler_size": 160,
@@
-      "execute_latency": 0,
+      "execute_latency": 1,
```

```diff
   "L1D": {
@@
-    "prefetcher": "no"
+    "prefetcher": "ip_stride"
   },
@@
   "L2C": {
@@
-    "latency": 10,
+    "hit_latency": 9,
+    "fill_latency": 1,
@@
-    "prefetcher": "no"
+    "prefetcher": "ip_stride"
   },
@@
   "LLC": {
@@
-    "latency": 20,
+    "hit_latency": 29,
+    "fill_latency": 1,
```

```diff
   "physical_memory": {
@@
-    "tCAS": 24,
-    "tRCD": 24,
-    "tRP": 24,
-    "tRAS": 52,
+    "tCAS": 12.5,
+    "tRCD": 12.5,
+    "tRP": 12.5,
+    "tRAS": 25,
```

구현/실험 의미:

- FDIP 자체뿐 아니라 core width, queue, scheduler, memory/cache latency가 함께 바뀐다.
- L1D/L2C data prefetcher가 `ip_stride`로 켜져 있다.
- 따라서 `ChampSim ae8924d` 기본 config와 `ChampSim_FDIP_ideal` 결과를 직접 비교하면 FDIP 효과만 분리되지 않는다.

## 구현 정확성 검토

### 1. 기본 상태에서 FDIP가 꺼져 있음

가장 중요한 문제다.

```cpp
constexpr bool ENABLE_FDIP = false;
```

`--ftq_size`가 추가되어도 이 값은 변하지 않는다. 즉 `ChampSim_FDIP_ideal` 최신 commit 그대로 빌드하면 `predict_future_blocks()`와 `process_ftq()`가 즉시 return한다.

### 2. 실제 FDIP라기보다 ideal/oracle FDIP에 가까움

공개 FDIP 설명 자료는 FDIP가 BPU/BTB가 예측한 fetch path를 따라 instruction prefetch를 수행하는 구조라고 설명한다. 그런데 이 구현은 `input_queue`의 실제 trace instruction과 실제 `branch_taken`을 사용한다.

```cpp
if (instr.is_branch && instr.branch_taken) {
  ...
}
```

따라서 실제 branch predictor/BTB miss, wrong-path prediction 효과를 정확히 모델링하지 않는다. 이름 그대로 `ChampSim_FDIP_ideal`이라면 의도된 oracle model일 수 있지만, 논문형 hardware FDIP라고 쓰면 부정확하다.

### 3. `PERFECT_BP`와 FDIP path가 분리되어 있음

`PERFECT_BP`는 normal branch prediction을 perfect로 만드는 옵션이지만, FDIP path는 그 값과 무관하게 actual branch outcome을 사용한다. 따라서 `PERFECT_BP=false`여도 FDIP future path는 사실상 perfect path다.

### 4. `FTQ_ENTRY` 내부에 잘못 위치한 듯한 상태가 있음

`FTQ_ENTRY` 안에 `predict_future_blocks()`와 scan 상태가 선언되어 있지만 실제로 쓰이지 않는다. 이 상태는 이미 `O3_CPU`에 있다. 정리 대상이다.

### 5. config 변경이 FDIP 효과를 오염시킬 수 있음

core width, scheduler, latency, L1D/L2C prefetcher, DRAM timing이 함께 바뀌었다. 실험 목적이 FDIP 단독 효과라면 base config를 최대한 동일하게 두고 FDIP만 on/off해야 한다.

## 결론

`ChampSim_FDIP_ideal`은 `ChampSim ae8924d` 위에 FTQ 기반 instruction prefetch 실험 경로와 풍부한 분석 통계를 추가한 코드다. 다만 최신 commit 기준으로는:

- 기본 빌드에서 FDIP가 꺼져 있고,
- `--ftq_size`와 enable flag가 연결되어 있지 않으며,
- FTQ 생성이 BTB/BPU 예측 기반이 아니라 trace의 actual future path 기반이다.

따라서 이 코드는 “논문형 realistic FDIP 구현”이라기보다 “FDIP 효과 상한을 보기 위한 ideal/perfect-path FDIP 모델 + 분석 instrumentation”으로 해석하는 것이 안전하다.
