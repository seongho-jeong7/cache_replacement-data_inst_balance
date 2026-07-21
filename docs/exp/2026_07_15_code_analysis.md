# 2026-07-15 Code Analysis: L2C Way Partition과 Latency 모델

## 목적

이 문서는 L2C instruction/data partition 실험을 해석하기 위해, 현재 `ChampSim_FDIP` 코드가 way 수와 latency를 어떻게 모델링하는지 정리한다.

핵심 질문:

- L2C `ways`를 나누면 hit/miss latency도 바뀌는가?
- partition을 적용했을 때 실제 lookup/search 대상 way가 줄어드는가?
- 원래 ChampSim의 L2C/LLC latency 설정은 무엇이었고, 현재 way 기반 search latency 모델은 어떻게 해석해야 하는가?

## 원래 ChampSim의 Cache 설정

원래 `ChampSim/champsim_config.json` 기준:

| Cache | Sets | Ways | Latency |
|---|---:|---:|---:|
| L2C | 1024 | 8 | 10 cycles |
| LLC | 2048 | 16 | 20 cycles |

즉 원래 ChampSim 모델은 대략 `L2C 8-way = 10 cycles`, `LLC 16-way = 20 cycles`로 설정되어 있었다. 이 latency는 `ways`에서 자동 계산되는 값이 아니라 config에 명시된 고정값이다.

## 현재 ChampSim_FDIP의 Cache 설정

현재 `ChampSim_FDIP/champsim_config.json` 기준:

```json
"L2C": {
    "sets": 1024,
    "ways": 8,
    "partition": "shared",
    "instruction_ways": 4,
    "data_ways": 4,
    "hit_latency": 8,
    "fill_latency": 1
}
```

LLC는 다음과 같다.

```json
"LLC": {
    "sets": 2048,
    "ways": 16,
    "hit_latency": 16,
    "fill_latency": 1
}
```

L2C 전체 way 수는 8이고, 실험에서는 이 8 way를 다음처럼 나누었다.

| Policy | Instruction ways | Data ways |
|---|---:|---:|
| shared | 공유 | 공유 |
| 0i8d | 0 | 8 |
| 1i7d | 1 | 7 |
| 2i6d | 2 | 6 |
| 4i4d | 4 | 4 |
| 6i2d | 6 | 2 |
| 8i0d | 8 | 0 |

## Way 수가 Hit/Miss에 미치는 영향

실제 cache에서 way 수는 두 가지 측면에 영향을 줄 수 있다.

첫째, capacity/conflict 측면이다. Way가 많으면 같은 set 안에 더 많은 line을 보관할 수 있으므로 conflict miss가 줄 수 있다. ChampSim에서도 `ways`를 바꾸면 cache block 수와 replacement 대상이 바뀌므로 MPKI에 영향을 준다.

둘째, lookup/search latency 측면이다. 실제 하드웨어에서는 더 많은 way를 비교하면 tag comparator 수, way mux, banking 구조, timing, energy가 달라질 수 있다. 다만 8-way가 16-way가 된다고 latency가 정확히 2배가 되는 것은 아니다. tag 비교는 병렬로 수행될 수 있고, 설계에 따라 latency 증가는 작을 수도 있고 클 수도 있다.

현재 ChampSim 모델에서는 이 둘이 분리되어 있다.

- `ways`: cache capacity, conflict, replacement에 영향
- `hit_latency`: access delay에 영향

따라서 `ways`를 8에서 16으로 바꿔도 `hit_latency`를 바꾸지 않으면 lookup delay는 그대로다.

## 현재 L2C Partition 모델의 Search Latency

수정 후 L2C partition은 capacity뿐 아니라 search latency도 함께 바꾸는 모델이다. 기본 가정은 단순하게 둔다.

- way당 search cost: 1 cycle
- fill cost: 1 cycle
- shared L2C: instruction/data 모두 전체 8 way를 search한다.
- static partition: instruction/data가 자기에게 할당된 way만 search한다.
- `0i8d`: instruction은 L2C search/fill을 건너뛰고 LLC로 내려간다.
- `8i0d`: data는 L2C search/fill을 건너뛰고 LLC로 내려간다.

따라서 L2C search latency는 다음처럼 해석한다.

| Policy | Instruction search | Data search |
|---|---:|---:|
| shared | 8 cycles | 8 cycles |
| 0i8d | 0 cycles, L2C bypass | 8 cycles |
| 1i7d | 1 cycle | 7 cycles |
| 2i6d | 2 cycles | 6 cycles |
| 4i4d | 4 cycles | 4 cycles |
| 6i2d | 6 cycles | 2 cycles |
| 8i0d | 8 cycles | 0 cycles, L2C bypass |

코드 기준으로는 `CACHE::effective_l2c_search_latency()`가 L2C policy와 request origin(`is_instr_fetch`)을 보고 tag check 완료 시점을 계산한다. `CACHE::try_hit()`과 `probe_tag_hit_only()`도 partition 범위 안에서만 hit를 찾도록 맞췄다.

즉 현재 모델의 의미는 다음과 같다.

- shared: 전체 8 way를 공유하고, 전체 8-cycle search latency를 지불한다.
- `1i7d`, `2i6d`, `4i4d`, `6i2d`: fill/victim way뿐 아니라 lookup range와 search latency도 instruction/data 영역으로 제한한다.
- `0i8d`: instruction line은 L2C에 저장하지 않고, L2C search/fill도 지불하지 않는다.
- `8i0d`: data line은 L2C에 저장하지 않고, L2C search/fill도 지불하지 않는다.

## L2C/LLC Search Latency 설정

