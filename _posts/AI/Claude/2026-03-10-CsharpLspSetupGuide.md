---
title: "macOS에서 Claude Code C# LSP 완벽 세팅 가이드 — csharp-ls 설치부터 트러블슈팅까지"
date: 2026-03-10 10:00:00 +0900
categories: [AI, Claude]
tags: [Claude Code, C#, LSP, csharp-ls, dotnet, macOS, 개발환경, AI]
difficulty: beginner
toc: true
toc_sticky: true
prerequisites:
  - /posts/ClaudeCodeInsights/
tldr:
  - "Claude Code에서 C# LSP를 사용하려면 .NET SDK + csharp-ls + 환경변수 2줄 + 플러그인 활성화, 이 4가지만 갖추면 된다"
  - "설치 실패의 90%는 DOTNET_ROOT 환경변수 미설정이 원인이다 — Apple Silicon과 Intel Mac의 경로가 다르다"
  - "프로젝트 루트에 .sln 파일이 없으면 csharp-ls가 심볼을 인덱싱하지 못한다"
---

## 들어가며

Claude Code는 다양한 언어의 LSP(Language Server Protocol)를 지원하여 코드 분석, 심볼 탐색, 리팩토링 등을 수행할 수 있다. 그중 **C# LSP는 Unity, .NET 프로젝트에서 코드 품질을 높이는 데 핵심적인 도구**다.

하지만 macOS에서 C# LSP를 설정하는 과정은 Windows보다 까다롭다. .NET SDK 경로, 환경변수, 플러그인 활성화 등 **여러 단계에서 막힐 수 있는 포인트**가 존재한다.

이 글은 macOS에서 Claude Code의 C# LSP(csharp-ls)를 설치하며 **실제로 겪은 문제들과 해결 방법**을 정리한 실전 가이드다. Quick Start로 빠르게 설치하거나, 문제가 생기면 수동 설정 가이드를 참고하면 된다.

---

## 1. 검증된 환경

| 항목 | 값 |
|------|-----|
| macOS | Sequoia 26.1 |
| Architecture | arm64 (Apple Silicon) |
| Rosetta | 설치됨 |
| .NET SDK | 10.0.101 (Homebrew) |
| csharp-ls | 0.22.0 |
| Claude Code | 최신 버전 |

---

## 2. Quick Start (6단계)

이미 Homebrew가 설치되어 있다면, 아래 6단계로 바로 설치할 수 있다. 문제가 발생하면 [수동 설정 가이드](#4-수동-설정-가이드)를 참고하자.

### 사전 확인

터미널을 열고 현재 상태를 확인한다:

```bash
dotnet --version     # 버전 나오면 → Step 1 건너뛰기
csharp-ls --version  # 버전 나오면 → Step 2 건너뛰기
echo $DOTNET_ROOT    # 경로 나오면 → Step 3 건너뛰기
```

### Step 1. .NET SDK 설치

```bash
brew install dotnet
```

설치 후 확인:

```bash
dotnet --version
# 출력: 10.0.101
```

### Step 2. csharp-ls 설치

```bash
dotnet tool install --global csharp-ls
```

설치 후 확인:

```bash
csharp-ls --version
# 출력: 0.22.0
```

> `csharp-ls: command not found`가 뜨면 Step 3의 PATH 설정을 먼저 진행하자.
{: .prompt-tip }

### Step 3. 환경변수 설정 (.zshrc)

**이 단계가 가장 중요하다.** `~/.zshrc` 파일에 아래 2줄을 추가한다:

```bash
# Apple Silicon Mac (M1/M2/M3/M4)
export DOTNET_ROOT="/opt/homebrew/opt/dotnet/libexec"
export PATH="$PATH:$HOME/.dotnet/tools"
```

셸 다시 로드:

```bash
source ~/.zshrc
```

> **Intel Mac인 경우** DOTNET_ROOT 경로가 다르다:
> ```bash
> export DOTNET_ROOT="/usr/local/share/dotnet"
> ```
{: .prompt-warning }

### Step 4. Claude Code 플러그인 활성화

`~/.claude/settings.json`에 추가:

```json
{
  "enabledPlugins": {
    "csharp-lsp@claude-plugins-official": true
  }
}
```

프로젝트별로도 활성화하려면 `<프로젝트>/.claude/settings.json`에도 동일하게 추가한다.

### Step 5. 프로젝트에 .sln 파일 확인

csharp-ls는 `.sln` → `.csproj` 경로를 통해 심볼을 인덱싱한다. 프로젝트 루트에 `.sln` 파일이 반드시 있어야 한다.

```bash
ls *.sln
# 출력 예: MyProject.sln
```

`.sln` 파일이 없다면 생성:

```bash
dotnet new sln -n MyProject
dotnet sln add path/to/MyProject.csproj
```

### Step 6. 설치 확인

모든 설정이 끝났다면 아래 명령어로 최종 확인한다:

```bash
# 모두 정상 출력되면 성공
dotnet --version          # .NET SDK 버전
which csharp-ls           # ~/.dotnet/tools/csharp-ls
csharp-ls --version       # 0.22.0
echo $DOTNET_ROOT         # /opt/homebrew/opt/dotnet/libexec
```

Claude Code를 실행하고 C# 프로젝트 디렉토리에서 LSP 기능이 작동하는지 확인하면 된다.

---

## 3. 아키텍처 이해

Quick Start만으로 충분하지만, 문제가 발생했을 때 원인을 파악하려면 전체 구조를 이해하는 것이 좋다.

### 구성 요소 관계도

```
Claude Code
    │
    ├── csharp-lsp 플러그인 (settings.json에서 활성화)
    │       │
    │       └── csharp-ls (LSP 서버)
    │               │
    │               ├── DOTNET_ROOT → .NET SDK 위치 참조
    │               │
    │               └── .sln 파일 → .csproj → 심볼 인덱싱
    │
    └── PATH → ~/.dotnet/tools (csharp-ls 바이너리 위치)
```

### 각 구성 요소의 역할

| 구성 요소 | 역할 | 설치 경로 |
|-----------|------|----------|
| .NET SDK | C# 컴파일러 및 런타임 | `/opt/homebrew/Cellar/dotnet/10.0.101/` |
| csharp-ls | LSP 서버 (심볼 탐색, 자동완성 등) | `~/.dotnet/tools/csharp-ls` |
| DOTNET_ROOT | csharp-ls가 SDK를 찾는 환경변수 | `/opt/homebrew/opt/dotnet/libexec` |
| .sln 파일 | 프로젝트 구조 정의 (인덱싱 진입점) | 프로젝트 루트 |
| 플러그인 | Claude Code와 csharp-ls를 연결 | `~/.claude/plugins/` |

### 플러그인 파일 구조

플러그인 활성화 시 자동 생성되는 파일들:

```
~/.claude/plugins/
├── cache/claude-plugins-official/csharp-lsp/1.0.0/README.md
└── marketplaces/claude-plugins-official/plugins/csharp-lsp/
    ├── LICENSE
    └── README.md
```

---

## 4. 수동 설정 가이드

Quick Start에서 문제가 발생했을 때 참고하는 단계별 상세 가이드다.

### 4-1. .NET SDK 수동 설치 및 검증

Homebrew로 설치가 안 되는 경우, Microsoft 공식 설치 스크립트를 사용한다:

```bash
# 공식 설치 스크립트
curl -sSL https://dot.net/v1/dotnet-install.sh | bash /dev/stdin --channel LTS
```

이 경우 설치 경로가 `~/.dotnet`이 되므로 환경변수를 맞춰야 한다:

```bash
export DOTNET_ROOT="$HOME/.dotnet"
export PATH="$PATH:$DOTNET_ROOT:$DOTNET_ROOT/tools"
```

설치 확인:

```bash
dotnet --info
```

`dotnet --info` 출력에서 아래 항목을 확인한다:
- **Base Path** — SDK가 실제로 설치된 경로
- **Runtime Environment: OS** — 아키텍처가 `arm64`(Apple Silicon) 또는 `x64`(Intel)인지 확인

### 4-2. csharp-ls 수동 설치 및 검증

기본 설치 실패 시:

```bash
# 캐시 정리 후 재설치
dotnet nuget locals all --clear
dotnet tool install --global csharp-ls

# 특정 버전 지정 설치
dotnet tool install --global csharp-ls --version 0.22.0
```

이미 설치된 경우 업데이트:

```bash
dotnet tool update --global csharp-ls
```

바이너리 직접 확인:

```bash
# 파일 존재 여부
ls -la ~/.dotnet/tools/csharp-ls

# 아키텍처 확인 (arm64여야 함)
file ~/.dotnet/tools/csharp-ls
# 출력 예: Mach-O 64-bit executable arm64
```

### 4-3. 환경변수 디버깅

환경변수 문제가 의심될 때 하나씩 확인하는 방법:

```bash
# 1. DOTNET_ROOT 확인
echo $DOTNET_ROOT
# 빈 문자열이면 → 미설정 (가장 흔한 실패 원인)

# 2. DOTNET_ROOT 경로에 실제 SDK가 있는지 확인
ls $DOTNET_ROOT/sdk/
# 10.0.101 같은 디렉토리가 있어야 함

# 3. csharp-ls 바이너리가 PATH에 있는지 확인
which csharp-ls
# 출력 없으면 → ~/.dotnet/tools가 PATH에 없음

# 4. PATH에 ~/.dotnet/tools가 포함되어 있는지 확인
echo $PATH | tr ':' '\n' | grep dotnet
```

### 4-4. .sln 파일 생성 (Unity 프로젝트)

Unity 프로젝트의 경우 `.sln` 파일이 Unity Editor에서 자동 생성된다:

1. Unity Editor를 연다
2. **Edit → Preferences → External Tools**로 이동
3. **External Script Editor**를 설정 (Visual Studio Code 등)
4. **Regenerate project files** 클릭

수동으로 생성하는 경우:

```bash
cd /path/to/unity-project
dotnet new sln -n MyUnityProject

# Assembly-CSharp.csproj 등을 추가
dotnet sln add Assembly-CSharp.csproj
```

### 4-5. 플러그인 수동 활성화 확인

플러그인이 제대로 활성화되었는지 확인하는 방법:

```bash
# 글로벌 설정 확인
cat ~/.claude/settings.json | grep -A2 "enabledPlugins"

# 프로젝트별 설정 확인
cat .claude/settings.json | grep -A2 "enabledPlugins"

# 플러그인 파일이 다운로드되었는지 확인
ls ~/.claude/plugins/cache/claude-plugins-official/csharp-lsp/
```

---

## 5. 트러블슈팅

### Case 1: `csharp-ls: command not found`

**원인**: `~/.dotnet/tools`가 PATH에 없음

**해결**:

```bash
# 1. 바이너리 존재 확인
ls ~/.dotnet/tools/csharp-ls

# 2. PATH에 추가 (~/.zshrc)
export PATH="$PATH:$HOME/.dotnet/tools"
source ~/.zshrc

# 3. 확인
which csharp-ls
```

### Case 2: csharp-ls 실행 시 SDK를 찾지 못함

**원인**: DOTNET_ROOT 환경변수 미설정 (가장 흔한 원인)

**해결**:

```bash
# Apple Silicon Mac
export DOTNET_ROOT="/opt/homebrew/opt/dotnet/libexec"

# Intel Mac
export DOTNET_ROOT="/usr/local/share/dotnet"

# 확인 — SDK 디렉토리가 보여야 함
ls $DOTNET_ROOT/sdk/
```

### Case 3: OmniSharp와 충돌

**증상**: csharp-ls가 설치되어 있지만 LSP가 비정상 작동

**원인**: OmniSharp가 함께 설치되어 있으면 충돌 가능

**해결**:

```bash
# OmniSharp 설치 여부 확인
dotnet tool list -g | grep omnisharp

# 설치되어 있다면 제거
dotnet tool uninstall -g omnisharp
```

> Mono(`/opt/homebrew/bin/mono`)는 csharp-ls와 충돌하지 않는다. Mono가 설치되어 있어도 문제없다.
{: .prompt-info }

### Case 4: .sln 파일이 있는데 심볼 인덱싱이 안 됨

**원인**: `.sln` 파일에 `.csproj`가 등록되지 않았거나, `.csproj` 경로가 잘못됨

**해결**:

```bash
# .sln에 등록된 프로젝트 확인
cat MyProject.sln | grep "\.csproj"

# 빈 결과면 → .csproj 등록 필요
dotnet sln add path/to/MyProject.csproj
```

### Case 5: Claude Code에서 LSP 기능이 작동하지 않음

**진단 순서**:

```bash
# 1단계: csharp-ls 자체가 작동하는지 확인
csharp-ls --version

# 2단계: DOTNET_ROOT 확인
echo $DOTNET_ROOT

# 3단계: 플러그인 활성화 확인
cat ~/.claude/settings.json

# 4단계: .sln 파일 존재 확인
ls *.sln

# 5단계: Claude Code 재시작
# 플러그인 설정 변경 후에는 반드시 Claude Code를 재시작해야 한다
```

### Case 6: Homebrew dotnet과 공식 설치 스크립트 dotnet 충돌

**증상**: `dotnet`이 실행되지만 csharp-ls가 SDK를 못 찾음

**원인**: Homebrew와 공식 스크립트가 다른 경로에 SDK를 설치하여 DOTNET_ROOT가 잘못된 SDK를 가리킴

**해결**:

```bash
# 어떤 dotnet이 실행되고 있는지 확인
which dotnet
dotnet --info

# Homebrew 버전이면
export DOTNET_ROOT="/opt/homebrew/opt/dotnet/libexec"

# 공식 스크립트 버전이면
export DOTNET_ROOT="$HOME/.dotnet"

# 하나만 남기는 것을 권장
# Homebrew 버전 제거
brew uninstall dotnet

# 또는 공식 스크립트 버전 제거
rm -rf ~/.dotnet
```

---

## 6. 회사 컴퓨터(다른 Mac) 세팅 체크리스트

새 Mac에서 처음부터 세팅할 때 사용하는 체크리스트다. 복사해서 그대로 따라하면 된다.

```bash
# ✅ Step 1: .NET SDK 설치
brew install dotnet

# ✅ Step 2: 환경변수 설정 (~/.zshrc에 추가)
echo '' >> ~/.zshrc
echo '# .NET & csharp-ls 설정' >> ~/.zshrc
echo 'export DOTNET_ROOT="/opt/homebrew/opt/dotnet/libexec"' >> ~/.zshrc
echo 'export PATH="$PATH:$HOME/.dotnet/tools"' >> ~/.zshrc

# ✅ Step 3: 셸 다시 로드
source ~/.zshrc

# ✅ Step 4: csharp-ls 설치
dotnet tool install --global csharp-ls

# ✅ Step 5: 설치 확인
which csharp-ls          # ~/.dotnet/tools/csharp-ls
csharp-ls --version      # 0.22.0

# ✅ Step 6: Claude Code 플러그인 활성화
# ~/.claude/settings.json에 아래 내용 추가:
# {
#   "enabledPlugins": {
#     "csharp-lsp@claude-plugins-official": true
#   }
# }

# ✅ Step 7: 프로젝트 루트에 .sln 파일 확인
ls *.sln
```

> **Intel Mac인 경우** Step 2의 DOTNET_ROOT를 아래로 변경:
> ```bash
> export DOTNET_ROOT="/usr/local/share/dotnet"
> ```
{: .prompt-warning }

---

## 7. 자주 묻는 질문

### Q. OmniSharp도 설치해야 하나?

**아니다.** csharp-ls만 있으면 된다. OmniSharp는 설치하지 않는 것이 오히려 깔끔하다. 두 LSP 서버가 공존하면 충돌 가능성이 있다.

### Q. Mono가 설치되어 있는데 괜찮은가?

**괜찮다.** Mono(`/opt/homebrew/bin/mono`)는 csharp-ls와 독립적으로 동작하며 충돌하지 않는다.

### Q. Apple Silicon Mac에서 Rosetta가 필요한가?

**필수는 아니다.** csharp-ls는 arm64 네이티브 바이너리로 설치된다. 다만 일부 .NET 도구가 x64만 지원하는 경우가 있어 Rosetta가 설치되어 있으면 호환성이 좋다.

### Q. 프로젝트마다 플러그인 설정을 해야 하나?

`~/.claude/settings.json`에 글로벌로 설정하면 모든 프로젝트에 적용된다. 특정 프로젝트에서만 사용하고 싶다면 `<프로젝트>/.claude/settings.json`에만 설정하면 된다.

### Q. csharp-ls 업데이트는 어떻게 하나?

```bash
dotnet tool update --global csharp-ls
```

---

## 8. workspaceSymbol 제한사항 및 대안

### workspaceSymbol이란?

`workspace/symbol`은 LSP 표준 요청으로, **워크스페이스 전체에서 심볼을 이름으로 검색**하는 기능이다.

```
클라이언트 → 서버: { method: "workspace/symbol", params: { query: "GamePauseLayer" } }
서버 → 클라이언트: [ { name: "GamePauseLayer", kind: Class, location: {...} }, ... ]
```

IDE에서는 `Ctrl+T` (Go to Symbol in Workspace)로 사용되는 기능이다.

### Claude Code에서 작동하지 않는 이유

Claude Code의 LSP tool 스펙에는 `workspaceSymbol`에 필요한 `query` 파라미터가 **존재하지 않는다**:

```json
{
    "operation": "workspaceSymbol",
    "filePath": "string (required)",    // ← workspaceSymbol에 불필요
    "line": "integer (required)",       // ← workspaceSymbol에 불필요
    "character": "integer (required)"   // ← workspaceSymbol에 불필요
    // query 파라미터 없음!
}
```

결과적으로 빈 쿼리(`query: ""`)가 전송되어 전체 심볼 중 **최대 100개만 반환**되며, 대규모 프로젝트에서는 원하는 심볼이 포함되지 않는다.

> 예시: Unity 프로젝트(18,500+ 심볼)에서 `GamePauseLayer`를 검색하면, proto 자동생성 파일이 알파벳순으로 먼저 나와서 100개 제한 안에 게임 코드 심볼이 포함되지 않았다.
{: .prompt-warning }

### 다른 LSP operation은 정상 작동

| Operation | 쿼리 필요? | 상태 | 비고 |
| --- | --- | --- | --- |
| `documentSymbol` | 아니오 (파일 지정) | **정상** | 파일 구조 파악 |
| `hover` | 아니오 (위치 지정) | **정상** | 타입+문서 풍부 |
| `findReferences` | 아니오 (위치 지정) | **정상** | 시맨틱 검색 |
| `goToDefinition` | 아니오 (위치 지정) | **정상** | 정확한 점프 |
| `goToImplementation` | 아니오 (위치 지정) | **정상** | 인터페이스→구현 |
| `incomingCalls` / `outgoingCalls` | 아니오 (위치 지정) | **정상** | 호출 추적 |
| `workspaceSymbol` | **예 (쿼리 필수)** | **사용 불가** | 쿼리 파라미터 없음 |

`workspaceSymbol`만 유일하게 `query` 문자열이 필요한 operation이며, Claude Code에서 이를 지원하지 않는다.

### 대안: 심볼 찾기 전략

#### 파일/클래스 위치 찾기

| 방법 | 속도 | 정확도 |
| --- | --- | --- |
| **Rider 실행 시:** `find_files_by_name_keyword` → `documentSymbol` | 즉시 (~0.1s + ~0.5s) | 100% |
| **Rider 미실행:** `Glob **/ClassName.cs` → `documentSymbol` | 즉시 (~0.1s + ~0.5s) | 100% |
| `Grep "class ClassName"` | 빠름 (~1s) | 100% |
| `workspaceSymbol` | 느림 (~3s) | **0%** (대규모 프로젝트) |

#### 심볼 이름 패턴 검색

| 방법 | 예시 |
| --- | --- |
| **Rider:** `search_in_files_by_text "class.*Pause"` → `documentSymbol` | 시맨틱 검색 + 구조 분석 |
| **No Rider:** `Glob **/*Pause*.cs` → 각 파일에 `documentSymbol` | 파일 찾기 + 구조 분석 |
| `Grep "class.*Pause"` | 텍스트 매칭 |

#### 심볼 사용처 찾기

| 방법 | 정확도 |
| --- | --- |
| `LSP findReferences` | **최고** (코드 참조만) |
| `Grep "ClassName"` | 문자열/주석 포함 |

### 권장 워크플로우

```
┌──────────────────────────────────────────────────────────┐
│  심볼 찾기 최적 전략                                       │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  "이 클래스 파일이 어디있지?"                               │
│  → [Rider] find_files_by_name_keyword "ClassName"        │
│  → [No Rider] Glob **/ClassName.cs                       │
│  → LSP documentSymbol (구조 확인)                         │
│                                                          │
│  "Pause 관련 클래스 전부 찾아줘"                            │
│  → [Rider] search_in_files_by_text "class.*Pause"        │
│  → [No Rider] Glob **/*Pause*.cs                         │
│  → 각 파일에 LSP documentSymbol                           │
│                                                          │
│  "이 심볼을 어디서 쓰고 있지?"                              │
│  → LSP findReferences (파일+위치 지정)                     │
│                                                          │
│  "이 파일 구조가 어떻게 되지?"                              │
│  → LSP documentSymbol                                    │
│                                                          │
│  ✗ workspaceSymbol → 사용하지 말 것                        │
│    (쿼리 파라미터 미지원, 100개 제한)                        │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## 마치며

C# LSP 설정의 핵심은 **환경변수 2줄**이다:

```bash
export DOTNET_ROOT="/opt/homebrew/opt/dotnet/libexec"  # SDK 경로
export PATH="$PATH:$HOME/.dotnet/tools"                # 바이너리 경로
```

이 2줄이 `.zshrc`에 있고, csharp-ls가 설치되어 있으며, 플러그인이 활성화되어 있다면 Claude Code에서 C# 코드를 완벽하게 분석할 수 있다.

문제가 발생하면 [트러블슈팅 섹션](#5-트러블슈팅)의 진단 순서를 따라가면 대부분 해결된다. 가장 흔한 원인은 **DOTNET_ROOT 미설정**이라는 것만 기억하자.
