---
title: "Unity Netcode - Networking Components Guide"
date: 2024-07-01 10:00:00 +/-TTTT
categories: [Unity, Netcode]
tags: [Unity, Netcode, Dedicated Server, NetworkObject, NetworkManager, NetworkBehaviour, NetworkAnimator, NetworkRigidbody]
lang: en
difficulty: intermediate
toc: true
math: true
mermaid: true
---

<br>

## What is Unity Netcode?

<br>

- It refers to **Unity Netcode for GameObjects** (there is also Netcode for ECS), which is a networking library provided by Unity.

- It offers a high-level API, allowing easy implementation of game object state synchronization, Remote Procedure Calls (RPCs), and connection management.

- At a low level, it uses **Unity Transport**, a network transport library, to handle data packet transmission, retransmission, and ordering guarantees.

- For example, when you call a `ServerRpc` in a `NetworkBehaviour`, Unity Transport converts this call into a packet and sends it to the server.

<br>

---

<br>

## Unity Netcode Components

<br>

---

<br>

## NetworkManager

<br>

- `NetworkManager` manages the lifecycle of network sessions and establishes connections between the server and clients.

- Connections are typically made via Host-Client, Relay Server, or Dedicated Server.

<br>

- **How it works**

![Desktop View](/assets/img/post/unity/netcode001.png){: : width="600" .normal }    

<br>

- Set the **Network Transport** to **Unity Transport**.

> - Assign a so-called "Player Shell" to the **Player Prefab**. (This refers to a character dedicated to network communication, with components like `NetworkObject` and `NetworkTransform` attached.)
>     
> - A Scriptable Object is assigned to **Network Prefab Lists**. If you assign the prefabs you want to spawn to this list, `Spawn` and `Despawn` become possible. (It also handles internal GC.)
>     
> ![Desktop View](/assets/img/post/unity/netcode002.png){: : width="600" .normal }    
>     
> ```csharp 
> spawnedObjectTransform.GetComponent<NetworkObject>().Spawn(true);
> spawnedObjectTransform.GetComponent<NetworkObject>().Despawn();
> ```

<br>

- **NetworkManager Component**

![Desktop View](/assets/img/post/unity/netcode003.png){: : width="600" .normal }    

<br>

- Just add the component and place it in the scene...

![Desktop View](/assets/img/post/unity/netcode004.png){: : width="600" .normal }    

<br>

- There is also a companion component called **Unity Transport**. You can modify the IP address and port number via script.

```csharp
ut = NetworkManager.Singleton.GetComponent<UnityTransport>();
 
...
 
ut.SetConnectionData(ipAddStr, portNumber);
 
...
 
// Since the server uses an EC2 instance and runs as a dedicated server in a virtual environment,
// it has no graphics device type.
// Therefore, the code to distinguish between server and client execution via NetworkManager is as follows:
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

- `NetworkObject` is the core of all game objects synchronized and managed over the network.

- It must contain one `NetworkObject` component and at least one `NetworkBehaviour` component. Only then can the game object react to and interact with network code.

![Desktop View](/assets/img/post/unity/netcode005.png){: : width="600" .normal }    
![Desktop View](/assets/img/post/unity/netcode006.png){: : width="600" .normal }    
_A PlayerKitchen prefab with a NetworkObject component and a Player component (inheriting from NetworkBehaviour) attached._

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

- Also, to replicate Netcode-aware properties (like `NetworkVariable` for synchronization) or send/receive RPCs, the game object must have `NetworkObject` and `NetworkBehaviour` attached.

- Components like `NetworkTransform` and `NetworkAnimator` also require this `NetworkObject`.

<br>

> **NetworkObject is instantiated and given a unique NetworkObjectId.**
>      
> - When the first client connects, it identifies the `NetworkObject.GlobalObjectIdHash` value.
>     
> - After local instantiation, each `NetworkObject` is assigned a `NetworkObjectId` used to link the object across the network.
>      
> - For example, if one peer says "Send this RPC to the object with NetworkObjectId 103," everyone knows which object is meant.
>      
> - Finally, the `NetworkObject` is created on the client when it is instantiated and assigned a unique `NetworkObjectId`.
{: .prompt-info }

<br>
<br>

### Ownership

<br>

- The server or a connected authorized client owns each `NetworkObject`.

- By default, **Netcode for GameObjects** uses a **Server-Authoritative** approach, where only the server can spawn or destroy `NetworkObject`s.

- However, permissions can be granted to clients to spawn or destroy them.

<br>

```csharp
// The default NetworkObject.Spawn method assumes server-side ownership
GetComponent<NetworkObject>().Spawn();
```

```csharp
// To spawn a NetworkObject with specific ownership, use:
GetComponent<NetworkObject>().SpawnWithOwnership(clientId);
```

```csharp
// To change ownership, use the ChangeOwnership method
GetComponent<NetworkObject>().ChangeOwnership(clientId);
```

```csharp
// To return ownership to the server, use the RemoveOwnership method
GetComponent<NetworkObject>().RemoveOwnership();
```

<br>

- To check if the local client is the owner of a `NetworkObject`, you can check the `NetworkBehaviour.IsOwner` property.

- To check if the server owns the `NetworkObject`, you can check the `NetworkBehaviour.IsOwnedByServer` / `IsServer` properties.

<br>

```csharp
// IsOwner and IsServer are available as properties when inheriting from NetworkBehaviour.
     
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

