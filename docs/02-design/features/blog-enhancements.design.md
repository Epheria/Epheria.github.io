# Blog Enhancements Design Document

> **Feature**: blog-enhancements
> **Plan Reference**: `docs/01-plan/features/blog-enhancements.plan.md`
> **Author**: Sehyup
> **Date**: 2026-02-18
> **Status**: Final (구현 완료 반영)

---

## 1. Overview

Plan 문서에서 확정된 3개 기능의 상세 구현 설계.

| 기능 | 구현 순서 | 예상 난이도 |
|------|----------|------------|
| F2. 검색 기능 | Phase 1 (최우선) | 낮음 |
| F1. 통계 대시보드 | Phase 2 | 중간 |
| F3. 시리즈 네비게이션 | Phase 3 | 낮음 |

---

## 2. F2. 검색 기능 (Phase 1)

### 2.1 기술 분석

**현황**: `assets/lib/simple-jekyll-search/simple-jekyll-search.min.js` 이미 존재 (Chirpy 내장).

Chirpy v6.1은 `simple-jekyll-search`를 기반으로 검색을 지원한다. 검색이 동작하려면 두 가지가 필요하다:
1. Jekyll이 빌드 시 생성하는 `assets/js/data/search.json` (포스트 인덱스)
2. 검색 UI (테마 내장 `_includes/search.html` 또는 커스텀 구현)

### 2.2 구현 전략

**단계 1**: `_config.yml` 확인 — 별도 설정 없이 동작 여부 확인

**단계 2**: `assets/js/data/search.json` Liquid 템플릿 생성 — 포스트 제목/카테고리/태그/URL 인덱싱

**단계 3**: 검색 UI 동작 확인 (Chirpy 내장 topbar 검색 버튼 활성화 여부)

### 2.3 파일 상세 설계

#### `assets/js/data/search.json` (신규)

```liquid
---
layout: compress
swcache: true
---
[
  {% for post in site.posts %}
  {
    "title": {{ post.title | jsonify }},
    "url": {{ post.url | relative_url | jsonify }},
    "categories": {{ post.categories | join: ", " | jsonify }},
    "tags": {{ post.tags | join: ", " | jsonify }},
    "date": {{ post.date | date: "%Y-%m-%d" | jsonify }}
  }{% unless forloop.last %},{% endunless %}
  {% endfor %}
]
```

> `layout: compress` + `swcache: true` 는 Chirpy의 기존 패턴 (`assets/js/dist/` 파일들과 동일).

#### `_config.yml` 검색 설정 (불필요)

Chirpy v6.1은 `search.json` 파일 존재만으로 검색을 활성화한다. 별도 config 설정 불필요.

### 2.4 UI 동작 방식

- Chirpy 내장 topbar에 돋보기 아이콘 존재 (테마 gem의 `_includes/` 처리)
- 클릭 시 검색창 노출, `search.json`을 `simple-jekyll-search`로 읽어 결과 표시
- 커스텀 `sidebar.html`은 topbar와 독립적이므로 충돌 없음

### 2.5 검증 방법

```bash
bundle exec jekyll serve
# http://localhost:4000 접속 후 돋보기 아이콘 확인
# "Unity", "Linear Algebra" 등 검색 테스트
```

---

## 3. F1. 통계 대시보드 (Phase 2)

### 3.1 페이지 구조

**접근 경로**: 사이드바 → "Stats" 탭 → `/stats/`

**레이아웃 계층**:
```
_tabs/stats.md
  └── layout: stats (_layouts/stats.html)
        ├── _includes/stats/summary-cards.html
        ├── _includes/stats/category-chart.html
        ├── _includes/stats/heatmap.html
        └── _includes/stats/tag-cloud.html
```

### 3.2 파일별 상세 설계

---

#### `_tabs/stats.md` (신규)

```yaml
---
layout: stats
icon: fas fa-chart-bar
order: 7
title: Stats
---
```

> `order: 7`은 기존 탭(about=6) 이후에 표시.

---

#### `_layouts/stats.html` (신규)

