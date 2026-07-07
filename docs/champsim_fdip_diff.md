# ChampSim_DPC4 vs ChampSim_FDIP Diff

이 문서는 `ChampSim_DPC4`를 기준으로 `ChampSim_FDIP`가 어떤 코드 변경을 포함하는지 분석한 내용이다.

이전 문서는 일반 `ChampSim`과 `ChampSim_FDIP`를 비교했기 때문에 기준이 맞지 않았다. 여기서는 기준을 `ChampSim_DPC4`로 다시 잡았다.

## 비교 기준

- 기준 버전: `ChampSim_DPC4`
- 변경 버전: `ChampSim_FDIP`
- 제외하고 본 항목:
  - `.git`
  - `.csconfig`
  - `obj`
  - `bin`
  - `saved_bins`
  - `fdip_test`
  - `vcpkg`
  - `vcpkg_installed`
  - `compile_commands.json`
  - `*.o`, `*.d`, `*.log`, `*.png`

## 전체 변경 요약

`ChampSim_FDIP`는 `ChampSim_DPC4` 위에 단순히 FDIP만 추가한 버전은 아니다. 크게 보면 다음 변경이 함께 들어 있다.

- FTQ 기반 instruction prefetch 경로 추가
- L1I prefetch coverage 통계 추가
- TLB to cache/memory breakdown 통계 추가
- instruction object pointer를 cache/channel request에 전달
- fetch/translation/memory 결과를 instruction 단위로 추적
- `--ftq_size` CLI 옵션 추가
- DPC4 API 제거
- DPC4용 prefetcher 디렉터리 일부 제거
- Makefile 단순화
- 기본 `champsim_config.json` 변경
- FDIP 실험/분석용 shell/python script 추가

## 변경 파일 목록

주요 차이 파일은 다음과 같다.

```text
Makefile
champsim_config.json
inc/block.h
inc/cache.h
inc/cache_stats.h
inc/champsim.h
inc/channel.h
inc/core_stats.h
inc/dram_controller.h
inc/event_counter.h
inc/instruction.h
inc/modules.h
inc/msl/fwcounter.h
inc/ooo_cpu.h
inc/operable.h
inc/ptw.h
replacement/drrip/drrip.cc
replacement/drrip/drrip.h
replacement/ship/ship.cc
replacement/ship/ship.h
src/cache.cc
src/cache_stats.cc
src/champsim.cc
src/core_stats.cc
src/dram_controller.cc
src/generated_environment.cc
src/json_printer.cc
src/main.cc
src/modules.cc
src/ooo_cpu.cc
src/plain_printer.cc
src/ptw.cc
src/vmem.cc
```

`ChampSim_DPC4`에만 있는 주요 항목:

```text
dpc4/
inc/dpc_api.h
prefetcher/berti
prefetcher/ipcp
prefetcher/pythia
prefetcher/sms
docs/
test/
tracer/
vcpkg/
```

`ChampSim_FDIP`에만 있는 주요 항목:

```text
build.sh
kill_simul.sh
run.sh
run_champsim_all.sh
run_champsim_all_with_traces.sh
run_test.sh
script/
config/generate_compile_commands.py
```

## 핵심 Diff 1: FDIP Enable, FTQ 크기, operate 경로

파일:

- `ChampSim_DPC4/src/ooo_cpu.cc`
- `ChampSim_FDIP/src/ooo_cpu.cc`

핵심 diff:

```diff
+#ifndef CHAMPSIM_ENABLE_FDIP
+#define CHAMPSIM_ENABLE_FDIP 0
+#endif
+
+constexpr bool ENABLE_FDIP = CHAMPSIM_ENABLE_FDIP != 0;
+constexpr bool PERFECT_BP = false;
+uint32_t FTQ_SIZE = 32;
+#define FQ_OFFSET 6
```

```diff
-  progress += fetch_instruction(); // fetch
+  predict_future_blocks();         // Fill FTQ independently
+  process_ftq();                   // Issue FTQ prefetches
+  progress += fetch_instruction(); // fetch
```

