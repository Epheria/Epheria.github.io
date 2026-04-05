---
name: diagram
description: 블로그 포스트에 맞춤형 HTML/SVG/Chart.js 시각화를 생성하여 삽입한다. 템플릿을 사용하지 않고 매번 맥락에 맞는 커스텀 인라인 코드를 직접 생성한다. "다이어그램 넣어줘", "차트 추가", "아키텍처 그려줘", "비교 표 만들어줘", "플로우차트", "파이프라인" 등의 요청에 대응한다.
argument-hint: <diagram-description>
allowed-tools: Read, Edit, Write, Glob, Grep
---

# 커스텀 시각화 생성 스킬

블로그 포스트에 맞춤형 시각화를 **직접 인라인 생성**하는 스킬이다.
미리 만든 템플릿을 사용하지 않고, 매번 해당 다이어그램에 최적화된 HTML/CSS/SVG/JS를 작성한다.

## 핵심 원칙

1. **매번 커스텀 생성** — 재사용 include 없음. 포스트 본문에 인라인으로 직접 삽입
2. **맥락 맞춤** — 데이터 구조와 내용에 맞게 좌표, 색상, 레이아웃을 정밀 계산
3. **고품질 비주얼** — 곡선 화살표, 그라디언트, 그림자, 애니메이션 적극 활용
4. **다크모드 필수** — `[data-mode="dark"]` CSS 또는 JS 감지로 양방향 지원

## 생성 가능한 시각화 유형

### HTML/CSS 다이어그램
- 파이프라인 플로우 (곡선 SVG 화살표 + CSS 박스)
- 의사결정 트리 (SVG 연결선 + 조건 분기)
- 비교 레이아웃 (그리드 + 강조 색상)
- 타임라인
- 프로세스 흐름도

### SVG 다이어그램
- 아키텍처 레이어 다이어그램
- 컴포넌트 관계도 (곡선 bezier 화살표)
- 데이터 흐름 DAG
- 트리 구조 시각화
- 메모리 레이아웃 도식

### Chart.js 차트 (기존 인프라 활용)
- 바 차트 (수직/수평, 그룹, 스택)
- 라인 차트 (다중 데이터셋)
- 레이더 차트
- 도넛/파이 차트

## 생성 규칙

### 필수 준수 사항

```
1. 인라인 JS에서 // 주석 금지 → /* */ 만 사용 (compress.html 호환)
2. 다크모드: [data-mode="dark"] CSS 셀렉터 또는 JS로 감지
3. 반응형: 768px 이하 모바일 대응
4. Chart.js 사용 시: 포스트 front matter에 chart: true 필요
5. Chart.js 패턴: window.chartConfigs 배열에 push (chart-init.html이 처리)
6. 외부 라이브러리 추가 금지: Chart.js, D3, Mermaid 외 CDN 로드 금지
7. 폰트: system-ui, -apple-system 또는 블로그 기본 폰트 사용
```

### CSS 클래스 네이밍 컨벤션

각 다이어그램은 **고유 2~3글자 접두사**로 CSS 클래스를 스코핑한다. 같은 페이지에 여러 다이어그램이 있어도 충돌하지 않는다.

```
접두사 예시:
  gca-  → GC Architecture (레이어)
  gcf-  → GC Flow (데이터 흐름)
  gct-  → GC Tree (의사결정)
  gc-cmp- → GC Compare (비교)
  pip-  → Pipeline (파이프라인)
  
명명 규칙:
  {prefix}-sh   → SVG filter (shadow)
  {prefix}-arr  → SVG marker (arrow)
  {prefix}-af   → arrow fill class
  {prefix}-al   → arrow line class
  {prefix}-g0~3 → gradient IDs
  {prefix}-src  → source node
  {prefix}-q    → question node
  {prefix}-r*   → result node
```

### SVG 다이어그램 템플릿 구조

```html
<div class="my-diagram" style="margin:2rem 0;overflow-x:auto;">
<svg viewBox="0 0 W H" xmlns="http://www.w3.org/2000/svg"
     style="width:100%;max-width:Wpx;margin:0 auto;display:block;
            font-family:system-ui,-apple-system,sans-serif;">
  <defs>
    <!-- 1. 그림자 필터 -->
    <filter id="pre-sh"><feDropShadow dx="0" dy="2" stdDeviation="3" flood-opacity="0.15"/></filter>
    <!-- 2. 화살표 마커 (orient="auto"로 자동 회전) -->
    <marker id="pre-arr" viewBox="0 0 10 10" refX="10" refY="5"
            markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,1 L10,5 L0,9Z" class="pre-af"/>
    </marker>
    <!-- 3. 그라디언트 -->
    <linearGradient id="pre-g0" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#color1"/><stop offset="100%" stop-color="#color2"/>
    </linearGradient>
  </defs>
  
  <!-- SVG 요소 — fill/stroke는 CSS 클래스로 설정 (다크모드 오버라이드 가능) -->
  <rect class="pre-node" x="..." rx="12" filter="url(#pre-sh)"/>
  <text class="pre-txt" text-anchor="middle">텍스트</text>
  <line class="pre-al" marker-end="url(#pre-arr)"/>
</svg>
</div>
<style>
/* 라이트모드 기본 */
.pre-node{fill:#ffcdd2}.pre-txt{fill:#c62828}.pre-al{stroke:#9e9e9e}.pre-af{fill:#9e9e9e}
/* 다크모드 오버라이드 */
[data-mode="dark"] .pre-node{fill:#5c2a2a}[data-mode="dark"] .pre-txt{fill:#ef9a9a}
/* 모바일 대응 */
@media(max-width:768px){.my-diagram svg{min-width:520px}}
</style>
```

