# 2026-07-21 Verification: ChampSim_Split Shared 동작 검증

이 문서는 `ChampSim_Split`의 `shared` mode가 원본 `ChampSim`과 동일하게 동작하는지 검증하기 위한 절차와 결과를 기록한다.

## 검증 목적

`ChampSim_Split`는 원본 `ChampSim`을 fork해서 L2 cache split 기능을 추가한 코드다. split 기능의 목적은 config 단계에서 `L2I`와 `L2D`를 별도 cache object로 만들 수 있게 하는 것이다.

하지만 `shared` mode에서는 split 기능이 꺼져야 한다. 즉 hierarchy가 원래 ChampSim과 동일하게 유지되어야 한다.

| Build | Expected hierarchy |
|---|---|
| `ChampSim` | `L1I/L1D -> L2C -> LLC` |
| `ChampSim_Split shared` | `L1I/L1D -> L2C -> LLC` |
| `ChampSim_Split split` | `L1I -> L2I -> LLC`, `L1D -> L2D -> LLC` 또는 한쪽 bypass |

따라서 `ChampSim_Split shared`와 원본 `ChampSim`이 같은 config, 같은 trace, 같은 instruction count로 실행되면 결과가 같아야 한다. 만약 shared 결과가 다르면 split 기능이 꺼져 있는 상태에서도 원래 ChampSim 동작을 바꾼 것이므로, split 구현의 baseline으로 사용할 수 없다.

## 기준 결과

비교 기준은 이미 실행된 `ChampSim_Split` shared 결과다.

```bash
./scripts/run.sh \
  -C ChampSim_Split \
  -t \
  -T l2c_test_g2.txt \
  -L2C 0x7b \
  -f 0x01 \
  -w 1000000 \
  -i 10000000 \
  -p 58 \
  -r 260721_2005_w10_i100_champ_split_2g
```

이 실행에서 비교 대상으로 사용하는 결과는 shared policy뿐이다.

```text
outputs/260721_2005_w10_i100_champ_split_2g/summary/fdip_0/shared/metrics.csv
```

현재 repository의 trace list 이름은 `trace_gtrace_l2c_test_g2.txt`이므로, 원본 `run.log`의 `l2c_test_g2.txt` 대신 이 파일명을 사용한다.

## ChampSim 비교 실행 계획

원본 `ChampSim`은 FDIP/FTQ 기능이 없지만, root `scripts/run.sh`는 공통 실행 경로에서 `--ftq_size`를 넘긴다. 따라서 `ChampSim`에는 `--ftq_size` 옵션을 받되 무시하는 compatibility 변경만 추가했다. 이 변경은 시뮬레이션 동작에는 영향을 주지 않는다.

빌드와 실행은 같은 run id에 기록한다.

```bash
./scripts/run.sh \
  -C ChampSim \
  -b \
  -r 260721_2130_w10_i100_champ_hard_config_2g
```

```bash
./scripts/run.sh \
  -C ChampSim \
  -t \
  -T trace_gtrace_l2c_test_g2.txt \
  -L2C 0x1 \
  -f 0x01 \
  -w 1000000 \
  -i 10000000 \
  -p 2 \
  -r 260721_2130_w10_i100_champ_hard_config_2g
```

`-L2C 0x1`은 shared binary만 실행하기 위한 선택이다. 원본 `ChampSim`은 split 기능을 구현하지 않으므로, shared 결과만 비교하면 된다.

## Summary 생성 계획

실행이 끝나면 같은 run id에서 metrics를 생성한다.

```bash
./scripts/run.sh \
  -C ChampSim \
  -s 0x41 \
  -T trace_gtrace_l2c_test_g2.txt \
  -L2C 0x1 \
  -f 0x01 \
  -r 260721_2130_w10_i100_champ_hard_config_2g
```

생성될 비교 대상은 다음 파일이다.

```text
outputs/verify/260721_2130_w10_i100_champ_hard_config_2g/summary/fdip_0/shared/metrics.csv
```

