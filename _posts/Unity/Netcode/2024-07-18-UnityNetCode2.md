---
title: Unity Netcode - Network Synchronization (RPC, NetworkVariables)
date: 2024-07-18 10:00:00 +/-TTTT
categories: [Unity, Netcode]
tags: [Unity, Netcode, NetworkVariable, RPC, legacy, universial]     # TAG names should always be lowercase

toc: true
toc_sticky: true
math: true  
use_math: true
mermaid: true
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

---

<br>

## 네트워크 동기화

네트워크 동기화는 다음과 같이 크게 2가지 방법으로 나뉜다. RPC, NetworkVariables

- NetworkVariables 는 게임 실행 이후 늦게 진입하는(난입) 클라이언트 간의 동기화를 진행하는데 가장 일반적으로 사용된다.

- 반면, RPC 의 경우 게임 로직을 RPC 로 처리할 경우 데이터 소실로 인해 뒤늦게 진입한 클라이언트와의 동기화에 대한 신뢰성이 떨어질 가능성이 높다.

<br>
<br>

## RPC ([Remote procedure calls](https://docs-multiplayer.unity3d.com/netcode/current/advanced-topics/messaging-system/)) 호출

<br>

- RPC 는 Messaging, 이벤트 알림을 보내는 방법 뿐만 아니라 서버와 클라이언트 간 또는 클라이언트와 NetworkBehaviour 간의 직접 통신을 처리하는 방법이다.

- 클라이언트는 NetworkObject 에서 Server RPC 를 호출할 수 있다. RPC 는 로컬 큐에 배치된 후 서버로 전송되며, 서버 버전의 동일한 NetworkObject 에서 실행된다.

- 클라이언트에서 RPC 를 호출할 때 SDK 는 해당 RPC 의 객체, 컴포넌트, 메서드 및 매개변수를 기록하고 이 정보를 네트워크를 통해 전송한다.


<br>
<br>

- Server RPC 의 작동 원리

<br>

![Desktop View](/assets/img/post/unity/netcode013.png){: : width="2000" .normal }    

<br>
<br>

- Client RPC 의 작동원리

<br>

![Desktop View](/assets/img/post/unity/netcode014.png){: : width="2000" .normal }    

<br>
<br>

#### RPC 사용 방법

- RPC 는 기본적으로 RPC 호출을 하고자하는 메소드 상단에 어트리뷰트로 선언하면 된다.

- 주의 할 점은 메소드 이름 끝에 Rpc, ServerRpc, ClientRpc 등과 같은 이름을 붙여줘야만 한다.

<br>

```csharp
// universial RPC
[Rpc(SendTo.Server)] // Server
public void PingRpc(int pingCount) { }
 
[Rpc(SendTo.NotServer)] // Client
void PongRpc(int pingCount, string message) { }
 
 
// Legacy RPC
[ServerRpc]
public void PingServerRpc(int pingCount) { }
 
[ClientRpc]
public void PongClientRpc(int pingCount, string message) { }
```

<br>
<br>

#### RPC Attribute Target Table

- 뭔가 타겟들이 다양하게 많지만, 주로 사용하는 것은 Server, NotServer, Everyone 정도이다.

<br>

![Desktop View](/assets/img/post/unity/netcode015.png){: : width="1360" .normal }    
![Desktop View](/assets/img/post/unity/netcode016.png){: : width="1360" .normal }    

<br>

- 위 어트리뷰트와 함께 자주 사용하는 파라미터 또한 존재한다.

![Desktop View](/assets/img/post/unity/netcode017.png){: : width="1000" .normal }    

```csharp

[Rpc(SendTo.Everyone, RequireOwnership = false)]
 
[ServerRpc(RequireOwnership = false)]

```

<br>

- 사실상 Legacy RPC 를 사용하는게 가장 쉽고 직관적이라고 생각하지만..  universal RPC attribute 로 대체되었다고 하니 가능하면 universial RPC 형태로 사용하는게..?
- 근데 둘 다 사용이 가능한 것으로 보아 차이점에 대한 것은 추가적인 연구가 필요해보인다.

<br>

#### 실제 사용 예시 1

![Desktop View](/assets/img/post/unity/netcode018.png){: : width="1000" .normal }    

<br>
<br>

#### 실제 사용 예시 2

- 각 클라이언트에서 **TryAddIngredient** 클라이언트 전용 메소드를 실행한다.
- 이후 ServerRpc 인 **AddIngredientServerRpc** 를 호출한다.

- ServerRpc 는 서버에서만 실행되지만, 메소드 내부에 ClientRpc 인 **AddIngredientClientRpc** 메소드를 실행시켜 연결된 모든 클라이언트에 반영 해준다.

<br>

