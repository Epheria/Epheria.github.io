---
title: "Unity Netcode - 同期の実践：RPCとNetworkVariableの使い分け"
date: 2024-07-18 10:00:00 +/-TTTT
categories: [Unity, Netcode]
tags: [Unity, Netcode, NetworkVariable, RPC, Legacy, Universal]
lang: ja
difficulty: intermediate
toc: true
math: true
mermaid: true
---

<br>

## ネットワーク同期

ネットワーク同期は、大きく分けて2つの方法があります： **RPC** と **NetworkVariables** です。

- **NetworkVariables** は、ゲーム実行後に遅れて参加する（途中参加）クライアントとの同期を行う際に、最も一般的に使用されます。

- 一方、ゲームロジックを **RPC** だけで処理する場合、データ消失により、遅れて参加したクライアントとの同期の信頼性が低下する可能性が高くなります。

<br>
<br>

## RPC ([Remote Procedure Calls](https://docs-multiplayer.unity3d.com/netcode/current/advanced-topics/messaging-system/))

<br>

- RPCは、メッセージングやイベント通知を送る方法であるだけでなく、サーバーとクライアント間、またはクライアントと `NetworkBehaviour` 間の直接通信を処理する方法です。

- クライアントは `NetworkObject` 上で **Server RPC** を呼び出すことができます。RPCはローカルキューに配置された後、サーバーに送信され、サーバーバージョンの同一 `NetworkObject` 上で実行されます。

- クライアントでRPCを呼び出すと、SDKは該当するRPCのオブジェクト、コンポーネント、メソッド、およびパラメータを記録し、この情報をネットワーク経由で送信します。

<br>
<br>

- **Server RPC の動作原理**

<br>

![Desktop View](/assets/img/post/unity/netcode013.png){: : width="2000" .normal }    

<br>
<br>

- **Client RPC の動作原理**

<br>

![Desktop View](/assets/img/post/unity/netcode014.png){: : width="2000" .normal }    

<br>
<br>

#### RPC の使用方法

- RPCは基本的に、呼び出したいメソッドの上部に属性（Attribute）として宣言します。

- **注意**：メソッド名の末尾には必ず `Rpc`、`ServerRpc`、`ClientRpc` などを付ける必要があります。

<br>

<div class="code-compare">
  <div class="code-compare-pane">
    <div class="code-compare-label label-before">Legacy RPC</div>
    <div class="highlight">
<pre><code class="language-csharp">// メソッド名にサフィックス必須
// ServerRpc / ClientRpc で個別の属性

[ServerRpc]
public void PingServerRpc(int pingCount)
{
    // サーバーで実行
}

[ClientRpc]
public void PongClientRpc(
    int pingCount,
    string message)
{
    // すべてのクライアントで実行
}</code></pre>
    </div>
  </div>
  <div class="code-compare-pane">
    <div class="code-compare-label label-after">Universal RPC (推奨)</div>
    <div class="highlight">
<pre><code class="language-csharp">// メソッド名は Rpc サフィックスのみ
// SendTo で対象を指定（柔軟）

[Rpc(SendTo.Server)]
public void PingRpc(int pingCount)
{
    // サーバーで実行
}

[Rpc(SendTo.NotServer)]
void PongRpc(
    int pingCount,
    string message)
{
    // サーバー以外で実行
}</code></pre>
    </div>
  </div>
</div>

<br>
<br>

#### RPC Attribute Target Table

- ターゲットの種類は多いですが、主に使用するのは `Server`、`NotServer`、`Everyone` 程度です。

<br>

![Desktop View](/assets/img/post/unity/netcode015.png){: : width="1360" .normal }    
![Desktop View](/assets/img/post/unity/netcode016.png){: : width="1360" .normal }    

<br>

- 上記の属性とともに、よく使用されるパラメータもあります。

![Desktop View](/assets/img/post/unity/netcode017.png){: : width="1000" .normal }    

```csharp
[Rpc(SendTo.Everyone, RequireOwnership = false)]
 
[ServerRpc(RequireOwnership = false)]
```

<br>

