# Blog i18n (다국어 로컬라이징) Planning Document

> **Summary**: Jekyll + Chirpy 블로그에 한국어 외 영어(en) / 일본어(ja) 다국어 지원 시스템 구축
>
> **Project**: Epheria.github.io (Jekyll + Chirpy v6.1)
> **Author**: Sehyup
> **Date**: 2026-02-18
> **Status**: Draft

---

## 1. Overview

### 1.1 Purpose

현재 한국어 단일 언어로 운영되는 블로그에 영어(en) / 일본어(ja) 다국어 지원 시스템을 구축한다.
- 1단계: **UI 텍스트 + 시스템 구조만 구축** (번역 내용 제외)
- 2단계: 이후 번역 콘텐츠를 외부(Gemini 등)에서 생성하여 추가

### 1.2 Background

- 현재 `_config.yml`의 `lang: ko` 고정
- Chirpy 테마가 `site.data.locales[lang]` 기반 locale 시스템을 이미 사용 중 (sidebar.html 확인)
- `_data/locales/` 폴더 미존재 (gem 내부에 있음 → 오버라이드 가능)
- GitHub Actions 빌드 사용 중 → 커스텀 플러그인 사용 가능

### 1.3 Related Documents

- `CLAUDE.md`: 프로젝트 개요 및 빌드 가이드
- `_config.yml`: 사이트 설정 (`lang: ko`)
- `_includes/sidebar.html`: `site.data.locales[include.lang]` 사용 확인
- Chirpy Theme Docs: https://chirpy.cotes.page/

---

## 2. Scope

### 2.1 In Scope (이번 Phase — 시스템 구조만)

- [x] **F1. jekyll-polyglot 플러그인 설치 및 설정**
- [x] **F2. `_data/locales/` 파일 구조 (ko.yml / en.yml / ja.yml)**
- [x] **F3. 언어 전환 UI 컴포넌트** (`_includes/language-switcher.html`)
- [x] **F4. 사이드바 언어 전환 통합** (`_includes/sidebar.html` 수정)
- [x] **F5. SEO hreflang 태그 설정**
- [x] **F6. 언어별 URL 구조 설정** (루트=ko, /en/, /ja/)

### 2.2 Out of Scope (번역 작업 — 외부 위임)

- 포스트 실제 번역 콘텐츠 (`_posts/en/`, `_posts/ja/` 파일들)
- 탭 페이지 번역 내용 (about, archives 등)
- locale yml의 실제 번역 문자열 (골격만 제공)

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-01 | jekyll-polyglot 플러그인 설치 및 `_config.yml` 다국어 설정 | High | Pending |
| FR-02 | `_data/locales/ko.yml`, `en.yml`, `ja.yml` 파일 골격 생성 | High | Pending |
| FR-03 | `_includes/language-switcher.html` 컴포넌트 구현 | High | Pending |
| FR-04 | `_includes/sidebar.html`에 언어 전환 UI 통합 | High | Pending |
| FR-05 | 각 언어별 포스트 디렉토리 구조 정의 (`_posts/en/`, `_posts/ja/`) | Medium | Pending |
| FR-06 | `<link rel="alternate" hreflang>` SEO 태그 자동 생성 | Medium | Pending |
| FR-07 | 언어 미번역 포스트의 폴백(fallback) 동작 정의 | Medium | Pending |
| FR-08 | 모바일에서도 언어 전환 접근 가능 | High | Pending |

### 3.2 Non-Functional Requirements

| Category | Criteria |
|----------|----------|
| Compatibility | 기존 Chirpy v6.1 테마 / blog-enhancements 기능과 충돌 없음 |
| Extensibility | 번역 콘텐츠를 나중에 쉽게 추가할 수 있는 구조 |
| Performance | 언어 전환 JS 추가 용량 < 5KB |
| SEO | 각 언어별 독립 URL, hreflang 태그 |

---

## 4. Architecture Decisions

### 4.1 구현 방식 비교

| 방식 | SEO | 포스트 번역 | 복잡도 | 선택 |
|------|:---:|:-----------:|:------:|:----:|
| **jekyll-polyglot** | ✅ 언어별 URL | ✅ 자연스러운 분리 | 중간 | ✅ |
| Chirpy locale만 | ❌ URL 단일 | ❌ UI 텍스트만 | 낮음 | - |
| 클라이언트 JS 전환 | ❌ 크롤러 미지원 | ❌ 어려움 | 낮음 | - |
| 수동 폴더 구조 | ✅ | ✅ | 높음 | - |

**선택: jekyll-polyglot + Chirpy locale 하이브리드**

- jekyll-polyglot: URL 라우팅, 포스트 언어 분리
- Chirpy locale (ko.yml/en.yml/ja.yml): UI 텍스트 번역

### 4.2 URL 구조

```
https://epheria.github.io/           → 한국어 (기본)
https://epheria.github.io/en/        → 영어
https://epheria.github.io/ja/        → 일본어

https://epheria.github.io/posts/slug/           → 한국어 포스트
https://epheria.github.io/en/posts/slug/        → 영어 번역본 (있으면)
https://epheria.github.io/ja/posts/slug/        → 일본어 번역본 (있으면)
```

### 4.3 폴백 동작

번역본이 없는 포스트에 접근 시:
- `/en/posts/slug/` → 번역본 없으면 한국어 원본으로 리다이렉트(또는 안내 배너 표시)
- locale 파일: Chirpy 기본 locale 상속, 미번역 키는 ko.yml 값 사용

