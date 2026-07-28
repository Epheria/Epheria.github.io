---
title: SIMD 이해하기 — 벡터 레지스터 원리부터 Unity Burst Intrinsics까지
date: 2026-07-28 10:00:00 +0900
categories: [Unity, JobSystem]
tags: [simd, vector, intrinsics, neon, avx2, burst, unity-mathematics, vectorization, optimization, unity]
toc: true
toc_sticky: true
image: /assets/img/og/jobsystem.png
chart: true
difficulty: intermediate
prerequisites:
  - /posts/UnityJobSystemBurst/
  - /posts/SoAvsAoS/
tldr:
  - SIMD는 벡터 레지스터 하나에 여러 값을 담아 명령 하나로 동시에 연산하는 CPU 기능입니다. ARM NEON은 128bit로 float 4개, x86 AVX2는 256bit로 8개를 한 번에 처리합니다
  - SIMD는 GPU처럼 별도 장치가 아니라 CPU 코어 안의 실행 포트입니다. 오프로드 비용이 0이라 마이크로초 단위 작업에도 쓸 수 있다는 점이 GPU 컴퓨트와의 결정적 차이입니다
  - i9-14900K를 포함한 인텔 소비자 CPU에는 AVX-512가 없습니다(AVX2 256bit까지). Zen 5는 네이티브 512bit를 지원하고, Radeon은 CU당 SIMD32 유닛 2개로 구성된 SIMD 기계 그 자체입니다
  - 64bit CPU에는 SIMD가 반드시 있습니다 — x86-64는 SSE2, AArch64는 NEON이 아키텍처 필수 사양입니다. Unreal의 VectorRegister·ISPC, Jolt 물리(Horizon Forbidden West), Unity DOTS 상용 게임까지 업계 검증도 끝난 기법입니다
  - 명시적 SIMD 루프는 언제나 같은 5단계입니다 — 상수 브로드캐스트, 벡터 폭 단위 순회, 레인 병렬 연산, 스칼라로 축소, 나머지 꼬리 처리
  - .NET 10 + Apple M4 Pro 실측 결과, float 100만 개 합산은 스칼라 대비 3.6배, 일치 카운트는 2.7배 빨라졌습니다. 두 경우 모두 힙 할당은 0입니다
  - Unity에서 신뢰할 수 있는 SIMD 경로는 Burst뿐입니다. 기본은 자동 벡터화 + Unity.Mathematics이고, Burst Inspector로 검증된 병목에만 Unity.Burst.Intrinsics의 v128을 씁니다
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

## 서론: SIMD는 정말 전문가 전용 기술일까

Ghostty 터미널을 만든 Mitchell Hashimoto가 최근 "SIMD는 모든 프로그래머가 알아야 할 일상적 최적화 수단"이라는 글을 올렸습니다. Ghostty의 코드포인트 검색 루프를 AVX2로 다시 쓰자 약 5배 빨라졌고, 그 코드의 구조가 어셈블리 마법이 아니라 누구나 따라 쓸 수 있는 정형화된 5단계 패턴이었다는 것이 요지입니다.

> Mitchell Hashimoto, *"SIMD Basics"* — <https://mitchellh.com/writing/simd-basics>

이 시리즈에서 SIMD는 이미 여러 번 등장했습니다. [Burst Compiler 심화편](/posts/BurstCompilerDeepDive/)에서는 LLVM의 Loop Vectorizer가 **컴파일러 스스로** 루프를 벡터화하는 과정을 다뤘고, [SoA vs AoS편](/posts/SoAvsAoS/)에서는 벡터화가 잘 되는 메모리 레이아웃을 다뤘습니다. 그런데 두 편 모두 한 가지 질문을 건너뛰었습니다. **SIMD 명령이 하드웨어에서 정확히 무엇을 하길래 빨라지는가**, 그리고 **자동 벡터화가 실패했을 때 직접 쓰려면 어떻게 하는가**입니다.

이번 편의 목표는 세 가지입니다.

1. SIMD를 벡터 레지스터와 레인 수준에서 이해하고, 실제 하드웨어(인텔 i9, Ryzen, Apple M, Radeon)에서 SIMD가 어떤 형태로 존재하는지 확인합니다
2. 명시적 SIMD 루프의 5단계 구조를 C# `Vector<T>`로 직접 작성해 실측합니다
3. 그 지식을 Unity로 가져와, 자동 벡터화 → Unity.Mathematics → Burst Intrinsics로 이어지는 3계층 선택 기준을 정리합니다

측정은 .NET 10 + Apple M4 Pro에서 BenchmarkDotNet으로 직접 수행한 값입니다.

---

## Part 1: SIMD가 하드웨어에서 하는 일

### 스칼라 명령과 벡터 명령

SIMD는 **S**ingle **I**nstruction, **M**ultiple **D**ata의 약자입니다. 이름 그대로 명령(instruction)은 하나인데 그 명령이 처리하는 데이터가 여러 개입니다.

CPU에는 일반 연산에 쓰는 범용 레지스터(Arm64 기준 `x0`~`x30`, 64bit) 외에 **벡터 레지스터**(`v0`~`v31`, 128bit)가 따로 있습니다. `float`은 32bit이므로 128bit 벡터 레지스터 하나에 4개가 들어가고, 이렇게 나뉜 각 칸을 **레인(lane)**이라고 부릅니다. 벡터 덧셈 명령 하나는 두 레지스터의 같은 위치 레인끼리 4쌍의 덧셈을 동시에 수행합니다.

<div class="sml-wrap">
  <div class="sml-grid">
    <div class="sml-col">
      <div class="sml-head sml-head-scalar">스칼라 — 명령 4개</div>
      <div class="sml-row">
        <div class="sml-reg"><span class="sml-lane">a[i]</span></div>
        <span class="sml-op">+</span>
        <div class="sml-reg"><span class="sml-lane">b[i]</span></div>
        <span class="sml-op">=</span>
        <div class="sml-reg"><span class="sml-lane sml-lane-res">c[i]</span></div>
      </div>
      <div class="sml-loop">&#8635; i = 0, 1, 2, 3 — 같은 명령을 4회 반복</div>
      <code class="sml-asm">fadd s0, s1, s2</code>
    </div>
    <div class="sml-col">
      <div class="sml-head sml-head-simd">SIMD — 명령 1개</div>
      <div class="sml-row">
        <div class="sml-reg sml-reg4">
          <span class="sml-lane">a[0]</span><span class="sml-lane">a[1]</span><span class="sml-lane">a[2]</span><span class="sml-lane">a[3]</span>
        </div>
        <span class="sml-op">+</span>
        <div class="sml-reg sml-reg4">
          <span class="sml-lane">b[0]</span><span class="sml-lane">b[1]</span><span class="sml-lane">b[2]</span><span class="sml-lane">b[3]</span>
        </div>
      </div>
      <div class="sml-row sml-row-eq">
        <span class="sml-op">=</span>
        <div class="sml-reg sml-reg4">
          <span class="sml-lane sml-lane-res">c[0]</span><span class="sml-lane sml-lane-res">c[1]</span><span class="sml-lane sml-lane-res">c[2]</span><span class="sml-lane sml-lane-res">c[3]</span>
        </div>
      </div>
      <div class="sml-loop">128bit 레지스터의 레인 4개를 동시에 연산</div>
      <code class="sml-asm">fadd v0.4s, v1.4s, v2.4s</code>
    </div>
  </div>
  <p class="sml-cap">같은 덧셈 4개를 처리하는 두 가지 방법 (Arm64 NEON 기준)</p>
</div>

