---
title: "Unity Netcode - Synchronization Deep Dive: RPCs vs. NetworkVariables"
date: 2024-07-18 10:00:00 +/-TTTT
categories: [Unity, Netcode]
tags: [Unity, Netcode, NetworkVariable, RPC, Legacy, Universal]
lang: en
difficulty: intermediate
toc: true
math: true
mermaid: true
---

<br>

## Network Synchronization

Network synchronization is broadly divided into two methods: **RPC** and **NetworkVariables**.

- **NetworkVariables** are most commonly used to synchronize state with clients who join the game late (Late Join).

- On the other hand, if game logic relies solely on **RPCs**, reliability issues may arise for late-joining clients due to missed data packets.

<br>
<br>

## RPC ([Remote Procedure Calls](https://docs-multiplayer.unity3d.com/netcode/current/advanced-topics/messaging-system/))

<br>

- RPCs are a way to handle direct communication between Server and Client, or Client and `NetworkBehaviour`, in addition to sending messages and event notifications.

- A client can invoke a **Server RPC** on a `NetworkObject`. The RPC is placed in a local queue, sent to the server, and executed on the server's version of the same `NetworkObject`.

- When a client invokes an RPC, the SDK records the object, component, method, and parameters of that RPC and transmits this information over the network.

<br>
<br>

- **How Server RPC works**

<br>

![Desktop View](/assets/img/post/unity/netcode013.png){: : width="2000" .normal }    

<br>
<br>

- **How Client RPC works**

<br>

![Desktop View](/assets/img/post/unity/netcode014.png){: : width="2000" .normal }    

<br>
<br>

#### How to Use RPCs

- Generally, you declare an RPC by adding an attribute to the method you want to call.

- **Important**: The method name must end with `Rpc`, `ServerRpc`, or `ClientRpc`.

<br>

<div class="code-compare">
  <div class="code-compare-pane">
    <div class="code-compare-label label-before">Legacy RPC</div>
    <div class="highlight">
<pre><code class="language-csharp">// Suffix is mandatory in method name
// Separate attributes for ServerRpc / ClientRpc

[ServerRpc]
public void PingServerRpc(int pingCount)
{
    // Executed on Server
}

[ClientRpc]
public void PongClientRpc(
    int pingCount,
    string message)
{
    // Executed on all Clients
}</code></pre>
    </div>
  </div>
  <div class="code-compare-pane">
    <div class="code-compare-label label-after">Universal RPC (Recommended)</div>
    <div class="highlight">
<pre><code class="language-csharp">// Method name only needs 'Rpc' suffix
// Target specified via SendTo (Flexible)

[Rpc(SendTo.Server)]
public void PingRpc(int pingCount)
{
    // Executed on Server
}

[Rpc(SendTo.NotServer)]
void PongRpc(
    int pingCount,
    string message)
{
    // Executed on everyone except Server
}</code></pre>
    </div>
  </div>
</div>

<br>
<br>

#### RPC Attribute Target Table

- There are many targets, but `Server`, `NotServer`, and `Everyone` are the most commonly used.

<br>

![Desktop View](/assets/img/post/unity/netcode015.png){: : width="1360" .normal }    
![Desktop View](/assets/img/post/unity/netcode016.png){: : width="1360" .normal }    

<br>

- Parameters often used with attributes:

![Desktop View](/assets/img/post/unity/netcode017.png){: : width="1000" .normal }    

```csharp
[Rpc(SendTo.Everyone, RequireOwnership = false)]
 
[ServerRpc(RequireOwnership = false)]
```

<br>

- Legacy RPCs might feel more intuitive, but since they are being replaced by Universal RPC attributes, it's better to get used to the Universal form.
- Both are currently usable, so further research on their differences might be needed.

<br>

#### Practical Example 1

![Desktop View](/assets/img/post/unity/netcode018.png){: : width="1000" .normal }    

<br>
<br>

#### Practical Example 2

- Each client executes the client-only method `TryAddIngredient`.
- Then, it calls the ServerRpc `AddIngredientServerRpc`.
- `ServerRpc` runs only on the server, but inside it calls `AddIngredientClientRpc`, which executes on all connected clients to reflect the change.

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

## [NetworkVariables](https://docs-multiplayer.unity3d.com/netcode/current/basics/networkvariable/) Synchronization

- Unlike RPCs, **NetworkVariables** provide continuous synchronization of properties between server and client.

- Unlike RPCs and messages, they are not one-off communications at a specific point in time, meaning they persist for clients connecting later.

<br>

- `NetworkVariable` is a wrapper for a specified value type `T`. To access the synchronized value, you must use the `NetworkVariable.Value` property.