- Legacy RPCを使用するのが最も簡単で直感的だと思いますが、Universal RPC属性に置き換わりつつあるため、可能であればUniversal形式に慣れておくのが良いでしょう。
- 両方使用可能であるため、違いについてはさらなる研究が必要です。

<br>

#### 実践例 1

![Desktop View](/assets/img/post/unity/netcode018.png){: : width="1000" .normal }    

<br>
<br>

#### 実践例 2

- 各クライアントでクライアント専用メソッド `TryAddIngredient` を実行します。
- その後、ServerRpcである `AddIngredientServerRpc` を呼び出します。
- `ServerRpc` はサーバーでのみ実行されますが、メソッド内部で ClientRpc である `AddIngredientClientRpc` を実行し、接続されているすべてのクライアントに変更を反映させます。

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

## [NetworkVariables](https://docs-multiplayer.unity3d.com/netcode/current/basics/networkvariable/) 同期

- NetworkVariables はRPCとは異なり、サーバーとクライアント間のプロパティなどを**継続的に**同期する方法です。

- RPCやメッセージとは異なり、特定の時点での一回限りの通信ではなく、接続されていないクライアント（後から接続したクライアント）とも共有されます。

<br>

- `NetworkVariable` は指定された値型 `T` のラッパーであり、実際に同期される値にアクセスするには `NetworkVariable.Value` プロパティを使用する必要があります。

- **注意**：型 `T` には値型（int, bool, float, FixedStringなど）のみ指定可能で、参照型は使用できません。

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

#### NetworkVariable は以下のように同期されます

**1. 新しいクライアントがゲームに参加（途中参加）**
- `NetworkBehaviour` に `NetworkVariable` 属性を持つ `NetworkObject` が生成されると、`NetworkVariable` の現在の状態（Value）はクライアント側で自動的に同期されます。

<br>

**2. 接続済みのクライアント**
- `NetworkVariable` の値が変更されると、`NetworkVariable.OnValueChanged` イベントを購読しているすべての接続済みクライアントは、値が変更される前に通知を受け取ります。
- `OnValueChanged` コールバックには、`previous`（変更前）と `current`（変更後）の2つのパラメータがあります。

<br>

#### 実践例 1

- `state` という `NetworkVariable` を生成し、`OnValueChanged` に `State_OnValueChanged` メソッドを登録します。
- その後、`state` の値が変更されるたびに、`OnStateChanged` イベントを購読しているすべてのリスナーを Invoke します。

<br>

