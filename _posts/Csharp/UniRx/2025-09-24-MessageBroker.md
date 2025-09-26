---
title: UniRx - MessageBroker 활용 가이드
date: 2025-09-24 12:21:00 +/-TTTT
categories: [Csharp, UniRx]
tags: [Unity, Csharp, UniRx, MessageBroker]     # TAG names should always be lowercase

toc: true
toc_sticky: true
math: true  
use_math: true
mermaid: true
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

---

<br>

---

> **주의** : UniRx가 R3로 업데이트 되면서 [R3](https://github.com/Cysharp/R3?tab=readme-ov-file)에서 MessageBroker는 [MessagePipe](https://github.com/Cysharp/MessagePipe)로 변경되었음.
{: .prompt-warning }

---

## UniRx의 MessageBroker란?

- **MessageBroker** 는 UniRx 에서 제공하는 중앙 집중형 Pub/Sub (발행/구독) 패턴 구현체이다. 쉽게 비유하자면 라디오 방송국과 같다.
- 말은 거창하지만 실제로 디버깅 테스트용으로 사용하면 아주 좋다고 생각한다. 느슨한 결합이 포인트이고 의존성을 제거한다. SRDebugger 와 잘 조합해서 사용하면 디버깅용으료 엄청난 퍼포먼스를 발휘한다.
- Unity 프로젝트에서 확장 가능하고 테스트가 용이한 아키텍쳐를 구축하는 핵심패턴이라고 생각한다. (실제로는 서버 통신에서 많이 쓰인다고 한다)

<br>

### MessageBroker 의 장점들

> **느슨한 결합** : 모듈간의 직접 참조가 원천적으로 차단된다. 유지보수와 테스트 비용을 극적으로 낮춘다.
> **타입 기반의 명확한 계약** : ```Receive<T>()``` 와 ```Publish(T)``` 는 메시지 타입을 통해 명시적인 계약을 형성한다. 컴파일 타임에 통신 규격이 보장되는 것.
> **중앙 집중화된 통신 흐름** : 메시지 라우팅이 ```MessageBroker.Default``` 를 통해 일어나므로, 시스템의 이벤트 흐름을 추적하고 디버깅하기 용이.
> **예측 가능한 동기 실행** : 기본적으로 발행과 즉시 구독자 콜백이 동기적으로 실행된다.
{: .prompt-info }

<br>
    
---

<br>

> UniRx 는 Unity 이벤트와 비동기를 Reactive Extensions 방식으로 다루는 라이브러리이다.
> CyberAgent사 소속의 Cysharp 이라는 깃허브 조직에서 만든 것으로 오픈소스로 공개하여 많은 개발자들에게 도움을 주고있다.
{: .prompt-tip }

<br>

---

## MessageBroker 예시 코드

<br>

### 1. 메시지 타입의 정의 : 명확한 계약서 작성

- 모든 메시지는 그 자체로 명확한 의도를 가진 DTO(Data Transfer Object)여야 한다.

```csharp

public enum DebugCommandType
{
    KillPlayer,
    KillMob,
    KillBoss,
    InfiniteUlt,
    ApplySkill
}

// sealed: 상속을 금지하여 메시지 타입의 불변성을 보장
// readonly struct도 좋은 선택지
public sealed class DebugCommandMessage
{
    public DebugCommandType CommandType { get; }
    public IReadOnlyDictionary<string, object> Parameters { get; }

    public DebugCommandMessage(DebugCommandType commandType, Dictionary<string, object> parameters = null)
    {
        CommandType = commandType;
        // 방어적 복사: 외부에서 Dictionary가 수정되어도 메시지 내부에는 영향이 없도록 보장
        Parameters = parameters ?? new Dictionary<string, object>();
    }
}
```

<br>

### 2. 발행(Publish)

- Publisher 는 누가 듣고 있는지 신경 쓸 필요가 전혀 없다. 오직 어떤 일이 일어났는지에만 집중하여 메시지를 발행해야한다.

```csharp
// 다음 두 가지로 메시지 발행이 가능하다.
// SRDebugger SROptions 일수도 DebugPanel 같은 개인 클래스 내부일 수도 있음.

// 단순 메시지 발행
public void KillPlayer()
{
    MessageBroker.Default.Publish(new DebugCommand(DebugCommandType.KillPlayer));
}

// 파라미터가 포함된 메시지 발행
public bool InfiniteUlt
{
    get => isUltInfiniteActive;
    set
    {
        if (isUltInfiniteActive != value)
        {
            isUltInfiniteActive = value;
            MessageBroker.Default.Publish(new DebugCommandMessage(
                DebugCommandType.InfiniteUlt,
                new Dictionary<string, object> { { "trigger", isUltInfiniteActive } }
            ));
        }
    }
}
```

<br>

### 3. 구독(Subscribe)

- 구독자는 특정 타입의 메시지에만 반응하며, 구독의 생명주기를 반드시 관리해야한다.

```csharp
// 예시 코드 : 하나의 게임 씬을 관리하는 매니저 클래스
public partial class StageManager
{
    private Dictionary<DebugCommandType, Action<DebugCommandMessage>> debugActions;
    
    private void Awake()
    {
        // 메시지별 액션 매핑
        debugActions = new Dictionary<DebugCommandType, Action<DebugCommandMessage>>()
        {
            {DebugCommandType.KillPlayer, msg => CurrentPlayer.KillPlayer()},
            {DebugCommandType.KillMob, msg => monsterSpawner.KillMonsters()},
            {DebugCommandType.KillBoss, msg => monsterSpawner.KillBoss()},
            {DebugCommandType.InfiniteUlt, msg => InfiniteUlt(msg.Parameters)}
        };
        
        // 메시지 구독
        MessageBroker.Default.Receive<DebugCommandMessage>()
            .Subscribe(msg =>
            {
                if (debugActions.TryGetValue(msg.CommandType, out var action))
                {
                    action(msg);
                }
                else
                { 
                    UnityEngine.Debug.LogWarning($"Unknown DebugCommandType: {msg.CommandType}");
                }
            }).AddTo(this);
    }
    
    private void InfiniteUlt(Dictionary<string, object> parameters)
    {
        if (parameters.TryGetValue("trigger", out var trigger))
        {
            var isUltInfiniteActive = (bool) trigger;
            
            if (isUltInfiniteActive)
            {
                gameModel.UltDelayProperty.Value = 0.1f;
                OnTriggerUltActivate.Invoke();
            }
            else
            {
                gameModel.UltDelayProperty.Value = 10f;
            }
        }
        else
        {
            UnityEngine.Debug.LogWarning("InfiniteUlt command requires 'trigger' parameter");
        }
    }
}
```
<br>
<br>

---

## 파라미터 전달 전략 

<br>

### Dictonary 방식

- MessageBroker는 ```Dictionary<string, object>```를 통해 다양한 타입의 파라미터를 유연하게 전달할 수 있다.
- 프로덕션 환경에서 치명적인 단점이 존재하긴 하지만 개인적으로는 디버깅 용도로 사용할 경우 충분하다고 생각한다.

```csharp
var parameters = new Dictionary<string, object>
{
    { "trigger", true },                              // bool 값
    { "skillName", "Fireball" },                     // string 값
    { "damageMultiplier", 1.5f },                    // float 값
    { "retryCount", 3 },                            // int 값
    { "affectedTargets", new List<int> { 101, 102, 103 } } // List<int> 값
};

MessageBroker.Default.Publish(new DebugCommandMessage(
    DebugCommandType.ApplySkill, parameters
));
```

<br>

### DTO

- 이벤트마다 전용 DTO를 정의하면 컴파일 타임에 모든 것이 검증되며, 매직 스트링과 런타임 캐스팅이 사라진다. 
- 좀 더 명확하고 실수없이 프로덕션 환경에 적합하다.

```csharp
// 발행: 명확하고 실수가 없다
MessageBroker.Default.Publish(new SkillAppliedEvent("Fireball_Lv3", 1.5f, new[] {101, 102}));

// 구독: 타입 캐스팅 없이 안전하게 파라미터 사용
MessageBroker.Default.Receive<SkillAppliedEvent>()
    .Subscribe(evt => CombatSystem.ApplyDamage(evt.SkillId, evt.DamageMultiplier, evt.TargetIds));
```

<br>
<br>

---

## 동작 원리, 성능, 그리고 스레드 모델

<br>

### 반드시 확인해야할 내용 3가지

1. **시간 복잡도** : ```O(n)``` 이다. 한 번의 발행은 모든 구독자(n) 에게 순차적으로 전달된다. 구독자가 수백 개 이상인 고빈도 이벤트는 성능 문제를 일으킬 수 있다.
2. **동기 실행** : 발행 스레드에서 구독자 콜백이 즉시, 순차적으로 호출된다. 이는 예측 가능성을 높이지만, 하나의 콜백이 지연되면 전체 시스템이 멈출 수 있음을 의미한다.
3. **메모리 관리**  : 구독을 해제(Dispose)하지 않으면 100% 메모리 누수가 발생한다. ```AddTo(this)``` 는 ```Monobehaviour``` 생명주기에 의존하는 가장 기본적인 방어선이며, ```CompositeDisposable``` 은 더 정밀한 제어를 위해 필수적이다.

<br>

### 메인 스레드 전환

- Unity의 API(UI, GameObject 등)는 메인 스레드에서만 안전하게 호출할 수 있다. 백그라운드 스레드에서 발행된 메시지를 받아 Unity API를 조작하려면, ```ObservableOnMainThread()``` 를 만드시 사용해야 한다.

```csharp
// 네트워크 수신(백그라운드 스레드) -> 결과 처리(메인 스레드)
MessageBroker.Default.Receive<NetworkResponse>()
    .ObserveOnMainThread() // 이 시점 이후의 모든 콜백은 메인 스레드에서 실행됨을 보장
    .Subscribe(response => UpdateUI(response.Data))
    .AddTo(this);
```

<br>

### 고빈도 이벤트 최적화 : 시스템 과부하 방지

- 프레임당 수십 번 호출되는 이벤트는 그대로 브로드캐스트하면 안된다. Rx의 강력한 연산자들로 호출량을 제어해야한다.

```csharp
MessageBroker.Default.Receive<PlayerHitEvent>()
    .Buffer(TimeSpan.FromMilliseconds(100)) // 100ms 동안 발생한 이벤트를 리스트로 묶음
    .Where(hits => hits.Count > 0)          // 빈 배치는 무시
    .Subscribe(hits =>
    {
        // 여러 번의 피격 대미지를 한 번에 계산하여 UI 갱신, 네트워크 전송 등을 처리
        var totalDamage = hits.Sum(h => h.Damage);
        DamageUIManager.ShowAggregatedDamage(totalDamage);
    })
    .AddTo(this);
```

<br>
<br>

---

## 생명주기 관리(Dispose)와 누수 방지

<br>

### ``AddTo(this)`` 를 넘어 ``CompositeDisposable`` 으로

- ``AddTo(this)``는 ``MonoBehaviour``에 종속된 구독에 대한 훌륭한 기본값이다. 하지만 객체의 생명주기가 ``GameObject``와 무관하다면, ``CompositeDisposable``을 사용한 명시적 관리가 필수이다.

```csharp
public class PlayerService
{
    // 이 서비스 인스턴스가 살아있는 동안의 모든 구독을 담는 컨테이너
    private readonly CompositeDisposable _subscriptions = new CompositeDisposable();

    public void Activate()
    {
        MessageBroker.Default.Receive<GameStateChangedEvent>()
            .Where(evt => evt.NewState == GameState.InGame)
            .Subscribe(_ => OnGameStarted())
            .AddTo(_subscriptions); // 컨테이너에 추가
    }

    public void Deactivate()
    {
        _subscriptions.Clear(); // 모든 구독을 한 번에 해제. Dispose()는 재사용 불가.
    }
}
```

<br>

### 메모리 누수를 유발하는 흔한 실수

- **정적(static) 이벤트 구독** : 전역 ``MessageBroker``를 정적 클래스나 오래 살아남는 싱글턴에서 구독하고 해제하지 않는 경우, 씬이 바뀌어도 구독이 계속 살아남아 메모리 누수를 유발한다.

- **``OnCompleted`` 만 기다리기** : ``MessageBroker``는 ``OnCompleted`` 신호를 보내지 않는다. 구독의 끝은 반드시 ``Dispose`` 로 명시해야한다.

<br>
<br>

---

## 스코프 분리 권장

- 전역 브로커 ``MessageBroker.Default`` 만 썼을 때의 문제점은 모든 이벤트가 뒤섞이는 스파게티가 되어버릴 가능성이 있다. 메시지 도메인의 경계가 무너지고, 의도치 않은 교차 구독이 발생하거나 코드의 추론이 불가능해진다.

### 해결책 : 기능별 브로커 스코프 설정

- UI 관련 이벤트는 ``UIMessageBus`` 에서만, 전투 관련 이벤트는 ``CombatMessageBus`` 에서만 흐르도록 스코프를 분리하자.

```csharp
// 의존성 주입(DI) 컨테이너 등을 통해 주입되는 모듈 전용 버스
public sealed class UIMessageBus
{
    public IMessageBroker Broker { get; } = new MessageBroker();
}

// 사용처 (UI 컴포넌트)
public class HUDController : MonoBehaviour
{
    [Inject] private UIMessageBus _uiBus; // DI 컨테이너로부터 주입

    void Start()
    {
        _uiBus.Broker.Receive<PlayerHealthChanged>()
            .Subscribe(evt => UpdateHealthBar(evt.CurrentHealth))
            .AddTo(this);
    }
}
```

<br>
<br>

---

## 체크리스트

이 체크리스트를 코드 리뷰의 기준으로 삼아보자.

<br>

[✅] 메시지는 강타입 DTO인가? (Dictionary는 디버그 툴에만 허용)

[✅] 모든 Subscribe 호출은 AddTo 또는 CompositeDisposable로 끝나고 있는가? (예외 없음)

[✅] Unity API를 다루는 콜백은 ObserveOnMainThread()로 보호되고 있는가?

[✅] 전역 브로커를 남용하지 않고, 기능별 브로커로 스코프를 분리했는가? (대규모 프로젝트 필수)

[✅] 고빈도 이벤트는 Buffer, Throttle, Sample 등으로 제어되고 있는가?

<br>
<br>

---

## 결론

- MessageBroker는 강력한 도구이지만, 보다 신중한 결정과 책임이 요구된다. 이 패턴은 단순히 코드를 분리하는 것을 넘어, 시스템의 각 부분이 어떤 '계약'을 통해 소통하는지를 설계하는 아키텍처적 행위이다.
- DTO, 엄격한 생명주기 관리, 명확한 스레드 모델, 그리고 적절한 스코프 분리. 이 원칙들을 지킬 때, MessageBroker는 비로소 복잡한 Unity 프로젝트를 지탱하는 견고하고 유연한 아키텍쳐가 되리라 생각한다.