- If the server needs to retrieve the `PlayerObject` instance of a specific client, you can use the following method:

<br>

```csharp
NetworkManager.Singleton.ConnectedClients[clientId].PlayerObject;
```

<br>
<br>

## NetworkBehaviour

<br>

- `NetworkBehaviour` is an abstract class inheriting from Unity's `MonoBehaviour`. It is a mandatory component alongside `NetworkObject` for `NetworkVariable` synchronization or sending/receiving RPCs.

<br>

- **Spawning**

- When a `NetworkObject` is spawned, `OnNetworkSpawn` is called on each associated `NetworkBehaviour`.

- All Netcode-related initialization should happen at this point.

<br>

```csharp
public class Player : NetworkBehaviour
{ 
    public override void OnNetworkSpawn()
    {
        // Netcode initialization here
    }
}
```

<br>

- The table below shows when `NetworkBehaviour.OnNetworkSpawn` is called.

<br>

| **Dynamically Spawned** | **Placed in Scene** |   
| ----------------------- | ------------------- | 
| Awake                   | Awake               |  
| OnNetworkSpawn          | Start               |  
| Start                   | OnNetworkSpawn      |  

<br>

- **Despawning**

- Each `NetworkBehaviour` has a virtual `OnDestroy` method that can be overridden to handle cleanup when the `NetworkBehaviour` is destroyed.

<br>

```csharp
public override void OnDestroy()
{
    // Clean up your NetworkBehaviour
 
    // Always invoke the base
    base.OnDestroy();
}
```

<br>
<br>

- **NetworkBehaviour Synchronization**

- You can synchronize settings for before, during, and after spawning a `NetworkObject` via `NetworkBehaviour`.

<br>

![Desktop View](/assets/img/post/unity/netcode012.png){: : width="1400" .normal }    

<br>
<br>

---

<br>

## NetworkTransform

<br>

> **Overview of NetworkTransform Synchronization**
>      
>   a. Decide which Transform Axes to synchronize.
>   
>   b. Serialize the values. (Similar to `INetworkSerialize` of `NetworkVariable`)
>   
>   c. Send the serialized values as a message to all connected clients.
>   
>   d. Process the message and deserialize the values.
>   
>   e. Apply the deserialized values to the corresponding Transform Axes.
{: .prompt-tip }

<br>

- **Component Configuration**

- Typically attached to the same hierarchy level as `NetworkObject` and `NetworkBehaviour` components.
- Synchronization of `NetworkTransform` is divided based on the ***Authoritative Mode***.

<br>

