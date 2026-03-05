---
title: "Claude 메모리 무료 개방과 /simplify, /batch — 그리고 CLAUDE.md의 숨겨진 비용"
date: 2026-03-04 14:00:00 +0900
categories: [AI, Claude]
tags: [Claude, Claude Code, Memory, AI, LLM, simplify, batch, CLAUDE.md, Token Optimization, Developer Tools]

difficulty: intermediate
toc: true
toc_sticky: true
prerequisites:
  - /posts/ClaudeCodeInsights/
  - /posts/EvaluatingAgentsMd/
tldr:
  - "Anthropic이 Claude 메모리를 무료 플랜에 개방하고, ChatGPT/Gemini 메모리 가져오기 도구를 출시했다 — App Store 무료 앱 1위 등극 직후의 공격적 행보"
  - "/simplify는 3개의 병렬 리뷰 에이전트(코드 재사용·품질·효율성)로 PR당 3~5개 이슈를 자동 수정하고, /batch는 코드베이스 전체를 5~30개 단위로 분해해 병렬 마이그레이션한다"
  - "CLAUDE.md를 과도하게 네스팅하면 세션당 최대 55K+ 토큰이 낭비되며, Skill 기반 점진적 로딩으로 82%까지 컨텍스트를 절약할 수 있다"
---

## 들어가며

2026년 3월 첫째 주, Claude 생태계에서 주목할 만한 세 가지 움직임이 있었다.

1. **Claude 메모리가 무료 플랜에 개방**되고, 경쟁사 메모리 가져오기 도구가 출시됐다
2. Claude Code에 **`/simplify`와 `/batch`** 스킬이 번들로 탑재됐다
3. CLAUDE.md의 **네스팅 패턴이 야기하는 토큰 비용 문제**가 커뮤니티에서 본격적으로 논의되기 시작했다

이 글에서는 세 주제를 각각 깊이 다루되, 특히 세 번째 주제에서는 이전 포스트([AGENTS.md는 정말 도움이 될까?](/posts/EvaluatingAgentsMd/))에서 다뤘던 컨텍스트 파일의 역설을 실제 토큰 수치로 확장한다.

---

## 1. Claude 메모리 — 무료 플랜 개방과 메모리 가져오기

### 1-1. 타임라인

| 시점 | 이벤트 |
|------|--------|
| 2025년 8월 | Claude 메모리 최초 도입 (유료 플랜 한정) |
| 2025년 10월 | Pro, Max, Team, Enterprise 전 유료 플랜 확대 |
| 2026년 3월 2일 | **무료 플랜 개방** + 메모리 가져오기 도구 출시 |

약 8개월에 걸친 단계적 롤아웃이 완료된 셈이다. 타이밍이 의미심장한데, Claude가 **App Store 무료 앱 차트 1위**에 오른 직후이고, ChatGPT DoD(미국 국방부) 계약 이후 **ChatGPT 삭제가 295% 급증**한 시점이다.

### 1-2. 메모리 작동 방식

Claude의 메모리는 대화를 나누는 동안 자동으로 생성되는 요약본이다.

```
사용자 대화 → Claude가 선호도/프로젝트/컨텍스트 추론 → 텍스트 파일로 저장
```

핵심 특징:
- **자동 추론**: 대화 중 사용자의 선호도, 진행 중인 프로젝트, 작업 맥락을 자동으로 파악
- **편집 가능**: 저장된 메모리를 사용자가 직접 확인하고 수정할 수 있다
- **제어 옵션**: 일시정지(메모리 보존, 비활성화) 또는 완전 삭제 선택 가능
- **업무 중심**: 업무 관련 맥락에 집중하도록 설계되어, 업무와 무관한 개인 정보는 보존하지 않을 수 있다

### 1-3. 메모리 가져오기 도구

ChatGPT, Gemini 등 경쟁 챗봇에서 Claude로 전환하는 사용자를 위한 도구가 동시에 출시됐다.

**이전 과정:**

1. Claude가 제공하는 내보내기 프롬프트를 ChatGPT/Gemini에 붙여넣기
2. 해당 챗봇이 저장된 메모리를 코드 블록 형태로 출력
3. 이 텍스트를 Claude에 붙여넣고 "Add to memory" 클릭
4. Claude가 핵심 정보를 추출해 개별 메모리 항목으로 저장

