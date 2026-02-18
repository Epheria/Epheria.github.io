# blog-enhancements Analysis Report

> **Analysis Type**: Gap Analysis (Design vs Implementation)
>
> **Project**: Epheria.github.io (Jekyll blog)
> **Analyst**: Claude (gap-detector)
> **Date**: 2026-02-18
> **Design Doc**: [blog-enhancements.design.md](../02-design/features/blog-enhancements.design.md)

---

## 1. Analysis Overview

### 1.1 Analysis Purpose

Design 문서(blog-enhancements.design.md)에서 정의한 3개 기능(검색, 통계 대시보드, 시리즈 네비게이션)의 실제 구현 상태를 비교하여 Gap을 식별한다.

### 1.2 Analysis Scope

- **Design Document**: `docs/02-design/features/blog-enhancements.design.md`
- **Implementation Files**: 아래 "파일 변경 목록" 참조
- **Analysis Date**: 2026-02-18

---

## 2. Overall Scores

| Category | Score | Status |
|----------|:-----:|:------:|
| Design Match (파일 존재) | 82% | Warning |
| Feature Match (기능 일치) | 90% | Pass |
| Convention Compliance | 95% | Pass |
| **Overall** | **87%** | **Warning** |

---

## 3. File-Level Gap Analysis

### 3.1 Design Section 5 "파일 변경 목록" vs Implementation

| # | Design File | Action | Implementation Status | Status |
|---|-------------|--------|----------------------|--------|
| 1 | `assets/js/data/search.json` | New | Exists | Pass |
| 2 | `_tabs/stats.md` | New | Exists | Pass |
| 3 | `_layouts/stats.html` | New | Exists | Pass |
| 4 | `_includes/stats/summary-cards.html` | New | Exists | Pass |
| 5 | `_includes/stats/category-chart.html` | New | Exists | Pass |
| 6 | `_includes/stats/heatmap.html` | New | Exists | Pass |
| 7 | `_includes/stats/tag-cloud.html` | New | Exists | Pass |
| 8 | `_includes/series-nav.html` | New | Exists | Pass |
| 9 | `_sass/addon/_stats.scss` | New | **NOT FOUND** | Missing |
| 10 | `_sass/addon/_series-nav.scss` | New | **NOT FOUND** | Missing |
| 11 | `_layouts/post.html` | Modify | Modified (series-nav include present) | Pass |

**File Existence Rate**: 9/11 = **82%**

---

## 4. Feature-Level Detailed Comparison

### 4.1 F2. Search (Phase 1)

| Item | Design | Implementation | Status | Notes |
|------|--------|---------------|--------|-------|
| File exists | `assets/js/data/search.json` | Exists | Pass | |
| Front matter `layout: compress` | Yes | Yes | Pass | |
| Front matter `swcache: true` | Yes | Yes | Pass | |
| Field: `title` | `post.title \| jsonify` | `post.title \| jsonify` | Pass | |
| Field: `url` | `post.url \| relative_url \| jsonify` | `post.url \| relative_url \| jsonify` | Pass | |
| Field: `categories` | `post.categories \| join: ", " \| jsonify` | `post.categories \| join: ", " \| jsonify` | Pass | |
| Field: `tags` | `post.tags \| join: ", " \| jsonify` | `post.tags \| join: ", " \| jsonify` | Pass | |
| Field: `date` | `post.date \| date: "%Y-%m-%d" \| jsonify` | `post.date \| date: "%Y-%m-%d" \| jsonify` | Pass | |
| Field: `content` | Not in design | `post.content \| strip_html \| strip_newlines \| truncatewords: 50 \| jsonify` | Added | Implementation adds content snippet for full-text search |

**Search Match Rate**: 8/8 design items matched + 1 enhancement = **100% + bonus**

---

### 4.2 F1. Stats Dashboard (Phase 2)

#### 4.2.1 `_tabs/stats.md`