## 비교 기준

trace별로 다음 항목을 비교한다.

- `status`, `reason`
- `ipc`, `instructions`, `cycles`
- `l1i_mpki`, `l1d_mpki`, `l2c_mpki`, `llc_mpki`
- 주요 access/miss counter (`l1i/l1d/l2c/llc load/rfo`)

기대 결과는 모든 trace에서 차이가 0이거나, floating-point 출력/파싱 과정의 매우 작은 오차만 존재하는 것이다.

## 진행 상태

- `260721_2130_w10_i100_champ_hard_config_2g` run id로 `ChampSim` 빌드를 완료했다.
- 같은 run id로 `trace_gtrace_l2c_test_g2.txt`, `-L2C 0x1`, `-f 0x01`, `w=1000000`, `i=10000000`, `-p 2` 실행을 시작했다.
- 실행은 22개 trace 모두 완료되었고, summary 생성 결과도 22개 모두 `ok`였다.

## 비교 결과

현재 비교는 exact match가 아니다. 다만 원인은 `ChampSim_Split shared`의 shared 경로 자체라기보다, 두 실행의 config가 서로 다르게 잡힌 점이다.

| 항목 | `ChampSim_Split shared` 기준 | `ChampSim` 비교 실행 |
|---|---|---|
| config signature | `bimodal-basic_btb-no-next_line-ip_stride-l2cshared-no-lru-1core` | `bimodal-basic_btb-no-no-no-l2cshared-no-lru-1core` |
| L1I prefetcher | `no` | `no` |
| L1D prefetcher | `next_line` | `no` |
| L2C prefetcher | `ip_stride` | `no` |
| trace rows | 22 | 22 |
| status | 22 ok | 22 ok |

즉, 비교 대상은 trace와 instruction count는 맞지만 L1D/L2C prefetcher가 다르다. 이 상태에서는 IPC, L1D MPKI, L2C MPKI, LLC MPKI가 달라지는 것이 정상이다.

대표 차이는 다음과 같다.

| trace | metric | `ChampSim_Split shared` | `ChampSim` | delta |
|---|---:|---:|---:|---:|
| `delta_0000` | IPC | 0.5030 | 0.4429 | -0.0601 |
| `delta_0000` | L1D MPKI | 53.4258 | 58.7854 | +5.3596 |
| `delta_0000` | L2C MPKI | 16.8453 | 20.8977 | +4.0524 |
| `delta_0001` | IPC | 0.6195 | 0.3740 | -0.2455 |
| `delta_0001` | L1D MPKI | 30.6533 | 54.3118 | +23.6585 |
| `delta_0002` | IPC | 0.6315 | 0.3696 | -0.2619 |
| `delta_0002` | LLC MPKI | 4.8563 | 19.1060 | +14.2497 |
| `sierra.a.6_0000` | IPC | 0.4999 | 0.4999 | 거의 동일 |
| `sierra.a.6_0000` | L2C MPKI | 32.5959 | 28.5232 | -4.0727 |

정량 비교 결과:

- 공통 trace row: 22개
- 누락 row: 0개
- numeric diff가 발생한 column: 26개
- 가장 큰 cycle 차이: `delta_0002`, +11,217,410 cycles
- 모든 trace에서 L1D/L2C/LLC 관련 counter 차이가 발생했다.

### 결론

이번 비교 실행은 `ChampSim_Split shared`와 원본 `ChampSim`의 동일성 검증으로는 부적합하다. 이유는 shared/split 구현 차이가 아니라, 기준 binary의 prefetcher 구성이 다르기 때문이다.

정확한 검증을 위해서는 다음 둘 중 하나로 다시 비교해야 한다.

1. `ChampSim`도 `ChampSim_Split shared`와 동일하게 L1D=`next_line`, L2C=`ip_stride`로 빌드해서 비교한다.
2. `ChampSim_Split shared`도 원본 `ChampSim`과 동일하게 L1D=`no`, L2C=`no`로 빌드해서 비교한다.