**주의사항:**
- 아직 실험적 기능이라 모든 메모리가 완벽하게 이전되지 않을 수 있다
- 업무 관련 컨텍스트 위주로 보존되며, 무관한 개인 정보는 누락될 수 있다

### 1-4. 이것이 의미하는 것

메모리 무료 개방은 단순한 기능 확대가 아니다. AI 챗봇 시장에서 **전환 비용(switching cost)을 낮추는** 전략적 행보다. 다른 챗봇에 축적된 컨텍스트가 "이미 익숙한 AI를 계속 쓰게 만드는" 잠금 효과를 만드는데, 가져오기 도구는 이 장벽을 정면으로 부순다.

게임 개발자 관점에서는, Unity 에디터에서 Unreal Engine으로 이전할 때 에셋 마이그레이션 도구를 제공하는 것과 비슷한 맥락이다.

---

## 2. /simplify — 3개의 병렬 리뷰 에이전트

### 2-1. 개요

`/simplify`는 Claude Code v2.1.63에서 도입된 **번들 스킬**이다. 기능을 구현하고 동작을 확인한 뒤, 커밋 전에 실행하면 코드 품질을 자동으로 개선한다.

공식 문서의 설명:

> `/simplify`: reviews your recently changed files for code reuse, quality, and efficiency issues, then fixes them.

### 2-2. 3개의 병렬 리뷰 에이전트

`/simplify`의 핵심은 **세 개의 서브에이전트를 병렬로 스폰**하는 구조다.

```
/simplify 실행
    ├── 🔄 Code Reuse Agent
    │    └── 중복 로직, 추출 가능한 패턴 검사
    ├── 📐 Code Quality Agent
    │    └── 가독성, 네이밍, 구조 검사
    └── ⚡ Efficiency Agent
         └── 불필요한 복잡도, 중복 연산 검사

    → 3개 에이전트 결과 집계
    → 자동 수정 적용
```

**각 에이전트의 역할:**

| 에이전트 | 검사 대상 | 실무에서 주로 잡는 것 |
|---------|----------|-------------------|
| Code Reuse | 중복 로직, 추출 가능한 패턴 | 여러 파일에 복사된 유사 함수 |
| Code Quality | 가독성, 네이밍, 구조 | 명확하지 않은 변수명, 과도한 중첩 |
| Efficiency | 불필요한 복잡도, 놓친 최적화 | 불필요한 반복, 놓친 동시성 기회 |

실사용 보고에 따르면, **피처 브랜치당 3~5개의 이슈**를 일관되게 잡아내며, 특히 Efficiency 에이전트가 불필요한 반복과 놓친 동시성 기회를 포착하는 데 강하다.

### 2-3. 사용법

```bash
# 기본 사용 — 변경된 파일 전체 리뷰
/simplify

# 특정 관심사에 집중
/simplify focus on memory efficiency

# 특정 패턴에 집중
/simplify focus on null safety and error handling
```

**권장 워크플로우:**

```
기능 구현 → 동작 확인 → /simplify → 커밋 → PR
```

매 PR 전에 `/simplify`를 실행하는 것을 습관으로 만들면, 코드 리뷰에서 지적받을 이슈를 사전에 제거할 수 있다.

---

## 3. /batch — 대규모 병렬 코드 마이그레이션

### 3-1. 개요

`/batch`는 코드베이스 전체에 걸친 대규모 변경을 **병렬로** 수행하는 스킬이다. 단순한 검색-치환이 아니라, 연구 → 분해 → 실행 → PR 생성까지의 전체 파이프라인을 오케스트레이션한다.

### 3-2. 작동 방식

```
/batch "migrate src/ from Solid to React"
    │
    ├── 1. 코드베이스 리서치
    │    └── 변경 대상 파일과 패턴 분석
    │
    ├── 2. 작업 분해 (5~30개 단위)
    │    └── 독립적으로 처리 가능한 단위로 분할
    │
    ├── 3. 사용자 승인
    │    └── 분해된 계획을 보여주고 승인 요청
    │
    └── 4. 병렬 실행
         ├── Worker 1 (격리된 git worktree)
         │    ├── 구현
         │    ├── 테스트
         │    ├── /simplify (자동)
         │    └── PR 생성
         ├── Worker 2 (격리된 git worktree)
         │    └── ...
         └── Worker N
              └── ...
```