```csharp
// T型である State は enum
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

#### 実践例 2

- 各クライアントは Door を使用するたびに `ServerRpc` を呼び出し、サーバー側で Door の状態である `State` をトグルします。
- その後、ラップされた `Door.State.Value` が変更されると、すべての接続済みクライアントは新しい `current value`（ここではbool）に同期され、`OnStateChanged` メソッドが各クライアントで呼び出されます。

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
        // note: ここで `State.Value` は `current` と同じになります
        if (State.Value)
        {
            // ドアが開いた：
            //  - ドアの回転
            //  - アニメーション、サウンド再生など
        }
        else
        {
            // ドアが閉じた：
            //  - ドアの回転
            //  - アニメーション、サウンド再生など
        }
    }
 
    [Rpc(SendTo.Server)]
    public void ToggleServerRpc()
    {
        // これによりネットワーク上でのレプリケーションが発生し、
        // 受信側で `OnValueChanged` が呼び出されます
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

- `NetworkVariable` を使用して、いわゆる「パケット」形式でカスタムデータを同期することも可能です。
- 主にカスタム形式の `NetworkVariable` は、ジェネリック型を使用して直列化（シリアライズ）を行う必要があります。

<br>

#### NetworkVariable の例

- カスタム `NetworkVariable` を宣言する際、値の初期化だけでなく、`NetworkVariableReadPermission`、`NetworkVariableWritePermission` オプションを指定することもできます。
- ここでは `MyCustomData` という任意の struct、つまり **「構造体」** で直列化を行いました。
- 該当する構造体は `INetworkSerializable` インターフェースを継承する必要があります。
- その後、内部的に同期したい Value 型の変数を宣言し、

<br>

```csharp
NetworkSerialize<T>
```

<br>

- メソッド内部で `BufferSerializer` を通じて変数の直列化を行います。

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

- その後、`OnValueChanged` で `randomNumber` の値をラムダ式で購読し、デバッグログに出力します。
- 「T」キーを押して `randomNumber` の値を指定して出力するログですが、ここで注意すべき点は、該当する `NetworkVariable` の所有権を誰に付与するかです。
- 上記の Door の例では `state` 値が `ServerRpc` を通じて変更され、サーバーが主体となる `NetworkVariable` でしたが、この例では `randomNumber` はクライアントが主体となる `NetworkVariable` です。
- 要約すると、`NetworkVariable` の所有権がサーバー管理（各種FSM状態、ゲームロジック変数）か、クライアント管理（プレイヤーステータス）かによって役割が分かれます。

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

#### NetworkList の例

- `NetworkVariable` のリスト形式である `NetworkList` も存在します。
- **`IEquatable`** インターフェースが追加されていることが確認できます。これは `NetworkVariable` または `NetworkList` の構造体型が効率的に同一性比較を行えるようにするためです。
- また、データの変更有無を検知してネットワークトラフィックを削減するのにも役立ちます。

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

- リスト型であるためか、`previous`、`current` の2つのパラメータには分かれず、`NetworkListEvent` 内部的に
- ***Value*** と ***PreviousValue*** の2つの変数が存在します。

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

- **RPCの使用**：一時的なイベントや情報を伝達する際に使用し、その情報が受信された瞬間のみ有用です。
- **NetworkVariablesの使用**：持続的な状態情報を管理するのに有用です。「持続的な状態情報」はゲーム内で維持され続け、すべてのプレイヤーに一貫して伝達されるべきものです。

- どちらを使うべきかの最も早い決定方法は、**「途中でゲームに参加したプレイヤーがその情報を受け取る必要があるか？」**という質問を投げかけることです。

<br>

![Desktop View](/assets/img/post/unity/netcode019.png){: : width="1000" .normal }    
_NetworkVariable は現在の状態を送信するため、遅れて参加したクライアントが容易に最新の状態に追いつくことができます。_

<br>

![Desktop View](/assets/img/post/unity/netcode020.png){: : width="1000" .normal }    
_もしRPCをすべてのクライアントに送信した場合、そのRPCが送信された後に途中でゲームに参加したプレイヤーはその情報を逃し、クライアント上で誤ったビジュアルを見ることになります。_

<br>

- こうなると「じゃあRPCは全く役に立たなくて、NetworkVariablesだけ使えばいいんじゃないの？」と思うかもしれませんが...

<br>
<br>

## すべてに NetworkVariables を使用しない理由

- **RPCの方がシンプルです。**
- ゲーム内のすべての一時的なイベント（爆発、オブジェクト生成など）のために `NetworkVariable` を宣言して使用する必要はありません。

<br>

- **NetworkVariableを使用して2つの変数が同時に受信されるようにしたい場合、RPCの方が適しています。**
- `NetworkVariables` の "a" と "b" を変更しても、クライアント側でその2つの変数が同時に受信されるという保証はありません。

<br>

- 以下の写真を見ると、遅延時間によりクライアントがそれぞれ異なる時間にアップデートを受信していることが確認できます。

<br>

![Desktop View](/assets/img/post/unity/netcode021.png){: : width="1000" .normal }    
_同一ティック内で更新された異なるネットワーク変数が、同時にクライアントに伝達される保証はありません。_

<br>
<br>

- 一方、同一のRPCの2つのパラメータとして送信すれば、クライアント側で2つの変数を同時に受信可能です。

<br>

![Desktop View](/assets/img/post/unity/netcode022.png){: : width="1000" .normal }    
_複数の異なるネットワーク変数がすべて同時に同期されるようにするために、クライアントRPCを使用してこれらの値の変化を一つに結合することができます。_

<br>
<br>

#### まとめ

1. **NetworkVariable** は持続的な状態情報を伝達する際に使用します。
2. 持続的な状態情報とは、ゲーム内で維持され続け、すべてのプレイヤーに一貫して伝達されるべき情報を意味します。
3. これにより、新しいプレイヤーが接続しても最新の状態を即座に同期でき、すべてのプレイヤーが同一の状態情報を共有できます。
