# 2026-07-15 실험 노트: `l2c_test` 장기 실행 진행 기록

이 문서는 2026-07-15에 `260714_2030_w20_i300_l2c_partition` run(`trace_gtrace_l2c_test.txt`, 296 traces, L2C 5개 policy, `w=2,000,000`/`i=30,000,000`)을 진행하면서 확인한 상태, 판단, 코드 변경을 실시간으로 기록한다. Daily는 나중에 별도로 요약하고, 여기에는 진행 과정과 판단 근거를 자세히 남긴다.

## 배경: 어제(2026-07-14) 저녁 실험 설계

`docs/exp/2026_07_14_experiment.md`에서 정리한 `l2c_test` trace set(8개 trace group, 296 traces)을 대상으로, `0i8d`를 포함한 L2C 5개 policy 전체 x FTQ 전체 조합을 처음보다 긴 instruction 설정으로 돌리기로 했다.

**설정값 결정**: `w=2,000,000`(=`w20`x100000) / `i=30,000,000`(=`i300`x100000) — run id `260714_2030_w20_i300_l2c_partition`의 `w20_i300`이 이 축약 표기다. FTQ는 처음 "0, 8, 32, 64" 4개로 요청했으나 `run.sh`의 `-f` 비트마스크가 `0, 2, 4, 16, 32, 64`만 지원하고 `8`은 없어서(`8`은 `16`의 오기로 보임), 새 값을 추가하지 않고 **기존 6개 FTQ 전부**를 돌리는 것으로 정했다. L2C는 `-L2C 0x1f`(shared/0i8d/2i6d/4i4d/6i2d 전체).

**시간 추정**: 296 traces x 6 FTQ x 5 L2C = 8,880 jobs. 기준 처리량(`w=2,000,000`/`i=10,000,000`, `-p50`일 때 5.07초/job, `docs/exp/2026_07_14_experiment.md`에서 실측)에 instruction 배율(32M/12M ≈ 2.667)과 병렬도 보정을 곱해 총 소요 시간을 역산했다.

**병렬도와 단계 분할**: `-p58`로 정했다. 다만 8,880 jobs를 한 번에(`-f 0xff` 전부) 돌리면 하나의 명령으로 끝나지만, 사용자가 "58 workload를 계속 유지하고 싶다"는 이유로 여러 단계로 나눠 순차 실행하길 원했다. 처음엔 FTQ를 2개씩 3단계(`0,32` / `4,64` / `2,16`)로 나눴다가, 최종적으로 **3개씩 2단계**로 재조정했다:

- stage 1: `-f 0x15` = FTQ `0, 4, 32`
- stage 2: `-f 0x2a` = FTQ `2, 16, 64`

각 단계는 296 x 3 x 5 = 4,440 jobs, `-p58` 기준 약 14.4시간/단계, 2단계 합쳐 약 28.8시간(약 1.2일) 예상. 두 단계를 같은 `run_id`로 묶어 `stage1 && stage2` 형태로 하나의 `nohup bash -c '...'` 백그라운드 프로세스에 태웠다(같은 run id를 재사용해도 `raw`/`summary` 출력이 FTQ별로 나뉘고 로그가 append라 안전함을 확인 후 진행).

```bash
nohup bash -c '
./scripts/run.sh -t -T trace_gtrace_l2c_test.txt -L2C 0x1f -f 0x15 -w 2000000 -i 30000000 -p 58 -r 260714_2030_w20_i300_l2c_partition && \
./scripts/run.sh -t -T trace_gtrace_l2c_test.txt -L2C 0x1f -f 0x2a -w 2000000 -i 30000000 -p 58 -r 260714_2030_w20_i300_l2c_partition
' > /tmp/260714_2030_w20_i300_l2c_partition.log 2>&1 &
```

이 명령을 2026-07-14 20:40 KST경 실행하고 밤새 백그라운드로 돌렸다.

## 오늘 아침: 시작 시점 상태

2026-07-15 오전에 대화를 재개하면서 확인한 시작 상태:

- 백그라운드 프로세스(PID 4129894)가 여전히 살아 있었고, `ps`의 `etime`으로 경과 시간을 확인.
- `outputs/260714_2030_w20_i300_l2c_partition/raw/`에는 stage 1 대상인 `fdip_0`, `fdip_4`, `fdip_32` 디렉토리만 존재 — stage 2(`fdip_2`/`fdip_16`/`fdip_64`)는 아직 생성 전, 즉 stage 1이 진행 중인 상태에서 분석을 시작했다.
- 이 시점까지 `summary/`는 비어 있었다(전날 만든 `260713_2013_l2c_partition`의 summary와는 별개 run).

