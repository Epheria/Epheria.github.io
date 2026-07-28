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
- **번역 파일 필수**: front matter에 반드시 `lang: en` 또는 `lang: ja`를 명시해야 한다. 누락하면 polyglot이 번역본으로 인식하지 못하고 ko 사이트에 별도 포스트로 생성된다.
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

번역 파일(`.en.md`, `.ja.md`)의 Front Matter에는 `lang` 필드 필수:
```yaml
---
title: Post Title in English
lang: en          # 필수! en 또는 ja. 누락 시 ko 사이트에 별도 포스트로 노출됨
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

### 수식 작성 규칙 (MathJax)
- `\text{}` 블록 안에서 언더스코어(`_`)를 쓸 때 `\_`로 이스케이프하면 `\_`가 그대로 렌더링된다. 공백으로 대체하거나 별도 `\text` 블록으로 분리할 것.
  - Bad: `\text{base\_address}` → 렌더링 시 `base\_address`로 보임
  - Good: `\text{base address}` 또는 `\text{base}\_\text{address}`

### 본문 시작 패턴
대부분의 포스트는 front matter 직후 방문자 카운터 뱃지로 시작:
```markdown
[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)
```

### LLM 글쓰기 안티패턴 체크리스트

포스트 초안 작성 후 다음 항목을 점검한다. LLM 도움을 받은 글에서 반복적으로 발견된 패턴이며, 그대로 두면 매끄럽지만 알맹이가 없는 글이 된다. (감사 근거: Tailscale 시리즈, Survivor 포트폴리오, UnityCLIArchitecture)

1. **불릿 묶음 뒤 종합 문단 부재**
   - 3개 이상 항목을 나열했으면 그 뒤에 "왜 이 조합인지", "이 중 결정적인 항목은", "빠지면 무너지는 의존성은" 중 하나를 문단으로 잇는다.
   - 단순 나열로 섹션을 끝내지 않는다.

2. **정보 진전 정체 (같은 말 반복)**
   - 한 주장이 다른 표현으로 두 번 등장하면 한 번으로 통합한다.
   - 각 문장은 직전 문장에 없던 사실·수치·근거를 더해야 한다.

3. **표·다이어그램 뒤 공허한 일반 요약**
   - "이 모든 것이 자동으로 조합되어 동작합니다" 식 마무리 금지.
   - 시각 자료 뒤에는 (a) 가장 결정적인 항목, (b) 빠지면 무너지는 의존성, (c) 흔한 오해 중 최소 하나를 짚는다.

4. **모호한 지시대명사**
   - "이/그/이러한"의 지시 대상이 같은 문단 안에 있어야 한다.
   - 두 문장 이상 떨어지면 명사로 다시 호명한다 (예: "이런 케이스" → "양쪽 다 EDM인 케이스").

5. **입장 약화 (중립 회피)**
   - "~할 수 있다", "~인 경향이 있다"로 도망치지 않는다. 측정값·경험 근거가 있으면 단정한다.
   - 1인칭 경험과 동기("후쿠오카에서 측정해보니", "본가에서 운영 중")를 의도적으로 남긴다. 이게 사라지면 LLM 균질화의 핵심 증상이다.

6. **카드·항목의 단조로운 리듬**
   - 모든 항목 설명을 같은 길이로 맞추지 않는다. 중요도 차이가 문장 길이에 드러나야 한다.
   - 핵심 항목은 길게, 보조 항목은 짧게.

기존 문체 가이드 (계속 유지):
- 합니다체 일관성, 드라마틱·과장 표현 금지 ("이건 SF가 아니다" 같은 교묘하게 오글거리는 표현 회피)
- 비유는 도입부·섹션 제목에 가볍게만. 본문은 팩트+수치 중심
- 외부 코드(ftol-client 등) 참조 시 의사코드로 추상화

위 6가지 점검을 자동화한 `/post-review` 스킬이 있다. 발행 전 초안에 적용하면 라인 번호와 함께 안티패턴을 보고한다 (자동 수정은 하지 않는다).

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

### 커스텀 시각화 (`/diagram` 스킬)

포스트에 시각화가 필요하면 `/diagram` 스킬을 사용한다. 미리 만든 템플릿 없이 매번 맥락에 맞는 **맞춤형 인라인 HTML/CSS/SVG/JS를 직접 생성**한다.

- **생성 가능**: 파이프라인, 의사결정 트리, 비교 레이아웃, 아키텍처 레이어, 컴포넌트 관계도, 데이터 흐름 DAG, Chart.js 차트 등
- **Mermaid 대비 장점**: 곡선 화살표, 그라디언트, 애니메이션, 정밀 좌표 제어, 완벽한 다크모드/반응형
- **Chart.js 사용 시**: `chart: true` front matter 필요, 기존 `window.chartConfigs` + `chart-init.html` 패턴 활용
- **필수 규칙**: 인라인 JS에 `//` 주석 금지 (`/* */`만), `[data-mode="dark"]` 다크모드, 768px 반응형
- **다국어**: ko/en/ja 각 파일에 해당 언어 텍스트로 인라인 코드를 생성