현재 `ChampSim_FDIP`에서 L2C는 `hit_latency=8`, `fill_latency=1`로 설정되어 있다. 여기서 `hit_latency`는 실험 해석상 `search_latency`에 가깝다. LLC는 16-way이므로 같은 가정에 맞춰 `hit_latency=16`, `fill_latency=1`로 설정한다.

변경 이력:

- 원래 ChampSim: `L2C latency = 10`, `LLC latency = 20`
- FDIP 적용 commit `5c1922971c8f58bb6706f73b4fe1563b73c02605`: `L2C latency 10 -> hit_latency 9 + fill_latency 1`, `LLC latency 20 -> hit_latency 29 + fill_latency 1`
- L2C partition 실험 과정에서 `hit_latency`를 way 기반 search latency로 재해석하면서 L2C `8`, LLC `16`으로 조정했다.

따라서 현재 값은 원래 ChampSim baseline을 그대로 보존하기 위한 값이 아니라, "way당 1cycle search + fill 1cycle"이라는 명시적 실험 모델이다.

## Fill Latency의 의미

`fill_latency`는 lower level에서 data가 돌아온 뒤, 현재 cache에 block을 채우고 upper level로 응답하기까지의 추가 지연을 모델링한다.

코드 흐름은 다음과 같다.

1. Request가 cache에 들어오면 tag check가 시작된다.
2. `CACHE::initiate_tag_check()`에서 tag check 완료 시점이 `base_now + effective_l2c_search_latency()`로 설정된다.
3. Tag check가 끝났을 때 hit이면 `CACHE::try_hit()`에서 바로 upper level로 response를 보낸다.
4. Miss이면 `CACHE::handle_miss()`에서 MSHR을 할당하고 lower level RQ/PQ로 request를 보낸다.
5. Lower level에서 data가 돌아오면 `CACHE::finish_packet()`이 호출된다.
6. 이때 MSHR entry의 `data_promise`가 `current_time + FILL_LATENCY`에 ready 되도록 설정된다.
7. 이후 `CACHE::handle_fill()`이 ready 된 MSHR을 cache block에 채우고 upper level로 response를 보낸다.

즉 miss path의 latency는 단순히 L2C `hit_latency` 하나가 아니다.

대략적인 흐름:

```text
L2C access
  -> L2C search latency 동안 tag lookup
  -> miss 판정
  -> lower level로 request 전달
  -> lower level hit/miss/DRAM latency
  -> lower level response가 L2C로 돌아옴
  -> L2C FILL_LATENCY
  -> L2C fill 및 upper level response
```

따라서 L2C miss일 때는 다음 비용이 포함된다.

- L2C tag lookup latency
- lower level에서 처리되는 latency
- L2C fill latency
- queue/MSHR/bandwidth contention에 따른 추가 대기

현재 L2C 설정에서는 `hit_latency=8`, `fill_latency=1`이다. 여기서 `hit_latency`는 전체 8-way shared lookup의 기본 search latency로 해석한다. Static partition에서는 실제 tag check delay가 config의 고정 `hit_latency` 대신 request origin에 할당된 way 수로 계산된다.

## Fill 분리 전후의 L2C Hit/Miss Latency 비교

원래 ChampSim config에서는 L2C가 다음처럼 설정되어 있었다.

```json
"L2C": {
    "ways": 8,
    "latency": 10
}
```

현재 `ChampSim_FDIP`에서는 다음처럼 나뉘어 있다.

```json
"L2C": {
    "ways": 8,
    "hit_latency": 9,
    "fill_latency": 1
}
```

### L2C Hit Case

L2C hit인 경우 lower level로 내려가지 않는다.

분리 전:

```text
L2C access -> latency 10 -> response
총 L2C hit 비용: 10 cycles
```

분리 후:

```text
L2C access -> hit_latency 9 -> response
총 L2C hit 비용: 9 cycles
```

즉 hit case에서는 L2C latency가 `10 -> 9`로 1 cycle 줄었다.

### L2C Miss Case

L2C miss인 경우 L2C에서 tag lookup을 한 뒤 lower level로 request를 보내고, lower level response가 돌아온 뒤 L2C에 fill한다.

분리 전의 개념적 모델:

```text
L2C access -> latency 10 -> miss 판정
          -> lower level latency
          -> response/fill
```

단순화하면:

```text
총 miss path 비용 = L2C 10 + lower level latency
```

분리 후:

```text
L2C access -> hit_latency 9 -> miss 판정
          -> lower level latency
          -> fill_latency 1
          -> fill 및 response
```

단순화하면:

```text
총 miss path 비용 = L2C hit_latency 9 + lower level latency + L2C fill_latency 1
                 = 10 + lower level latency
```

따라서 miss case에서는 이상적으로 총 L2C 자체 비용이 `9 + 1 = 10 cycles`로 유지된다.

### 수치 예시

lower level latency를 `X`라고 두면:

| Case | 분리 전 | 분리 후 | 차이 |
|---|---:|---:|---:|
| L2C hit | 10 | 8 | -2 |
| L2C miss | 10 + X | 8 + X + 1 | -1 |

즉 현재 way 기반 search 모델에서는 L2C shared hit은 원래보다 2 cycles 짧고, L2C miss의 local L2C 비용은 `8 + 1 = 9 cycles`가 된다. 이 값은 원래 `10 cycles`를 보존하는 모델이 아니라, 8-way search cost를 직접 반영한 실험 모델이다.

다만 실제 시뮬레이션에서는 queue, MSHR, bandwidth, lower-level return timing 때문에 정확히 이 단순식만으로 모든 request latency가 결정되지는 않는다. 그래도 모델의 의도는 `hit path`와 `miss fill path`를 분리하는 것이다.