## 아침: stage 1 진행 상황 확인

여러 시점에 걸쳐 진행률을 확인했다. `ps`로 프로세스 경과 시간을 보고, `raw/fdip_<ftq>/` 아래 로그 중 완료 마커(`Simulation Complete`/`CPU 0 cumulative` 등)가 있는 파일 수를 세서 `완료 job / 전체 job`으로 진행률을 계산했다.

| 확인 시각 | 경과 | 완료 (stage1, 4,440 jobs 중) | 비고 |
|---|---:|---:|---|
| 11:19 AM | 14h39m | 4,194 (94.5%) | 실패 2건(yankee) 발견 |
| 11:28 AM | 14h48m | 4,237 | 실측 12.57초/job, ETA 약 12:11 PM |
| 11:45 AM | 15h04m | 4,301 | ETA 재확인, 약 12:11 PM |

실측 처리 속도(12.5~12.6초/job)는 사전 추정치(11.66초/job)에 거의 수렴했다.

## `fdip_0`/`fdip_4` 완료분만 먼저 summary 생성

`fdip_32`가 아직 도는 중이어서, 완료된 `fdip_0`(1,480개 시도, 2건 실패)/`fdip_4`(1,480개 전부 성공)만 대상으로 summary를 먼저 뽑았다.

```bash
./scripts/run.sh -r 260714_2030_w20_i300_l2c_partition -s 0xC0 -f 0x05 -L2C 0x1f
```

`-f 0x05` = FTQ 0/4, `-L2C 0x1f` = 5개 policy 전체, `-s 0xC0` = metrics.csv 재생성(`0x40`) + L2C delta grid/CSV 생성(`0x80`). 실패한 yankee 2개 trace는 로그가 비어서 `metrics.csv`에서 자동으로 빠졌고, 다른 행은 전부 `ok` 상태였다.

## `0i8d`에서 L2I MPKI가 0으로 나오는지 확인

`0i8d` 정책은 L2C에 instruction way를 0개 주는 정책이라, `l2i_mpki`가 정확히 0이 나와야 정상이다(측정 실패가 아니라 애초에 L2C를 거치지 않는 구조). `l2c_raw_values.csv`를 HTML 표로 만들어 직접 확인했다.

확인 결과: **80행(8 trace group x 2 FTQ x 5 policy 중 `0i8d` 16행) 전부에서 `l2i_mpki == 0.00`**이었고, 교차 검증으로 `l2c_mpki`(=L2I+L2D)가 `0i8d` 행마다 `l2d_mpki`와 정확히 같다는 것도 확인했다(L2I가 0이니 당연히 성립해야 하는 항등식).

## `0i8d`의 L2I MPKI delta를 0으로 고정

`delta_grid.py`는 원래 모든 지표에 대해 `delta = policy - shared`(또는 `%` 변화)를 그대로 계산했다. 그런데 `0i8d`의 `l2i_mpki`는 shared 대비 "L2C가 instruction을 더 잘 캐싱해서" 줄어든 게 아니라 "애초에 L2C를 거치지 않아서" 0이 된 것이므로, 이 delta를 그대로 쓰면 (예: `-8.82`처럼) 실제로는 없는 "L2I 캐싱 개선"으로 오독될 수 있다.

두 가지 대안을 검토했다:

- **N/A로 표시하고 그래프/표에서 제외**: 가장 정확하지만, 그래프에서 그 칸만 비어서 레이아웃이 깨질 수 있음.
- **delta를 0으로 고정**: "shared와 차이 없음"이라는 것도 완전히 정확한 표현은 아니지만, 레이아웃을 해치지 않고 "이 지표는 이 정책에서 의미가 없다"는 뉘앙스를 전달할 수 있음.

레이아웃을 우선해 **0 고정** 방식으로 결정했다. `build_deltas()`에 `key == "l2i_mpki" and policy == "0i8d"`인 경우 `d = 0.0`으로 강제하는 분기를 추가했다(`parser/l2c/delta_grid.py`). `l2c_delta_raw.csv`/`l2c_delta_pct.csv` 둘 다 이 분기를 공유하므로 두 CSV 모두, 그리고 grid/overlay 그래프에도 일괄 반영된다. 재생성해서 `d_l2i_mpki` 컬럼이 `0i8d` 행마다 정확히 `0.0`인 것을 확인했다.