```html
---
layout: default
---
{% include lang.html %}
<div id="stats-page" class="px-1">
  <h1 class="stats-title">📊 Blog Statistics</h1>
  {% include stats/summary-cards.html %}
  {% include stats/category-chart.html %}
  {% include stats/heatmap.html %}
  {% include stats/tag-cloud.html %}
</div>
```

> `layout: default` 상속으로 Chirpy의 사이드바/헤더 유지.

---

#### `_includes/stats/summary-cards.html` (신규)

**설계**:
```liquid
{% assign total_posts = site.posts | size %}
{% assign total_tags = site.tags | size %}
{% assign total_categories = site.categories | size %}
{% assign first_post = site.posts | last %}
{% assign last_post = site.posts | first %}
```

**출력 HTML 구조**:
```html
<div class="stats-cards">
  <div class="stat-card">
    <span class="stat-number">{{ total_posts }}</span>
    <span class="stat-label">총 포스트</span>
  </div>
  <div class="stat-card">
    <span class="stat-number">{{ total_categories }}</span>
    <span class="stat-label">카테고리</span>
  </div>
  <div class="stat-card">
    <span class="stat-number">{{ total_tags }}</span>
    <span class="stat-label">태그</span>
  </div>
  <div class="stat-card">
    <span class="stat-number">{{ first_post.date | date: "%Y" }}</span>
    <span class="stat-label">블로그 시작</span>
  </div>
</div>
```

---

#### `_includes/stats/category-chart.html` (신규)

**설계**: Liquid로 카테고리별 포스트 수 계산 → CSS 너비 비율 계산 → 수평 바 차트

```liquid
{% assign max_count = 0 %}
{% for category in site.categories %}
  {% if category[1].size > max_count %}
    {% assign max_count = category[1].size %}
  {% endif %}
{% endfor %}

{% for category in site.categories %}
  {% assign count = category[1].size %}
  {% assign width_pct = count | times: 100 | divided_by: max_count %}
  <div class="category-bar-row">
    <a href="{{ site.baseurl }}/categories/{{ category[0] | slugify }}/" class="category-name">
      {{ category[0] }}
    </a>
    <div class="bar-container">
      <div class="bar-fill" style="width: {{ width_pct }}%"></div>
    </div>
    <span class="bar-count">{{ count }}</span>
  </div>
{% endfor %}
```

> **CSS 변수 활용**: `--bar-color` 다크/라이트 모드 대응

---

#### `_includes/stats/heatmap.html` (신규)

**설계**: 블로그 시작 연도부터 현재까지 **연도별 × 월별** 활동 히트맵

> **변경 이유**: 52주 일별 방식은 Liquid의 timestamp 날짜 연산 한계로 구현 어려움.
> 연도-월 문자열 비교 방식이 Liquid에서 안정적으로 동작함.

**핵심 알고리즘**:
```liquid
{% assign current_year = "now" | date: "%Y" | plus: 0 %}
{% assign start_year   = site.posts.last.date | date: "%Y" | plus: 0 %}

{% for year in (start_year..current_year) %}
  {% for month_str in months_num %}
    {% assign year_month = year | append: "-" | append: month_str %}
    {% assign count = 0 %}
    {% for post in site.posts %}
      {% assign post_ym = post.date | date: "%Y-%m" %}
      {% if post_ym == year_month %}
        {% assign count = count | plus: 1 %}
      {% endif %}
    {% endfor %}
    {% comment %} level 0~4 산정: 0개/1~2개/3~4개/5~7개/8개+ {% endcomment %}
  {% endfor %}
{% endfor %}
```

**그리드 렌더링** (Flex row 방식):
```liquid
<div class="heatmap-row">
  <span class="heatmap-year">{{ year }}</span>
  <div class="heatmap-months">
    {% for month_str in months_num %}
      <div class="heatmap-cell level-{{ level }}" title="{{ year_month }}: {{ count }}개"></div>
    {% endfor %}
  </div>
</div>
```

---

#### `_includes/stats/tag-cloud.html` (신규)

