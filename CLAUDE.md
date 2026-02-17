# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Game Programmer "Sehyup"의 기술 블로그. Jekyll 기반 정적 사이트로, **jekyll-theme-chirpy v6.1** 테마를 사용한다. GitHub Pages로 배포되며, 한국어(`lang: ko`)로 운영된다.

- URL: https://Epheria.github.io
- 댓글 시스템: utterances (GitHub Issues 기반)
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
- 카테고리 디렉토리: Common, Csharp, ETC, Language, ML, Mathematics, Python, Survivor, TheQuesting, Toyverse, Unity, Unreal

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

### 본문 시작 패턴
대부분의 포스트는 front matter 직후 방문자 카운터 뱃지로 시작:
```markdown
[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)
```

### 이미지
포스트 이미지는 `assets/img/post/{category}/` 하위에 저장한다.

## Architecture

### 커스터마이징된 파일들 (테마 오버라이드)
- `_layouts/post.html` — TOC 팝업 UI가 추가된 커스텀 포스트 레이아웃 (dialog 기반 TOC)
- `_includes/sidebar.html` — 사이드바 레이아웃
- `_includes/toc-status.html` — TOC 활성화 여부를 결정하는 로직
- `_plugins/posts-lastmod-hook.rb` — git log 기반으로 `last_modified_at`을 자동 설정하는 Jekyll 훅

### 탭 (사이드바 네비게이션)
`_tabs/` 디렉토리에 정의. `order` 값으로 정렬:
- about, archives, categories, tags, books, sideproject

### 정적 자산
- `assets/lib/` — chirpy-static-assets git submodule
- `assets/js/dist/` — gitignore됨 (빌드 시 생성)

### 코드 스타일
`.editorconfig` 기준: UTF-8, 들여쓰기 2칸 스페이스, LF 줄바꿈. Markdown 파일은 trailing whitespace를 유지한다.