baseline 보존 관점에서는 1번이 더 적절하다. 현재 `260721_2005_w10_i100_champ_split_2g` 결과를 기준으로 검증하려면, 원본 `ChampSim`의 config를 기준 결과와 같은 prefetcher 구성으로 맞춘 뒤 재실행해야 한다.

---

## 재검증: prefetcher config 정합 후 비교

위 비교에서 config mismatch가 확인되었으므로, 원본 `ChampSim`의 config를 `ChampSim_Split shared` 기준과 동일하게 맞춘 뒤 다시 비교했다.

수정한 원본 `ChampSim` config:

| 항목 | 값 |
|---|---|
| L1I prefetcher | `no` |
| L1D prefetcher | `next_line` |
| L2C prefetcher | `ip_stride` |
| LLC prefetcher | `no` |

재검증 실행의 config signature는 기준 `ChampSim_Split shared`와 동일하다.

```text
bimodal-basic_btb-no-next_line-ip_stride-l2cshared-no-lru-1core
```

재검증 run id:

```text
260722_1228_w10_i100_champ_hard_config_matched_prefetch_2g
```

실행 명령:

```bash
./scripts/run.sh \
  -C ChampSim \
  -b \
  -r 260722_1228_w10_i100_champ_hard_config_matched_prefetch_2g
```

```bash
./scripts/run.sh \
  -C ChampSim \
  -t \
  -T trace_gtrace_l2c_test_g2.txt \
  -L2C 0x1 \
  -f 0x01 \
  -w 1000000 \
  -i 10000000 \
  -p 4 \
  -r 260722_1228_w10_i100_champ_hard_config_matched_prefetch_2g
```

summary 생성:

```bash
./scripts/run.sh \
  -C ChampSim \
  -s 0x41 \
  -T trace_gtrace_l2c_test_g2.txt \
  -L2C 0x1 \
  -f 0x01 \
  -r 260722_1228_w10_i100_champ_hard_config_matched_prefetch_2g
```

비교 대상:

| 구분 | metrics |
|---|---|
| `ChampSim_Split shared` 기준 | `outputs/260721_2005_w10_i100_champ_split_2g/summary/fdip_0/shared/metrics.csv` |
| 원본 `ChampSim` 재검증 | `outputs/verify/260722_1228_w10_i100_champ_hard_config_matched_prefetch_2g/summary/fdip_0/shared/metrics.csv` |

비교 결과:

| 항목 | 결과 |
|---|---:|
| 공통 trace row | 22 |
| 기준에만 있는 row | 0 |
| 재검증 결과에만 있는 row | 0 |
| 문자열 column 차이 | 0 |
| numeric column 차이 | 0 |

### 최종 결론

`ChampSim_Split shared`는 원본 `ChampSim`과 같은 config, 같은 trace, 같은 instruction count로 실행했을 때 `metrics.csv` 기준으로 완전히 동일한 결과를 낸다.

따라서 `shared` mode는 split 기능이 꺼진 baseline으로 사용할 수 있다. 이후 `0i8d`, `1i7d`, `2i6d`, `4i4d`, `6i2d`, `8i0d` 결과에서 관찰되는 차이는 shared baseline의 오염이 아니라 L2I/L2D split 정책 자체의 영향으로 해석할 수 있다.

---

## 추가 검증: `ChampSim_split_L2` 2:6 강제 설정 비교

`ChampSim_split_L2`는 `_L2C`와 달리 하나의 `L2C` 안에서 way를 나누는 방식이 아니라, `L2IC`와 `L2DC`를 별도 cache object로 분리하는 방식이다. 그래도 config를 `_L2C`의 `2i6d`와 최대한 같은 의미로 맞췄을 때 결과가 동일한지 확인했다.

`ChampSim_split_L2`에 적용한 config 의미:

| 항목 | 설정 |
|---|---|
| L1I path | `L1I -> L2IC -> LLC` |
| L1D path | `L1D -> L2DC -> LLC` |
| L2IC | `sets=1024`, `ways=2`, `prefetcher=ip_stride` |
| L2DC | `sets=1024`, `ways=6`, `prefetcher=ip_stride` |
| L1D prefetcher | `next_line` |

