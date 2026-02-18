---
title: Claude Code 완벽 가이드 - 설치부터 고급 활용 전략까지
date: 2026-02-17 14:00:00 +0900
categories: [Tool, Claude Code]
tags: [claude code, ai, llm, vibe coding, claude, anthropic, cli]
difficulty: intermediate
toc: true
toc_sticky: true
---

<br>

## Claude Code란?

**Claude Code**는 Anthropic에서 개발한 **에이전틱 코딩 도구(Agentic Coding Tool)**입니다. 터미널(CLI)에서 직접 실행되며, 자연어로 코드 작성, 리팩토링, 디버깅, git 관리 등 거의 모든 개발 작업을 수행할 수 있습니다.

기존 AI 코딩 어시스턴트(Copilot, Cursor 등)와의 가장 큰 차이점은 **프로젝트 전체를 컨텍스트로 이해**하고, 파일 시스템을 직접 읽고 쓸 수 있는 **에이전트(Agent)** 형태라는 점입니다.

<br>

---

## I. 설치 (macOS 환경)

### 방법 1: Homebrew를 통한 설치 (권장)

| 단계 | 명령어 | 설명 |
|:---:|:---|:---|
| **1** | `brew install --cask claude-code` | Homebrew로 Claude Code 설치 |
| **2** | `claude --version` | 설치 확인 및 버전 체크 |

### 방법 2: npm을 통한 설치

| 단계 | 명령어 | 설명 |
|:---:|:---|:---|
| **1** | `node --version` | Node.js 18.0 이상 확인 |
| **2** | `npm install -g @anthropic-ai/claude-code` | npm 전역 설치 |
| **3** | `claude --version` | 설치 확인 |

