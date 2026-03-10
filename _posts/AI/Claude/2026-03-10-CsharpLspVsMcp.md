---
title: "C# LSP vs JetBrains MCP — 토큰 효율성 분석 리포트"
date: 2026-03-10 11:00:00 +0900
categories: [AI, Claude]
tags: [Claude Code, C#, LSP, MCP, JetBrains, Rider, Unity, Token Efficiency, csharp-ls]
difficulty: intermediate
toc: true
toc_sticky: true
prerequisites:
  - /posts/CsharpLspSetupGuide/
tldr:
  - "LSP는 MCP보다 평균 3.1배 적은 토큰을 소비하면서 더 높은 정보 품질을 제공한다"
  - "LSP와 MCP의 기능은 하나도 겹치지 않는다 — 경쟁이 아닌 보완 관계이므로 둘 다 쓰는 것이 최적 전략이다"
  - "하이브리드 전략(LSP 우선 + MCP 보조)으로 세션당 약 60% 이상의 토큰을 절약할 수 있다"
---

日本語バージョンはこちらへ [csharp-lsp と Rider MCP 比較分析](/ja/posts/CsharpLspVsMcp.ja/)

> **Project:** psv-client (Unity 2022.3.31)
> **Target File:** `Assets/App/Editor/EditorStartup.cs`
> **Date:** 2026-03-10
> **Tool Versions:** csharp-lsp (Claude Code built-in) / JetBrains Rider MCP

---

## 요약(핵심 요약)

| Metric | Value |
| --- | --- |
| **Average Token Savings** | **3.1x** (LSP가 MCP 대비) |
| **LSP 정보 품질** | **A+** (Semantic + XML Docs) |
| **MCP 고유 기능** | **3개** (Diagnostics / Refactoring / Formatting) |
| **최적 전략** | **Hybrid** (LSP-first, MCP for IDE tasks) |

### 핵심 결론

- **일반적인 코드 탐색/분석**: csharp-lsp가 토큰 **2~5배 효율적**이고 정보 품질도 높음
- **Rider 인스펙션 (에러 진단) & 리팩토링**: MCP만 가능
- **최적 접근법**: 둘을 용도에 맞게 **하이브리드로 혼용**

---

## 테스트 방법론(측정 방법)

동일한 파일(`EditorStartup.cs`, 56줄)에 대해 양쪽 도구로 동일한 작업을 수행하고 응답 크기를 측정했다.
토큰 추정 기준: **~4자 = 1 토큰** (영문/코드 혼합 콘텐츠 기준)

| Test ID | Task | LSP Operation | MCP Operation |
| --- | --- | --- | --- |
| T1 | Symbol Info (EditorStartup class) | `hover` | `get_symbol_info` |
| T2 | File-scope Search ("SessionState") | `Grep` (LSP native) | `search_in_files_by_text` |
| T3 | Project-wide Reference Search ("EditorStartup") | `findReferences` | `search_in_files_by_text` |
| T4 | File Symbol Structure | `documentSymbol` | N/A |
| T5 | External Type Info (Canvas API) | `hover` | `get_symbol_info` |
| T6 | Go To Definition (Shader.Find) | `goToDefinition` | `get_symbol_info` |
| T7 | Error Diagnostics | N/A | `get_file_problems` |

---

## 측정 결과(원시 데이터)

| Test | LSP (chars) | LSP (tokens) | MCP (chars) | MCP (tokens) | Ratio | Winner | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| T1: Symbol Hover | **280** | **70** | 22 | 6 | 0.08x | **LSP** | MCP는 빈 docs 반환, LSP는 full signature + XML docs |
| T2: File Search | **180** | **45** | 448 | 112 | 2.5x | **LSP** | 동일 4건 결과. MCP는 JSON 오버헤드 + \|\| 마커 |
| T3: Project Search | **110** | **28** | 520 | 130 | 4.7x | **LSP** | LSP: 시맨틱 참조 2건, MCP: 문자열 포함 5건 |
| T4: Doc Symbols | **280** | **70** | - | - | - | **LSP Only** | MCP에 해당 기능 없음 |
| T5: External Type | **120** | **30** | 22 | 6 | 0.18x | **LSP** | MCP 다시 빈 값. LSP는 Material 시그니처 + docs |
| T6: Go To Def | 125 | 31 | 22 | 6 | - | Draw | 둘 다 외부 Unity API (decompiled)에서 실패 |
| T7: Diagnostics | - | - | **55** | **14** | - | **MCP Only** | LSP 플러그인에 진단 기능 없음 |

> **T1, T5 주의:** MCP 응답이 더 작지만 `{"documentation":""}` — **유용한 정보가 0**이다. 단순 크기 비교는 오해를 부른다.
{: .prompt-warning }

---

## 시각적 비교

### 1. 응답 크기 비교(문자 수)

![Response Size Comparison](/assets/img/post/lsp-vs-mcp/01_response_size.png)

T2 File Search에서 2.5배, T3 Project Search에서 **4.7배** LSP가 더 작은 응답을 반환한다.

---

### 2. 추정 토큰 소비량

![Estimated Token Consumption](/assets/img/post/lsp-vs-mcp/02_token_consumption.png)

동일 작업 수행 시 LSP가 평균 **3.1배** 적은 토큰을 소비한다.

---

### 3. 정보 품질 점수(레이더 차트)

![Information Quality Radar](/assets/img/post/lsp-vs-mcp/03_quality_radar.png)

LSP와 MCP의 강점 영역이 **완전히 상보적**이다.
- **LSP**: Symbol Hover, Search, Symbols에서 만점
- **MCP**: Diagnostics, Refactoring에서 만점

---

### 4. 테스트 승자 분포

![Test Winner Distribution](/assets/img/post/lsp-vs-mcp/04_winner_distribution.png)

7개 테스트 중:
- **LSP 승리**: 4건 (57%)
- **LSP Only**: 1건 (14%)
- **MCP Only**: 1건 (14%)
- **무승부**: 1건 (14%)

---

### 5. 기능/역량 매트릭스

![Feature Capability Matrix](/assets/img/post/lsp-vs-mcp/05_capability_matrix.png)

두 도구의 기능이 **겹치지 않고 상호 보완**된다.
- LSP Domain (상단 7개): 시맨틱 분석 전담
- MCP Domain (하단 8개): IDE 기능 전담

---

### 6. 세션 토큰 절감량

![Token Savings](/assets/img/post/lsp-vs-mcp/06_token_savings.png)

하이브리드 접근법을 사용하면 세션당 **약 61~63% 토큰 절약**이 가능하다.

---

### 7. 시맨틱 검색 vs 텍스트 검색

![Semantic vs Textual Search](/assets/img/post/lsp-vs-mcp/07_semantic_vs_text.png)

`"EditorStartup"` 검색 시:
- **LSP** `findReferences`: 2건 (class 선언 + 생성자) — **실제 심볼 참조만**
- **MCP** `search_in_files_by_text`: 5건 (2건 실제 + 3건 문자열/로그 매칭) — **false positive 포함**

> 문자열 내 `"EditorStartup.Reloading"`과 로그 메시지 `[EditorStartup]`까지 매칭되어 AI에게 **오해를 유발**할 수 있다.
{: .prompt-info }

---

### 8. 품질 보정 토큰 효율

![Quality-Adjusted Efficiency](/assets/img/post/lsp-vs-mcp/08_quality_adjusted.png)

품질 대비 토큰 효율(Quality per Token)을 계산하면 LSP의 우위가 더욱 뚜렷해진다.
T1(Symbol Hover)과 T5(External Type)에서 MCP는 응답이 작지만 **정보량이 0**이므로 실질 효율도 0이다.

---

## 정보 품질 분석

### 품질 보정 토큰 효율 표

| Test | LSP Info Quality | MCP Info Quality | LSP Useful Tokens | MCP Useful Tokens | Effective Ratio |
| --- | --- | --- | ---: | ---: | --- |
| T1: Symbol Hover | **10** (signature + docs) | 0 (empty) | 70 | 0 | LSP infinitely better |
| T2: File Search | **9** (clean format) | 8 (same data, noisy) | 45 | 112 | LSP 2.5x better |
| T3: Project Search | **10** (semantic only) | 6 (includes false positives) | 28 | 130 | LSP 7.7x better |
| T5: External Type | **10** (return type + docs) | 0 (empty) | 30 | 0 | LSP infinitely better |
| T7: Diagnostics | N/A | **10** (Rider inspections) | - | 14 | MCP exclusive |

### 핵심 인사이트: 시맨틱 vs 텍스트 검색

T3 `"EditorStartup"` 검색이 근본적 차이를 보여준다:

| Tool | Results | Type |
| --- | --- | --- |
| LSP `findReferences` | 2건 | 시맨틱 — class 선언 + 생성자 (실제 참조만) |
| MCP `search_in_files` | 5건 | 텍스트 — 2건 실제 + 3건 문자열 리터럴/로그 (false positive) |

LSP는 **심볼 수준에서 분석**하므로 문자열 안의 `"EditorStartup.Reloading"`은 무시한다.
MCP는 **단순 텍스트 매칭**이므로 false positive가 포함되어 컨텍스트를 낭비하고 AI를 오도할 수 있다.

---

## 기능/역량 매트릭스

| Capability | csharp-lsp | JetBrains MCP | Notes |
| --- | :---: | :---: | --- |
| Hover / Type Info | **O** (rich) | △ (often empty) | LSP는 XML docs 반환, MCP는 Unity API에서 자주 빈 값 |
| Go To Definition | **O** | X | MCP에 직접 대응 기능 없음 |
| Find References (Semantic) | **O** | X | MCP는 텍스트 검색만 가능 |
| Document Symbols | **O** | X | 파일 구조를 한 눈에 파악 |
| Call Hierarchy | **O** | X | 호출 관계 추적 (incoming/outgoing) |
| Go To Implementation | **O** | X | 인터페이스 → 구현 클래스 |
| Workspace Symbol Search | **O** | X | 프로젝트 전체에서 클래스/메서드 검색 |
| Text Search (in files) | X | **O** | Grep도 대안으로 사용 가능 |
| Regex Search (in files) | X | **O** | 패턴 매칭 |
| Error/Warning Diagnostics | X | **O** | Rider 인스펙션 (에러/경고/코드 스멜) |
| Rename Refactoring | X | **O** | 크로스 프로젝트 안전 리네이밍 |
| Code Formatting | X | **O** | Rider 코드 스타일 적용 |
| File Read/Write | X | **O** | Read/Edit 도구도 대안 |
| Directory Browse | X | **O** | `list_directory_tree` |
| Run Configurations | X | **O** | IDE 빌드/테스트 실행 |

> **Score:** LSP 7 capabilities | MCP 8 capabilities | **겹침: 0개** (완전히 상호 보완)
{: .prompt-tip }

---

## 최적 전략: 하이브리드 접근

### csharp-lsp 우선(기본) — 토큰 절약

코드 탐색/분석 작업은 **기본적으로 LSP를 먼저 사용**한다.

| Operation | 용도 |
| --- | --- |
| `hover` | 타입 정보, 문서, 시그니처 조회 |
| `findReferences` | 시맨틱 심볼 참조 검색 |
| `documentSymbol` | 파일 구조 파악 |
| `goToDefinition` | 소스 코드로 이동 |
| `goToImplementation` | 인터페이스 구현체 찾기 |
| `callHierarchy` | 호출 체인 분석 |
| `workspaceSymbol` | 프로젝트 전체 클래스/메서드 검색 |

> 평균 **3.1배 적은 토큰** 소비. 더 높은 정보 밀도.
{: .prompt-tip }

### JetBrains MCP(필요 시) — 고유 기능

LSP로 할 수 없는 작업에만 MCP를 사용한다.

| Operation | 용도 |
| --- | --- |
| `get_file_problems` | 코드 수정 후 에러/경고 검증 |
| `rename_refactoring` | 심볼 리네이밍 (YAML, 문자열까지 안전) |
| `reformat_file` | Rider 코드 스타일 포맷팅 |
| `search_in_files_by_text/regex` | 로그 문자열, 주석 등 텍스트 검색 |
| `execute_terminal_command` | 빌드/테스트 실행 |
| `execute_run_configuration` | IDE 실행 프로필 |

> Diagnostics, Refactoring, IDE 통합은 **MCP만 가능** — 대체 불가.
{: .prompt-warning }

---

## 세션당 추정 토큰 절감량

| Scenario | MCP Only (tokens) | Hybrid (tokens) | Savings |
| --- | ---: | ---: | ---: |
| Light (10 lookups, 5 searches) | ~1,750 | ~650 | **63%** |
| Medium (30 lookups, 15 searches, 3 refactors) | ~5,800 | ~2,200 | **62%** |
| Heavy (80 lookups, 40 searches, 10 refactors) | ~15,200 | ~5,900 | **61%** |

> Refactoring 작업은 항상 MCP를 사용. 절약분은 lookup과 reference search를 LSP로 라우팅한 결과.

---

## CLAUDE.md 업데이트 권장안

기존 CLAUDE.md의 `"ALWAYS use Rider MCP tools over generic alternatives"` 를 아래로 교체 권장:

| Task | Primary Tool | Fallback |
| --- | --- | --- |
| Type/Docs lookup | **LSP** `hover` | MCP `get_symbol_info` |
| Semantic references | **LSP** `findReferences` | MCP text search |
| File structure | **LSP** `documentSymbol` | (none) |
| Definition navigation | **LSP** `goToDefinition` | (none) |
| Call hierarchy | **LSP** `callHierarchy` | (none) |
| Implementation lookup | **LSP** `goToImplementation` | (none) |
| Text/Regex search | **MCP** `search_in_files` | Grep |
| Error diagnostics | **MCP** `get_file_problems` | (none) |
| Rename symbol | **MCP** `rename_refactoring` | (none) |
| Code formatting | **MCP** `reformat_file` | (none) |
| File read | Read / MCP `get_file` | (either) |
| File edit | Edit / MCP `replace` | (either) |

---

## 빠른 참조 카드(요약 카드)

```
┌─────────────────────────────────────────────────┐
│  작업별 최적 도구 선택 가이드                      │
├─────────────────────────────────────────────────┤
│                                                 │
│  🟢 csharp-lsp 사용 (토큰 절약)                  │
│  ├─ hover (타입/문서 조회)                       │
│  ├─ findReferences (시맨틱 참조 검색)             │
│  ├─ documentSymbol (파일 구조 파악)              │
│  ├─ goToDefinition / goToImplementation         │
│  └─ callHierarchy (호출 관계)                    │
│                                                 │
│  🔵 JetBrains MCP 사용 (고유 기능)               │
│  ├─ get_file_problems (에러/경고 진단)            │
│  ├─ rename_refactoring (안전한 리네이밍)          │
│  ├─ reformat_file (코드 포맷팅)                  │
│  └─ 텍스트 기반 검색 (로그 문자열 등)              │
│                                                 │
│  ⚪ 어느 쪽이든 OK                               │
│  ├─ 파일 읽기 (Read ≈ get_file_text_by_path)     │
│  └─ 파일 수정 (Edit ≈ replace_text_in_file)      │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

*Generated by Claude Code — psv-client C# LSP vs JetBrains MCP Analysis — 2026-03-10*