## stage 1 → stage 2 체이닝이 끊긴 것을 발견

`ps`로 진행 상황을 다시 확인하던 중 원래 백그라운드 프로세스(PID 4129894)가 더 이상 보이지 않는데도 `raw/fdip_2`, `fdip_16`, `fdip_64` 디렉토리가 전혀 생기지 않은 것을 발견했다.

원인: `run.sh`는 trace가 하나라도 실패하면 `exit "${trace_status}"`로 non-zero 종료 코드를 반환한다(`scripts/run.sh:701-704`). stage 1에 실패 2건(`yankee_0012`, `yankee_0054`)이 있었기 때문에, `stage1 && stage2`로 체이닝한 명령이 stage 1의 실패 exit code 때문에 stage 2를 아예 실행하지 않고 끝나버렸다.

## 실패 원인 조사 및 재시도

실패한 두 trace의 정확한 FTQ/policy 조합을 알아내기 위해, 로그 인터리빙(병렬 58개 worker가 동시에 stdout을 씀) 때문에 `run.log`의 앞뒤 문맥만으로는 신뢰할 수 없어서, 대신 `raw/fdip_0/<policy>/.../yankee_00{12,54}...log` 파일들을 정책별로 전부 뒤져서 크기/완료 마커를 확인했다. **`ftq0` x `4i4d` 조합에서만 두 파일이 223바이트짜리 비정상 로그였고, 나머지 4개 policy(shared/0i8d/2i6d/6i2d)에서는 정상 완료**되어 있었다. 로그 내용은:

```
terminate called after throwing an instance of 'std::bad_alloc'
  what():  std::bad_alloc
```

처음에는 `-p58`의 동시 메모리 부하 때문인 transient 오류로 보고, 그 두 trace만 담은 `traces/trace_gtrace_l2c_test_err.txt`를 만들어 `-f 0x01 -L2C 0x08`(ftq0, 4i4d만)로 단독 재시도했다:

```bash
./scripts/run.sh -t -T trace_gtrace_l2c_test_err.txt -L2C 0x08 -f 0x01 -w 2000000 -i 30000000 -p 58 -r 260714_2030_w20_i300_l2c_partition
```

**동시 job이 2개뿐인데도 동일하게 `std::bad_alloc`으로 재현됐다.** 이 시점의 `free -h`는 `available 232Gi`로 메모리 여유가 충분했으므로, 시스템 메모리 부족이 아니라 **`yankee_0012`/`yankee_0054` + `4i4d`/`ftq0` 조합에서만 나오는 결정론적 문제**로 결론 내렸다. 재시도로는 해결되지 않아 이 2개는 결측으로 남기기로 하고, stage 2를 수동으로 시작했다.

```bash
nohup ./scripts/run.sh -t -T trace_gtrace_l2c_test.txt -L2C 0x1f -f 0x2a -w 2000000 -i 30000000 -p 58 -r 260714_2030_w20_i300_l2c_partition > /tmp/260714_2030_w20_i300_l2c_partition_stage2.log 2>&1 &
```

### `ChampSim_FDIP_debug`에서 `std::bad_alloc` 원인 재현 및 수정 검증

원본 `ChampSim_FDIP`는 장기 실험이 계속 읽고 있으므로 절대 수정/빌드하지 않고, 폴더를 복사해 `ChampSim_FDIP_debug`를 만들었다. `absolute.options`가 처음에는 원본 `ChampSim_FDIP/inc`를 가리키고 있어서 debug 폴더의 `inc`/`vcpkg_installed`를 보도록 수정한 뒤 debug copy만 빌드했다. root `.gitignore`에는 `ChampSim_FDIP_debug/`를 추가했다.

처음에는 `CACHE::mshr_type::merge()`의 `std::set_union` 입력 정렬 전제가 깨지면서 dependency vector가 커지는 문제를 의심했다. debug copy에서 MSHR merge size marker를 넣고, merge를 `append -> sort -> unique` 방식으로 바꿔 실험했다. 하지만 `bad_alloc` 로그에는 marker가 찍히지 않았고, gdb backtrace를 확인한 결과 실제 throw 지점은 cache가 아니라 `PageTableWalker::finish_packet()`이었다.