## L2C Miss에서 X의 구성

앞 절에서 `X`라고 둔 값은 L2C 아래 lower level에서 request가 처리되어 L2C로 response가 돌아오기까지의 시간이다. 현재 hierarchy에서 L2C의 lower level은 LLC다.

현재 config:

| Level | Hit latency | Fill latency | Ways |
|---|---:|---:|---:|
| L2C | 8 | 1 | 8 |
| LLC | 16 | 1 | 16 |

### L2C Miss + LLC Hit

L2C에서 miss가 나고 LLC에서 hit가 나는 경우:

```text
L2C tag lookup: 8
LLC tag lookup and hit response: 16
L2C fill: 1
```

따라서 queue/bandwidth 대기를 제외한 기본 비용은:

```text
8 + 16 + 1 = 25 cycles
```

이 경우 앞 절의 `X`는 LLC hit/search latency인 `16 cycles`다.

```text
L2C miss cost = L2C search_latency 8 + X + L2C fill_latency 1
              = 8 + 16 + 1
              = 25 cycles
```

### L2C Miss + LLC Miss + DRAM

L2C에서 miss가 나고 LLC에서도 miss가 나면 DRAM까지 내려간다.

```text
L2C tag lookup: 8
LLC tag lookup: 16
DRAM service: memory-system dependent
LLC fill: 1
L2C fill: 1
```

따라서 기본 구조는:

```text
8 + 16 + DRAM_service + 1 + 1
= 26 + DRAM_service cycles
```

이 경우 앞 절의 `X`는 다음과 같다.

```text
X = LLC search_latency 16 + DRAM_service + LLC fill_latency 1
```

DRAM service는 고정 상수가 아니다. 현재 physical memory config에는 다음 timing이 있다.

```json
"data_rate": 3200,
"channels": 1,
"ranks": 1,
"bankgroups": 8,
"banks": 4,
"tCAS": 12.5,
"tRCD": 12.5,
"tRP": 12.5,
"tRAS": 25
```

DRAM에서는 row buffer 상태, bank/channel queue, read/write turnaround, refresh, request contention에 따라 실제 service time이 달라진다. 따라서 LLC miss 이후의 DRAM 지연은 `tCAS + tRCD + ...` 같은 단일 고정값으로만 표현하기 어렵고, memory controller의 동적 상태에 의해 결정된다.

## DRAM Service Time 계산 방식

현재 generated config에서는 DRAM controller가 다음 값으로 생성되어 있다.

```cpp
DRAM{
  champsim::chrono::picoseconds{312}, // data bus period
  champsim::chrono::picoseconds{625}, // memory controller period
  std::size_t{12}, // tRP
  std::size_t{12}, // tRCD
  std::size_t{12}, // tCAS
  std::size_t{25}, // tRAS
  ...
}
```

`champsim_config.json`에는 `tCAS`, `tRCD`, `tRP`가 `12.5`로 적혀 있지만, config generator가 `int()`로 넘기기 때문에 실제 generated C++에서는 `12` memory-controller cycles로 들어간다.

현재 timing 단위:

| 항목 | 값 |
|---|---:|
| CPU clock period | 250 ps (`4000 MHz`) |
| Memory controller period | 625 ps (`1600 MHz`) |
| Data bus period | 312 ps (`3200 MT/s`) |
| DRAM prefetch size | 8 transfers (`64B block / 8B channel_width`) |
| DRAM data bus return time | `312 ps * 8 = 2496 ps` |

CPU cycle로 환산하면:

| 항목 | ps | CPU cycles |
|---|---:|---:|
| 1 memory-controller cycle | 625 ps | 2.5 cycles |
| tCAS 12 cycles | 7500 ps | 30 cycles |
| tRCD 12 cycles | 7500 ps | 30 cycles |
| tRP 12 cycles | 7500 ps | 30 cycles |
| data bus return | 2496 ps | 약 10 cycles |

### Bank scheduling

DRAM request가 queue에서 선택되면 `DRAM_CHANNEL::service_packet()`에서 target row와 현재 open row를 비교한다.

```cpp
bool row_buffer_hit = (open_row exists && open_row == op_row);
row_charge_delay = open_row exists ? tRP + tRCD : tRCD;
ready_time = current_time + tCAS + (row_buffer_hit ? 0 : row_charge_delay);
```

따라서 bank 내부에서 data bus에 올라갈 준비가 되는 시간은 다음과 같다.

| Case | Bank ready time |
|---|---:|
| Row buffer hit | `tCAS` |
| Row miss, open row 없음 | `tRCD + tCAS` |
| Row conflict, 다른 row 열림 | `tRP + tRCD + tCAS` |

현재 수치로는:

| Case | Memory-controller cycles | CPU cycles |
|---|---:|---:|
| Row buffer hit | 12 | 30 |
| Row miss, no open row | 24 | 60 |
| Row conflict | 36 | 90 |

### Data bus return

Bank request가 ready 되면 `DRAM_CHANNEL::populate_dbus()`에서 data bus에 올린다. 이때 response ready time은 다음처럼 잡힌다.

```cpp
if (bankgroup_ready_time > current_time)
  ready_time = bankgroup_ready_time + DRAM_DBUS_RETURN_TIME;
else
  ready_time = current_time + DRAM_DBUS_RETURN_TIME;
```

현재 `DRAM_DBUS_RETURN_TIME`은:

```text
data_bus_period * prefetch_size = 312 ps * 8 = 2496 ps
```

이는 약 `4` memory-controller cycles, 또는 약 `10` CPU cycles에 해당한다.

