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
- **Python:** 3.x (for OG image generation and popular posts fetching)

### Commands
- **Install Dependencies:** `bundle install`
- **Local Development Server:** `bundle exec jekyll serve` (Available at `http://localhost:4000`)
- **Production Build:** `JEKYLL_ENV=production bundle exec jekyll build`
- **HTML Proofing (Validation):** `bundle exec htmlproofer _site --disable-external --check-html --allow_hash_href`
- **Generate Category OG Images:** `python3 scripts/generate_og_images.py`
- **Fetch Popular Posts:** `python3 scripts/fetch_popular_posts.py`

## Development Conventions

### Post Structure
- **Path:** `_posts/{Category}/{Subcategory}/YYYY-MM-DD-slug.md`
- **Categories:** `Common`, `Csharp`, `ETC`, `Language`, `Mathematics`, `ML`, `Python`, `Survivor`, `TheQuesting`, `Toyverse`, `Unity`, `Unreal`.

### Front Matter Requirements
```yaml
---
title: Post Title
date: YYYY-MM-DD HH:MM:SS +/-TTTT
categories: [ParentCategory, SubCategory]
tags: [tag1, tag2]
toc: true
toc_sticky: true
difficulty: beginner | intermediate | advanced  # Optional
prerequisites: ["/posts/slug/"]              # Optional
tldr: ["Summary point 1", "Summary point 2"] # Optional
---
```
- **Optional:** `math: true`, `mermaid: true`.
- **Hits Counter:** Posts typically start with `[![Hits](...)](...)` immediately after front matter.

### Rich Content & UI Features
- **Difficulty Badges:** Use `difficulty` field to display level badges (beginner/intermediate/advanced).
- **Series Navigation:** Automatically activated if a post has at least 2 categories. Posts sharing the same `categories[0]` and `categories[1]` are grouped into a series.
- **TL;DR Box:** Use `tldr` list to display a summary box at the top.
- **Prerequisites:** Use `prerequisites` list (post URL paths) to link required previous reading.

## Architecture & Automation

- **Auto Lastmod:** `_plugins/posts-lastmod-hook.rb` sets `last_modified_at` via Git logs.
- **Stats Dashboard:** Accessible at `/stats/`. Layout defined in `_layouts/stats.html` using components in `_includes/stats/`.
- **Popular Posts:** Managed via `_data/popular-posts.yml` and updated automatically via GitHub Actions or manually via Python script.
- **Custom UI Components:** Found in `_includes/` (e.g., `series-nav.html`, `tldr.html`, `post-difficulty.html`).
- **Asset Management:**
  - **Images:** Post-specific images in `assets/img/post/{category}/`.
  - **OG Images:** Category OG images generated into `assets/img/og/`.

## Key Files
- `_config.yml`: Main site configuration.
- `CLAUDE.md`: Detailed instructions for AI assistants.
- `_tabs/`: Sidebar navigation pages (About, Archives, Categories, Tags, Books, Sideproject, **Stats**).
- `_sass/addon/`: Custom styles for new UI features.