실행 중 확인된 추가 수정:

- `run.sh`는 모든 ChampSim 계열에 `--ftq_size`를 넘긴다.
- `ChampSim_split_L2`는 FDIP가 없으므로 처음에는 `--ftq_size 0`의 `0`을 trace 이름으로 해석해 모든 trace가 exit 105로 실패했다.
- 원본 `ChampSim`과 동일하게 `--ftq_size`를 받되 무시하는 compatibility option을 `src/main.cc`에 추가했다.
- pull 이후 `.csconfig`/`absolute.options`에 남아 있던 이전 절대경로를 현재 workspace 경로로 정리한 뒤 빌드했다.

실행 명령:

```bash
./scripts/run.sh \
  -C ChampSim_split_L2 \
  -b \
  -r 260722_1228_w10_i100_champ_hard_config_matched_prefetch_2g
```

```bash
./scripts/run.sh \
  -C ChampSim_split_L2 \
  -t \
  -T trace_gtrace_l2c_test_g2.txt \
  -L2C 0x08 \
  -f 0x01 \
  -w 1000000 \
  -i 10000000 \
  -p 4 \
  -r 260722_1228_w10_i100_champ_hard_config_matched_prefetch_2g
```

summary 생성:

```bash
./scripts/run.sh \
  -C ChampSim_split_L2 \
  -s 0x41 \
  -T trace_gtrace_l2c_test_g2.txt \
  -L2C 0x08 \
  -f 0x01 \
  -r 260722_1228_w10_i100_champ_hard_config_matched_prefetch_2g
```

비교 대상:

| 구분 | metrics |
|---|---|
| `_L2C 2i6d` 기준 | `outputs/260721_2005_w10_i100_champ_split_2g/summary/fdip_0/2i6d/metrics.csv` |
| `split_L2` 2i6d 강제 설정 | `outputs/verify/260722_1228_w10_i100_champ_hard_config_matched_prefetch_2g/summary/fdip_0/2i6d/metrics.csv` |

비교 결과:

| 항목 | 결과 |
|---|---:|
| 공통 trace row | 22 |
| 기준에만 있는 row | 0 |
| 재검증 결과에만 있는 row | 0 |
| 문자열 column 차이 | 0 |
| numeric column 차이 | 21 |
| 최대 IPC 차이 | 0.0253 |
| 최대 cycle 차이 | 682,697 |
| 최대 L1D MPKI 차이 | 1.2931 |
| 최대 LLC MPKI 차이 | 1.0871 |

대표 차이:

| trace | metric | `_L2C 2i6d` | `split_L2 2i6d` | delta |
|---|---:|---:|---:|---:|
| `delta_0001` | IPC | 0.6206 | 0.5953 | -0.0253 |
| `delta_0001` | cycles | 16,114,339 | 16,797,036 | +682,697 |
| `delta_0001` | L1D MPKI | 30.7698 | 32.0629 | +1.2931 |
| `delta_0000` | LLC MPKI | 9.9891 | 8.9020 | -1.0871 |
| `sierra.a.6_0000` | IPC | 0.4973 | 0.4963 | -0.0010 |

### 결론

`ChampSim_split_L2`의 `L2IC=2way`, `L2DC=6way` 구성은 `_L2C`의 `L2C partition 2i6d`와 완전히 동일한 결과를 내지 않는다.

처음에는 `_L2C`가 하나의 `L2C` object 내부에서 instruction/data way 선택만 제한하고, `split_L2`만 `L2IC/L2DC`를 별도 cache object로 구성한다고 해석했다. 그러나 코드 확인 결과 이 해석은 틀렸다.

`ChampSim_Split`도 `-L2C 0x08`처럼 static partition을 받으면 config parse 단계에서 `L2I`와 `L2D` cache object를 생성한다.

근거:

```text
ChampSim_Split/config/parse.py
  partition == 'static'
  L2I = chain(L2I config, L2C config)
  L2D = chain(L2D config, L2C config)
  instruction_ways -> L2I.ways
  data_ways -> L2D.ways
  pinned_cache_names += L2I/L2D

ChampSim_Split/config/defaults.py
  L1I -> L2I -> LLC
  L1D -> L2D -> LLC
```

따라서 `_L2C 2i6d`와 `split_L2 2i6d`의 차이는 “하나는 내부 way partition이고 하나는 별도 object”라서 생긴 것이 아니다. 두 구현 모두 split L2 object 구조를 갖는다.

현재 확인된 구조 차이 후보는 다음과 같다.

| 항목 | `ChampSim_Split` | `ChampSim_split_L2` 현재 상태 |
|---|---|---|
| Instruction L2 name | `L2I` | `L2IC` |
| Data L2 name | `L2D` | `L2DC` |
| L1I lower level | `L2I` | `L2IC` |
| L1D lower level | `L2D` | `L2DC` |
| PTW lower level | `L1D` | `L2DC` |
| `-L2C` compatibility parse | 있음 (`apply_l2c_compat`) | 없음. config에 직접 `L2IC/L2DC`를 강제 설정 |
| base code version | `ChampSim_Split` branch | 최신 `ChampSim` pull 후 split patch 재적용 |

특히 PTW 경로 차이는 결과 차이의 강한 후보이다. `ChampSim_Split`는 page walk가 `L1D`를 lower level로 쓰도록 유지되어 있고, `split_L2`는 현재 `PTW -> L2DC`로 되어 있다. 이 차이는 STLB miss 처리, data-side queue pressure, L2D/LLC traffic ordering에 영향을 줄 수 있다.

정리하면:

- `ChampSim_Split shared`와 원본 `ChampSim shared`는 동일 config에서 완전히 동일하다.
- `_L2C 2i6d`와 `split_L2 2i6d`는 둘 다 split L2 object 구조지만 현재 결과는 완전히 동일하지 않다.
- 다음 검증은 `split_L2`의 PTW lower level을 `L1D`로 맞추고, 가능하면 `ChampSim_Split`의 `apply_l2c_compat` 방식까지 반영한 뒤 다시 비교해야 한다.

---

## 재검증: PTW lower level을 L1D로 맞춘 뒤 비교

위 비교에서 가장 큰 구조 차이는 PTW의 lower level이었다. `_L2C`는 page table walker가 기존 ChampSim 구조처럼 `L1D`를 거쳐 내려가지만, `split_L2`는 `L2DC`로 바로 내려가도록 되어 있었다.

따라서 `ChampSim_split_L2/config/defaults.py`를 다음과 같이 수정했다.

```diff
 def ptw_core_defaults(cpu):
     ''' Generate the lower levels that a default core would expect for each of its PTWs '''
-    yield { 'name': cpu.get('PTW'), 'lower_level': cpu.get('L2DC') }
+    yield { 'name': cpu.get('PTW'), 'lower_level': cpu.get('L1D') }
```

이 수정 후 `split_L2`를 다시 빌드하고, 기존과 같은 조건으로 `2i6d`를 재실행했다.

```bash
./scripts/run.sh \
  -C ChampSim_split_L2 \
  -b \
  -r 260722_1228_w10_i100_champ_hard_config_matched_prefetch_2g
```

```bash
./scripts/run.sh \
  -C ChampSim_split_L2 \
  -t \
  -T trace_gtrace_l2c_test_g2.txt \
  -L2C 0x08 \
  -f 0x01 \
  -w 1000000 \
  -i 10000000 \
  -p 4 \
  -r 260722_1228_w10_i100_champ_hard_config_matched_prefetch_2g
```

summary 생성:

```bash
./scripts/run.sh \
  -C ChampSim_split_L2 \
  -s 0x41 \
  -T trace_gtrace_l2c_test_g2.txt \
  -L2C 0x08 \
  -f 0x01 \
  -r 260722_1228_w10_i100_champ_hard_config_matched_prefetch_2g
```

