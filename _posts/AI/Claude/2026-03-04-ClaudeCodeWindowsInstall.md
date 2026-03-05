---
title: "Windows에서 Claude Code 설치 완전 가이드 — 실전 트러블슈팅 포함"
date: 2026-03-04 16:00:00 +0900
categories: [AI, Claude]
tags: [Claude Code, Windows, 설치 가이드, PowerShell, Node.js, Git, Developer Tools, AI]

difficulty: beginner
toc: true
toc_sticky: true
prerequisites:
  - /posts/ClaudeCodeInsights/
tldr:
  - "Windows 11에서 Claude Code를 설치하려면 Node.js LTS, Git, Git Bash 경로 환경 변수 설정이 필요하다 — Quick Start 5단계로 완료 가능"
  - "설치 후 가장 흔한 실패 원인은 터미널 미재시작(PATH 미갱신)과 CLAUDE_CODE_GIT_BASH_PATH 환경 변수 누락이다"
  - "PowerShell 진단 스크립트 한 번이면 현재 환경의 문제점을 한눈에 파악할 수 있다"
---

## 들어가며

Claude Code는 Anthropic이 제공하는 CLI 기반 AI 코딩 에이전트다. macOS/Linux에서는 설치가 비교적 간단하지만, **Windows에서는 Git Bash 경로 설정, PowerShell 실행 정책, PATH 문제** 등 여러 단계에서 막힐 수 있다.

이 글은 Windows 환경에서 Claude Code를 설치하며 **실제로 겪은 문제들과 해결 방법**을 정리한 실전 가이드다. Quick Start로 빠르게 설치하거나, 문제가 생기면 단계별 상세 가이드를 참고하면 된다.

---

## 1. 검증된 환경

| 항목 | 버전/값 |
|------|--------|
| OS | Windows 11 Home (10.0.26200) |
| Node.js | v24.12.0 (LTS) |
| npm | 11.6.2 |
| Git | 2.51.0.windows.2 |
| Claude Code | @anthropic-ai/claude-code@**2.1.63** |
| 기본 모델 | Claude Opus 4.6 (`claude-opus-4-6`) |

### 사용 가능한 Claude 모델

| 모델 | 모델 ID | 특징 |
|------|---------|-----|
| **Opus 4.6** | `claude-opus-4-6` | 가장 강력, 복잡한 작업에 적합 **(기본값)** |
| Sonnet 4.6 | `claude-sonnet-4-6` | 빠른 응답, 일반 작업에 적합 |
| Haiku 4.5 | `claude-haiku-4-5-20251001` | 가장 빠름, 간단한 작업에 적합 |

---

## 2. Quick Start (5단계)