**설계**: 태그 빈도 기반 폰트 크기 (3단계: sm/md/lg)

```liquid
{% assign max_tag_count = 0 %}
{% for tag in site.tags %}
  {% if tag[1].size > max_tag_count %}
    {% assign max_tag_count = tag[1].size %}
  {% endif %}
{% endfor %}

<div class="tag-cloud">
{% for tag in site.tags %}
  {% assign count = tag[1].size %}
  {% assign ratio = count | times: 3 | divided_by: max_tag_count %}
  {% if ratio >= 2 %}{% assign size_class = "tag-lg" %}
  {% elsif ratio >= 1 %}{% assign size_class = "tag-md" %}
  {% else %}{% assign size_class = "tag-sm" %}
  {% endif %}
  <a href="{{ site.baseurl }}/tags/{{ tag[0] | slugify }}/"
     class="tag-cloud-item {{ size_class }}">
    {{ tag[0] }} <span class="tag-count">{{ count }}</span>
  </a>
{% endfor %}
</div>
```

---

#### `_sass/addon/_stats.scss` (신규)

> Chirpy 테마는 `_sass/addon/` 에 커스텀 SCSS를 추가하면 자동으로 로드됨.

**SCSS 구조** (주요 클래스):
```scss
// 통계 대시보드 스타일
// Chirpy CSS 변수 활용 (다크/라이트 모드 자동 대응)

.stats-page-title { /* 페이지 제목 (stats-title → stats-page-title로 변경) */ }
.stats-section-title { /* 섹션별 소제목 */ }

.stats-cards { /* 지표 카드 그리드 (auto-fit) */ }
.stat-card { background: var(--card-bg, var(--main-bg)); /* hover 시 box-shadow */ }

.category-bar-row { /* 카테고리 바 행 */ }
.bar-fill {
  background: var(--link-color); /* Chirpy 변수 활용 */
  transition: width 0.3s ease;
}

// 히트맵: Flex row 방식 (연도 × 월)
.heatmap-row { display: flex; align-items: center; }
.heatmap-months { display: flex; gap: 4px; }
.heatmap-cell {
  width: 32px; height: 22px; border-radius: 3px;
  &.level-0 { background: var(--main-border-color); }
  &.level-1 { background: #9be9a8; }
  &.level-2 { background: #40c463; }
  &.level-3 { background: #30a14e; }
  &.level-4 { background: #216e39; }
}
[data-mode="dark"] .heatmap-cell.level-0 { background: #21262d; }

.tag-sm { font-size: 0.78rem; }   /* 0.85 → 0.78 */
.tag-md { font-size: 0.92rem; }   /* 1.0  → 0.92 */
.tag-lg { font-size: 1.08rem; font-weight: 600; } /* 1.2 → 1.08 */

// 반응형 (576px 이하)
@media (max-width: 576px) {
  .stats-cards { grid-template-columns: repeat(2, 1fr); }
  .heatmap-cell { width: 22px; }
}
```

---

### 3.3 데이터 흐름

```
Jekyll 빌드 타임
  site.posts ──→ Liquid 집계 ──→ HTML/CSS 렌더링
  site.categories
  site.tags
```

외부 JS 불필요. 완전한 정적 HTML.

---

## 4. F3. 시리즈 네비게이션 (Phase 3)

### 4.1 시리즈 정의

**규칙**: 동일한 카테고리 배열(`categories[0]` + `categories[1]`)을 공유하는 포스트 집합을 "시리즈"로 정의.

```yaml
# 예: Mathematics/Linear Algebra 시리즈
categories: [Mathematics, Linear Algebra]
```

### 4.2 파일별 설계

---

#### `_includes/series-nav.html` (신규)

> **변경 사항**:
> - 시리즈 키 구분자 `-` → `|` (카테고리명에 하이픈 포함 시 충돌 방지)
> - CSS 클래스명: `series-header` → `series-nav-header`, `current` → `current-post`
> - 버튼: Bootstrap `btn-outline-primary` → 커스텀 `.series-nav-btn` (Bootstrap 의존 제거)
> - 진행률 표시 추가: `(현재 / 전체)` 형식