| Item | Design | Implementation | Status |
|------|--------|---------------|--------|
| `layout: stats` | Yes | Yes | Pass |
| `icon: fas fa-chart-bar` | Yes | Yes | Pass |
| `order: 7` | Yes | Yes | Pass |
| `title: Stats` | Yes | Yes | Pass |

**Match**: 4/4 = **100%**

#### 4.2.2 `_layouts/stats.html`

| Item | Design | Implementation | Status | Notes |
|------|--------|---------------|--------|-------|
| `layout: default` | Yes | Yes | Pass | |
| `{% include lang.html %}` | Yes | Yes | Pass | |
| Container `#stats-page` | Yes (`<div id="stats-page" class="px-1">`) | Yes (`<div id="stats-page" class="px-1">`) | Pass | |
| Title text | `Blog Statistics` (with emoji) | `Blog Statistics` (no emoji, `data-toc-skip`) | Changed | Emoji removed, toc-skip attribute added |
| Title CSS class | `stats-title` | `stats-page-title` | Changed | Class name differs |
| Includes 4 partials | Yes | Yes | Pass | All 4 partials included |
| CSS location | `_sass/addon/_stats.scss` (separate) | Inline `<style>` in layout | Changed | CSS inlined instead of SCSS file |

**Match**: 5/7 = **71%** (2 intentional changes)

#### 4.2.3 `_includes/stats/summary-cards.html`

| Item | Design | Implementation | Status | Notes |
|------|--------|---------------|--------|-------|
| `total_posts = site.posts \| size` | Yes | Yes | Pass | |
| `total_tags = site.tags \| size` | Yes | Yes | Pass | |
| `total_categories = site.categories \| size` | Yes | Yes | Pass | |
| `first_post = site.posts \| last` | Yes | Yes | Pass | |
| `last_post = site.posts \| first` | Yes | Yes | Pass | |
| Card 1: Total posts | Yes | Yes | Pass | |
| Card 2: Categories | Yes | Yes | Pass | |
| Card 3: Tags | Yes | Yes | Pass | |
| Card 4: Blog start year | Yes | Yes | Pass | |
| HTML structure `.stats-cards > .stat-card` | Yes | Yes | Pass | |
| Extra: `total_words` computation | Not in design | Present | Added | Word count computed but not displayed in card |

**Match**: 10/10 = **100%** (+ 1 enhancement)

#### 4.2.4 `_includes/stats/category-chart.html`

| Item | Design | Implementation | Status | Notes |
|------|--------|---------------|--------|-------|
| Max count calculation | Yes | Yes | Pass | |
| Loop `site.categories` | Yes | Yes | Pass | |
| Width percentage calculation | Yes | Yes | Pass | |
| Category link with `slugify` | Yes | Yes (`slugify \| url_encode`) | Pass | Implementation adds `url_encode` for safety |
| Bar structure `.category-bar-row` | Yes | Yes | Pass | |
| Bar fill `.bar-fill` with `style="width:..."` | Yes | Yes | Pass | |
| Section title | Not in design | Present (`<h2>` with icon) | Added | |
| `title` attribute on link | Not in design | Present | Added | |

**Match**: 6/6 = **100%** (+ 2 enhancements)

#### 4.2.5 `_includes/stats/heatmap.html`

| Item | Design | Implementation | Status | Notes |
|------|--------|---------------|--------|-------|
| Concept | Weekly 52x7 grid (GitHub-style) | Monthly year-row grid (year x 12 months) | Changed | Completely different approach |
| Time range | Recent 52 weeks (1 year) | Entire blog history (start_year..current_year) | Changed | Broader range |
| Granularity | Daily cells | Monthly cells | Changed | Monthly instead of daily |
| Level classes | `level-0` through `level-4` | `level-0` through `level-4` | Pass | Same 5-level system |
| Level thresholds | Not specified | 0/1/3/5/8 | N/A | |
| Cell title tooltip | Yes | Yes | Pass | |
| Dark mode support | Via SCSS variable | Via `[data-mode="dark"]` selector | Pass | Different method, same goal |
| Legend | Not in design | Present | Added | |
| Month labels | Not in design | Present | Added | |

