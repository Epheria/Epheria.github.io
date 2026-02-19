# C++ for Unreal 시리즈 기획 문서

> **Summary**: 유니티 개발자를 위한 언리얼 C++ 코드 리딩 가이드 (총 15강)
>
> **Project**: Epheria.github.io (Jekyll + Chirpy v6.1)
> **Author**: Sehyup
> **Date**: 2026-02-20
> **Status**: In Progress

---

## 1. Overview

### 1.1 Purpose

유니티(C#) 클라이언트 개발자가 **언리얼 C++ 코드를 자연스럽게 읽을 수 있도록** 하는 것이 목표. 범용 C++ 문법 강좌가 아니라, 언리얼 코드에서 실제로 마주치는 C++ 패턴과 문법을 중심으로 설명한다.

### 1.2 Background

- 블로그 운영자가 10년차 언리얼 시니어 프로그래머이자 C++ 전문가
- 대상 독자: 유니티 클라이언트 개발 경험이 있고 언리얼로 전환하려는 개발자
- 참고 소스: `/Users/son_sehyup/cpp_study/` (25개 디렉토리, 47개 .cpp 파일)
- 스타일 참고: `_posts/ML/2026-2-13-llm-guide.md` (llm-guide 포맷)

### 1.3 Related Documents

- CLAUDE.md: 블로그 프로젝트 개요, 포스트 컨벤션
- `_posts/Unreal/Study/2025-09-03-UnrealStudy01.md`: 기존 언리얼 학습 포스트
- `/Users/son_sehyup/cpp_study/STUDY_GUIDE.md`: C++ 학습 가이드 (원본)

---

## 2. Series Design

### 2.1 핵심 컨셉

| 항목 | 내용 |
|------|------|
| 시리즈 제목 | 유니티 개발자를 위한 언리얼 C++ 코드 리딩 가이드 |
| 화자 | 언리얼 10년차 시니어 프로그래머 (블로그 주인) |
| 독자 | 유니티 클라이언트 개발자 (C# 경험 있음, C++ 초보) |
| 목표 | 언리얼 C++ 코드를 읽고 이해할 수 있게 되는 것 |
| 구성 원칙 | 언리얼 코드에서 출발 → 필요한 C++ 문법 설명 (역방향) |
| 톤 | llm-guide 스타일 — 재밌고 유익하게, 게임 개발 비유 활용 |

### 2.2 스타일 가이드

#### 포스트 포맷 (매 강 공통)

```
1. Front Matter (title, categories, tags, difficulty, tldr 필수)
2. "이 코드, 읽을 수 있나요?" — 언리얼 코드 스니펫으로 시작 (퀴즈 느낌)
3. 서론 — 이 강에서 다루는 내용이 왜 필요한지 (Unity 개발자 관점)
4. C# ↔ C++ 비교 — 표 + 코드 나란히 비교
5. 핵심 개념 설명 — mermaid 다이어그램 + 상세 코드
6. 언리얼 실전 코드 해부 — 실제 언리얼에서 쓰이는 패턴
7. "잠깐, 이건 알고 가자" Q&A 박스 — blockquote로 자주 묻는 질문
8. 흔한 실수 & 주의사항
9. 체크리스트 — 이 강을 마치면 읽을 수 있는 것들
10. 다음 강 미리보기
```

#### Front Matter 템플릿

```yaml
---
title: "{주제} - 유니티 개발자를 위한 언리얼 C++ #{번호}"
date: 2026-MM-DD 10:00:00 +0900
categories: [Unreal, Cpp]
tags: [Unreal, C++, Unity, C#, {주제별 태그}]
toc: true
toc_sticky: true
math: false
mermaid: true
difficulty: {beginner | intermediate | advanced}
tldr:
  - "핵심 요약 1"
  - "핵심 요약 2"
  - "핵심 요약 3"
---
```

#### 파일 네이밍

- 경로: `_posts/Unreal/Cpp/2026-M-DD-Cpp{번호}.md`
- 카테고리: `[Unreal, Cpp]` → 시리즈 네비게이션 자동 활성화
- 번호: 01 ~ 15 (2자리)

#### 문체 규칙

- 경어체 사용 (~합니다, ~입니다)
- C# 코드는 주석으로 비교 표시 (`// C# (Unity)`)
- 언리얼 코드는 실제로 컴파일 가능한 수준으로 작성
- "잠깐, 이건 알고 가자" 블록은 `> **💬 잠깐, 이건 알고 가자**` 형식
- 매 섹션마다 비교 표 최소 1개 포함

---

## 3. 시리즈 구성 (총 15강, 3파트)

### Part 1: C++ 기초 다지기 — "C#과 뭐가 다른데?" (6강)

| # | 제목 | 핵심 내용 | 난이도 | 참고 소스 (cpp_study) |
|---|------|----------|--------|----------------------|
| **01** | C# → C++ 넘어가기 - 변수, 타입, 함수의 차이 | 값 타입/참조 타입 차이, int32 vs int, auto, const, FString, TEXT(), UE_LOG, 네이밍 컨벤션(A/U/F/E/T/I/b), 함수 프로토타입, 값/참조/포인터 전달 | beginner | 01_HelloWorld, 02_Variables, 03_Operators, 05_Functions |
| **02** | 헤더와 소스 - .h/.cpp 분리와 컴파일의 이해 | #include, #pragma once, 선언 vs 정의, 전방선언, include guard, 링커, 왜 빌드가 느린지, .generated.h | beginner | 13_ForwardDeclaration |
| **03** | 포인터 입문 - C#에는 없는 그것 | *, &, ->, nullptr, new/delete, 포인터 산술, 이중 포인터, AActor* 읽기 | beginner | 07_Pointers (01, 02, main) |
| **04** | 참조와 const - 언리얼 코드의 절반은 이것 | lvalue 참조, const auto&, const 4가지 조합, 왜 const FString&를 쓰는지, 참조 vs 포인터 선택 기준 | beginner | 12_References (01), 07_Pointers (02) |
| **05** | 클래스와 OOP - C++만의 생성자/소멸자 규칙 | 생성자/소멸자, 초기화 리스트, this, 접근 지정자, struct vs class, 소멸자에서의 정리 | intermediate | 08_Classes, 17_InheritanceAdvanced (03) |
| **06** | 상속과 다형성 - virtual의 진짜 의미 | virtual, override, final, 순수 가상 함수, 가상 소멸자, VTable, 다중 상속, 인터페이스 | intermediate | 09_Inheritance, 17_InheritanceAdvanced (01) |

### Part 2: 언리얼 C++ 핵심 — "이제 언리얼 코드가 보인다" (6강)

| # | 제목 | 핵심 내용 | 난이도 | 참고 소스 (cpp_study) |
|---|------|----------|--------|----------------------|
| **07** | 언리얼 매크로의 마법 - UCLASS, UPROPERTY, UFUNCTION | GENERATED_BODY(), 리플렉션 시스템, 에디터 노출 지정자, 블루프린트 연동, UCLASS 지정자, UPROPERTY 조합, UFUNCTION 지정자 | intermediate | 15_UnrealCppPatterns (01) |
| **08** | 언리얼 클래스 계층과 게임플레이 프레임워크 | UObject → AActor → APawn → ACharacter, Super::, GameMode, PlayerController, BeginPlay/Tick 라이프사이클, 컴포넌트 아키텍처 | intermediate | 15_UnrealCppPatterns (01), 25_UnrealPracticalPatterns |
| **09** | 메모리 관리 - GC가 있지만 C#과 다르다 | 언리얼 GC, UPROPERTY() = GC 루트, TSharedPtr, TWeakObjectPtr, TObjectPtr, 댕글링 포인터, RAII, 소유권 모델 | intermediate | 11_SmartPointers (01, 02, 03), 19_MemoryAndPerformance (03) |
| **10** | 언리얼 컨테이너와 문자열 | TArray, TMap, TSet, FString/FName/FText 심화, 범위 기반 for, 이터레이터, 컨테이너 메서드, STL과의 차이 | intermediate | 15_UnrealCppPatterns (02), 06_Arrays |
| **11** | 캐스팅과 템플릿 - Cast\<T\>()의 모든 것 | Cast\<T\>(), CastChecked\<T\>(), IsA(), 템플릿 기초, static_cast vs dynamic_cast, RTTI, 타입 안전성 | intermediate | 18_Casting, 10_Templates, 16_Templates (01) |
| **12** | 델리게이트와 이벤트 - UnityEvent의 언리얼 버전 | 싱글캐스트, 멀티캐스트, 다이나믹 델리게이트, BindUObject, BindLambda, 이벤트 디스패처, C# event와 비교 | intermediate | 15_UnrealCppPatterns (03) |

### Part 3: 실전 — "이제 코드를 읽고 쓸 수 있다" (3강)

| # | 제목 | 핵심 내용 | 난이도 | 참고 소스 (cpp_study) |
|---|------|----------|--------|----------------------|
| **13** | 람다, 콜백, 타이머 - Modern C++ in Unreal | 람다 캡처 ([this], [&], [WeakThis]), FTimerHandle, 비동기 콜백 패턴, rvalue 참조, std::move, Modern C++ 키워드 | advanced | 14_Lambda (01, 02), 20_ModernCpp, 12_References (02) |
| **14** | 전처리기, 디버깅, 실전 키워드 | UE_LOG 심화, check(), ensure(), verify(), static, explicit, mutable, constexpr, 조건부 컴파일, 매크로 | advanced | 21_Preprocessor, 24_DebuggingTips, 20_ModernCpp (03) |
| **15** | 실전 코드 패턴 총정리 - 10년차가 매일 쓰는 것들 | Spawn, 컴포넌트 초기화, 충돌/오버랩, Enhanced Input, 데미지, 비동기 에셋 로딩, 세이브/로드, 안티패턴, 멀티스레딩 맛보기 | advanced | 25_UnrealPracticalPatterns, 22_Multithreading, 23_BitwiseOperations |

---

## 4. cpp_study 디렉토리 매핑

어떤 cpp_study 소스가 어느 강에서 사용되는지 역매핑.

| cpp_study 디렉토리 | 사용 강 | 비고 |
|---|---|---|
| 01_HelloWorld | 1강 | 기본 출력, main 함수 |
| 02_Variables | 1강 | 타입, const, auto |
| 03_Operators | 1강 | 연산자 (C#과 같으므로 간략히) |
| 04_ControlFlow | 1강 (간략) | if/for/while (C#과 거의 같으므로 생략 가능) |
| 05_Functions | 1강 | 함수 선언/정의, 오버로딩, 기본 매개변수 |
| 06_Arrays | 10강 | 배열, vector → TArray 비교 |
| 07_Pointers | 3강, 4강 | 포인터 기초, const 포인터 |
| 08_Classes | 5강 | 클래스, 생성자, 소멸자 |
| 09_Inheritance | 6강 | 상속, 다형성, virtual |
| 10_Templates | 11강 | 템플릿 기초 |
| 11_SmartPointers | 9강 | unique_ptr, shared_ptr, weak_ptr |
| 12_References | 4강, 13강 | 참조 기초(4강), rvalue/move(13강) |
| 13_ForwardDeclaration | 2강 | 전방선언, 헤더 의존성 |
| 14_Lambda | 13강 | 람다, 캡처, 콜백 |
| 15_UnrealCppPatterns | 7강, 8강, 10강, 12강 | 언리얼 매크로, 컨테이너, 델리게이트 |
| 16_Templates | 11강 | SFINAE, concepts (심화) |
| 17_InheritanceAdvanced | 5강, 6강 | 생성자 규칙(5강), virtual 심화(6강) |
| 18_Casting | 11강 | 캐스팅 종류, Cast\<T\>() |
| 19_MemoryAndPerformance | 9강 | RAII, 메모리 레이아웃 |
| 20_ModernCpp | 13강, 14강 | Modern C++ 키워드, static |
| 21_Preprocessor | 14강 | 매크로, 조건부 컴파일 |
| 22_Multithreading | 15강 | 멀티스레딩 기초 (맛보기) |
| 23_BitwiseOperations | 15강 | 비트 연산, 플래그 시스템 |
| 24_DebuggingTips | 14강 | UE_LOG, check, ensure |
| 25_UnrealPracticalPatterns | 8강, 15강 | 실전 코드 패턴 |

---

## 5. 진행 상황

| # | 제목 | 상태 | 파일 | 날짜 |
|---|------|------|------|------|
| 01 | C# → C++ 넘어가기 | ✅ 완료 | `2026-2-20-Cpp01.md` | 2026-02-20 |
| 02 | 헤더와 소스 | ✅ 완료 | `2026-2-20-CppForUnreal02.md` | 2026-02-20 |
| 03 | 포인터 입문 | ✅ 완료 | `2026-2-20-CppForUnreal03.md` | 2026-02-20 |
| 04 | 참조와 const | ✅ 완료 | `2026-2-20-CppForUnreal04.md` | 2026-02-20 |
| 05 | 클래스와 OOP | ⬜ 대기 | | |
| 06 | 상속과 다형성 | ⬜ 대기 | | |
| 07 | 언리얼 매크로 | ⬜ 대기 | | |
| 08 | 클래스 계층과 프레임워크 | ⬜ 대기 | | |
| 09 | 메모리 관리 | ⬜ 대기 | | |
| 10 | 컨테이너와 문자열 | ⬜ 대기 | | |
| 11 | 캐스팅과 템플릿 | ⬜ 대기 | | |
| 12 | 델리게이트와 이벤트 | ⬜ 대기 | | |
| 13 | 람다, 콜백, 타이머 | ⬜ 대기 | | |
| 14 | 전처리기, 디버깅 | ⬜ 대기 | | |
| 15 | 실전 코드 패턴 총정리 | ⬜ 대기 | | |

---

## 6. 태그 계획

모든 포스트에 공통으로 들어가는 태그: `Unreal`, `C++`, `Unity`, `C#`

| 강 | 추가 태그 |
|----|----------|
| 01 | 변수, 타입, 함수 |
| 02 | 헤더, 컴파일, include, 전방선언 |
| 03 | 포인터, nullptr, new, delete |
| 04 | 참조, const, lvalue |
| 05 | 클래스, 생성자, 소멸자, OOP |
| 06 | 상속, virtual, override, 다형성 |
| 07 | UCLASS, UPROPERTY, UFUNCTION, 리플렉션 |
| 08 | AActor, UObject, 게임플레이 프레임워크 |
| 09 | GC, 스마트 포인터, RAII, 메모리 |
| 10 | TArray, TMap, FString, 컨테이너 |
| 11 | Cast, 템플릿, 캐스팅, RTTI |
| 12 | 델리게이트, 이벤트, 콜백, Delegate |
| 13 | 람다, Modern C++, move, 타이머 |
| 14 | UE_LOG, 매크로, 디버깅, 전처리기 |
| 15 | 패턴, Spawn, 입력, 데미지, 실전 |

---

## 7. 주의사항

- 언리얼 코드 예시는 UE5 기준으로 작성
- C# 코드는 Unity 2021+ 기준
- 각 강은 독립적으로 읽을 수 있지만, 1강부터 순서대로 읽는 것을 권장
- 시리즈 네비게이션은 `categories: [Unreal, Cpp]` 조합으로 자동 활성화
- 이미지는 `assets/img/post/Cpp/` 하위에 저장 (필요 시)