### Queue와 contention을 제외한 최소 DRAM service time

따라서 request가 바로 scheduling되고, data bus도 바로 사용할 수 있다고 가정하면 최소 DRAM service time은 다음과 같다.

| Case | 구성 | Memory-controller cycles | CPU cycles |
|---|---|---:|---:|
| Row buffer hit | `tCAS + dbus_return` | 약 16 | 약 40 |
| Row miss, no open row | `tRCD + tCAS + dbus_return` | 약 28 | 약 70 |
| Row conflict | `tRP + tRCD + tCAS + dbus_return` | 약 40 | 약 100 |

하지만 실제 service time은 이보다 길어질 수 있다. 이유는 다음과 같다.

- RQ/WQ queue에서 기다릴 수 있다.
- 같은 bank가 이미 busy이면 scheduling되지 못한다.
- data bus가 busy이면 `populate_dbus()`에서 기다린다.
- 같은 bankgroup의 data bus cooldown이 있으면 `bankgroup_readytime` 이후로 밀린다.
- read/write mode 전환 시 `DRAM_DBUS_TURN_AROUND_TIME`이 들어간다.
- refresh가 걸리면 bank가 `tRFC` 동안 막힌다.

따라서 LLC miss의 `DRAM_service`는 고정 상수가 아니라 다음처럼 볼 수 있다.

```text
DRAM_service =
  queue_wait
+ bank_activate/precharge/CAS time
+ data_bus_wait
+ data_bus_return
+ bankgroup_stall
+ optional write_turnaround
+ optional refresh_delay
```

현재 실험에서 L2C miss가 LLC miss까지 내려가면, 최소 비용은 다음처럼 해석할 수 있다.

```text
L2C miss + LLC miss + DRAM row hit
  = L2C 8 + LLC 16 + DRAM row-hit service 약 40 cycles + LLC fill 1 + L2C fill 1
  = 약 66 CPU cycles + queue/contention
```

row miss 또는 row conflict이면 DRAM service가 각각 약 70 cycles, 약 100 cycles 이상으로 커진다.

### 분리 전 원래 ChampSim과 비교

원래 ChampSim config를 단순화하면:

| Level | Latency |
|---|---:|
| L2C | 10 |
| LLC | 20 |

따라서 원래 설정의 단순 기본 비용은:

```text
L2C hit = 10
L2C miss + LLC hit = 10 + 20 = 30
L2C miss + LLC miss = 10 + 20 + DRAM_service
```

현재 way 기반 search config에서는:

```text
L2C hit = 8
L2C miss + LLC hit = 8 + 16 + 1 = 25
L2C miss + LLC miss = 8 + 16 + DRAM_service + 1 + 1
                    = 26 + DRAM_service
```

즉 현재 설정은 원래 ChampSim의 총 latency를 보존하는 모델이 아니라, way 수를 search latency로 직접 해석한 모델이다. 이 모델에서는 shared 8-way L2C보다 16-way LLC가 더 오래 걸리지만, 원래 FDIP artifact의 `LLC hit_latency=29`보다는 LLC 비용이 작다.

## 0i8d/8i0d에서의 Bypass Path

현재 `0i8d`는 instruction line을 L2C에 저장하지 않고, instruction request의 L2C search/fill latency도 0으로 둔다. `8i0d`는 같은 동작을 data request에 적용한다.

현재 코드 기준:

- `bypasses_l2c_access()`는 L2C에서 해당 origin의 way 수가 0이면 true가 된다.
- bypass된 request는 L2C hit search를 하지 않고 miss path로 lower level에 내려간다.
- `effective_l2c_search_latency()`는 bypass origin에 대해 0 cycle을 반환한다.
- lower level에서 돌아온 뒤 `handle_fill()`의 bypass branch에서 L2C block fill 없이 upper level로 response를 보낸다.
- `8i0d`에서 L1D writeback이 L2C에 채워지는 것을 막기 위해, bypass writeback은 lower-level WQ로 전달한다.

즉 `0i8d`/`8i0d`는 해당 origin에 대해 L2C search/fill을 제거하고 LLC cost만 남기는 control point다.

## 해석상 주의점

수정 전 결과는 partition의 capacity 효과를 주로 보여줬다. 수정 후 결과는 capacity 효과와 함께 partition별 search latency 차이도 포함한다.

따라서 현재 결과를 해석할 때는 다음처럼 표현하는 것이 정확하다.

- 현재 새 실험은 L2C capacity interference와 search latency 변화를 함께 본다.
- 이전 결과와 직접 비교할 때는 latency 모델이 달라졌다는 점을 명시해야 한다.
- partition별 search latency를 넣으면 적은 way를 쓰는 쪽의 hit/search 비용이 줄어들기 때문에, 이전보다 static partition의 이득이 더 크게 보일 수 있다.

## 물리 Cache 관점에서 Ways와 Latency

실제 물리 cache에서 latency는 way 수만으로 결정되지 않는다. Way 수가 늘어나면 tag comparator, way select mux, data mux, metadata update 비용이 증가할 수 있지만, 대부분의 set-associative cache는 여러 way를 병렬로 tag compare하도록 설계할 수 있다.

따라서 `8-way -> 16-way`가 된다고 hit latency가 정확히 2배가 되는 것은 아니다. 실제 latency는 다음 요소의 영향을 함께 받는다.

- cache 총 용량
- set 수와 way 수
- tag/data array 크기
- banking/slicing 구조
- tag compare 병렬성
- way select mux 비용
- wire delay와 physical distance
- pipeline stage 수
- port 수와 access bandwidth
- LLC의 경우 slice/interconnect/coherence 경로