### SCSS 추가 파일 (`_sass/addon/`)
모두 `assets/css/jekyll-theme-chirpy.scss`에서 import됨:
- `_series-nav.scss` — 시리즈 네비게이션 스타일
- `_stats.scss` — 통계 대시보드 스타일
- `_popular-posts.scss` — 인기 포스트 위젯 스타일
- `_post-meta.scss` — 난이도 배지 / 선수지식 스타일
- `_chart.scss` — 차트 컴포넌트 스타일
- `_diagrams.scss` — HTML 다이어그램 스타일 (pipeline, decision-tree, comparison)
- `_svg-diagrams.scss` — SVG 아키텍처 다이어그램 스타일
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

## 포스트 현황 (2026-07-28 기준)

수치는 `_posts/` 실측값이다. 파일명 날짜 접두사가 있는 `.md`만 집계하며, 월·일이 0으로 패딩되지 않은 파일(`2024-6-12-...`)도 포함한다.

### 카테고리별 포스트 수 (ko 원본)

| 카테고리 | ko | 하위 카테고리 |
|----------|----|--------------|
| Unity | 42 | JobSystem, Netcode, Plugins, RenderTexture, Shader, addressable, animator, build, buildError, cinemachine, googleSheets, light, localization, optimization |
| Mathematics | 36 | Linear Algebra (33, Chapter1~6 중첩), Mathematical Thinking (2), Set Theory (1) |
| AI | 21 | Claude, Gemini, LLM, Swift |
| CS | 12 | — |
| ETC | 12 | Tailscale |
| Language | 12 | Japanese |
| Csharp | 10 | DataStructure, Thread, UniRx, foundation, internals, memory |
| Unreal | 10 | Cpp, Mac, Study |
| Python | 9 | numpy |
| ML | 7 | — |
| Common | 5 | — |
| ProjectAliveRevive | 2 | FlowField |
| Survivor | 2 | — |
| Toyverse | 2 | — |
| TheQuesting | 1 | — |
| **합계** | **183** | |

`Mathematics`는 `Linear Algebra` 아래에 `Chapter1`~`Chapter6`이 한 단계 더 중첩되어 있어, 3단 디렉토리 구조를 갖는 유일한 카테고리다.

### 다국어 번역 진척도

jekyll-polyglot으로 다국어 지원. 지원 언어: `ko`(기본), `en`, `ja`. 중국어는 없다.

- **ko 원본**: 183개
- **번역 완료 (ko 기준)**: 119개 (65.0%) — en/ja가 항상 쌍으로 존재
- **`.en.md` 파일**: 121개 / **`.ja.md` 파일**: 121개 (각각 고아 번역본 2개 포함)

| 카테고리 | ko | EN | JA | 번역률 |
|----------|----|----|----|--------|
| Unity | 42 | 38 | 38 | 90.5% |
| Mathematics | 36 | 2 | 2 | 5.6% |
| AI | 21 | 21 | 21 | 100% |
| CS | 12 | 12 | 12 | 100% |
| ETC | 12 | 11 | 11 | 91.7% |
| Language | 12 | 0 | 0 | 0% |
| Csharp | 10 | 10 | 10 | 100% |
| Unreal | 10 | 12 | 12 | 100% (고아 2개 별도) |
| Python | 9 | 6 | 6 | 66.7% |
| ML | 7 | 0 | 0 | 0% |
| Common | 5 | 5 | 5 | 100% |
| ProjectAliveRevive | 2 | 2 | 2 | 100% |
| Survivor | 2 | 0 | 0 | 0% |
| Toyverse | 2 | 1 | 1 | 50% |
| TheQuesting | 1 | 1 | 1 | 100% |
| **합계** | **183** | **121** | **121** | **65.0%** |

미번역 카테고리: Language, ML, Survivor. 번역 잔여량이 가장 많은 곳은 `Mathematics`(34편 미번역)이고, 그다음이 `Unity`(4편)다.

### 정리가 필요한 항목

- **고아 번역본 4개**: `_posts/Unreal/Cpp/2026-02-20-CppForUnreal06`, `07`의 `.en.md`/`.ja.md`가 ko 원본 없이 존재한다. 현재 en/ja 사이트에만 노출된다
- **빈 디렉토리**: `_posts/en/`, `_posts/ja/` (내용 없음, 삭제 대상)
- **비포스트 파일**: `_posts/Unity/optimization/메모용.md` (날짜 접두사 없어 Jekyll이 포스트로 처리하지 않음)
- **미커밋 초안 2개**: `_posts/ETC/2026-04-08-UnityCLIArchitecture.md`, `_posts/Survivor/2026-04-07-SurvivorPortfolio.md` (위 집계에 포함됨)
