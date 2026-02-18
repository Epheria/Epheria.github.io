# Blog i18n 설계 문서

> **Feature**: blog-i18n (다국어 로컬라이징 시스템)
> **Plan Reference**: `docs/01-plan/features/blog-i18n.plan.md`
> **Author**: Sehyup
> **Date**: 2026-02-18
> **Status**: Draft

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                   jekyll-polyglot                        │
│                                                         │
│  빌드 시 각 언어별 페이지 복제                              │
│  site.active_lang → "ko" | "en" | "ja"                 │
└─────────────────┬───────────────────────────────────────┘
                  │
     ┌────────────┼────────────┐
     ▼            ▼            ▼
  /           /en/          /ja/
(한국어)      (영어)          (일본어)
                  │
     ┌────────────┼────────────┐
     ▼            ▼            ▼
_data/locales  lang.html    language-switcher
  ko.yml       오버라이드       UI 컴포넌트
  en.yml         │
  ja.yml         ▼
             sidebar.html
          (Globe 버튼 통합)
```

### 동작 원리
1. **jekyll-polyglot**이 빌드 시 모든 페이지를 3개 언어로 복제
2. **`site.active_lang`** 변수로 현재 빌드 언어 결정
3. **Chirpy `lang.html`** 오버라이드 → `site.active_lang` 우선 사용
4. **`_data/locales/{lang}.yml`** → UI 텍스트 번역 제공
5. **`language-switcher.html`** → 사이드바에서 언어 전환 UI 제공

---

## 2. 기술 스택

| 구성 요소 | 선택 | 이유 |
|-----------|------|------|
| 다국어 라우팅 | jekyll-polyglot | SEO 친화적 URL, `site.active_lang` 제공, Chirpy 호환 |
| UI 텍스트 번역 | Chirpy locale YAML | 기존 시스템 활용, 오버라이드 가능 |
| 언어 전환 UI | Vanilla JS + CSS | 의존성 없음, Chirpy 패턴 준수 |
| 언어 상태 저장 | localStorage | 재방문 시 언어 유지 |

---

## 3. 파일 구조

```
신규/수정 파일:
├── Gemfile                                  [수정] jekyll-polyglot gem 추가
├── _config.yml                              [수정] polyglot 설정 추가
├── _data/
│   └── locales/
│       ├── ko.yml                           [신규] Chirpy ko-KR 기반 한국어
│       ├── en.yml                           [신규] 영어 (Chirpy en.yml 오버라이드 + 확장)
│       └── ja.yml                           [신규] 일본어 골격
├── _includes/
│   ├── lang.html                            [신규/오버라이드] site.active_lang 지원
│   └── language-switcher.html              [신규] 언어 전환 드롭다운
├── _sass/addon/
│   └── _language-switcher.scss             [신규] 언어 전환 UI 스타일
├── _includes/sidebar.html                   [수정] language-switcher include 추가
└── assets/css/jekyll-theme-chirpy.scss     [수정] _language-switcher import 추가

미래 번역 포스트용 (비워둠):
└── _posts/
    └── (기존 KO 포스트 그대로 유지)
    → 번역 포스트는 front matter의 lang 및 permalink로 언어 구분
```

---

## 4. 상세 구현 설계

### 4.1 Gemfile

```ruby
# 기존 내용 유지, 아래 추가
gem 'jekyll-polyglot'
```

### 4.2 `_config.yml` 변경 사항

```yaml
# 기존 lang: ko 유지 (polyglot의 default_lang과 일치)
lang: ko

# polyglot 다국어 설정 추가 (기존 설정 하단에)
languages: ["ko", "en", "ja"]
default_lang: "ko"
exclude_from_localization: ["assets/js", "assets/css", "assets/img", "assets/lib"]
parallel_localization: false  # true 시 Jekyll 빌드 오류 가능성 있음

# plugins 배열에 추가
plugins:
  - jekyll-polyglot
```

### 4.3 `_includes/lang.html` (Chirpy 오버라이드)

```liquid
{% comment %}
  Chirpy lang.html 오버라이드:
  jekyll-polyglot의 site.active_lang을 우선 사용,
  없으면 기존 Chirpy 방식(site.lang) 사용
{% endcomment %}
{% if site.active_lang %}
  {% if site.data.locales[site.active_lang] %}
    {% assign lang = site.active_lang %}
  {% elsif site.data.locales[site.lang] %}
    {% assign lang = site.lang %}
  {% else %}
    {% assign lang = 'en' %}
  {% endif %}
{% elsif site.data.locales[site.lang] %}
  {% assign lang = site.lang %}
{% else %}
  {% assign lang = 'en' %}
{% endif %}
```

### 4.4 `_data/locales/ko.yml`

```yaml
# Chirpy ko-KR.yml 기반 (blog-i18n 확장 포함)

