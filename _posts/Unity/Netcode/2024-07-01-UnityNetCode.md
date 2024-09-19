---
title: Unity Netcode - Networking Components
date: 2024-07-01 10:00:00 +/-TTTT
categories: [Unity, Netcode]
tags: [Unity, Netcode, Dedicated Server, NetworkObject, NetworkManager, NetworkBehaviour, NetworkAnimator, NetworkRigidbody]     # TAG names should always be lowercase

toc: true
toc_sticky: true
math: true  
use_math: true
mermaid: true
---

[![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https%3A%2F%2Fepheria.github.io&count_bg=%2379C83D&title_bg=%23555555&icon=&icon_color=%23E7E7E7&title=views&edge_flat=false)](https://hits.seeyoufarm.com)

---

<br>

## Unity Netcode 란?

<br>

- Unity Netcode for Gameobject 를 의미하며 (Unity Netcode for ECS 도 존재함..) 유니티에서 제공하는 네트워크 개발 라이브러리이다.

- 고수준의 API 를 제공하며, 게임 객체 상태의 동기화, 원격 프로시져 호출(RPC), Connection 관리 등을 쉽게 구현할 수 있다는 장점이 있다.

- 또한 로우레벨에서는 기본적으로 네트워크 전송 라이브러리인 Unity Transport 를 사용하여 데이터 패킷 전송, 재전송, 순서 보장 등을 처리한다.

- 예를 들어, NetworkBehaviour 에서 ServerRpc 를 호출하면, Unity Transport 가 이 호출을 패킷으로 변환하여 서버로 전송한다.

<br>

---

<br>

## Unity Netcode Components 구성 요소

<br>

---

<br>

## NetworkManager

<br>

- NetworkManager 는 네트워크 세션의 수명 주기를 관리하고, 서버와 클라이언트 간의 연결을 설정한다.

- 보통 Host-Client, Relay Server, Dedicated Server 등을 통해 연결이 가능하다.

<br>

- 작동 방식

![Desktop View](/assets/img/post/unity/netcode001.png){: : width="600" .normal }    

<br>

- Network Transport 를 Unity Transport 로 설정해준다.

> - Player Prefab 에 일명 Player 껍데기를 할당해주자. (Network 통신 전용 캐릭터를 의미함. NetworkObject, NetworkTransform 등의 컴포넌트가 부착되어있음)     
>     
> - Netowork Prefab Lists 에는 스크립터블 오브젝트가 할당되어 있는데, 여기서 생성하고 싶은 프리팹들을 리스트에 할당해주면 Spawn, Despawn 이 가능하다. (내부적으로 GC 까지 같이 돌아감)     
>     
> ![Desktop View](/assets/img/post/unity/netcode002.png){: : width="600" .normal }    
>     
> ```csharp 
> spawnedObjectTransform.GetComponent<NetworkObject>().Spawn(true);
> spawnedObjectTransform.GetComponent<NetworkObject>().Despawn();
> ```

<br>

- NetowkrManager 컴포넌트

![Desktop View](/assets/img/post/unity/netcode003.png){: : width="600" .normal }    

<br>

- 컴포넌트를 추가하여  씬에 배치해주면 끝.. 

![Desktop View](/assets/img/post/unity/netcode004.png){: : width="600" .normal }    

<br>

- 자매품 Untiy Transport 도 존재한다. 스크립트로 IP 주소와 Port 번호 수정이 가능하다.

```csharp

ut = NetworkManager.Singleton.GetComponent<UnityTransport>();
 
...
 
ut.SetConnectionData(ipAddStr, portNumber);
 
...
 
// 서버는 EC2 인스턴스를 사용하며 가상환경에서 데디케이티드 서버로 돌아가므로.. 그래픽스 디바이스 타입이 없다.
// 따라서 NetworkManager 를 통해 서버-클라이언트 실행을 구분하는 코드는 다음과 같다.
if (SystemInfo.graphicsDeviceType == GraphicsDeviceType.Null)
{
    Debug.Log("ServerBuild");
    NetworkManager.Singleton.StartServer();
}
else
{
    NetworkManager.Singleton.StartClient();
}
```

<br>
<br>

---

<br>

### NetworkObject


<br>

- NetworkObject 는 네트워크를 통해 동기화되고 관리되는 모든 게임 오브젝트의 핵심이다.

- NetworkObject 컴포넌트 하나와 최소한 하나의 NetworkBehaviour 컴포넌트를 포함해야한다. 그래야만 게임 오브젝트가 네트워크 코드에 반응하고 상호작용이 가능해지므로..

![Desktop View](/assets/img/post/unity/netcode005.png){: : width="600" .normal }    
![Desktop View](/assets/img/post/unity/netcode006.png){: : width="600" .normal }    
_PlayerKitchen 프리팹 내부에 껍데기 형태로 NetworkObject 컴포넌트와 NetworkBehaviour 를 상속받는 Player 컴포넌트가 부착된 모습._

<br>

```csharp
public class Player : NetworkBehaviour, IKitchenObjectParent
{
    public static event EventHandler OnAnyPlayerSpawned;
    public static event EventHandler OnAnyPickedSomething;
 
    public static void ResetStaticData()
    {
        OnAnyPlayerSpawned = null;
    }
 
    ...
 
}
```

- 또한, Netcode 인식 속성 (네트워크 동기화를 위한 네트워크 객체의 모든 기능 : NetworkVariable 과 같은)을 복제하거나 RPC 를 보내고 받으려면 게임 오브젝트에 NetworkObject 와 NetworkBehaviour 가 부착되어 있어야 한다.

- 또한 NetworkTransform, NetworkAnimator 등과 같은 컴포넌트도 이 NetworkObject 가 필수.

<br>

> **NetworkObject 는 인스턴스화 되고 고유한 NetworkObjectId 가 부여된다.**     
>      
> - 최초 클라이언트가 연결되면 'NetworkObject.GlobalObjectIdHash' 값을 식별한다.     
>     
> - 로컬에서 인스턴스화 된 후, 각 NetworkObject는 네트워크 전체에서 NetworkObject를 연결하는데 사용되는 'NetworkObjectId'가 할당된다.      
>      
> - 예를 들어, 한 피어가 "NetworkObjectId 103 을 가진 오브젝트에 이 RPC 를 보내라"고 말하면, 모든 사람은 그것이 어떤 오브젝트를 의미하는지 알게 된다.      
>      
> - 마지막으로, NetworkObject는 인스턴스화되고 고유한 NetworkObjectId 가 할당될 때 클라이언트에 생성된다.
{: .prompt-info }

<br>
<br>

### 소유권 (Ownership)

<br>

- 서버 또는 연결된 승인된 클라이언트가 각각의 NetworkObject를 소유한다.

- 기본적으로 Netcode for GameObjects 는 서버 권한 방식을 사용하고 있으며, 서버만이 NetworkObject 를 생성하거나 제거할 수 있지만

- 클라이언트에 권한을 부여해서 NetworkObject 를 생성, 삭제가 가능하다.

<br>

```csharp
// 기본 NetworkObject.Spawn 메서드는 서버 측 소유권을 가정
 
GetComponent<NetworkObject>().Spawn();
```


```csharp
// 소유권을 지정하여 NetworkObject를 생성하려면 다음을 사용
 
GetComponent<NetworkObject>().SpawnWithOwnership(clientId);
```

```csharp
// 소유권을 변경하려면 ChangeOwnership 메서드를 사용
 
GetComponent<NetworkObject>().ChangeOwnership(clientId);
```

```csharp
// 소유권을 서버에 다시 넘기려면 RemoveOwnership 메서드를 사용
 
GetComponent<NetworkObject>().RemoveOwnership();
```

<br>

- 로컬 클라이언트가 NetworkObject 의 소유자인지 확인하려면 'NetworkBehaviour.IsOwner' 속성을 확인할 수 있다.

- 서버가 NetworkObject를 소유하는지 확인하려면 NetworkBehaviour.IsOwnedByServer / IsServer 속성을 확인할 수 있다.

<br>

```csharp
// IsOwner, IsServer 는 NetworkBehaviour 를 상속받으면 프로퍼티로 사용이 가능.
     
    public class Player : NetworkBehaviour
    { 
 
        ...
 
        public override void OnNetworkSpawn()
        {
            if (IsOwner)
            {
                LocalInstance = this;
            }
             
            ...
 
            if (IsServer)
            {
                NetworkManager.Singleton.OnClientDisconnectCallback += NetworkManager_OnClientDisconnectCallback;
            }
 
        }
 
        ...
 
    }
```

<br>

- 서버측에서 특정 클라이언트의 PlayerObject 인스턴스를 가져와야 하는 경우 다음과 같은 방법을 사용할 수 있다.

<br>

```csharp
NetworkManager.Singleton.ConnectedClients[clientId].PlayerObject;
```

<br>
<br>

## NetworkBehaviour

<br>

- NetworkBehaviour 는 Unity Monobehaviour 를 상속하는 abstract class 이며, NetworkVaraible 동기화나 RPC 를 송수신하려면 NetworkObject 컴포넌트와 함께 필수적으로 게임 오브젝트에 포함되어야하는 컴포넌트이다.

<br>

- **Spawning**

- NetworkObject 가 스폰될 때, NetworkObject 와 관련된 각 NetworkBehaviour 에서 "OnNetworkSpawn" 이 호출된다.

- 이 시점에서 모든 Netcode 관련 초기화가 이루어져야한다.

<br>

```csharp

public class Player : NetworkBehaviour
    { 
        public override void OnNetworkSpawn()
        {
 
        }
    }
```

<br>


- 아래 표는 NetworkBehaviour.OnNetworkSpawn 의 호출 시점을 표로 나타낸것.

<br>

| **동적으로 Spawn 되는 경우** | **Scene 에 배치된 경우**  |   
| ----------------| ------------------- | 
| Awake             | Awake                   |  
| OnNetworkSpawn            | Start                  |  
| Start            | OnNetworkSpawn                   |  

<br>

- **Despawning**

- 각 NetworkBehaviour 에는 가상 함수 OnDestroy 메소드를 오버라이드하여 NetworkBehaviour 가 파괴될 때 처리를 재정의할 수 있다.

<br>

```csharp

public override void OnDestroy()
{
    // Clean up your NetworkBehaviour
 
    // Always invoked the base
    base.OnDestroy();
}
```

<br>
<br>

- **NetworkBehaviour 동기화**

- NetworkBehaviour 를 통해 NetworkObject 를 스폰하기 전, 스폰 중, 스폰 후에 대한 설정을 동기화할 수 있다.

<br>

![Desktop View](/assets/img/post/unity/netcode012.png){: : width="1400" .normal }    

<br>
<br>

---

<br>

## NetworkTransform

<br>

> **NetworkTransform의 동기화 작업 개요**     
>      
>   a. 동기화할 Transform Axis 를 결정한다.     
>   
>   b. 값들을 직렬화한다. 여기서 직렬화란, NetworkVariable 의 INetworkSerialize 와 같은 형태로 추측됨    
>   
>   c. 직렬화된 값을 메시지로 모든 연결된 클라이언트에 보낸다.    
>   
>   d. 메시지를 처리하고 값을 역직렬화 한다.
>   
>   e. 대응되는 Transform Axis 에 역직렬화한 값을 적용한다.
{: .prompt-tip }

<br>

- **컴포넌트 구성**

- 보통 NetworkObject, NetworkBehaviour 컴포넌트를 부착한 하이어라키상에 같이 부착해준다.
- NetworkTransform 의 동기화는 ***Authoritative Mode (권한 모드)*** 에 따라 나뉘게 된다.

<br>

- **1. NetworkTransform : Server Authoritative Mode (서버 권한 모드 전용)**
> - 서버에서 이동 로직을 계산하고 연결된 클라이언트들에게 위치 정보를 동기화 시켜준다.

![Desktop View](/assets/img/post/unity/netcode023.png){: : width="700" .normal }    

<br>

- **2. OwnerNetworkTransform : Owner/Client Authoritative Mode (클라이언트 권한 모드 전용)**
> - Interpolation 기능을 사용할 수 있다.     
> - 클라이언트 A에서 이동 로직을 계산하고 위치 정보를 서버에 전송해주고, 서버는 연결된 클라이언트들에게 A의 위치정보를 동기화, 중계해주는 역할만 한다.

![Desktop View](/assets/img/post/unity/netcode007.png){: : width="700" .normal }    

<br>

- 어떤 권한 모드를 사용할 지는 신중하게 결정을 내려야한다. **[권한 모드에 관해 자세한 내용은 이 문서를 확인](https://epheria.github.io/posts/UnityNetCode3/)**하는 것을 추천한다.

<br>
<br>

- 다음은 위 NetworkTransform 에 인스펙터 내부의 property 들에 대해 알아보자.

<br>
<br>

- **Syncing**

- 일부 NetworkTransform 속성은 권한 인스턴스에 의해 자동으로 모든 비권한 인스턴스로 동기화된다. 

- 여기서 중요한 점은 동기화된 속성이 변경되면 NetworkTransform 이 효과적으로 "Teleport" 된다. (모든 값이 동기화되고 보간이 재설정됨)

<br>

- **Synchronization 최적화**

![Desktop View](/assets/img/post/unity/netcode008.png){: : width="500" .normal }    

- 위 사진을 보면 대부분의 경우 GameObject 의 모든 Transform 값을 네트워크 상에서 동기화될 필요가 없다.

- 즉 GameObject 의 크기가 변경되지 않는다면, Scale 같은 값을 동기화 하지 않도록 비활성화 해둘 수 있다.

- 동기화를 비활성화 하면, CPU 비용과 네트워크 대역폭을 절약할 수 있다. → 인스턴스 당 추가 처리 오버헤드가 제거된다.

<br>

- **Thresholds (임계값)**

- 임계값을 사용하여 최소 임계값을 설정할 수 있다. 이는 임계값 이상 또는 동일한 변경 사항만을 동기화하여 동기화 업데이트 빈도를 줄일 수 있다.

- NetworkTransform 에 보간이 활성화된 경우, 위치 임계값(Position Thresold)을 증가 시키면 객체의 움직임의 "부드러움"에 영향을 주지 않으면서도 위치 업데이트 빈도를 낮출 수 있다.

- 빈도를 낮추게 되면, 인스턴스당 대역폭 비용을 줄일 수 있다.

- 위치 임계값을 낮출 수록 빈도가 증가한다. → 인스턴스당 대역폭 비용이 증가

![Desktop View](/assets/img/post/unity/netcode009.png){: : width="600" .normal }    

<br>

- **Delivery (전달)**

- 네트워크 조건이 나빠질 경우 패킷 지연, 패킷 손실이 발생할 수 있다. → 주로 "끊김" 이 발생해서 시각적으로 움직임의 격차를 발생시킨다.

- 하지만, Netcode 의 NetworkTransform은 Delta(위치, 회전, 스케일) 상태가 손실이 되더라도, BufferedLinearInterpolator 를 통해서

- 이미 손실된 다음 상태 업데이트를 기다리지 않고, 전체 보간 경로를 계산하여 쉽게 복구할 수 있다.

- 예를 들어, TickRate 30 인 경우, 1초 동안 전체 상태 업데이트의 5%~10% 를 소실해도 완벽하게 전달된 30 델타 업데이트 경로와 상대적으로 유사한 보간 경로를 도출할 수 있다.

![Desktop View](/assets/img/post/unity/netcode010.png){: : width="400" .normal }    

<br>

- Use Unreliable Deltas 옵션은 신뢰할 수 없는 델타 상태 업데이트를 활성화 하겠다는 의미다.

    - 패킷 손실 회복 : 신뢰할 수 없는 순서로 업데이트를 전송하면 일부 패킷이 손실되더라도 전체 상태 업데이트 경로의 작은 부분만 손실되며 나머지는 정상적으로 유지된다.

    - 지연 감소 : 신뢰할 수 없는 전송은 일반적으로 신뢰할 수 있는 전송보다 지연이 적다. 신뢰할 수 있는 전송은 패킷 손실 시 재전송을 시도해야 하므로 지연이 더 커질 수 있다.

<br>


- 하지만, 대역폭 소비가 증가할 수 있다. →  축 프레임 동기화, 빈번한 패킷 전송으로 인한 대역폭 소비 증가

- 결론 : UseUnreliableDeltas 옵션을 활성화하면 네트워크의 패킷 손실과 지연 문제를 완화할 수 있지만, 약간의 추가 대역폭이 소비될 수 있다. 이 옵션을 사용할 때는 네트워크 환경과 대역폭 사용량을 고려하여 최적의 설정을 선택하는 것이 중요하다. 만약 대역폭 소비가 문제가 된다면, 이 옵션을 비활성화하고 테스트를 통해 시각적 결함이 없는지 확인한 후 비활성화된 상태로 유지하는 것도 하나의 방법이 될 수 있다.

<br>

- **Interpolation (보간)**

![Desktop View](/assets/img/post/unity/netcode011.png){: : width="2000" .normal }    

- 보간은 기본적으로 활성화되어 있다. 지연이 높을 때 보간을 적용하여 "Zittering" 을 방지할 수 있다.

- 이외에도, Configuration 에는 여러가지 옵션이 존재하지만, Interpolation 을 제외한 나머지 옵션은 비활성화 하는 것을 추천한다. (Euler → Quaternion 을 사용하면 Quaternion 압축을 위해 대역폭 증가 가능성이 있음)

- 자세한 설명은 공식문서 참조바람.

<br>
<br>

### Authority Mode

- **Server authoriative mode (서버 권한 모드)**

- 기본적으로 NetworkTransform 은 서버 권한 모드로 작동한다. (NetworkTransform 컴포넌트 부착 시)

- 이는 Transform Axis 의 변경 사항이 서버 측에서 감지되고 연결된 클라이언트에 푸시된다는 것을 의미.

- 또한 클라이언트에서 발생한 Transform Axis 값의 모든 변경사항이 권한 상태(서버 측)에 의해 덮어씌여진다는 것을 의미한다.

- 이로 인해 클라이언트 측에서 위치가 즉시 업데이트가 되지 않는 경우가 발생하며, 클라이언트 측 조작이 먹통이 되어버리는 경우가 발생한다.

<br>


- **Owner authoriative mode (소유자 권한 모드) → ClientNetworkTransform**

- 위 내용을 해결하기 위해서는, 소유자 권한 모드로 업데이트를 해줘야 한다.

- 특정 NetworkObject (일반적으로 플레이어) 에 대해 클라이언트 측에서 즉시 위치 업데이트를 해야만 하는 경우가 있다.

- NetworkTransform 컴포넌트가 처음 초기화 될 때, **NetworkTransform.OnIsServerAuthoriative** 메서드에 의해 소유자 권한이 결정된다.

- 따라서 소유자 권한 모드를 활성화 하기 위해서는 위 메소드의 반환값을 ***false*** 로 바꿔주면 됩다.

<br>

```csharp
public class OwnerNetworkTransform : NetworkTransform
{
    protected override bool OnIsServerAuthoritative()
    {
        return false;
    }
}
```

<br>

- 위 스크립트를 작성 후, 플레이어 프리팹에 NetworkTransform 컴포넌트 대신에 OwnerNetworkTransform 컴포넌트를 부착하면 됨.

<br>
<br>

---

<br>

## NetworkRigidbody

<br>

- Netcode for GameObjects 에서는 멀티플레이 물리 시뮬레이션 관리를 위해 기본적으로 ***Server-Authoritative physics (서버 권한 기반 물리)*** 방식을 제공한다.

- 이 경우 물리 시뮬레이션은 오직 **"서버"**에서만 실행된다.

- 네트워크 물리를 적용하기 위해서는 NetworkObject 컴포넌트가 있는 프리팹에 Rigidbody 와 함께 NetoworkRigidbody 가 부착되어야 한다.

- 또한 권한 모드에 관해서는 [서버 권한 모드 관련 문서](https://epheria.github.io/posts/UnityNetCode3/)를 참조하는 것을 추천한다.

<br>
<br>

#### Authoritative Mode 를 Client 로 설정했을 때

- NetworkRigidbody 를 부착하면 Server 상에서 연결된 클라이언트들의 Rigidbody 의 **isKinematic** 이 활성화가 되어버린다.

- 반면 클라이언트 상은 isKinematic 이 비활성화 되어 있다. 따라서 클라이언트에서는 물리 기반 이동(Rigidbody.velocity 와 같은)이 가능하고, Client Network Transform 이 주체가 되어 서버에 클라이언트 자신의 Transform 정보를 보내어 다른 연결된 클라이언트들과 동기화 한다. (이는 클라이언트에 권한이 부여 되었기 때문에 보안상 위험도가 높다.)

- 하지만 물리 기반 이동은 가능했으나, 서버상에서는 연결된 클라이언트들의 isKinematic 이 활성화가 되었기 때문에 파티게임에 사용해야하는 기본적인 서버-클라이언트 간 Rigidbody 물리 시뮬레이션이 불가능했다. (오직 서버에서만 물리 시뮬레이션이 가능하므로)

- 즉, 로컬 클라이언트 (본인) 에서의 Rigidbody 물리 시뮬레이션은 가능하지만 다른 클라이언트 혹은 서버에 대한 물리 시뮬레이션(Network Rigidbody)은 불가능했다. (다른 클라이언트에 대한 물리적인 간섭이 불가능했다는 말)

<br>

- Client Authoritative Mode 는 유저의 인풋 → Transform 이동 계산을 클라이언트에서 처리하기 때문에 즉각적인 반응이 가능하다는 장점이 있지만 본인과 다른 클라 혹은 서버 간 Rigidbody 물리 시뮬레이션이 불가능하여 포기해야했다.

- 그렇다고 물리 시뮬레이션이 불가능한가?는 아닐 것이다. 물리 시뮬레이션을 서버에서 직접 수동으로 힘을 추가하거나 이벤트로 구현하면 사용가능 하지만, 흔들림(wobble)이 발생할 가능성이 높다.

<br>

- 따라서, 프로젝트가 어떤 게임 유형인지에 따라 권한 모드를 적절하게 선택하는 것을 권장한다.

<br>

{% include embed/youtube.html id='10XBoDuyjb4' %}
_Client Authoritative Mode 물리 처리 영상_

<br>

![Desktop View](/assets/img/post/unity/netcode029.png){: : width="800" .normal }    
_서버상의 연결된 클라이언트 Rigidbody 의 isKinematic 이 활성화된 모습_

<br>

#### isKinematic 비활성화를 위해 시도해봤던 내용

```csharp
public class CustomNetworkRigidbody : NetworkRigidbody
{
    private Rigidbody m_Rigidbody;
 
    private void Start()
    {
        m_Rigidbody = GetComponent<Rigidbody>();
    }
     
    public override void OnNetworkSpawn()
    {
        base.OnNetworkSpawn();
 
        if (IsServer)
        {
            m_Rigidbody.isKinematic = false;
        }
    }
    public override void OnGainedOwnership()
    {
        base.OnGainedOwnership();
     
        if (transform.parent != null)
        {
            var parentNetworkObject = transform.parent.GetComponent<NetworkObject>();
             
            if (parentNetworkObject != null)
            {
                m_Rigidbody.isKinematic = false;
            }
        }
 
        m_Rigidbody.isKinematic = false;
    }
}
```

<br>

1. OnNetworkSpawn 네트워크 오브젝트 스폰 타이밍에 비활성화 시도 → **실패**
2. OnGainedOwnership 권한 부여 타이밍에 비활성화 시도 → **실패**

<br>

- isKinematic 활성화 문제는 근본적으로 서버에 물리 시뮬레이션이 위임되었기 때문에 절대 비활성화가 불가능하다는 것을 배울 수 있었다..

<br>
<br>

#### Authoritative Mode 를 Server로 설정했을 때

<br>

{% include embed/youtube.html id='sPZimrgZqB4' %}
_Client Authoritative Mode 물리 처리 영상_

<br>
<br>

---

<br>

### NetworkAnimator

`테스트 및 작성중..`