L2C와 LLC를 비교할 때, LLC가 L2C보다 느린 것은 자연스럽다. LLC는 보통 더 크고, 더 멀고, slice 또는 bank 구조를 가지며, interconnect/coherence 비용도 포함될 수 있기 때문이다. 하지만 그 차이가 "ways가 2배라서 latency도 2배"라고 단순화되는 것은 물리적으로 과하다.

현재 config 변경을 보면:

| Model | L2C | LLC |
|---|---:|---:|
| 원래 ChampSim | 8-way, latency 10 | 16-way, latency 20 |
| fill 분리 유지 모델 | hit 9 + fill 1 | hit 19 + fill 1 |
| 현재 way 기반 search 모델 | search 8 + fill 1 | search 16 + fill 1 |

원래 ChampSim 자체는 L2C 8-way와 LLC 16-way의 latency를 `10 -> 20`으로 두었으므로, 겉으로는 LLC를 L2C보다 2배 느리게 잡은 셈이다. 이것이 way 수 2배 때문이라고 추측할 수는 있지만, 원래 ChampSim config가 물리 cache model에서 자동 산출한 값은 아니다. 사람이 정한 architectural parameter에 가깝다.

만약 원래 ChampSim baseline을 보존하려면, fill을 분리한 뒤에는 다음 설정이 더 일관적이다.

```text
L2C: hit_latency 9, fill_latency 1
LLC: hit_latency 19, fill_latency 1
```

이렇게 하면 L2C miss-side local cost는 `9 + 1 = 10`, LLC miss-side local cost는 `19 + 1 = 20`으로 원래 config와 맞는다.

반대로 FDIP artifact에서 들어왔던 `LLC hit_latency 29, fill_latency 1`은 LLC local miss-side cost를 `30`으로 만들었다. 이는 원래 ChampSim보다 LLC를 10 cycles 더 느리게 만든다. 현재는 이 값을 way 기반 search 모델에 맞춰 `16 + 1`로 조정했다.

정리하면:

- 물리 cache에서는 way가 늘면 latency가 증가할 수 있다.
- 하지만 way가 2배라고 latency가 정확히 2배가 되지는 않는다.
- 원래 ChampSim과 공정하게 비교하려면 `LLC hit_latency 19 + fill_latency 1`이 더 자연스럽다.
- way 기반 search 모델을 실험하려면 현재처럼 `L2C search 8`, `LLC search 16`으로 두는 것이 더 일관적이다.
- 실제 물리 latency까지 주장하려면 CACTI 같은 cache modeling tool 또는 논문/프로세서 기반 latency 근거가 필요하다.

## FDIP 논문과 Cache Latency 모델의 관계

FDIP 계열 논문에서 핵심은 branch predictor/BTB가 fetch engine보다 앞서 미래 fetch target을 만들고, FTQ에 쌓인 미래 fetch block을 이용해 L1I prefetch를 발행하는 구조다. 즉 논문의 중심은 frontend prefetch mechanism, FTQ, BTB reach, branch target tracking이다.

`Fetch-Directed Instruction Prefetching Revisited`는 FDIP의 기본 구조를 설명하면서, branch-prediction unit이 fetch engine보다 앞서 future control flow를 예측하고 FTQ를 통해 prefetch candidate를 만든다고 설명한다. 또한 FTQ의 non-head entry가 future fetch address가 되며, FDIP가 해당 L1I block이 없으면 higher cache level에서 L1I로 prefetch한다고 설명한다.

하지만 이 논문은 L2C/LLC의 `hit_latency`, `fill_latency`, way 수에 따른 cache access latency를 구체적으로 정의하지 않는다. 논문에서 말하는 partition도 L2C instruction/data partition이 아니라, BTB storage를 줄이기 위한 partitioned BTB 구조에 가깝다.

따라서 현재 논의 중인 내용:

- L2C/LLC search latency를 way 수에 연결할지 여부
- fill latency를 1 cycle로 둘지 여부
- `0i8d`/`8i0d`에서 L2C search/fill을 bypass할지 여부

이것들은 FDIP 논문에서 직접 정해준 값이라기보다, ChampSim/FDIP artifact config와 우리가 만든 L2C partition 모델의 시뮬레이션 가정이다.

정리하면:

- FDIP 논문은 "왜 instruction prefetch를 할 것인가"와 "FTQ/BTB를 어떻게 활용할 것인가"를 설명한다.
- Cache level별 hit/fill latency는 FDIP 알고리즘 자체의 핵심 정의가 아니다.
- L2C/LLC latency를 물리적으로 주장하려면 FDIP 논문보다 CACTI, 실제 프로세서 공개 문서, 또는 별도 cache timing model 근거가 필요하다.

## 이번 수정으로 확정한 모델

위 분석을 바탕으로, 이번 코드 수정에서는 L2C instruction/data partition을 단순한 capacity 분리로만 보지 않고, 실제로 자기 partition만 lookup한다는 가정을 latency 모델에도 반영했다.

이전 구현에서는 `2i6d`, `4i4d`, `6i2d`처럼 L2C way를 나누어도 tag lookup delay는 shared와 동일하게 고정되어 있었다. 따라서 partition으로 인한 capacity 변화는 볼 수 있었지만, 더 적은 way를 검색할 때 lookup latency가 줄어드는 효과는 반영되지 않았다.

수정 후 모델은 다음 가정을 사용한다.

