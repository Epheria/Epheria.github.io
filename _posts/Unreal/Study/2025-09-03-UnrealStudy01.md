---
layout: post
title: 언리얼 C++ 첫걸음 - UHT, UObject, 문자열/로깅, GameInstance, 포인터·레퍼런스·매크로까지 한 번에
date: 2025-09-03 23:12:00 +0900
categories: [Unreal, Study]
tags: [Unreal, Study, UHT, UObject, FString, GameInstance, C++]     # TAG names should always be lowercase

toc: true
math: true
mermaid: true
---

<br>

## 목차

> [빌드 파이프라인 & UHT(Unreal Header Tool)](#1-빌드-파이프라인--uht)
> [헤더/CPP 파일 분리 원칙(IWYU), 전방 선언, include 순서, 모듈 매크로](#2-헤더cpp-분리-원칙iwyu-전방-선언-include-순서-모듈-매크로)
> [리플렉션 기초 : UCLASS/UPROPERTY/UFUNCTION/generated.h 규칙](#3-리플렉션-기초--uclassupropertyufunction--generatedh-규칙)
> [UObject생성,수명,GC - UPROPERTY/TObjectPtr/TweakObjectPtr](#4-uobject-생성-수명-gc---upropertytobjectptrtweakobjectptr)
> [문자열 로깅 - FString, FName, FText, TEXT/TCHAR](#문자열로깅-fstringfnameftext-texttchar-s와-fstring)
> [GameInstance와 Subsystem 초기화 흐름과 Super::Init()에 대해](#gameinstance와-subsystem-초기화-흐름과-super-호출)
> [언리얼 C++ 기초 : 포인터, 레퍼런스, 인라인, assertion](#cpp-기초언리얼-관점-포인터레퍼런스인라인빌드-매크로어설션)

<br>

---

## 1. 빌드 파이프라인 & UHT

- 언리얼은 블루프린트 노출, 직렬화, RPC 등을 C++ 메타데이터로 처리한다. 빌드는 두 단계로 진행된다.

> 1. UHT(언리얼 헤더 툴)가 `UCLASS/UPROPERTY/UFUNCTION`가 붙은 헤더를 스캔해 메타 데이터를 만들고, `*.generated.h/.cpp`파일을 생성한다.
> 2. 그다음 일반 C++ 컴파일이 진행된다.
{: .prompt-info }

<br>

- UHT는 UObject 기반 클래스의 메타데이터를 수집해서, 이를 토대로 C++ 코드를 자동 생성한다. 즉, 지정된 매크로를 사용해 빌드를 돌리면 추가 코드가 자동으로 붙는 구조다. 우리가 작성한 클래스 선언부 위에 붙은 매크로들이 단순 장식이 아니라, 실제로 엔진이 이해할 수 있는 코드를 만들어내는 트리거 역할을 한다.

- 핵심 규칙은 하나. 헤더의 `#include "X.generated.h`는 **항상 마지막**에 둔다. 그래야 UHT가 생성한 선언이 앞선 선언을 바탕으로 정확히 확장된다.

```cpp
#pragma once
#include "CoreMinimal.h"
#include "MyObject.generated.h" // 반드시 마지막

UCLASS()
class HELLOUNREAL_API UMyObject : public UObject
{
    GENERATED_BODY()
};

```

<br>

---

<br>

## 2. 헤더/CPP 분리 원칙(IWYU), 전방 선언, include 순서, 모듈 매크로

- 헤더는 가볍게, CPP는 무겁게. 이렇게 설계해야 빌드 시간이 안정된다.
- 헤더에는 `CoreMinimal.h`와 **최소한만 포함**된다.
- 가능한 한 **전방선언(Forward Declaration)**으로 참조를 해결한다.
- 실제 구현에서만 필요한 헤더는 **CPP에 포함**한다.
- CPP의 첫 번째 include는 항상 **자기 헤더**로 둔다. 빠진 의존성을 컴파일 타임에 즉시 드러나게 한다.
- 다른 모듈에서 사용할 타입/함수에는 `HELLOUNREAL_API` 같은 모듈 내보내기 매크로를 붙인다.
- 특히 다른 프로젝트의 스크립트를 적용시킬 때 현재 프로젝트의 매크로로 수정할 필요가있다.
- 해당 스크립트를 추가한 뒤 반드시 Tool 에 있는 **Refresh Rider/VS Uproject Project** 로 갱신 시켜줘야한다!

![Desktop View](/assets/img/post/unreal/unrealmac04.png){: : width="500" .normal }

```cpp
// MyFeature.h
#pragma once
#include "CoreMinimal.h"

UCLASS()
class HELLOUNREAL_API AMyFeature : public AActor
{
    GENERATED_BODY()

public:
    AMyFeature();
    virtual void BeginPlay() override;
private:
    UPROPERTY()
    TObjectPtr<UStaticMeshComponent> Mesh; // 포인터, 레퍼런스는 전방선언으로 충분하다.
};


// MyFeature.cpp
#include "MyFeature.h"                         // 자기 헤더
#include "Components/StaticMeshComponent.h"    // 구현에 필요한 헤더

AMyFeature::AMyFeature()
{
    Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
    SetRootComponent(Mesh);
}

```
- 값 멤버(예: `UStaticMeshComponent Mesh;`)처럼 완전한 정의가 필요한 경우엔 전방 선언만으로는 부족하므로 헤더에 실제 include가 필요하다.

<br>

---

<br>

## 3. 리플렉션 기초 : UCLASS/UPROPERTY/UFUNCTION & generated.h 규칙

- 언리얼 리플렉션은 런타임에 타입 정보를 조회하는 시스템이다. C++ 자체의 RTTI보다 훨씬 풍부하며, 블루프린트 바인딩·직렬화·GC·네트워크 리플리케이션 등 엔진의 핵심 기능이 전부 여기에 의존한다.

- 리플렉션에 참여하려면 반드시 매크로(`UCLASS`, `UPROPERTY`, `UFUNCTION`, `USTRUCT`, `UENUM`)를 붙여야 한다. 매크로가 없으면 UHT가 무시하고, 엔진도 해당 심볼을 인식하지 못한다.

<br>

### UCLASS

- 클래스 자체를 엔진에 등록하는 매크로. 괄호 안에 **지정자(Specifier)**를 넣어 동작을 제어한다.

```cpp
UCLASS(Blueprintable, BlueprintType, ClassGroup=(Custom), meta=(BlueprintSpawnableComponent))
class HELLOUNREAL_API UMyComponent : public UActorComponent
{
    GENERATED_BODY()
    // ...
};
```

> 자주 쓰는 UCLASS 지정자 정리
>
> `Blueprintable` — 블루프린트에서 이 클래스를 상속할 수 있게 허용
> `BlueprintType` — 블루프린트 변수 타입으로 사용 가능
> `Abstract` — 인스턴스를 직접 생성 불가, 서브클래스만 허용
> `NotBlueprintable` — 블루프린트 상속 차단
> `Transient` — 디스크에 직렬화하지 않음 (런타임 전용 객체에 유용)
> `Config=GameName` — ini 파일에서 설정 읽기 가능
> `meta=(BlueprintSpawnableComponent)` — 블루프린트 에디터의 Add Component 목록에 노출
{: .prompt-info }

<br>

### UPROPERTY

- 멤버 변수를 엔진에 등록한다. GC 루트 역할도 겸하므로, UObject 포인터 멤버는 **반드시** UPROPERTY를 붙여야 GC에서 누락되지 않는다.

```cpp
UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Stats", meta=(ClampMin="0.0", ClampMax="100.0"))
float Health = 100.f;

UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components")
TObjectPtr<UStaticMeshComponent> MeshComp;

UPROPERTY(Transient)
int32 CachedValue; // 직렬화에서 제외
```

> 자주 쓰는 UPROPERTY 지정자 정리
>
> **에디터 노출**: `EditAnywhere`, `EditDefaultsOnly`, `EditInstanceOnly`, `VisibleAnywhere`, `VisibleDefaultsOnly`
> **블루프린트 노출**: `BlueprintReadWrite`, `BlueprintReadOnly`
> **카테고리**: `Category="GroupName"` — 디테일 패널에서 그룹 분류
> **직렬화 제외**: `Transient` — 저장/로드 시 무시
> **리플리케이션**: `Replicated`, `ReplicatedUsing=OnRep_FuncName` — 네트워크 동기화
> **메타**: `meta=(AllowPrivateAccess="true")` — private 멤버를 블루프린트에 노출
{: .prompt-info }

<br>

### UFUNCTION

- 멤버 함수를 엔진에 등록한다. 블루프린트 호출, RPC, 델리게이트 바인딩 등에 사용된다.

```cpp
// 블루프린트에서 호출 가능
UFUNCTION(BlueprintCallable, Category="Combat")
void TakeDamage(float DamageAmount);

// 블루프린트에서 구현 가능 (C++에선 호출만)
UFUNCTION(BlueprintImplementableEvent, Category="Combat")
void OnDeath();

// C++ 기본 구현 + 블루프린트에서 오버라이드 가능
UFUNCTION(BlueprintNativeEvent, Category="Combat")
void OnHit();
void OnHit_Implementation(); // 실제 C++ 구현부

// 서버 RPC
UFUNCTION(Server, Reliable, WithValidation)
void ServerFireWeapon();
void ServerFireWeapon_Implementation();
bool ServerFireWeapon_Validate();
```

> 자주 쓰는 UFUNCTION 지정자 정리
>
> `BlueprintCallable` — 블루프린트에서 호출 가능
> `BlueprintPure` — 부작용 없는 순수 함수 (Getter 등)
> `BlueprintImplementableEvent` — C++에서 선언만, 구현은 블루프린트에서
> `BlueprintNativeEvent` — C++ 기본 구현 + 블루프린트 오버라이드 가능
> `Server / Client / NetMulticast` — 네트워크 RPC
> `Reliable / Unreliable` — RPC 신뢰성
> `Exec` — 콘솔 커맨드로 실행 가능
{: .prompt-info }

<br>

### USTRUCT & UENUM

- 구조체와 열거형도 리플렉션에 등록할 수 있다. USTRUCT는 UObject를 상속하지 않으므로 GC 대상이 아니지만, UPROPERTY가 붙은 UObject 포인터 멤버는 GC에서 추적된다.

```cpp
USTRUCT(BlueprintType)
struct FCharacterStats
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite)
    float MaxHP = 100.f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite)
    float Attack = 10.f;
};

UENUM(BlueprintType)
enum class ECharacterState : uint8
{
    Idle     UMETA(DisplayName="대기"),
    Moving   UMETA(DisplayName="이동"),
    Attack   UMETA(DisplayName="공격"),
    Dead     UMETA(DisplayName="사망")
};
```

- `USTRUCT`에는 반드시 `GENERATED_BODY()`가 필요하다. `UENUM`은 필요 없다.
- `UMETA(DisplayName="...")` 으로 에디터 표시명을 지정할 수 있다.

<br>

### GENERATED_BODY() 규칙 정리

> 1. `GENERATED_BODY()`는 클래스/구조체 선언 블록의 **맨 처음**(public/private 이전)에 둔다.
> 2. `#include "X.generated.h"`는 헤더의 **맨 마지막** include로 둔다.
> 3. `GENERATED_BODY()`는 기존의 `GENERATED_UCLASS_BODY()`를 대체한다. 레거시 코드가 아니면 `GENERATED_BODY()`만 사용한다.
> 4. `GENERATED_BODY()`를 빠뜨리면 UHT 빌드 에러가 발생하는데, 에러 메시지가 직관적이지 않아서 초보자가 원인을 찾기 어렵다. 클래스를 만들면 무조건 넣는 습관을 들이자.
{: .prompt-warning }

<br>

---

<br>

## 4. UObject 생성, 수명, GC - UPROPERTY/TObjectPtr/TWeakObjectPtr

- 언리얼의 UObject 기반 객체는 `new/delete`를 직접 쓰지 않는다. 엔진이 제공하는 팩토리 함수로 생성하고, GC(가비지 컬렉터)가 수명을 관리한다.

<br>

### 생성 함수 두 가지

```cpp
// 1. NewObject<T>() — 일반적인 UObject 생성
UMyObject* Obj = NewObject<UMyObject>(this); // Outer를 this로 지정

// 2. CreateDefaultSubobject<T>() — 생성자 안에서만 사용, 컴포넌트 초기화 전용
UStaticMeshComponent* Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
```

> `NewObject<T>(Outer)`
> - 어디서든 호출 가능
> - Outer는 이 객체의 "소유자". 보통 `this`나 `GetTransientPackage()`
>
> `CreateDefaultSubobject<T>(Name)`
> - **생성자에서만** 호출 가능 (CDO 생성 과정에서 실행)
> - 컴포넌트를 루트에 붙이거나 서브오브젝트를 설정할 때 사용
> - 생성자 밖에서 호출하면 크래시가 난다
{: .prompt-info }

<br>

- **AActor 파생 클래스**는 `NewObject`가 아니라 반드시 `GetWorld()->SpawnActor<T>()`로 생성한다. SpawnActor 내부에서 NewObject + 월드 등록 + BeginPlay 호출까지 처리된다.

```cpp
FActorSpawnParameters Params;
Params.Owner = this;
AMyEnemy* Enemy = GetWorld()->SpawnActor<AMyEnemy>(EnemyClass, &SpawnTransform, Params);
```

<br>

### GC(가비지 컬렉션)와 UPROPERTY

- 언리얼 GC는 **Mark-and-Sweep** 방식이다. 루트 셋(Root Set)에서 시작해서 UPROPERTY로 연결된 참조 체인을 따라 Mark하고, Mark되지 않은 UObject를 Sweep(해제)한다.

- 핵심: UObject 포인터를 UPROPERTY 없이 raw 포인터로만 들고 있으면 GC가 해당 참조를 모른다. 어느 순간 GC가 해당 객체를 수거해 버리면 **댕글링 포인터** 크래시가 난다.

```cpp
// 위험 — GC가 이 참조를 모름
UMyObject* DangerousPtr; // UPROPERTY 없음!

// 안전 — GC가 이 참조를 추적
UPROPERTY()
TObjectPtr<UMyObject> SafePtr;
```

<br>

### TObjectPtr vs Raw Pointer

- UE5부터 `TObjectPtr<T>`가 도입되었다. 에디터 빌드에서 **레이지 로딩**, **액세스 트래킹** 등 추가 기능을 제공하고, 쉬핑 빌드에서는 raw 포인터와 동일한 성능으로 컴파일된다.

```cpp
// UE5 권장 스타일
UPROPERTY()
TObjectPtr<UStaticMeshComponent> MeshComp;

// 함수 파라미터, 로컬 변수에서는 raw 포인터를 써도 된다
void DoSomething(UMyObject* Obj); // OK
```

> `TObjectPtr<T>`는 **UPROPERTY 멤버 변수**에 사용한다.
> 함수 파라미터, 로컬 변수, 반환 타입에서는 여전히 raw 포인터(`T*`)를 사용한다.
> 이 구분은 Epic의 코딩 스탠다드에 명시되어 있다.
{: .prompt-tip }

<br>

### TWeakObjectPtr — 약한 참조

- 소유권 없이 "살아있는지"만 확인하고 싶을 때 사용한다. GC가 해당 객체를 수거하면 자동으로 null이 된다.

```cpp
TWeakObjectPtr<AActor> WeakTarget;

void SetTarget(AActor* Target)
{
    WeakTarget = Target;
}

void Tick(float DeltaTime)
{
    if (WeakTarget.IsValid())
    {
        // 아직 살아있으므로 안전하게 사용
        FVector Loc = WeakTarget->GetActorLocation();
    }
    else
    {
        // 이미 파괴됨 — 새 타겟 탐색 등
    }
}
```

- AI에서 타겟 추적, UI에서 바인딩된 액터 참조, 캐시 등에 자주 사용된다.
- UPROPERTY가 아닌 곳에서 UObject를 참조할 때 raw 포인터 대신 TWeakObjectPtr을 쓰면 댕글링 포인터를 예방할 수 있다.

<br>

### TSoftObjectPtr — 소프트 레퍼런스

- 에셋을 직접 로드하지 않고 **경로만 저장**해두는 레퍼런스. 메모리에 올리지 않은 상태에서 필요할 때 비동기 로드할 수 있다.

```cpp
UPROPERTY(EditAnywhere, Category="Assets")
TSoftObjectPtr<UStaticMesh> MeshAsset;

void LoadMesh()
{
    if (!MeshAsset.IsNull())
    {
        UStaticMesh* Loaded = MeshAsset.LoadSynchronous(); // 동기 로드
        // 비동기: StreamableManager.RequestAsyncLoad(...)
    }
}
```

- 하드 레퍼런스(`TObjectPtr`)는 해당 객체가 메모리에 항상 로드되지만, 소프트 레퍼런스는 필요할 때만 로드하므로 메모리 관리에 유리하다. 특히 대규모 오픈월드에서 자주 활용된다.

<br>

### AddToRoot / RemoveFromRoot

- GC 루트 셋에 수동으로 등록/해제한다. 어디서도 UPROPERTY로 참조하지 않지만 살아있어야 하는 싱글턴 등에 사용된다.

```cpp
UMyManager* Mgr = NewObject<UMyManager>();
Mgr->AddToRoot(); // GC에서 보호

// 더 이상 필요 없을 때
Mgr->RemoveFromRoot(); // 다음 GC 사이클에서 수거 대상
```

> `AddToRoot()`는 **최후의 수단**이다. 대부분의 경우 UPROPERTY 참조 체인으로 해결하는 것이 맞고, AddToRoot를 남발하면 메모리 누수의 원인이 된다. 반드시 짝이 되는 `RemoveFromRoot()`를 호출해야 한다.
{: .prompt-warning }

<br>

---

<br>

## 문자열·로깅: FString/FName/FText, TEXT/TCHAR, `%s`와 `*FString`

- 언리얼에는 용도별로 세 가지 문자열 타입이 있다. 각각 쓰임새가 다르므로 제대로 구분해야 성능과 현지화 양쪽에서 문제가 없다.

<br>

### 세 가지 문자열 타입

| 타입 | 특징 | 용도 |
|------|------|------|
| `FString` | 힙 할당, 가변(mutable), `TArray<TCHAR>` 기반 | 일반적인 문자열 조작, 포맷팅, 출력 |
| `FName` | 해시 테이블 기반, 대소문자 구분 없음, 비교 극도로 빠름 | 에셋 이름, 본 이름, 소켓 이름, 태그 등 식별자 |
| `FText` | 현지화(로컬라이제이션) 지원, 불변(immutable) | UI 텍스트, 사용자에게 보여지는 모든 문자열 |

```cpp
FString Str = TEXT("Hello World");                  // 일반 문자열
FName   Name = FName(TEXT("WeaponSocket"));          // 식별자
FText   Text = FText::FromString(TEXT("체력: 100")); // UI 표시용
```

<br>

### TEXT() 매크로와 TCHAR

- `TEXT("...")` 매크로는 문자열 리터럴을 플랫폼에 맞는 **와이드 문자(TCHAR)**로 변환한다. Windows에서는 `wchar_t`, 그 외 플랫폼에서는 설정에 따라 UTF-16이나 UTF-32가 된다.

- 언리얼 코드에서 문자열 리터럴은 **항상 TEXT()로 감싸야** 한다. 안 감싸면 ANSI 리터럴이 되어 플랫폼 간 인코딩 불일치가 발생한다.

```cpp
// 올바름
FString Good = TEXT("안녕하세요");

// 위험 — ANSI 리터럴, 한글 깨질 수 있음
FString Bad = "안녕하세요";
```

<br>

### 문자열 간 변환

```cpp
// FString → FName
FName NameFromStr = FName(*MyString);

// FName → FString
FString StrFromName = MyName.ToString();

// FString → FText
FText TextFromStr = FText::FromString(MyString);

// FText → FString
FString StrFromText = MyText.ToString();

// FString → int32/float
int32 IntVal = FCString::Atoi(*MyString);
float FloatVal = FCString::Atof(*MyString);

// int32/float → FString
FString FromInt = FString::FromInt(42);
FString FromFloat = FString::SanitizeFloat(3.14f);
```

<br>

### FString::Printf — 포맷 문자열

- C의 `printf`와 동일한 형식으로 문자열을 조합한다.

```cpp
FString Msg = FString::Printf(TEXT("플레이어 %s의 체력: %.1f"), *PlayerName, Health);
```

> 주의: `%s` 포맷에 FString을 넘길 때는 반드시 `*FString`(역참조)을 해야 한다.
> `*FString`은 내부 `TCHAR*` 버퍼를 반환하는 `operator*` 오버로드다.
> `*` 없이 FString 객체를 그대로 넘기면 크래시가 난다.
{: .prompt-warning }

```cpp
FString Name = TEXT("Warrior");

// 올바름
UE_LOG(LogTemp, Log, TEXT("Name: %s"), *Name);

// 크래시! — FString 객체를 varargs에 그대로 넘김
// UE_LOG(LogTemp, Log, TEXT("Name: %s"), Name);
```

<br>

### UE_LOG — 로깅

- 카테고리와 심각도(Verbosity)를 지정하는 전통적 로깅 매크로.

```cpp
// 기본 로그 카테고리 사용
UE_LOG(LogTemp, Log, TEXT("일반 로그"));
UE_LOG(LogTemp, Warning, TEXT("경고: %s"), *WarningMsg);
UE_LOG(LogTemp, Error, TEXT("에러 발생! 코드: %d"), ErrorCode);

// 커스텀 로그 카테고리 선언 (헤더)
DECLARE_LOG_CATEGORY_EXTERN(LogMyGame, Log, All);
// (CPP)
DEFINE_LOG_CATEGORY(LogMyGame);
// 사용
UE_LOG(LogMyGame, Verbose, TEXT("상세 디버그 정보"));
```

> Verbosity 레벨 (낮을수록 중요)
>
> `Fatal` — 로그 출력 후 크래시 (프로그램 종료)
> `Error` — 빨간색, 심각한 문제
> `Warning` — 노란색, 주의 필요
> `Display` — 일반 출력 (화면에도 표시)
> `Log` — 파일에만 기록
> `Verbose` — 상세 디버그, 기본적으로 숨겨짐
> `VeryVerbose` — 가장 상세한 레벨
{: .prompt-info }

<br>

### UE_LOGFMT — 구조화 로깅 (UE 5.2+)

- UE 5.2부터 도입된 현대적 로깅. `printf` 스타일 대신 **이름 기반 포맷**을 지원하고, `*FString` 역참조가 필요 없다.

```cpp
#include "Logging/StructuredLog.h"

UE_LOGFMT(LogMyGame, Log, "Player {Name} took {Damage} damage", Name, Damage);
UE_LOGFMT(LogMyGame, Warning, "Health low: {Health}", Health);
```

- 변수 이름이 포맷 문자열의 `{}`와 매칭되므로 가독성이 좋고, FString을 역참조할 필요도 없다. 신규 프로젝트라면 UE_LOGFMT를 기본으로 사용하는 것을 추천한다.

<br>

### 화면 출력 디버그

```cpp
// 화면에 직접 텍스트 출력 (디버그용)
if (GEngine)
{
    GEngine->AddOnScreenDebugMessage(-1, 5.f, FColor::Green,
        FString::Printf(TEXT("HP: %.0f"), CurrentHP));
}
```

<br>

---

<br>

## GameInstance와 Subsystem: 초기화 흐름과 Super 호출

- `UGameInstance`는 게임 프로세스가 시작되고 종료될 때까지 단 하나만 존재하는 객체다. 레벨이 전환되어도 파괴되지 않기 때문에, **레벨 간 공유 데이터**(플레이어 인벤토리, 세이브 슬롯 관리, 글로벌 설정 등)를 보관하기에 적합하다.

<br>

### 기본 오버라이드와 초기화 흐름

```cpp
// MyGameInstance.h
#pragma once
#include "CoreMinimal.h"
#include "Engine/GameInstance.h"
#include "MyGameInstance.generated.h"

UCLASS()
class HELLOUNREAL_API UMyGameInstance : public UGameInstance
{
    GENERATED_BODY()

public:
    virtual void Init() override;
    virtual void OnStart() override;
    virtual void Shutdown() override;

    UPROPERTY(BlueprintReadWrite, Category="Save")
    int32 CurrentSaveSlot = 0;
};
```

```cpp
// MyGameInstance.cpp
#include "MyGameInstance.h"

void UMyGameInstance::Init()
{
    Super::Init(); // 반드시 호출!
    UE_LOG(LogTemp, Log, TEXT("GameInstance 초기화 완료"));
}

void UMyGameInstance::OnStart()
{
    Super::OnStart(); // 반드시 호출!
    // 첫 레벨 진입 시 실행할 로직
}

void UMyGameInstance::Shutdown()
{
    // 정리 로직
    UE_LOG(LogTemp, Log, TEXT("GameInstance 종료"));
    Super::Shutdown(); // 반드시 호출!
}
```

<br>

> **초기화 순서**
>
> 1. 엔진 시작 → `UGameInstance::Init()` 호출
> 2. 첫 번째 맵 로드 완료 → `UGameInstance::OnStart()` 호출
> 3. 게임 종료 시 → `UGameInstance::Shutdown()` 호출
{: .prompt-info }

<br>

### Super:: 호출이 왜 중요한가

- `Super::Init()`을 빠뜨리면 부모 클래스의 초기화 로직이 실행되지 않는다. GameInstance 수준에서는 Subsystem 초기화, 내부 엔진 바인딩 등이 Super에서 처리된다.

- 일반적인 규칙: **Init/BeginPlay 계열은 Super를 먼저 호출**하고, **Shutdown/EndPlay 계열은 자기 정리를 먼저 한 다음 Super를 마지막에 호출**한다.

```cpp
void AMyActor::BeginPlay()
{
    Super::BeginPlay(); // 부모 먼저
    // 내 초기화 로직
}

void AMyActor::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    // 내 정리 로직 먼저
    Super::EndPlay(EndPlayReason); // 부모 마지막
}
```

<br>

### Subsystem 개요

- UE 4.24부터 도입된 Subsystem은 특정 Outer 객체의 수명에 자동으로 맞춰지는 **싱글턴 패턴 대체물**이다. 직접 생성/해제할 필요 없이, 엔진이 Outer의 생성/파괴에 맞춰 자동으로 Initialize/Deinitialize를 호출해준다.

| Subsystem 타입 | Outer (수명 기준) | 인스턴스 수 |
|---|---|---|
| `UEngineSubsystem` | `GEngine` | 1개 (프로세스 전체) |
| `UEditorSubsystem` | `GEditor` | 1개 (에디터 전용) |
| `UGameInstanceSubsystem` | `UGameInstance` | 1개 (게임 인스턴스당) |
| `UWorldSubsystem` | `UWorld` | 월드당 1개 |
| `ULocalPlayerSubsystem` | `ULocalPlayer` | 로컬 플레이어당 1개 |

<br>

```cpp
// MySubsystem.h
#pragma once
#include "Subsystems/GameInstanceSubsystem.h"
#include "MySubsystem.generated.h"

UCLASS()
class HELLOUNREAL_API UMySubsystem : public UGameInstanceSubsystem
{
    GENERATED_BODY()

public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;

    void DoSomething();

private:
    int32 SomeData = 0;
};
```

```cpp
// 사용법 — 어디서든 접근 가능
UMySubsystem* Sub = GetGameInstance()->GetSubsystem<UMySubsystem>();
Sub->DoSomething();
```

- Subsystem의 장점은 모듈 간 결합도를 낮추면서도 전역 접근이 가능하다는 것이다. 싱글턴의 편리함은 가져가되, 수명 관리는 엔진에 위임하는 구조다.

<br>

---

<br>

## CPP 기초(언리얼 관점): 포인터·레퍼런스·인라인·빌드 매크로·어설션

- 표준 C++ 문법이지만 언리얼에서 특별히 자주 쓰이거나, 언리얼만의 래퍼가 있는 항목들을 정리한다.

<br>

### 포인터 (Pointer)

- 언리얼에서 포인터는 크게 네 종류로 구분된다.

| 종류 | 용도 | GC 추적 |
|------|------|---------|
| `T*` (raw) | 함수 파라미터, 로컬 변수 | X (UPROPERTY 안 붙이면 추적 안 됨) |
| `TObjectPtr<T>` | UPROPERTY 멤버 변수 (UE5) | O |
| `TSharedPtr<T>` | 비-UObject의 공유 소유권 | X (자체 참조 카운팅) |
| `TUniquePtr<T>` | 비-UObject의 단독 소유권 | X |

```cpp
// TSharedPtr — UObject가 아닌 일반 C++ 클래스에 사용
TSharedPtr<FMyData> SharedData = MakeShared<FMyData>();
TWeakPtr<FMyData> WeakData = SharedData; // 약한 참조

// TUniquePtr — 소유권 이전만 가능, 복사 불가
TUniquePtr<FMyData> UniqueData = MakeUnique<FMyData>();
TUniquePtr<FMyData> Moved = MoveTemp(UniqueData); // 소유권 이전
```

> `TSharedPtr`/`TUniquePtr`는 **UObject가 아닌** 일반 C++ 클래스에만 사용한다.
> UObject는 GC가 수명을 관리하므로, TSharedPtr로 감싸면 이중 해제 위험이 있다.
{: .prompt-warning }

<br>

### 레퍼런스 (Reference)

- 언리얼에서 const 레퍼런스는 대형 구조체(FVector, FTransform, FString 등)를 복사 없이 전달할 때 필수적이다.

```cpp
// 값 복사 — FString 복사 비용 발생
void PrintName(FString Name);

// const 레퍼런스 — 복사 없음, 읽기만 가능
void PrintName(const FString& Name);

// 비-const 레퍼런스 — 호출자의 값을 수정
void GetName(FString& OutName);

// 출력 파라미터 관례: Out 접두사를 붙인다
void CalculateDamage(float InBaseDamage, float& OutFinalDamage);
```

> 언리얼 코딩 스탠다드에서 출력 파라미터에는 `Out` 접두사를 붙이는 것이 관례다.
> `const&`는 함수 파라미터의 기본 선택지. 기본 타입(int32, float, bool 등)만 값으로 전달한다.
{: .prompt-tip }

<br>

### 인라인 (FORCEINLINE)

- 표준 C++의 `inline`은 컴파일러에 대한 힌트일 뿐이지만, 언리얼의 `FORCEINLINE`은 플랫폼별로 `__forceinline`(MSVC)이나 `__attribute__((always_inline))`(GCC/Clang)으로 확장되어 **강제 인라인**을 시도한다.

```cpp
FORCEINLINE float GetHealthPercent() const
{
    return MaxHealth > 0.f ? CurrentHealth / MaxHealth : 0.f;
}
```

- 호출 빈도가 극히 높고 함수 본체가 작은 경우(Getter, 유틸리티 계산 등)에 사용한다.
- 남용하면 코드 크기가 커지고 I-cache 미스가 증가하므로, 프로파일링 결과를 기반으로 적용하는 것이 바람직하다.

<br>

### 빌드 매크로

- 빌드 설정에 따라 조건부로 코드를 포함/제외하는 매크로들이 있다.

```cpp
#if WITH_EDITOR
    // 에디터 빌드에서만 컴파일 (패키지 빌드에서는 제외)
    void EditorOnlyFunction();
#endif

#if UE_BUILD_SHIPPING
    // 쉬핑 빌드에서만 컴파일
#endif

#if !UE_BUILD_SHIPPING
    // 쉬핑이 아닌 모든 빌드 (개발용 디버그 코드)
    UE_LOG(LogTemp, Verbose, TEXT("디버그 정보: %d"), DebugValue);
#endif

#if UE_BUILD_DEBUG
    // 디버그 빌드에서만 컴파일
#endif
```

| 매크로 | 참인 경우 |
|--------|----------|
| `WITH_EDITOR` | 에디터 빌드 (PIE 포함) |
| `UE_BUILD_DEBUG` | Debug 설정 |
| `UE_BUILD_DEVELOPMENT` | Development 설정 |
| `UE_BUILD_TEST` | Test 설정 |
| `UE_BUILD_SHIPPING` | Shipping 설정 |
| `UE_SERVER` | 데디케이티드 서버 빌드 |

<br>

### 어설션 (Assertion)

- 언리얼은 표준 `assert()` 대신 자체 매크로를 제공한다. 상황별로 적절한 것을 골라 사용해야 한다.

```cpp
// check — 조건 실패 시 크래시 (디버그/개발 빌드에서)
check(Ptr != nullptr);
checkf(Health >= 0.f, TEXT("Health가 음수: %f"), Health);

// verify — check와 동일하지만, 쉬핑 빌드에서도 표현식 자체는 실행됨
verify(ImportantFunction()); // 쉬핑에서도 함수는 호출됨, 실패 시 무시

// ensure — 조건 실패 시 크래시 대신 경고 로그 + 콜스택 출력 (한 번만)
if (ensure(Ptr != nullptr))
{
    Ptr->DoSomething();
}
ensureMsgf(Value > 0, TEXT("Value가 0 이하: %d"), Value);

// unimplemented — 아직 구현하지 않은 함수에 넣어두는 매크로 (호출 시 크래시)
void AMyActor::NotYetDone()
{
    unimplemented();
}
```

> **check vs ensure 선택 기준**
>
> `check` — "이 조건이 거짓이면 프로그램 상태가 완전히 망가진 것이므로 즉시 중단해야 한다"
> `ensure` — "이 조건이 거짓이면 버그이지만, 크래시 없이 로그를 남기고 복구를 시도할 수 있다"
>
> `check`는 쉬핑 빌드에서 **표현식 자체가 컴파일에서 제거**되므로, 사이드 이펙트가 있는 표현식을 check에 넣으면 안 된다.
> `verify`는 쉬핑에서도 표현식은 실행되므로, 사이드 이펙트가 있는 경우에 사용한다.
{: .prompt-warning }

<br>

### MoveTemp — 언리얼의 std::move

- 표준 C++의 `std::move` 대신 언리얼에서는 `MoveTemp()`를 사용한다. 동작은 동일하게 lvalue를 rvalue 레퍼런스로 캐스팅하여 이동 시멘틱을 활성화한다.

```cpp
TArray<FString> Source = { TEXT("A"), TEXT("B"), TEXT("C") };
TArray<FString> Dest = MoveTemp(Source); // Source는 이후 빈 상태
```

- 언리얼 코딩 스탠다드에서 `std::move` 대신 `MoveTemp`를 권장한다. 이유는 디버그 빌드에서 추가적인 검증(const 객체 이동 방지 등)을 수행하기 때문이다.