핵심 포인트:
- **격리된 git worktree**: 각 워커가 독립된 워킹 트리에서 작업하므로 충돌이 없다
- **자동 /simplify**: 각 워커가 커밋 전에 자동으로 `/simplify`를 실행한다. 수동 체이닝이 불필요
- **git 저장소 필수**: 워크트리 기능을 사용하므로 git 저장소에서만 동작한다

### 3-3. 사용 예시

```bash
# 프레임워크 마이그레이션
/batch migrate src/ from Solid to React

# API 버전 업그레이드
/batch update all API calls from v2 to v3 endpoints

# 테스트 프레임워크 변경
/batch convert all Jest tests in tests/ to Vitest

# 코딩 컨벤션 일괄 적용
/batch rename all React components from PascalCase files to kebab-case files
```

### 3-4. /simplify vs /batch 비교

| | /simplify | /batch |
|---|----------|--------|
| **목적** | 변경된 코드 정리 | 대규모 코드베이스 변경 |
| **실행 시점** | 기능 구현 후, PR 전 | 마이그레이션/리팩토링 시 |
| **병렬 단위** | 3개 리뷰 에이전트 | 5~30개 워커 에이전트 |
| **격리 방식** | 현재 브랜치에서 실행 | 개별 git worktree |
| **결과물** | 현재 코드 수정 | 워커당 개별 PR |
| **/simplify 포함** | 본인이 /simplify | 각 워커가 자동 실행 |

---

## 4. CLAUDE.md 네스팅의 숨겨진 비용

### 4-1. 문제의 배경

[이전 포스트](/posts/EvaluatingAgentsMd/)에서 컨텍스트 파일이 야기하는 **정보 중복**과 **비용 증가**를 논문 데이터로 확인했다. 이번에는 실제 Claude Code 환경에서 CLAUDE.md를 과도하게 구성할 때 발생하는 **토큰 비용**을 구체적 수치로 분석한다.

### 4-2. CLAUDE.md 로딩 메커니즘

Claude Code는 세션 시작 시 다음을 자동으로 로드한다:

```
세션 시작
    ├── CLAUDE.md (프로젝트 루트)
    ├── ~/.claude/CLAUDE.md (사용자 레벨)
    ├── 상위 디렉토리의 CLAUDE.md (재귀 탐색)
    ├── MCP 서버 도구 정의
    └── 활성화된 Skill 설명
```

**문제는 이 모든 것이 매 세션, 매 메시지에 컨텍스트로 들어간다는 것이다.**

### 4-3. 수치로 보는 낭비

커뮤니티와 공식 문서에서 보고된 수치들을 종합하면:

#### MCP 서버 토큰 오버헤드

| MCP 서버 수 | 대화 시작 전 토큰 소비 |
|------------|---------------------|
| 0개 | ~0 토큰 |
| 5개 | **~55,000 토큰** |
| 10개+ | **100,000+ 토큰** |

5개의 MCP 서버만 연결해도, 대화가 시작되기 전에 이미 **55K 토큰이 소비**된다. Jira 같은 도구 정의가 큰 서버를 추가하면 100K에 쉽게 도달한다.

> Claude Code의 Tool Search 기능은 이 문제를 46.9% 완화한다 (51K → 8.5K 토큰). 도구 설명이 컨텍스트 윈도우의 10%를 초과하면 자동으로 on-demand 로딩으로 전환된다.

#### CLAUDE.md 컨텍스트 효율성

실제 측정 사례에서 CLAUDE.md의 세션별 컨텍스트 활용률:

| 세션 유형 | 로드된 토큰 | 실제 활용 토큰 | 활용률 |
|----------|-----------|-------------|-------|
| README 오타 수정 | 2,100 | ~300 | **14%** |
| API 엔드포인트 추가 | 2,100 | ~600 | **28%** |
| 테스트 작성 | 2,100 | ~500 | **24%** |

**평균 활용률은 22% 수준**이다. 즉, CLAUDE.md에 작성한 내용의 **78%는 해당 세션에서 불필요한 토큰을 소비**하고 있다.

