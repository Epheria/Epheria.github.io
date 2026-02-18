# AGENTS.md

This file provides guidance to coding agents when working in this repository.

## Project Overview

Game Programmer "Sehyup"의 기술 블로그 저장소다. Jekyll 기반 정적 사이트이며 `jekyll-theme-chirpy v6.1` 테마를 사용한다.

- URL: `https://Epheria.github.io`
- Language: Korean (`lang: ko`)
- Comments: utterances (GitHub Issues)
- Analytics: Google Analytics (`G-3GL54C48GF`)

## Build & Development

- Install dependencies:
  - `bundle install`
- Local dev server (`http://localhost:4000`):
  - `bundle exec jekyll serve`
- Production build:
  - `JEKYLL_ENV=production bundle exec jekyll build`
- HTML validation:
  - `bundle exec htmlproofer _site --disable-external --check-html --allow_hash_href`

Requirements:
- Ruby `3.2`
- Do not commit `Gemfile.lock` (ignored by this repo).

## Deployment

Push to `main` triggers automatic build/deploy through `.github/workflows/pages-deploy.yml` to GitHub Pages.

## Post Conventions

### Path & naming
- Path: `_posts/{Category}/{Subcategory}/YYYY-MM-DD-slug.md`
- Category directories:
  - `Common`, `Csharp`, `ETC`, `Language`, `ML`, `Mathematics`, `Python`, `Survivor`, `TheQuesting`, `Toyverse`, `Unity`, `Unreal`

### Required front matter
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

Optional front matter:
- `math: true` or `use_math: true` for equations
- `mermaid: true` for diagrams

Typical post body start:
```markdown
[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)
```

Images:
- Store post images under `assets/img/post/{category}/`

## Architecture Notes

Customized theme overrides:
- `_layouts/post.html`: custom dialog-based TOC UI
- `_includes/sidebar.html`: sidebar layout customization
- `_includes/toc-status.html`: TOC enable/disable logic
- `_plugins/posts-lastmod-hook.rb`: auto-set `last_modified_at` from git log

Sidebar tabs are defined in `_tabs/` and ordered by `order` value (`about`, `archives`, `categories`, `tags`, `books`, `sideproject`).

Static assets:
- `assets/lib/`: `chirpy-static-assets` git submodule
- `assets/js/dist/`: generated at build time and gitignored

## Style

Follow `.editorconfig`:
- UTF-8
- 2-space indentation
- LF line endings
- Keep trailing whitespace in Markdown files