```text
#7  PageTableWalker::finish_packet(champsim::channel::response const&)
#8  PageTableWalker::operate()
#9  champsim::operable::operate_on(...)
```

PTW 코드를 확인해 보니 `MSHR_SIZE` 필드는 있지만, upper-level translation request를 받을 때 active PTW MSHR 수를 검사하지 않고 `next_steps`를 계속 추가하고 있었다. 특정 trace/policy에서 translation pressure가 커지면 PTW MSHR이 무한히 누적되고, `finish_packet()`에서 같은 PTE block에 매칭되는 MSHR들을 `completed`/`finished`로 복사하는 과정에서 `std::bad_alloc`이 발생할 수 있다.

debug copy에만 다음 수정을 적용했다.

- `PageTableWalker::operate()`에서 `MSHR + finished + completed + next_steps >= MSHR_SIZE`이면 새 upper RQ를 받지 않고 stall.
- `PageTableWalker::finish_packet()`에 비정상적으로 큰 matching MSHR 수를 stderr로 찍는 debug marker 추가.
- `CACHE::mshr_type::merge()`와 `channel` collision merge에서 dependency vector 병합을 `append -> sort -> unique`로 변경해 정렬 전제 의존을 제거.

검증은 실패가 재현되던 두 trace만 대상으로 했다.

```bash
./scripts/run.sh -C ChampSim_FDIP_debug -t \
  -T trace_gtrace_l2c_test_err.txt \
  -L2C 0x08 -f 0x01 \
  -w 2000000 -i 10000000 -p 2 \
  -r codex_debug_ptw_fix_yankee_4i4d_i100
```

`i=10M`에서 이전에는 `yankee_0054`가 `std::bad_alloc`으로 실패했지만, 수정 후에는 `yankee_0012`와 `yankee_0054` 모두 정상 완료했다.

```text
yankee_0012: Simulation complete ... IPC 0.4105
yankee_0054: Simulation complete ... IPC 0.3915
```

원래 실패 조건에 가까운 `i=30M`도 같은 debug copy에서 확인했다.

```bash
./scripts/run.sh -C ChampSim_FDIP_debug -t \
  -T trace_gtrace_l2c_test_err.txt \
  -L2C 0x08 -f 0x01 \
  -w 2000000 -i 30000000 -p 2 \
  -r codex_debug_ptw_fix_yankee_4i4d_i300
```

결과는 두 trace 모두 정상 완료:

```text
yankee_0012: Simulation complete CPU 0 instructions: 30000001 cycles: 67704998 cumulative IPC: 0.4431
yankee_0054: Simulation complete CPU 0 instructions: 30000000 cycles: 78102345 cumulative IPC: 0.3841
```

### 문제 코드 출처 판단

PTW의 `MSHR_SIZE` 필드는 있지만 upper-level RQ를 받을 때 capacity check를 하지 않는 구조는 `ChampSim` 원본 계열에도 이미 있었다. `ChampSim/src/ptw.cc`와 `ChampSim_FDIP_ideal/src/ptw.cc`를 비교하면 FDIP 쪽 PTW 변경은 `ooo_model_instr* instr`를 PTW MSHR과 translation request에 전달하는 정도이고, PTW MSHR capacity 동작 자체는 동일하다.

따라서 이 문제를 "FDIP 구현이 새로 만든 버그"라고 보기는 어렵다. 더 정확한 판단은 다음과 같다.

- **기저 문제**: 원래 ChampSim PTW 코드에 upper RQ 수락 시 MSHR capacity gate가 없어서, 특정 조건에서 PTW MSHR이 무제한으로 커질 수 있다.
- **FDIP 관련 변경**: `instr` 포인터 전달, instruction-origin metadata 전파 등은 디버깅/통계 경로를 확장했지만, 이번 `bad_alloc`의 직접 throw 지점은 아니다.
- **L2C partition 관련 변경**: `4i4d`가 직접 `bad_alloc`을 던진 것은 아니지만, yankee trace에서 translation/cache pressure를 특정 방향으로 만들어 PTW backlog 문제를 드러낸 trigger 역할을 했다.
- **현재 수정 위치**: fix는 `ChampSim_FDIP_debug`에서 검증한 뒤 원본 `ChampSim_FDIP` 코드에도 반영했다. 단, 장기 실험 보호를 위해 아직 원본 폴더에서 빌드는 하지 않았다.