**핵심: SVG presentation attribute(fill, stroke)는 CSS보다 우선순위가 낮으므로, 색상은 CSS 클래스로 지정해야 다크모드 오버라이드가 작동한다. `fill="url(#gradient)"`처럼 그라디언트가 필요한 경우만 인라인 attribute로 지정.**

### HTML/CSS 비교 레이아웃 템플릿

```html
<div class="my-cmp" style="margin:2rem 0;overflow-x:auto;">
  <div class="my-cmp-grid">
    <div class="my-cmp-left">
      <div class="my-cmp-badge" style="background:#4CAF50">좌측 제목</div>
      <ul class="my-cmp-list">
        <li><span class="my-cmp-ok">&#10003;</span> 항목</li>
      </ul>
    </div>
    <div class="my-cmp-mid"><span class="my-cmp-vs">VS</span></div>
    <div class="my-cmp-right">
      <div class="my-cmp-badge" style="background:#f44336">우측 제목</div>
      <ul class="my-cmp-list">
        <li><span class="my-cmp-no">&#10007;</span> 항목</li>
      </ul>
    </div>
  </div>
  <p class="my-cmp-cap">캡션 텍스트</p>
</div>
<style>
.my-cmp-grid{display:grid;grid-template-columns:1fr auto 1fr;align-items:stretch;
  max-width:740px;margin:0 auto;border-radius:14px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.08)}
.my-cmp-left{background:linear-gradient(135deg,#e8f5e9,#c8e6c9);padding:1.25rem 1.5rem}
.my-cmp-right{background:linear-gradient(135deg,#ffebee,#ffcdd2);padding:1.25rem 1.5rem}
.my-cmp-mid{display:flex;align-items:center;justify-content:center;padding:0 .5rem;
  background:linear-gradient(180deg,#e8f5e9,#f5f5f5 50%,#ffebee)}
.my-cmp-vs{width:42px;height:42px;border-radius:50%;background:linear-gradient(135deg,#555,#333);
  display:flex;align-items:center;justify-content:center;color:#fff;font-weight:900;font-size:13px}
.my-cmp-badge{text-align:center;border-radius:20px;padding:5px 16px;font-size:14px;font-weight:700;color:#fff;margin-bottom:.75rem}
.my-cmp-list{list-style:none;padding:0;margin:0;font-size:13.5px;line-height:2.1}
.my-cmp-ok{color:#2e7d32;font-weight:700;margin-right:8px}
.my-cmp-no{color:#c62828;font-weight:700;margin-right:8px}
.my-cmp-cap{text-align:center;margin-top:.75rem;font-size:12.5px;color:var(--text-muted-color,#6c757d);font-style:italic}
[data-mode="dark"] .my-cmp-left{background:linear-gradient(135deg,#1a3320,#263e2a)}
[data-mode="dark"] .my-cmp-right{background:linear-gradient(135deg,#3b1a1a,#4a2525)}
[data-mode="dark"] .my-cmp-mid{background:linear-gradient(180deg,#1a3320,#252528 50%,#3b1a1a)}
[data-mode="dark"] .my-cmp-list{color:#ddd}
[data-mode="dark"] .my-cmp-ok{color:#81c784}[data-mode="dark"] .my-cmp-no{color:#ef9a9a}
@media(max-width:768px){.my-cmp-grid{grid-template-columns:1fr!important}.my-cmp-mid{padding:.5rem 0}}
</style>
```

### Chart.js 생성 시

```html
<!-- 포스트 front matter에 chart: true 필수 -->
<div class="chart-wrapper">
  <div class="chart-title">차트 제목</div>
  <canvas id="uniqueId" class="chart-canvas" height="240"></canvas>
</div>

<script>
window.chartConfigs = window.chartConfigs || [];
window.chartConfigs.push({
  id: 'uniqueId',
  type: 'bar',
  data: { /* ... */ },
  options: {
    scales: {
      r: { grid:{color:'rgba(128,128,128,0.15)'}, angleLines:{color:'rgba(128,128,128,0.15)'} },
      y: { grid:{color:'rgba(128,128,128,0.1)'} },
      x: { grid:{display:false} }
    },
    responsive: true,
    maintainAspectRatio: true
  }
});
</script>
```