```csharp

public bool TryAddIngredient(KitchenObjectSO kitchenObjectSO)
{
    AddIngredientServerRpc(GetKitchenObjectSOIndex(kitchenObjectSO))
}
 
 
 
[ServerRpc(RequireOwnership = false)]
private void AddIngredientServerRpc(int kitchenObjectSOIndex)
{
    AddIngredientClientRpc(kitchenObjectSOIndex);
}
 
 
 
[ClientRpc]
private void AddIngredientClientRpc(int kitchenObjectSOIndex)
{
    KitchenObjectSO kitchenObjectSO =
        KitchenGameMultiplayer.Instance.GetKitchenObjectSOFromIndex(kitchenObjectSOIndex);
     
    kitchenObjectSOList.Add(kitchenObjectSO);
     
    OnIngredientAdded?.Invoke(this, new OnIngredientAddedEventArgs
    {
        kitchenObjectSO = kitchenObjectSO
    });
}
```

<br>
<br>
<br>

---

<br>

## [NetworkVariables](https://docs-multiplayer.unity3d.com/netcode/current/basics/networkvariable/) 동기화


- NetworkVariables 는 RPC 와 달리 서버와 클라이언트 간의 프로퍼티등을 지속적으로 동기화하는 방법이다. 

- RPC 및 메시지와 달리 특정 시점의 일회성 통신이 아니고, 연결되지 않은 클라이언트와는 공유되지 않음.

<br>

- NetworkVariable 은 지정된 값 타입 T 의 Wrapper 로, 실제로 동기화되는 값을 접근하려면 NetworkVariable.Value 속성을 사용해야한다.

- 여기서 주의할 점은 T 타입에는 Value 타입(int, bool, float, string 도 FixedString) 만 지정할 수 있다는 것 (Reference 타입은 안됨.)

<br>

```csharp
private NetworkVariable<int> testValue = new NetworkVariable<int>();
 private const int initValue = 1111;
 
 public override void OnNetworkSpawn()
{
       testValue.Value = initValue;
 
       ...
 }
```

<br>
<br>

#### NetworkVariable 은 다음과 같이 동기화 된다.

**1. 새로운 클라이언트가 게임에 참여 (혹은 늦게)**
- NetworkBehaviour 에 NetworkVariable 속성이 있는 NetworkObject가 생성되면, NetworkVariable 의 현재 상태(Value)는 클라이언트 측에서 자동으로 동기화

<br>

**2. 연결된 클라이언트**
- NetworkVariable 값이 변경되면, NetworkVariable.OnValueChanged 이벤트에 구독한 모든 연결된 클라이언트는 값이 변경되기 전에 이를 알림받는다.

- OnValueChanged 콜백에는 두 개의 매개변수가 있다. previous, current

<br>

#### 실제 사용 예시 1

- state 라는 NetowkrVariable 을 생성하고 OnValueChanged 에 실행할 State_OnValueChanged 메소드를 등록시킨다.

- 이후 state 값이 변경될 때 마다, OnStateChanged event 를 구독하고 있는 모든 구독자들을 Invoke 한다.

<br>

```csharp
// T 타입인 State 는 enum
[SerializeField] private NetworkVariable<State> state = new NetworkVariable<State>(State.WaitingToStart);
 
public event EventHandler OnStateChanged;
 
public override void OnNetworkSpawn()
{
    state.OnValueChanged += State_OnValueChanged;
    isGamePaused.OnValueChanged += IsGamePaused_OnValueChanged;
 
    if (IsServer)
    {
        NetworkManager.Singleton.OnClientDisconnectCallback += NetworkManager_OnClientDisconnectCallback;
        NetworkManager.Singleton.SceneManager.OnLoadEventCompleted += SceneManager_OnLoadEventCompleted;
    }
}
 
private void State_OnValueChanged(State previousValue, State newValue)
{
    OnStateChanged?.Invoke(this, EventArgs.Empty);
}
```

<br>

#### 실제 사용 예시 2

- 각 클라이언트는 Door를 사용할 때 마다 ServerRpc 를 호출하고 서버 측에서 Door의 상태인 State 를 토글한다.

- 이후 래핑된 Door.State.Value 가 변경되면 모든 연결된 클라이언트는 새로운 current value(여기서는 bool) 로 동기화되고 OnStateChanged 메소드가 각 클라이언트에서 호출된다.

<br>