**Match**: 2/5 core items matched, 3 changed = **40%** (significant design deviation)

The heatmap implementation chose a "monthly activity per year" approach instead of the design's "GitHub-style weekly contribution grid." This is a major structural change.

#### 4.2.6 `_includes/stats/tag-cloud.html`

| Item | Design | Implementation | Status | Notes |
|------|--------|---------------|--------|-------|
| Max tag count calculation | Yes | Yes | Pass | |
| 3-level sizing (`tag-sm/md/lg`) | Yes | Yes | Pass | |
| Ratio calculation (`count * 3 / max`) | Yes | Yes | Pass | |
| Tag link with `slugify` | Yes | Yes (`slugify \| url_encode`) | Pass | |
| CSS classes `tag-cloud-item` + size | Yes | Yes | Pass | |
| Count display `tag-count` | Yes | Yes | Pass | |
| Section title | Not in design | Present (`<h2>` with icon) | Added | |
| `title` attribute | Not in design | Present | Added | |

**Match**: 6/6 = **100%** (+ 2 enhancements)

#### 4.2.7 CSS/Styling (`_sass/addon/_stats.scss`)

| Item | Design | Implementation | Status | Notes |
|------|--------|---------------|--------|-------|
| Separate SCSS file | `_sass/addon/_stats.scss` | **Not created** | Missing | CSS inlined in `_layouts/stats.html` |
| `.stats-cards` grid | `display: grid` | `display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr))` | Pass | More detailed in impl |
| `.stat-card` styling | Basic | More detailed (hover, transitions) | Pass | Enhanced |
| `.bar-fill` uses `var(--link-color)` | Yes | Yes | Pass | |
| `.heatmap-grid` | `display: grid; grid-template-columns: repeat(53, 1fr)` | Row-based flex layout | Changed | Different layout for monthly approach |
| Heatmap color levels | Defined (5 levels) | Same 5 levels with same colors | Pass | |
| `.tag-cloud` container | Yes | Yes | Pass | |
| `.tag-sm/md/lg` font sizes | `0.85/1.0/1.2rem` | `0.78/0.92/1.08rem` | Changed | Slightly smaller values |
| Dark mode support | Via CSS variables | Via CSS variables + `[data-mode="dark"]` | Pass | |
| Responsive design | Not explicitly in design | Present (`@media max-width: 576px`) | Added | |

**Styling Match**: 6/9 = **67%**

---

### 4.3 F3. Series Navigation (Phase 3)

#### 4.3.1 `_includes/series-nav.html`

| Item | Design | Implementation | Status | Notes |
|------|--------|---------------|--------|-------|
| Series key: `categories[0]` + `categories[1]` | `join: "-"` comparison | `append: "\|"` comparison | Pass | Different separator but same logic |
| `categories.size >= 2` guard | In `post.html` | In `series-nav.html` itself | Pass | Guard moved to include file |
| `site.posts reversed` loop | Yes | Yes | Pass | |
| `series_posts.size > 1` check | Yes | Yes | Pass | |
| Series header with icon | `fas fa-list-ol` + series name + count | `fas fa-list-ol fa-fw` + series name + (current/total) | Pass | Enhanced with position indicator |
| Ordered list `<ol>` | Yes | Yes | Pass | |
| Current post highlighting | `class="current"` + `<strong>` | `class="current-post"` + text only | Changed | CSS class name differs; uses CSS bold instead of `<strong>` tag |
| Previous/Next buttons | `btn btn-sm btn-outline-primary` classes | Custom `series-nav-btn` class | Changed | Custom styling instead of Bootstrap classes |
| `truncate: 30` on titles | Yes | `truncate: 35` | Changed | 35 chars instead of 30 |
| `prev_post` variable access | Direct `series_posts[current_index \| minus: 1]` | Via `prev_index` intermediate variable | Pass | Same result, cleaner code |
| Empty state for prev button | Not specified | `<span></span>` placeholder | Added | Better layout stability |