### 4.4 언어 전환 UI 위치 결정

```
옵션 분석:
┌─────────────────────────────────────────────────┐
│ 위치             │ 장점              │ 단점       │
├─────────────────┼──────────────────┼──────────── │
│ 사이드바 하단    │ 다크모드 토글 옆  │ 모바일에서 │
│ (★ 추천)        │ "글로벌 설정" 일관│ 사이드바   │
│                 │ 성, Chirpy 패턴   │ 열어야 함  │
├─────────────────┼──────────────────┼────────────  │
│ 탑바/헤더       │ 눈에 잘 띔        │ Chirpy에   │
│                 │                  │ 헤더 없음  │
├─────────────────┼──────────────────┼────────────  │
│ Floating 버튼   │ 항상 보임         │ 다른 요소  │
│                 │                  │ 방해 가능  │
└─────────────────┴──────────────────┴──────────── │
```

**최종 결정: 사이드바 하단 (다크모드 토글 영역)**

근거:
1. Chirpy 기존 패턴 (`sidebar-bottom`) 준수 — 다크모드, SNS 아이콘과 동일 영역
2. Globe 아이콘(`🌐`) + 드롭다운으로 직관적 UX
3. 데스크톱에서 항상 표시됨
4. 모바일에서도 사이드바 열면 접근 가능 (핵심 설정 → 사이드바 내 위치 자연스러움)

**모바일 보완**: 사이드바가 닫혀 있어도 접근할 수 있도록,
첫 방문 시 자동 감지 언어 안내 배너(선택적) 고려

---

## 5. File Structure Plan

```
신규/수정 파일:
├── Gemfile                              [수정] jekyll-polyglot 추가
├── _config.yml                          [수정] languages, default_lang 설정
├── _data/
│   └── locales/
│       ├── ko.yml                       [신규] 한국어 UI 텍스트 (기존 Chirpy locale 오버라이드)
│       ├── en.yml                       [신규] 영어 UI 텍스트 (골격만)
│       └── ja.yml                       [신규] 일본어 UI 텍스트 (골격만)
├── _includes/
│   ├── language-switcher.html           [신규] 언어 전환 드롭다운 컴포넌트
│   └── sidebar.html                     [수정] language-switcher include 추가
├── _sass/addon/
│   └── _language-switcher.scss          [신규] 언어 전환 UI 스타일
├── _posts/
│   ├── (기존 KO 포스트들 그대로 유지)
│   ├── en/                             [신규 디렉토리] 영어 번역 포스트 (번역 시 추가)
│   └── ja/                             [신규 디렉토리] 일본어 번역 포스트 (번역 시 추가)
└── assets/css/jekyll-theme-chirpy.scss  [수정] _language-switcher import 추가
```

---

## 6. locale.yml 구조 (골격)

```yaml
# _data/locales/en.yml (예시 골격)
tabs:
  home: Home
  categories: Categories
  tags: Tags
  archives: Archives
  about: About
  stats: Stats

posts:
  undefined_lang: English translation not available
  back_to_original: View original (Korean)

panel:
  lastmod: Last Modified
  trending_tags: Trending Tags
  toc: Contents
```

---

## 7. Success Criteria

- [ ] `bundle exec jekyll serve` 로컬 빌드 정상 (en/ja URL 접근 가능)
- [ ] 사이드바 하단에 언어 전환 UI 표시
- [ ] 언어 전환 시 URL 변경 및 UI 텍스트 전환 확인
- [ ] ko/en/ja locale 파일이 Chirpy 기본값 올바르게 오버라이드
- [ ] GitHub Actions 배포 파이프라인 통과
- [ ] HTML Proofer 통과

---

## 8. Risks and Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| jekyll-polyglot과 Chirpy 테마 충돌 | High | 사전에 호환성 이슈 리서치, 필요시 수동 URL 구조로 대체 |
| jekyll-polyglot GitHub Actions 빌드 지원 | Medium | GitHub Actions에 gem 추가로 해결 가능 (이미 커스텀 빌드 사용 중) |
| 기존 permalink 구조 (`/posts/:title/`) 변경 | High | default_lang(ko)는 기존 URL 유지, 신규 언어만 prefix 추가 |
| Chirpy locale 키 구조 변경 (버전업) | Low | `_data/locales/`에 오버라이드 파일 유지로 격리 |

---

## 9. Implementation Order

```
Step 1: 플러그인 설치 및 기본 설정
  ├── Gemfile에 jekyll-polyglot 추가
  └── _config.yml 다국어 설정

Step 2: Locale 파일 구조
  ├── _data/locales/ko.yml (Chirpy 기본값 오버라이드)
  ├── _data/locales/en.yml (골격, 번역 키만)
  └── _data/locales/ja.yml (골격, 번역 키만)

Step 3: 언어 전환 UI
  ├── _includes/language-switcher.html (Globe 아이콘 + 드롭다운)
  ├── _sass/addon/_language-switcher.scss
  └── _includes/sidebar.html 수정

Step 4: SEO 설정
  └── hreflang 태그 (head include 수정)

Step 5: 포스트 디렉토리 구조
  └── _posts/en/, _posts/ja/ 디렉토리 생성 (빈 상태)
```

---

## 10. Next Steps

1. [ ] Design 문서 작성 (`blog-i18n.design.md`)
2. [ ] jekyll-polyglot 호환성 검증
3. [ ] Step 1~5 순서로 구현
4. [ ] 번역 콘텐츠 추가 (Gemini 위임)

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-02-18 | Initial draft | Sehyup + Claude |