### PTW MSHR 제한 방식과 성능 영향 판단

이번 debug fix의 핵심 방향은 PTW가 감당할 수 있는 translation request만 받아서 backpressure를 거는 것이다. 기존 코드에는 `PTW.mshr_size = 5`가 있지만, upper-level RQ에서 새 translation request를 받을 때 이 한계를 검사하지 않아 특정 조건에서 PTW MSHR이 무제한으로 커질 수 있었다.

PTW 내부 상태를 나누면 다음과 같다.

- `MSHR`: lower cache/DRAM 응답을 기다리는 page-table walk entry.
- `finished`: 한 단계 page-table access 응답은 왔고, 다음 level walk로 진행해야 하는 entry.
- `completed`: page translation은 끝났고, 위쪽 CPU/cache에 응답을 돌려줘야 하는 entry.
- `next_steps`: 현재 cycle에서 새로 생성되어 곧 `MSHR`에 들어갈 entry.

따라서 capacity check에는 두 가지 선택지가 있다.

1. **느슨한 제한**: `MSHR + next_steps`만 센다.
   - 장점: 원래 ChampSim 동작과 더 비슷하게 유지될 가능성이 크다.
   - 단점: `finished`/`completed`가 많이 쌓이는 상황에서는 PTW 내부에 이미 처리 대기 중인 entry가 많은데도 새 request를 계속 받을 수 있다. `bad_alloc`을 완전히 막는 데 덜 보수적일 수 있다.

2. **보수적 제한**: `MSHR + finished + completed + next_steps`를 모두 센다.
   - 장점: PTW 내부에 남아 있는 모든 active entry를 자원 점유로 보고 제한하므로, unbounded growth를 더 확실하게 막는다.
   - 단점: `finished`/`completed`까지 자원 점유로 보기 때문에 PTW가 더 일찍 stall될 수 있고, 일부 workload에서 IPC가 낮아질 수 있다.

현재 `ChampSim_FDIP_debug`에서 검증하고 `ChampSim_FDIP`에 반영한 코드는 두 번째 방식, 즉 보수적 제한을 사용한다. 성능에는 영향이 있을 수 있지만, 이는 새롭게 성능을 깎는 임의 제한이라기보다 원래 config에 존재하던 finite PTW resource를 실제로 반영하는 쪽에 가깝다. 만약 "원래 ChampSim 결과와 최대한 동일한 수치"가 더 중요하다면, `MSHR + next_steps`만 제한하는 느슨한 방식과 현재 보수적 방식을 나란히 비교해야 한다.

### `std::bad_alloc` 재조사: 동시성 완전 배제, 원인 후보 좁히기

앞서 `-p58`에서 이 두 trace만 골라 재시도했을 때도 실패했지만, 동시 job이 58개 → 2개로 줄었을 뿐 여전히 병렬이었다. **완전히 순차(`-p 1`)로 다시 재현을 시도**했다.

```bash
./scripts/run.sh -t -T trace_gtrace_l2c_test_err.txt -L2C 0x08 -f 0x01 -w 2000000 -i 30000000 -p 1 -r 260714_2030_w20_i300_l2c_partition
```

**`-p 1`에서도 둘 다 동일하게 `std::bad_alloc`으로 실패했다.** 이걸로 동시성/메모리 경합 가능성은 완전히 배제된다. trace 파일 크기도 확인했는데 `yankee_0012`(2.4GB)/`yankee_0054`(2.6GB) 둘 다 다른 yankee trace(2.3~2.9GB)와 같은 범위라 "trace가 유난히 커서"도 아니다.

다음으로 "instruction 수를 늘린 게 원인 아닐까"라는 가설이 나와서, `outputs/` 아래 모든 run을 뒤져 **yankee가 L2C partition 코드(0i8d/2i6d/4i4d/6i2d)를 언제부터 탔는지** 확인했다:

| Run | yankee 로그 | 비고 |
|---|---:|---|
| `260707_2245_w500_i2000` | 415 | partition 기능(07-13) 이전, flat 구조 — 사실상 shared만 |
| `260708_0856_w20_i100` | 415 | 위와 동일 |
| `260713_1300_w1_i5_frontend_stall_test` | 415 | 위와 동일 |
| `260713_2013_w20_i100_l2c_partition` | 0 | l2c_test 첫 버전엔 yankee가 아예 없었음(07-14에 추가) |
| `260714_2030_w20_i300_l2c_partition` (현재) | 1,245 | **yankee가 partition 코드를 타는 첫 실행** |

