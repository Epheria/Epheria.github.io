---
title: 언리얼 C++ 첫걸음 - UHT, UObject, 문자열/로깅, GameInstance, 포인터·레퍼런스·매크로까지 한 번에
date: 2025-09-03 23:12:00 +/-TTTT
categories: [Unreal, Study]
tags: [Unreal, Study, UHT, UObject, FString, GameInstance, C++]     # TAG names should always be lowercase

toc: true
toc_sticky: true
math: true  
use_math: true
mermaid: true
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

---

<br>

## 목차

> [빌드 파이프라인 & UHT(Unreal Header Tool)](#1-빌드-파이프라인--uht)      
> [헤더/CPP 파일 분리 원칙(IWYU), 전방 선언, include 순서, 모듈 매크로](#2-헤더cpp-분리-원칙iwyu-전방-선언-include-순서-모듈-매크로)     
> [리플렉션 기초 : UCLASS/UPROPERTY/UFUNCTION/generated.h 규칙](#3-리플렉션-기초--uclassupropertyufunction--generatedh-규칙)     
> [UObject생성,수명,GC - UPROPERTY/TObjectPtr/TweakObjectPtr](#4-uobject-생성-수명-gc---uporpertytobjectptrtweakobjectptr)  
> [문자열 로깅 - FString, FName, FText, TEXT/TCHAR](#문자열로깅-fstringfnameftext-texttchar-s와-fstring)  
> [GameInstance와 Subsystem 초기화 흐름과 Super::Init()에 대해](#gameinstance와-subsystem-초기화-흐름과)  
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
    GENREATED_BODY()
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
    Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh));
    SetRootComponent(Mesh);
}

```
- 값 멤버(예: `UStaticMeshComponent Mesh;`)처럼 완전한 정의가 필요한 경우엔 전방 선언만으로는 부족하므로 헤더에 실제 include가 필요하다.

<br>

---

<br>

## 3. 리플렉션 기초 : UCLASS/UPROPERTY/UFUNCTION & generated.h 규칙



<br>

---

<br>

## 4. UObject 생성, 수명, GC - UPORPERTY/TObjectPtr/TWeakObjectPtr





<br>

---

<br>

## 문자열·로깅: FString/FName/FText, TEXT/TCHAR, `%s`와 `*FString`






<br>

---

<br>

## GameInstance와 Subsystem: 초기화 흐름과







<br>

---

<br>

## CPP 기초(언리얼 관점): 포인터·레퍼런스·인라인·빌드 매크로·어설션





- 목표 지향 행동 계획 (Goal Oriented Action Planning)는 게임 인공지능(AI)에서 에이전트가 자율적으로 행동을 결정하고 게임 환경 내에서 특정 목표를 달성할 수 있도록 하는 기술이다.

- GOAP는 게임의 비플레이어 캐릭터(NPC)에 복잡하고 적응적인 행동을 부여하는 데 사용되며 NPC가 자율적으로 행동을 결정하고 목표를 달성할 수 있도록 하는 기술이다.

- 복잡한 목표를 더 작은 행동으로 나누고, 이를 조합하여 목표에 도달하는 계획을 세우고 에이전트는 현재 상태와 목표 상태를 평가하고, 필요 시 계획을 동적으로 조정하여 목표를 달성한다.


<br>
<br>

## GOAP Plugin 설명

**[GOAP for Unity](https://github.com/crashkonijn/GOAP/tree/master)**

- 해당 플러그인은 crashkonijn 이라는 사람이 만든 멀티스레드 기반의 유니티 잡 시스템을 사용하여 개발한 GOAP 플러그인이다.

> **주요 특징은 다음과 같다.**     
>      
> 높은 퍼포먼스 - 유니티 잡 시스템을 활용한 멀티 스레드 작업으로 속도 최적화     
> 스크립터블 오브젝트로 인젝트 가능     
> GOAP 를 편하게 디버깅 가능한 전용 노드 뷰어 제공     
{: .prompt-info }

<br>

![Desktop View](/assets/img/post/unity/unitygoap01.gif){: : width="500" .normal }    


- 사진에 나와있는 2D 기반의 간단한 GOAP AI 를 구성한 샘플 프로젝트에 대해 PC, 모바일 기기 Android 부하 테스트를 진행했다.

- 플랫폼 별로 최대 2K 의 오브젝트를 움직이고, GOAP 의사결정을 진행하고 수행하는 것을 확인했다.

<br>

{% include embed/youtube.html id='N34bPqlzii4' %}

- 3D 오브젝트에 대해서도 모바일(LG V5)에서 부하 테스트를 진행하였고, 대략 500-최대 1K의 오브젝트까지 컨트롤이 가능했다.

- 예전에 개인적으로 유니티에 FlowFIeld(다익스트라) 알고리즘을 적용하여 메인 스레드 기반으로 1200 까지 늘려본적이 있는데

- 확실히 멀티스레드 기반의 계산이 들어가서 퍼포먼스적으로 매우 우월하다고 생각한다.

<br>
<br>

![Desktop View](/assets/img/post/unity/unitygoap02.png){: : width="1000" .normal }    

- 위 영상에서 구현한 NPC 의 GOAP 노드 뷰어이다.

- 이처럼 편하게 시각적으로 편하게 디버깅이 가능하다는 장점도 존재한다. (번거롭게 로그나 인스펙터로 수치를 확인하지 않아도 됨)


<br>

## GOAP 클래스 구조

#### Goals

- GOAP 시스템에서는 에이전트가 달성하고자 하는 원하는 결과 또는 목표(Goals)를 설정할 수 있다.

```csharp
using CrashKonijn.Goap.Behaviours;
 
namespace GOAP.Goals
{
    public class WanderGoal : GoalBase
    {
         
    }
}
```

<br>

- GoalBase 클래스를 상속하여 사용한다.

- 클래스 내부의 코드는 일절 필요없다. 왜냐하면 Planner 가 Goal 을 빌드할 때 필요한 Condition 들을 헤더함수를 통해 추가가 가능하기 때문이다.

<br>

```csharp
builder.AddGoal<WanderGoal>()
    .AddCondition<IsWandering>(Comparison.GreaterThanOrEqual, 1);
 
builder.AddGoal<KillEnemy>()
    .AddCondition<EnemyHealth>(Comparison.SmallerThanOrEqual, 0);
 
builder.AddGoal<EatGoal>()
    .AddCondition<Hunger>(Comparison.SmallerThanOrEqual, 0)
    .AddCondition<Fatigue>(Comparison.SmallerThanOrEqual, 0);
```

<br>

- 여기서 IsWandering, EnemyHealth, Hunger, Fatigue 등은 WorldKey 로 에이전트가 다음에 수행해야할 작업을 결정하는 지표역할을 맡는다.

- 예를 들어, Hunger와 Fatigue 가 둘 다 0이하 여야만 다음 Goal 을 설정할 수 있다.

- 특히 현재 목표를 완료한 뒤에는 다음 의사결정을  내리기 위한 지표들(WorldKey) 혹은 Sensor 에서 검출한 Target들을 선별하여 목표를 설정한다.

<br>
<br>

#### Actions

- 에이전트가 특정 목표를 달성하기 위해 수행할 수 있는 단계들이라고 보면 된다. 
- Planner 에 Action 을 추가할 수 있다.
- SetTarget 을 통해 목표의 위치값을 설정한다. 즉, SetTarget 으로 TargetKeyBase 클래스를 상속받는 Target을 매핑한다. 이 Target 은 Sensor 에서 검출해낸 오브젝트의 Vector3 를 뜻한다.
- Condition 과 Effect 를 추가할 수 있다.
- Condition 을 통해 전제 조건을 설정할 수 있다. 예시에서는 거리가 10 이하인지 판단한다.
- Effect 는 액션이 실행될 때 WorldKey 값을 증가, 감소 하는 역할을 한다.

<br>

```csharp
builder.AddAction<WanderAction>().SetTarget<WanderTarget>()
      .AddCondition<InRange>(Comparison.SmallerThanOrEqual, 10)
      .AddEffect<IsWandering>(EffectType.Increase)
      .SetBaseCost(5)
      .SetInRange(10);
```

<br>

- 여기서 SetBaseCost, SetInRange(휴리스틱) 를 주목해야한다.

- 코드를 보면, WanderAction 을 수행하기 위해서는 BaseCost 값과 에이전트와 WanderTarget의 Distance 를 의미하는 InRange 값의 합을 판단하여 나온 낮은 값을 기반으로 의사결정을 내린다.

<br>

- 즉, 거리가 똑같더라도 BaseCost 가 낮으면 그 Action 을 우선적으로 수행한다는 것이다.

<br>

```csharp

builder.AddAction<EatAction>()
         .SetTarget<FoodTarget>()
         .AddCondition<Hunger>(Comparison.GreaterThan, 0)
         .AddEffect<Hunger>(EffectType.Decrease)
         .SetBaseCost(8)
         .SetInRange(1);
 
     builder.AddAction<RestAction>()
         .SetTarget<HomeTarget>()
         .AddCondition<Fatigue>(Comparison.GreaterThan, 0)
         .AddEffect<Fatigue>(EffectType.Decrease)
         .SetBaseCost(10)
         .SetInRange(1);
```

<br>

- WorldSensor 가 Hunger, Fatigue 둘 다 Action 수행 여부를 결정하는 값인 20(임의)을 동시에 넘겼을 경우 EatAction 을 먼저 수행하게 된다.


<br>


- 특히 SetInRange 는 내부적으로 잡 시스템을 활용하여 A* 알고리즘의 휴리스틱과 유사하게 만들어 놓았는데

- GraphResolverJob(Planner) 이라는 패키지 내부적으로 캐시된 클래스를 뜯어본 결과 내부적으로 다음 휴리스틱 메소드가 존재했다.

- 단순한 직선 거리를 계산하는 코드지만, 이런 Distance 휴리스틱과 BaseCost 기반으로 어떤 Action 을 취할지에 대한 의사결정을 내릴지 계산한다.

<br>

```csharp
private float Heuristic(int currentIndex, int previousIndex)
{
    var previousPosition = this.RunData.Positions[previousIndex];
    var currentPosition = this.RunData.Positions[currentIndex];
 
    if (previousPosition.Equals(InvalidPosition) || currentPosition.Equals(InvalidPosition))
    {
        return 0f;
    }
 
    return math.distance(previousPosition, currentPosition) * this.RunData.DistanceMultiplier;
}
```

<br>

#### 실제 사용 방법

`RestAction.cs`

- 기본적으로 Created, Start, Perform, End 메소드를 오버라이드하여 커스텀이 가능하다.

- Perform 에서는 FSM 과 비슷하게, 전체 Goal-Actions 간의 트리 구조에서 현재 Action 을 매 프레임 업데이트한다.

<br>

```csharp
public class RestAction : ActionBase<RestAction.Data>, Iinjectable
{
 
        public override void Start(IMonoAgent agent, Data data)
        {
            data.Fatigue.enabled = false;
            data.Timer = 1f;
        }
 
        public override ActionRunState Perform(IMonoAgent agent, Data data, ActionContext context)
        {
            data.Timer -= context.DeltaTime;
            data.Fatigue.Fatigue -= context.DeltaTime * BioSigns.FatigueRestorationRate;
            data.Animator.SetBool(IS_SLEEPING, true);
 
            if (data.Target == null || data.Fatigue.Fatigue <= 0)
            {
                return ActionRunState.Stop;
            }
 
            return ActionRunState.Continue;
        }
 
        public override void End(IMonoAgent agent, Data data)
        {
            data.Animator.SetBool(IS_SLEEPING, false);
            data.Fatigue.enabled = true;
        }
}
```

<br>

- 여기서 Data data 의 구조는 다음과 같다.

```csharp
public class CommonData : IActionData
{
    public ITarget Target { get; set; }
    public float Timer { get; set; }
}
 
public class Data : CommonData
{
    [GetComponent] public Animator Animator { get; set; }
 
    [GetComponent] public FatigueBehavior Fatigue { get; set; }
}
```

<br>

```csharp
public class WanderAction : ActionBase<CommonData>
{
     public override void Start(IMonoAgent agent, CommonData data)
     {

     }
}
```

- 제네릭 타입에 따라 파라미터 타입이 달라진다.

<br>
<br>

`FatigueBehavior.cs`

- Behaviors 는 Monobehaviour 를 상속받는 클래스를 의미하며 실제로 각종 파라미터의 수치들, 유니티의 게임 오브젝트, 리스트 등 각종 모노와 관련된 작업을 수행한다.

<br>

```csharp
[RequireComponent(typeof(Animator), typeof(AgentBehaviour))]
    public class FatigueBehavior : MonoBehaviour
    {
        [field: SerializeField] public float Fatigue { get; set; }
        [field: SerializeField] public Transform HomeTransform { get; set; }
        [FormerlySerializedAs("BioSings")] [SerializeField] private BioSignSO BioSigns;
 
        private void Awake()
        {
            Fatigue = Random.Range(0, BioSigns.MaxFatigue);
        }
 
        private void Start()
        {
            HomeTransform = Managers.BuildingManager.buildingList[0].transform;
        }
 
        private void Update()
        {
            Fatigue += Time.deltaTime * BioSigns.FatigueDepletionRate;
        }
    }
```

<br>
<br>

---

<br>

## GOAP 시스템의 핵심에 대해

- GOAP 시스템과 인게임 상황을 분리해서 생각을 해야한다.
- GOAP 시스템의 단일 목적은 사실상 특정 Goal 에 대한 최적의 Action 을 찾는 것이다. 주의할 점은 최적의 Goal 을 찾는 행위는 인게임에 의존적이며 이는 GOAP 시스템에 포함되어 있지 않다.
- 최적의 Goal 을 찾는 방법은 FSM 일 수도 있으며 BT 일 수도 있고, 상위에 또 다른 GOAP (Action 만을 수행하는)를 만들어 관리할 수도 있다.

<br>

**GOAP 시스템은 본질적으로 다음 두 가지 일을 수행한다.**

- Goal 과 그에 연결되는 Action 의 그래프를 생성한다.
- 해당 그래프를 기반으로 현재 설정된 Goal 을 이루기 위한 최적의 Action 을 찾는다.

<br>

여기서 그래프를 작성하기 위해 GOAP 시스템은 Action 이 어떤 종류의 Effect 를 가지고 있는지 알아야하며, 이는 실제로 인게임 데이터를 매핑(포인터)하여 시스템에서 인식하게 된다.

<br>

예를 들어, FixHungerGoal 이 있다고 가정해보면, 이 Goal 은 IsHungry <= 50 이라는 Condition 을 지니고 있다.

<br>

여기서 EatAppleAction 은 IsHungry-- 감소시키는 Effect를 지니고 있다. 이렇게 EatAppleAction 을 수행하면 Goal 을 향해 게임이 어떻게 변하고 있는지 알 수 있게 되고, 그 Action 과 Goal 간의 연결이 만들어진다.

<br>

다음 그림을 살펴보면

<br>

![Desktop View](/assets/img/post/unity/unitygoap03.png){: : width="1200" .normal }    

<br>


1. FixHungerGoal 이 활성화되기 위해 에이전트의 배고픔 상태(IsHungry)가 50 이하이어야 한다.
2. IsHungrySensor는 에이전트의 현재 배고픔 상태를 평가하여, 이를 IsHungry 월드 키에 매핑한다.
3. TransformTargetSensor는 에이전트의 목표 위치(TransformTarget)를 평가하여, 이를 TransformTarget 타겟 키에 설정한다.
4. EatAppleAction은 에이전트가 사과를 가지고 있고(HasApple >= 1), 목표 위치에서 수행된다. 이 행동은 배고픔 상태(IsHungry)를 감소시킨다.
5. HasAppleSensor는 에이전트가 사과를 가지고 있는지를 평가하여, 이를 HasApple 월드 키에 설정한다.
6. ClosestAppleSensor는 가장 가까운 사과의 위치를 평가하여, 이를 ClosestApple 타겟 키에 설정한다.
7. PickupAppleAction은 에이전트가 가장 가까운 사과 위치에서 사과를 획득하는 행동이다. 이 행동은 에이전트의 사과 상태(HasApple)를 증가시킨다.

<br>
<br>

#### Sensor

- 센서는 GOAP 가 현재 게임의 상황을 이해할 수 있도록 도와주는 기능이다.

- 크게 WorldSensor(Gloabal), TargetSensor(Local) 로 나뉜다.

<br>

**Global Sensor**

- Global 센서는 모든 에이전트에 대한 정보를 제공한다. 예를 들어 IsDaytimeSensor는 모든 사람이 낮인지 밤인지 확인한다.

- 실제로 헷갈렸던 부분인데, Sensor 가 어떻게 WorldKey 를 인식하는것인지? 였다.

<br>

```csharp
builder.AddWorldSensor<HungerSensor>()
    .SetKey<Hunger>();
```

<br>

- WorldKey 로 설정한 Hunger를 Planner 를 통해 WorldSensor 에 매핑하기 때문에 인식이 가능했었다. 따라서 Behavior나 Action 에서 증가, 감소를 실행하면 WorldSensor 에서 상태를 파악하고 GOAP 에 해당 정보를 전송해준다.

- 이후 GOAP 는 해당 정보를 기반으로 어떤 Action 을 취할지 결정한다.

<br>
<br>

**Local Sensor**

- Planner가 실행될 때 작동하며, 단 하나의 에이전트의 정보만 제공한다. 예를 들어 FoodTargetSensor 는 가장 가까운 음식을 찾는다.

<br>

```csharp
public class HungerSensor : LocalWorldSensorBase
{
    ...
 
    public override SenseValue Sense(IMonoAgent agent, IComponentReference references)
    {
        return new SenseValue(Mathf.CeilToInt(references.GetCachedComponent<HungerBehavior>().Hunger));
    }
 
    ...
 
}
 
public class FoodTargetSensor : LocalTargetSensorBase, Iinjectable
{
 
    ...
 
    public override ITarget Sense(IMonoAgent agent, IComponentReference references)
    {
        Vector3 agentPosition = agent.transform.position;
        int hits = Physics.OverlapSphereNonAlloc(agentPosition, BioSigns.FoodSearchRadius, Colliders,
            BioSigns.FoodLayer);
 
        if (hits == 0)
        {
            return null;
        }
 
        for (int i = Colliders.Length - 1; i > hits; i--)
        {
            Colliders[i] = null;
        }
 
        Colliders = Colliders.OrderBy(collider =>
            collider == null
                ? 999
                : (collider.transform.position - agent.transform.position).sqrMagnitude).ToArray();
 
        return new PositionTarget(Colliders[0].transform.position);
    }
 
 
    ...
 
}
```

<br>

#### Injector

- Data Injection 은 다른 객체나 모듈에 런타임 데이터를 제공하는 디자인 패턴이다.
- GOAP 시스템에서 관리하는 핵심 클래스(Goal, Action, Sensor)에 특정 데이터나 종속성을 제공하는 데 사용된다.
- 특히 디커플링을 위해 자주 사용하는데, 핵심 로직을 수정하지 않고 스크립터블 오브젝트로 Injectable 데이터를 주입해서 GOAP 클래스를 일반적이고 재사용 가능하게 활용할 수 있다.
- 예를 들어, 직업별로 이동속도와 같은 스탯이 다를 경우 직업별로 스크립터블 오브젝트를 생성하고 Injectable 인터페이스를 각 클래스에 상속시켜서 모듈식으로 활용이 가능하다.

<br>
<br>

## 연구 목표

- GOAP 를 제대로 활용하기 위해서는, 인게임 상태와 GOAP 시스템을 분리해서 생각해야한다는 점

<br>

- 이를 위해 FSM, BT, Layered GOAP 들 중 프로젝트에 알맞는 방법을 활용하여 복잡한 알고리즘 속에서 최적의 Goal 을 선택하는 로직을 잘 구현해야한다는 점

<br>

- 특정 Goal 을 달성하기 위한 최적의 Action 을 수행하기 위해 Condition 과 Effect 를 설정하여 알고리즘을 구현해야한다는 점

<br>

- 각 GOAP 들의 Goal, Action 들에 대한 데이터 관리 방법을 정해야 한다는 점 (세이브/로드도 고려해야함)
- 이 부분은 crashkonjin 이 새로이 출시한 [Blackboard 시스템](https://blackboard.crashkonijn.com/)을 사용하면 될 것 같다.