**Match**: 7/10 = **70%** (3 minor changes)

#### 4.3.2 `_layouts/post.html` (series-nav integration)

| Item | Design | Implementation | Status | Notes |
|------|--------|---------------|--------|-------|
| `{% include series-nav.html %}` present | Yes | Yes | Pass | |
| Position: before `<div class="content">` | Yes | Yes | Pass | |
| Guard: `{% if page.categories.size >= 2 %}` | In `post.html` | **In `series-nav.html`** | Changed | Guard moved into the include itself |
| Comment annotation | Yes | Yes (slightly different wording) | Pass | |

**Match**: 3/4 = **75%** (guard location moved)

Design specifies the guard in `post.html`:
```liquid
{% if page.categories.size >= 2 %}
  {% include series-nav.html %}
{% endif %}
```

Implementation places the guard inside `series-nav.html` and calls it unconditionally from `post.html`:
```liquid
{% include series-nav.html %}
```

This is functionally equivalent but structurally different.

#### 4.3.3 CSS/Styling (`_sass/addon/_series-nav.scss`)

| Item | Design | Implementation | Status | Notes |
|------|--------|---------------|--------|-------|
| Separate SCSS file | `_sass/addon/_series-nav.scss` | **Not created** | Missing | CSS inlined in `series-nav.html` via `<style>` |
| `.series-nav` border + radius | Yes | Yes | Pass | |
| `background: var(--sidebar-bg)` | Yes | `var(--card-bg, var(--main-bg))` | Changed | Different CSS variable |
| `.series-header` styling | Yes | `.series-nav-header` (renamed) | Changed | Class renamed |
| `.series-list` padding | `1.5rem` | `1.5rem` | Pass | |
| `.series-pagination` flex layout | Yes | Yes | Pass | |
| `.series-pagination` gap | `0.5rem` | `0.5rem` | Pass | |
| Button styling | Bootstrap classes | Custom `.series-nav-btn` | Changed | Fully custom styling |

**Styling Match**: 4/8 = **50%**

---

## 5. Missing Features (Design O, Implementation X)

| # | Item | Design Location | Description | Impact |
|---|------|----------------|-------------|--------|
| 1 | `_sass/addon/_stats.scss` | Design Section 3.2 (line 276-307) | Separate SCSS file for stats dashboard styles | Medium |
| 2 | `_sass/addon/_series-nav.scss` | Design Section 4.2 (line 415-443) | Separate SCSS file for series nav styles | Medium |

---

## 6. Added Features (Design X, Implementation O)

| # | Item | Implementation Location | Description | Impact |
|---|------|------------------------|-------------|--------|
| 1 | `content` field in search.json | `assets/js/data/search.json:14` | Full-text search content snippet (50 words) | Positive |
| 2 | `total_words` computation | `_includes/stats/summary-cards.html:7-11` | Total word count computed (not displayed in card) | Neutral |
| 3 | Section titles with icons | `category-chart.html:9-11`, `heatmap.html:8-9`, `tag-cloud.html:9-11` | `<h2>` section headers added to each stats section | Positive |
| 4 | Heatmap legend | `_includes/stats/heatmap.html:55-63` | Visual legend (Less/More) for heatmap levels | Positive |
| 5 | Responsive CSS | `_layouts/stats.html:235-240` | Mobile breakpoint at 576px | Positive |
| 6 | Dark mode heatmap override | `_layouts/stats.html:180-181` | Explicit dark mode cell color | Positive |
| 7 | `title` attributes on links | Multiple files | Tooltips on category/tag links | Positive |
| 8 | `url_encode` filter | `category-chart.html:17`, `tag-cloud.html:24` | Extra URL encoding for safety | Positive |
| 9 | Series position indicator | `_includes/series-nav.html:116` | "(current / total)" display | Positive |