```liquid
{% if page.categories.size >= 2 %}
  {% assign series_key = page.categories[0] | append: "|" | append: page.categories[1] %}
  {% assign series_posts = "" | split: "" %}

  {% for post in site.posts reversed %}
    {% if post.categories.size >= 2 %}
      {% assign post_key = post.categories[0] | append: "|" | append: post.categories[1] %}
      {% if post_key == series_key %}
        {% assign series_posts = series_posts | push: post %}
      {% endif %}
    {% endif %}
  {% endfor %}

  {% if series_posts.size > 1 %}
    {% assign current_index = 0 %}
    {% for post in series_posts %}
      {% if post.url == page.url %}{% assign current_index = forloop.index0 %}{% endif %}
    {% endfor %}

    <div class="series-nav">
      <div class="series-nav-header">
        <i class="fas fa-list-ol fa-fw"></i>
        {{ page.categories[1] }} 시리즈
        <span>({{ current_index | plus: 1 }} / {{ series_posts.size }})</span>
      </div>
      <ol class="series-list">
        {% for post in series_posts %}
          <li class="{% if post.url == page.url %}current-post{% endif %}">
            {% if post.url == page.url %}
              {{ post.title }}
            {% else %}
              <a href="{{ post.url | relative_url }}">{{ post.title }}</a>
            {% endif %}
          </li>
        {% endfor %}
      </ol>

      <div class="series-pagination">
        {% if current_index > 0 %}
          {% assign prev_post = series_posts[current_index | minus: 1] %}
          <a href="{{ prev_post.url | relative_url }}" class="series-nav-btn">
            <i class="fas fa-angle-left fa-fw"></i>
            <span class="nav-label">{{ prev_post.title | truncate: 35 }}</span>
          </a>
        {% else %}
          <span></span>
        {% endif %}

        {% assign next_index = current_index | plus: 1 %}
        {% if next_index < series_posts.size %}
          {% assign next_post = series_posts[next_index] %}
          <a href="{{ next_post.url | relative_url }}" class="series-nav-btn" style="margin-left:auto; text-align:right;">
            <span class="nav-label">{{ next_post.title | truncate: 35 }}</span>
            <i class="fas fa-angle-right fa-fw"></i>
          </a>
        {% endif %}
      </div>
    </div>
  {% endif %}
{% endif %}
```

---

#### `_layouts/post.html` (수정)

`<div class="content">` 직전에 `series-nav` include 추가.

> **변경**: 카테고리 수 조건(`page.categories.size >= 2`)은 `series-nav.html` 내부로 이동 — 레이아웃을 단순하게 유지.

```html
{% comment %} 시리즈 네비게이션 {% endcomment %}
{% include series-nav.html %}

<div class="content">
  {% include hits-counter.html %}
  {{ content }}
</div>
```

---

#### `_sass/addon/_series-nav.scss` (신규)

> **변경 사항**: `sidebar-bg` → `card-bg`, 클래스명 변경, Bootstrap 버튼 제거 후 커스텀 `.series-nav-btn` 추가

```scss
.series-nav {
  border: 1px solid var(--main-border-color, #e1e4e8);
  border-radius: 0.5rem;
  padding: 1rem 1.25rem;
  margin-bottom: 1.5rem;
  background: var(--card-bg, var(--main-bg)); /* sidebar-bg → card-bg */
}

.series-nav-header {  /* series-header → series-nav-header */
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--link-color, #0366d6);
  margin-bottom: 0.75rem;
  display: flex; align-items: center; gap: 0.4rem;
}

.series-list {
  list-style: decimal;
  padding-left: 1.5rem;

  li.current-post {  /* current → current-post */
    font-weight: 700;
    color: var(--link-color, #0366d6);
  }
}

.series-pagination {
  display: flex;
  justify-content: space-between;
  border-top: 1px solid var(--main-border-color, #e1e4e8);
  padding-top: 0.75rem;
  flex-wrap: wrap;
}

/* Bootstrap btn-outline-primary 대체 */
.series-nav-btn {
  display: inline-flex; align-items: center; gap: 0.35rem;
  padding: 0.35rem 0.75rem;
  border: 1px solid var(--main-border-color, #e1e4e8);
  border-radius: 0.35rem;
  font-size: 0.8rem; text-decoration: none;
  color: var(--text-color, inherit);
  max-width: 48%;

  &:hover {
    background: var(--link-color, #0366d6);
    color: #fff;
    border-color: var(--link-color, #0366d6);
  }

  .nav-label { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
}
```