```csharp
public class Door : NetworkBehaviour
{
    public NetworkVariable<bool> State = new NetworkVariable<bool>();
 
    public override void OnNetworkSpawn()
    {
        State.OnValueChanged += OnStateChanged;
    }
 
    public override void OnNetworkDespawn()
    {
        State.OnValueChanged -= OnStateChanged;
    }
 
    public void OnStateChanged(bool previous, bool current)
    {
        // note: `State.Value` will be equal to `current` here
        if (State.Value)
        {
            // door is open:
            //  - rotate door transform
            //  - play animations, sound etc.
        }
        else
        {
            // door is closed:
            //  - rotate door transform
            //  - play animations, sound etc.
        }
    }
 
    [Rpc(SendTo.Server)]
    public void ToggleServerRpc()
    {
        // this will cause a replication over the network
        // and ultimately invoke `OnValueChanged` on receivers
        State.Value = !State.Value;
    }
}
```

<br>
<br>
<br>

---

<br>

## Custom NetworkVariables

- NetworkVariable 을 이른바 "패킷" 형태로 커스텀하게 동기화가 가능해보인다.

- 주로 커스텀 형태의 NetworkVariable 은 제네릭 타입을 사용하여 직렬화를 해줘야한다.

<br>

#### NetworkVariable 예시

- 커스텀 NetowkrVariable 을 선언할 때, 값의 초기화 뿐만 아니라 NetworkVariableReadPermission, NetworkVariableWritePermission 옵션을 지정할 수도 있었다.

- MyCustomData 라는 임의의 struct 즉 **"구조체"**로 직렬화를 진행했다.

- 해당 구조체는 INetworkSerializable 이라는 인터페이스를 상속받아야한다.

- 이후 내부적으로 동기화 하고 싶은 Value 타입의 변수들을 선언하고 

<br>

```csharp
NetworkSerialize<T>
```

<br>

- 메소드 내부에서 BufferSerializer 를 통해 변수들의 직렬화를 진행한다.

<br>

```csharp
private NetworkVariable<MyCustomData> randomNumber = new NetworkVariable<MyCustomData>(
    new MyCustomData
    {
        _int = 1,
        _bool = true,
        _message = "nan"
    }, NetworkVariableReadPermission.Everyone, NetworkVariableWritePermission.Owner);
 
 
 
 
public struct MyCustomData : INetworkSerializable
{
    public int _int;
    public bool _bool;
    public string _message;
     
    public void NetworkSerialize<T>(BufferSerializer<T> serializer) where T : IReaderWriter
    {
        serializer.SerializeValue(ref _int);
        serializer.SerializeValue(ref _bool);
        serializer.SerializeValue(ref _message);
    }
}
```

<br>

- 이후 OnValueChanged 에 randomNumber 값을 람다식으로 구독하고 디버그 로그로 출력해주자.

- "T" 키를 눌러 randomNumber 값을 지정하여 출력하는 로그인데, 여기서 주의할 점은  해당 NetworkVariable 의 소유 권한을 누구에게 부여할 것이냐 이다.

- 위 예제 Door 에서는 state 값이 ServerRpc 를 통해 바뀌며 서버가 주체가 되는 NetworkVariable 인 반면, 해당 예제는 randomNumber  클라이언트가 주체가 되는 NetworkVariable 이다.

- 요약하자면, NetworkVariable 의 소유권이 서버가 관리(각종 FSM 상태, 게임 로직 변수) vs 클라이언트가 관리 (플레이어의 스텟) 에 따라 역할이 나뉘게 된다.

<br>

```csharp

public override void OnNetworkSpawn()
  {
      randomNumber.OnValueChanged += (MyCustomData previousValue, MyCustomData newValue) =>
      {
          Debug.Log(OwnerClientId + ";  " + newValue._int + ";  " + newValue._bool + ";  " + newValue._message);
      };
  }
 
  private void Update()
  {
      if (!IsOwner) return;
 
      if (Input.GetKeyDown(KeyCode.T))
      {       
          randomNumber.Value = new MyCustomData
          {
              _int = Random.Range(0, 100),
              _bool = Random.Range(0, 1) == 0 ? true : false,
              _message = "Hello, World!",
          };
      }
  }
```

<br>
<br>

#### NetworkList 예시

- NetworkVariable 의 List 형태인, NetworkList 또한 존재한다.

- **IEquatable** 인터페이스가 추가된 것을 확인할 수 있는데, 이는 NetworkVariable 혹은 NetworkList 구조체 타입이 동일성 비교를 효율적으로 수행할수 있도록 하기 위함이다.

- 또한 데이터 변경 여부를 감지하여 네트워크 트래픽을 줄일 수 있다. 

<br>