- **Note**: Type `T` must be a Value Type (int, bool, float, FixedString, etc.). Reference types are not allowed.

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

#### How NetworkVariables Synchronize

**1. New Client Joins Game (Late Join)**
- When a `NetworkObject` with `NetworkVariable` properties is spawned on a `NetworkBehaviour`, the current state (`Value`) of the `NetworkVariable` is automatically synchronized to the client.

<br>

**2. Connected Clients**
- When a `NetworkVariable` value changes, all connected clients subscribed to `NetworkVariable.OnValueChanged` are notified before the value is updated locally.
- The `OnValueChanged` callback takes two parameters: `previous` and `current`.

<br>

#### Practical Example 1

- Create a `NetworkVariable` named `state` and register `State_OnValueChanged` to `OnValueChanged`.
- Whenever `state` changes, invoke all subscribers of the `OnStateChanged` event.

<br>

```csharp
// State is an enum type T
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

#### Practical Example 2

- Each client calls a `ServerRpc` when using a Door, toggling the Door's state on the server.
- Once `Door.State.Value` changes, all connected clients sync to the new current value (bool here), and `OnStateChanged` is called on each client.

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

- It is possible to synchronize custom "packet-like" data structures using `NetworkVariable`.
- Custom `NetworkVariable` types must implement serialization, typically via generic types.

<br>

#### NetworkVariable Example

- When declaring a custom `NetworkVariable`, you can specify initialization values as well as `NetworkVariableReadPermission` and `NetworkVariableWritePermission`.
- We used an arbitrary struct `MyCustomData` for serialization.
- This struct must implement the `INetworkSerializable` interface.
- Inside, define the Value types you want to sync.

<br>

```csharp
NetworkSerialize<T>
```

<br>

- Implement serialization of variables using `BufferSerializer` inside this method.

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

- Subscribe to `randomNumber` via `OnValueChanged` with a lambda to log the output.
- Pressing "T" sets a new `MyCustomData` value. Note who has ownership of the `NetworkVariable`.
- In the Door example, `state` was changed via `ServerRpc` (Server-owned). Here, `randomNumber` is Client-owned.
- **Summary**: Roles are divided based on ownership: Server-managed (FSM states, game logic) vs. Client-managed (Player stats).

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

#### NetworkList Example

- `NetworkList` is a List version of `NetworkVariable`.
- Note the addition of the **`IEquatable`** interface. This allows `NetworkVariable` or `NetworkList` structs to perform efficient equality checks.
- It also helps reduce network traffic by detecting if data actually changed.

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
        return clientId == other.clientId &&
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

- Since it's a List type, the event arguments are not `previous` and `current`. Instead, `NetworkListEvent` contains:
- ***Value*** and ***PreviousValue***.

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

- **Use RPC**: For transient events or information transfer. Useful only at the moment the info is received.
- **Use NetworkVariables**: Useful for managing persistent state information. "Persistent state" should be maintained in-game and consistently delivered to all players.

- The quickest way to decide is to ask: **"Does a player joining midway need to receive this information?"**

<br>

![Desktop View](/assets/img/post/unity/netcode019.png){: : width="1000" .normal }    
_NetworkVariable sends the current state, allowing late-joining clients to easily catch up._

<br>

![Desktop View](/assets/img/post/unity/netcode020.png){: : width="1000" .normal }    
_If an RPC is sent to all clients, players joining after the RPC was sent will miss that info and see incorrect visuals._

<br>

- You might think, "Then isn't RPC useless? Can't I just use NetworkVariables for everything?" But...

<br>
<br>

## Why Not Use NetworkVariables for Everything?

- **RPCs are simpler.**
- You don't need to declare a `NetworkVariable` for every transient event in the game (like explosions, object spawning).

<br>

- **RPCs are better for synchronized delivery of multiple values.**
- If you change `NetworkVariables` "a" and "b", there is no guarantee that the client receives both changes in the same frame.

<br>

- Due to latency, clients might receive updates at different times.

<br>

![Desktop View](/assets/img/post/unity/netcode021.png){: : width="1000" .normal }    
_There is no guarantee that different NetworkVariables updated in the same tick are delivered to clients simultaneously._

<br>
<br>

- On the other hand, if sent as two parameters of the same RPC, the client receives both values simultaneously.

<br>

![Desktop View](/assets/img/post/unity/netcode022.png){: : width="1000" .normal }    
_To ensure multiple values sync at the exact same time, you can bundle them into a Client RPC._

<br>
<br>

#### Summary

1. Use **NetworkVariable** for persistent state information.
2. Persistent state means information that must be maintained in the game and consistently delivered to all players.
3. This allows new players to immediately sync to the latest state upon connection, ensuring everyone shares the same state.
