# Blog Enhancements Planning Document

> **Summary**: Jekyll 블로그에 통계 대시보드, 검색, 시리즈 네비게이션 등 부족한 기능 추가
>
> **Project**: Epheria.github.io (Jekyll + Chirpy v6.1)
> **Author**: Sehyup
> **Date**: 2026-02-18
> **Status**: Draft

---

## 1. Overview

### 1.1 Purpose

123개 포스트가 축적된 기술 블로그에서 콘텐츠 발견성과 사용자 경험을 개선한다. 현재 단순 리스트 형태의 Archives/Categories에서 벗어나, **통계적 시각화**, **검색**, **시리즈 탐색** 기능을 추가하여 방문자와 작성자 모두에게 더 나은 경험을 제공한다.

### 1.2 Background

- 현재 123개 포스트, 15개 카테고리, 다수의 태그 보유
- Archives는 단순 시간순 리스트, Categories는 접히는 리스트뿐
- 검색 기능 부재로 특정 포스트 찾기 어려움
- Mathematics(36개), Unity(38개) 등 시리즈성 포스트가 많지만 순차 탐색 불편
- Hits.sh / Google Analytics 데이터가 있지만 블로그 자체에서 활용되지 않음

### 1.3 Related Documents

- CLAUDE.md: 프로젝트 개요 및 빌드 가이드
- `_config.yml`: 사이트 설정
- Chirpy Theme Docs: https://chirpy.cotes.page/

---

## 2. Scope

### 2.1 In Scope

- [x] **F1. 통계 대시보드 페이지** — 포스트 활동 시각화
- [x] **F2. 검색 기능 활성화** — 클라이언트 사이드 검색
- [x] **F3. 시리즈 네비게이션** — 연관 포스트 순차 탐색

### 2.2 Out of Scope

- 서버 사이드 검색 (Algolia 등 외부 서비스)
- Google Analytics 데이터 연동 인기 포스트 (API 키 필요, 보안 이슈)
- 포스트 난이도 뱃지 시스템 (낮은 우선순위)
- 인터랙티브 차트 라이브러리 (Chart.js/D3.js — 빌드 복잡도 증가)

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-01 | 통계 대시보드: 연도별/월별 포스트 작성 히트맵 (GitHub 잔디 스타일) | High | Pending |
| FR-02 | 통계 대시보드: 카테고리별 포스트 비율 표시 (시각적 바 차트) | High | Pending |
| FR-03 | 통계 대시보드: 핵심 지표 카드 (총 포스트, 총 카테고리, 총 태그 등) | High | Pending |
| FR-04 | 통계 대시보드: 태그 사용 빈도 시각화 (크기 기반 태그 클라우드) | Medium | Pending |
| FR-05 | 통계 대시보드: 최근 활동 타임라인 | Low | Pending |
| FR-06 | 검색: Chirpy 내장 검색 활성화 또는 Lunr.js 기반 검색 구현 | High | Pending |
| FR-07 | 검색: 제목, 내용, 태그, 카테고리 대상 풀텍스트 검색 | High | Pending |
| FR-08 | 시리즈 네비: 같은 카테고리 내 포스트 이전/다음 네비게이션 바 | High | Pending |
| FR-09 | 시리즈 네비: 시리즈 목차(TOC) 사이드 위젯 표시 | Medium | Pending |

### 3.2 Non-Functional Requirements

| Category | Criteria | Measurement Method |
|----------|----------|-------------------|
| Performance | 대시보드 페이지 로드 < 2초 (모바일 포함) | Lighthouse |
| Performance | JS 번들 추가 용량 < 50KB (gzip) | 빌드 사이즈 비교 |
| Compatibility | 기존 Chirpy v6.1 테마와 충돌 없음 | 로컬 빌드 검증 |
| Compatibility | 모바일/데스크톱 반응형 지원 | 다양한 뷰포트 테스트 |
| Maintainability | 포스트 추가 시 대시보드 자동 갱신 (Jekyll 빌드 타임) | 포스트 추가 후 빌드 |

---

## 4. Success Criteria

### 4.1 Definition of Done

- [ ] 통계 대시보드 페이지가 사이드바에서 접근 가능
- [ ] 검색으로 모든 포스트 검색 가능
- [ ] 시리즈 포스트에서 이전/다음 탐색 가능
- [ ] `bundle exec jekyll serve`로 로컬 빌드 정상 동작
- [ ] GitHub Pages 배포 파이프라인 통과

### 4.2 Quality Criteria

- [ ] Lighthouse Performance 점수 90+ 유지
- [ ] HTML Proofer 검증 통과
- [ ] 다크모드에서 정상 표시
- [ ] 모바일(375px~)에서 정상 레이아웃

---

## 5. Risks and Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Chirpy 테마 업데이트 시 커스텀 파일 충돌 | Medium | Medium | 커스텀 파일 목록을 CLAUDE.md에 기록, 오버라이드 최소화 |
| 대시보드 JS가 페이지 로드 성능 저하 | Medium | Low | 순수 CSS 기반 시각화 우선, JS는 최소화 |
| Jekyll Liquid 템플릿으로 복잡한 통계 처리 한계 | High | Medium | 빌드 타임 데이터 생성, 필요 시 Jekyll 플러그인 추가 |
| GitHub Pages에서 커스텀 플러그인 제한 | High | High | GitHub Actions 빌드 사용 (이미 설정됨), 안전한 플러그인만 사용 |

---

## 6. Architecture Considerations

### 6.1 Project Level Selection