이미 Node.js와 Git이 설치되어 있다면, 아래 5단계로 바로 설치할 수 있다. 문제가 발생하면 [단계별 상세 가이드](#3-단계별-상세-가이드)를 참고하자.

### 사전 확인

PowerShell을 열고 아래 명령어로 현재 상태를 확인한다:

```powershell
node -v          # 버전 나오면 → Step 2에서 Node.js 건너뛰기
npm -v           # 버전 나오면 → npm 정상
git --version    # 버전 나오면 → Step 2에서 Git 건너뛰기
claude --version # 버전 나오면 → 이미 설치됨! "업그레이드" 섹션만 참고
```

### Step 1. 실행 정책 설정 (최초 1회)

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
```

### Step 2. 필수 프로그램 설치

```powershell
winget install -e --id OpenJS.NodeJS.LTS
winget install -e --id Git.Git
```

> **설치 후 반드시 PowerShell 터미널을 완전히 닫고 새로 열어야 한다.** 새 터미널을 열어야 PATH가 갱신되어 `node`, `git` 명령어를 인식한다.
{: .prompt-warning }

### Step 3. Git Bash 경로 환경 변수 설정 (최초 1회)

```powershell
[Environment]::SetEnvironmentVariable("CLAUDE_CODE_GIT_BASH_PATH", "C:\Program Files\Git\bin\bash.exe", "User")
```

> 마지막 인자 `"User"`는 실제 사용자 이름이 아니다. Windows 환경 변수의 **적용 범위(Scope)**를 의미하는 키워드다. 자신의 사용자 이름으로 바꾸면 안 된다.
{: .prompt-info }

### Step 4. Claude Code 설치

```powershell
# 방법 A: 공식 스크립트 (권장)
irm https://claude.ai/install.ps1 | iex

# 방법 B: npm 직접 설치 (방법 A가 안 될 때)
npm install -g @anthropic-ai/claude-code
```

### Step 5. 설치 확인

```powershell
claude --version
# 예: 2.1.63 (Claude Code) ← 버전 번호가 나오면 성공!
```

---

## 3. 단계별 상세 가이드

Quick Start에서 문제가 생겼다면, 이 섹션에서 각 단계의 상세한 트러블슈팅을 확인하자.

### 3-1. PowerShell 실행 정책 설정

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
```

설정 확인:

```powershell
Get-ExecutionPolicy -List
# CurrentUser 항목이 RemoteSigned여야 함
```

| 정책 | 설명 | 권장 |
|------|------|-----|
| Restricted | 모든 스크립트 차단 (Windows 기본값) | |
| **RemoteSigned** | 로컬 스크립트 허용, 원격은 서명 필요 | **권장** |
| Unrestricted | 모든 스크립트 허용 | 보안 위험 |

**왜 필요한가?** Windows는 기본적으로 PowerShell 스크립트 실행을 차단(`Restricted`)한다. Claude Code 설치 스크립트를 실행하려면 이 정책을 `RemoteSigned`로 변경해야 한다.

---

### 3-2. Node.js 설치

```powershell
winget install -e --id OpenJS.NodeJS.LTS
```

설치 확인 (새 터미널에서):

```powershell
node -v  # 예: v24.12.0
npm -v   # 예: 11.6.2
```

#### winget이 안 될 때

winget이 없는 구버전 Windows라면 수동 설치:

1. [https://nodejs.org/](https://nodejs.org/) 접속
2. LTS 버전 다운로드
3. 설치 파일(.msi) 실행
4. 기본 옵션으로 설치
5. 터미널 새로 열기

#### `node -v`에서 "명령어를 찾을 수 없음"

**원인:** PATH에 Node.js 경로가 등록되지 않았다.

**해결 순서:**

1. 터미널을 완전히 닫고 새로 열기
2. 그래도 안 되면 시스템 재부팅
3. 그래도 안 되면 수동 PATH 추가:
   - 시작 → "환경 변수" 검색 → "사용자 환경 변수"
   - Path 편집 → `C:\Program Files\nodejs\` 추가

---

### 3-3. Git 설치

```powershell
winget install -e --id Git.Git
```

설치 확인:

```powershell
git --version  # 예: git version 2.51.0.windows.2
```

#### winget이 안 될 때

1. [https://gitforwindows.org/](https://gitforwindows.org/) 접속
2. 다운로드 후 설치 파일 실행
3. 설치 옵션에서 기본값 유지 (Git Bash 포함 설치됨)
4. 터미널 새로 열기

---

### 3-4. Git Bash 경로 환경 변수 설정

**왜 필요한가?** Claude Code는 내부적으로 bash 쉘을 사용한다. Windows에서는 Git Bash를 사용하는데, 자동으로 경로를 찾지 못하는 경우가 있어서 직접 지정해야 한다.

```powershell
[Environment]::SetEnvironmentVariable("CLAUDE_CODE_GIT_BASH_PATH", "C:\Program Files\Git\bin\bash.exe", "User")
```

설정 확인 (새 터미널에서):

```powershell
echo $env:CLAUDE_CODE_GIT_BASH_PATH
# 예: C:\Program Files\Git\bin\bash.exe
```

> `"User"` 파라미터 설명
>
> | 값 | 의미 | 비고 |
> |---|------|-----|
> | `"User"` | 현재 로그인한 사용자 환경 변수 | **권장 (그대로 사용)** |
> | `"Machine"` | 시스템 전체 환경 변수 | 관리자 권한 필요 |
> | `"Process"` | 현재 터미널 세션에서만 유효 | 터미널 닫으면 사라짐 |
{: .prompt-info }

#### Git이 다른 경로에 설치된 경우

```powershell
# Git 설치 위치 확인
where git
# 예: C:\Program Files\Git\cmd\git.exe
# → bash.exe는 같은 Git 폴더의 bin 안에 있음

# 일반적인 Git Bash 경로:
# C:\Program Files\Git\bin\bash.exe        ← 64비트 (대부분)
# C:\Program Files (x86)\Git\bin\bash.exe  ← 32비트

# 확인된 경로로 환경 변수 설정
[Environment]::SetEnvironmentVariable("CLAUDE_CODE_GIT_BASH_PATH", "실제_경로", "User")
```

#### WSL을 사용하는 경우 (대안)

```powershell
wsl --install  # WSL 설치 (최초 1회, 재부팅 필요)
```

WSL로도 가능하지만, Git Bash 경로 설정이 더 간단하므로 **Git Bash 방식을 권장**한다.

---

### 3-5. Claude Code 설치

#### 방법 A: 공식 설치 스크립트 (권장)

```powershell
irm https://claude.ai/install.ps1 | iex
```

위 명령이 안 될 때:

```powershell
# 변형 1: scriptblock으로 실행
& ([scriptblock]::Create((irm https://claude.ai/install.ps1))) latest

# 변형 2: CMD 스크립트 사용
curl -fsSL https://claude.ai/install.cmd -o install.cmd && install.cmd && del install.cmd
```

#### 방법 B: npm 직접 설치 (방법 A 실패 시)

```powershell
npm install -g @anthropic-ai/claude-code
```

> npm 명령어 문법에 주의하자:
> ```powershell
> npm install -g 패키지명    # ✅ 올바른 문법
> npm i -g 패키지명          # ✅ 축약형
> npm --install 패키지명     # ❌ 잘못된 문법
> npm -install 패키지명      # ❌ 잘못된 문법
> ```
{: .prompt-warning }

---

### 3-6. 설치 확인 및 PATH 문제 해결

```powershell
claude --version
# 예: 2.1.63 (Claude Code)
```

#### `claude` 명령어를 찾을 수 없을 때

```powershell
# 1. 터미널을 닫고 새로 열기

# 2. npm 글로벌 경로 확인
npm config get prefix
# 예: C:\Users\사용자명\AppData\Roaming\npm

# 3. 해당 경로가 PATH에 있는지 확인
echo $env:PATH

# 4. PATH에 없으면 추가 ($env:USERPROFILE로 사용자 경로 자동 완성)
[Environment]::SetEnvironmentVariable(
  "Path",
  [Environment]::GetEnvironmentVariable("Path", "User") + ";$env:USERPROFILE\AppData\Roaming\npm",
  "User"
)

# 5. 터미널 새로 열고 다시 시도
claude --version
```

#### Windows 사용자 이름 확인법

경로에서 `사용자명`을 직접 타이핑해야 하는 경우:

```powershell
# 방법 1: 사용자 프로필 폴더 전체 경로
echo $env:USERPROFILE
# 예: C:\Users\홍길동  ← "홍길동"이 사용자 이름

# 방법 2: 사용자 이름만
echo $env:USERNAME
# 예: 홍길동

# 방법 3: whoami
whoami
# 예: DESKTOP-ABC123\홍길동  ← "\" 뒤가 사용자 이름
```

> `$env:USERPROFILE`을 활용하면 사용자 이름을 몰라도 경로를 자동으로 완성할 수 있으므로, 가능하면 직접 타이핑 대신 이 변수를 사용하자.
{: .prompt-tip }

---

## 4. 설치 후 설정

### 설정 파일 위치

| 파일 | 경로 | 용도 |
|------|------|-----|
| 글로벌 설정 | `%USERPROFILE%\.claude\settings.json` | 언어, 상태표시줄 등 |
| 프로젝트 설정 | `프로젝트폴더\.claude\settings.local.json` | 프로젝트별 권한 등 |
| 프로젝트 컨텍스트 | `프로젝트폴더\CLAUDE.md` | AI에게 전달할 규칙/지침 |

### 글로벌 설정 예시

`%USERPROFILE%\.claude\settings.json`:

```json
{
  "statusLine": {
    "type": "command",
    "command": "bash ~/.claude/statusline-command.sh"
  },
  "language": "Korean"
}
```

`"language": "Korean"` 설정으로 Claude Code가 한국어로 응답한다.

---

## 5. Claude Code 기본 사용법

### 실행 명령어

```powershell
# 프로젝트 폴더에서 대화형 세션 시작
cd C:\MyProject
claude

# 한 줄 질문 (대화형 세션 없이 바로 답변)
claude -p "이 코드의 버그를 찾아줘"

# 파이프로 입력 전달
cat main.cpp | claude -p "이 코드를 리뷰해줘"

# 특정 모델로 실행
claude --model claude-sonnet-4-6

# 이전 대화 이어서 하기
claude --continue

# 가장 최근 대화 이어서 하기
claude --resume
```

### 대화 중 슬래시 명령어

| 명령어 | 설명 |
|--------|------|
| `/help` | 도움말 표시 |
| `/model` | 모델 확인/변경 |
| `/compact` | 대화 컨텍스트 압축 (긴 대화에서 유용) |
| `/clear` | 대화 초기화 |
| `/cost` | 현재 세션 비용 확인 |
| `/fast` | Fast 모드 토글 (같은 모델, 더 빠른 출력) |
| `/commit` | 변경사항 Git 커밋 생성 |
| `/simplify` | 변경 코드 자동 리뷰 및 개선 |
| `/batch` | 대규모 코드베이스 병렬 변경 |

> `/simplify`와 `/batch`에 대한 자세한 설명은 [Claude 메모리 무료 개방과 /simplify, /batch](/posts/ClaudeMemoryAndCodeSkills/) 포스트를 참고하자.
{: .prompt-info }

---

## 6. 업그레이드

### 방법 A: npm update (권장)

```powershell
npm update -g @anthropic-ai/claude-code
```

### 방법 B: 최신 버전 강제 설치

```powershell
npm install -g @anthropic-ai/claude-code@latest
```

업그레이드 후 확인:

```powershell
# 새 터미널을 열고
claude --version

# 기존 설정 파일은 자동으로 유지된다.
```

---

## 7. 전체 진단 스크립트

어디서 문제가 발생했는지 모를 때, 이 스크립트를 PowerShell에 붙여넣으면 환경 전체를 한번에 진단할 수 있다.

```powershell
Write-Host "=== Claude Code 환경 진단 ===" -ForegroundColor Cyan

Write-Host "`n[Node.js]" -ForegroundColor Yellow
try { node -v } catch { Write-Host "  ❌ 미설치" -ForegroundColor Red }

Write-Host "`n[npm]" -ForegroundColor Yellow
try { npm -v } catch { Write-Host "  ❌ 미설치" -ForegroundColor Red }

Write-Host "`n[Git]" -ForegroundColor Yellow
try { git --version } catch { Write-Host "  ❌ 미설치" -ForegroundColor Red }

Write-Host "`n[Git Bash 경로]" -ForegroundColor Yellow
$gitBash = [Environment]::GetEnvironmentVariable("CLAUDE_CODE_GIT_BASH_PATH", "User")
if ($gitBash) { Write-Host "  $gitBash" } else { Write-Host "  ❌ 미설정" -ForegroundColor Red }

Write-Host "`n[실행 정책]" -ForegroundColor Yellow
Get-ExecutionPolicy -Scope CurrentUser

Write-Host "`n[Claude Code]" -ForegroundColor Yellow
try { claude --version } catch { Write-Host "  ❌ 미설치" -ForegroundColor Red }

Write-Host "`n[npm 글로벌 경로]" -ForegroundColor Yellow
npm config get prefix
```

실행 결과 예시:

```
=== Claude Code 환경 진단 ===

[Node.js]
v24.12.0

[npm]
11.6.2

[Git]
git version 2.51.0.windows.2

[Git Bash 경로]
  C:\Program Files\Git\bin\bash.exe

[실행 정책]
RemoteSigned

[Claude Code]
2.1.63 (Claude Code)

[npm 글로벌 경로]
C:\Users\사용자명\AppData\Roaming\npm
```

모든 항목이 정상이면 설치 완료다. 빨간색 `❌`이 보이면 해당 섹션의 트러블슈팅을 참고하자.

---

## 8. 트러블슈팅 요약

| 증상 | 원인 | 해결 |
|------|------|------|
| `node -v` 안 됨 | Node.js 미설치 또는 PATH 미등록 | [3-2. Node.js 설치](#3-2-nodejs-설치) |
| `irm ... \| iex` 차단됨 | 실행 정책 Restricted | [3-1. 실행 정책 설정](#3-1-powershell-실행-정책-설정) |
| `npm --install` 오류 | 잘못된 npm 문법 | `npm install -g` 사용 |
| `claude` 실행 시 쉘 오류 | Git Bash 경로 미설정 | [3-4. Git Bash 경로 설정](#3-4-git-bash-경로-환경-변수-설정) |
| `claude` 명령어 없음 | npm 글로벌 경로 미등록 | [3-6. PATH 문제 해결](#3-6-설치-확인-및-path-문제-해결) |
| 모든 명령어 안 됨 | 터미널 재시작 안 함 | **터미널 닫고 새로 열기** |

---

## 파일 경로 요약

| 항목 | 경로 |
|------|------|
| Claude 실행 파일 | `%USERPROFILE%\AppData\Roaming\npm\claude.cmd` |
| npm 글로벌 패키지 | `%USERPROFILE%\AppData\Roaming\npm\` |
| Claude 글로벌 설정 | `%USERPROFILE%\.claude\settings.json` |
| Claude 프로젝트 설정 | `프로젝트\.claude\settings.local.json` |
| Git Bash | `C:\Program Files\Git\bin\bash.exe` |

---

## 마치며

Windows에서 Claude Code를 설치할 때 가장 많이 막히는 세 가지:

1. **터미널 미재시작** — PATH가 갱신되지 않아 설치한 프로그램을 인식하지 못함
2. **`CLAUDE_CODE_GIT_BASH_PATH` 미설정** — Claude Code가 bash를 찾지 못해 실행 실패
3. **`"User"` 파라미터 혼동** — 환경 변수 Scope 키워드를 자신의 사용자 이름으로 착각

이 세 가지만 주의하면 대부분의 설치 문제를 해결할 수 있다. 문제가 생기면 [진단 스크립트](#7-전체-진단-스크립트)를 먼저 돌려보자.

---

## References

- Anthropic. (2026). *Claude Code Documentation*. [https://docs.anthropic.com/en/docs/claude-code](https://docs.anthropic.com/en/docs/claude-code)
- Anthropic. (2026). *Claude Code GitHub*. [https://github.com/anthropics/claude-code](https://github.com/anthropics/claude-code)
- Node.js. *Node.js 공식 사이트*. [https://nodejs.org/](https://nodejs.org/)
- Git for Windows. *Git for Windows*. [https://gitforwindows.org/](https://gitforwindows.org/)