- L2C/LLC lookup cost는 way당 1 cycle로 둔다.
- Fill cost는 cache level과 관계없이 1 cycle로 둔다.
- Shared L2C에서는 instruction/data 모두 전체 8 way를 lookup한다.
- Static partition에서는 instruction/data가 자기에게 할당된 way만 lookup한다.
- `0i8d`에서는 instruction access가 L2C lookup/fill을 건너뛰고 LLC로 내려간다.
- `8i0d`에서는 data access가 L2C lookup/fill을 건너뛰고 LLC로 내려간다.

코드 변경의 핵심은 다음과 같다.

- `CACHE::effective_l2c_search_latency()`를 추가해 L2C request origin별 lookup latency를 계산한다.
- `CACHE::try_hit()`과 `probe_tag_hit_only()`가 partition 범위 안에서만 hit를 찾도록 변경했다.
- 기존 instruction 전용 bypass를 `bypasses_l2c_access()`로 일반화해 `0i8d`와 `8i0d`를 모두 처리한다.
- `8i0d`에서 L1D writeback이 L2C에 fill되는 것을 막기 위해 bypass writeback을 lower-level WQ로 전달한다.
- Base config는 L2C `8 + 1`, LLC `16 + 1`로 조정했다.

현재 config field 이름은 아직 `hit_latency`지만, 이 실험 문맥에서는 `lookup_latency` 또는 `search_latency`에 가까운 의미로 해석한다. 이후 config/parser 호환성을 유지하면서 `lookup_latency` 이름으로 옮기는 것도 가능하다.

## 다음 모델링 방향

더 정교한 모델을 만들려면 다음 중 하나를 선택할 수 있다.

1. 현재 way 기반 lookup latency 모델로 `0i8d`, `1i7d`, `2i6d`, `4i4d`, `6i2d`, `8i0d`를 다시 실험한다.
2. 원래 ChampSim baseline 보존 모델(`L2C 9+1`, `LLC 19+1`)과 별도 비교해 latency 가정의 영향을 분리한다.
3. `hit_latency` field를 `lookup_latency`로 옮기되, 기존 config 호환성을 위해 fallback을 유지한다.
4. CACTI 같은 cache modeling tool로 way/sets/size별 latency를 추정하고 config에 반영한다.
5. Static partition 대신 workload phase에 따라 instruction/data way 또는 bypass 여부를 바꾸는 동적 정책을 검토한다.

---

## 2026-07-16 진행사항: `8i0d` abort 원인 분석과 debug 수정

### 문제 상황

`260716_1305_w10_i20_latency_test`에서 `8i0d` policy가 대부분의 trace에서 `exit 134`로 실패했다. 대표 로그는 다음과 같다.

```text
[cpu0_L2C_MSHR] finish_packet cannot find a matching entry! address: 0x1747a07a8 v_address: 0x0
champsim_l2c8i0d: src/cache.cc:1346: void CACHE::finish_packet(const response_type&): Assertion `0' failed.
```

`8i0d`는 data access가 L2C를 bypass하고 LLC로 바로 내려가는 정책이다. 따라서 L2C가 data request를 직접 fill하지 않아야 한다. 그런데 lower level에서 response가 L2C로 돌아왔을 때, L2C MSHR에 해당 address를 기다리는 entry가 없어 assert가 발생했다.

원본 `ChampSim_FDIP`는 다른 실험에서 사용 중이므로 빌드하거나 수정하지 않았다. 대신 `ChampSim_FDIP_debug` 복사본을 만들고, debug copy에서만 빌드와 재현 실험을 진행했다. 복사 과정에서 `.git`은 제외했고, `absolute.options`도 debug copy의 `inc`/`vcpkg_installed`를 보도록 수정했다.

### 원인 분석

원인은 두 단계로 좁혀졌다.

첫 번째 후보는 bypassed request가 lower level completion을 받을 MSHR 없이 내려가는 경우였다. 특히 L2C bypass path에서 response를 기다리지 않는 prefetch가 먼저 lower queue에 들어가고, 나중에 같은 block에 대한 demand가 lower queue에서 merge되면 lower level은 response를 L2C로 돌려줄 수 있다. 이때 L2C에는 matching MSHR이 없으므로 `finish_packet()` assert가 발생할 수 있다.

이를 막기 위해 debug copy에서는 L2C bypass request가 lower level로 내려갈 때 completion을 drain할 수 있도록 `response_requested=true`를 강제하고 MSHR을 잡도록 했다.

```cpp
auto mshr_pkt = mshr_and_forward_packet(handle_pkt);
if (l2c_bypass) {
  mshr_pkt.second.response_requested = true;
}
```

하지만 이 수정만으로는 실패가 계속 재현됐다.

두 번째 원인은 bypass writeback 경로였다. `handle_write()`에서 `8i0d` data writeback을 lower-level WQ로 넘길 때, `request_type`의 기본값 때문에 `response_requested`가 `true`로 남아 있었다. Writeback은 response를 요구하면 안 되는데, 이 flag가 켜진 상태로 WQ에 들어가면 이후 WQ forwarding/collision 경로에서 L2C로 response가 생길 수 있다. 이 response 역시 L2C MSHR에 matching entry가 없어서 같은 assert를 유발한다.

따라서 debug copy에서는 bypass writeback에 대해 명시적으로 response를 끄도록 수정했다.

```cpp
writeback_packet.type = access_type::WRITE;
writeback_packet.instr = handle_pkt.instr;
writeback_packet.is_instr_fetch = handle_pkt.is_instr_fetch;
writeback_packet.response_requested = false;
return lower_level->add_wq(writeback_packet);
```

### 수정 방향

현재 debug copy의 수정 의미는 다음과 같다.

- Bypassed demand/prefetch request는 L2C에 fill되지는 않지만, lower completion을 안전하게 drain하기 위해 L2C MSHR entry를 가진다.
- Bypassed writeback은 lower-level WQ로 전달하되, response를 요구하지 않는다.
- 따라서 `8i0d`에서 data는 L2C tag lookup/fill/stat access를 만들지 않고 LLC로 내려가며, lower response가 L2C로 돌아오는 경우에도 MSHR mismatch assert가 나지 않는다.

### 검증

먼저 기존 실패와 같은 단일 trace를 debug binary로 재실행했다.

```bash
./scripts/run.sh -C ChampSim_FDIP_debug -t \
  -T codex_debug_8i0d_one.txt \
  -L2C 0x40 -f 0x01 \
  -w 1000000 -i 2000000 -p 1 \
  -r codex_debug_8i0d_test2
