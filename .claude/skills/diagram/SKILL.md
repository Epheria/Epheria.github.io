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

### 인라인 스타일 구조

```html
<div style="margin:1.5rem 0; padding:1.25rem; background:var(--card-bg,#fff); border:1px solid var(--card-border-color,rgba(0,0,0,.125)); border-radius:.5rem; overflow-x:auto;">
  <!-- 다이어그램 내용 -->
</div>

<style>
  /* 컴포넌트별 스코프 스타일 */
  [data-mode="dark"] .my-diagram { /* 다크모드 오버라이드 */ }
</style>
```

### SVG 생성 시 품질 기준

```
- 곡선 화살표: <path d="M... C..." /> (bezier curve) 사용
- 그림자: <filter> + feDropShadow 또는 CSS box-shadow
- 그라디언트: <linearGradient> / <radialGradient> 활용
- 화살표 마커: <defs><marker> 정의 후 marker-end 참조
- 텍스트: text-anchor="middle" dominant-baseline="central"
- 색상: 다크모드 인지하여 두 벌 준비
- viewBox 사용하여 반응형 SVG
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
  options: { /* ... */ }
});
</script>
```

기존 `.chart-wrapper`, `.chart-canvas`, `.chart-title` 클래스는 `_sass/addon/_chart.scss`에 정의되어 있음.

## 다국어 지원

ko/en/ja 포스트 각각에 해당 언어로 텍스트를 포함한 인라인 HTML을 생성한다.
번역 파일 작성 시 다이어그램의 텍스트만 해당 언어로 교체하고 구조는 동일하게 유지.

## CSS 변수 (Chirpy 테마)

다이어그램에서 사용 가능한 테마 변수:
- `--card-bg` — 카드 배경 (#fff / #1e1e2e)
- `--card-border-color` — 카드 테두리
- `--text-color` — 기본 텍스트
- `--text-muted-color` — 보조 텍스트 (#6c757d)
- `--link-color` — 링크 색상

## 워크플로우

1. 사용자가 시각화 요청 (또는 포스트 작성 중 다이어그램이 필요한 맥락 감지)
2. 포스트 내용을 읽고 어떤 시각화가 적합한지 판단
3. 맞춤형 인라인 HTML/CSS/SVG/JS 코드를 직접 생성
4. 포스트 본문의 적절한 위치에 삽입
5. Chart.js 사용 시 front matter에 `chart: true` 확인/추가
