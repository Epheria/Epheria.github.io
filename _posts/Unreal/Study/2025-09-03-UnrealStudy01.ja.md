---
layout: post
title: "Unreal C++ 入門：UHT、UObject、文字列/ログ、GameInstance、ポインタ・参照・マクロまで一気に"
date: 2025-09-03 23:12:00 +0900
categories: [Unreal, Study]
tags: [Unreal, Study, UHT, UObject, FString, GameInstance, C++]
lang: ja
difficulty: intermediate
toc: true
math: true
mermaid: true
---

<br>

## 目次

> [ビルドパイプライン & UHT (Unreal Header Tool)](#1-ビルドパイプライン--uht)
> [ヘッダー/CPP 分離原則 (IWYU)、前方宣言、include 順序、モジュールマクロ](#2-ヘッダーcpp-分離原則iwyu前方宣言include-順序モジュールマクロ)
> [リフレクション基礎：UCLASS/UPROPERTY/UFUNCTION/generated.h ルール](#3-リフレクション基礎--uclassupropertyufunction--generatedh-ルール)
> [UObject 生成、寿命、GC - UPROPERTY/TObjectPtr/TWeakObjectPtr](#4-uobject-生成寿命gc---upropertytobjectptrtweakobjectptr)
> [文字列・ロギング - FString, FName, FText, TEXT/TCHAR](#文字列ロギング-fstringfnameftext-texttchar-sとfstring)
> [GameInstanceとSubsystem 初期化フローと Super::Init()](#gameinstanceとsubsystem-初期化フローと-super-呼び出し)
> [Unreal C++ 基礎：ポインタ、参照、インライン、アサーション](#cpp-基礎unreal-観点ポインタ参照インラインビルドマクロアサーション)

<br>

---

## 1. ビルドパイプライン & UHT

- Unrealはブループリント露出、直列化、RPCなどをC++メタデータで処理します。ビルドは2段階で進行します。

> 1. **UHT (Unreal Header Tool)** が `UCLASS/UPROPERTY/UFUNCTION` の付いたヘッダーをスキャンしてメタデータを作成し、 `*.generated.h/.cpp` ファイルを生成します。
> 2. その後、通常のC++コンパイルが進行します。
{: .prompt-info }

<br>

- UHTはUObjectベースのクラスのメタデータを収集し、それを基にC++コードを自動生成します。つまり、指定されたマクロを使用してビルドを回すと追加コードが自動的に付く構造です。私たちが作成したクラス宣言部の上に付いたマクロは単なる装飾ではなく、実際にエンジンが理解できるコードを作り出すトリガーの役割を果たします。

- 核心ルールは一つ。ヘッダーの `#include "X.generated.h"` は **常に最後** に置きます。そうして初めて、UHTが生成した宣言が先行する宣言を基に正確に拡張されます。

```cpp
#pragma once
#include "CoreMinimal.h"
#include "MyObject.generated.h" // 必ず最後

UCLASS()
class HELLOUNREAL_API UMyObject : public UObject
{
    GENERATED_BODY()
};
```

<br>

---

<br>

## 2. ヘッダー/CPP 分離原則 (IWYU)、前方宣言、include 順序、モジュールマクロ

- ヘッダーは軽く、CPPは重く。このように設計してこそビルド時間が安定します。
- ヘッダーには `CoreMinimal.h` と **最小限のみ** 含めます。
- 可能な限り **前方宣言 (Forward Declaration)** で参照を解決します。
- 実際の実装でのみ必要なヘッダーは **CPPに含めます**。
- CPPの最初のincludeは常に **自分のヘッダー** にします。欠落した依存性をコンパイル時に即座に明らかにします。
- 他のモジュールで使用するタイプ/関数には `HELLOUNREAL_API` のようなモジュールエクスポートマクロを付けます。
- 特に他のプロジェクトのスクリプトを適用する際、現在のプロジェクトのマクロに修正する必要があります。
- 該当スクリプトを追加した後、必ずToolにある **Refresh Rider/VS Uproject Project** で更新してください！

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
    TObjectPtr<UStaticMeshComponent> Mesh; // ポインタ、参照は前方宣言で十分
};


// MyFeature.cpp
#include "MyFeature.h"                         // 自分のヘッダー
#include "Components/StaticMeshComponent.h"    // 実装に必要なヘッダー

AMyFeature::AMyFeature()
{
    Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
    SetRootComponent(Mesh);
}
```
- 値メンバー（例：`UStaticMeshComponent Mesh;`）のように完全な定義が必要な場合には前方宣言だけでは不十分なため、ヘッダーに実際のincludeが必要です。

<br>

---

<br>

## 3. リフレクション基礎：UCLASS/UPROPERTY/UFUNCTION & generated.h ルール

- Unrealリフレクションはランタイムにタイプ情報を照会するシステムです。C++自体のRTTIよりはるかに豊富で、ブループリントバインディング・直列化・GC・ネットワークリプリケーションなどエンジンの核心機能がすべてこれに依存しています。

- リフレクションに参加するには必ずマクロ（`UCLASS`, `UPROPERTY`, `UFUNCTION`, `USTRUCT`, `UENUM`）を付ける必要があります。マクロがないとUHTが無視し、エンジンも該当シンボルを認識できません。

<br>

### UCLASS

- クラス自体をエンジンに登録するマクロ。括弧の中に **指定子 (Specifier)** を入れて動作を制御します。

```cpp
UCLASS(Blueprintable, BlueprintType, ClassGroup=(Custom), meta=(BlueprintSpawnableComponent))
class HELLOUNREAL_API UMyComponent : public UActorComponent
{
    GENERATED_BODY()
    // ...
};
```

> よく使う UCLASS 指定子まとめ
>
> `Blueprintable` — ブループリントでこのクラスを継承することを許可
> `BlueprintType` — ブループリント変数タイプとして使用可能
> `Abstract` — インスタンスを直接生成不可、サブクラスのみ許可
> `NotBlueprintable` — ブループリント継承遮断
> `Transient` — ディスクに直列化しない（ランタイム専用オブジェクトに有用）
> `Config=GameName` — iniファイルから設定読み込み可能
> `meta=(BlueprintSpawnableComponent)` — ブループリントエディタのAdd Componentリストに露出
{: .prompt-info }

<br>

### UPROPERTY

- メンバー変数をエンジンに登録します。GCルートの役割も兼ねるため、UObjectポインタメンバーは **必ず** UPROPERTYを付けないとGCから漏れてしまいます。

```cpp
UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Stats", meta=(ClampMin="0.0", ClampMax="100.0"))
float Health = 100.f;

UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components")
TObjectPtr<UStaticMeshComponent> MeshComp;

UPROPERTY(Transient)
int32 CachedValue; // 直列化から除外
```

> よく使う UPROPERTY 指定子まとめ
>
> **エディタ露出**: `EditAnywhere`, `EditDefaultsOnly`, `EditInstanceOnly`, `VisibleAnywhere`, `VisibleDefaultsOnly`
> **ブループリント露出**: `BlueprintReadWrite`, `BlueprintReadOnly`
> **カテゴリ**: `Category="GroupName"` — 詳細パネルでのグループ分類
> **直列化除外**: `Transient` — 保存/ロード時に無視
> **リプリケーション**: `Replicated`, `ReplicatedUsing=OnRep_FuncName` — ネットワーク同期
> **メタ**: `meta=(AllowPrivateAccess="true")` — privateメンバーをブループリントに露出
{: .prompt-info }

<br>

### UFUNCTION

- メンバー関数をエンジンに登録します。ブループリント呼び出し、RPC、デリゲートバインディングなどに使用されます。

```cpp
// ブループリントから呼び出し可能
UFUNCTION(BlueprintCallable, Category="Combat")
void TakeDamage(float DamageAmount);

// ブループリントで実装可能（C++では呼び出しのみ）
UFUNCTION(BlueprintImplementableEvent, Category="Combat")
void OnDeath();

// C++基本実装 + ブループリントでオーバーライド可能
UFUNCTION(BlueprintNativeEvent, Category="Combat")
void OnHit();
void OnHit_Implementation(); // 実際のC++実装部

// サーバーRPC
UFUNCTION(Server, Reliable, WithValidation)
void ServerFireWeapon();
void ServerFireWeapon_Implementation();
bool ServerFireWeapon_Validate();
```

> よく使う UFUNCTION 指定子まとめ
>
> `BlueprintCallable` — ブループリントから呼び出し可能
> `BlueprintPure` — 副作用のない純粋関数（Getterなど）
> `BlueprintImplementableEvent` — C++で宣言のみ、実装はブループリントで
> `BlueprintNativeEvent` — C++基本実装 + ブループリントオーバーライド可能
> `Server / Client / NetMulticast` — ネットワークRPC
> `Reliable / Unreliable` — RPC信頼性
> `Exec` — コンソールコマンドで実行可能
{: .prompt-info }

<br>

### USTRUCT & UENUM

- 構造体と列挙型もリフレクションに登録できます。USTRUCTはUObjectを継承しないためGC対象ではありませんが、UPROPERTYが付いたUObjectポインタメンバーはGCで追跡されます。

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
    Idle     UMETA(DisplayName="待機"),
    Moving   UMETA(DisplayName="移動"),
    Attack   UMETA(DisplayName="攻撃"),
    Dead     UMETA(DisplayName="死亡")
};
```

- `USTRUCT` には必ず `GENERATED_BODY()` が必要です。 `UENUM` は必要ありません。
- `UMETA(DisplayName="...")` でエディタ表示名を指定できます。

<br>

### GENERATED_BODY() ルールまとめ

> 1. `GENERATED_BODY()` はクラス/構造体宣言ブロックの **一番最初** （public/private以前）に置きます。
> 2. `#include "X.generated.h"` はヘッダーの **一番最後** のincludeとして置きます。
> 3. `GENERATED_BODY()` は既存の `GENERATED_UCLASS_BODY()` を代替します。レガシーコードでなければ `GENERATED_BODY()` のみ使用します。
> 4. `GENERATED_BODY()` を忘れるとUHTビルドエラーが発生しますが、エラーメッセージが直感的ではないため初心者が原因を見つけるのが難しいです。クラスを作る時は無条件に入れる習慣をつけましょう。
{: .prompt-warning }

<br>

---

<br>

## 4. UObject 生成、寿命、GC - UPROPERTY/TObjectPtr/TWeakObjectPtr

- UnrealのUObjectベースオブジェクトは `new/delete` を直接使いません。エンジンが提供するファクトリー関数で生成し、GC（ガベージコレクタ）が寿命を管理します。

<br>

### 生成関数 2つ

```cpp
// 1. NewObject<T>() — 一般的なUObject生成
UMyObject* Obj = NewObject<UMyObject>(this); // Outerをthisに指定

// 2. CreateDefaultSubobject<T>() — コンストラクタ内でのみ使用、コンポーネント初期化専用
UStaticMeshComponent* Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
```

> `NewObject<T>(Outer)`
> - どこでも呼び出し可能
> - Outerはこのオブジェクトの「所有者」。通常 `this` や `GetTransientPackage()`
>
> `CreateDefaultSubobject<T>(Name)`
> - **コンストラクタでのみ** 呼び出し可能（CDO生成過程で実行）
> - コンポーネントをルートに付けたりサブオブジェクトを設定する時に使用
> - コンストラクタ外で呼び出すとクラッシュします
{: .prompt-info }

<br>

- **AActor 派生クラス** は `NewObject` ではなく必ず `GetWorld()->SpawnActor<T>()` で生成します。SpawnActor内部でNewObject + ワールド登録 + BeginPlay呼び出しまで処理されます。

```cpp
FActorSpawnParameters Params;
Params.Owner = this;
AMyEnemy* Enemy = GetWorld()->SpawnActor<AMyEnemy>(EnemyClass, &SpawnTransform, Params);
```

<br>

### GC (ガベージコレクション) と UPROPERTY

- Unreal GCは **Mark-and-Sweep** 方式です。ルートセット（Root Set）から始めてUPROPERTYで接続された参照チェーンに沿ってMarkし、MarkされていないUObjectをSweep（解放）します。

- 核心：UObjectポインタをUPROPERTYなしでrawポインタとしてのみ持っていると、GCがその参照を知りません。ある瞬間GCが該当オブジェクトを回収してしまうと **ダングリングポインタ** クラッシュが発生します。

```cpp
// 危険 — GCがこの参照を知らない
UMyObject* DangerousPtr; // UPROPERTYなし！

// 安全 — GCがこの参照を追跡
UPROPERTY()
TObjectPtr<UMyObject> SafePtr;
```

<br>

### TObjectPtr vs Raw Pointer

- UE5から `TObjectPtr<T>` が導入されました。エディタビルドで **レイジーローディング**、 **アクセストラッキング** などの追加機能を提供し、シッピングビルドではrawポインタと同じ性能でコンパイルされます。

```cpp
// UE5 推奨スタイル
UPROPERTY()
TObjectPtr<UStaticMeshComponent> MeshComp;

// 関数パラメータ、ローカル変数ではrawポインタを使っても良い
void DoSomething(UMyObject* Obj); // OK
```

> `TObjectPtr<T>` は **UPROPERTY メンバー変数** に使用します。
> 関数パラメータ、ローカル変数、戻り値タイプでは依然としてrawポインタ（`T*`）を使用します。
> この区分はEpicのコーディングスタンダードに明示されています。
{: .prompt-tip }

<br>

### TWeakObjectPtr — 弱い参照

- 所有権なしに「生きているか」だけを確認したい場合に使用します。GCが該当オブジェクトを回収すると自動的にnullになります。

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
        // まだ生きているので安全に使用
        FVector Loc = WeakTarget->GetActorLocation();
    }
    else
    {
        // すでに破壊された — 新しいターゲット探索など
    }
}
```

- AIでターゲット追跡、UIでバインドされたアクタ参照、キャッシュなどによく使用されます。
- UPROPERTYではない場所でUObjectを参照する際、rawポインタの代わりにTWeakObjectPtrを使えばダングリングポインタを予防できます。

<br>

### TSoftObjectPtr — ソフトリファレンス

- アセットを直接ロードせず **パスのみ保存** しておくリファレンス。メモリに上げていない状態で必要な時に非同期ロードできます。

```cpp
UPROPERTY(EditAnywhere, Category="Assets")
TSoftObjectPtr<UStaticMesh> MeshAsset;

void LoadMesh()
{
    if (!MeshAsset.IsNull())
    {
        UStaticMesh* Loaded = MeshAsset.LoadSynchronous(); // 同期ロード
        // 非同期: StreamableManager.RequestAsyncLoad(...)
    }
}
```

- ハードリファレンス（`TObjectPtr`）は該当オブジェクトがメモリに常にロードされますが、ソフトリファレンスは必要な時だけロードするためメモリ管理に有利です。特に大規模オープンワールドでよく活用されます。

<br>

### AddToRoot / RemoveFromRoot

- GCルートセットに手動で登録/解除します。どこからもUPROPERTYで参照していないが生きている必要があるシングルトンなどに使用されます。

```cpp
UMyManager* Mgr = NewObject<UMyManager>();
Mgr->AddToRoot(); // GCから保護

// もう必要ない時
Mgr->RemoveFromRoot(); // 次のGCサイクルで回収対象
```

> `AddToRoot()` は **最後の手段** です。ほとんどの場合UPROPERTY参照チェーンで解決するのが正しく、AddToRootを乱発するとメモリリークの原因になります。必ず対になる `RemoveFromRoot()` を呼び出す必要があります。
{: .prompt-warning }

<br>

---

<br>

## 文字列・ロギング：FString/FName/FText, TEXT/TCHAR, `%s` と `*FString`

- Unrealには用途別に3つの文字列タイプがあります。それぞれ使い道が異なるため、しっかり区別しなければ性能とローカライゼーションの両方で問題が発生しません。

<br>

### 3つの文字列タイプ

| タイプ | 特徴 | 用途 |
|------|------|------|
| `FString` | ヒープ割り当て、可変(mutable)、`TArray<TCHAR>` ベース | 一般的な文字列操作、フォーマット、出力 |
| `FName` | ハッシュテーブルベース、大文字小文字区別なし、比較極めて高速 | アセット名、ボーン名、ソケット名、タグなどの識別子 |
| `FText` | ローカライゼーション（多言語）対応、不変(immutable) | UIテキスト、ユーザーに表示されるすべての文字列 |

```cpp
FString Str = TEXT("Hello World");                  // 一般文字列
FName   Name = FName(TEXT("WeaponSocket"));          // 識別子
FText   Text = FText::FromString(TEXT("体力: 100")); // UI表示用
```

<br>

### TEXT() マクロと TCHAR

- `TEXT("...")` マクロは文字列リテラルをプラットフォームに合った **ワイド文字(TCHAR)** に変換します。Windowsでは `wchar_t`、その他のプラットフォームでは設定によりUTF-16やUTF-32になります。

- Unrealコードで文字列リテラルは **常にTEXT()で囲む** 必要があります。囲まないとANSIリテラルになり、プラットフォーム間のエンコーディング不一致が発生します。

```cpp
// 正しい
FString Good = TEXT("こんにちは");

// 危険 — ANSIリテラル、文字化けする可能性あり
FString Bad = "こんにちは";
```

<br>

### 文字列間の変換

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

### FString::Printf — フォーマット文字列

- Cの `printf` と同じ形式で文字列を組み合わせます。

```cpp
FString Msg = FString::Printf(TEXT("プレイヤー %s の体力: %.1f"), *PlayerName, Health);
```

> 注意：`%s` フォーマットにFStringを渡す時は必ず `*FString`（逆参照）をする必要があります。
> `*FString` は内部 `TCHAR*` バッファを返す `operator*` オーバーロードです。
> `*` なしでFStringオブジェクトをそのまま渡すとクラッシュします。
{: .prompt-warning }

```cpp
FString Name = TEXT("Warrior");

// 正しい
UE_LOG(LogTemp, Log, TEXT("Name: %s"), *Name);

// クラッシュ！ — FStringオブジェクトをvarargsにそのまま渡した
// UE_LOG(LogTemp, Log, TEXT("Name: %s"), Name);
```

<br>

### UE_LOG — ロギング

- カテゴリと重要度（Verbosity）を指定する伝統的なロギングマクロ。

```cpp
// デフォルトログカテゴリ使用
UE_LOG(LogTemp, Log, TEXT("一般ログ"));
UE_LOG(LogTemp, Warning, TEXT("警告: %s"), *WarningMsg);
UE_LOG(LogTemp, Error, TEXT("エラー発生！コード: %d"), ErrorCode);

// カスタムログカテゴリ宣言（ヘッダー）
DECLARE_LOG_CATEGORY_EXTERN(LogMyGame, Log, All);
// (CPP)
DEFINE_LOG_CATEGORY(LogMyGame);
// 使用
UE_LOG(LogMyGame, Verbose, TEXT("詳細デバッグ情報"));
```

> Verbosity レベル（低いほど重要）
>
> `Fatal` — ログ出力後クラッシュ（プログラム終了）
> `Error` — 赤色、深刻な問題
> `Warning` — 黄色、注意必要
> `Display` — 一般出力（画面にも表示）
> `Log` — ファイルにのみ記録
> `Verbose` — 詳細デバッグ、基本的に隠されている
> `VeryVerbose` — 最も詳細なレベル
{: .prompt-info }

<br>

### UE_LOGFMT — 構造化ロギング (UE 5.2+)

- UE 5.2から導入された現代的ロギング。 `printf` スタイルの代わりに **名前ベースフォーマット** をサポートし、 `*FString` 逆参照が必要ありません。

```cpp
#include "Logging/StructuredLog.h"

UE_LOGFMT(LogMyGame, Log, "Player {Name} took {Damage} damage", Name, Damage);
UE_LOGFMT(LogMyGame, Warning, "Health low: {Health}", Health);
```

- 変数名がフォーマット文字列の `{}` とマッチするため可読性が良く、FStringを逆参照する必要もありません。新規プロジェクトならUE_LOGFMTを基本として使用することをお勧めします。

<br>

### 画面出力デバッグ

```cpp
// 画面に直接テキスト出力（デバッグ用）
if (GEngine)
{
    GEngine->AddOnScreenDebugMessage(-1, 5.f, FColor::Green,
        FString::Printf(TEXT("HP: %.0f"), CurrentHP));
}
```

<br>

---

<br>

## GameInstanceとSubsystem：初期化フローとSuper呼び出し

- `UGameInstance` はゲームプロセスが開始されて終了するまで一つだけ存在するオブジェクトです。レベルが切り替わっても破壊されないため、 **レベル間共有データ** （プレイヤーインベントリ、セーブスロット管理、グローバル設定など）を保管するのに適しています。

<br>

### 基本オーバーライドと初期化フロー

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
    Super::Init(); // 必ず呼び出し！
    UE_LOG(LogTemp, Log, TEXT("GameInstance 初期化完了"));
}

void UMyGameInstance::OnStart()
{
    Super::OnStart(); // 必ず呼び出し！
    // 最初のレベル進入時に実行するロジック
}

void UMyGameInstance::Shutdown()
{
    // 整理ロジック
    UE_LOG(LogTemp, Log, TEXT("GameInstance 終了"));
    Super::Shutdown(); // 必ず呼び出し！
}
```

<br>

> **初期化順序**
>
> 1. エンジン開始 → `UGameInstance::Init()` 呼び出し
> 2. 最初のマップロード完了 → `UGameInstance::OnStart()` 呼び出し
> 3. ゲーム終了時 → `UGameInstance::Shutdown()` 呼び出し
{: .prompt-info }

<br>

### Super:: 呼び出しがなぜ重要なのか

- `Super::Init()` を忘れると親クラスの初期化ロジックが実行されません。GameInstanceレベルではSubsystem初期化、内部エンジンバインディングなどがSuperで処理されます。

- 一般的なルール： **Init/BeginPlay系はSuperを先に呼び出し**、 **Shutdown/EndPlay系は自分の整理を先にしてからSuperを最後に呼び出し** ます。

```cpp
void AMyActor::BeginPlay()
{
    Super::BeginPlay(); // 親を先に
    // 私の初期化ロジック
}

void AMyActor::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    // 私の整理ロジックを先に
    Super::EndPlay(EndPlayReason); // 親を最後に
}
```

<br>

### Subsystem 概要

- UE 4.24から導入されたSubsystemは、特定のOuterオブジェクトの寿命に自動的に合わせられる **シングルトンパターンの代替物** です。直接生成/解除する必要なく、エンジンがOuterの生成/破壊に合わせて自動的にInitialize/Deinitializeを呼び出してくれます。

| Subsystem タイプ | Outer (寿命基準) | インスタンス数 |
|---|---|---|
| `UEngineSubsystem` | `GEngine` | 1個 (プロセス全体) |
| `UEditorSubsystem` | `GEditor` | 1個 (エディタ専用) |
| `UGameInstanceSubsystem` | `UGameInstance` | 1個 (ゲームインスタンスごと) |
| `UWorldSubsystem` | `UWorld` | ワールドごと1個 |
| `ULocalPlayerSubsystem` | `ULocalPlayer` | ローカルプレイヤーごと1個 |

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
// 使用法 — どこでもアクセス可能
UMySubsystem* Sub = GetGameInstance()->GetSubsystem<UMySubsystem>();
Sub->DoSomething();
```

- Subsystemの長所は、モジュール間の結合度を下げながらもグローバルアクセスが可能だということです。シングルトンの利便性は維持しつつ、寿命管理はエンジンに委任する構造です。

<br>

---

<br>

## CPP 基礎(Unreal観点)：ポインタ・参照・インライン・ビルドマクロ・アサーション

- 標準C++文法ですがUnrealで特によく使われたり、Unrealだけのラッパーがある項目を整理します。

<br>

### ポインタ (Pointer)

- Unrealでポインタは大きく4種類に区分されます。

| 種類 | 用途 | GC追跡 |
|------|------|---------|
| `T*` (raw) | 関数パラメータ、ローカル変数 | X (UPROPERTYを付けないと追跡されない) |
| `TObjectPtr<T>` | UPROPERTYメンバー変数 (UE5) | O |
| `TSharedPtr<T>` | 非UObjectの共有所有権 | X (自己参照カウント) |
| `TUniquePtr<T>` | 非UObjectの単独所有権 | X |

```cpp
// TSharedPtr — UObjectではない一般C++クラスに使用
TSharedPtr<FMyData> SharedData = MakeShared<FMyData>();
TWeakPtr<FMyData> WeakData = SharedData; // 弱い参照

// TUniquePtr — 所有権移転のみ可能、コピー不可
TUniquePtr<FMyData> UniqueData = MakeUnique<FMyData>();
TUniquePtr<FMyData> Moved = MoveTemp(UniqueData); // 所有権移転
```

> `TSharedPtr`/`TUniquePtr` は **UObjectではない** 一般C++クラスにのみ使用します。
> UObjectはGCが寿命を管理するため、TSharedPtrで包むと二重解放の危険があります。
{: .prompt-warning }

<br>

### 参照 (Reference)

- Unrealでconst参照は大型構造体（FVector, FTransform, FStringなど）をコピーなしで渡す時に必須です。

```cpp
// 値コピー — FStringコピーコスト発生
void PrintName(FString Name);

// const参照 — コピーなし、読み取りのみ可能
void PrintName(const FString& Name);

// 非const参照 — 呼び出し元の値を修正
void GetName(FString& OutName);

// 出力パラメータ慣例：Out接頭辞を付ける
void CalculateDamage(float InBaseDamage, float& OutFinalDamage);
```

> Unrealコーディングスタンダードで出力パラメータには `Out` 接頭辞を付けるのが慣例です。
> `const&` は関数パラメータの基本選択肢。基本タイプ（int32, float, boolなど）のみ値で渡します。
{: .prompt-tip }

<br>

### インライン (FORCEINLINE)

- 標準C++の `inline` はコンパイラへのヒントに過ぎませんが、Unrealの `FORCEINLINE` はプラットフォーム別に `__forceinline`(MSVC) や `__attribute__((always_inline))`(GCC/Clang) に拡張され、 **強制インライン** を試みます。

```cpp
FORCEINLINE float GetHealthPercent() const
{
    return MaxHealth > 0.f ? CurrentHealth / MaxHealth : 0.f;
}
```

- 呼び出し頻度が極めて高く関数本体が小さい場合（Getter、ユーティリティ計算など）に使用します。
- 乱用するとコードサイズが大きくなりI-cacheミスが増加するため、プロファイリング結果を基に適用するのが望ましいです。

<br>

### ビルドマクロ

- ビルド設定に応じて条件付きでコードを含める/除外するマクロがあります。

```cpp
#if WITH_EDITOR
    // エディタビルドでのみコンパイル（パッケージビルドでは除外）
    void EditorOnlyFunction();
#endif

#if UE_BUILD_SHIPPING
    // シッピングビルドでのみコンパイル
#endif

#if !UE_BUILD_SHIPPING
    // シッピング以外のすべてのビルド（開発用デバッグコード）
    UE_LOG(LogTemp, Verbose, TEXT("デバッグ情報: %d"), DebugValue);
#endif

#if UE_BUILD_DEBUG
    // デバッグビルドでのみコンパイル
#endif
```

| マクロ | 真の場合 |
|--------|----------|
| `WITH_EDITOR` | エディタビルド (PIE含む) |
| `UE_BUILD_DEBUG` | Debug設定 |
| `UE_BUILD_DEVELOPMENT` | Development設定 |
| `UE_BUILD_TEST` | Test設定 |
| `UE_BUILD_SHIPPING` | Shipping設定 |
| `UE_SERVER` | デディケイテッドサーバービルド |

<br>

### アサーション (Assertion)

- Unrealは標準 `assert()` の代わりに独自のマクロを提供します。状況別に適切なものを選んで使用する必要があります。

```cpp
// check — 条件失敗時にクラッシュ（デバッグ/開発ビルドで）
check(Ptr != nullptr);
checkf(Health >= 0.f, TEXT("Healthが負数: %f"), Health);

// verify — checkと同じだが、シッピングビルドでも式自体は実行される
verify(ImportantFunction()); // シッピングでも関数は呼び出される、失敗時は無視

// ensure — 条件失敗時にクラッシュの代わりに警告ログ + コールスタック出力（一度だけ）
if (ensure(Ptr != nullptr))
{
    Ptr->DoSomething();
}
ensureMsgf(Value > 0, TEXT("Valueが0以下: %d"), Value);

// unimplemented — まだ実装していない関数に入れておくマクロ（呼び出し時にクラッシュ）
void AMyActor::NotYetDone()
{
    unimplemented();
}
```

> **check vs ensure 選択基準**
>
> `check` — "この条件が偽ならプログラムの状態が完全に壊れたものなので即時中断すべきだ"
> `ensure` — "この条件が偽ならバグだが、クラッシュなしでログを残して復旧を試みることができる"
>
> `check` はシッピングビルドで **式自体がコンパイルから除去** されるため、サイドエフェクトがある式をcheckに入れてはいけません。
> `verify` はシッピングでも式は実行されるため、サイドエフェクトがある場合に使用します。
{: .prompt-warning }

<br>

### MoveTemp — Unrealの std::move

- 標準C++の `std::move` の代わりにUnrealでは `MoveTemp()` を使用します。動作は同様にlvalueをrvalue参照にキャストして移動セマンティクスを有効にします。

```cpp
TArray<FString> Source = { TEXT("A"), TEXT("B"), TEXT("C") };
TArray<FString> Dest = MoveTemp(Source); // Sourceは以後空の状態
```

- Unrealコーディングスタンダードで `std::move` の代わりに `MoveTemp` を推奨します。理由はデバッグビルドで追加の検証（constオブジェクト移動防止など）を実行するためです。
