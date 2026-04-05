---
name: diagram
description: 블로그 포스트에 시각화 컴포넌트(파이프라인, 의사결정 트리, 비교 레이아웃, Chart.js 차트, SVG 아키텍처 다이어그램)를 삽입한다. 다이어그램, 차트, 아키텍처 도식이 필요할 때 사용한다. "다이어그램 넣어줘", "차트 추가", "아키텍처 그려줘", "비교 표 만들어줘" 등의 요청에 대응한다.
argument-hint: <type> [parameters...]
allowed-tools: Read, Edit, Write, Glob, Grep
---

# 시각화 컴포넌트 스킬

블로그 포스트에 HTML/Chart.js/SVG 기반 시각화 컴포넌트를 삽입하는 스킬이다.
Mermaid 대비 커스텀 스타일링, 다크모드, 반응형이 완벽 지원된다.

## 컴포넌트 목록

### 1. HTML 다이어그램 (순수 CSS, front matter 불필요)

#### Pipeline — 선형 파이프라인 (A → B → C)
```liquid
{% include diagrams/pipeline.html
   steps="Cost Field,Integration Field,Flow Field"
   descriptions="각 셀의 이동 비용|목적지까지의 누적 비용|각 셀의 이동 방향 벡터"
   colors="#e8d5b7,#b7d5e8,#b7e8c4"
   direction="horizontal"
%}
```

| 파라미터 | 필수 | 기본값 | 설명 |
|---------|------|--------|------|
| `steps` | O | — | 쉼표로 구분된 단계 이름 |
| `descriptions` | X | — | 파이프(`\|`)로 구분된 각 단계 설명 (HTML 허용) |
| `colors` | X | 자동 팔레트 | 쉼표로 구분된 배경색 |
| `direction` | X | `horizontal` | `horizontal` 또는 `vertical` |

#### Decision Tree — Yes/No 분기 의사결정 (최대 2단계)
```liquid
{% include diagrams/decision-tree.html
   question="지형이 변했는가?"
   yes_result="Cost Field 재계산"
   no_question="목적지가 이동했는가?"
   no_yes_result="Integration Field 재계산"
   no_no_result="재계산 없음 — 캐시 사용"
   no_no_highlight="success"
%}
```

| 파라미터 | 필수 | 기본값 | 설명 |
|---------|------|--------|------|
| `question` | O | — | 루트 질문 |
| `yes_label` / `no_label` | X | Yes / No | 브랜치 라벨 |
| `yes_result` | O | — | Yes 경로 결과 |
| `yes_highlight` | X | — | `success` 또는 `warning` |
| `no_result` | △ | — | No 경로 직접 결과 (2단계 없을 때) |
| `no_question` | △ | — | 2단계 질문 (No 브랜치) |
| `no_yes_result` | △ | — | 2단계 Yes 결과 |
| `no_no_result` | △ | — | 2단계 No 결과 |
| `*_highlight` | X | — | 각 결과에 `success` / `warning` 강조 |

#### Comparison — 좌우 비교 레이아웃
```liquid
{% include diagrams/comparison.html
   left_title="AoS"
   left_items="pos 12B ✓,vel 12B ✗,spd 4B ✗"
   left_color="#FF9800"
   right_title="SoA"
   right_items="pos[0] 12B ✓,pos[1] 12B ✓,pos[2] 12B ✓"
   right_color="#4CAF50"
   caption="캐시 활용률 비교"
%}
```

| 파라미터 | 필수 | 기본값 | 설명 |
|---------|------|--------|------|
| `left_title` / `right_title` | O | — | 열 제목 |
| `left_items` / `right_items` | O | — | 쉼표로 구분된 항목들 |
| `left_color` / `right_color` | X | 빨강 / 초록 | 헤더 색상 |
| `caption` | X | — | 하단 캡션 |

---

### 2. Chart.js 차트 (front matter에 `chart: true` 필수)

#### Bar Comparison — Before/After 바 비교
```liquid
{% include charts/bar-comparison.html
   id="perf" title="성능 비교"
   labels="Before,After" data="120,45"
   colors="rgba(231,76,60,0.75),rgba(39,174,96,0.75)"
   unit="ms"
%}
```

| 파라미터 | 필수 | 기본값 | 설명 |
|---------|------|--------|------|
| `id` | O | — | 고유 canvas ID |
| `title` | X | — | 차트 제목 |
| `labels` | O | — | 항목 라벨 (쉼표 구분) |
| `data` | O | — | 값 (쉼표 구분) |
| `colors` | X | 자동 | rgba 색상 (쉼표 구분) |
| `unit` | X | — | 툴팁 단위 |
| `horizontal` | X | `false` | `"true"`이면 수평 바 |

