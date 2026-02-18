# Sehyup's Technical Blog (Epheria.github.io)

This repository contains the source code for Sehyup's technical blog, a Game Programmer focusing on development challenges, technical summaries, and portfolios. The site is built using **Jekyll** with the **Chirpy** theme (v6.1).

## Project Overview

- **Owner:** Sehyup (Game Programmer)
- **URL:** [https://Epheria.github.io](https://Epheria.github.io)
- **Tech Stack:** Jekyll, Ruby 3.2, HTML/SASS/JavaScript
- **Theme:** [jekyll-theme-chirpy](https://github.com/cotes2020/jekyll-theme-chirpy)
- **Language:** Korean (`lang: ko`)
- **Comments:** Utterances (GitHub Issues based)
- **Analytics:** Google Analytics (G-3GL54C48GF)

## Building and Running

### Prerequisites
- **Ruby:** 3.2 (managed via `Gemfile`)
- **Bundler:** `gem install bundler`
- **Python:** 3.x (for OG image generation)

### Commands
- **Install Dependencies:**
  ```bash
  bundle install
  ```
- **Local Development Server:**
  ```bash
  bundle exec jekyll serve
  ```
  The site will be available at `http://localhost:4000`.
- **Production Build:**
  ```bash
  JEKYLL_ENV=production bundle exec jekyll build
  ```
- **HTML Proofing (Validation):**
  ```bash
  bundle exec htmlproofer _site --disable-external --check-html --allow_hash_href
  ```
- **Generate Category OG Images:**
  ```bash
  python3 scripts/generate_og_images.py
  ```

## Development Conventions

### Post Structure
Posts are organized by category and subcategory directories:
- **Path:** `_posts/{Category}/{Subcategory}/YYYY-MM-DD-slug.md`
- **Existing Categories:** `Common`, `Csharp`, `ETC`, `Language`, `Mathematics`, `ML`, `Python`, `Survivor`, `TheQuesting`, `Toyverse`, `Unity`, `Unreal`.

### Front Matter Requirements
Every post should include the following front matter:
```yaml
---
title: Post Title
date: YYYY-MM-DD HH:MM:SS +/-TTTT
categories: [ParentCategory, SubCategory]
tags: [tag1, tag2]
toc: true
---
```
- **Optional:** `math: true` (for MathJax), `mermaid: true` (for diagrams).
- **Hits Counter:** Posts typically start with a hits counter badge immediately after the front matter:
  ```markdown
  [![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)
  ```

### Asset Management
- **Images:** Post-specific images belong in `assets/img/post/{category}/`.
- **OG Images:** Category-specific OG images are generated into `assets/img/og/` via the Python script.

## Architecture & Automation

- **Auto Lastmod:** `_plugins/posts-lastmod-hook.rb` automatically sets `last_modified_at` based on the latest Git commit date for each post.
- **Custom Layouts:** 
  - `_layouts/post.html` includes a custom dialog-based TOC UI.
  - `_includes/toc-status.html` controls TOC visibility.
- **Deployment:** GitHub Actions (`.github/workflows/pages-deploy.yml`) automatically builds and deploys to GitHub Pages upon pushing to the `main` branch.

## Key Files
- `_config.yml`: Main site configuration (title, url, social links, defaults).
- `CLAUDE.md`: Specific instructions for AI assistants.
- `Gemfile`: Ruby dependencies.
- `_tabs/`: Sidebar navigation pages (About, Archives, etc.).