layout:
  post: 포스트
  category: 카테고리
  tag: 태그

tabs:
  home: 홈
  categories: 카테고리
  tags: 태그
  archives: 아카이브
  about: 정보
  stats: 통계
  books: 독서
  sideproject: 사이드 프로젝트

search:
  hint: 검색
  cancel: 취소
  no_results: 검색 결과가 없습니다.

panel:
  lastmod: 최근 업데이트
  trending_tags: 인기 태그
  toc: 바로가기

copyright:
  license:
    template: 이 기사는 저작권자의 :LICENSE_NAME 라이센스를 따릅니다.
    name: CC BY 4.0
    link: https://creativecommons.org/licenses/by/4.0/
  brief: 일부 권리 보유
  verbose: >-
    명시되지 않는 한 이 사이트의 블로그 게시물은 작성자의
    Creative Commons Attribution 4.0 International(CC BY 4.0) 라이선스에 따라 사용이 허가되었습니다.

meta: Powered by :PLATFORM with :THEME theme

not_found:
  statment: 해당 URL은 존재하지 않습니다.

notification:
  update_found: 새 버전의 콘텐츠를 사용할 수 있습니다.
  update: 업데이트

post:
  written_by: By
  posted: 게시
  updated: 업데이트
  words: 단어
  pageview_measure: 조회
  read_time:
    unit: 분
    prompt: 읽는 시간
  relate_posts: 관련된 글
  share: 공유하기
  button:
    next: 다음 글
    previous: 이전 글
    copy_code:
      succeed: 복사되었습니다!
    share_link:
      title: 링크 복사하기
      succeed: 링크가 복사되었습니다!

df:
  post:
    strftime: "%Y/%m/%d"
    dayjs: "YYYY/MM/DD"
  archives:
    strftime: "%Y년 %m월"
    dayjs: "YYYY년 MM월"

categories:
  category_measure: 카테고리
  post_measure: 포스트

# blog-i18n 전용 키
i18n:
  language_label: 언어
  no_translation: 이 포스트는 아직 번역되지 않았습니다.
  view_original: 원본(한국어) 보기
  popular_posts: 인기 포스트
  series: 시리즈
  difficulty:
    beginner: 초급
    intermediate: 중급
    advanced: 고급
```

### 4.5 `_data/locales/en.yml`

```yaml
# English locale (Chirpy en.yml base + blog-i18n extensions)
# 번역 작업: Gemini에 위임 예정

layout:
  post: Post
  category: Category
  tag: Tag

tabs:
  home: Home
  categories: Categories
  tags: Tags
  archives: Archives
  about: About
  stats: Stats
  books: Books
  sideproject: Side Projects

search:
  hint: search
  cancel: Cancel
  no_results: Oops! No results found.

panel:
  lastmod: Recently Updated
  trending_tags: Trending Tags
  toc: Contents

copyright:
  license:
    template: This post is licensed under :LICENSE_NAME by the author.
    name: CC BY 4.0
    link: https://creativecommons.org/licenses/by/4.0/
  brief: Some rights reserved.
  verbose: >-
    Except where otherwise noted, the blog posts on this site are licensed
    under the Creative Commons Attribution 4.0 International (CC BY 4.0) License by the author.

meta: Using the :PLATFORM theme :THEME

not_found:
  statment: Sorry, we've misplaced that URL or it's pointing to something that doesn't exist.

notification:
  update_found: A new version of content is available.
  update: Update

post:
  written_by: By
  posted: Posted
  updated: Updated
  words: words
  pageview_measure: views
  read_time:
    unit: min
    prompt: read
  relate_posts: Further Reading
  share: Share
  button:
    next: Newer
    previous: Older
    copy_code:
      succeed: Copied!
    share_link:
      title: Copy link
      succeed: Link copied successfully!

df:
  post:
    strftime: "%b %e, %Y"
    dayjs: "ll"
  archives:
    strftime: "%b"
    dayjs: "MMM"

categories:
  category_measure:
    singular: category
    plural: categories
  post_measure:
    singular: post
    plural: posts