> Node.js가 없다면 [공식 사이트](https://nodejs.org/)에서 LTS 버전을 설치하거나, `brew install node`로 설치할 수 있습니다.
{: .prompt-tip }

<br>

---

## II. 초기 설정

### 1. 로그인

설치 후 터미널에서 로그인을 진행합니다.

```bash
claude login
```

브라우저가 열리면 Anthropic 계정으로 로그인하고, CLI tool 타입을 선택합니다.

### 2. 토큰 사용량 확인

[https://claude.ai/settings/usage](https://claude.ai/settings/usage) 에서 현재 토큰 사용량을 확인할 수 있습니다.

> **토큰(Token)이란?** LLM이 텍스트를 처리하는 최소 단위입니다. 영어 기준 약 1단어 = 1.3토큰, 한국어는 1글자 = 약 2~3토큰으로 계산됩니다. Claude Code는 **입력 토큰(프롬프트 + 컨텍스트)**과 **출력 토큰(응답)**을 모두 소비합니다.
{: .prompt-info }

<br>

---

## III. IDE 연동 (추천 환경)

터미널에서 바로 사용할 수 있지만, **IDE에 연결해서 쓰는 것을 강력히 추천**합니다. 코드 변경 사항을 실시간으로 확인할 수 있어 훨씬 효율적입니다.

### VS Code (추천)

1. [VS Code](https://code.visualstudio.com/) 설치
2. **Open Folder** 로 프로젝트 폴더 열기
3. 상단 메뉴에서 **Terminal > New Terminal** 열기
4. 터미널에 `claude` 입력하여 실행

```bash
# 프로젝트 디렉토리에서 실행
cd /path/to/your/project
claude
```

> Claude Code는 실행 시 프로젝트 루트의 `CLAUDE.md` 파일을 자동으로 읽어 프로젝트의 아키텍처, 코딩 규칙, 작업 절차를 파악합니다. 이후 요구사항에 맞춰 더 정확하고 관련성 높은 답변을 제공합니다.
{: .prompt-tip }

### JetBrains (Rider, IntelliJ 등)

JetBrains IDE의 내장 터미널에서도 동일하게 `claude` 명령어로 실행 가능합니다. 다만 개인적으로는 VS Code의 터미널 사용성이 더 좋았습니다.

<br>

---

## IV. 핵심 명령어 완전 정리

### 세션 관리 명령어

| 명령어 | 기능 | 설명 |
|:---|:---|:---|
| `claude` | Claude Code 시작 | 현재 디렉토리에서 새 세션 시작 |
| `claude -c` / `claude --continue` | 최근 세션 이어가기 | 마지막 대화를 이어서 진행 |
| `claude -r` / `claude --resume` | 이전 대화 불러오기 | 과거 세션 목록에서 선택하여 재개 |
| `claude --verbose` | 상세 로그 모드 | 디버깅 시 유용한 상세 로그 출력 |
| `claude --dangerously-skip-permissions` | 권한 확인 생략 | 모든 파일 접근/실행을 자동 허용 (주의!) |

### 세션 내 슬래시 명령어

| 명령어 | 기능 | 상세 설명 |
|:---|:---|:---|
| `/clear` | **컨텍스트 초기화** | 새로운 대화 시작. **가장 중요한 명령어.** 컨텍스트 윈도우를 충분히 확보해야 할루시네이션 가능성이 낮아집니다. 태스크 단위로 `/clear`하고 시작하는 것을 권장합니다. |
| `/compact` | 대화 압축 | 대화를 요약/압축하여 컨텍스트 윈도우를 확보합니다. `/compact 핵심 내용`처럼 특정 내용을 중심으로 압축할 수도 있습니다. |
| `/model` | 모델 변경 | Opus, Sonnet 등 모델 선택. 계획은 Opus, 구현은 Sonnet이 효율적입니다. |
| `/resume` | 이전 대화 재개 | 과거 대화를 불러올 수 있습니다. |
| `/config` | 설정 관리 | verbose, model, todo list 등 다양한 세팅 조정 |
| `/memory` | CLAUDE.md 편집 | 프로젝트/글로벌 CLAUDE.md 파일을 직접 수정 |
| `/init` | 프로젝트 초기화 | Claude가 프로젝트 전체를 분석하고 CLAUDE.md 자동 생성 |
| `/terminal-setup` | 터미널 줄바꿈 설정 | `Shift+Enter`로 줄바꿈 가능하도록 설정 |
| `/plugin` | 플러그인 관리 | 플러그인 탐색, 설치, 제거 |
| `/agents` | 에이전트 관리 | 커스텀 에이전트 확인 및 관리 |
| `/mcp` | MCP 서버 관리 | Model Context Protocol 서버 설정 |
| `/statusline` | 상태줄 설정 | 터미널 상태줄 표시 설정 |
| `/todos` | Todo 리스트 확인 | 현재 작업 목록 확인 |
| `/permissions` | 권한 관리 | bash 명령 등의 사전 허용 규칙 설정 |
| `/insights` | **사용 패턴 분석** | 최근 30일간의 세션을 분석하여 HTML 리포트 생성. 사용 패턴, 병목 지점, 워크플로우 개선 제안을 제공합니다. |
| `/fast` | **Fast 모드 토글** | 빠른 출력 모드 전환. 번개 아이콘(↯)이 표시되며 세션 간 유지됩니다. |

### 업데이트 명령어

```bash
# Claude Code 업데이트 (npm 설치인 경우)
claude update

# Homebrew로 설치한 경우
brew upgrade claude-code
```

### 특수 기능

| 기능 | 사용법 | 설명 |
|:---|:---|:---|
| **파일 참조** | `@파일명` | `@GameHandler.cs`처럼 `@`를 붙여 프로젝트 내 파일을 직접 참조할 수 있습니다. |
| **이미지 첨부** | 드래그 앤 드롭 / `Cmd+Shift+4` 후 붙여넣기 | 스크린샷이나 UI 디자인을 첨부하면 시각적 컨텍스트를 제공하여 효율이 크게 증가합니다. 공식 문서에서도 이미지 활용을 권장합니다. |
| **Rewind (되감기)** | `Esc` 2번 탭 | 현재 대화를 중지하고 이전 체크포인트로 되돌립니다. 이전 대화/코드/대화+코드 중 선택 가능합니다. 할루시네이션이 감지될 때 매우 유용합니다. |
| **모드 변경** | `Shift+Tab` | Plan 모드 / Auto-accept 모드 / 기본 모드 간 전환 |
| **Thinking 토글** | `Tab` | Extended Thinking(깊은 추론) 모드를 켜고 끕니다. 세션 간 설정이 유지됩니다. |
| **메모리 추가** | `#` 키 | CLAUDE.md에 기억할 내용을 빠르게 추가합니다. "이 규칙을 기억해줘"와 같은 용도로 활용합니다. |

<br>

---

## V. 최신 기능 (v2.1.x, 2026년 2월 기준)

Claude Code v2.1.x에서 추가된 주요 기능들입니다.

### 1. `/insights` - 사용 패턴 분석 리포트

`/insights`는 최근 30일간의 세션 데이터를 분석하여 **인터랙티브 HTML 리포트**를 생성하는 명령어입니다.

```bash
# Claude Code 세션 내에서 실행
/insights
```

**분석 대상:**
- `~/.claude/` 에 저장된 세션 기록 (프롬프트 + Claude 응답)
- 도구 사용 패턴, 에러 패턴, 인터랙션 패턴
- 소스 코드 자체는 분석하지 않음 (프라이버시 보장)

**리포트에 포함되는 내용:**

| 항목 | 설명 |
|:---|:---|
| **사용 통계** | 메시지 수, 세션 수, 파일 수정 이력 |
| **프로젝트별 분석** | 어떤 프로젝트에서 어떤 작업을 주로 했는지 |
| **도구 사용 패턴** | 어떤 도구를 가장 많이 사용했는지 차트로 시각화 |
| **언어별 사용량** | 어떤 프로그래밍 언어로 작업했는지 |
| **병목 지점** | 생산성을 떨어뜨리는 패턴 식별 |
| **개선 제안** | CLAUDE.md에 복사 가능한 맞춤 제안, Custom Skill 추천, Hook 추천 |

리포트는 `~/.claude/usage-data/report.html`에 저장되며, 자동으로 브라우저에서 열립니다.

> `/insights`의 제안은 **Copy 버튼**이 포함되어 있어 바로 CLAUDE.md에 붙여넣을 수 있습니다. 자신의 사용 패턴에 기반한 맞춤 최적화 제안이므로 매우 유용합니다.
{: .prompt-tip }

### 2. Extended Thinking & Effort 시스템

Claude Code는 **Extended Thinking(확장 추론)** 기능을 지원합니다. 이는 Claude가 응답 전에 **내부적으로 깊이 사고**하는 과정을 거치는 것으로, 복잡한 문제에서 정확도가 크게 향상됩니다.

**Thinking 토글 방법:**

| 방법 | 설명 |
|:---|:---|
| `Tab` 키 | 세션 내에서 즉시 Thinking 모드 On/Off 토글 |
| `/config` | 설정에서 Thinking 활성화/비활성화 |
| 환경변수 `MAX_THINKING_TOKENS=8000` | Thinking 토큰 예산을 직접 지정 (최소 1,024) |

**Effort 레벨 (Opus 4.6 전용):**

`/model` 명령어에서 모델 선택 시 **Effort 레벨**을 조정할 수 있습니다. 이는 Claude가 얼마나 깊이 추론할지를 제어합니다.

| Effort | 용도 | 토큰 소비 | 추천 상황 |
|:---:|:---|:---:|:---|
| **Low** | 빠른 응답, 단순 작업 | 적음 | 간단한 분류, 빠른 조회, 대량 처리 |
| **Medium** | 균형 잡힌 성능 | 보통 | 일반적인 코딩 작업 |
| **High** (기본값) | 최고 품질 추론 | 많음 | 복잡한 추론, 어려운 코딩 문제 |
| **Max** | 절대 최고 성능 | 최대 | 극도로 복잡한 아키텍처 분석, 다단계 추론 |

```bash
# Effort 레벨 환경변수로 설정
CLAUDE_CODE_EFFORT_LEVEL=high claude

# 또는 세션 내에서 /model로 변경
/model
# → 모델 선택 후 Effort 슬라이더 조정
```

> **Adaptive Thinking**: Opus 4.6에서는 `budget_tokens`를 직접 지정하는 대신 **Adaptive Thinking**이 권장됩니다. Claude가 질문의 복잡도에 따라 **동적으로** Thinking 깊이를 조절합니다. Effort 레벨을 통해 이 범위를 제어할 수 있습니다.
{: .prompt-info }

### 3. Fast 모드

**Fast 모드**는 동일한 모델을 사용하되 **출력 토큰 생성 속도를 최대 2.5배 높이는** 기능입니다. 모델이 바뀌는 것이 아니라 같은 모델의 빠른 추론 경로를 사용합니다.

```bash
# 세션 내에서 토글
/fast

# 활성화되면 번개 아이콘(↯) 표시
# 설정은 세션 간 유지됨
```

> Fast 모드는 **프리미엄 요금** ($30/$150 per MTok)이 적용됩니다. 빠른 반복이 필요한 프로토타이핑 단계에서 유용하지만, 비용을 고려하여 선택적으로 사용하세요.
{: .prompt-warning }

### 4. Agent Teams (연구 프리뷰)

**Agent Teams**는 여러 Claude Code 인스턴스가 **팀으로 협업**하는 기능입니다. 하나의 오케스트레이터가 전체 작업을 조율하고, 각 서브에이전트가 다른 부분을 병렬로 처리합니다.

```
┌─────────────────────────────┐
│      Orchestrator (리더)      │
│    전체 작업 조율 및 분배       │
└──────┬──────┬──────┬────────┘
       │      │      │
  ┌────▼──┐ ┌─▼───┐ ┌▼─────┐
  │Agent 1│ │Agent2│ │Agent3│
  │백엔드  │ │프론트│ │테스트 │
  └───────┘ └─────┘ └──────┘
```

- 각 서브에이전트는 자체 **tmux pane**에서 실행
- 독립적인 작업을 **병렬로 처리**하여 대규모 작업 속도 향상
- 현재 **연구 프리뷰** 단계 (변경될 수 있음)

### 5. Auto Memory (자동 메모리)

Claude Code가 **자동으로 세션 간 컨텍스트를 기억**하는 기능입니다. 수동 설정 없이 백그라운드에서 동작합니다.

**동작 방식:**

| 표시 | 의미 |
|:---|:---|
| `Recalled X memories` | 세션 시작 시 이전 세션의 기억을 로드함 |
| `Wrote X memories` | 세션 중 현재 작업의 스냅샷을 저장함 |

- 프로젝트 패턴, 주요 명령어, 사용자 선호도를 자동 저장
- `~/.claude/projects/<project-hash>/<session-id>/session-memory/summary.md`에 저장
- `#` 키로 CLAUDE.md에 빠르게 메모리 추가 가능

> Auto Memory는 CLAUDE.md와 별개입니다. CLAUDE.md는 사용자가 직접 관리하는 명시적 규칙이고, Auto Memory는 Claude가 자동으로 추출하는 암묵적 컨텍스트입니다. 두 가지를 함께 활용하면 가장 효과적입니다.
{: .prompt-info }

### 6. Opus 4.6 & 1M 토큰 컨텍스트 (베타)

최신 모델인 **Claude Opus 4.6**은 **1M(100만) 토큰 컨텍스트 윈도우**를 베타로 지원합니다.

| 특징 | 설명 |
|:---|:---|
| **1M 토큰 컨텍스트** | 기존 200K의 5배. 대규모 코드베이스 전체를 한 번에 분석 가능 |
| **Adaptive Thinking** | 질문 복잡도에 따라 동적으로 추론 깊이 조절 |
| **Context Compaction** | 긴 대화에서 오래된 컨텍스트를 자동 요약하여 한계 극복 |
| **Agent Teams** | 멀티에이전트 협업 지원 |

### 7. 모델별 비교 (2026년 2월 기준)

| 모델 | 컨텍스트 | 속도 | 추론 능력 | 비용 | 추천 용도 |
|:---|:---:|:---:|:---:|:---:|:---|
| **Opus 4.6** | 200K (1M 베타) | 보통 | 최강 | 높음 | 아키텍처 설계, 복잡한 리팩토링, Plan 모드 |
| **Opus 4.6 Fast** | 200K (1M 베타) | 빠름 (2.5x) | 최강 | 매우 높음 | 빠른 프로토타이핑, 반복 작업 |
| **Sonnet 4.5** | 200K | 빠름 | 우수 | 보통 | 일반 구현, 코드 작성, 디버깅 |
| **Haiku 4.5** | 200K | 매우 빠름 | 양호 | 낮음 | 간단한 작업, 대량 처리 |

> **하이브리드 전략**: Opus로 계획을 세우고(`/model` → Opus) Sonnet으로 구현(`/model` → Sonnet)하는 **opusplan** 패턴을 사용하면, Opus만 사용하는 것 대비 **60~80% 비용 절감**이 가능합니다.
{: .prompt-tip }

<br>

---

## VI. 컨텍스트 윈도우 심층 이해

Claude Code를 효과적으로 사용하려면 **컨텍스트 윈도우(Context Window)**에 대한 이해가 필수적입니다.

### 컨텍스트 윈도우란?

컨텍스트 윈도우는 LLM이 **한 번에 처리할 수 있는 토큰의 최대 크기**입니다. Claude 모델 기준으로:

| 모델 | 컨텍스트 윈도우 | 특징 |
|:---|:---|:---|
| **Claude Opus 4.6** | 200K (1M 베타) | 가장 강력한 추론, 복잡한 아키텍처 분석에 적합 |
| **Claude Sonnet 4.5** | 200K tokens | 빠른 응답, 일반 코딩 작업에 효율적 |

> **200K 토큰은 대략 어느 정도?** 영어 기준 약 15만 단어, A4 약 300페이지 분량입니다. 하지만 코드와 한국어는 토큰 효율이 낮아 실제로는 더 적습니다. 1M 토큰은 이의 약 5배인 A4 1,500페이지 분량입니다.
{: .prompt-info }

### 컨텍스트 윈도우가 중요한 이유

LLM은 매 요청이 **Stateless**합니다. 즉, Claude Code와의 새 채팅은 **매번 새 팀원과 협업하는 것**과 같습니다. 이전 대화 내용은 컨텍스트 윈도우 안에 있어야만 기억됩니다.

```
[시스템 프롬프트] + [CLAUDE.md] + [대화 이력] + [현재 질문] = 총 토큰 사용량
                                                              ↕
                                                    컨텍스트 윈도우 한계
```

컨텍스트 윈도우가 가득 차면:
1. **Auto-compact**가 발동 → 이전 대화가 자동 요약됨
2. 요약 과정에서 **정보 손실/왜곡** 발생
3. 기존 계획의 맥락이 사라질 수 있음

### Auto-Compact의 구조적 문제

Auto-compact가 실행되면 **되돌릴 수 없습니다.** 요약되면 기존 대화는 영원히 소실되며, 다음과 같은 문제가 발생합니다:

| 문제 | 설명 |
|:---|:---|
| **컨텍스트 왜곡** | 요약 과정에서 원본의 의미가 변질될 수 있음 |
| **시간적 맥락 손실** | "이전에 말한 A를 기반으로 B를 하자"와 같은 순차적 맥락이 사라짐 |
| **정보 파편화** | 연관된 정보가 분리되어 추론 품질이 저하됨 |

> Auto-compact는 대화의 "중간 지점"을 요약하는 경향이 있어, Phase 1 전체를 요약하는 게 아니라 Phase 1.2~1.5 부근을 요약해버리는 현상이 발생합니다.
{: .prompt-warning }

### 컨텍스트 관리 전략

**1. 주기적인 수동 `/compact`**
- Auto-compact에 의존하지 말고, 적절한 시기에 직접 `/compact`를 실행
- `/compact 현재 Todo 리스트와 진행 상황을 중심으로` 처럼 핵심 내용을 지정할 수 있음

**2. 태스크 단위로 `/clear`**
- 하나의 큰 작업을 여러 세션으로 분리
- 각 세션은 `/clear`로 깨끗한 컨텍스트에서 시작

**3. CLAUDE.md 활용**
- 매번 반복해야 하는 프로젝트 정보를 CLAUDE.md에 기록
- 새 세션마다 자동으로 로드되므로 컨텍스트를 아낄 수 있음

**4. 외부 문서 참조**
- 복잡한 계획은 별도의 `.md` 파일로 작성하여 `@파일명`으로 참조
- 컨텍스트 윈도우 내에 계획을 직접 유지하는 것보다 효율적

<br>

---

## VII. CLAUDE.md 파일에 대한 이해

### CLAUDE.md란?

CLAUDE.md는 프로젝트의 **"AI 온보딩 문서"**입니다. 새로운 팀원이 입사하면 프로젝트 위키를 읽듯이, Claude Code는 매 세션마다 이 파일을 읽어 프로젝트를 이해합니다.

### CLAUDE.md에 포함해야 할 내용

```markdown
# CLAUDE.md

## Project Overview
- 프로젝트 설명, 기술 스택, 아키텍처 개요

## Build & Development Commands
- 빌드, 테스트, 실행 명령어

## Code Conventions
- 코딩 스타일, 네이밍 규칙, 파일 구조

## Architecture
- 주요 디렉토리 구조, 핵심 모듈 설명

## Common Patterns
- 프로젝트에서 자주 사용하는 패턴
- "이렇게 하지 마라" 규칙 (Claude가 반복하는 실수 방지)
```

### 메모리 네스팅 (Memory Nesting)

CLAUDE.md는 [여러 계층으로 구성](https://code.claude.com/docs/en/memory#how-claude-looks-up-memories)할 수 있습니다:

| 위치 | 범위 | 용도 |
|:---|:---|:---|
| `~/.claude/CLAUDE.md` | **전역 (사용자 단위)** | 모든 프로젝트에 공통 적용되는 규칙 |
| `./CLAUDE.md` | **프로젝트 루트** | 해당 프로젝트 전체에 적용 |
| `./src/CLAUDE.md` | **하위 디렉토리** | 특정 모듈/디렉토리에만 적용 |

> `/init` 명령어로 자동 생성된 CLAUDE.md를 **그대로 사용하지 마세요.** 프로젝트의 코드 규칙, 설계 방향, 자주 하는 실수를 직접 추가하고 지속적으로 개선해야 합니다.
{: .prompt-warning }

<br>

---

## VIII. 계획-실행 워크플로우 (Plan & Execute)

### 핵심 원칙

Claude Code 활용의 핵심은 **계획(Plan)**과 **실행(Execute)** 단계를 명확히 분리하는 것입니다.

### 모델 선택 전략

| 단계 | 추천 모델 | 이유 |
|:---|:---|:---|
| **계획 수립** | Opus | 복잡한 추론, 아키텍처 분석, 전략 수립에 강함 |
| **코드 구현** | Sonnet | 빠른 응답, 비용 효율적, 단순 구현 작업에 적합 |

```
1. /model → Opus 선택
2. Shift+Tab 2번 → Plan 모드 진입
3. 계획 수립 및 Todo 리스트 작성
4. /model → Sonnet으로 변경
5. 단계별 코드 구현 진행
```

### Plan 모드 기반 워크플로우

**1단계: 탐색 및 계획 수립 (Explore & Plan)**

Plan 모드(`Shift+Tab` 2번)에서 시작합니다:

- 구현 전략 수립
- 작업을 **독립적으로 테스트 가능한 단계**로 분해
- 예상 소요 시간 추정
- UI/라이브러리 관련 사항 포함

> 상세한 프롬프팅이 핵심입니다. "이 기능을 구현하기 위한 작업을 단계별로 나눠줘. 각 단계는 독립적으로 테스트 가능해야 하고, 예상 소요 시간도 추정해줘"와 같이 구체적으로 지시합니다.
{: .prompt-tip }

**2단계: 계획 확정 및 실행**

계획이 만족스러워지면:
1. `Shift+Tab`으로 **Auto-accept edits 모드** 전환
2. Claude가 계획에 따라 **한 번에(1-shot) 구현** 진행

**Plan 모드의 장점:**

| 장점 | 설명 |
|:---|:---|
| **컨텍스트 지속** | Plan 모드의 Todo 리스트는 세션이 길어져도 유지되어, 작업의 연속성이 보장됩니다. |
| **동적 계획 수정** | 구현 중 빠진 부분이 있으면 계획을 즉시 수정할 수 있습니다. |
| **할루시네이션 감소** | 명확한 계획이 있으면 Claude가 엉뚱한 방향으로 가는 것을 방지합니다. |

> 가능하면 `.md` 형태로 현재 작업 중인 태스크의 체크 리스트 문서를 만들어서, 지속적으로 업데이트하도록 유도하는 것이 좋습니다.
{: .prompt-tip }

### PRD(Product Requirements Document) 활용

단순히 Plan 모드로 Todo 리스트를 작성하는 것도 좋지만, **대규모 작업이나 리팩토링**에서는 PRD를 활용하는 것이 효과적입니다.

PRD에는 다음을 포함합니다:
- **목표 및 배경**: 왜 이 작업이 필요한가
- **요구사항**: 기능적/비기능적 요구사항
- **범위**: 포함/미포함 사항
- **설계 방향**: 아키텍처 결정사항
- **성공 기준**: 완료 조건

<br>

---

## IX. 안전성 및 제어 (Safety & Control)

### 권한 모드 이해

| 모드 | 설명 | 사용 시기 |
|:---|:---|:---|
| **기본 모드** | 파일 수정/명령 실행 시 매번 승인 필요 | 중요 프로젝트, 학습 단계 |
| **Auto-accept** | 파일 수정은 자동 승인 | 계획이 확정된 후 구현 단계 |
| **dangerously-skip-permissions** | 모든 권한 자동 승인 | 샌드박스 환경에서만 사용 권장 |

### `/permissions`를 통한 세밀한 제어

`--dangerously-skip-permissions` 대신 `/permissions`로 자주 사용하는 안전한 명령만 사전 허용하는 것이 권장됩니다.

```bash
# .claude/settings.json에 저장되어 팀과 공유 가능
# 예: git, npm, build 명령은 사전 허용
```

### 안전한 사용 원칙

1. **처음에는 승인 모드**로 하나씩 확인하면서 진행
2. 계획이 확정되면 Auto-accept으로 전환
3. 기능 구현이 예상과 다르면 `Esc 2번`(Rewind)으로 되돌리기
4. 계획 자체가 잘못되었다면 Plan을 수정

<br>

---

## X. 13가지 고급 활용 팁 (Claude Code 창시자의 워크플로우)

Claude Code 개발자가 직접 공유한 실전 팁입니다.

### 1. 병렬 실행 환경 구성

터미널에서 **5개의 Claude를 병렬 실행**합니다. 탭에 1~5 번호를 붙이고, [시스템 알림](https://code.claude.com/docs/en/terminal-config#iterm-2-system-notifications)으로 입력이 필요한 시점을 파악합니다.

### 2. 웹과 로컬의 병렬 운영

- `claude.ai/code` 웹에서도 **5~10개의 Claude를 추가로 병렬 실행**
- 로컬 세션을 웹으로 핸드오프(`&` 사용)하거나, `-teleport`로 양방향 전환
- iOS 앱에서 세션을 시작하고 나중에 확인하는 방식도 활용

### 3. 모델 선택: Opus with thinking

- 모든 작업에 **Opus 4 with thinking** 사용
- Sonnet보다 크고 느리지만, **조정(steering)이 적게 필요**하고 **도구 활용 능력이 뛰어남**
- 결과적으로 작은 모델보다 **거의 항상 더 빠른** 최종 결과 도출

### 4. CLAUDE.md를 통한 팀 단위 지식 축적

- 팀 전체가 공유하는 **단일 CLAUDE.md 파일** 유지
- git에 체크인하며, 팀 전체가 **주 단위로 여러 번 기여**
- Claude가 잘못된 행동을 할 때마다 추가해 **다음에 같은 실수 방지**

### 5. 코드 리뷰 시 CLAUDE.md 업데이트

- 코드 리뷰 시 동료 PR에 **@.claude를 태그**해 CLAUDE.md에 내용 추가
- **Claude Code GitHub Action**(`/install-github-action`) 활용

### 6. Plan 모드와 자동 수락 워크플로우

- 대부분의 세션을 **Plan 모드**(`Shift+Tab` 2번)로 시작
- 계획이 만족스러워질 때까지 반복 협의
- 확정 후 **Auto-accept 모드**로 전환하면 **한 번에(1-shot) 완성**
- **좋은 계획이 정말 중요**

### 7. 슬래시 커맨드로 반복 작업 자동화

- 자주 수행하는 "inner loop" 워크플로우마다 슬래시 커맨드 사용
- `.claude/commands/` 디렉토리에 저장되며 git에 체크인
- 예: `/commit-push-pr` 슬래시 커맨드를 매일 수십 번 사용
- [인라인 bash](https://code.claude.com/docs/en/slash-commands#bash-command-execution)로 git status 등을 미리 계산해 불필요한 모델 왕복 방지

### 8. 서브에이전트 활용

여러 [서브에이전트](https://code.claude.com/docs/en/sub-agents)를 정기적으로 사용:
- **code-simplifier**: 작업 완료 후 코드 단순화
- **verify-app**: 엔드투엔드 테스트를 위한 상세 지침

### 9. PostToolUse 훅으로 코드 포매팅

- **PostToolUse 훅**을 사용해 코드 포매팅 자동 처리
- Claude가 기본적으로 잘 포매팅된 코드를 생성하며, 훅이 **나머지 10%를 처리**

### 10. 권한 관리 방식

- `--dangerously-skip-permissions` 사용하지 않음
- 대신 `/permissions`로 안전한 bash 명령을 **사전 허용**
- `.claude/settings.json`에 체크인하여 팀과 공유

### 11. 도구 통합 활용

Claude Code가 **외부 도구를 대신 사용**:
- **Slack** 검색 및 게시 (MCP 서버 활용)
- **BigQuery** 쿼리 실행 (bq CLI)
- **Sentry**에서 에러 로그 가져오기
- MCP 설정은 `.mcp.json`에 체크인하여 팀과 공유

### 12. 장시간 작업 처리 방식

매우 긴 작업의 경우 세 가지 방법 중 선택:
- **(a)** 완료 시 **백그라운드 에이전트**로 작업 검증하도록 프롬프트
- **(b)** [에이전트 Stop 훅](https://code.claude.com/docs/en/hooks-guide)을 사용해 더 결정론적으로 검증
- **(c)** [ralph-wiggum 플러그인](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/ralph-wiggum) 사용

### 13. 가장 중요한 팁: 검증 피드백 루프

> Claude Code에서 훌륭한 결과를 얻기 위한 **가장 중요한 요소**: Claude에게 **작업을 검증할 방법을 제공**하는 것입니다.
{: .prompt-warning }

이 피드백 루프가 있으면 최종 결과물 품질이 **2~3배 향상**됩니다:
- bash 명령 실행으로 결과 확인
- 테스트 스위트 실행
- 브라우저나 시뮬레이터에서 앱 테스트
- [Chrome 확장 프로그램](https://code.claude.com/docs/en/chrome)으로 UI 테스트

**검증 과정을 견고하게 구축하는 데 투자하는 것이 가장 가치 있는 일입니다.**

<br>

---

## XI. SDD (Spec-Driven Development)

### SDD란?

SDD(Spec-Driven Development)는 "Claude에게 말로 시키는 개발"에서 벗어나, **팀이 공유하는 테크 스펙을 기준으로 AI가 구현/테스트까지 수행하는 개발 방식**입니다.

**SDD의 핵심 가치:**
- 컨텍스트 유실 최소화
- 할루시네이션 감소
- 팀 협업 효율화

### Spec Kit 설치 및 사용

[Spec Kit](https://github.com/github/spec-kit)은 SDD를 실현하기 위한 도구입니다.

```bash
# Spec Kit 초기화
specify init --here
# → 'y' 입력
# → 'claude' 선택
# → 'sh' 선택
```

설치 후 새 세션에서 claude를 실행하면 새로운 명령어들이 추가됩니다.

### Spec Kit 워크플로우

| 명령어 | 단계 | 설명 |
|:---|:---|:---|
| `/speckit.constitution` | 규약 설정 | CLAUDE.md 및 프로젝트 코드 룰, 아키텍처 기반 규약 |
| `/speckit.specify` | 요구사항 정의 | **What/Why** 기반. 기술 스택은 쓰지 않음 |
| `/speckit.clarify` | 상세화 | 부족한 기술서 보완 |
| `/speckit.plan` | 계획 수립 | 기술 스택/아키텍처를 이 단계에서 결정 |
| `/speckit.tasks` | 태스크 분해 | 구현 가능한 단위로 분해 |
| `/speckit.implement` | 구현 | 실제 코드 작성 |
| `/speckit.analyze` | 분석 (옵션) | 문서 간 일관성 점검 |
| `/speckit.checklist` | 체크리스트 (옵션) | 품질 체크 |

### `/speckit.specify` 작성 가이드

`specify`는 **무엇을 만들지(What/Why)**를 쓰는 단계입니다. 구현 방법(How)은 `/speckit.plan`에서 다룹니다.

**WHAT (요구사항)**
- 사용자가 할 수 있어야 하는 일 (행동)
- 시스템이 보장해야 하는 규칙 (검증/제약/호환성)
- 산출물 (에셋, 프리팹, 등록, 테스트 환경)
- 성공 기준 (시간 제약, 레거시 호환 등)

**WHY (필요성)**
- 기존 문제 (병목, 중복, 불일치, 컨텍스트 유실)
- 성공지표에의 기여도

**작성 금지 사항 (이건 `/plan`에서)**
- ~~"BaseWeapon에 DI 컨테이너를 넣고..."~~
- ~~"BulletRecipe를 ScriptableObject로 만들고..."~~
- ~~"ECS로 최적화하고..."~~

<br>

---

## XII. 플러그인 활용

### 플러그인 설치 방법

```bash
# Claude Code 실행 후
claude

# 마켓플레이스에서 플러그인 다운로드
/plugin marketplace add wshobson/agents

# 원하는 플러그인 선택적 설치
/plugin install game-development
/plugin install debugging-toolkit
/plugin install code-refactoring
```

[wshobson/agents](https://github.com/wshobson/agents/tree/main) 저장소에는 오케스트레이션을 통해 최적화된 다양한 에이전트가 포함되어 있습니다.

### 플러그인 동작 방식

설치된 플러그인은 **자동으로 상황에 맞게 활용**됩니다:

- **자동 활용**: 작업 특성에 맞으면 자동으로 해당 에이전트가 동작
  - 코드 작성 후 → code-reviewer 에이전트
  - 에러 발생 시 → debugger 에이전트
- **명시적 요청**: "코드 리뷰해줘" → code-reviewer 활성화
- **상황 판단**: 단순 작업에는 별도 에이전트 없이 직접 처리

<br>

---

## XIII. 주의사항

### Unity 연동 제한

현재 Claude Code와 Unity 에디터 간 직접 연결 수단이 없습니다. 이로 인해 Unity 에디터의 에러 코드를 정확히 인지하지 못하는 경우가 있습니다. 다만 **로직 에러 분석이나 코드 의도 파악 성능은 뛰어납니다.**

> Unity-MCP라는 도구가 존재하지만, 보안 취약점이 있으므로 사용 전 반드시 보안 검토를 진행하세요.
{: .prompt-danger }

### MCP 서버 사용 시 주의

MCP(Model Context Protocol) 서버를 사용할 때는:
- 신뢰할 수 있는 소스인지 반드시 확인
- 보안 취약점이 없는지 검토
- 팀에서 사용하는 경우 화이트리스트 관리 권장

<br>

---

## 참고 자료

- [Claude Code 공식 문서](https://code.claude.com/docs)
- [Spec Kit (GitHub)](https://github.com/github/spec-kit)
- [wshobson/agents 플러그인 모음](https://github.com/wshobson/agents/tree/main)
- [Claude Code 메모리 시스템](https://code.claude.com/docs/en/memory#how-claude-looks-up-memories)
- [Claude Code 훅 가이드](https://code.claude.com/docs/en/hooks-guide)
- [Claude Code 슬래시 커맨드](https://code.claude.com/docs/en/slash-commands#bash-command-execution)
- [Claude Code 서브에이전트](https://code.claude.com/docs/en/sub-agents)
