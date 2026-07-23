# 2026-07-21 코드 노트: ChampSim_Split L2 구조

이 문서는 `ChampSim_Split`에서 L2 cache를 실제 `L2I`와 `L2D` 하드웨어 구조로 분리하기 위해 반영한 코드 변경을 정리한다. 이전 `ChampSim_FDIP` 실험은 하나의 `L2C` 내부 way를 instruction/data로 나누는 방식이었다. 이번 변경의 목적은 config 단계에서 cache hierarchy 자체를 `L1I -> L2I -> LLC`, `L1D -> L2D -> LLC`로 구성할 수 있게 만드는 것이다.

## 목적

L2C partition 실험은 두 가지 방식으로 모델링할 수 있다.

- 단일 `L2C` 안에서 way만 instruction/data로 나눈다.
- config에서 `L2I`와 `L2D`를 별도 cache object로 만들어 실제 hierarchy를 분리한다.

이번 `ChampSim_Split` 변경은 두 번째 방식이다. `run.sh`의 `-L2C` 옵션은 그대로 사용하되, `ChampSim_Split/config/parse.py`가 `champsim_config.json`의 `L2C.partition`, `instruction_ways`, `data_ways`를 해석해서 shared 또는 split hierarchy를 만든다.

## 핵심 변경

### L2C 호환 계층 해석 추가

`config/parse.py`에 `apply_l2c_compat()`을 추가했다.

```diff
+def apply_l2c_compat(config_file):
+    '''
+    Interpret the legacy run.sh L2C partition fields for split-L2 builds.
+
+    The repository-level run script still emits a single "L2C" object with
+    "partition", "instruction_ways", and "data_ways". For ChampSim_Split, treat
+    "shared" as the original L2C hierarchy and "static" as split L2I/L2D.
+    '''
+    l2c = config_file.get('L2C')
+    if not isinstance(l2c, dict):
+        return config_file, ('L1I', 'L1D', 'ITLB', 'DTLB', 'L2I', 'L2D', 'STLB')
+
+    partition = l2c.get('partition')
+    if partition == 'shared':
+        ...
+        return {**config_file, 'L2C': shared_l2c}, ('L1I', 'L1D', 'ITLB', 'DTLB', 'L2C', 'STLB')
+
+    if partition == 'static':
+        ...
+        return {**config_file, 'L2I': l2i, 'L2D': l2d}, tuple(pinned_cache_names)
```

동작은 다음과 같다.

| `-L2C` 정책 | 구성 |
|---|---|
| `shared` | `L1I/L1D -> L2C -> LLC` |
| `0i8d` | `L1I -> LLC`, `L1D -> L2D -> LLC` |
| `2i6d`, `4i4d`, `6i2d` | `L1I -> L2I -> LLC`, `L1D -> L2D -> LLC` |
| `8i0d` | `L1I -> L2I -> LLC`, `L1D -> LLC` |

zero-way side는 해당 L2 cache를 만들지 않고 LLC로 바로 내려가도록 했다. 예를 들어 `0i8d`는 instruction path에서 L2I를 만들지 않으므로 L1I miss가 L2I를 거치지 않고 LLC로 간다.

### 기본 cache path 확장

`config/defaults.py`는 core의 cache path를 `L2I/L2D` 존재 여부에 따라 다르게 만든다.

```diff
-    yield { 'name': cpu.get('L1I'), 'lower_level': cpu.get('L2C') }
-    yield { 'name': cpu.get('L1D'), 'lower_level': cpu.get('L2C') }
+    l2i = cpu.get('L2I', cpu.get('L2C', 'LLC'))
+    l2d = cpu.get('L2D', cpu.get('L2C', 'LLC'))
+    yield { 'name': cpu.get('L1I'), 'lower_level': l2i }
+    yield { 'name': cpu.get('L1D'), 'lower_level': l2d }
```

PTW는 기존 구조를 유지했다.

```diff
 def ptw_core_defaults(cpu):
     ''' Generate the lower levels that a default core would expect for each of its PTWs '''
     yield { 'name': cpu.get('PTW'), 'lower_level': cpu.get('L1D') }
```

즉, page walk path는 여전히 `L1D` 쪽으로 연결된다. 이번 변경의 목표는 instruction/data cache hierarchy 분리이지 PTW 구조 변경이 아니다.

### L2I/L2D 기본값 추가

`inc/defaults.hpp`에 `default_l2i`, `default_l2d`를 추가했다. 기본 구조는 `default_l2c`와 같은 cache builder 설정을 사용하고, 실제 ways는 config parser가 `instruction_ways`, `data_ways`에 따라 덮어쓴다.

```diff
+const auto default_l2i = champsim::cache_builder<...>{}
+                             .sets_factor(512)
+                             .ways(8)
+                             .pq_size(16)
+                             .offset_bits(champsim::data::bits{LOG2_BLOCK_SIZE})
+                             .reset_prefetch_as_load()
+                             .reset_virtual_prefetch()
+                             .reset_wq_checks_full_addr()
+                             .prefetch_activate(access_type::LOAD, access_type::PREFETCH);
+
+const auto default_l2d = champsim::cache_builder<...>{}
+                             .sets_factor(512)
+                             .ways(8)
+                             .pq_size(16)
+                             .offset_bits(champsim::data::bits{LOG2_BLOCK_SIZE})
+                             .reset_prefetch_as_load()
+                             .reset_virtual_prefetch()
+                             .reset_wq_checks_full_addr()
+                             .prefetch_activate(access_type::LOAD, access_type::PREFETCH);
```