# blog-i18n 전용 키
i18n:
  language_label: Language
  no_translation: This post is not yet translated.
  view_original: View original (Korean)
  popular_posts: Popular Posts
  series: Series
  difficulty:
    beginner: Beginner
    intermediate: Intermediate
    advanced: Advanced
```

### 4.6 `_data/locales/ja.yml`

```yaml
# 日本語ロケール (골격 — 번역 Gemini 위임 예정)

layout:
  post: 記事
  category: カテゴリー
  tag: タグ

tabs:
  home: ホーム
  categories: カテゴリー
  tags: タグ
  archives: アーカイブ
  about: プロフィール
  stats: 統計
  books: 読書
  sideproject: サイドプロジェクト

search:
  hint: 検索
  cancel: キャンセル
  no_results: 検索結果がありません。

panel:
  lastmod: 最近更新
  trending_tags: 人気タグ
  toc: 目次

copyright:
  license:
    template: この記事は著者の:LICENSE_NAMEライセンスの下で提供されています。
    name: CC BY 4.0
    link: https://creativecommons.org/licenses/by/4.0/
  brief: 一部の権利を保有。
  verbose: >-
    特別な記載がない限り、このサイトのブログ記事は著者による
    Creative Commons Attribution 4.0 International (CC BY 4.0) ライセンスの下で提供されています。

meta: Powered by :PLATFORM with :THEME theme

not_found:
  statment: お探しのURLは存在しません。

notification:
  update_found: 新しいバージョンのコンテンツが利用可能です。
  update: 更新

post:
  written_by: By
  posted: 投稿
  updated: 更新
  words: 語
  pageview_measure: 閲覧
  read_time:
    unit: 分
    prompt: 読む時間
  relate_posts: 関連記事
  share: シェア
  button:
    next: 次の記事
    previous: 前の記事
    copy_code:
      succeed: コピーしました！
    share_link:
      title: リンクをコピー
      succeed: リンクをコピーしました！

df:
  post:
    strftime: "%Y/%m/%d"
    dayjs: "YYYY/MM/DD"
  archives:
    strftime: "%Y年%m月"
    dayjs: "YYYY年MM月"

categories:
  category_measure: カテゴリー
  post_measure: 記事

# blog-i18n 전용 키
i18n:
  language_label: 言語
  no_translation: この記事はまだ翻訳されていません。
  view_original: 原文（韓国語）を見る
  popular_posts: 人気記事
  series: シリーズ
  difficulty:
    beginner: 初級
    intermediate: 中級
    advanced: 上級
```

### 4.7 `_includes/language-switcher.html`

```liquid
{% comment %}
  언어 전환 드롭다운 컴포넌트
  sidebar-bottom 영역에 삽입
  현재 언어: site.active_lang (polyglot) 또는 site.lang
{% endcomment %}

{% assign current_lang = site.active_lang | default: site.lang | default: 'ko' %}

<div class="language-switcher" id="languageSwitcher">
  <button class="lang-toggle btn" aria-label="{{ site.data.locales[current_lang].i18n.language_label | default: 'Language' }}" aria-expanded="false" aria-haspopup="true">
    <i class="fas fa-globe fa-fw"></i>
    <span class="lang-current">{{ current_lang | upcase }}</span>
  </button>

  <div class="lang-dropdown" role="menu" aria-hidden="true">
    {% assign lang_labels = "ko:한국어,en:English,ja:日本語" | split: "," %}
    {% for lang_item in lang_labels %}
      {% assign parts = lang_item | split: ":" %}
      {% assign lang_code = parts[0] %}
      {% assign lang_name = parts[1] %}

      {% if lang_code == current_lang %}
        <span class="lang-item active" role="menuitem" aria-current="true">
          {{ lang_name }}
          <i class="fas fa-check fa-fw"></i>
        </span>
      {% else %}
        {% comment %}
          URL 생성: polyglot은 자동으로 /en/, /ja/ prefix를 추가
          현재 페이지의 상대 경로를 유지하면서 언어 전환
        {% endcomment %}
        {% if lang_code == site.default_lang %}
          {% assign lang_url = page.url | remove: '/en' | remove: '/ja' | relative_url %}
        {% else %}
          {% assign raw_url = page.url | remove: '/en' | remove: '/ja' %}
          {% assign lang_url = lang_code | prepend: '/' | append: raw_url | relative_url %}
        {% endif %}
        <a href="{{ lang_url }}" class="lang-item" role="menuitem"
           hreflang="{{ lang_code }}"
           onclick="localStorage.setItem('preferred-lang', '{{ lang_code }}')">
          {{ lang_name }}
        </a>
      {% endif %}
    {% endfor %}
  </div>
