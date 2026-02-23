# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Game Programmer "Sehyup"의 기술 블로그. Jekyll 기반 정적 사이트로, **jekyll-theme-chirpy v6.1** 테마를 사용한다. GitHub Pages로 배포되며, **jekyll-polyglot**으로 다국어 지원 (ko/en/ja).

- URL: https://Epheria.github.io
- 기본 언어: 한국어 (`ko`), 지원 언어: 영어 (`en`), 일본어 (`ja`)
- 댓글 시스템: Giscus (GitHub Discussions 기반)
- 분석: Google Analytics (G-3GL54C48GF)

## Build & Development Commands

```bash
# 의존성 설치
bundle install

# 로컬 개발 서버 실행 (http://localhost:4000)
bundle exec jekyll serve

# 프로덕션 빌드
JEKYLL_ENV=production bundle exec jekyll build

# HTML 검증 (CI에서 실행됨)
bundle exec htmlproofer _site --disable-external --check-html --allow_hash_href
```

Ruby 3.2 필요. `Gemfile.lock`은 `.gitignore`에 포함되어 있으므로 커밋하지 않는다.

## Deployment

`main` 브랜치에 push하면 `.github/workflows/pages-deploy.yml`을 통해 자동 빌드 및 GitHub Pages 배포된다.

## Post Conventions

### 파일 위치 및 네이밍
- 경로: `_posts/{Category}/{Subcategory}/YYYY-MM-DD-slug.md`
- 번역 파일: `YYYY-MM-DD-slug.en.md`, `YYYY-MM-DD-slug.ja.md` (같은 디렉토리)
- 카테고리 디렉토리: AI, Common, Csharp, ETC, Investment, Language, ML, Mathematics, Pobos, Python, Survivor, TheQuesting, Toyverse, Unity, Unreal

### Front Matter 필수 형식
```yaml
---
title: 포스트 제목
date: YYYY-MM-DD HH:MM:SS +/-TTTT
categories: [상위카테고리, 하위카테고리]
tags: [tag1, tag2, tag3]
toc: true
toc_sticky: true
---
```

선택적 front matter:
- `math: true` / `use_math: true` — 수학 수식(MathJax/KaTeX) 사용 시
- `mermaid: true` — Mermaid 다이어그램 사용 시
- `difficulty: beginner | intermediate | advanced` — 난이도 배지 (초급/중급/고급)
- `prerequisites: ["/posts/slug/", "/posts/slug2/"]` — 선수지식 포스트 링크 목록
- `tldr: ["핵심 요약 1", "핵심 요약 2"]` — 포스트 상단 TL;DR 요약 박스

### 본문 시작 패턴
대부분의 포스트는 front matter 직후 방문자 카운터 뱃지로 시작:
```markdown
[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)
```

### 이미지
포스트 이미지는 `assets/img/post/{category}/` 하위에 저장한다.

## Architecture

### 커스터마이징된 파일들 (테마 오버라이드)
- `_layouts/post.html` — TOC 팝업 UI + 추가 기능들이 삽입된 커스텀 포스트 레이아웃
- `_layouts/stats.html` — 블로그 통계 대시보드 페이지 레이아웃
- `_includes/sidebar.html` — 사이드바 레이아웃 (인기 포스트 위젯 포함)
- `_includes/toc-status.html` — TOC 활성화 여부를 결정하는 로직
- `_plugins/posts-lastmod-hook.rb` — git log 기반으로 `last_modified_at`을 자동 설정하는 Jekyll 훅

### 탭 (사이드바 네비게이션)
`_tabs/` 디렉토리에 정의. `order` 값으로 정렬:
- about, archives, categories, tags, books, sideproject, **stats** (order: 7)

### 정적 자산
- `assets/lib/` — chirpy-static-assets git submodule
- `assets/js/dist/` — gitignore됨 (빌드 시 생성)

### 코드 스타일
`.editorconfig` 기준: UTF-8, 들여쓰기 2칸 스페이스, LF 줄바꿈. Markdown 파일은 trailing whitespace를 유지한다.

## 추가 기능 (블로그 강화)

### 포스트 내 UI 컴포넌트 (post.html에 자동 삽입 순서)
1. `post-difficulty.html` — 헤더 영역에 난이도 배지 표시 (front matter: `difficulty`)
2. `post-prerequisites.html` — 선수지식 링크 목록 (front matter: `prerequisites`)
3. `series-nav.html` — 시리즈 네비게이션 (자동 감지, 별도 설정 불필요)
4. `tldr.html` — TL;DR 요약 박스 (front matter: `tldr`)
5. `hits-counter.html` — 방문자 카운터 (항상 표시)

### 시리즈 네비게이션 (`_includes/series-nav.html`)
- **자동 활성화**: `categories`가 2개 이상인 포스트에서 자동으로 표시
- 같은 `categories[0] + categories[1]` 조합을 공유하는 포스트들이 하나의 시리즈
- 별도 front matter 설정 없이 카테고리만 맞추면 이전/다음 링크 자동 생성
- 예시: `categories: [Unity, build]` 인 포스트들이 "build 시리즈"로 묶임