---

## 5. 파일 변경 목록 요약

| 파일 | 작업 | 기능 |
|------|------|------|
| `assets/js/data/search.json` | **신규** | 검색 인덱스 |
| `_tabs/stats.md` | **신규** | 통계 탭 |
| `_layouts/stats.html` | **신규** | 통계 레이아웃 |
| `_includes/stats/summary-cards.html` | **신규** | 핵심 지표 카드 |
| `_includes/stats/category-chart.html` | **신규** | 카테고리 바 차트 |
| `_includes/stats/heatmap.html` | **신규** | 히트맵 |
| `_includes/stats/tag-cloud.html` | **신규** | 태그 클라우드 |
| `_includes/series-nav.html` | **신규** | 시리즈 네비 |
| `_sass/addon/_stats.scss` | **신규** | 대시보드 스타일 |
| `_sass/addon/_series-nav.scss` | **신규** | 시리즈 스타일 |
| `_layouts/post.html` | **수정** | series-nav include 추가 |

**수정 없음**: `_config.yml`, `_includes/sidebar.html`

---

## 6. 구현 위험 요소

| 위험 | 영향 | 대응 |
|------|------|------|
| Liquid 날짜 연산 한계 (히트맵) | 중 | `timestamp` 비교로 처리, 근사값 허용 |
| `_sass/addon/` 자동 로드 미지원 시 | 중 | `assets/css/jekyll-theme-chirpy.scss`에 직접 import |
| 검색 UI가 테마 gem 내부에 있을 경우 | 낮 | 커스텀 search bar HTML 추가 |
| 시리즈 포스트 순서 정렬 | 낮 | `reversed` + 날짜 오름차순 정렬 |

---

## 7. 구현 체크리스트

### Phase 1: 검색 (목표: 1시간)
- [ ] `assets/js/data/search.json` 생성
- [ ] 로컬 빌드로 검색 동작 확인
- [ ] 검색 UI 미동작 시 커스텀 search bar 추가

### Phase 2: 통계 대시보드 (목표: 2~3시간)
- [ ] `_tabs/stats.md` 생성
- [ ] `_layouts/stats.html` 생성
- [ ] `_includes/stats/summary-cards.html` 생성
- [ ] `_includes/stats/category-chart.html` 생성
- [ ] `_includes/stats/heatmap.html` 생성
- [ ] `_includes/stats/tag-cloud.html` 생성
- [ ] `_sass/addon/_stats.scss` 생성 (또는 기존 SCSS에 추가)
- [ ] 다크/라이트 모드 확인
- [ ] 모바일(375px) 레이아웃 확인

### Phase 3: 시리즈 네비게이션 (목표: 1시간)
- [ ] `_includes/series-nav.html` 생성
- [ ] `_layouts/post.html` 수정
- [ ] `_sass/addon/_series-nav.scss` 생성
- [ ] Mathematics/Linear Algebra 시리즈에서 동작 확인

### 최종 검증
- [ ] `bundle exec jekyll serve` 로컬 빌드 성공
- [ ] HTML Proofer 통과
- [ ] `main` branch push → GitHub Actions 배포 성공

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 0.1 | 2026-02-18 | Initial design (검색 우선) |
| 0.2 | 2026-02-18 | 구현 반영 업데이트: 히트맵 방식 변경(52주→연도×월), 시리즈 키 구분자 변경(`-`→`\|`), CSS 클래스명 정정, Bootstrap 버튼 제거 |