즉 **yankee가 `4i4d` 등 실제 partition 코드를 거친 건 이번이 처음**이라, "짧게는 잘 됐는데 길게 돌리니 터졌다"고 단정할 수 있는 이전 비교 데이터가 없다. instruction 수 증가와 "yankee+4i4d 최초 실행"이라는 두 변수가 얽혀 있어서, 다음 단계로 같은 두 trace를 **짧은 설정(`w=2M/i=10M`, 07-13 기준)으로 4i4d에 돌려서 성공하는지**를 확인해 두 가설을 분리하기로 했다(아직 실행 전 — stage 2 완료를 우선하기로 함).

## `0i8d`의 `l2i_mpki` delta 수정을 stage 1 3개 FTQ 전체로 검증

`fdip_0`/`fdip_4`만으로 검증했던 것을, stage 1이 완료된 뒤 `fdip_32`까지 포함해 다시 생성했다.

```bash
./scripts/run.sh -r 260714_2030_w20_i300_l2c_partition -s 0xC0 -f 0x15 -L2C 0x1f
```

`l2c_delta_raw.csv`에서 `d_l2i_mpki` 컬럼이 `0i8d` 행 24개(8 trace group x 3 FTQ) 전부 정확히 `0.0`인 것을 확인했다. `metrics.csv`에는 실패한 두 trace(`yankee_0012`/`0054`, ftq0/4i4d)가 `status=failed`로 행 자체는 남지만, `delta_grid.py`의 `load_metrics()`가 `status == "ok"`인 행만 평균에 넣으므로 delta 계산에는 영향이 없다는 것도 확인했다.

## 현재 상태 (13:44 PM 기준)

- **stage 1** (FTQ 0/4/32): 완료. 4,438/4,440 성공, 2건 결측(`yankee_0012`, `yankee_0054`, ftq0/4i4d, `std::bad_alloc`, `-p58`/`-p1` 양쪽에서 재현). summary(metrics.csv + delta grid/CSV) 재생성 및 검증 완료.
- **stage 2** (FTQ 2/16/64): 진행 중 (PID 271647, 시작 후 약 36분 경과). `fdip_2`가 153/1,480 진행, `fdip_16`/`fdip_64`는 아직 시작 전(policy 순서상 `fdip_2`의 5개 policy를 먼저 순회).
- `delta_grid.py`는 `0i8d`의 `l2i_mpki` delta를 0으로 고정하도록 수정 완료, stage 1 전체(FTQ 0/4/32) 기준으로 검증됨.

## 남겨둔 조사 과제

- PTW MSHR capacity fix는 원본 `ChampSim_FDIP` 코드에 반영했지만 아직 빌드하지 않았다. 장기 실험 종료 후 빌드하고 재검증해야 한다.
- root summary는 현재 실패 2건을 결측으로 처리하고 있으므로, fix 반영 후 해당 두 trace만 재실행해 `260714_2030_w20_i300_l2c_partition`의 결측을 메울 수 있다.

---

## 2026-07-16: stage 1/2 완료 및 실패 3건 처리

### stage 1/2 실제 소요 시간

raw 로그 파일의 mtime을 기준으로 각 stage의 실제 시작/종료 시각을 역산했다(재실행으로 덮어써진 파일은 제외하고 계산).

| Stage | 시작 | 종료 | 소요 시간 |
|---|---|---|---:|
| stage 1 (FTQ 0/4/32) | 2026-07-14 20:48 | 2026-07-15 12:07 | 약 15.3시간 |
| stage 2 (FTQ 2/16/64) | 2026-07-15 13:16 | 2026-07-16 04:41 | 약 15.4시간 |

두 stage 사이에 약 1.1시간의 공백이 있다. stage 1에 실패 2건이 있어서 `stage1 && stage2`로 체이닝한 명령의 exit code가 non-zero가 되었고, 그 결과 stage 2가 자동으로 이어지지 않고 끝나버렸다(앞서 "stage 1 → stage 2 체이닝이 끊긴 것을 발견" 절 참고). 이 공백은 그 문제를 뒤늦게 발견해서 수동으로 stage 2를 재시작하기까지 걸린 시간이다.