#### Agent Teams의 배수 효과

| 모드 | 토큰 사용 배수 | 이유 |
|------|-------------|-----|
| 단일 세션 | 1x (기준) | — |
| 서브에이전트 | 1.5~3x | 각자 컨텍스트 윈도우 유지 |
| Agent Teams (plan mode) | **~7x** | 팀원마다 독립 Claude 인스턴스 |

Agent Teams에서 팀원이 plan mode로 작동하면 **단일 세션 대비 약 7배의 토큰**을 사용한다. 여기에 과도한 CLAUDE.md가 각 팀원에게 로드되면, 낭비가 팀원 수만큼 곱해진다.

#### Auto-Compaction 오버헤드

자동 압축(auto-compact) 기능도 컨텍스트 윈도우의 일부를 소비한다. 일부 보고에 따르면, **autocompact 버퍼가 45K 토큰 — 컨텍스트 윈도우의 22.5%** — 을 사전 점유하는 경우가 있다.

### 4-4. 네스팅 패턴별 비용 분석

많은 개발자가 CLAUDE.md를 체계적으로 관리하기 위해 네스팅 패턴을 사용한다. 하지만 이 패턴에 따라 토큰 비용이 크게 달라진다.

#### 패턴 1: 모놀리식 CLAUDE.md (비권장)

```markdown
# CLAUDE.md (2,000줄+)
## 프로젝트 개요 ...
## 빌드 명령어 ...
## 코딩 컨벤션 ...
## API 문서 ...
## 데이터베이스 스키마 ...
## 배포 가이드 ...
## 테스트 전략 ...
```

- **문제**: 모든 세션에서 전체 내용 로드
- **토큰 비용**: 매 세션 ~8,000~15,000 토큰
- **활용률**: 14~28% (대부분 불필요)

#### 패턴 2: 디렉토리별 분산 (부분 개선)

```
project/
├── CLAUDE.md              # 프로젝트 전체 규칙
├── src/
│   └── CLAUDE.md          # src 관련 규칙
├── tests/
│   └── CLAUDE.md          # 테스트 관련 규칙
└── docs/
    └── CLAUDE.md          # 문서 관련 규칙
```

- **개선점**: 작업 디렉토리에 따라 관련 규칙만 추가 로드
- **남은 문제**: 루트 CLAUDE.md는 여전히 항상 로드됨
- **토큰 비용**: 3,000~8,000 토큰 (디렉토리에 따라 변동)

#### 패턴 3: Skill 기반 점진적 로딩 (권장)

```
project/
├── CLAUDE.md              # 최소한의 필수 정보만 (~500줄 이하)
└── .claude/skills/
    ├── deploy/SKILL.md    # 배포 시에만 로드
    ├── api-guide/SKILL.md # API 작업 시에만 로드
    └── db-schema/SKILL.md # DB 작업 시에만 로드
```

- **핵심**: Skill은 **호출될 때만** 전체 내용이 로드됨
- **평소에는**: Skill 설명(description)만 컨텍스트에 포함
- **토큰 절약**: **최대 82% 절약** (약 15,000 토큰/세션)

### 4-5. 최적화 전후 비교

공식 문서와 커뮤니티 보고를 종합한 최적화 효과:

| 전략 | 절약률 | 방법 |
|------|-------|------|
| CLAUDE.md → Skill 이전 | **82%** | 전문 지침을 Skill로 분리 |
| MCP Tool Search 활성화 | **46.9%** | 도구 정의 on-demand 로딩 |
| Plan mode 사용 | **40~60%** | 복잡한 작업의 탐색 비용 절감 |
| CLAUDE.md 500줄 이하 유지 | **62%** | 세션당 ~1,300 토큰 절약 |
| 전체 최적화 적용 시 | **55~70%** | 위 전략 조합 |

### 4-6. 실천 가이드: CLAUDE.md 다이어트

**CLAUDE.md에 남겨야 할 것:**

```markdown
# 빌드/실행 명령어 (프로젝트 고유)
bundle exec jekyll serve

# 프로젝트 고유의 비표준 규칙
- 번역 파일: .en.md, .ja.md 접미사 사용
- 이미지: assets/img/post/{category}/ 하위

# 특수 도구 요구사항
- Ruby 3.2 필요
- Gemfile.lock은 커밋하지 않음
```