</div>

<script>
  // 언어 전환 드롭다운 토글
  (function() {
    var switcher = document.getElementById('languageSwitcher');
    if (!switcher) return;
    var toggle = switcher.querySelector('.lang-toggle');
    var dropdown = switcher.querySelector('.lang-dropdown');

    toggle.addEventListener('click', function(e) {
      e.stopPropagation();
      var isOpen = dropdown.classList.contains('show');
      dropdown.classList.toggle('show');
      toggle.setAttribute('aria-expanded', !isOpen);
      dropdown.setAttribute('aria-hidden', isOpen);
    });

    document.addEventListener('click', function() {
      dropdown.classList.remove('show');
      toggle.setAttribute('aria-expanded', 'false');
      dropdown.setAttribute('aria-hidden', 'true');
    });
  })();
</script>
```

### 4.8 `_includes/sidebar.html` 수정 위치

```liquid
<!-- 기존 sidebar-bottom div 내부 수정 -->
<div class="sidebar-bottom d-flex flex-wrap align-items-center w-100">

  {% unless site.theme_mode %}
    <button class="mode-toggle btn" aria-label="Switch Mode">
      <i class="fas fa-adjust"></i>
    </button>
    {% if site.data.contact.size > 0 %}
      <span class="icon-border"></span>
    {% endif %}
  {% endunless %}

  <!-- ★ 언어 전환 추가 위치 (다크모드 토글 다음) -->
  {% include language-switcher.html %}
  <span class="icon-border"></span>
  <!-- ★ 끝 -->

  {% for entry in site.data.contact %}
    ... (기존 코드 유지)
  {% endfor %}
</div>
```

### 4.9 `_sass/addon/_language-switcher.scss`

```scss
/* 언어 전환 드롭다운 스타일 */