```csharp
public struct PlayerData : IEquatable<PlayerData>, INetworkSerializable
{
    public ulong clientId;
    public int colorId;
    public FixedString64Bytes playerName;
    public FixedString64Bytes playerId;
     
    public bool Equals(PlayerData other)
    {
        returnIEquatable
            clientId == other.clientId &&
            colorId == other.colorId &&
            playerName == other.playerName &&
            playerId == other.playerId;
    }
 
    public void NetworkSerialize<T>(BufferSerializer<T> serializer) where T : IReaderWriter
    {
        serializer.SerializeValue(ref clientId);
        serializer.SerializeValue(ref colorId);
        serializer.SerializeValue(ref playerName);
        serializer.SerializeValue(ref playerId);
    }
}
```

<br>

- List 타입이라 그런지 previous, current 두 개의 매개변수로 나뉘지 않고 NetworkListEvent 내부적으로

- ***Value***, ***PreviousValue*** 두 가지 변수가 존재한다.

<br>

```csharp
public event EventHandler OnPlayerDataNetworkListChanged;
 
private NetworkList<PlayerData> playerDataNetworkList;
 
private void Awake()
{
    playerDataNetworkList = new NetworkList<PlayerData>();
    playerDataNetworkList.OnListChanged += PlayerDataNetworkList_OnListChanged;
}
 
 
private void PlayerDataNetworkList_OnListChanged(NetworkListEvent<PlayerData> changeEvent)
{
    OnPlayerDataNetworkListChanged?.Invoke(this, EventArgs.Empty);
}
```

<br>
<br>
<br>

---

<br>

## RPC vs NetworkVariable

- **RPC 사용** : 일시적인 이벤트나 정보를 전달할 때 사용하며, 해당 정보가 수신될 때만 유용하다.

- **NetworkVariables 사용** : 지속적인 상태 정보를 관리하는 데 유용하다. "지속적인 상태 정보" 를 게임 내에서 계속 유지하고 모든 플레이어에게 일관적으로 전달되어야 한다.

- 둘 중에 뭘 써야 하는지에 대한 가장 빠른 결정 방법은 "중간에 게임에 합류한 플레이어가 그 정보를 받아야 하는가?"  질문을 던져 보는 것이다.

<br>

![Desktop View](/assets/img/post/unity/netcode019.png){: : width="1000" .normal }    
_NetworkVariable 는 현재 상태를 전송하여 늦게 합류한 클라이언트가 쉽게 최신 상태를 따라잡을 수 있게 해준다._

<br>

![Desktop View](/assets/img/post/unity/netcode020.png){: : width="1000" .normal }    
_만약 RPC를 모든 클라이언트에게 보낸다면, 그 RPC가 전송된 후에 중간에 게임에 합류한 모든 플레이어는 그 정보를 놓치고 잘못된 비주얼을 클라이언트에서 보게 될 것._

<br>

- 이렇게 되면 RPC 는 하등 쓸모 없고, NetworkVariables 로만 사용해도 되는거 아닌가요? 라고 생각할 수 있지만.. 

<br>
<br>

## 모든 것에 NetworkVariables 를 사용하지 않는 이유

- **RPCs가 더 간단하다.**

- 게임 내의 모든 일시적인 이벤트 (폭발, 오브젝트 생성 등과 같은) 를 위해 NetworkVariable 로 선언해서 사용할 필요는 없다는 것이다.

<br>


- NetworkVariable 을 사용하여 두 변수가 동시에 수신 되도록 하고 싶다면, RPCs 가 적합

- NetworkVariables "a" 와 "b" 를 변경하면, 클라이언트 측에서 두 변수가 동시에 수신된다는 보장이 없다.

<br>

- 아래 사진을 보면 지연 시간으로 인해 클라이언트가 제 각기 다른 시간에 업데이트를 수신하는 것을 확인할 수 있다.

<br>

![Desktop View](/assets/img/post/unity/netcode021.png){: : width="1000" .normal }    
_동일한 틱 내에서 업데이트된 서로 다른 네트워크 변수가 동시에 클라이언트에 전달된다는 보장은 없다._

<br>
<br>

- 반면 동일한 RPC 의 두 매개변수로 보낸다면, 클라이언트 측에서 두 변수가 동시에 수신 가능.

<br>

![Desktop View](/assets/img/post/unity/netcode022.png){: : width="1000" .normal }    
_여러 개의 다른 네트워크 변수들이 모두 동시에 동기화되도록 하기 위해 우리는 클라이언트 RPC를 사용하여 이러한 값 변화들을 함께 결합할 수 있다._

<br>
<br>

#### 정리

1. NetworkVariable 은 지속적인 상태 정보를 전달할 때 사용한다.
2. 지속적인 상태 정보란, 게임 내에서 계속 유지되고 모든 플레이어에게 일관되게 전달되어야 하는 정보를 의미한다.
3. 이를 통해 새로운 플레이어가 접속해도 최신 상태를 즉시 동기화할 수 있으며, 모든 플레이어가 동일한 상태정보를 공유할 수 있다.