**Skill로 옮겨야 할 것:**

```yaml
# .claude/skills/post-guide/SKILL.md
---
name: post-guide
description: 블로그 포스트 작성 가이드. 포스트 작성 시 사용.
---
## Front Matter 형식
...상세한 front matter 가이드...

## 카테고리 목록
...전체 카테고리 나열...

## 포스트 현황
...통계 데이터...
```

이렇게 하면 포스트를 작성할 때만 `/post-guide`가 로드되고, 다른 작업에서는 "블로그 포스트 작성 가이드. 포스트 작성 시 사용."이라는 한 줄 설명만 컨텍스트에 포함된다.

---

## 5. 세 가지 변화의 교차점

이번 주의 세 가지 변화는 서로 연결된다:

```
메모리 무료 개방          /simplify + /batch          CLAUDE.md 최적화
      │                         │                          │
      ▼                         ▼                          ▼
  사용자 확대  ──→  더 많은 에이전트 사용  ──→  토큰 비용 관리 중요
      │                         │                          │
      └─────────────── 결국 비용 효율의 문제 ────────────────┘
```

메모리 무료 개방으로 사용자가 늘고, `/simplify`와 `/batch` 같은 멀티에이전트 스킬이 일상이 되면, **토큰 비용 관리는 선택이 아닌 필수**가 된다. 이전 포스트에서 다뤘던 "컨텍스트 파일의 역설"이 이제 실제 비용의 문제로 확대된 것이다.

---

## 마치며

Claude 생태계의 진화 방향은 명확하다:

1. **접근성 확대**: 메모리 무료 개방, 경쟁사 전환 도구
2. **자동화 심화**: `/simplify`의 3-에이전트 리뷰, `/batch`의 병렬 마이그레이션
3. **비용 최적화 필수화**: Skill 기반 점진적 로딩, Tool Search, Plan mode

특히 CLAUDE.md를 "프로젝트의 모든 것을 담는 백과사전"처럼 쓰던 패턴은 이제 재고해야 한다. 공식 문서도 500줄 이하를 권장하며, 전문 지침은 Skill로 분리하는 것이 토큰 효율 면에서 압도적으로 유리하다.

다음에 CLAUDE.md를 수정할 때 스스로에게 물어보자: **"이 내용이 매 세션, 매 메시지에 로드될 가치가 있는가?"**

---

## References

- Anthropic. (2026). *Claude Memory - Free Plan*. [Engadget](https://www.engadget.com/ai/anthropic-brings-memory-to-claudes-free-plan-220729070.html)
- Anthropic. (2026). *Import and export your memory from Claude*. [Claude Help Center](https://support.claude.com/en/articles/12123587-import-and-export-your-memory-from-claude)
- Anthropic. (2026). *Extend Claude with skills*. [Claude Code Docs](https://code.claude.com/docs/en/skills)
- Anthropic. (2026). *Manage costs effectively*. [Claude Code Docs](https://code.claude.com/docs/en/costs)
- Boris Cherny. (2026). */simplify and /batch announcement*. [Threads](https://www.threads.com/@boris_cherny/post/DVR-HzBkqRd/)
- Joe Njenga. (2026). *Claude Code Just Cut MCP Context Bloat by 46.9%*. [Medium](https://medium.com/@joe.njenga/claude-code-just-cut-mcp-context-bloat-by-46-9-51k-tokens-down-to-8-5k-with-new-tool-search-ddf9e905f734)
- MacRumors. (2026). *Anthropic Adds Free Memory Feature and Import Tool*. [MacRumors](https://www.macrumors.com/2026/03/02/anthropic-memory-import-tool/)
- TechCrunch. (2026). *ChatGPT uninstalls surged by 295% after DoD deal*. [TechCrunch](https://techcrunch.com/2026/03/02/chatgpt-uninstalls-surged-by-295-after-dod-deal/)
- The Verge. (2026). *Anthropic upgrades Claude's memory to attract AI switchers*. [The Verge](https://www.theverge.com/ai-artificial-intelligence/887885/anthropic-claude-memory-upgrades-importing)