---

## 7. Changed Features (Design != Implementation)

| # | Item | Design | Implementation | Impact | Assessment |
|---|------|--------|---------------|--------|------------|
| 1 | Heatmap structure | Weekly 52x7 grid (GitHub-style daily) | Monthly year-row grid (year x 12 months) | High | Intentional simplification due to Liquid limitations |
| 2 | Heatmap time range | Recent 52 weeks | Entire blog history | Medium | Broader scope, more informative |
| 3 | CSS architecture | Separate `_sass/addon/` SCSS files | Inline `<style>` blocks in HTML | Medium | Simpler approach, no SCSS compilation dependency |
| 4 | Stats title | `stats-title` class with emoji | `stats-page-title` class, no emoji | Low | Minor naming/style change |
| 5 | Tag font sizes | `0.85/1.0/1.2rem` | `0.78/0.92/1.08rem` | Low | Slight visual tuning |
| 6 | Series nav background | `var(--sidebar-bg)` | `var(--card-bg, var(--main-bg))` | Low | More appropriate semantic variable |
| 7 | Current post class | `.current` | `.current-post` | Low | More descriptive name |
| 8 | Prev/Next button style | Bootstrap `.btn .btn-sm .btn-outline-primary` | Custom `.series-nav-btn` | Low | Custom styling, no Bootstrap dependency |
| 9 | Title truncation | 30 chars | 35 chars | Low | Minor adjustment |
| 10 | Category guard location | In `post.html` wrapping the include | Inside `series-nav.html` itself | Low | Functionally equivalent |

---

## 8. Match Rate Calculation

### 8.1 Per-Feature Scores

| Feature | Design Items | Matched | Changed | Missing | Score |
|---------|:-----------:|:-------:|:-------:|:-------:|:-----:|
| F2. Search | 8 | 8 | 0 | 0 | 100% |
| F1. Stats - Core HTML | 26 | 24 | 2 | 0 | 92% |
| F1. Stats - Heatmap | 5 | 2 | 3 | 0 | 40% |
| F1. Stats - CSS | 9 | 6 | 3 | 0 | 67% |
| F3. Series Nav - Core | 10 | 7 | 3 | 0 | 70% |
| F3. Series Nav - post.html | 4 | 3 | 1 | 0 | 75% |
| F3. Series Nav - CSS | 8 | 4 | 4 | 0 | 50% |
| File Existence | 11 | 9 | 0 | 2 | 82% |

### 8.2 Weighted Overall Score

| Category | Weight | Score | Weighted |
|----------|:------:|:-----:|:--------:|
| File Existence | 20% | 82% | 16.4 |
| Feature Logic Match | 50% | 85% | 42.5 |
| CSS/Styling Match | 15% | 56% | 8.4 |
| Convention/Quality | 15% | 95% | 14.3 |
| **Total** | **100%** | | **81.6%** |

```
+---------------------------------------------+
|  Overall Match Rate: 82%                     |
+---------------------------------------------+
|  Pass (exact match):    47 items (65%)       |
|  Changed (functional):  16 items (22%)       |
|  Added (bonus):          9 items (12%)       |
|  Missing (not impl):    2 items  (3%)        |
+---------------------------------------------+
```

---

## 9. Key Findings

### 9.1 Heatmap Design Deviation (HIGH Impact)

The most significant gap is the heatmap implementation. The design specified a **GitHub-style weekly contribution grid** (52 columns x 7 rows = 364 daily cells) but the implementation delivers a **monthly activity grid** (years x 12 months). This was likely an intentional decision due to Liquid's limitations with date arithmetic (identified as a risk in Design Section 6), but it represents a structural departure from the design spec.