비교 대상:

| 구분 | metrics |
|---|---|
| `_L2C 2i6d` 기준 | `outputs/260721_2005_w10_i100_champ_split_2g/summary/fdip_0/2i6d/metrics.csv` |
| `split_L2` PTW=`L1D` 재검증 | `outputs/verify/260722_1228_w10_i100_champ_hard_config_matched_prefetch_2g/summary/fdip_0/2i6d/metrics.csv` |

비교 결과:

| 항목 | 결과 |
|---|---:|
| 공통 trace row | 22 |
| 기준에만 있는 row | 0 |
| 재검증 결과에만 있는 row | 0 |
| 문자열 column 차이 | 0 |
| numeric column 차이 | 0 |

단, `l2c_mpki` column은 표시 방식 차이가 있었다. `_L2C` 쪽은 split mode에서도 `0.0`을 출력하고, `split_L2` 쪽은 단일 `L2C` object가 없으므로 빈 값으로 남는다. 이 값은 split mode에서 의미 있는 총합 지표가 아니며, `l2i_mpki`와 `l2d_mpki`를 기준으로 봐야 한다. 실제 numeric metric 비교에서는 차이가 없었다.

### 최종 결론

`ChampSim_split_L2`의 `2i6d` 결과는 PTW lower level을 `L1D`로 맞추면 `_L2C 2i6d` 결과와 `metrics.csv` 기준으로 완전히 동일하다.

따라서 이전의 차이는 L2 split 방식 자체의 차이가 아니라 PTW가 `L1D`를 거치지 않고 `L2DC`로 바로 연결된 hierarchy 차이에서 발생한 것으로 판단한다. 이 검증 결과를 기준으로 보면, `_L2C`와 `split_L2`는 다음 조건에서 같은 동작을 한다.

| 조건 | 필요 설정 |
|---|---|
| I-cache path | `L1I -> L2I/L2IC -> LLC` |
| D-cache path | `L1D -> L2D/L2DC -> LLC` |
| PTW path | `PTW -> L1D -> L2D/L2DC -> LLC` |
| L2I/L2D ways | 같은 instruction/data way 수 |
| prefetcher/replacement | 같은 policy |

즉, split L2 구현을 비교할 때는 L1I/L1D의 lower level뿐 아니라 PTW path까지 반드시 동일하게 맞춰야 한다.

---

## 추가 검증: `split_L2` 4:4 강제 설정 비교

`2i6d`가 PTW 경로를 맞춘 뒤 완전히 동일해졌으므로, 같은 방식으로 `4i4d`도 검증했다. 이번에는 `run.sh`에서 `-f`를 주지 않았다. 현재 `run.sh`는 `-f`가 없으면 `--ftq_size`를 ChampSim binary에 넘기지 않으므로, FDIP가 없는 `ChampSim_split_L2`에서도 `src/main.cc`에 `--ftq_size` compatibility option을 둘 필요가 없다.

먼저 `ChampSim_split_L2/src/main.cc`에 임시로 추가했던 `--ftq_size` 무시 option을 되돌렸다.

```diff
-  uint32_t ignored_ftq_size = 0;
-  app.add_option("--ftq_size", ignored_ftq_size, "Accepted for run.sh compatibility; ignored by this ChampSim build");
-
   app.add_option("traces", trace_names, "The paths to the traces")->required()->expected(NUM_CPUS)->check(CLI::ExistingFile);
```

그 다음 `ChampSim_split_L2/champsim_config.json`을 4:4 의미로 직접 수정했다.

```diff
   "L2DC": {
     "sets": 1024,
-    "ways": 6,
+    "ways": 4,
     ...
   },

   "L2IC": {
     "sets": 1024,
-    "ways": 2,
+    "ways": 4,
     ...
   },
```

빌드:

```bash
./scripts/run.sh \
  -C ChampSim_split_L2 \
  -b \
  -r 260722_1228_w10_i100_champ_hard_config_matched_prefetch_2g
```

실행:

```bash
./scripts/run.sh \
  -C ChampSim_split_L2 \
  -t \
  -T trace_gtrace_l2c_test_g2.txt \
  -L2C 0x10 \
  -w 1000000 \
  -i 10000000 \
  -p 4 \
  -r 260722_1228_w10_i100_champ_hard_config_matched_prefetch_2g
```

실행 로그에서 `-f`가 전달되지 않았음을 확인했다.

```text
FTQ size: 0 (not passed, ChampSim default)
L2C policy: 4i4d
```

summary 생성:

```bash
./scripts/run.sh \
  -C ChampSim_split_L2 \
  -s 0x41 \
  -T trace_gtrace_l2c_test_g2.txt \
  -L2C 0x10 \
  -r 260722_1228_w10_i100_champ_hard_config_matched_prefetch_2g
```

### Parser alias 보정

처음 summary를 만들었을 때 IPC, cycles, L1/LLC 지표는 `_L2C 4i4d`와 같았지만, `l2i_mpki`, `l2d_mpki`, `l2c_mpki` 계열이 빈 값으로 남았다. 원인은 parser가 split-L2 cache 이름을 `L2I/L2D`로만 가정하고 있었기 때문이다.

`ChampSim_split_L2` 로그 이름:

```text
cpu0->cpu0_L2IC TOTAL ...
cpu0->cpu0_L2DC TOTAL ...
```

`ChampSim_Split` 로그 이름:

```text
cpu0->cpu0_L2I TOTAL ...
cpu0->cpu0_L2D TOTAL ...
```

의미상 `L2IC == L2I`, `L2DC == L2D`이므로 `parser/parse_outputs.py`에 alias를 추가했다.

```diff
 def normalize_cache_name(name):
     if "_" in name and name.startswith("cpu"):
-        return name.split("_", 1)[1]
-    return name
+        name = name.split("_", 1)[1]
+    split_l2_aliases = {
+        "L2IC": "L2I",
+        "L2DC": "L2D",
+    }
+    return split_l2_aliases.get(name, name)
```

이 보정은 log parser의 이름 해석만 바꾸며, 시뮬레이션 동작에는 영향을 주지 않는다.

### 비교 결과

비교 대상:

| 구분 | metrics |
|---|---|
| `_L2C 4i4d` 기준 | `outputs/260721_2005_w10_i100_champ_split_2g/summary/fdip_0/4i4d/metrics.csv` |
| `split_L2` 4i4d 강제 설정 | `outputs/verify/260722_1228_w10_i100_champ_hard_config_matched_prefetch_2g/summary/fdip_0/4i4d/metrics.csv` |

비교 결과:

| 항목 | 결과 |
|---|---:|
| 공통 trace row | 22 |
| 기준에만 있는 row | 0 |
| 재검증 결과에만 있는 row | 0 |
| blank field 차이 | 0 |
| 문자열 column 차이 | 0 |
| numeric column 차이 | 0 |

### 결론

`ChampSim_split_L2`의 `4i4d` 직접 설정 결과도 `_L2C 4i4d` 결과와 `metrics.csv` 기준으로 완전히 동일하다.

현재까지 확인된 결과는 다음과 같다.

| 비교 | 결과 |
|---|---|
| `ChampSim_Split shared` vs 원본 `ChampSim shared` | 동일 |
| `ChampSim_Split 2i6d` vs `ChampSim_split_L2 2i6d` | PTW=`L1D`로 맞추면 동일 |
| `ChampSim_Split 4i4d` vs `ChampSim_split_L2 4i4d` | 동일 |

따라서 `ChampSim_Split`와 `ChampSim_split_L2`는 cache hierarchy, PTW path, prefetcher/replacement, way 수를 동일하게 맞추면 같은 결과를 낸다. 남은 차이는 구현 방식의 차이라기보다 config 이름과 parser naming convention 차이로 볼 수 있다.