#### Grouped Bar — 그룹 바 차트 (최대 4 데이터셋)
```liquid
{% include charts/grouped-bar.html
   id="bench" title="벤치마크"
   labels="Count,Where,Select"
   dataset1_name="For" dataset1_data="1.0,1.0,1.0" dataset1_color="rgba(39,174,96,0.7)"
   dataset2_name="LINQ" dataset2_data="3.8,1.05,1.1" dataset2_color="rgba(192,57,43,0.7)"
%}
```

#### Line Chart — 라인 차트 (최대 4 데이터셋)
```liquid
{% include charts/line-chart.html
   id="trend" title="프레임 타임"
   labels="1K,2K,5K,10K"
   dataset1_name="Baseline" dataset1_data="3.2,5.1,14.2,38.5" dataset1_color="#e74c3c"
   dataset2_name="Optimized" dataset2_data="2.8,3.5,5.1,5.2" dataset2_color="#27ae60"
   x_label="에이전트 수" y_label="ms"
%}
```

#### Radar Chart — 레이더 차트 (최대 4 데이터셋)
```liquid
{% include charts/radar-chart.html
   id="algo" title="알고리즘 비교"
   labels="메모리,CPU,확장성,난이도,유연성"
   dataset1_name="A*" dataset1_data="3,4,2,3,4" dataset1_color="rgba(52,152,219,0.5)"
   dataset2_name="Flow Field" dataset2_data="4,2,5,4,3" dataset2_color="rgba(46,204,113,0.5)"
   max_value="5"
%}
```

Chart.js 공통 파라미터: `dataset1_name`, `dataset1_data`, `dataset1_color` ~ `dataset4_*`

---

### 3. SVG 아키텍처 다이어그램 (front matter 불필요)

#### Layer Architecture — 적층 레이어
```liquid
{% include svg-diagrams/layer-architecture.html
   layers="Application,Service,Data,Hardware"
   descriptions="게임 로직|ECS, Job System|NativeArray, Burst|CPU Cache, SIMD"
   colors="#e3f2fd,#bbdefb,#90caf9,#64b5f6"
%}
```

#### Component Diagram — 박스 + 화살표
```liquid
{% include svg-diagrams/component-diagram.html
   boxes="Manager,CostField,IntField,FlowField,AgentSystem"
   connections="0>1,1>2,2>3,0>4,3>4"
   cols="3"
%}
```

`connections` 형식: `소스인덱스>타겟인덱스` (0-based)

#### Data Flow — 좌→우 데이터 흐름 (DAG)
```liquid
{% include svg-diagrams/data-flow.html
   nodes="텍스처,셰이더,모델,머티리얼,렌더링"
   connections="0>3,1>3,2>4,3>4"
   node_colors="#ffd43b,#ffd43b,#ffd43b,#51cf66,#339af0"
%}
```

---

## 다국어 지원

모든 텍스트가 파라미터로 전달되므로 ko/en/ja 각 파일에서 해당 언어 텍스트를 넘기면 된다.

```liquid
<!-- ko -->
{% include diagrams/pipeline.html steps="비용 필드,통합 필드,흐름 필드" %}

<!-- en -->
{% include diagrams/pipeline.html steps="Cost Field,Integration Field,Flow Field" %}

<!-- ja -->
{% include diagrams/pipeline.html steps="コストフィールド,統合フィールド,フローフィールド" %}
```

Decision Tree의 `yes_label`/`no_label`도 덮어쓸 수 있다: `yes_label="はい" no_label="いいえ"`

## 컴포넌트 선택 가이드

| 상황 | 추천 컴포넌트 |
|------|-------------|
| 단계별 프로세스 흐름 | `diagrams/pipeline.html` |
| Yes/No 분기 판단 | `diagrams/decision-tree.html` |
| A vs B 비교 | `diagrams/comparison.html` |
| 수치 성능 비교 | `charts/bar-comparison.html` |
| 여러 항목 벤치마크 | `charts/grouped-bar.html` |
| 시간별 추이 | `charts/line-chart.html` |
| 다축 특성 비교 | `charts/radar-chart.html` |
| 시스템 계층 구조 | `svg-diagrams/layer-architecture.html` |
| 컴포넌트 관계도 | `svg-diagrams/component-diagram.html` |
| 데이터 파이프라인 (DAG) | `svg-diagrams/data-flow.html` |
| 복잡한 그래프/시퀀스 | Mermaid 유지 |

## 구분자 규칙

- 1차 구분자: `,` (쉼표) — 항목 목록
- 2차 구분자: `|` (파이프) — descriptions, 보조 데이터

## 관련 파일

- SCSS: `_sass/addon/_diagrams.scss`, `_sass/addon/_svg-diagrams.scss`, `_sass/addon/_chart.scss`
- Chart.js 로더: `_includes/chart-init.html` (`chart: true` 시 자동 로드)
- 기존 Chart.js 패턴: `window.chartConfigs` 배열에 push