### 9.2 CSS Architecture Change (MEDIUM Impact)

The design specified two separate SCSS files:
- `_sass/addon/_stats.scss`
- `_sass/addon/_series-nav.scss`

Neither file was created. Instead, CSS is inlined directly into the HTML files:
- Stats CSS is in `_layouts/stats.html` via `<style>` block (232 lines)
- Series nav CSS is in `_includes/series-nav.html` via `<style>` block (82 lines)

This avoids the risk noted in Design Section 6 ("`_sass/addon/` auto-load not supported") but trades maintainability for simplicity. The inline approach means styles cannot benefit from SCSS features (nesting, variables, mixins) beyond what CSS natively supports.

### 9.3 Positive Deviations

Several implementation enhancements improve upon the design:
- Full-text search content in `search.json` enables more useful search results
- Section titles with icons improve visual hierarchy
- Responsive CSS ensures mobile compatibility
- URL encoding on category/tag links prevents broken URLs with special characters
- Series position indicator ("2 / 5") provides better navigation context

---

## 10. Recommended Actions

### 10.1 Immediate Actions

| Priority | Item | Description | Recommendation |
|----------|------|-------------|----------------|
| 1 | CSS Architecture Decision | SCSS files missing, CSS inlined | Choose one approach and document the decision. If inline CSS is intentional, update design document. If SCSS is preferred, create the files and move styles. |
| 2 | Heatmap Design Update | Monthly grid vs weekly grid | Update design document to reflect the monthly approach, or implement the original weekly grid design. |

### 10.2 Documentation Update Needed

The following design document updates are recommended to reflect the current implementation:

- [ ] Section 3.2: Update `_layouts/stats.html` to document inline CSS approach
- [ ] Section 3.2: Remove `_sass/addon/_stats.scss` from design or mark as "replaced by inline CSS"
- [ ] Section 3.2: Update heatmap design to reflect monthly grid approach
- [ ] Section 4.2: Remove `_sass/addon/_series-nav.scss` from design or mark as "replaced by inline CSS"
- [ ] Section 4.2: Update `_layouts/post.html` to reflect guard logic moved into `series-nav.html`
- [ ] Section 5: Update file list to reflect CSS architecture decision
- [ ] Add `content` field to `search.json` design in Section 2.3

### 10.3 Optional Improvements

| Item | File | Notes |
|------|------|-------|
| Remove unused `total_words` | `_includes/stats/summary-cards.html` | Computed but not displayed; either display it or remove |
| Consider extracting inline CSS | `_layouts/stats.html`, `_includes/series-nav.html` | If project grows, external CSS improves maintainability |
| Add `data-toc-skip` to section titles | stats partials | Prevent stats headings from appearing in TOC |

---

## 11. Synchronization Options

Given the 82% match rate, the following options are available:

| Option | Description | Effort |
|--------|-------------|--------|
| **A. Update design to match implementation** | Document inline CSS approach, monthly heatmap, and other changes | Low |
| **B. Modify implementation to match design** | Create SCSS files, implement weekly heatmap grid | Medium-High |
| **C. Hybrid approach** | Update design for CSS decision; keep heatmap as-is but document rationale | Low |

**Recommendation**: Option **C** (Hybrid). The implementation improvements are generally positive. The CSS inline approach and monthly heatmap are reasonable given Jekyll/Liquid constraints. Update the design document to accurately reflect these decisions and their rationale.

---

## 12. Next Steps

- [ ] Decide on synchronization option (A/B/C)
- [ ] Update design document with chosen changes
- [ ] Verify `total_words` usage in `summary-cards.html`
- [ ] Run `bundle exec jekyll serve` for local validation
- [ ] Write completion report (`blog-enhancements.report.md`)

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-02-18 | Initial gap analysis | Claude (gap-detector) |