기존 `.chart-wrapper`, `.chart-canvas`, `.chart-title` 클래스는 `_sass/addon/_chart.scss`에 정의되어 있음.

**Chart.js 다크모드**: grid 색상은 `rgba(128,128,128,0.15)` 등 중립 색상으로 설정하면 라이트/다크 모두 작동.

### 색상 팔레트 가이드

| 용도 | 라이트모드 | 다크모드 |
|------|-----------|---------|
| 위험/경고 (red) | `#ffcdd2` bg / `#c62828` text | `#5c2a2a` bg / `#ef9a9a` text |
| 성공/안전 (green) | `#e8f5e9` bg / `#2e7d32` text | `#1a3320` bg / `#a5d6a7` text |
| 정보 (blue) | `#e3f2fd` bg / `#1565c0` text | `#1a2a3a` bg / `#90caf9` text |
| 주의 (yellow) | `#fff8e1` bg / `#e65100` text | `#3a2e10` bg / `#ffcc80` text |
| 중립 (gray) | `#f5f5f5` bg / `#333` text | `#2a2a2e` bg / `#e0e0e0` text |
| 그라디언트 managed | `#ffcdd2 → #ef9a9a` | opacity 0.82 |
| 그라디언트 unmanaged | `#c8e6c9 → #a5d6a7` | opacity 0.82 |
| 브라켓/라벨 red | `#e57373` | `#ef9a9a` |
| 브라켓/라벨 green | `#66bb6a` | `#a5d6a7` |
| 화살표/연결선 | `#9e9e9e` | `#757575` |

### SVG 애니메이션 (선택적)

위험/강조 노드에 펄스 효과:
```xml
<circle cx="X" cy="Y" r="40" fill="url(#pulse-grad)">
  <animate attributeName="r" values="35;48;35" dur="2s" repeatCount="indefinite"/>
  <animate attributeName="opacity" values="0.8;0.3;0.8" dur="2s" repeatCount="indefinite"/>
</circle>
```

## 다국어 지원

ko/en/ja 포스트 각각에 해당 언어로 텍스트를 포함한 인라인 HTML을 생성한다.

**필수 규칙:**
1. HTML/SVG/CSS 구조는 **3개 언어 완전 동일** — 텍스트만 교체
2. Chart.js canvas ID는 언어별 고유: `myChart` (ko), `myChartEn` (en), `myChartJa` (ja)
3. SVG element ID(`<defs>` 내)는 페이지별 고유이므로 3개 언어 동일 OK
4. CSS 클래스명도 3개 언어 동일 OK (각 언어가 별도 페이지)
5. JA 의사결정 트리: Yes/No → はい/いいえ 로 교체

## CSS 변수 (Chirpy 테마)

다이어그램에서 사용 가능한 테마 변수:
- `--card-bg` — 카드 배경 (#fff / #1e1e2e)
- `--card-border-color` — 카드 테두리
- `--text-color` — 기본 텍스트
- `--text-muted-color` — 보조 텍스트 (#6c757d)
- `--link-color` — 링크 색상

## 참고 구현 (검증 완료)

`_posts/Unity/JobSystem/2026-04-04-UnityGCDeepDive.md` (ko/en/ja)에 6개 다이어그램이 이 패턴으로 구현되어 있다:
1. **레이어 아키텍처** (`gc-arch`) — SVG 4단 레이어 + Managed/Unmanaged 사이드 브라켓
2. **비교 레이아웃** (`gc-cmp`) — HTML Grid + VS 뱃지 + 초록/빨강 컬럼
3. **데이터 플로우** (`gc-flow`) — SVG 6노드 → Bezier 수렴 → 펄스 애니메이션 위험 노드
4. **레이더 차트** (`memoryCompare`) — Chart.js radar 3 datasets
5. **의사결정 트리** (`gc-tree`) — SVG 질문(pill)/결과(rect) 노드 + Yes/No 분기
6. **바 차트** (`gcBudget`) — Chart.js bar 4 categories

## 워크플로우

1. 사용자가 시각화 요청 (또는 포스트 작성 중 다이어그램이 필요한 맥락 감지)
2. 포스트 내용을 읽고 어떤 시각화가 적합한지 판단
3. 고유 접두사 결정 (포스트 주제 약어 2~3글자)
4. 맞춤형 인라인 HTML/CSS/SVG/JS 코드를 직접 생성 (위 템플릿 참고)
5. 포스트 본문의 적절한 위치에 삽입
6. Chart.js 사용 시 front matter에 `chart: true` 확인/추가
7. 다국어 파일이 있으면 텍스트만 교체하여 동일 구조로 삽입