<style>
.sml-wrap{margin:2rem 0}
.sml-grid{display:grid;grid-template-columns:1fr 1fr;gap:1rem;max-width:740px;margin:0 auto}
.sml-col{border-radius:14px;padding:1.1rem 1rem 1rem;box-shadow:0 2px 12px rgba(0,0,0,.08);background:var(--card-bg,#fff);border:1px solid rgba(128,128,128,.15)}
.sml-head{text-align:center;border-radius:20px;padding:4px 14px;font-size:13.5px;font-weight:700;color:#fff;margin-bottom:1rem}
.sml-head-scalar{background:linear-gradient(135deg,#ef9a9a,#c62828)}
.sml-head-simd{background:linear-gradient(135deg,#81c784,#2e7d32)}
.sml-row{display:flex;align-items:center;justify-content:center;gap:6px;margin-bottom:.5rem;flex-wrap:nowrap}
.sml-row-eq{margin-top:.1rem}
.sml-reg{display:flex;border:1.5px solid #90a4ae;border-radius:6px;overflow:hidden}
.sml-lane{display:flex;align-items:center;justify-content:center;min-width:40px;height:32px;font-size:12px;font-weight:600;background:#e3f2fd;color:#1565c0;border-right:1px dashed #90a4ae;padding:0 4px}
.sml-lane:last-child{border-right:none}
.sml-lane-res{background:#e8f5e9;color:#2e7d32}
.sml-op{font-size:16px;font-weight:700;color:#546e7a}
.sml-loop{text-align:center;font-size:12px;color:var(--text-muted-color,#6c757d);margin:.4rem 0}
.sml-asm{display:block;text-align:center;font-size:11.5px;color:var(--text-muted-color,#6c757d);background:rgba(128,128,128,.08);border-radius:6px;padding:3px 6px}
.sml-cap{text-align:center;margin-top:.75rem;font-size:12.5px;color:var(--text-muted-color,#6c757d);font-style:italic}
[data-mode="dark"] .sml-lane{background:#1a2a3a;color:#90caf9;border-right-color:#546e7a}
[data-mode="dark"] .sml-lane-res{background:#1a3320;color:#a5d6a7}
[data-mode="dark"] .sml-reg{border-color:#546e7a}
[data-mode="dark"] .sml-op{color:#b0bec5}
@media(max-width:768px){.sml-grid{grid-template-columns:1fr}}
</style>

### 벡터 폭 — 플랫폼마다 다른 이론상 상한

한 명령이 몇 개의 값을 처리하는지는 명령어 세트가 제공하는 벡터 레지스터의 폭이 정합니다.

| 명령어 세트 | 레지스터 폭 | float 레인 | 주요 플랫폼 |
|------------|-----------|-----------|------------|
| **ARM NEON** | 128bit | 4개 | 모든 모바일 기기, Apple Silicon, Nintendo Switch |
| **x86 SSE4** | 128bit | 4개 | x86-64 공통 베이스라인 |
| **x86 AVX2** | 256bit | 8개 | 2013년 이후 데스크톱, PS5, Xbox Series |
| **x86 AVX-512** | 512bit | 16개 | 일부 서버·최신 데스크톱 CPU |

게임 프로그래머 입장에서 이 표의 결론은 하나입니다. **크로스플랫폼의 보수적 기준선은 128bit, 즉 "float 4개 = 이론상 4배"**라는 점입니다. 모바일 타깃이면 NEON 128bit로 고정입니다. 데스크톱은 사정이 조금 낫습니다 — Burst의 64bit 데스크톱 기본 설정은 SSE2와 AVX2 두 벌을 컴파일해 두고 런타임에 CPU를 보고 고르므로(runtime dispatch), AVX2를 지원하는 CPU에서는 256bit가 자동으로 활용됩니다. AVX-512는 게임 배포 대상에서 사실상 제외해도 됩니다.

### 왜 항상 4배가 나오지 않는가

레인이 4개라고 해서 아무 코드나 4배가 되지는 않습니다. SIMD가 이득을 내려면 세 가지 전제가 필요합니다.

- **연속 메모리**: 벡터 로드 명령은 메모리에서 연속된 128bit를 통째로 가져옵니다. 데이터가 흩어져 있으면 레인을 채우는 비용이 연산 이득을 잠식합니다
- **동일 연산**: 레인 4개에는 같은 명령이 적용됩니다. 요소마다 다른 처리가 필요하면 SIMD 모델 자체가 성립하지 않습니다
- **분기 최소**: 레인별 `if`는 존재하지 않습니다. 조건 처리는 비교 마스크와 산술로 바꿔야 합니다 (Part 3에서 실제로 해봅니다)

이 세 전제를 코드 구조로 강제하는 것이 바로 [SoA 레이아웃](/posts/SoAvsAoS/)입니다. "SoA가 SIMD에 유리하다"는 이전 편의 결론은, 벡터 로드가 연속 128bit를 요구한다는 하드웨어 제약의 소프트웨어 쪽 표현이었던 셈입니다.

---

## Part 2: 실제 하드웨어의 SIMD — i9, Ryzen, Apple M, 그리고 Radeon

### 전용 파이프라인이 있는가 — 아니요, 코어 안의 실행 포트입니다

"CPU→GPU처럼 SIMD도 전용 파이프라인이 있는가"라는 질문에 먼저 답하면, **SIMD는 별도의 장치나 전송 경로를 갖지 않습니다**. 벡터 유닛은 CPU 코어 내부의 실행 포트 중 일부입니다. 명령 인출·디코드·스케줄러 같은 프론트엔드를 스칼라 명령과 그대로 공유하고, 스케줄러가 명령의 종류를 보고 정수 ALU 포트로 보낼지 벡터 FMA 포트로 보낼지 정할 뿐입니다. 데이터도 같은 L1 캐시에서 직접 읽습니다.

<div class="shw-wrap">
  <div class="shw-grid">
    <div class="shw-panel">
      <div class="shw-head shw-head-cpu">CPU 코어 내부 — SIMD는 실행 포트</div>
      <div class="shw-box shw-box-wide">프론트엔드 (인출 · 디코드)</div>
      <div class="shw-varrow">&#8595;</div>
      <div class="shw-box shw-box-wide">스케줄러 — 명령 종류에 따라 포트 배정</div>
      <div class="shw-varrow">&#8595;</div>
      <div class="shw-ports">
        <div class="shw-box shw-box-scalar">스칼라<br/>ALU 포트</div>
        <div class="shw-box shw-box-vec">벡터 FMA<br/>포트 &#215;2</div>
      </div>
      <div class="shw-varrow">&#8595;</div>
      <div class="shw-box shw-box-wide">L1 캐시 (공유)</div>
      <div class="shw-note">오프로드 비용 0 — µs 단위 작업에도 적용 가능</div>
    </div>
    <div class="shw-panel">
      <div class="shw-head shw-head-gpu">GPU — 별도 디바이스</div>
      <div class="shw-box shw-box-wide">CPU — 커맨드 버퍼 기록</div>
      <div class="shw-varrow shw-varrow-cost">&#8595; PCIe 전송 + 디스패치 지연</div>
      <div class="shw-box shw-box-gpu">GPU<br/><span class="shw-sub">CU &#215; 수십 개, CU마다 SIMD32 유닛 2개</span></div>
      <div class="shw-varrow shw-varrow-cost">&#8595; 결과 readback (동기화 대기)</div>
      <div class="shw-box shw-box-wide">CPU — 결과 수신</div>
      <div class="shw-note">왕복 지연 수십 µs~ms — 대량 작업 전용</div>
    </div>
  </div>
  <p class="shw-cap">같은 "병렬 연산"이지만 위치가 다릅니다 — CPU SIMD는 코어 안, GPU는 버스 건너편</p>
</div>

<style>
.shw-wrap{margin:2rem 0}
.shw-grid{display:grid;grid-template-columns:1fr 1fr;gap:1rem;max-width:740px;margin:0 auto}
.shw-panel{border-radius:14px;padding:1rem;box-shadow:0 2px 12px rgba(0,0,0,.08);background:var(--card-bg,#fff);border:1px solid rgba(128,128,128,.15);display:flex;flex-direction:column}
.shw-head{text-align:center;border-radius:20px;padding:4px 14px;font-size:13px;font-weight:700;color:#fff;margin-bottom:.8rem}
.shw-head-cpu{background:linear-gradient(135deg,#64b5f6,#1565c0)}
.shw-head-gpu{background:linear-gradient(135deg,#ba68c8,#6a1b9a)}
.shw-box{border-radius:8px;padding:.5rem .6rem;text-align:center;font-size:12px;font-weight:600;background:#eceff1;color:#37474f;line-height:1.5}
.shw-box-wide{width:100%}
.shw-ports{display:grid;grid-template-columns:1fr 1fr;gap:.5rem}
.shw-box-scalar{background:#f5f5f5;color:#546e7a}
.shw-box-vec{background:#e8f5e9;color:#2e7d32;border:1.5px solid #66bb6a}
.shw-box-gpu{background:#f3e5f5;color:#6a1b9a;border:1.5px solid #ba68c8;padding:.7rem .6rem}
.shw-sub{font-size:11px;font-weight:500}
.shw-varrow{text-align:center;font-size:13px;color:#90a4ae;padding:2px 0}
.shw-varrow-cost{color:#e65100;font-size:11.5px;font-weight:600}
.shw-note{text-align:center;font-size:11.5px;color:var(--text-muted-color,#6c757d);margin-top:.7rem;font-style:italic}
.shw-cap{text-align:center;margin-top:.75rem;font-size:12.5px;color:var(--text-muted-color,#6c757d);font-style:italic}
[data-mode="dark"] .shw-box{background:#2a2a2e;color:#cfd8dc}
[data-mode="dark"] .shw-box-scalar{background:#26262a;color:#90a4ae}
[data-mode="dark"] .shw-box-vec{background:#1a3320;color:#a5d6a7;border-color:#4caf50}
[data-mode="dark"] .shw-box-gpu{background:#31173a;color:#ce93d8;border-color:#8e24aa}
[data-mode="dark"] .shw-varrow-cost{color:#ffcc80}
@media(max-width:768px){.shw-grid{grid-template-columns:1fr}}
</style>

"실행 포트"라는 위치가 SIMD의 성격을 결정합니다. 별도 장치가 아니므로 **시작 비용이 0**입니다. GPU 컴퓨트는 커맨드 버퍼 기록 → 디스패치 → 결과 readback의 왕복이 최소 수십 마이크로초에서 밀리초 단위라 작은 작업에는 배보다 배꼽이 크지만, SIMD는 루프 하나를 벡터화하는 데 어떤 준비 비용도 없어서 마이크로초 단위 작업에도 그대로 이득이 나옵니다. 대신 코어의 자원을 쓰므로 병렬성의 규모는 코어 수 × 레인 수로 제한됩니다.

다만 "공짜 실행 포트"에도 역사적인 예외가 하나 있었습니다. 초기 AVX-512 구현(Skylake-X)은 512bit 유닛을 돌릴 때 전력 한계로 코어 클럭을 크게 내렸고, 벡터 코드가 같은 코어의 스칼라 코드까지 느리게 만드는 부작용이 있었습니다. 최신 구현에서는 이 문제가 크게 줄어서, Zen 5(Ryzen 9950X)는 AVX-512 전력 바이러스 부하에서도 클럭 하락이 5.7→5.3GHz로 약 10%에 그칩니다.

### 게임 PC의 현주소 — i9에는 AVX-512가 없다

"인텔 i9에서 SIMD를 쓸 수 있는가"에 대한 답은 "AVX2까지는 확실히, AVX-512는 없음"입니다. 2026년 현재 주요 게임용 CPU의 SIMD 지원 현황입니다.

| CPU | 최대 SIMD | 벡터 폭 | 벡터 레지스터 용량 | 비고 |
|-----|----------|--------|------------------|------|
| Intel i9-14900K (Raptor Lake) | AVX2 | 256bit | YMM 16개 = 512B | AVX-512 하드웨어는 있지만 퓨즈로 비활성 |
| Intel Core Ultra 9 285K (Arrow Lake) | AVX2 | 256bit | YMM 16개 = 512B | 소비자 라인 AVX-512 미지원 지속 |
| Intel Nova Lake (2026 예정) | AVX10.2 | 512bit | ZMM 32개 = 2KB | P·E코어 모두 512bit 지원 예고 |
| AMD Ryzen 9 9950X (Zen 5) | AVX-512 | 512bit | ZMM 32개 = 2KB | 네이티브 512bit 데이터패스 (Zen 4는 256bit 더블펌프) |
| Apple M4 | NEON | 128bit | V 32개 = 512B | 폭 대신 파이프 수(P코어당 4개)로 처리량 확보 |

이 표에서 게임 개발자가 기억할 것은 순위표가 아니라 **이력**입니다. 인텔은 11세대(Rocket Lake)에서 소비자용 AVX-512를 지원했다가 12세대(Alder Lake)에서 E-코어와의 명령어 세트 불일치 때문에 비활성화했고, 이후 세대에서도 소비자 라인에는 돌아오지 않았습니다. 반대로 AMD는 Zen 4부터 AVX-512를 넣었고 Zen 5에서 완전한 512bit로 확장했습니다. 그래서 "요즘 데스크톱이면 AVX-512 되겠지"라는 가정은 시장 절반에서 틀립니다 — 배포 대상 전체를 커버하는 안전선은 AVX2(256bit)입니다. Burst가 데스크톱 기본 설정에서 SSE2·AVX2 두 벌을 컴파일해 런타임에 고르는 방식을 택한 것도 바로 이 지원 파편화 때문입니다.

"용량" 관점에서 벡터 레지스터 파일은 킬로바이트 단위로 작습니다. AVX2의 YMM 레지스터 16개를 다 합쳐도 512바이트, AVX-512의 ZMM 32개도 2KB입니다. 벡터 레지스터는 데이터를 담아두는 저장소가 아니라 **L1 캐시에서 흘러들어오는 데이터가 통과하는 창구**이고, 그래서 Part 1의 "연속 메모리" 전제가 다시 중요해집니다. 창구가 아무리 넓어도 공급이 끊기면 소용이 없습니다.

폭이 전부가 아니라는 점도 이 표가 보여줍니다. 실효 처리량은 **폭 × 코어당 벡터 포트 수**입니다. i9의 P-코어는 256bit FMA 포트가 2개라 사이클당 FP32 기준 8레인 × 2포트 × 2연산(곱+합) = 32 FLOP이고, Apple M4의 P-코어는 128bit 파이프 4개라 4레인 × 4파이프 × 2연산 = 역시 32 FLOP입니다. NEON이 "폭이 절반이라 느리다"는 직관은 포트 수를 빼먹은 계산입니다.

### SIMD가 아예 없는 CPU는 — 64bit면 반드시 있습니다

지원 파편화 이야기를 하면 "그럼 SIMD 자체가 없는 CPU도 있는 것 아닌가"라는 걱정이 따라오는데, 64bit를 배포 대상으로 삼는 한 그런 CPU는 없습니다. SIMD의 **유무**는 아키텍처 표준이 보장하기 때문입니다.

- **x86-64**: SSE2(128bit)가 아키텍처 필수 사양입니다. 2003년 첫 x86-64 CPU부터 예외 없이 탑재됐고, 컴파일러는 일반 `float` 연산조차 x87 대신 SSE 레지스터로 컴파일합니다
- **AArch64 (64bit ARM)**: NEON(AdvSIMD)이 필수 사양입니다. 모든 64bit 스마트폰·태블릿·Apple Silicon이 해당됩니다
- **예외는 과거와 임베디드에 있습니다**: 32bit 시절 ARMv7에서는 NEON이 선택 사양이라 이를 뺀 칩(초기 Android 태블릿에 쓰인 NVIDIA Tegra 2가 유명합니다)이 실제로 있었고, Cortex-M 계열 마이크로컨트롤러에는 지금도 벡터 유닛이 없습니다

사실 Part 1의 다이어그램에 이 보장이 이미 숨어 있었습니다. 스칼라 명령 `fadd s0, s1, s2`의 `s0`은 별도의 스칼라 레지스터가 아니라 **벡터 레지스터 `v0`의 하위 32bit**입니다. 64bit CPU에서는 스칼라 부동소수점 코드조차 벡터 레지스터 파일 위에서 돌고 있고, SIMD를 쓴다는 것은 이미 깔려 있는 하드웨어의 나머지 레인을 마저 쓰는 일에 가깝습니다. 그러니 걱정할 것은 "있느냐"가 아니라 앞의 표가 보여준 "폭이 얼마냐" 하나입니다.

### 최소 사양표의 정체 — 폭 가정이 틀리면 Illegal Instruction

그 "폭" 가정이 어긋나면 어떻게 되는지도 봐두어야 합니다. 결과는 성능 저하가 아니라 **즉사**입니다. CPU가 디코드할 수 없는 명령을 만나면 Illegal Instruction 예외가 발생하고 프로세스가 그 자리에서 종료됩니다. 상위 명령어 세트로 빌드된 게임을 구형 CPU에서 실행하면 정확히 이 크래시가 나고, 실제 사고 사례도 여럿입니다.

- **Cyberpunk 2077** (2020) — 실행 파일에 AVX 명령이 포함되어 AVX 미지원 CPU(AMD Phenom 계열 등)에서 크래시. 핫픽스 1.05에서 AVX 사용을 제거해 해결했습니다
- **Helldivers 2** (2024) — 업데이트로 AVX2가 사실상 필수가 되면서 2013년 이전 CPU 사용자들의 게임이 하루아침에 실행 불가로 바뀐 사건
- 소니 산하 PC 포팅 스튜디오 Nixxes는 아예 "이 게임은 AVX2 지원 CPU가 필요합니다"라는 공식 에러 안내 페이지를 운영합니다

게임 최소 사양표의 CPU 모델명이 사실상 이것을 의미하는 경우가 많습니다. "Core i3-8100 이상"이라는 표기는 클럭이 모자라다는 뜻이 아니라 **명령어 세트 세대를 지정**하는 것에 가깝습니다.

개발자 쪽의 표준 해법이 앞에서 언급한 **런타임 디스패치**입니다. SSE2용과 AVX2용 코드를 둘 다 실행 파일에 넣고 시작 시점에 CPUID로 CPU 지원 여부를 확인해 고르는 방식이고, Burst의 데스크톱 기본 설정(SSE2+AVX2 두 벌 컴파일)이 바로 이것입니다. Cyberpunk와 Helldivers 2는 디스패치 없이 상위 명령을 박아 넣었다가 사고가 난 경우입니다. 반면 콘솔은 하드웨어가 고정이라(PS5·Xbox Series의 Zen 2는 AVX2 보장) AVX2를 하드코딩해도 안전합니다 — 콘솔 게임의 PC 포팅에서 유독 이 문제가 터지는 이유입니다.

### Radeon도 SIMD인가 — GPU는 SIMD로 만든 기계입니다

"라데온 같은 GPU에도 SIMD가 있는가"라는 질문은 방향을 뒤집어야 정확해집니다. GPU에 SIMD가 "있는" 정도가 아니라, **GPU는 처음부터 SIMD 유닛을 대량으로 쌓아 만든 기계**입니다.

AMD RDNA 아키텍처의 Compute Unit(CU) 하나는 **SIMD32 유닛 2개**로 구성됩니다. SIMD32 유닛은 32개 레인이 매 사이클 같은 명령을 실행하는, CPU 벡터 유닛의 확대판입니다. 마케팅 용어인 "스트림 프로세서 64개"가 바로 이 32레인 × 2유닛을 풀어 쓴 것이고, Radeon RX 7900 XTX의 CU 96개를 환산하면 FP32 레인이 6,144개입니다. CPU 코어 하나의 8~16레인과는 세 자릿수 차이입니다.

그런데 GPU에서는 아무도 intrinsic을 쓰지 않습니다. 프로그래밍 모델이 다르기 때문입니다.

- **CPU SIMD**: 프로그래머가 레인을 직접 의식합니다. 브로드캐스트·마스크·축소를 코드로 씁니다 (Part 3의 5단계)
- **GPU (SIMT)**: 프로그래머는 "스레드 하나"의 스칼라 코드(HLSL 등)를 쓰고, 하드웨어가 스레드 32개를 wavefront로 묶어 SIMD32 유닛의 레인에 자동 배정합니다
- **분기 처리**: 스레드마다 `if`의 방향이 갈리면(divergence) 하드웨어가 양쪽 경로를 모두 실행하며 마스크로 결과를 골라냅니다 — Part 3에서 우리가 손으로 쓸 마스크 산술을 하드웨어가 대신 해주는 것입니다

즉 SIMT는 SIMD 하드웨어 위에 씌운 편의 계층이고, "분기는 마스크가 된다"는 비용 모델은 CPU와 GPU가 동일합니다. GPU 셰이더에서 분기가 비싸다는 상식의 뿌리가 CPU SIMD에 레인별 `if`가 없다는 사실과 같은 곳에 있습니다.

Unity 맥락에서 이 선택지는 Compute Shader vs Burst Job입니다. 판단 기준은 앞 절의 다이어그램이 이미 보여줬습니다 — 데이터가 이미 GPU에 있거나(렌더링 파이프라인과 연결) 작업량이 왕복 지연을 상쇄할 만큼 크면 Compute Shader, 결과를 매 프레임 CPU 로직이 소비해야 하고 작업이 마이크로초~수백 마이크로초 규모라면 CPU SIMD(Burst)가 맞습니다. 레인 6,144개가 레인 8개를 항상 이기는 게 아닙니다. 이기려면 일단 데이터가 버스를 건너가야 합니다.

---

## Part 3: 명시적 SIMD 루프의 5단계 구조

### 언제나 같은 다섯 단계

Mitchell Hashimoto의 글이 좋은 이유는 SIMD 코드가 언어와 명령어 세트를 불문하고 **항상 같은 5단계**로 구성된다는 점을 짚었기 때문입니다. Zig로 쓰든, C의 intrinsic으로 쓰든, 아래에서 볼 C# `Vector<T>`로 쓰든 구조는 동일합니다.

<div class="sm5-wrap">
  <div class="sm5-flow">
    <div class="sm5-step">
      <div class="sm5-num">1</div>
      <div class="sm5-name">브로드캐스트</div>
      <div class="sm5-desc">상수를 모든 레인에 복사</div>
    </div>
    <div class="sm5-arr">&#8594;</div>
    <div class="sm5-step">
      <div class="sm5-num">2</div>
      <div class="sm5-name">벡터 순회</div>
      <div class="sm5-desc">배열을 벡터 폭 단위로 진행</div>
    </div>
    <div class="sm5-arr">&#8594;</div>
    <div class="sm5-step sm5-step-core">
      <div class="sm5-num">3</div>
      <div class="sm5-name">병렬 연산</div>
      <div class="sm5-desc">레인 전체에 한 명령 적용</div>
    </div>
    <div class="sm5-arr">&#8594;</div>
    <div class="sm5-step">
      <div class="sm5-num">4</div>
      <div class="sm5-name">축소</div>
      <div class="sm5-desc">레인 결과를 스칼라 하나로</div>
    </div>
    <div class="sm5-arr">&#8594;</div>
    <div class="sm5-step">
      <div class="sm5-num">5</div>
      <div class="sm5-name">꼬리 처리</div>
      <div class="sm5-desc">나머지는 스칼라 루프로</div>
    </div>
  </div>
  <p class="sm5-cap">명시적 SIMD 루프의 5단계 — 성패를 가르는 곳은 ③ 병렬 연산 단계</p>
</div>

<style>
.sm5-wrap{margin:2rem 0}
.sm5-flow{display:flex;align-items:stretch;justify-content:center;gap:4px;max-width:760px;margin:0 auto;flex-wrap:nowrap}
.sm5-step{flex:1;min-width:0;border-radius:12px;padding:.8rem .5rem;text-align:center;background:linear-gradient(160deg,#e3f2fd,#bbdefb);box-shadow:0 2px 8px rgba(0,0,0,.08)}
.sm5-step-core{background:linear-gradient(160deg,#fff8e1,#ffe082);box-shadow:0 2px 10px rgba(230,150,0,.25)}
.sm5-num{width:24px;height:24px;border-radius:50%;background:#1565c0;color:#fff;font-size:12.5px;font-weight:800;display:flex;align-items:center;justify-content:center;margin:0 auto .4rem}
.sm5-step-core .sm5-num{background:#e65100}
.sm5-name{font-size:13px;font-weight:700;color:#0d47a1;margin-bottom:.25rem}
.sm5-step-core .sm5-name{color:#bf360c}
.sm5-desc{font-size:11px;line-height:1.5;color:#37474f}
.sm5-arr{display:flex;align-items:center;font-size:15px;color:#90a4ae;font-weight:700}
.sm5-cap{text-align:center;margin-top:.75rem;font-size:12.5px;color:var(--text-muted-color,#6c757d);font-style:italic}
[data-mode="dark"] .sm5-step{background:linear-gradient(160deg,#1a2a3a,#12395c)}
[data-mode="dark"] .sm5-step-core{background:linear-gradient(160deg,#3a2e10,#4d3a08)}
[data-mode="dark"] .sm5-name{color:#90caf9}
[data-mode="dark"] .sm5-step-core .sm5-name{color:#ffcc80}
[data-mode="dark"] .sm5-desc{color:#b0bec5}
@media(max-width:768px){.sm5-flow{flex-direction:column;align-items:stretch}.sm5-arr{justify-content:center;transform:rotate(90deg);padding:2px 0}}
</style>

### C# Vector&lt;T&gt;로 직접 작성하기

.NET의 `System.Numerics.Vector<T>`는 "현재 하드웨어의 벡터 폭"을 추상화한 타입입니다. NEON에서 `Vector<int>.Count`는 4, AVX2에서는 8이 되고, JIT이 각 연산을 해당 플랫폼의 벡터 명령으로 변환합니다. Ghostty의 코드포인트 검색과 같은 구조인 "배열에서 특정 값의 개수 세기"를 5단계 그대로 옮기면 이렇게 됩니다.

```csharp
using System.Numerics;

int CountTarget(int[] data, int target)
{
    // ① 브로드캐스트 — target을 모든 레인에 복사
    var targetVec = new Vector<int>(target);
    var acc = Vector<int>.Zero;

    int width = Vector<int>.Count;   // NEON에서 4
    int i = 0;

    // ② 벡터 순회 — 4개씩 진행
    for (; i <= data.Length - width; i += width)
    {
        var chunk = new Vector<int>(data, i);

        // ③ 병렬 연산 — 일치 레인은 -1(전체 비트 1), 불일치는 0
        acc += Vector.Equals(chunk, targetVec);
    }

    // ④ 축소 — 레인 4개의 누적값을 스칼라 하나로
    int count = -Vector.Sum(acc);

    // ⑤ 꼬리 처리 — 4로 나누어떨어지지 않는 나머지
    for (; i < data.Length; i++)
        if (data[i] == target) count++;

    return count;
}
```

③ 단계가 이 코드의 핵심입니다. 스칼라 버전이라면 `if (data[i] == target) count++`라고 쓸 자리인데, SIMD에는 레인별 분기가 없으므로 **비교 결과를 마스크로 받아 산술로 처리**합니다. `Vector.Equals`는 일치한 레인을 `-1`(모든 비트가 1), 불일치한 레인을 `0`으로 채운 벡터를 돌려주고, 이것을 그대로 누적하면 각 레인에 "일치 횟수 × (-1)"이 쌓입니다. ④에서 부호만 뒤집으면 총 개수입니다. 분기가 마스크 산술로 바뀌는 이 변환이 SIMD 사고방식의 전부라고 해도 과언이 아닙니다.

나머지 단계는 정형화된 보일러플레이트입니다. ①②⑤는 어떤 SIMD 코드를 쓰든 형태가 거의 같고, ④의 축소도 `Vector.Sum` 한 줄입니다. 즉 새로운 문제를 만났을 때 고민할 부분은 "③을 분기 없이 구성할 수 있는가" 하나로 좁혀집니다.

---

## Part 4: 실측 — 스칼라 vs Vector&lt;T&gt;

### 측정 환경과 대상

이론상 4배가 실제로 얼마나 나오는지 제 개발 머신에서 직접 측정했습니다.

- **환경**: .NET 10.0.0, Apple M4 Pro, Arm64 RyuJIT (AdvSIMD), BenchmarkDotNet v0.14.0, `[MemoryDiagnoser]`
- **데이터**: 요소 100만 개 배열 (float 합산 / int 일치 카운트, 시드 고정 난수)
- **비교쌍**: 단순 스칼라 루프 vs 위 5단계 구조의 `Vector<T>` 루프 (`Vector<float>.Count` = 4)

합산 쪽 코드는 카운트보다 더 단순합니다.

```csharp
[Benchmark(Baseline = true)]
public float SumScalar()
{
    float sum = 0f;
    for (int i = 0; i < _floats.Length; i++)
        sum += _floats[i];
    return sum;
}

[Benchmark]
public float SumVector()
{
    var acc = Vector<float>.Zero;
    int width = Vector<float>.Count;
    int i = 0;
    for (; i <= _floats.Length - width; i += width)
        acc += new Vector<float>(_floats, i);   // 레인 4개 동시 누적

    float sum = Vector.Sum(acc);                // 축소
    for (; i < _floats.Length; i++)             // 꼬리
        sum += _floats[i];
    return sum;
}
```

### 결과

| 벤치마크 | Mean | 스칼라 대비 | Allocated |
|----------|-----:|-----------:|----------:|
| SumScalar (float 100만) | 585.5 µs | 1.00x | 0 B |
| **SumVector** | **163.0 µs** | **3.59x 빠름** | 0 B |
| CountScalar (int 100만) | 331.1 µs | 1.00x | 0 B |
| **CountVector** | **124.3 µs** | **2.66x 빠름** | 0 B |

<div class="chart-wrapper">
  <div class="chart-title">스칼라 vs Vector&lt;T&gt; — 100만 요소 처리 시간 (Apple M4 Pro, .NET 10)</div>
  <canvas id="simdBench" class="chart-canvas" height="260"></canvas>
</div>

<script>
window.chartConfigs = window.chartConfigs || [];
window.chartConfigs.push({
  id: 'simdBench',
  type: 'bar',
  data: {
    labels: ['float 100만 개 합산', 'int 100만 개 일치 카운트'],
    datasets: [
      {label:'스칼라 루프',data:[585.5,331.1],backgroundColor:'rgba(244,67,54,0.75)',borderColor:'rgba(244,67,54,1)',borderWidth:1.5},
      {label:'Vector<T> (NEON 128bit)',data:[163.0,124.3],backgroundColor:'rgba(76,175,80,0.75)',borderColor:'rgba(76,175,80,1)',borderWidth:1.5}
    ]
  },
  options: {
    scales: {
      y: {beginAtZero:true,title:{display:true,text:'평균 실행 시간 (µs) — 낮을수록 빠름'},grid:{color:'rgba(128,128,128,0.15)'}},
      x: {grid:{display:false}}
    },
    plugins: {
      legend:{position:'bottom',labels:{padding:16,usePointStyle:true,pointStyleWidth:10}},
      tooltip:{callbacks:{label:function(ctx){return ctx.dataset.label+': '+ctx.parsed.y.toFixed(1)+' µs';}}}
    },
    responsive: true,
    maintainAspectRatio: true
  }
});
</script>

### 숫자 해석 — 왜 3.6배와 2.7배인가

두 결과의 배율이 다른 이유가 이 벤치마크에서 가장 배울 것이 많은 부분입니다.

**합산이 3.59배로 이론 상한(4배)에 근접한 이유**는 스칼라 합산이 최악의 조건이기 때문입니다. `sum += x`는 직전 덧셈이 끝나야 다음 덧셈을 시작할 수 있는 직렬 의존성 체인이라, 스칼라 루프의 속도는 부동소수점 덧셈의 지연시간(latency)에 그대로 묶입니다. 벡터 버전은 이 체인을 레인 4개로 쪼개므로 폭만큼의 이득이 거의 온전히 나옵니다.

**카운트가 2.66배에 그친 이유**는 반대로 스칼라 쪽이 이미 상당히 빠르기 때문입니다. 테스트 데이터에서 일치 확률은 1/256이라 `if (data[i] == target)` 분기는 거의 항상 "불일치"로 예측되고, 분기 예측이 계속 맞는 루프는 파이프라인이 끊기지 않습니다. 상대가 빠를수록 배율은 줄어듭니다 — SIMD의 이득 폭은 벡터 코드가 아니라 **비교 대상인 스칼라 코드가 어디에 묶여 있는지**가 정합니다.

두 가지 주의점도 실측에 함께 드러납니다.

- **부동소수점 합산 순서가 바뀝니다.** 스칼라는 왼쪽부터 하나씩, 벡터는 4개 레인에 나눠 담았다가 마지막에 합치므로 결합 순서가 다르고, 부동소수점 덧셈은 결합법칙이 성립하지 않아 비트 단위로 같은 결과가 보장되지 않습니다. Burst에서 리덕션 벡터화에 `FloatMode.Fast`가 필요한 이유([심화편 Part 2](/posts/BurstCompilerDeepDive/))가 정확히 이것입니다
- **이 숫자는 RyuJIT의 것입니다.** 같은 `Vector<T>` 코드를 Unity에 가져가면 이 배율이 나오지 않습니다. Unity의 Mono 런타임은 `Vector<T>`를 하드웨어 가속 없이 소프트웨어로 처리하고, IL2CPP도 벡터 명령 생성을 보장하지 않습니다

두 번째 주의점이 다음 파트의 주제입니다. Unity에서 SIMD를 쓰는 길은 따로 있습니다.

---

## Part 5: Unity의 SIMD 경로 — 3계층 사다리

### Unity에서 System.Numerics.Vector가 답이 아닌 이유

Unity 런타임에서 SIMD 명령이 실제로 생성되는 경로는 사실상 Burst 하나입니다.

- **Mono**: `Vector<T>` API는 동작하지만 하드웨어 가속이 없습니다. 레인별 연산을 소프트웨어 루프로 흉내 내므로 오히려 스칼라보다 느려질 수 있습니다
- **IL2CPP**: IL을 C++로 변환할 뿐 `System.Numerics` 타입을 벡터 명령으로 특별 취급하지 않습니다. 남는 것은 C++ 컴파일러의 자동 벡터화인데, [심화편](/posts/BurstCompilerDeepDive/)에서 봤듯 자동 벡터화는 조건 하나로 깨지는 취약한 최적화입니다
- **Burst**: Job 코드를 LLVM으로 직접 컴파일하면서 NEON/SSE/AVX 명령을 생성합니다. 벡터화 여부를 Burst Inspector로 검증할 수 있고, `Loop.ExpectVectorized()`로 컴파일 타임에 강제할 수도 있습니다

### Burst는 C#을 어떻게 벡터 명령으로 바꾸나

Burst가 SIMD를 만들어내는 과정은 4단계로 요약됩니다.

1. **수집**: `[BurstCompile]`이 붙은 Job의 IL(중간 언어)을 모읍니다
2. **변환**: 자체 프론트엔드가 IL을 **LLVM IR로 직접 변환**합니다. C++을 거치는 IL2CPP와 갈라지는 지점이 여기입니다 — C++ 소스라는 중간 단계가 없으므로 타입·앨리어싱 정보가 손실 없이 LLVM에 전달됩니다
3. **최적화**: LLVM 패스가 돕니다. SROA가 `float4` 같은 구조체를 통째로 벡터 레지스터에 올리고, Loop Vectorizer가 루프를 벡터 폭 단위로 다시 씁니다
4. **코드 생성**: 타깃별 백엔드가 NEON/SSE2/AVX2 기계어를 만듭니다. 데스크톱에서는 Part 2에서 본 대로 SSE2·AVX2 두 벌 + 런타임 디스패치입니다

이 파이프라인에서 Burst의 결정적 무기는 컴파일 기술이 아니라 **Job 구조가 공짜로 주는 앨리어싱 보장**입니다. Job의 `NativeArray` 필드들은 Safety System이 겹치지 않음을 보장하므로, Burst는 모든 입출력을 alias-free로 간주하고 벡터화할 수 있습니다. C++ 컴파일러가 "이 두 포인터가 같은 메모리를 가리키면 어쩌지"라며 벡터화를 포기하는 지점을 Burst는 그냥 지나갑니다 — [심화편](/posts/BurstCompilerDeepDive/)에서 다룬 "Burst가 C++보다 빠를 수 있는 이유"의 핵심입니다.

예를 들어 `float4` 배열에 스칼라를 곱하는 Job(잠시 뒤 2층 예제로 나올 `ScaleJob`)이 이 파이프라인을 통과하면, 루프 본문은 개념적으로 다음 세 줄로 압축됩니다.

```
ldr  q0, [x0, x2]          ; input에서 128bit (float 4개) 로드
fmul v0.4s, v0.4s, v1.4s   ; 4레인 동시 곱셈 — scale은 v1에 브로드캐스트됨
str  q0, [x1, x2]          ; output에 128bit 저장
```

C# 한 줄(`output[i] = input[i] * scale`)이 로드-연산-저장 각 1명령으로 떨어진 셈입니다. 이것이 실제로 나왔는지 확인하는 곳이 Burst Inspector이고, LLVM 패스별 상세와 어셈블리 읽는 법은 [심화편 Part 1·3](/posts/BurstCompilerDeepDive/)에 있습니다.

그래서 Unity에서 SIMD 최적화를 한다는 것은 곧 Burst 위에서 어느 수준까지 내려갈지 고르는 일이 됩니다. 선택지는 세 계층입니다.

<div class="sbi-wrap">
  <div class="sbi-ladder">
    <div class="sbi-tier sbi-tier1">
      <div class="sbi-tier-head"><span class="sbi-badge sbi-badge1">1층 — 기본</span> 자동 벡터화</div>
      <div class="sbi-tier-body">[BurstCompile] + Job + NativeArray만으로 LLVM Loop Vectorizer에 맡깁니다. 코드는 평범한 C# 루프 그대로이고, 대부분의 경우 여기서 끝나야 정상입니다.</div>
    </div>
    <div class="sbi-tier sbi-tier2">
      <div class="sbi-tier-head"><span class="sbi-badge sbi-badge2">2층 — 권장</span> Unity.Mathematics</div>
      <div class="sbi-tier-body">float4·int4를 쓰면 Burst가 타입을 벡터 레지스터에 직접 매핑합니다. 자동 벡터화의 성공 여부에 덜 의존하면서도 코드는 이식성을 유지합니다.</div>
    </div>
    <div class="sbi-tier sbi-tier3">
      <div class="sbi-tier-head"><span class="sbi-badge sbi-badge3">3층 — 최후</span> Unity.Burst.Intrinsics</div>
      <div class="sbi-tier-body">v128 타입과 NEON/SSE intrinsic으로 명령을 직접 지정합니다. 플랫폼별 분기가 필요해지므로, Burst Inspector로 1·2층의 실패를 확인한 병목에만 씁니다.</div>
    </div>
  </div>
  <div class="sbi-axis">
    <span>&#9650; 이식성·유지보수성</span>
    <span>제어력·확실성 &#9660;</span>
  </div>
  <p class="sbi-cap">Unity SIMD의 3계층 — 아래로 내려갈수록 확실해지지만 코드가 플랫폼에 묶입니다</p>
</div>

<style>
.sbi-wrap{margin:2rem 0}
.sbi-ladder{max-width:680px;margin:0 auto;display:flex;flex-direction:column;gap:.6rem}
.sbi-tier{border-radius:12px;padding:.9rem 1.1rem;box-shadow:0 2px 10px rgba(0,0,0,.07)}
.sbi-tier1{background:linear-gradient(135deg,#e8f5e9,#dcedc8);border-left:5px solid #2e7d32}
.sbi-tier2{background:linear-gradient(135deg,#e3f2fd,#bbdefb);border-left:5px solid #1565c0}
.sbi-tier3{background:linear-gradient(135deg,#fff8e1,#ffecb3);border-left:5px solid #e65100}
.sbi-tier-head{font-size:14px;font-weight:700;color:#263238;margin-bottom:.35rem}
.sbi-badge{display:inline-block;border-radius:12px;padding:2px 10px;font-size:11.5px;font-weight:700;color:#fff;margin-right:8px}
.sbi-badge1{background:#2e7d32}
.sbi-badge2{background:#1565c0}
.sbi-badge3{background:#e65100}
.sbi-tier-body{font-size:13px;line-height:1.7;color:#37474f}
.sbi-axis{max-width:680px;margin:.6rem auto 0;display:flex;justify-content:space-between;font-size:11.5px;color:var(--text-muted-color,#6c757d)}
.sbi-cap{text-align:center;margin-top:.6rem;font-size:12.5px;color:var(--text-muted-color,#6c757d);font-style:italic}
[data-mode="dark"] .sbi-tier1{background:linear-gradient(135deg,#1a3320,#20401f)}
[data-mode="dark"] .sbi-tier2{background:linear-gradient(135deg,#1a2a3a,#12395c)}
[data-mode="dark"] .sbi-tier3{background:linear-gradient(135deg,#3a2e10,#4d3a08)}
[data-mode="dark"] .sbi-tier-head{color:#eceff1}
[data-mode="dark"] .sbi-tier-body{color:#b0bec5}
</style>

### 1·2층 — 자동 벡터화와 Unity.Mathematics

1층과 2층은 이 시리즈에서 이미 자세히 다뤘으므로 요점만 다시 짚습니다. 자동 벡터화의 성공·실패 조건과 Burst Inspector로 어셈블리를 확인하는 워크플로우는 [Burst Compiler 심화편 Part 3·4](/posts/BurstCompilerDeepDive/)에 있습니다. 2층의 핵심은 `float4` 연산이 자동 벡터화를 기다릴 필요 없이 그 자체로 벡터 명령에 매핑된다는 점입니다.

```csharp
[BurstCompile]
struct ScaleJob : IJobParallelFor
{
    [ReadOnly] public NativeArray<float4> input;
    public NativeArray<float4> output;
    public float scale;

    // float4 곱셈 하나가 NEON fmul v0.4s 명령 하나로 컴파일됩니다
    public void Execute(int i) => output[i] = input[i] * scale;
}
```

주의할 점은 `float3`입니다. 레인 4개짜리 레지스터에 3개만 담기므로 한 레인이 낭비되고, 배열로 두면 16바이트 정렬도 어긋납니다. SIMD를 의식한 데이터라면 처음부터 `float4`로 잡거나, [SoA 레이아웃](/posts/SoAvsAoS/)으로 x·y·z를 각각의 배열로 분리하는 편이 낫습니다.

### 3층 — Unity.Burst.Intrinsics로 직접 쓰기

자동 벡터화가 실패하고 `float4`로도 표현이 안 되는 패턴 — 대표적으로 Part 3의 "마스크 누적" 같은 리덕션 — 은 intrinsic으로 직접 씁니다. Part 3의 카운트 루프를 `Unity.Burst.Intrinsics`의 NEON 버전으로 옮기면 이렇습니다.

```csharp
using Unity.Burst;
using Unity.Burst.Intrinsics;
using Unity.Collections;
using Unity.Collections.LowLevel.Unsafe;
using static Unity.Burst.Intrinsics.Arm.Neon;

[BurstCompile]
unsafe struct CountTargetJob : IJob
{
    [ReadOnly] public NativeArray<int> data;
    public int target;
    public NativeReference<int> result;

    public void Execute()
    {
        int* p = (int*)data.GetUnsafeReadOnlyPtr();
        int count = 0;
        int i = 0;

        if (IsNeonSupported)   // 컴파일 타임 상수 — 런타임 분기 비용 0
        {
            v128 targetVec = new v128(target);        // ① 브로드캐스트
            v128 acc = new v128(0);

            for (; i <= data.Length - 4; i += 4)      // ② 벡터 순회
            {
                v128 chunk = vld1q_s32(p + i);        //    128bit 로드
                v128 mask  = vceqq_s32(chunk, targetVec); // ③ 일치 레인 = -1
                acc = vsubq_s32(acc, mask);           //    -(-1) = +1 누적
            }
            count = vaddvq_s32(acc);                  // ④ 수평 합으로 축소
        }

        for (; i < data.Length; i++)                  // ⑤ 꼬리 + NEON 미지원 폴백
            if (p[i] == target) count++;

        result.Value = count;
    }
}
```

구조가 Part 3의 `Vector<T>` 버전과 완전히 같다는 점을 봐주셨으면 합니다. `Vector.Equals`가 `vceqq_s32`로, `Vector.Sum`이 `vaddvq_s32`로 바뀌었을 뿐 5단계는 그대로입니다. 명시적 SIMD의 학습 비용은 명령어 이름 암기가 아니라 이 구조를 한 번 체득하는 데 있고, 한 번 체득하면 어느 플랫폼의 intrinsic이든 같은 틀에 끼워 넣게 됩니다.

`IsNeonSupported` 분기는 [심화편](/posts/BurstCompilerDeepDive/)에서 다룬 컴파일 타임 평가 메커니즘 덕분에 공짜입니다. Burst는 타깃 플랫폼별로 코드를 따로 컴파일하므로, ARM 빌드에는 NEON 경로만 남고 x86 빌드에는 스칼라 폴백만 남습니다. 반대로 말하면 x86에서도 SIMD를 원한다면 `X86.Sse2` 경로를 별도로 작성해야 한다는 뜻이고, 이 플랫폼별 중복이 3층의 실질적인 유지보수 비용입니다.

---

## Part 6: 게임 소프트웨어의 SIMD 활용 사례

Unity의 Burst가 특별한 경로가 아니라는 것을 보여주는 가장 좋은 방법은 다른 엔진과 상용 게임을 들여다보는 것입니다. 결론부터 말하면 SIMD는 게임 업계에서 검증이 끝난 표준 기법이고, 엔진마다 "어떻게 쓰게 해줄 것인가"의 답만 다릅니다.

### Unreal Engine ① — VectorRegister, 엔진 수학의 바닥

Unreal의 수학 라이브러리는 처음부터 SIMD 위에 서 있습니다. 핵심은 `VectorRegister4Float` 타입입니다. 이름 그대로 float 4개짜리 벡터 레지스터의 추상화이고, 플랫폼별 구현이 헤더 수준에서 갈립니다 — x86에서는 `UnrealMathSSE.h`가 SSE intrinsic으로, ARM에서는 `UnrealMathNeon.h`가 NEON intrinsic으로 같은 함수 집합(`VectorAdd`, `VectorMultiplyAdd`, `VectorCompareGT`...)을 구현합니다.

구조가 낯설지 않을 것입니다. **Burst의 `v128`과 정확히 같은 "얇은 추상화" 패턴**입니다. 차이는 위치입니다 — Unity에서 `v128`은 최적화가 필요한 사람이 선택적으로 내려가는 3층이지만, Unreal에서 `VectorRegister4Float`는 `FMatrix` 곱셈, `FTransform` 합성, 쿼터니언 보간 같은 엔진 수학 전체가 항상 밟고 있는 바닥입니다. 언리얼 게임은 개발자가 SIMD를 한 줄도 안 써도 매 프레임 트랜스폼 계산에서 SIMD의 이득을 이미 받고 있습니다.

### Unreal Engine ② — ISPC, "CPU의 셰이더"

명시적 SIMD가 필요한 곳에서 Unreal이 택한 답은 intrinsic이 아니라 **전용 컴파일러**입니다. UE 4.23부터 통합된 Intel ISPC(Implicit SPMD Program Compiler)는 C 비슷한 언어로 "요소 하나"의 코드를 쓰면 컴파일러가 SSE4·AVX2·NEON용 벡터 코드를 각각 생성해 주는 도구로, Chaos 물리·클로스 시뮬레이션·애니메이션 시스템에 쓰입니다.

```c
/* ISPC — 스레드 하나처럼 쓰면 레인 폭만큼 병렬 실행됩니다 */
export void Scale(uniform float input[], uniform float scale,
                  uniform float output[], uniform int count)
{
    foreach (i = 0 ... count)
        output[i] = input[i] * scale;   /* 이 한 줄이 AVX2에선 8레인 */
}
```

`foreach` 안의 코드는 GPU 셰이더처럼 "한 요소의 관점"으로 쓰지만 실제로는 벡터 레인 폭 단위로 실행됩니다 — Part 2에서 본 GPU의 SIMT 모델을 CPU 벡터 유닛 위에 소프트웨어로 재현한 것입니다. Unity와 접근을 비교하면 이렇게 정리됩니다.

| | Unity Burst | Unreal ISPC |
|---|------------|-------------|
| 언어 | C# 그대로 | 전용 언어 (C 유사) |
| 벡터화 주체 | LLVM 자동 벡터화 + 선택적 intrinsic | 컴파일러가 SPMD 모델로 항상 벡터화 |
| 멀티 타깃 | 플랫폼별 컴파일 (SSE2·AVX2 디스패치) | ISA별 코드 생성 후 런타임 선택 |
| 적용 범위 | Job 코드 전체 | 물리·클로스 등 지정 모듈 |

접근은 다르지만 도달점은 같습니다. 두 엔진 모두 "게임플레이 코드는 건드리지 않고, 대량 데이터를 도는 시스템 계층만 벡터화한다"는 같은 결론에 수렴했습니다.

### 물리 미들웨어 — Jolt Physics와 Horizon Forbidden West

엔진 바깥의 사례로 가장 좋은 것은 **Jolt Physics**입니다. Horizon Forbidden West와 Death Stranding 2가 쓰는 오픈소스 물리 엔진으로, x86에서 SSE4.1부터 AVX-512까지, ARM64에서 NEON까지 컴파일 타깃으로 지원합니다 — 충돌 검출과 강체 솔버의 핫 루프가 전부 SIMD 위에 있습니다.

Guerrilla Games가 GDC 2022에서 공개한 수치가 SIMD 포함 데이터 지향 설계의 효과를 요약합니다. 상용 물리 엔진에서 Jolt로 교체한 결과 **메모리와 실행 파일 크기를 줄이면서 시뮬레이션 주파수를 2배로 올렸고, CPU 시간은 오히려 덜 썼습니다**. 물리는 "동일 연산 × 대량 연속 데이터" 패턴의 교과서적 표본이라, 이 글에서 다룬 조건이 전부 갖춰진 도메인입니다.

### Unity — 자사 패키지부터 상용 게임까지

Unity 쪽 사례에서 먼저 볼 것은 **Unity 스스로가 Part 5의 3계층을 그대로 실천하고 있다**는 점입니다.

- **Unity Physics**: DOTS 기반의 스테이트리스 물리 엔진으로, 충돌 검출·솔버 전체가 Unity.Mathematics 위의 Burst Job입니다 — 2층(SIMD 친화 타입 + 자동 벡터화)의 대규모 실전입니다. Jolt가 C++ intrinsic으로 한 일을 Unity는 C# + Burst로 한 셈입니다
- **Unity.Collections의 xxHash3**: 해시 함수 하나에 구현이 두 벌 들어 있습니다. Unity.Mathematics 기반의 범용 구현과, AVX2 지원 플랫폼에서 쓰이는 **Burst intrinsics 기반 구현**입니다. 공식 문서 기준으로 intrinsics 구현이 큰 데이터에서 30~50% 추가 이득을 냅니다 — "검증된 병목에만 3층으로 내려간다"는 원칙과 "내려가면 플랫폼별 두 벌을 유지한다"는 비용을 모두 보여주는 표본입니다

상용 게임 쪽 검증 사례로는 V Rising(2022, ECS 기반 출시)과 Cities: Skylines II가 있습니다. 특히 CS2는 도시 전체의 시민·교통 시뮬레이션을 ECS + Burst로 돌리는, 현재까지 가장 큰 DOTS 상용 게임입니다.

CS2에는 반면교사의 교훈도 있습니다. 출시 직후의 성능 논란을 분석한 자료를 보면 병목은 Burst로 컴파일된 시뮬레이션이 아니라 **GPU 렌더링 쪽**(과도한 버텍스의 LOD 미비 등)이었습니다. 시뮬레이션 계층을 SIMD로 아무리 빠르게 만들어도 프레임 타임은 가장 느린 병목이 결정합니다 — 다음 파트에서 정리할 "병목이 연산인가"라는 질문을 상용 게임 스케일에서 보여준 사례입니다.

이 사례들을 관통하는 공통점은 SIMD가 **시스템 계층에 집중된다**는 것입니다. 물리(Jolt·Chaos·Unity Physics), 애니메이션(ISPC), 트랜스폼 수학(VectorRegister), 해시 같은 유틸리티(xxHash3), 대량 시뮬레이션(DOTS) — 전부 엔진·미들웨어 레벨이고, 그 위의 게임플레이 코드는 어느 사례에서도 벡터화 대상이 아닙니다. Part 7의 판단 기준이 업계 전체의 실천과 일치하는 셈입니다.

---

## Part 7: 적용 판단 — 어디에 쓰고 어디에 쓰지 않는가

### 우선순위는 레이아웃이 먼저

SIMD는 최적화 사다리의 마지막 칸에 가깝습니다. 적용을 검토하는 시점에 이미 두 가지가 끝나 있어야 합니다.

1. **데이터가 연속 메모리에 SoA로 배치되어 있는가.** 흩어진 `GameObject` 필드를 순회하는 코드는 벡터화 대상 자체가 아닙니다. 레이아웃 전환만으로 캐시 효율에서 오는 이득이 먼저 나오고, SIMD는 그 위에 곱해지는 항입니다
2. **병목이 연산인가.** 데이터가 캐시를 벗어날 만큼 크면 병목은 메모리 대역폭으로 옮겨가고, ALU를 4배로 늘려도 데이터 공급이 따라오지 못합니다. 제 벤치마크의 100만 개(4MB)는 M4 Pro의 L2 캐시 안에 들어가는 크기라 연산 병목이 유지된 경우입니다

이 두 조건을 통과하는 작업은 게임에서 꽤 명확하게 정해져 있습니다. 파티클 시뮬레이션, 프로시저럴 메시 생성, 대량 유닛의 이동·거리 계산, 오디오 DSP처럼 "동일 연산 × 대량 연속 데이터" 패턴입니다. 반대로 일반 게임플레이 로직 — 상태 분기가 많고 객체마다 처리가 다른 코드 — 은 전제 조건인 "동일 연산"부터 성립하지 않으므로 검토 대상이 아닙니다. 원문 글에 "모든 프로그래머가 알아야 한다는 건 과장"이라는 반론 댓글이 붙었는데, 게임 프로그래머에 한정하면 반론 쪽이 맞다고 봅니다. 알아야 할 사람은 위 목록의 시스템을 만드는 사람이고, 나머지는 Burst의 자동 벡터화로 충분합니다.

### SIMD 이전의 질문 — 자료구조가 포인터를 따라가는가

앞의 1번 조건("SoA로 배치되어 있는가")은 사실 더 어려운 질문을 감추고 있습니다. **애초에 배열로 표현할 수 있는 자료구조인가**입니다. 트리·그래프처럼 노드가 서로를 참조하는 구조는 SoA로 "배치를 바꾸는" 정도로 해결되지 않습니다.

포인터 추적(pointer chasing)이 벡터화와 상극인 이유는 분명합니다. 다음에 읽을 주소가 **지금 읽고 있는 값 안에 들어 있기** 때문입니다. 로드가 완료되어야 다음 로드의 주소가 정해지므로 메모리 접근이 직렬로 묶이고, 하드웨어 프리페처는 다음 주소를 예측할 수 없으며, 벡터 로드가 요구하는 "연속된 128bit"는 처음부터 존재하지 않습니다. Part 4에서 스칼라 합산이 느렸던 이유가 부동소수점 덧셈의 지연시간에 묶인 것이었는데, 포인터 추적은 같은 직렬 의존성이 **메모리 지연시간**(캐시 미스 시 수백 사이클)에 걸린 형태입니다. 여기에 SIMD를 얹는 것은 의미가 없습니다. 병목이 연산이 아니니까요.

같은 함정이 자료구조 밖에서도 똑같은 모습으로 나타납니다. 정규식 엔진의 DFA 실행이 대표적인데, 핵심이 `state = table[state][byte]` 한 줄이라 **다음에 읽을 테이블 주소가 방금 읽은 값 안에 들어 있습니다.** 포인터 추적과 구조가 같으니 결과도 같아서, grep·ripgrep 같은 검색 도구는 오토마톤 자체를 벡터화하는 대신 **SIMD 프리필터 + 스칼라 검증**으로 역할을 나눕니다. 후보 위치를 골라내는 스캔은 `memchr`(SSE2/AVX2/NEON)이나 Teddy 같은 SIMD 알고리즘이 담당하고, 걸러진 소수의 후보만 느린 상태 기계로 넘어갑니다. 벡터화 가능 여부를 코드의 종류가 아니라 **접근이 직렬인가**가 정한다는 원칙은 게임 밖에서도 그대로 관철됩니다.

해법은 SIMD가 아니라 **선형화**입니다. 포인터를 배열 인덱스로 바꾸고 노드를 연속 배열(아레나)에 담는 변환이고, Rendello가 HN에서 공유한 경험 — 힙에 흩어진 포인터 기반 트리를 선형 배열 구조로 바꿔 캐시 효율을 올린 사례 — 이 정확히 이것입니다.

```csharp
/* Before — 포인터 추적: 노드마다 캐시 미스, 벡터화 불가 */
class Node { Node left, right; float bound; }

/* After — 인덱스 참조: 노드들이 한 배열에 연속으로, 순회가 선형 스캔이 됨 */
struct Node { int left, right; float bound; }   /* 인덱스는 NativeArray<Node>의 첨자 */
```

이 변환은 SIMD와 무관하게도 이득입니다. 인덱스는 32bit라 64bit 포인터보다 노드가 작아지고, 배열 통째로 직렬화·복사·재배치가 가능해지며, GC가 추적할 참조도 사라집니다. Unity에서 `NativeArray` 안에 트리를 담으려면 애초에 이 형태 외에는 선택지가 없기도 합니다.

그리고 여기서 한 걸음 더 들어가면 이 글에서 가장 반직관적인 지점이 나옵니다. **벡터 폭이 자료구조의 분기 계수를 바꿉니다.** 이진 트리를 선형화하는 데서 멈추지 않고, 아예 자식을 4개 가지는 트리로 다시 설계하는 것이죠. 노드 하나를 검사할 때 자식 4개의 경계를 4레인으로 한 번에 비교하기 위해서입니다.

Unity Physics의 BVH가 정확히 그렇게 만들어져 있습니다. `BoundingVolumeHierarchy.Node`의 필드는 `FourTransposedAabbs Bounds`와 `int4 Data`이고, 자식은 최대 4개입니다. 이름의 "Transposed"가 핵심입니다 — AABB 4개를 나란히 두는 대신 x 최솟값 4개, y 최솟값 4개… 식으로 축별로 전치해 담습니다. 노드 안에서 SoA를 한 셈이고, 덕분에 자식 4개와의 교차 판정이 레인 4개짜리 비교 몇 번으로 끝납니다. **이진 BVH가 아니라 4-way BVH인 이유가 알고리즘이 아니라 레지스터 폭에 있습니다.**

Rendello의 "데이터 표현은 교조가 아니라 접근 패턴에 묶여야 한다"는 원칙이 게임 엔진에서는 여기까지 밀고 나갑니다. 접근 패턴이 하드웨어에 묶여 있으니, 표현도 결국 하드웨어에 묶입니다.

그래서 "성급한 최적화"라는 경계심은 절반만 맞습니다. **SIMD 코드를 나중에 얹는 것은 확실히 성급한 최적화지만, 자료구조를 무엇으로 할지는 나중으로 미룰 수 있는 결정이 아닙니다.** 포인터 트리를 4-way 트리 아레나로 바꾸는 일은 호출부 전체를 건드리는 구조 변경이라, 프로파일러가 병목을 지목한 뒤에 시작하면 이미 늦습니다. HN 댓글의 "고성능 레이싱 타이어를 고물차에 끼운다"는 비유가 정확한 것은 이 때문입니다 — 문제는 타이어를 언제 끼우냐가 아니라, 차체가 애초에 그 타이어를 받을 수 있게 설계됐느냐입니다.

### 검증 없는 SIMD는 없다

마지막으로 원문의 조언 중 가장 실용적인 한 줄을 Unity 맥락으로 옮기면 이렇게 됩니다. **벡터화됐다고 믿지 말고 어셈블리로 확인하라.** 자동 벡터화(1층)에 기대는 코드라면 Burst Inspector에서 `fadd v0.4s` 같은 벡터 명령이 실제로 생성됐는지 확인하고, 회귀를 막으려면 `Loop.ExpectVectorized()`를 심어 컴파일 타임에 걸리게 합니다. 명시적으로 작성한 코드(3층)라도 전후 프로파일링 없이는 이득을 주장할 수 없습니다 — 이 글의 3.6배도 측정했으니 말할 수 있는 숫자입니다.

---

## 요약

| 질문 | 답 |
|------|-----|
| SIMD가 빠른 이유 | 128bit 벡터 레지스터의 레인 4개를 명령 하나로 연산 — 이론 상한은 벡터 폭 배수 |
| 전용 파이프라인? | 없음. GPU 같은 별도 장치가 아니라 코어 안의 실행 포트 — 오프로드 비용 0, 규모는 코어 수 × 레인 수로 제한 |
| 하드웨어 현황 | 인텔 소비자 CPU(i9 포함)는 AVX2 256bit까지, Zen 5는 네이티브 512bit, Radeon은 CU당 SIMD32 × 2로 이뤄진 SIMD 기계(SIMT 모델) |
| SIMD 없는 CPU? | 64bit면 반드시 있음 — x86-64는 SSE2, AArch64는 NEON이 아키텍처 필수 사양. 유무가 아니라 폭만 문제 |
| 업계 사례 | Unreal은 VectorRegister(수학의 바닥) + ISPC(Chaos·클로스), Jolt 물리(Horizon Forbidden West)는 SSE4.1~AVX-512·NEON, Unity는 Unity Physics·xxHash3(자사 패키지)와 V Rising·Cities: Skylines II(상용 게임) |
| 구형 CPU 리스크 | 미지원 명령 = Illegal Instruction 즉사 (Cyberpunk 2077 AVX, Helldivers 2 AVX2 사례). 해법은 런타임 디스패치 — Burst 데스크톱 기본값이 이 방식 |
| 명시적 SIMD 작성법 | 브로드캐스트 → 벡터 순회 → 병렬 연산 → 축소 → 꼬리의 고정 5단계, 분기는 마스크 산술로 |
| 실측 이득 (M4 Pro, .NET 10) | float 100만 합산 3.6배, 일치 카운트 2.7배 — 배율은 스칼라 쪽 병목이 결정 |
| Unity에서의 경로 | Burst가 유일한 신뢰 경로. 자동 벡터화 → Unity.Mathematics float4 → Burst Intrinsics v128 순으로 내려가되, 내려가기 전에 Burst Inspector로 확인 |
| 트리·그래프 자료구조 | 포인터 추적은 메모리 지연에 직렬로 묶여 벡터화 불가 → 인덱스 배열 선형화가 선행. 나아가 벡터 폭이 분기 계수를 정함 (Unity Physics BVH = 4-way + `FourTransposedAabbs`) |
| 상태 기계 (게임 밖 사례) | DFA의 `state = table[state][byte]`도 같은 직렬 의존 → grep·ripgrep은 오토마톤 대신 스캔만 벡터화 (SIMD 프리필터 + 스칼라 검증) |

## 시리즈 연결

- [Unity Job System과 Burst](/posts/UnityJobSystemBurst/) — Job·NativeContainer·Burst 기초와 메모리 정렬
- [SoA vs AoS](/posts/SoAvsAoS/) — SIMD의 전제 조건인 데이터 레이아웃
- [Burst Compiler 심화](/posts/BurstCompilerDeepDive/) — 자동 벡터화의 성공·실패 조건과 Burst Inspector 워크스루
- 이번 편 — SIMD 하드웨어 원리와 명시적 SIMD 작성

## 참고 자료

### 1차 출처 · 공식 문서

- Mitchell Hashimoto, *SIMD Basics* — <https://mitchellh.com/writing/simd-basics>
- .NET `Vector<T>` API — <https://learn.microsoft.com/dotnet/api/system.numerics.vector-1>
- Unity Burst Manual, *CPU Intrinsics* — <https://docs.unity3d.com/Packages/com.unity.burst@latest/manual/csharp-burst-intrinsics.html>
- Arm NEON Intrinsics Reference — <https://developer.arm.com/architectures/instruction-sets/intrinsics/>
- AMD, *RDNA Architecture Whitepaper* — <https://gpuopen.com/download/RDNA_Architecture_public.pdf>

### 하드웨어 분석

- Phoronix, *Quantifying The AVX-512 Performance Impact With AMD Zen 5* — <https://www.phoronix.com/review/amd-zen5-avx-512-9950x>
- Chips and Cheese, *Zen 5's AVX-512 Frequency Behavior* — <https://chipsandcheese.com/p/zen-5s-avx-512-frequency-behavior>
- Tom's Hardware, *Ryzen 9000 CPUs drop 10% frequency executing AVX-512* — <https://www.tomshardware.com/pc-components/cpus/ryzen-9000-cpus-drop-10-frequency-executing-avx-512-instructions-intel-cpus-typically-suffer-from-more-substantial-clock-speed-drops>
- TechPowerUp, *Intel Officially Confirms AVX10.2 and APX Support in "Nova Lake"* — <https://www.techpowerup.com/342881/intel-officially-confirms-avx10-2-and-apx-support-in-nova-lake>
- XDA, *A Helldivers 2 update is giving players with older CPUs hell* — <https://www.xda-developers.com/helldivers-2-update-avx2-bug/>
- Nixxes Support, *This game requires a CPU that supports the AVX2 instruction set* — <https://support.nixxes.com/hc/en-us/articles/24667980191645-This-game-requires-a-CPU-that-supports-the-AVX2-instruction-set>

### 게임 업계 사례

- Intel, *Unreal Engine's New Chaos Physics System Screams With In-Depth Intel CPU Optimizations* — <https://www.intel.com/content/www/us/en/developer/articles/technical/unreal-engines-new-chaos-physics-system-screams-with-in-depth-intel-cpu-optimizations.html>
- GDC 2020, *Intel ISPC in Unreal Engine 4 — A Peek Behind the Curtain* — <https://gdcvault.com/play/1026686/Intel-ISPC-in-Unreal-Engine>
- Guerrilla Games, *Architecting Jolt Physics for Horizon Forbidden West* (GDC 2022) — <https://www.guerrilla-games.com/read/architecting-jolt-physics-for-horizon-forbidden-west>
- Jolt Physics (GitHub) — <https://github.com/jrouwe/JoltPhysics>
- paavohtl, *Why Cities: Skylines 2 performs poorly* — <https://blog.paavo.me/cities-skylines-2-performance/>
- Unity Physics Manual — <https://docs.unity3d.com/Packages/com.unity.physics@1.0/manual/index.html>
- Unity.Collections `xxHash3` API (이중 구현 설명) — <https://docs.unity3d.com/Packages/com.unity.collections@2.6/api/Unity.Collections.xxHash3.html>
- Unity Physics `BoundingVolumeHierarchy.Node` API (`FourTransposedAabbs` + `int4`) — <https://docs.unity3d.com/Packages/com.unity.physics@0.3/api/Unity.Physics.BoundingVolumeHierarchy.Node.html>

### 데이터 지향 설계

- Rendello의 Data-Oriented Design 관련 HN 댓글 모음 — <https://hn.algolia.com/?query=Data-Oriented%20Design%20author%3ARendello&sort=byPopularity&type=all>
- Richard Fabian, *Data-Oriented Design* — <https://www.dataorienteddesign.com/dodbook/>

### 게임 밖의 SIMD — 텍스트 검색

- ripgrep의 SIMD 가속 논의 (memchr · Teddy 프리필터) — <https://github.com/BurntSushi/ripgrep/discussions/1822>
- Teddy 다중 패턴 매칭 알고리즘 (Hyperscan 유래) — <https://github.com/jneem/teddy>

### 커뮤니티 · 토론

- GeekNews 소개 및 댓글 논점 — <https://news.hada.io/topic?id=31734>
- Arm Learning Path, *Using NEON intrinsics to optimize Unity on Android* — <https://learn.arm.com/learning-paths/mobile-graphics-and-gaming/using-neon-intrinsics-to-optimize-unity-on-android/>

### 측정 도구

- BenchmarkDotNet — <https://benchmarkdotnet.org/>