### 통계 대시보드 (`_tabs/stats.md`, `_layouts/stats.html`)
- URL: `/stats/`
- `_includes/stats/` 하위 컴포넌트:
  - `summary-cards.html` — 전체 포스트 수, 카테고리 수, 태그 수
  - `category-chart.html` — 카테고리별 포스트 수 막대 차트
  - `heatmap.html` — 포스트 작성 히트맵
  - `tag-cloud.html` — 태그 클라우드

### 인기 포스트 위젯 (`_includes/popular-posts.html`)
- 사이드바에 표시됨
- 데이터 소스: `_data/popular-posts.yml`
- GitHub Actions: `.github/workflows/update-popular-posts.yml` (자동 업데이트)
- 수동 스크립트: `scripts/fetch_popular_posts.py`

### 데이터 파일
- `_data/popular-posts.yml` — 인기 포스트 순위 목록
- `_data/recommended-posts.yml` — 카테고리별 추천 포스트 (수동 관리)

### SCSS 추가 파일 (`_sass/addon/`)
모두 `assets/css/jekyll-theme-chirpy.scss`에서 import됨:
- `_series-nav.scss` — 시리즈 네비게이션 스타일
- `_stats.scss` — 통계 대시보드 스타일
- `_popular-posts.scss` — 인기 포스트 위젯 스타일
- `_post-meta.scss` — 난이도 배지 / 선수지식 스타일
- `_chart.scss` — 차트 컴포넌트 스타일
- `_code-compare.scss` — 코드 비교 레이아웃 스타일
- `_tldr.scss` — TL;DR 박스 스타일

### 포스팅 시 활용 예시
```yaml
---
title: Unity Addressable 심화
date: 2026-02-18 10:00:00 +0900
categories: [Unity, addressable]
tags: [unity, addressable, memory]
toc: true
toc_sticky: true
difficulty: intermediate
prerequisites:
  - /posts/UnityAddressable/
  - /posts/UnityAddressable2/
tldr:
  - Addressable 커스텀 분석기를 구현하면 빌드 전 리소스 의존성을 검사할 수 있다
  - IAssetBundleAnalyzeRule 인터페이스를 상속해 규칙을 정의한다
---
```
- `categories[1]`이 같은 포스트가 여러 개면 시리즈 네비게이션이 자동으로 표시됨
- `difficulty`는 초급(`beginner`)/중급(`intermediate`)/고급(`advanced`) 중 하나
- `prerequisites`에는 포스트 URL 경로(`/posts/{slug}/` 형식)를 사용

## 포스트 현황 (2026-02-24 기준)

### 카테고리별 포스트 수

| 카테고리 | 포스트 수 | 하위 카테고리 |
|----------|----------|--------------|
| Unity | 70 | addressable, animator, build, buildError, cinemachine, googleSheets, light, localization, naninovel, Netcode, optimization, Plugins, RenderTexture, Shader |
| Unreal | 32 | Cpp, Mac, Study |
| ETC | 18 | — |
| Common | 15 | — |
| Language | 12 | Japanese |
| Python | 10 | Linear Algebra, numpy, Python Language |
| ML | 8 | — |
| Csharp | 7 | DataStructure, UniRx |
| AI | 5 | Claude, LLM |
| Toyverse | 4 | — |
| TheQuesting | 3 | — |
| Mathematics | 2 | Linear Algebra, Mathematical Thinking, Set Theory |
| Survivor | 1 | — |
| **합계** | **187** | |

빈 카테고리 (예정): Investment, Pobos

### 다국어 번역 진척도

jekyll-polyglot 플러그인으로 다국어 지원. 지원 언어: `ko`(기본), `en`, `ja`.

- **전체 기본 포스트 (ko)**: 147개
- **영어 번역 (`.en.md`)**: 37개 (25.2%)
- **일본어 번역 (`.ja.md`)**: 37개 (25.2%)
- **중국어 번역**: 없음

#### 카테고리별 번역 현황

| 카테고리 | 기본(ko) | EN | JA | 번역률 |
|----------|---------|-----|-----|--------|
| Unity | 70 | 16 | 16 | 22.9% |
| Unreal | 32 | 7 | 7 | 21.9% |
| ETC | 18 | 5 | 5 | 27.8% |
| Common | 15 | 5 | 5 | 33.3% |
| Csharp | 7 | 2 | 2 | 28.6% |
| AI | 5 | 0 | 0 | 0% |
| Toyverse | 4 | 1 | 1 | 25.0% |
| TheQuesting | 3 | 1 | 1 | 33.3% |
| Language | 12 | 0 | 0 | 0% |
| Python | 10 | 0 | 0 | 0% |
| ML | 8 | 0 | 0 | 0% |
| Mathematics | 2 | 0 | 0 | 0% |
| Survivor | 1 | 0 | 0 | 0% |
| **합계** | **187** | **37** | **37** | **25.2%** |

미번역 카테고리: AI, Language, Python, ML, Mathematics, Survivor