```

결과:

- `bravo.a_0000` 정상 완료
- `Simulation complete CPU 0 instructions: 2000002 cycles: 6308480 cumulative IPC: 0.317`
- `finish_packet cannot find a matching entry` assert 재현되지 않음
- `cpu0_L2C LOAD_D/RFO_D/PREFETCH_D/WRITE_D ACCESS`는 모두 0으로 유지됨
- LLC에는 `LOAD_D` traffic이 관측되어 data가 L2C를 우회해 LLC로 내려간 것을 확인함

추가로 `8i0d`에서 L1D miss와 writeback이 LLC로 제대로 전달되는지도 확인했다. Debug run의 `bravo.a_0000` 결과에서는 L2C data-side access가 모두 0으로 유지되는 동시에 LLC data-side traffic이 관측됐다.

```text
cpu0->LLC LOAD_D       ACCESS:      23006
cpu0->LLC RFO_D        ACCESS:      10258
cpu0->LLC PREFETCH_D   ACCESS:        644
cpu0->LLC WRITE_D      ACCESS:      15160

cpu0->cpu0_L2C LOAD_D       ACCESS:          0
cpu0->cpu0_L2C RFO_D        ACCESS:          0
cpu0->cpu0_L2C PREFETCH_D   ACCESS:          0
cpu0->cpu0_L2C WRITE_D      ACCESS:          0
```

따라서 수정 후 `8i0d`의 data path는 다음처럼 동작한다고 볼 수 있다.

- L1D demand miss(`LOAD_D`, `RFO_D`)는 L2C lookup/fill 없이 LLC request queue로 내려간다.
- Data prefetch도 L2C를 채우지 않고 lower level로 내려간다.
- L1D/L2C writeback은 L2C에 fill되지 않고 LLC write queue로 내려간다.
- Bypassed demand/prefetch completion은 L2C MSHR로 drain한 뒤 upper level에 응답하고, bypassed writeback은 response를 요구하지 않는다.

추가로 `bravo.a_0000~0002` 세 trace를 짧은 설정으로 돌렸다.

```bash
./scripts/run.sh -C ChampSim_FDIP_debug -t \
  -T codex_debug_8i0d_bravo.txt \
  -L2C 0x40 -f 0x01 \
  -w 100000 -i 100000 -p 3 \
  -r codex_debug_8i0d_bravo
```

결과:

- 3개 trace 모두 정상 완료
- assert/abort/fail 로그 없음

### 현재 상태

수정과 빌드는 `ChampSim_FDIP_debug`에서만 수행했다. 원본 `ChampSim_FDIP`는 다른 실험 보호를 위해 아직 건드리지 않았다. debug 결과 기준으로는 `8i0d` abort의 직접 원인은 bypass writeback의 `response_requested` flag와 bypass completion drain 문제로 보는 것이 타당하다.

이 수정은 실험 종료 후 원본 `ChampSim_FDIP`에 반영할 후보로 남긴다.

---

## 2026-07-17 진행사항: long run의 `bad_alloc` 실패 분석

### 문제 상황

`260716_1733_w20_i300_latency_test`의 stage 1에서 7개 job이 실패했다. 실패 로그는 모두 `std::bad_alloc`으로 끝났다.

```text
terminate called after throwing an instance of 'std::bad_alloc'
  what():  std::bad_alloc
Failed trace: .../traces/gtrace_v2/yankee/yankee_0012.champsim.gz (exit 134)
```

실패는 모두 `fdip_0`에서 발생했고, trace는 `yankee_0006`, `yankee_0012`, `yankee_0027`, `yankee_0054`, `yankee_0057`처럼 큰 `yankee` trace에 몰려 있었다. 처음에는 `-p56` 병렬 실행으로 인한 시스템 메모리 부족 가능성을 의심했지만, debug copy에서 단일 실행으로도 재현됐다.

```bash
ChampSim_FDIP_debug/bin/champsim_l2cshared \
  --warmup-instructions 2000000 \
  --simulation-instructions 30000000 \
  --ftq_size 0 \
  traces/gtrace_v2/yankee/yankee_0012.champsim.gz
```

단일 실행에서도 약 10분대에 `bad_alloc`이 발생했고, 최대 RSS는 약 115 MB 수준이었다. 따라서 전체 시스템 메모리가 부족한 것이 아니라, 특정 코드 지점에서 비정상적으로 큰 allocation을 시도한 것으로 판단했다.

### 원인 분석

`gdb`로 `std::bad_alloc` throw 지점을 확인했다.

```text
#0  __cxa_throw
#1  std::__throw_bad_alloc()
#2  PageTableWalker::finish_packet(champsim::channel::response const&)
#3  PageTableWalker::operate()
#4  champsim::operable::operate_on(...)
#5  champsim::do_cycle(...)
```

문제 지점은 PTW의 `finish_packet()`이었다. 기존 코드는 lower level에서 page-walk response가 돌아오면 `MSHR` deque에서 같은 cache block address를 가진 entry를 `std::partition()`으로 앞쪽에 모은 뒤, `std::partition_copy()`로 `completed`와 `finished` deque에 복사하고 원본을 지웠다.

```cpp
auto last_finished = std::partition(std::begin(MSHR), std::end(MSHR), matches_addr);

