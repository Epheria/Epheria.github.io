---
title: Unity Netcode - Authoritative Mode
date: 2024-08-13 10:00:00 +/-TTTT
categories: [Unity, Netcode]
tags: [Unity, Netcode, Server Authoritative Mode, Client Authoritative Mode, Authoritative Mode]     # TAG names should always be lowercase

toc: true
toc_sticky: true
math: true  
use_math: true
mermaid: true
---

[![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https%3A%2F%2Fepheria.github.io&count_bg=%2379C83D&title_bg=%23555555&icon=&icon_color=%23E7E7E7&title=views&edge_flat=false)](https://hits.seeyoufarm.com)

---

<br>

- 지금까지 확인한 바로는 권한 모드를 커스텀 할 수 있는 NGO(Netcode for GameObject) 컴포넌트는 다음 두 가지이다.

<br>

1. **NetworkAnimator**
2. **NetworkTransform**

<br>
<br>

```csharp
public class OwnerNetworkAnimator : NetworkAnimator
{
    protected override bool OnIsServerAuthoritative()
    {
        return false;
    }
}
```

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

- NetworkAnimator, NetworkTransform 컴포넌트 대신 해당 컴포넌트를 상속받은 위 두 컴포넌트를 부착해주면 "커스텀 권한 모드"를 사용할 수 있다.

- `return false` → 소유자/클라이언트 권한 모드 변경
- `return true` → 서버 권한 모드 유지

<br>
<br>

---

<br>

## Server Authoritative Mode (서버 권한 모드)

- 서버 권한 모드에서 클라이언트의 역할은 Input (키 입력, 카메라 회전 등) 을 통해 관련된 데이터들을 서버에 패킷을 보내고 물리 연산, 로직, 게임 플레이에 대한 최종 결정은 서버에서 이루어진다.

<br>

![Desktop View](/assets/img/post/unity/netcode024.png){: : width="1000" .normal }    
_서버가 최종 게임 플레이 결정을 내린다._

<br>

#### 서버 권한 모드의 장점

- **Good for world consistency (일관된 월드 상태 유지)**
> - 서버가 모든 게임 플레이 결정을 내리기 때문에, 플레이어가 문을 열거나 봇이 플레이어를 공격하는 등의 결정이 동시에 이루어진다.       
> - 만약 클라이언트 권한을 사용할 경우, 클라이언트 A 에서 내린 결정과 클라이언트 B에서 내린 결정이 각각 **RTT(Rount Trip Time)** 만큼 지연되며, 이로인해 동기화 문제가 발생하게 된다.     
> - 예를 들어, A 가 B를 공격했는데, 이미 B가 엄폐물 뒤에 숨은 경우와 같은 문제가 발생할 수 있다. 그러나 이런 모든 게임 로직이 하나의 서버에서 처리된다면 일관성을 유지할 수 있다.

<br>

- **Good for security (보안 강화)**
> - 중요한 데이터 (캐릭터 스테이터스, 포지션 등)는 서버 권한으로 관리가 가능하며, 이를 통해 부정행위자가 해당 데이터를 변경하지 못하게 막을 수 있다.

<br>
<br>

#### 서버 권한 모드의 문제점

- **Reactivity (반응성)**
> - 유저가 인풋을 입력하고 → 서버까지 레이턴시 발생 → 서버 로직 실행 → 되돌아오는 레이턴시 발생까지 전체 RTT를 기다려야 한다.     
> - 이로 인해 반응성이 늦게 보일 수 있으며 유저에게 답답하게 느껴질 수 있다.

<br>
<br>

#### 서버 권한 모드의 특징

- 단적으로, 서버 권한 모드에서의 클라이언트는 오직 유저 입력과 입력 데이터 전송, 렌더링 역할만 수행한다고 보면 된다.
- NGO 는 서버 권한을 기반으로 구성되어 있어서 서버만이 NetworkVariables 를 사용할 수 있다.
- 하지만 클라이언트로부터 오는 RPC를 수락할 때는 해당 RPC가 신뢰할 수 없는 출처에서 오는 것이므로 반드시 유효성 검사를 추가해야한다.

<br>
<br>

---

<br>

## Owner/Client Authoritative Mode (소유자/클라이언트 권한 모드)

- 서버가 여전히 월드 상태를 공유하는 허브 역할을 하지만, 클라이언트가 자신의 현실(위치, 데이터)을 소유하고 이를 서버와 다른 클라이언트들에게 강요하게 된다.

<br>

![Desktop View](/assets/img/post/unity/netcode025.png){: : width="1000" .normal }    
_클라이언트가 최종 게임 플레이 결정을 내린다._

<br>

#### 클라이언트 권한 모드의 장점

- **Good for Reactivity (반응성 향상)**
> - 서버 권한 모드에서는 유저 입력을 서버에 보내고 서버에서 로직을 계산하고 결과를 받았다면, 클라이언트 권한 모드에서는 입력과 계산을 클라이언트에서 처리하고 결과를 서버에 보내준다고 생각하면 된다.      
> - 예를 들어, FSM 에서 모든 State 들에 대한 로직은 클라이언트에서 계산하고 현재 State 값만 서버에 동기화 해주면 된다.      
> - 따라서, 서버는 오직 클라이언트의 정보를 다른 클라이언트들에게 전달하는 역할만 하게 된다.

<br>
<br>

#### 클라이언트 권한 모드의 문제점

- **Issue: World consistency (일관성 문제)**
> - 클라이언트 권한을 사용하는 게임에서는 **"동기화 문제"**가 발생할 수 있다. 클라이언트 측에서 캐릭터가 이동할 때 아무 문제가 없다고 생각할 수 있지만, 그 동안 적이 내 캐릭터를 기절 시켰을 수 있다.     
> - 즉, 적은 내가 보고 있는 것과는 다른 세계에서 내 캐릭터를 기절시킨 것이다.    
> - 만약, 클라이언트가 오래된 정보를 사용하여 **"권한 있는"** 결정을 내리게 한다면, 동기화 문제, 물리 객체의 중첩과 같은 많은 문제에 직면하게 될 것이다.

<br>
<br>

- **Ownership race conditions (경쟁 상태 돌입)**
> - 여러 클라이언트가 동일한 공유 오브젝트에 영향을 줄 수 있을 경우, 이는 경쟁 상태에 돌입하게 되고 크나큰 혼란을 일으킬 수 있다.      
>       
> - **다수의 클라이언트가 공통 오브젝트에 자신들의 현실(계산,로직)을 강요하려고 한다.**      
> - 이를 방지하기 위해서는 서버가 소유권을 제어하고 있으므로 경쟁 상태를 방지하기 위해 클라이언트들은 서버에 소유권을 요청하고, 소유권을 기다린 후, 원하는 클라이언트 권한 로직을 실행하도록 해야한다.

<br>

![Desktop View](/assets/img/post/unity/netcode026.png){: : width="1000" .normal }    
_권한 요청 없이 자신이 로직을 강요했을 때_

<br>

![Desktop View](/assets/img/post/unity/netcode027.png){: : width="1000" .normal }    
_권한 요청을 추가 했을 때._

<br>
<br>

#### 클라이언트 권한 모드의 특징

- 클라이언트 권한은 서버 호스팅 위주의 게임에서는 위험한 방법이다. 악의적인 플레이어가 치팅하거나 승부를 조작하여 게임에서 승리할 수 있기 때문이다.
- 그러나 클라이언트가 주요한 게임 플레이 결정을 내리기 때문에, 사용자의 입력 결과를 몇백 밀리초를 기다릴 필요 없이 즉시 표시가 가능하다는 장점이 있다.


- 플레이어가 치트할 이유가 없을 경우 클라이언트 권한 모드는 복잡한 입력 예측 기술 없이 반응성을 높일 수 있는 좋은 방법이다.


- PVE 게임에서는 클라이언트 권한 모드를 충분히 고려할 수 있지만, PVP 게임에서는 서버 권한 모드가 필연적이라고 생각한다.

<br>
<br>

---

<br>

## 정리

![Desktop View](/assets/img/post/unity/netcode028.png){: : width="1000" .normal }    

<br>
<br>

---

<br>

## 프로젝트에 권한 모드를 결정하기에 앞서

- 프로젝트가 어떤 게임의 유형을 지녔는지에 따라 네트워크 통신(Server Authoritative, Owner Authoritative)을 어떻게 처리할지가 달라진다. 



- 마우스 클릭 or 터치를 통해 NavMesh 혹은 A* 패스파인딩을 통해 움직이는 즉 입력과 반응에 있어 인공적인 레이턴시 설정이 가능한 게임 종류, 혹은 FPS MOBA TPS 같이 치터가 빈번히 활동이 가능한 게임의 경우 서버 권한 모드가 좋다고 생각하고



- 움직임에 있어 즉각적인 반응이 필요한 컨트롤이 중요시 되는 게임들은 둘 다 혼합해서 사용하거나 혹은 호스트-클라 위주이며 보안성이 별로 중요하지 않고 게임의 승리유무가 중요하지 않은 게임들의 경우, 마인크래프트, 로블록스, 아웃워드 등은 클라이언트 권한 모드를 사용할 수도 있다.



- 서버 권한 모드에서의 RTT 를 해결하는 패턴, [클라이언트 권한 모드에서 예측 보상등에 대한 팁이나 정보는 관련 문서](https://docs-multiplayer.unity3d.com/netcode/current/learn/dealing-with-latency/)를 참조하면 더 좋은 방향성을 찾을 수 있을 것이다.