.language-switcher {
  position: relative;
  display: inline-flex;
  align-items: center;

  .lang-toggle {
    display: flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.25rem 0.4rem;
    color: var(--sidebar-btn-color, inherit);
    font-size: 0.85rem;

    &:hover {
      color: var(--sidebar-hover-color, #fff);
    }

    .lang-current {
      font-size: 0.7rem;
      font-weight: 600;
      letter-spacing: 0.05em;
    }
  }

  .lang-dropdown {
    display: none;
    position: absolute;
    bottom: calc(100% + 0.5rem);
    left: 50%;
    transform: translateX(-50%);
    background: var(--sidebar-bg, #21252a);
    border: 1px solid var(--border-color, rgba(255,255,255,0.15));
    border-radius: 0.375rem;
    padding: 0.25rem 0;
    min-width: 120px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    z-index: 1000;

    &.show {
      display: block;
    }

    .lang-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0.4rem 0.75rem;
      font-size: 0.85rem;
      color: var(--sidebar-muted-color, rgba(255,255,255,0.6));
      text-decoration: none;
      white-space: nowrap;
      cursor: pointer;

      &:hover {
        color: var(--sidebar-hover-color, #fff);
        background: rgba(255, 255, 255, 0.08);
      }

      &.active {
        color: var(--sidebar-active-color, #fff);
        font-weight: 600;

        i { font-size: 0.7rem; }
      }

      // anchor 스타일 리셋
      &[href] {
        display: flex;
      }
    }
  }
}
```

### 4.10 `assets/css/jekyll-theme-chirpy.scss` 수정

```scss
// 기존 내용에 아래 줄 추가
@import 'addon/language-switcher';
```

---

## 5. 번역 포스트 구조 설계

### 5.1 한국어 포스트 (기존 유지)

```yaml
# _posts/Unity/2024-01-15-example.md
---
title: 예시 포스트
date: 2024-01-15
categories: [Unity, build]
lang: ko  # 선택적 — 없으면 ko 기본
---
```

### 5.2 영어 번역 포스트 (미래 추가용)

```yaml
# _posts/en/2024-01-15-example.md
---
title: Example Post
date: 2024-01-15
categories: [Unity, build]
lang: en
permalink: /en/posts/example/  # 명시적 permalink
---
```

polyglot이 자동으로 `/en/` prefix를 생성하므로,
`_posts/` 폴더 내 포스트 중 `lang: en` 설정 포스트가 영어 버전으로 동작.

### 5.3 포스트 번역 연결 (선택적)

번역본이 있는 경우 front matter에 `translations` 명시:

```yaml
---
title: 예시 포스트
lang: ko
translations:
  en: /en/posts/example/
  ja: /ja/posts/example/
---
```

이를 `post.html`에서 활용해 "이 포스트의 번역본 보기" 링크 표시 가능.

---

## 6. SEO hreflang 설계

Chirpy의 `_includes/head.html`이 오버라이드되어 있지 않으므로,
`_includes/head.html`에 hreflang 태그를 주입하는 방법은 복잡함.

**대안: `_layouts/default.html` 오버라이드 없이 polyglot의 자동 처리 활용**

jekyll-polyglot은 기본적으로 hreflang 태그를 자동 생성하지 않으므로,
`_includes/head.html` 최소 오버라이드:

```html
<!-- _includes/head.html (Chirpy gem 내부 파일 오버라이드) -->
<!-- 기존 head 내용 그대로 포함 후 hreflang 추가 -->
<!-- 이 방법은 Chirpy 업데이트 시 유지보수 필요 -->
```

**권장 방식**: `_includes/seo.html` 파일 확인 후 최소 수정 적용
(구현 단계에서 Chirpy head 구조 확인 후 결정)

---

## 7. 데이터 흐름

```
사용자가 /en/ 접근
    │
    ▼
jekyll-polyglot → site.active_lang = "en"
    │
    ▼
lang.html (오버라이드) → lang = "en"
    │
    ▼
site.data.locales["en"] 로드
    │
    ▼
sidebar.html → language-switcher.html
  locale["en"].i18n.language_label = "Language"
    │
    ▼
language-switcher → 현재 "EN" 표시, ko/ja로 전환 링크 제공
```

---

## 8. 구현 순서 (Step-by-Step)

```
Step 1: 플러그인 설치
  ├── Gemfile: gem 'jekyll-polyglot' 추가
  └── bundle install

Step 2: _config.yml 설정
  ├── languages: ["ko", "en", "ja"]
  ├── default_lang: "ko"
  └── exclude_from_localization 설정

Step 3: locale 파일 생성
  ├── _data/locales/ko.yml
  ├── _data/locales/en.yml
  └── _data/locales/ja.yml

Step 4: lang.html 오버라이드
  └── _includes/lang.html

Step 5: language-switcher 컴포넌트
  ├── _includes/language-switcher.html
  └── _sass/addon/_language-switcher.scss

Step 6: sidebar.html 수정
  └── sidebar-bottom에 switcher include 추가

Step 7: CSS import
  └── assets/css/jekyll-theme-chirpy.scss 수정

Step 8: 로컬 빌드 검증
  └── bundle exec jekyll serve
      → /en/, /ja/ URL 접근 확인
      → 사이드바 언어 전환 UI 확인
```

---

## 9. 잠재적 이슈 및 해결 방안

| 이슈 | 원인 | 해결 |
|------|------|------|
| polyglot이 JS/CSS도 복제 | 기본 동작 | `exclude_from_localization` 설정 |
| 기존 permalink 구조 변경 | polyglot prefix 추가 | `default_lang: ko` → ko는 루트 유지 |
| Chirpy `lang.html` gem 내부 | 오버라이드 필요 | `_includes/lang.html` 로컬 파일 생성 |
| 번역 없는 포스트 /en/에서도 노출 | polyglot 복제 동작 | 정상 동작 (번역 추가 전까지 한국어 노출) |
| `parallel_localization: true` 빌드 오류 | Ruby 스레드 이슈 | `false`로 설정 |
| 모바일에서 사이드바 닫혀 있음 | Chirpy 기본 동작 | 사이드바 내 위치로 충분 (이미 예상된 UX) |

---

## 10. 검증 기준

| 항목 | 확인 방법 |
|------|-----------|
| ko URL 기존 유지 | `/posts/slug/` 정상 접근 |
| en URL 생성 | `/en/posts/slug/` 접근 가능 |
| ja URL 생성 | `/ja/posts/slug/` 접근 가능 |
| UI 텍스트 전환 | `/en/`에서 사이드바 탭 "Home", "Categories" 등 영어 표시 |
| 언어 전환 버튼 | 사이드바 하단 Globe 버튼 표시 및 드롭다운 동작 |
| 기존 기능 유지 | 통계, 시리즈 네비, 인기 포스트 등 정상 동작 |
| 빌드 성공 | `bundle exec jekyll build` 에러 없음 |
| HTML Proofer | `bundle exec htmlproofer _site` 통과 |

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-02-18 | Initial design | Sehyup + Claude |