std::for_each(std::begin(MSHR), last_finished, [is_last_step, finish_step, finish_last_step](auto& mshr_entry) {
  mshr_entry.data = is_last_step(mshr_entry) ? finish_last_step(mshr_entry) : finish_step(mshr_entry);
});

std::partition_copy(std::begin(MSHR), last_finished, std::back_inserter(completed), std::back_inserter(finished), is_last_step);
MSHR.erase(std::begin(MSHR), last_finished);
```

`mshr_type`에는 `instr_depend_on_me` vector가 포함된다. `yankee`처럼 ITLB/DTLB miss와 MSHR merge가 많이 생기는 trace에서는 이 dependency vector가 커질 수 있다. 이 상태에서 `std::partition()`/`std::partition_copy()`가 matching MSHR들을 재배열하거나 복사하면서 큰 추가 allocation을 요구했고, 그 과정에서 `bad_alloc`이 발생한 것으로 보인다.

### 수정 방향

동작 의미는 유지하되, matching MSHR entry를 복사하거나 전체 `MSHR` deque를 partition하지 않도록 수정했다. `MSHR`를 순회하면서 matching entry만 `completed` 또는 `finished`로 move한 뒤 즉시 erase한다.

```cpp
for (auto mshr_it = std::begin(MSHR); mshr_it != std::end(MSHR);) {
  if (!matches_addr(*mshr_it)) {
    ++mshr_it;
    continue;
  }

  mshr_it->data = is_last_step(*mshr_it) ? finish_last_step(*mshr_it) : finish_step(*mshr_it);
  if (is_last_step(*mshr_it)) {
    completed.emplace_back(std::move(*mshr_it));
  } else {
    finished.emplace_back(std::move(*mshr_it));
  }
  mshr_it = MSHR.erase(mshr_it);
}
```

이 수정의 의미는 다음과 같다.

- 기존과 동일하게 matching MSHR만 `completed` 또는 `finished`로 이동한다.
- 곧 지울 MSHR entry를 복사하지 않고 move한다.
- `std::partition()`으로 deque 내부 entry를 재배열하지 않는다.
- 큰 `instr_depend_on_me` vector를 가진 entry에서도 추가 allocation spike를 줄인다.

### 검증

수정과 빌드는 `ChampSim_FDIP_debug`에서만 수행했다. 원본 `ChampSim_FDIP`는 진행 중인 실험을 보호하기 위해 건드리지 않았다.

먼저 기존에 실패하던 `shared/ftq0/yankee_0012`를 같은 길이로 재실행했다.

```bash
ChampSim_FDIP_debug/bin/champsim_l2cshared \
  --warmup-instructions 2000000 \
  --simulation-instructions 30000000 \
  --ftq_size 0 \
  traces/gtrace_v2/yankee/yankee_0012.champsim.gz
```

결과:

- 정상 완료
- `Simulation complete CPU 0 instructions: 30000001`
- `cumulative IPC: 0.4793`
- elapsed time: `11:51`
- maximum RSS: 약 `115 MB`

추가로 같은 trace를 `8i0d` policy에서도 확인했다.

```bash
ChampSim_FDIP_debug/bin/champsim_l2c8i0d \
  --warmup-instructions 2000000 \
  --simulation-instructions 30000000 \
  --ftq_size 0 \
  traces/gtrace_v2/yankee/yankee_0012.champsim.gz
```

결과:

- 정상 완료
- `Simulation complete CPU 0 instructions: 30000001`
- `cumulative IPC: 0.4884`
- elapsed time: `11:37`
- maximum RSS: 약 `115 MB`

따라서 현재 확보한 수정 방안은 PTW `finish_packet()`의 MSHR 처리 방식을 copy/partition 기반에서 move/erase 기반으로 바꾸는 것이다. 이 수정은 simulator의 page-walk 의미를 바꾸기보다, 동일한 entry 이동을 더 메모리 안전하게 수행하는 변경으로 해석할 수 있다.

---

## 2026-07-20 진행사항: PTW `bad_alloc` fix 원본 반영

### 반영 내용

`ChampSim_FDIP_debug`에서 검증한 PTW 수정사항을 원본 `ChampSim_FDIP`에 반영했다. 변경 파일은 다음 하나뿐이다.

- `ChampSim_FDIP/src/ptw.cc`

수정 내용은 2026-07-17에 확인한 것과 동일하다. PTW `finish_packet()`에서 matching MSHR entry를 `std::partition()`과 `std::partition_copy()`로 재배열/복사하지 않고, `MSHR`를 순회하면서 matching entry만 `completed` 또는 `finished`로 `move`한 뒤 바로 erase한다.

### 반영 목적

- `yankee` long trace에서 발생하던 `std::bad_alloc`을 제거한다.
- PTW MSHR entry의 `instr_depend_on_me` vector가 커진 상황에서도 불필요한 copy/allocation spike를 피한다.
- page-walk의 기능적 의미는 유지하고, MSHR 이동 방식만 더 메모리 안전하게 바꾼다.

### 주의사항

원본 `ChampSim_FDIP`에는 코드만 반영했다. 진행 중인 실험을 보호하기 위해 원본 폴더에서는 빌드를 수행하지 않았다. 빌드와 실행 검증은 앞서 `ChampSim_FDIP_debug`에서 완료했다.