사전 추정치(단계당 약 14.4시간, `-p58` 기준)보다 실제로는 조금 더 걸렸지만 거의 근접했다.

stage 2가 끝난 시점(2026-07-16 04:41 이후) 기준 전체 결과는 8,877/8,880 성공(99.97%)이었고, 실패 3건은 전부 `std::bad_alloc`이었다:

- `yankee_0012`, `yankee_0054` — `ftq0/4i4d` (stage 1에서부터 있던 기존 실패)
- `sierra.a.4_0014` — `ftq2/2i6d` (stage 2에서 새로 발견된 같은 종류의 실패)

### 실패 3건을 `f6602de` 고정 커밋으로 재실행

원본 `ChampSim_FDIP`는 이미 `f6602de`(PTW MSHR pressure 수정) 이후로 커밋이 더 쌓여 있었다(`c19adac` "Model L2C lookup latency by partition" 등). 이번 실패 재현에는 그 이후 커밋을 섞지 않고 **`f6602de` 딱 그 지점만** 반영하고 싶어서, 별도 격리된 빌드 환경을 만들었다.

`cp -r`로 통째로 복사하는 대신 `git worktree`를 사용했다: `ChampSim_FDIP`가 슈퍼프로젝트의 서브모듈이라 `.git`이 `.git/modules/ChampSim_FDIP`를 가리키는 포인터 파일이고, `core.worktree`도 원본 경로를 가리키고 있어서 단순 폴더 복사 후 그 안에서 `git checkout`을 하면 원본 체크아웃 상태에 영향을 줄 위험이 있었기 때문이다. `git worktree add`는 별도 HEAD/인덱스를 가진 새 워킹트리를 안전하게 만들어준다.

```bash
git -C ChampSim_FDIP worktree add ../ChampSim_FDIP_f6602de f6602de0225dac669a712813b6b3a0798576433f
```

`vcpkg_installed`(빌드 의존성, git에는 안 잡히는 디렉터리)는 원본에서 그대로 복사해 왔고, `vcpkg` 툴 디렉터리(350M)는 Makefile에서 참조하지 않는 것을 확인해 복사하지 않았다. `absolute.options`는 `config.sh`가 자기 위치 기준으로 절대경로를 다시 생성해 주므로 별도 수정이 필요 없었다. `ChampSim_FDIP_f6602de/`는 root `.gitignore`에 추가했다.

```bash
./scripts/run.sh -C ChampSim_FDIP_f6602de -b -L2C 0x18
```

(`-b`는 mask와 무관하게 항상 7개 policy 바이너리를 전부 만든다.)

실패한 3개를 두 그룹(같은 ftq/policy끼리)으로 나눠 같은 run id(`260714_2030_w20_i300_l2c_partition`)에 재실행해서 기존 실패 로그를 덮어쓰게 했다. 사용자가 동시에 돌리자고 해서 두 그룹을 병렬 백그라운드로 실행했다.

```bash
# yankee_0012/0054, ftq0/4i4d, -p2
./scripts/run.sh -C ChampSim_FDIP_f6602de -t -T trace_gtrace_l2c_test_err_yankee.txt \
  -L2C 0x10 -f 0x01 -w 2000000 -i 30000000 -p 2 -r 260714_2030_w20_i300_l2c_partition

# sierra.a.4_0014, ftq2/2i6d, -p1
./scripts/run.sh -C ChampSim_FDIP_f6602de -t -T trace_gtrace_l2c_test_err_sierra.txt \
  -L2C 0x08 -f 0x02 -w 2000000 -i 30000000 -p 1 -r 260714_2030_w20_i300_l2c_partition
```

**3개 전부 정상 완료됐다** (`yankee_0012` 14,379B, `yankee_0054` 14,377B, `sierra.a.4_0014` 14,388B, 전부 완료 마커 확인). `f6602de`가 실제로 `std::bad_alloc`을 해결한다는 것이 재확인됐고, `260714_2030_w20_i300_l2c_partition`는 이제 **8,880/8,880 (100%)** 완료 상태다.

원본 `ChampSim_FDIP`는 이번에도 전혀 건드리지 않았다(빌드/체크아웃 전부 `ChampSim_FDIP_f6602de` 워크트리 안에서만 진행).
