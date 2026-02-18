# Blog Enhancements Design Document

> **Feature**: blog-enhancements
> **Plan Reference**: `docs/01-plan/features/blog-enhancements.plan.md`
> **Author**: Sehyup
> **Date**: 2026-02-18
> **Status**: Draft

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

**설계**: 최근 52주 데이터 → CSS Grid (7×52 = 364칸)

**핵심 알고리즘**:
```liquid
{% assign today = "now" | date: "%s" | plus: 0 %}
{% assign one_year_ago = today | minus: 31536000 %}

{% comment %} 날짜별 포스트 수 집계 {% endcomment %}
{% assign post_dates = "" %}
{% for post in site.posts %}
  {% assign post_ts = post.date | date: "%s" | plus: 0 %}
  {% if post_ts >= one_year_ago %}
    {% assign date_str = post.date | date: "%Y-%m-%d" %}
    {% assign post_dates = post_dates | append: date_str | append: "," %}
  {% endif %}
{% endfor %}
```

**그리드 렌더링**:
```liquid
{% comment %} 52주 × 7일 셀 렌더링 {% endcomment %}
<div class="heatmap-grid">
  {% for week in (0..51) %}
    <div class="heatmap-week">
      {% for day in (0..6) %}
        {% assign days_ago = week | times: 7 | plus: day %}
        {% comment %} 해당 날짜의 포스트 수 계산 {% endcomment %}
        <div class="heatmap-cell level-{{ count }}" title="{{ date_str }}: {{ count }}개"></div>
      {% endfor %}
    </div>
  {% endfor %}
</div>
```

> **Liquid 한계**: 날짜 연산이 복잡. `date_to_xmlschema` 필터와 오프셋 계산으로 처리.

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

**SCSS 구조**:
```scss
// 통계 대시보드 스타일
// Chirpy CSS 변수 활용 (다크/라이트 모드 자동 대응)

.stats-cards { /* 지표 카드 그리드 */ }
.stat-card { /* 개별 카드 */ }

.category-bar-row { /* 카테고리 바 행 */ }
.bar-container { /* 바 배경 */ }
.bar-fill {
  background-color: var(--link-color); /* Chirpy 변수 활용 */
}

.heatmap-grid { display: grid; grid-template-columns: repeat(53, 1fr); }
.heatmap-cell {
  &.level-0 { background: var(--main-border-color); }
  &.level-1 { background: #9be9a8; }
  &.level-2 { background: #40c463; }
  &.level-3 { background: #30a14e; }
  &.level-4 { background: #216e39; }
}

.tag-cloud { /* 워드클라우드 컨테이너 */ }
.tag-sm { font-size: 0.85rem; }
.tag-md { font-size: 1.0rem; }
.tag-lg { font-size: 1.2rem; font-weight: bold; }
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

```liquid
{% assign current_cats = page.categories | join: "-" %}
{% assign series_posts = "" | split: "" %}

{% for post in site.posts reversed %}
  {% assign post_cats = post.categories | join: "-" %}
  {% if post_cats == current_cats and post.categories.size >= 2 %}
    {% assign series_posts = series_posts | push: post %}
  {% endif %}
{% endfor %}

{% if series_posts.size > 1 %}
<div class="series-nav">
  <div class="series-header">
    <i class="fas fa-list-ol"></i>
    <span>{{ page.categories | last }} 시리즈 ({{ series_posts.size }}편)</span>
  </div>
  <ol class="series-list">
    {% for post in series_posts %}
      <li class="{% if post.url == page.url %}current{% endif %}">
        {% if post.url == page.url %}
          <strong>{{ post.title }}</strong>
        {% else %}
          <a href="{{ post.url | relative_url }}">{{ post.title }}</a>
        {% endif %}
      </li>
    {% endfor %}
  </ol>

  {% comment %} 이전/다음 버튼 {% endcomment %}
  {% assign current_index = 0 %}
  {% for post in series_posts %}
    {% if post.url == page.url %}{% assign current_index = forloop.index0 %}{% endif %}
  {% endfor %}

  <div class="series-pagination">
    {% if current_index > 0 %}
      {% assign prev_post = series_posts[current_index | minus: 1] %}
      <a href="{{ prev_post.url | relative_url }}" class="btn btn-sm btn-outline-primary">
        ← {{ prev_post.title | truncate: 30 }}
      </a>
    {% endif %}
    {% assign next_index = current_index | plus: 1 %}
    {% if next_index < series_posts.size %}
      {% assign next_post = series_posts[next_index] %}
      <a href="{{ next_post.url | relative_url }}" class="btn btn-sm btn-outline-primary">
        {{ next_post.title | truncate: 30 }} →
      </a>
    {% endif %}
  </div>
</div>
{% endif %}
```

---

#### `_layouts/post.html` (수정)

현재 `post.html`의 `<div class="content">` 직전에 `series-nav` include 추가:

```html
{% comment %} 시리즈 네비게이션 (2개 이상 카테고리 포스트만) {% endcomment %}
{% if page.categories.size >= 2 %}
  {% include series-nav.html %}
{% endif %}

<div class="content">
  {% include hits-counter.html %}
  {{ content }}
</div>
```

---

#### `_sass/addon/_series-nav.scss` (신규)

```scss
.series-nav {
  border: 1px solid var(--main-border-color);
  border-radius: 0.5rem;
  padding: 1rem;
  margin-bottom: 1.5rem;
  background: var(--sidebar-bg);

  .series-header {
    font-weight: bold;
    margin-bottom: 0.75rem;
    color: var(--link-color);
  }

  .series-list {
    padding-left: 1.5rem;
    .current { font-weight: bold; }
  }

  .series-pagination {
    display: flex;
    justify-content: space-between;
    margin-top: 1rem;
    gap: 0.5rem;
  }
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