- **1. NetworkTransform : Server Authoritative Mode (Default)**
> - The server calculates movement logic and synchronizes position information to connected clients.

![Desktop View](/assets/img/post/unity/netcode023.png){: : width="700" .normal }    

<br>

- **2. OwnerNetworkTransform : Owner/Client Authoritative Mode**
> - Allows use of Interpolation.
> - Client A calculates movement logic and sends position info to the server. The server only acts as a relay to synchronize A's position to other clients.

![Desktop View](/assets/img/post/unity/netcode007.png){: : width="700" .normal }    

<br>

- Deciding which authority mode to use requires careful consideration. **[Check this document for more details on Authority Modes](https://epheria.github.io/posts/UnityNetCode3/)**.

<br>
<br>

- Next, let's look at the properties inside the `NetworkTransform` inspector.

<br>
<br>

- **Syncing**

- Some `NetworkTransform` properties are automatically synchronized from the authoritative instance to all non-authoritative instances.

- **Important**: When a synchronized property changes, the `NetworkTransform` effectively "Teleports" (all values are synced, and interpolation is reset).

<br>

- **Optimization of Synchronization**

![Desktop View](/assets/img/post/unity/netcode008.png){: : width="500" .normal }    

- As shown above, in most cases, not all Transform values of a GameObject need to be synchronized over the network.

- For example, if the GameObject's scale doesn't change, you can disable synchronization for Scale.

- Disabling synchronization saves CPU costs and network bandwidth → removes additional processing overhead per instance.

<br>

- **Thresholds**

- You can set minimum thresholds. This reduces synchronization update frequency by syncing only changes equal to or greater than the threshold.

- If interpolation is enabled on `NetworkTransform`, increasing the Position Threshold can lower the update frequency without affecting the "smoothness" of the object's movement.

- Lowering the frequency reduces bandwidth cost per instance.

- Lowering the threshold increases frequency → bandwidth cost per instance increases.

![Desktop View](/assets/img/post/unity/netcode009.png){: : width="600" .normal }    

<br>

- **Delivery**

- Poor network conditions can cause packet delay or loss → mainly causes "stuttering," creating visual gaps in movement.

- However, Netcode's `NetworkTransform` can easily recover using `BufferedLinearInterpolator` even if Delta (Position, Rotation, Scale) states are lost.

- It calculates the full interpolation path without waiting for the next state update (which might already be lost).

- For example, with a TickRate of 30, even if 5-10% of updates are lost in a second, it can derive an interpolation path relatively similar to a perfectly delivered path.

![Desktop View](/assets/img/post/unity/netcode010.png){: : width="400" .normal }    

<br>

- The **Use Unreliable Deltas** option means enabling unreliable delta state updates.

    - **Packet Loss Recovery**: Sending updates in an unreliable order means that even if some packets are lost, only a small part of the total state update path is lost, and the rest remains normal.

    - **Reduced Latency**: Unreliable transmission generally has lower latency than reliable transmission. Reliable transmission must attempt retransmission upon packet loss, which can increase latency.

<br>

- However, bandwidth consumption may increase due to frequent packet transmission.

- **Conclusion**: Enabling `UseUnreliableDeltas` can mitigate packet loss and latency issues but may consume extra bandwidth. When using this option, it is important to choose optimal settings considering the network environment and bandwidth usage. If bandwidth is an issue, disabling this option and verifying no visual defects exist is a valid strategy.

<br>

- **Interpolation**

![Desktop View](/assets/img/post/unity/netcode011.png){: : width="2000" .normal }    

- Interpolation is enabled by default. Applying interpolation can prevent "Jittering" when latency is high.

- There are various options in Configuration, but it is recommended to disable options other than Interpolation (e.g., using Euler → Quaternion conversion might increase bandwidth due to Quaternion compression).

- Refer to the official documentation for detailed explanations.

<br>
<br>

### Authority Mode

- **Server Authoritative Mode**

- By default, `NetworkTransform` operates in Server Authoritative Mode.

- This means changes to Transform axes are detected on the server side and pushed to connected clients.

- It also means any changes to Transform values on the client side will be overwritten by the authoritative state (server side).

- This can cause issues where position updates are not immediate on the client side, making controls feel unresponsive.

<br>

- **Owner Authoritative Mode → ClientNetworkTransform**

- To solve the above, you need to update to Owner Authoritative Mode.

- There are cases where immediate position updates are required on the client side for a specific `NetworkObject` (typically the player).

- When the `NetworkTransform` component initializes, owner authority is determined by the **`NetworkTransform.OnIsServerAuthoritative`** method.

- Therefore, to enable Owner Authoritative Mode, simply override this method to return ***false***.

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

- After writing this script, replace the `NetworkTransform` component on the player prefab with the `OwnerNetworkTransform` component.

<br>
<br>

---

<br>

## NetworkRigidbody

<br>

- Netcode for GameObjects basically provides ***Server-Authoritative physics*** for multiplayer physics simulation management.

- In this case, physics simulation runs **only on the server**.

- To apply network physics, `NetworkRigidbody` must be attached along with `Rigidbody` on a prefab with a `NetworkObject` component.

- For more on authority modes, refer to the [Server Authoritative Mode document](https://epheria.github.io/posts/UnityNetCode3/).

<br>
<br>

#### When Authority Mode is set to Client

- Attaching `NetworkRigidbody` causes **`isKinematic`** of the connected clients' Rigidbodies to be enabled on the **Server**.

- On the client side, `isKinematic` is disabled. Thus, physics-based movement (like `Rigidbody.velocity`) is possible on the client, and the `ClientNetworkTransform` sends the client's transform info to the server to sync with other clients. (This poses a high security risk as authority is granted to the client.)

- However, while physics-based movement was possible, since `isKinematic` was enabled for clients on the server, basic Rigidbody physics interactions between server and clients (needed for party games) were impossible. (Since physics simulation is only possible on the server.)

- In other words, Rigidbody physics simulation on the local client (self) was possible, but physical simulation against other clients or the server (`NetworkRigidbody`) was not. (Physical interference with other clients was impossible.)

<br>

- **Client Authoritative Mode** has the advantage of immediate response since input → movement calculation is processed on the client, but I had to give it up because Rigidbody physics simulation between self and others was impossible.

- Does this mean physics simulation is impossible? Not necessarily. It is possible if you implement it by manually adding force or using events on the server, but "wobble" is likely to occur.

<br>

- Therefore, it is recommended to choose the authority mode appropriate for the game type of your project.

<br>

{% include embed/youtube.html id='10XBoDuyjb4' %}
_Client Authoritative Mode Physics Processing Video_

<br>

![Desktop View](/assets/img/post/unity/netcode029.png){: : width="800" .normal }    
_Client Rigidbody's isKinematic enabled on the Server_

<br>

#### Attempts to Disable isKinematic

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

1. Attempted to disable in `OnNetworkSpawn` → **Failed**
2. Attempted to disable in `OnGainedOwnership` → **Failed**

<br>

- I learned that disabling `isKinematic` is fundamentally impossible because physics simulation is delegated to the server.

<br>
<br>

#### When Authority Mode is set to Server

<br>

{% include embed/youtube.html id='sPZimrgZqB4' %}
_Server Authoritative Mode Physics Processing Video_

<br>
<br>

---

<br>

### NetworkAnimator

<br>

- If `NetworkTransform` synchronizes position, `NetworkAnimator` synchronizes **animation states** across the network. In a multiplayer game, other players' characters must run, attack, or get hit naturally, requiring precise synchronization of Animator parameters and state transitions.

<br>

#### Basic Setup

- Attaching a **NetworkAnimator** component alongside an **Animator** to a GameObject with a `NetworkObject` enables basic animation synchronization.

- `NetworkAnimator` automatically monitors parameters defined in the Animator Controller and propagates changes over the network.

<br>

> **What NetworkAnimator Automatically Synchronizes:**
>
> - **Animator Parameters**: Changes in Float, Int, Bool values.
> - **Animation State Transitions**: Current playing state and transition info.
> - **Trigger Parameters**: When `SetTrigger` is called (Must be called via `NetworkAnimator`).
{: .prompt-info }

<br>

#### Trigger Parameter Caution

- Unlike other parameters (Float, Int, Bool), a Trigger is a **one-shot event**. It automatically resets after being triggered.

- A common mistake when using Triggers in a network environment is calling `Animator.SetTrigger()` directly. This only plays locally and does not sync to other clients. **You must use the `NetworkAnimator.SetTrigger()` method.**

<br>

```csharp
// Correct - Call Trigger via NetworkAnimator
NetworkAnimator networkAnimator = GetComponent<NetworkAnimator>();
networkAnimator.SetTrigger("Attack");

// Incorrect - Only runs locally, no network sync
Animator animator = GetComponent<Animator>();
animator.SetTrigger("Attack"); // No Sync!
```

<br>

#### Authority Mode

- Like `NetworkTransform`, `NetworkAnimator` operates in **Server Authoritative Mode** by default.

- In Server Authoritative Mode, if the server changes Animator parameters, they sync to all connected clients. Conversely, if a client changes parameters directly, they are overwritten by the server's state.

- To switch to **Client Authoritative Mode**, override `OnIsServerAuthoritative` just like with `NetworkTransform`.

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

- Remove the existing `NetworkAnimator` component and attach the above `OwnerNetworkAnimator` component to sync animations in Owner Authoritative Mode.

<br>

#### Practical Recommendations

<br>

| Item | Server Auth | Client Auth |
|:---|:---|:---|
| **Sync Source** | Server changes params → Propagates to clients | Owner client changes → Server relays → Propagates |
| **Responsiveness** | Delayed by RTT | Immediate feedback possible |
| **Recommended For** | NPCs, security-critical actions | Player character movement/attack animations |

<br>

- Generally, it is recommended to use the **same Authority Mode as NetworkTransform**. If movement is client-authoritative but animation is server-authoritative, the character might move on the client, but the run animation plays later by RTT, causing awkwardness.

- Conversely, NPCs or server-controlled objects can achieve natural synchronization by setting both `NetworkTransform` and `NetworkAnimator` to Server Authoritative Mode.

<br>

> **Alternative: Not Using NetworkAnimator**
>
> In some cases, instead of `NetworkAnimator`, a pattern of syncing only state enum values via `NetworkVariable` and controlling the local Animator on each client is used. This saves bandwidth and allows finer control over animation blending or transition timing on the client. However, it comes with the trade-off of increased code complexity as you manage sync logic yourself.
{: .prompt-tip }

<br>

```csharp
// Example: Syncing only state values via NetworkVariable
public enum PlayerAnimState { Idle, Running, Attacking, Hit }

public NetworkVariable<PlayerAnimState> AnimState = new();

private void Update()
{
    // Set Animator parameters locally
    animator.SetBool("IsRunning", AnimState.Value == PlayerAnimState.Running);
    animator.SetBool("IsAttacking", AnimState.Value == PlayerAnimState.Attacking);
    animator.SetBool("IsHit", AnimState.Value == PlayerAnimState.Hit);
}
```

<br>

#### Limitations and Cautions of NetworkAnimator

- `NetworkAnimator` **monitors all parameter changes every tick**, so bandwidth consumption increases with the number of parameters. Keep this in mind when using complex Animator Controllers.

- **Animation Events** are not synchronized via `NetworkAnimator`. Logic based on animation events (footsteps, effect timing) must be handled separately via RPCs or `NetworkVariable`s.

- **Layer Weight** changes are synced, but dynamically adding/removing layers in the Animator Controller at runtime is not supported.

<br>

> **Summary**: `NetworkAnimator` is convenient for simple animation sync, but for complex systems, `NetworkVariable`-based state sync patterns might be more flexible and efficient. Choose the appropriate method based on project complexity and bandwidth requirements.