설명:

- `ChampSim_DPC4`에는 FDIP enable flag나 FTQ size가 없다.
- `ChampSim_FDIP`는 매 cycle fetch 전에 `predict_future_blocks()`와 `process_ftq()`를 호출한다.
- `predict_future_blocks()`는 trace/input queue를 미리 읽어 future instruction block을 FTQ에 넣는다.
- `process_ftq()`는 FTQ entry를 L1I prefetch로 발행한다.
- 현재 작업본에서는 `CHAMPSIM_ENABLE_FDIP` compile macro로 FDIP on/off가 가능하게 되어 있다.

실험 명령 예:

```bash
CXXFLAGS='-DCHAMPSIM_ENABLE_FDIP=1 ...' make
```

## 핵심 Diff 2: FTQ 구조 추가

파일:

- `ChampSim_DPC4/inc/ooo_cpu.h`
- `ChampSim_FDIP/inc/ooo_cpu.h`

핵심 diff:

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
+  void predict_future_blocks();
+  uint64_t ftq_last_scan_instr_id = 0;
+  uint64_t ftq_last_scan_ip = 0;
+  uint8_t ftq_current_block_count = 0;
+
+  uint64_t ftq_last_stats_version = 0;
+  uint64_t ftq_last_adjust_cycle = 0;
+  uint64_t ftq_accumulated_issued_count = 0;
```

설명:

- `FTQ_ENTRY`는 future instruction cache line 또는 branch-delimited block을 표현한다.
- `fetch_state`는 FDIP prefetch 상태를 나타낸다.
  - `0`: invalid
  - `1`: prediction complete
  - `2`: wait fill
  - `3`: ready
- `ftq_last_scan_*` 필드는 input queue를 중복 스캔하지 않기 위한 상태다.
- `ftq_accumulated_issued_count` 등은 adaptive FTQ/throttling을 위한 흔적으로 보인다.

## 핵심 Diff 3: FTQ drain과 branch misprediction 처리

파일:

- `ChampSim_FDIP/src/ooo_cpu.cc`

핵심 diff:

```diff
+  // Drain FTQ as instructions leave IFETCH_BUFFER
+  for (auto it = window_begin; it != window_end; ++it) {
+    if (!std::empty(FTQ)) {
+      bool pop_required = false;
+
+      if (it->is_branch && it->branch_taken) {
+        pop_required = true;
+      } else if (FTQ.front().termination_offset == 0) {
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
+        this->FTQ.clear(); // Clear FTQ on misprediction
+        this->ftq_last_scan_instr_id = 0;
+        this->ftq_current_block_count = 0;
+        this->ftq_last_scan_ip = 0;
```

설명:

- FTQ는 future block queue이므로 실제 fetch/decode stream이 지나가면 head entry를 제거해야 한다.
- taken branch 또는 block termination offset에 따라 FTQ를 pop한다.
- decode/execute에서 branch misprediction이 확인되면 FTQ를 clear한다.
- 이것은 wrong-path future prefetch를 줄이려는 처리다.

## 핵심 Diff 4: L1I prefetch 발행

파일:

- `ChampSim_FDIP/src/ooo_cpu.cc`

핵심 코드:

```cpp
void O3_CPU::process_ftq()
{
  if (std::empty(FTQ)) {
    return;
  }

  if (!ENABLE_FDIP) {
    return;
  }

  for (auto it = std::next(FTQ.begin()); it != FTQ.end(); ++it) {
    if (it->fetch_state == 1) {
      bool success = l1i->prefetch_line(it->ip, true, 0);
      if (success) {
        it->fetch_state = 2;
        ftq_accumulated_issued_count++;
      } else {
        break;
      }
    }
  }
}
```

설명:

- FTQ head는 현재 demand fetch에 가까운 block으로 보고 건너뛴다.
- tail 쪽 future block에 대해 `l1i->prefetch_line()`을 호출한다.
- 성공하면 state를 `2`로 바꾼다.
- L1I MSHR/PQ가 막히면 해당 cycle의 FDIP issue를 중단한다.

## 핵심 Diff 5: future block prediction

파일:

- `ChampSim_FDIP/src/ooo_cpu.cc`

핵심 코드:

```cpp
void O3_CPU::predict_future_blocks()
{
  if (!ENABLE_FDIP)
    return;
  if (input_queue.empty())
    return;

  int ftq_added_this_cycle = 0;

  for (const auto& instr : input_queue) {
    if (instr.instr_id <= ftq_last_scan_instr_id)
      continue;

    if (ftq_added_this_cycle >= 1) {
      break;
    }

    uint64_t curr_ip = instr.ip.to<uint64_t>();
    uint64_t curr_line = curr_ip >> FQ_OFFSET;
    uint64_t last_line = ftq_last_scan_ip >> FQ_OFFSET;

    if (ftq_last_scan_ip != 0 && curr_line != last_line) {
      if (FTQ.size() >= FTQ_SIZE)
        break;

      FTQ_ENTRY new_entry;
      new_entry.ip = champsim::address{last_line << FQ_OFFSET};
      new_entry.taken = false;
      new_entry.termination_offset = ftq_current_block_count - 1;
      new_entry.fetch_state = 1;
      FTQ.push_back(new_entry);
      ftq_added_this_cycle++;
      ftq_current_block_count = 0;
    }

    if (instr.is_branch && instr.branch_taken) {
      if (FTQ.size() >= FTQ_SIZE)
        break;

      FTQ_ENTRY new_entry;
      new_entry.ip = champsim::address{curr_line << FQ_OFFSET};
      new_entry.taken = true;
      new_entry.termination_offset = ftq_current_block_count - 1;
      new_entry.fetch_state = 1;
      FTQ.push_back(new_entry);
      ftq_added_this_cycle++;
      ftq_current_block_count = 0;
      ftq_last_scan_ip = 0;
    }
  }
}
```

설명:

- input queue를 미리 스캔해서 future instruction block을 만든다.
- cache line이 바뀌면 sequential block으로 FTQ에 push한다.
- taken branch를 만나면 branch block으로 FTQ에 push한다.
- 한 cycle에 최대 1개 FTQ entry만 추가한다.
- `FTQ_SIZE`보다 커지지 않게 제한한다.

## 핵심 Diff 6: channel/cache request에 instruction pointer 전달

파일:

- `ChampSim_DPC4/inc/channel.h`
- `ChampSim_FDIP/inc/channel.h`
- `ChampSim_DPC4/inc/cache.h`
- `ChampSim_FDIP/inc/cache.h`

핵심 diff:

```diff
+#include "instruction.h"
```

```diff
 struct request {
   bool forward_checked = false;
   bool is_translated = true;
+  bool trans_hit_L1D = false;
+  bool trans_hit_L2C = false;
+  bool trans_hit_LLC = false;
+  bool trans_hit_MEM = false;
+
+  uint8_t access_offset;
   uint8_t asid[2] = {...};
   access_type type{access_type::LOAD};
-  bool is_instr = false;
   uint32_t pf_metadata = 0;
   uint32_t cpu = ...;
   uint64_t instr_id = 0;
   champsim::address ip{};
+  ooo_model_instr* instr = nullptr;
 };
```

설명:

- DPC4는 request에 `is_instr` flag를 들고 다녔다.
- FDIP 버전은 `ooo_model_instr* instr`를 request에 직접 넣는다.
- 이렇게 하면 cache/TLB hit/miss 결과를 instruction object에 직접 기록할 수 있다.
- 대신 pointer lifetime과 stale pointer 위험이 생긴다.
- `access_offset`과 `trans_hit_*`는 translation/cache breakdown 분석에 쓰인다.

## 핵심 Diff 7: instruction object에 TLB/cache state 추가

파일:

- `ChampSim_DPC4/inc/instruction.h`
- `ChampSim_FDIP/inc/instruction.h`

핵심 diff:

```diff
+inline constexpr std::array stall_type_names{"ROB_STALL"sv, "LQ_STALL"sv, "SQ_STALL"sv};
+inline constexpr std::array rob_stall_type_names{"ADDR_TRANS"sv, "REPLAY_LOAD"sv, "NON_REPLAY_LOAD"sv};
```

```diff
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

설명:

- 각 instruction이 translation miss를 겪었는지, STLB miss 이후 어느 level에서 translation이 해결됐는지 기록한다.
- 이후 cache access 결과와 결합해서 TLB to cache/memory breakdown을 만든다.
- stall breakdown 출력을 위해 stall type 이름도 추가됐다.

## 핵심 Diff 8: L1I demand access breakdown

파일:

- `ChampSim_DPC4/src/cache.cc`
- `ChampSim_FDIP/src/cache.cc`
- `ChampSim_DPC4/inc/cache_stats.h`
- `ChampSim_FDIP/inc/cache_stats.h`
- `ChampSim_DPC4/src/plain_printer.cc`
- `ChampSim_FDIP/src/plain_printer.cc`

핵심 diff:

```diff
+  uint64_t fdip_l1i_hit = 0;
+  uint64_t fdip_l1i_hit_non_pf = 0;
+  uint64_t fdip_l1i_mshr_merge = 0;
+  uint64_t fdip_l1i_mshr_merge_non_pf = 0;
+  uint64_t fdip_l1i_miss = 0;
+  uint64_t fdip_l1i_total_access = 0;
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
+    if (mshr_entry->type == access_type::PREFETCH && handle_pkt.type != access_type::PREFETCH) {
+      if (NAME == "cpu0_L1I" && handle_pkt.type == access_type::LOAD && !warmup) {
+        ++sim_stats.fdip_l1i_mshr_merge;
+      }
+    } else {
+      if (NAME == "cpu0_L1I" && handle_pkt.type == access_type::LOAD && !warmup) {
+        ++sim_stats.fdip_l1i_mshr_merge_non_pf;
+      }
+    }
```

설명:

- L1I demand access가 FDIP prefetch line에 hit했는지 기록한다.
- prefetch가 늦어서 hit는 못 만들었지만 demand MSHR과 merge된 경우도 따로 기록한다.
- 이 통계는 FDIP 효과 분석의 핵심이다.

출력 예:

```text
==== L1I Demand Access Breakdown ====
L1I Hit (FDIP Covered)
L1I Hit (Non-Prefetch)
L1I Late Prefetch (Merge)
L1I Merge (Non-Prefetch)
L1I Miss
TOTAL (Direct Count)
Sum of Components
```

## 핵심 Diff 9: TLB to Cache/MEM breakdown 통계

파일:

- `ChampSim_FDIP/inc/cache_stats.h`
- `ChampSim_FDIP/src/cache_stats.cc`
- `ChampSim_FDIP/src/plain_printer.cc`
- `ChampSim_FDIP/src/cache.cc`

핵심 diff:

```diff
+  uint64_t dtlb_hit_L1I_hit = 0;
+  uint64_t dtlb_hit_L1D_hit = 0;
+  uint64_t dtlb_hit_L2C_hit = 0;
+  uint64_t dtlb_hit_LLC_hit = 0;
+  uint64_t dtlb_hit_MEM_hit = 0;
+
+  uint64_t itlb_hit_L1I_hit = 0;
+  uint64_t itlb_hit_L1D_hit = 0;
+  uint64_t itlb_hit_L2C_hit = 0;
+  uint64_t itlb_hit_LLC_hit = 0;
+  uint64_t itlb_hit_MEM_hit = 0;
```

추가로 다음 형태의 counter들이 대량 추가되어 있다.

```text
dtlb_miss_stlb_hit_<final_level>_hit
itlb_miss_stlb_hit_<final_level>_hit
dtlb_miss_stlb_miss_<translation_level>_hit_<final_level>_hit
itlb_miss_stlb_miss_<translation_level>_hit_<final_level>_hit
```

설명:

- DTLB/ITLB hit/miss, STLB hit/miss, translation resolution level, final cache hit level을 결합해서 기록한다.
- output에는 `==== TLB→Cache/MEM Breakdown ====` 섹션으로 출력된다.
- FDIP 자체보다 frontend miss 원인 분석과 instruction fetch latency 분석에 가까운 변경이다.

## 핵심 Diff 10: cache prefetch tracking

파일:

- `ChampSim_DPC4/inc/cache.h`
- `ChampSim_FDIP/inc/cache.h`
- `ChampSim_FDIP/src/cache.cc`

핵심 diff:

```diff
+  bool probe_tag_hit_only(champsim::address addr) const;
+
+  uint64_t pf_interval_useful = 0;
+  uint64_t pf_interval_issued = 0;
+  uint64_t pf_interval_timely = 0;
+  void track_prefetch_issuance();
+  void track_utility_and_timeliness(bool is_useful, bool is_timely);
+
+  uint64_t pf_stats_version = 0;
+  [[nodiscard]] uint64_t get_prefetch_stats_version() const { return pf_stats_version; }
+  [[nodiscard]] std::pair<double, double> get_and_reset_prefetch_stats();
```

설명:

- prefetch가 useful/timely 했는지를 interval 단위로 추적하려는 코드다.
- `probe_tag_hit_only()`는 cache tag hit 여부만 검사하는 helper이다.
- FTQ size 조절이나 prefetch throttling으로 확장하기 위한 기반으로 보인다.

## 핵심 Diff 11: DPC4 API 제거 및 FTQ CLI 추가

파일:

- `ChampSim_DPC4/src/main.cc`
- `ChampSim_FDIP/src/main.cc`

핵심 diff:

```diff
-#include "dpc_api.h"
```

```diff
-uint8_t get_dram_bw()
-{
-  MEMORY_CONTROLLER& mc = g_env->dram_view();
-  return mc.get_bw();
-}
-
-long long get_retired_insts(uint8_t cpu_id)
-{
-  assert(cpu_id < NUM_CPUS);
-  O3_CPU& cpu = g_env->cpu_view().at(cpu_id);
-  return cpu.num_retired;
-}
```

```diff
+extern uint32_t FTQ_SIZE;
+app.add_option("--ftq_size", FTQ_SIZE, "Set the FTQ size");
```

설명:

- `ChampSim_DPC4`는 DPC4 API(`get_dram_bw`, `get_retired_insts`)를 제공한다.
- `ChampSim_FDIP`에서는 이 API가 제거되어 있다.
- 대신 FDIP 실험을 위해 `--ftq_size` runtime option이 추가됐다.
- 이 차이 때문에 DPC4 prefetcher가 DPC4 API를 기대한다면 FDIP 쪽에서 그대로 동작하지 않을 수 있다.

## 핵심 Diff 12: configuration 변경

파일:

- `ChampSim_DPC4/champsim_config.json`
- `ChampSim_FDIP/champsim_config.json`

핵심 diff:

```diff
-      "decode_buffer_size": 32,
+      "decode_buffer_size": 192,
-      "register_file_size": 128,
+      "register_file_size": 280,
-      "fetch_width": 6,
+      "fetch_width": 8,
-      "decode_width": 6,
+      "decode_width": 4,
-      "dispatch_width": 6,
+      "dispatch_width": 5,
-      "execute_width": 4,
+      "execute_width": 10,
-      "scheduler_size": 128,
+      "scheduler_size": 160,
-      "execute_latency": 0,
+      "execute_latency": 1,
```

```diff
-    "prefetcher": "no"
+    "prefetcher": "ip_stride"
```

위 prefetcher 변경은 `L1D`와 `L2C`에 적용되어 있다.

```diff
-    "latency": 10,
+    "hit_latency": 9,
+    "fill_latency": 1,
```

```diff
-    "latency": 20,
+    "hit_latency": 29,
+    "fill_latency": 1,
```

```diff
-    "tCAS": 24,
-    "tRCD": 24,
-    "tRP": 24,
-    "tRAS": 52,
+    "tCAS": 12.5,
+    "tRCD": 12.5,
+    "tRP": 12.5,
+    "tRAS": 25,
```

설명:

- FDIP 버전은 frontend/backend width, register file, scheduler, latency, DRAM timing이 DPC4 기준과 다르다.
- 또한 L1D/L2C data prefetcher가 `ip_stride`로 켜져 있다.
- 따라서 `ChampSim_DPC4`와 `ChampSim_FDIP`를 그대로 비교하면 FDIP 효과만 비교하는 것이 아니다.
- FDIP 효과를 보려면 config를 DPC4 기준으로 맞춘 뒤 FDIP on/off만 비교해야 한다.

## 핵심 Diff 13: Makefile 변경

파일:

- `ChampSim_DPC4/Makefile`
- `ChampSim_FDIP/Makefile`

핵심 diff:

```diff
-override ROOT_DIR = ...
-BIN_ROOT:=bin
-OBJ_ROOT:=.csconfig
-DEP_ROOT:=$(OBJ_ROOT)
-override MODULE_ROOT += $(ROOT_DIR)
-override BRANCH_ROOT += ...
-override PREFETCH_ROOT += ...
-override REPLACEMENT_ROOT += ...
```

```diff
+CXX ?= g++
+CXXFLAGS += -Wall -Wextra -Wshadow -Wformat=2 -pedantic -O3 -g -std=c++17
+CXXFLAGS += -Iinc -I.csconfig -Ivcpkg_installed/x64-linux/include
+LDFLAGS += -Lvcpkg_installed/x64-linux/lib
+LDLIBS += -lfmt -lCLI11 -lz -lbz2 -llzma
+
+SRCS := $(wildcard src/*.cc)
+base_module_objs := $(patsubst src/%.cc,obj/%.o,$(SRCS))
```

설명:

- DPC4 Makefile은 원본 ChampSim의 module discovery, legacy bridge, generated config, tests, vcpkg integration을 유지한다.
- FDIP Makefile은 단순 g++ compile/link rule로 크게 축소되어 있다.
- FDIP 폴더 내부에 `vcpkg_installed`가 없으면 빌드가 실패한다.
- 현재 실험에서는 DPC4/ChampSim 쪽 `vcpkg_installed` include/lib를 CXXFLAGS/LDFLAGS로 넘겨 빌드했다.

## 핵심 Diff 14: replacement policy 변경

파일:

- `replacement/drrip/drrip.cc`
- `replacement/drrip/drrip.h`
- `replacement/ship/ship.cc`
- `replacement/ship/ship.h`

DRRIP 핵심 diff:

```diff
-drrip::drrip(...) : ..., brrip_counter(0), ...
+drrip::drrip(...) : ..., rrpv(...)
 {
-  std::fill_n(... PSEL ..., 1 << (PSEL_WIDTH - 1));
+  std::generate_n(std::back_inserter(rand_sets), TOTAL_SDM_SETS, std::knuth_b{1});
+  std::sort(std::begin(rand_sets), std::end(rand_sets));
+  std::fill_n(... PSEL ..., 0);
 }
```

```diff
-void drrip::update_brrip(long set, long way)
+void drrip::update_bip(long set, long way)
```

설명:

- DPC4의 DRRIP와 FDIP의 DRRIP 구현이 다르다.
- FDIP 쪽은 random sampler set 기반으로 leader/follower set을 고르는 형태다.
- `BRRIP`라는 이름 대신 `BIP` 흐름이 들어가 있다.

SHIP 핵심 diff:

```diff
-sampler(get_num_sampled_sets() * NUM_CPUS * NUM_WAY)
+sampler(SAMPLER_SET_FACTOR * NUM_CPUS * NUM_WAY)
+std::generate_n(std::back_inserter(rand_sets), SAMPLER_SET_FACTOR * NUM_CPUS, std::knuth_b{1});
```

설명:

- SHIP도 sampler set 선택 방식이 변경되어 있다.
- replacement policy까지 바뀌었기 때문에 FDIP 성능 비교 시 replacement 차이가 섞일 수 있다.

## 핵심 Diff 15: 분석 스크립트 추가

`ChampSim_FDIP/script`에는 다음 분석 스크립트가 추가되어 있다.

```text
fdip_cover.py
fetch_latency.py
hit_map.py
mispre_tlb.py
stlb_miss_rank.py
```

주요 역할:

- `fdip_cover.py`: `==== L1I Demand Access Breakdown ====`를 읽어서 FDIP coverage report 생성
- `fetch_latency.py`: fetch latency trace 분석
- `hit_map.py`: TLB to cache/memory breakdown heatmap 생성
- `stlb_miss_rank.py`: STLB miss 기준 로그 ranking
- `mispre_tlb.py`: branch misprediction과 ITLB 통계 분석

현재 작업본의 `fdip_cover.py`에는 다음 편의 수정이 들어가 있다.

```diff
+try:
+    import matplotlib.pyplot as plt
+except ModuleNotFoundError:
+    plt = None
```

```diff
+parser.add_argument('-d', '--output-dir', default=None, help='Output directory')
```

설명:

- `matplotlib`이 없는 환경에서도 `.txt` 분석 결과는 만들 수 있게 했다.
- `-d fdip_test`처럼 출력 위치를 지정할 수 있다.

## 해석상 주의점

`ChampSim_DPC4`와 `ChampSim_FDIP`의 차이는 FDIP만이 아니다.

성능 비교에 영향을 줄 수 있는 차이:

- CPU width/buffer/scheduler/register file 크기 변경
- L1D/L2C prefetcher 변경
- L2C/LLC latency 변경
- DRAM timing 변경
- replacement policy 변경
- DPC4 prefetcher 디렉터리 제거
- DPC4 API 제거
- Makefile/build 방식 변경

따라서 FDIP 효과만 보려면 다음 순서가 필요하다.

1. `ChampSim_DPC4` config와 `ChampSim_FDIP` config를 동일하게 맞춘다.
2. L1D/L2C prefetcher를 같은 값으로 맞춘다.
3. replacement policy 구현 차이를 제거하거나 동일 policy를 사용한다.
4. `CHAMPSIM_ENABLE_FDIP=0`으로 baseline을 빌드한다.
5. `CHAMPSIM_ENABLE_FDIP=1`으로 FDIP 버전을 빌드한다.
6. 같은 binary config, 같은 trace, 같은 warmup/simulation instruction으로 비교한다.
7. IPC와 함께 `L1I Demand Access Breakdown`을 본다.

## 결론

`ChampSim_FDIP`의 FDIP 핵심은 다음 네 가지다.

- `FTQ_ENTRY`와 `O3_CPU::FTQ` 추가
- `predict_future_blocks()`로 future instruction block 생성
- `process_ftq()`로 L1I prefetch 발행
- `fdip_l1i_*` counter로 FDIP coverage 분석

하지만 현재 FDIP 폴더는 DPC4 기준에서 다음 변경도 함께 포함한다.

- DPC4 API 제거
- DPC4 prefetcher 일부 제거
- CPU/cache/memory config 변경
- replacement policy 변경
- TLB/cache breakdown 분석 코드 추가
- build system 단순화

그래서 이 폴더는 “DPC4에 FDIP만 얹은 최소 patch”라기보다, FDIP 실험과 frontend/TLB 분석을 위해 별도로 갈라진 연구용 fork에 가깝다.