| Level | Characteristics | Recommended For | Selected |
|-------|-----------------|-----------------|:--------:|
| **Starter** | Jekyll 정적 사이트, Liquid 템플릿, 순수 CSS/JS | 블로그, 정적 사이트 | ✅ |
| Dynamic | N/A (BaaS 불필요) | - | ☐ |
| Enterprise | N/A (단일 정적 사이트) | - | ☐ |

### 6.2 Key Architectural Decisions

| Decision | Options | Selected | Rationale |
|----------|---------|----------|-----------|
| 대시보드 차트 방식 | Chart.js / 순수 CSS / SVG | **순수 CSS + Liquid** | JS 의존성 제거, 빌드 타임 생성, 경량 |
| 히트맵 구현 | JS 라이브러리 / CSS Grid | **CSS Grid + Liquid** | 외부 라이브러리 불필요, 반응형 |
| 검색 | Algolia / Lunr.js / Chirpy 내장 | **Chirpy 내장 검색** | 테마에 이미 포함, 설정만 활성화 |
| 시리즈 네비 | 플러그인 / Liquid 로직 | **Liquid 로직** | 추가 의존성 없음, 카테고리 기반 |
| 대시보드 위치 | `_tabs/` 새 페이지 | **`_tabs/stats.md`** | 사이드바 통합, 기존 패턴 준수 |

### 6.3 파일 구조 계획

```
변경/추가할 파일:
├── _tabs/stats.md                    # [신규] 통계 대시보드 탭 페이지
├── _layouts/stats.html               # [신규] 통계 대시보드 레이아웃
├── _includes/
│   ├── stats/heatmap.html            # [신규] 포스트 히트맵 컴포넌트
│   ├── stats/category-chart.html     # [신규] 카테고리 차트 컴포넌트
│   ├── stats/summary-cards.html      # [신규] 핵심 지표 카드 컴포넌트
│   ├── stats/tag-cloud.html          # [신규] 태그 클라우드 컴포넌트
│   └── series-nav.html               # [신규] 시리즈 네비게이션 컴포넌트
├── _sass/
│   └── addon/
│       ├── _stats.scss               # [신규] 통계 대시보드 스타일
│       └── _series-nav.scss          # [신규] 시리즈 네비게이션 스타일
├── _layouts/post.html                # [수정] 시리즈 네비 include 추가
├── _config.yml                       # [수정] 검색 설정 활성화 확인
└── _includes/sidebar.html            # [수정] Stats 탭 확인
```

---

## 7. Convention Prerequisites

### 7.1 Existing Project Conventions

- [x] `CLAUDE.md` has coding conventions section
- [x] `.editorconfig` 존재 (UTF-8, 2칸 스페이스, LF)
- [ ] SASS 네이밍 컨벤션 (Chirpy 테마 패턴 따름)
- [x] Jekyll 플러그인은 `_plugins/` 디렉토리
- [x] GitHub Actions 빌드 (커스텀 플러그인 사용 가능)

### 7.2 Conventions to Follow

| Category | Rule | Priority |
|----------|------|:--------:|
| **SASS** | Chirpy 테마의 `_sass/addon/` 디렉토리에 추가 | High |
| **Includes** | 기능별 디렉토리 (`stats/`) 분리 | High |
| **Liquid** | Chirpy 기존 패턴 따름 (site.posts, page.categories 등) | High |
| **레이아웃** | `_layouts/` 오버라이드 최소화, include 우선 | Medium |

---

## 8. Feature Details

### F1. 통계 대시보드 페이지

**히트맵 (GitHub 잔디 스타일)**
- 최근 12개월 포스트 작성 빈도
- 색상 농도로 활동량 표현
- CSS Grid 기반, Liquid로 데이터 생성

**카테고리 차트**
- 수평 바 차트 형태
- 포스트 수 기반 비율 표시
- 카테고리 클릭 시 해당 카테고리 페이지로 이동

**핵심 지표 카드**
- 총 포스트 수 / 총 카테고리 수 / 총 태그 수 / 첫 포스트 날짜 ~ 현재

**태그 클라우드**
- 빈도 기반 폰트 크기 조절
- 클릭 시 해당 태그 페이지로 이동

### F2. 검색 기능

- Chirpy 테마에 내장된 검색 기능 활성화 확인
- `_config.yml`의 `search` 설정 검증
- 필요 시 `simple-jekyll-search` 또는 Lunr.js 통합

### F3. 시리즈 네비게이션

- 같은 `categories[1]` (하위 카테고리)를 공유하는 포스트 그룹
- 포스트 상단 또는 하단에 시리즈 목록 + 현재 위치 표시
- 이전/다음 포스트 버튼

---

## 9. Implementation Order

```
Phase 1: 검색 기능 (가장 빠르게 임팩트)
  └── Chirpy 내장 검색 활성화/설정

Phase 2: 통계 대시보드 (핵심 신규 기능)
  ├── 핵심 지표 카드
  ├── 카테고리 바 차트
  ├── 히트맵
  └── 태그 클라우드

Phase 3: 시리즈 네비게이션 (포스트 UX 개선)
  ├── 시리즈 감지 로직
  ├── 네비게이션 UI
  └── post.html 통합
```

---

## 10. Next Steps

1. [ ] Design 문서 작성 (`blog-enhancements.design.md`)
2. [ ] Phase 1 (검색) 구현
3. [ ] Phase 2 (대시보드) 구현
4. [ ] Phase 3 (시리즈 네비) 구현
5. [ ] 로컬 빌드 테스트 및 배포

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-02-18 | Initial draft | Sehyup + Claude |