### `run.sh` 호환용 `--ftq_size` 수용

`ChampSim_Split`에는 FDIP/FTQ 구현이 없다. 하지만 root `scripts/run.sh`는 공통 실행 경로에서 `--ftq_size`를 넘긴다. 그래서 `src/main.cc`에서 옵션만 받고 무시하도록 했다.

```diff
  app.add_option("--listeners", requested_listeners, "A list of the listeners to be attached to the run");
+  uint32_t ignored_ftq_size = 0;
+  app.add_option("--ftq_size", ignored_ftq_size, "Accepted for run.sh compatibility; ignored by this ChampSim build");

  app.add_option("traces", trace_names, "The paths to the traces")->required()->expected(NUM_CPUS)->check(CLI::ExistingFile);
```

의미는 명확하다. `-f 0x01`처럼 FTQ 옵션을 주더라도 `ChampSim_Split`에서는 실험 축으로 사용하지 않는다.

## 빌드 관찰

`scripts/setup_champsim.sh -C ChampSim_Split`로 dependency setup을 수행했다. 이후 `absolute.options`에 stale include path가 남아 있어서 vcpkg include 경로를 현재 `ChampSim_Split/vcpkg_installed/x64-linux/include`로 맞춘 뒤 빌드가 진행됐다.

빌드 대상은 run script의 L2C policy binary 이름 규칙을 따른다.

| Policy | Binary 의미 |
|---|---|
| `l2cshared` | 기존 shared `L2C` |
| `l2c0i8d` | instruction L2 bypass, data 8-way L2D |
| `l2c1i7d` | instruction 1-way L2I, data 7-way L2D |
| `l2c2i6d` | instruction 2-way L2I, data 6-way L2D |
| `l2c4i4d` | instruction/data 4-way split |
| `l2c6i2d` | instruction 6-way L2I, data 2-way L2D |
| `l2c8i0d` | instruction 8-way L2I, data L2 bypass |

## 검증 포인트

이번 코드는 단순히 way 범위를 제한하는 것이 아니라 cache object 자체를 바꾸는 코드다. 따라서 raw log에서 다음 구조가 찍히는지를 확인해야 한다.

| Policy | 기대 log section |
|---|---|
| `shared` | `cpu0_L2C`만 존재 |
| `0i8d` | `cpu0_L2D`만 존재 |
| `2i6d`, `4i4d`, `6i2d` | `cpu0_L2I`, `cpu0_L2D` 존재 |
| `8i0d` | `cpu0_L2I`만 존재 |

`260721_2005_w10_i100_champ_split_2g`에서 위 구조가 모두 확인됐다.

## FDIP/L2C Output 의미 호환

`ChampSim_FDIP`와 `ChampSim_Split`는 L2 instruction/data 통계를 표현하는 방식이 다르다. FDIP는 하나의 `cpu0_L2C` 안에서 origin split counter를 찍고, L2C split 모델은 실제 cache object가 분리되어 `cpu0_L2I`, `cpu0_L2D`로 출력된다.

의미상 대응은 다음과 같다.

| FDIP output | L2C split output | Parser field |
|---|---|---|
| `cpu0->cpu0_L2C TOTAL_I`, `LOAD_I`, `RFO_I` | `cpu0->cpu0_L2I TOTAL`, `LOAD`, `RFO` | `l2i_mpki` |
| `cpu0->cpu0_L2C TOTAL_D`, `LOAD_D`, `RFO_D` | `cpu0->cpu0_L2D TOTAL`, `LOAD`, `RFO` | `l2d_mpki` |

따라서 log 문자열을 억지로 동일하게 맞추기보다 `parser/parse_outputs.py`가 두 표현을 같은 의미로 해석하도록 수정했다.

```diff
+def cache_demand_stats(cache_stats, cache, suffix=""):
+    load = cache_stats.get((cache, f"load{suffix}"))
+    rfo = cache_stats.get((cache, f"rfo{suffix}"))
+    if load is None and rfo is None:
+        return None
+    return {
+        "load_access": (load or {}).get("access", 0),
+        "load_miss": (load or {}).get("miss", 0),
+        "rfo_access": (rfo or {}).get("access", 0),
+        "rfo_miss": (rfo or {}).get("miss", 0),
+    }
```

`l2i_mpki`, `l2d_mpki` 계산은 다음 우선순위를 따른다.

- FDIP style `L2C LOAD_I/D`, `RFO_I/D`가 있으면 이를 우선 사용한다.
- 없으면 L2C split style `L2I LOAD/RFO`, `L2D LOAD/RFO`를 사용한다.
- split model에서 `L2C` block이 없으면 `l2c_mpki`는 `L2I + L2D` demand miss 합으로 계산한다.

```diff
+    for origin, (field, split_cache) in l2_split_sources.items():
+        demand = cache_demand_stats(cache_stats, "L2C", f"_{origin}")
+        if demand is None:
+            demand = cache_demand_stats(cache_stats, split_cache)
+        row[field] = "" if demand is None else mpki(demand_misses(demand), instructions)
```

검증은 `sierra.a.6_0004`, `w10 i200`, `2i6d` smoke run으로 수행했다. 해당 log에서는 `cpu0_L2I`와 `cpu0_L2D`가 모두 출력됐고, 파서 결과는 `l2i_mpki = 120.0`, `l2d_mpki = 120.0`, `l2c_mpki = 240.0`으로 계산됐다. smoke output은 검증 후 삭제했다.
