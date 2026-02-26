---
title: Unity Netcode - Networking Components
date: 2024-07-01 10:00:00 +/-TTTT
categories: [Unity, Netcode]
tags: [Unity, Netcode, Dedicated Server, NetworkObject, NetworkManager, NetworkBehaviour, NetworkAnimator, NetworkRigidbody]     # TAG names should always be lowercase
lang: ja
difficulty: intermediate
toc: true
math: true
mermaid: true
---

<br>

## Unity Netcode とは？

<br>

- Unity Netcode for Gameobject を指す（Unity Netcode for ECS も存在する）、Unity が提供するネットワーク開発ライブラリである。

- 高水準の API を提供しており、ゲームオブジェクトの状態同期、リモートプロシージャコール（RPC）、接続管理などを簡単に実装できるという利点がある。

- また、ローレベルでは基本的にネットワーク転送ライブラリである Unity Transport を使用して、データパケットの送信、再送信、順序保証などを処理する。

- 例えば、NetworkBehaviour で ServerRpc を呼び出すと、Unity Transport がこの呼び出しをパケットに変換してサーバーに送信する。

<br>

---

<br>

## Unity Netcode Components の構成要素

<br>

---

<br>

## NetworkManager

<br>

- NetworkManager はネットワークセッションのライフサイクルを管理し、サーバーとクライアント間の接続を確立する。

- 通常、Host-Client、Relay Server、Dedicated Server などを通じて接続が可能である。

<br>

- 動作の仕組み

![Desktop View](/assets/img/post/unity/netcode001.png){: : width="600" .normal }

<br>

- Network Transport を Unity Transport に設定する。

> - Player Prefab にいわゆる「プレイヤーの器」を割り当てよう。（ネットワーク通信専用のキャラクターを指す。NetworkObject、NetworkTransform などのコンポーネントがアタッチされている）
>
> - Network Prefab Lists にはスクリプタブルオブジェクトが割り当てられており、ここで生成したいプレハブをリストに割り当てると Spawn、Despawn が可能になる。（内部的に GC も動作する）
>
> ![Desktop View](/assets/img/post/unity/netcode002.png){: : width="600" .normal }
>
> ```csharp
> spawnedObjectTransform.GetComponent<NetworkObject>().Spawn(true);
> spawnedObjectTransform.GetComponent<NetworkObject>().Despawn();
> ```

<br>

- NetworkManager コンポーネント

![Desktop View](/assets/img/post/unity/netcode003.png){: : width="600" .normal }

<br>

- コンポーネントを追加してシーンに配置すれば完了..

![Desktop View](/assets/img/post/unity/netcode004.png){: : width="600" .normal }

<br>

- 姉妹品である Unity Transport も存在する。スクリプトで IP アドレスとポート番号を変更できる。

```csharp

ut = NetworkManager.Singleton.GetComponent<UnityTransport>();

...

ut.SetConnectionData(ipAddStr, portNumber);

...

// サーバーは EC2 インスタンスを使用しており、仮想環境でデディケイテッドサーバーとして動作するため、グラフィックスデバイスタイプが存在しない。
// そのため、NetworkManager を通じてサーバー・クライアントの実行を区別するコードは以下の通り。
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

- NetworkObject はネットワークを通じて同期・管理されるすべてのゲームオブジェクトの核心である。

- NetworkObject コンポーネント一つと、最低一つの NetworkBehaviour コンポーネントを含む必要がある。それによってのみ、ゲームオブジェクトがネットワークコードに反応して相互作用できるようになる。

![Desktop View](/assets/img/post/unity/netcode005.png){: : width="600" .normal }
![Desktop View](/assets/img/post/unity/netcode006.png){: : width="600" .normal }
_PlayerKitchen プレハブの内部に、器の形式で NetworkObject コンポーネントと NetworkBehaviour を継承した Player コンポーネントがアタッチされた様子。_

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

- また、Netcode 認識属性（ネットワーク同期のためのネットワークオブジェクトのすべての機能 : NetworkVariable など）を複製したり、RPC を送受信するには、ゲームオブジェクトに NetworkObject と NetworkBehaviour がアタッチされている必要がある。

- また NetworkTransform、NetworkAnimator などのコンポーネントも、この NetworkObject が必須となる。

<br>

> **NetworkObject はインスタンス化され、固有の NetworkObjectId が付与される。**
>
> - 最初にクライアントが接続すると、`NetworkObject.GlobalObjectIdHash` の値を識別する。
>
> - ローカルでインスタンス化された後、各 NetworkObject にはネットワーク全体で NetworkObject を紐付けるために使用される `NetworkObjectId` が割り当てられる。
>
> - 例えば、あるピアが「NetworkObjectId 103 を持つオブジェクトにこの RPC を送れ」と言えば、全員がどのオブジェクトを指しているかを把握できる。
>
> - 最後に、NetworkObject はインスタンス化されて固有の NetworkObjectId が割り当てられた時点でクライアントに生成される。
{: .prompt-info }

<br>
<br>

### オーナーシップ (Ownership)

<br>

- サーバーまたは接続された承認済みクライアントが、それぞれの NetworkObject を所有する。

- 基本的に Netcode for GameObjects はサーバー権限方式を採用しており、サーバーのみが NetworkObject を生成または削除できるが、

- クライアントに権限を付与することで NetworkObject の生成・削除が可能になる。

<br>

```csharp
// デフォルトの NetworkObject.Spawn メソッドはサーバー側のオーナーシップを前提とする

GetComponent<NetworkObject>().Spawn();
```


```csharp
// オーナーシップを指定して NetworkObject を生成するには以下を使用

GetComponent<NetworkObject>().SpawnWithOwnership(clientId);
```

```csharp
// オーナーシップを変更するには ChangeOwnership メソッドを使用

GetComponent<NetworkObject>().ChangeOwnership(clientId);
```

```csharp
// オーナーシップをサーバーに戻すには RemoveOwnership メソッドを使用

GetComponent<NetworkObject>().RemoveOwnership();
```

<br>

- ローカルクライアントが NetworkObject のオーナーであるかを確認するには、`NetworkBehaviour.IsOwner` プロパティを確認できる。

- サーバーが NetworkObject を所有しているかを確認するには、`NetworkBehaviour.IsOwnedByServer` / `IsServer` プロパティを確認できる。

<br>

```csharp
// IsOwner、IsServer は NetworkBehaviour を継承することでプロパティとして使用可能。

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

- サーバー側で特定クライアントの PlayerObject インスタンスを取得する必要がある場合は、以下の方法を使用できる。

<br>

```csharp
NetworkManager.Singleton.ConnectedClients[clientId].PlayerObject;
```

<br>
<br>

## NetworkBehaviour

<br>

- NetworkBehaviour は Unity の MonoBehaviour を継承した abstract class であり、NetworkVariable の同期や RPC の送受信を行うには NetworkObject コンポーネントと共に必須でゲームオブジェクトに含まれなければならないコンポーネントである。

<br>

- **Spawning**

- NetworkObject がスポーンされると、NetworkObject に関連する各 NetworkBehaviour で `OnNetworkSpawn` が呼び出される。

- この時点で、すべての Netcode 関連の初期化が行われる必要がある。

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


- 下の表は NetworkBehaviour.OnNetworkSpawn の呼び出しタイミングを表にしたもの。

<br>

| **動的にスポーンされる場合** | **シーンに配置された場合**  |
| ----------------| ------------------- |
| Awake             | Awake                   |
| OnNetworkSpawn            | Start                  |
| Start            | OnNetworkSpawn                   |

<br>

- **Despawning**

- 各 NetworkBehaviour には仮想関数 OnDestroy メソッドをオーバーライドして、NetworkBehaviour が破棄される際の処理を再定義できる。

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

- **NetworkBehaviour の同期**

- NetworkBehaviour を通じて、NetworkObject のスポーン前・スポーン中・スポーン後の設定を同期できる。

<br>

![Desktop View](/assets/img/post/unity/netcode012.png){: : width="1400" .normal }

<br>
<br>

---

<br>

## NetworkTransform

<br>

> **NetworkTransform の同期作業の概要**
>
>   a. 同期する Transform の軸を決定する。
>
>   b. 値をシリアライズする。ここでのシリアライズとは、NetworkVariable の INetworkSerialize と同様の形式と推測される
>
>   c. シリアライズされた値をメッセージとして接続されているすべてのクライアントに送信する。
>
>   d. メッセージを処理し、値をデシリアライズする。
>
>   e. 対応する Transform の軸にデシリアライズした値を適用する。
{: .prompt-tip }

<br>

- **コンポーネント構成**

- 通常、NetworkObject、NetworkBehaviour コンポーネントをアタッチしたヒエラルキー上に一緒にアタッチする。
- NetworkTransform の同期は ***Authoritative Mode（権限モード）*** によって分かれる。

<br>

- **1. NetworkTransform : サーバー権限モード専用**
> - サーバーで移動ロジックを計算し、接続されたクライアントたちに位置情報を同期する。

![Desktop View](/assets/img/post/unity/netcode023.png){: : width="700" .normal }

<br>

- **2. OwnerNetworkTransform : オーナー/クライアント権限モード専用**
> - 補間機能を使用できる。
> - クライアント A で移動ロジックを計算して位置情報をサーバーに送信し、サーバーは接続されたクライアントたちに A の位置情報を同期・中継するだけの役割を担う。

![Desktop View](/assets/img/post/unity/netcode007.png){: : width="700" .normal }

<br>

- どの権限モードを使用するかは慎重に決定する必要がある。**[権限モードの詳細についてはこのドキュメントを確認](https://epheria.github.io/posts/UnityNetCode3/)**することを推奨する。

<br>
<br>

- 次に、上記 NetworkTransform のインスペクター内のプロパティについて見ていこう。

<br>
<br>

- **Syncing**

- 一部の NetworkTransform プロパティは、権限インスタンスによってすべての非権限インスタンスに自動的に同期される。

- ここで重要な点は、同期されたプロパティが変更されると、NetworkTransform が実質的に「テレポート」する（すべての値が同期され、補間がリセットされる）。

<br>

- **Synchronization の最適化**

![Desktop View](/assets/img/post/unity/netcode008.png){: : width="500" .normal }

- 上の画像を見ると、ほとんどの場合、GameObject のすべての Transform 値をネットワーク上で同期する必要はない。

- つまり、GameObject のサイズが変わらないのであれば、Scale などの値を同期しないよう無効化しておくことができる。

- 同期を無効化すると、CPU コストとネットワーク帯域幅を節約できる。→ インスタンスあたりの追加処理オーバーヘッドが削減される。

<br>

- **Thresholds（しきい値）**

- しきい値を使用して最小しきい値を設定できる。これにより、しきい値以上または同等の変更のみを同期することで、同期更新の頻度を削減できる。

- NetworkTransform に補間が有効になっている場合、Position Threshold（位置しきい値）を増加させると、オブジェクトの動きの「滑らかさ」に影響を与えることなく、位置更新の頻度を下げることができる。

- 頻度を下げることで、インスタンスあたりの帯域幅コストを削減できる。

- 位置しきい値を下げるほど頻度が増加する。→ インスタンスあたりの帯域幅コストが増加する

![Desktop View](/assets/img/post/unity/netcode009.png){: : width="600" .normal }

<br>

- **Delivery（配信）**

- ネットワーク状況が悪化するとパケット遅延やパケットロスが発生する可能性がある。→ 主に「カクつき」が発生し、視覚的に動きのギャップが生じる。

- しかし、Netcode の NetworkTransform は Delta（位置、回転、スケール）状態が失われても、BufferedLinearInterpolator を通じて

- すでに失われた次の状態更新を待たず、完全な補間パスを計算して容易に回復できる。

- 例えば、TickRate 30 の場合、1秒間に全状態更新の 5%〜10% が失われても、完全に配信された 30 デルタ更新パスと比較的類似した補間パスを導出できる。

![Desktop View](/assets/img/post/unity/netcode010.png){: : width="400" .normal }

<br>

- Use Unreliable Deltas オプションは、信頼性のないデルタ状態更新を有効にするという意味だ。

    - パケットロスからの回復 : 信頼性のない順序で更新を送信すると、一部のパケットが失われても、全状態更新パスのごく一部のみが失われ、残りは正常に維持される。

    - 遅延の削減 : 信頼性のない送信は、一般的に信頼性のある送信よりも遅延が少ない。信頼性のある送信はパケットロス時に再送信を試みるため、遅延がさらに大きくなる可能性がある。

<br>


- しかし、帯域幅消費が増加する可能性がある。→ 軸フレームの同期、頻繁なパケット送信による帯域幅消費の増加

- 結論 : UseUnreliableDeltas オプションを有効にすると、ネットワークのパケットロスと遅延問題を軽減できるが、若干の追加帯域幅が消費される可能性がある。このオプションを使用する際は、ネットワーク環境と帯域幅の使用量を考慮して最適な設定を選択することが重要だ。もし帯域幅消費が問題になるのであれば、このオプションを無効化してテストで視覚的な不具合がないことを確認した上で無効化した状態を維持することも一つの方法となり得る。

<br>

- **Interpolation（補間）**

![Desktop View](/assets/img/post/unity/netcode011.png){: : width="2000" .normal }

- 補間はデフォルトで有効になっている。遅延が高い場合に補間を適用することで「ジッタリング（Zittering）」を防ぐことができる。

- この他にも、Configuration にはさまざまなオプションが存在するが、Interpolation 以外のオプションは無効化することを推奨する。（Euler → Quaternion を使用すると Quaternion 圧縮のために帯域幅が増加する可能性がある）

- 詳細な説明は公式ドキュメントを参照。

<br>
<br>

### Authority Mode

- **サーバー権限モード（Server Authoritative Mode）**

- 基本的に NetworkTransform はサーバー権限モードで動作する。（NetworkTransform コンポーネントをアタッチした場合）

- これは Transform の軸の変更がサーバー側で検出され、接続されたクライアントにプッシュされることを意味する。

- また、クライアントで発生した Transform の軸の値の変更がすべて権限状態（サーバー側）によって上書きされることを意味する。

- これにより、クライアント側で位置が即座に更新されない場合が発生し、クライアント側の操作が効かなくなる場合が生じる。

<br>


- **オーナー権限モード（Owner Authoritative Mode）→ ClientNetworkTransform**

- 上記の問題を解決するには、オーナー権限モードに更新する必要がある。

- 特定の NetworkObject（通常はプレイヤー）に対して、クライアント側で即座に位置を更新しなければならない場合がある。

- NetworkTransform コンポーネントが最初に初期化される際、**NetworkTransform.OnIsServerAuthoritative** メソッドによってオーナー権限が決定される。

- したがって、オーナー権限モードを有効にするには、上記メソッドの戻り値を ***false*** に変更すればよい。

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

- 上記スクリプトを作成後、プレイヤープレハブに NetworkTransform コンポーネントの代わりに OwnerNetworkTransform コンポーネントをアタッチすればよい。

<br>
<br>

---

<br>

## NetworkRigidbody

<br>

- Netcode for GameObjects では、マルチプレイヤーの物理シミュレーション管理のために基本的に ***サーバー権限ベースの物理（Server-Authoritative physics）*** 方式を提供する。

- この場合、物理シミュレーションは **「サーバー」** でのみ実行される。

- ネットワーク物理を適用するには、NetworkObject コンポーネントを持つプレハブに Rigidbody と一緒に NetworkRigidbody をアタッチする必要がある。

- また、権限モードについては、[サーバー権限モード関連ドキュメント](https://epheria.github.io/posts/UnityNetCode3/)を参照することを推奨する。

<br>
<br>

#### Authoritative Mode をクライアントに設定した場合

- NetworkRigidbody をアタッチすると、サーバー上で接続されたクライアントの Rigidbody の **isKinematic** が有効になってしまう。

- 一方、クライアント上では isKinematic が無効になっている。そのため、クライアントでは物理ベースの移動（Rigidbody.velocity など）が可能であり、Client Network Transform が主体となってクライアント自身の Transform 情報をサーバーに送信し、他の接続されたクライアントと同期する。（これはクライアントに権限が付与されているため、セキュリティ上リスクが高い。）

- しかし物理ベースの移動は可能であったものの、サーバー上では接続されたクライアントの isKinematic が有効になっているため、パーティゲームに必要な基本的なサーバー・クライアント間の Rigidbody 物理シミュレーションが不可能であった。（物理シミュレーションはサーバーでのみ可能なため）

- つまり、ローカルクライアント（自分自身）での Rigidbody 物理シミュレーションは可能だが、他のクライアントまたはサーバーに対する物理シミュレーション（Network Rigidbody）は不可能であった。（他のクライアントへの物理的な干渉ができなかったということ）

<br>

- クライアント権限モードは、ユーザーの入力 → Transform 移動計算をクライアントで処理するため、即座な反応が可能という利点があるが、自分と他のクライアントまたはサーバー間の Rigidbody 物理シミュレーションが不可能なため断念しなければならなかった。

- では物理シミュレーションが不可能かというと、そうではない。物理シミュレーションをサーバーで直接手動で力を追加したりイベントで実装すれば使用可能だが、揺れ（wobble）が発生する可能性が高い。

<br>

- したがって、プロジェクトがどのようなゲームタイプかに応じて、権限モードを適切に選択することを推奨する。

<br>

{% include embed/youtube.html id='10XBoDuyjb4' %}
_クライアント権限モードの物理処理映像_

<br>

![Desktop View](/assets/img/post/unity/netcode029.png){: : width="800" .normal }
_サーバー上で接続されたクライアントの Rigidbody の isKinematic が有効になっている様子_

<br>

#### isKinematic の無効化を試みた内容

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

1. OnNetworkSpawn ネットワークオブジェクトスポーンのタイミングで無効化を試みる → **失敗**
2. OnGainedOwnership 権限付与のタイミングで無効化を試みる → **失敗**

<br>

- isKinematic の有効化問題は、根本的に物理シミュレーションがサーバーに委任されているため、絶対に無効化できないということを学べた..

<br>
<br>

#### Authoritative Mode をサーバーに設定した場合

<br>

{% include embed/youtube.html id='sPZimrgZqB4' %}
_サーバー権限モードの物理処理映像_

<br>
<br>

---

<br>

### NetworkAnimator

<br>

- NetworkTransform が位置を同期するとすれば、NetworkAnimator は**アニメーション状態**をネットワーク全体に同期する役割を担う。マルチプレイヤーゲームで他のプレイヤーのキャラクターが走ったり、攻撃したり、被弾する様子が自然に見えなければならず、そのために Animator のパラメーターと状態遷移を正確に同期する必要がある。

<br>

#### 基本構成

- NetworkObject がアタッチされたゲームオブジェクトに **Animator** と一緒に **NetworkAnimator** コンポーネントをアタッチすることで、基本的なアニメーション同期が動作する。

- NetworkAnimator は Animator コントローラーに定義されたパラメーターを自動的に監視し、値が変更されるとネットワークを通じて伝播する。

<br>

> **NetworkAnimator が自動的に同期する項目：**
>
> - **Animator パラメーター** : Float、Int、Bool 値の変更
> - **Animation State の遷移** : 現在再生中の状態と遷移情報
> - **Trigger パラメーター** : SetTrigger 呼び出し時（ただし、必ず NetworkAnimator を通じて呼び出す必要がある）
{: .prompt-info }

<br>

#### Trigger パラメーターの注意事項

- Trigger は他のパラメーター（Float、Int、Bool）と異なり、**ワンショットイベント（one-shot event）** である。一度発動後、自動的にリセットされるという特性がある。

- ネットワーク環境で Trigger を使用する際に最もよくある間違いは、`Animator.SetTrigger()` を直接呼び出すことだ。こうするとローカルでのみ再生され、他のクライアントには同期されない。**必ず `NetworkAnimator.SetTrigger()` メソッドを使用しなければならない。**

<br>

```csharp
// 正しい方法 - NetworkAnimator を通じて Trigger を呼び出す
NetworkAnimator networkAnimator = GetComponent<NetworkAnimator>();
networkAnimator.SetTrigger("Attack");

// 間違った方法 - ローカルでのみ実行され、他のクライアントに同期されない
Animator animator = GetComponent<Animator>();
animator.SetTrigger("Attack"); // ネットワーク同期がされない！
```

<br>

#### Authority Mode（権限モード）

- NetworkTransform と同様に、NetworkAnimator も基本的に**サーバー権限モード**で動作する。

- サーバー権限モードでは、サーバーで Animator パラメーターを変更すると、接続されたすべてのクライアントに同期される。逆に、クライアントで直接パラメーターを変更してもサーバーの状態で上書きされる。

- クライアント権限モードに変更するには、NetworkTransform と同じパターンで **OnIsServerAuthoritative** をオーバーライドすればよい。

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

- その後、既存の NetworkAnimator コンポーネントを削除し、上記の **OwnerNetworkAnimator** コンポーネントをアタッチすれば、オーナー権限モードでアニメーションが同期される。

<br>

#### 実務での推奨事項

<br>

| 項目 | サーバー権限 | クライアント権限 |
|:---|:---|:---|
| **同期の主体** | サーバーでパラメーターを変更 → クライアントに伝播 | オーナークライアントで変更 → サーバー経由 → 伝播 |
| **反応性** | RTT 分の遅延が発生 | 即座のフィードバックが可能 |
| **推奨シナリオ** | NPC、セキュリティが重要なアクション | プレイヤーキャラクターの移動・攻撃アニメーション |

<br>

- 一般的に、**NetworkTransform と同じ権限モード**を使用することを推奨する。移動がクライアント権限なのにアニメーションがサーバー権限だと、クライアントではキャラクターがすでに走っているのに走りのアニメーションが RTT 分だけ遅れて再生されるという不自然な状況が発生するためだ。

- 一方、NPC やサーバーで制御するオブジェクトは、サーバー権限モードで NetworkTransform と NetworkAnimator を共に設定することで自然な同期が可能となる。

<br>

> **NetworkAnimator を使用しない代替案**
>
> 場合によっては NetworkAnimator を使用せず、NetworkVariable で状態の enum 値のみを同期した後、各クライアントでローカルの Animator を直接制御するパターンも実務でよく使用される。この方式は帯域幅を節約でき、アニメーションのブレンドや遷移タイミングをクライアントでより細かく制御できるという利点がある。ただし、同期ロジックを自分で管理する必要があるため、コードの複雑度が上がるというトレードオフが存在する。
{: .prompt-tip }

<br>

```csharp
// NetworkVariable で状態値のみを同期するパターンの例
public enum PlayerAnimState { Idle, Running, Attacking, Hit }

public NetworkVariable<PlayerAnimState> AnimState = new();

private void Update()
{
    // ローカルで Animator パラメーターを直接設定
    animator.SetBool("IsRunning", AnimState.Value == PlayerAnimState.Running);
    animator.SetBool("IsAttacking", AnimState.Value == PlayerAnimState.Attacking);
    animator.SetBool("IsHit", AnimState.Value == PlayerAnimState.Hit);
}
```

<br>

#### NetworkAnimator の限界と注意点

- NetworkAnimator は**すべてのパラメーター変更をティックごとに監視**するため、パラメーター数が増えるほど帯域幅消費が増加する。複雑な Animator Controller を使用する場合は、この点を必ず念頭に置く必要がある。

- **Animation Event** は NetworkAnimator を通じて同期されない。アニメーションイベントベースのロジック（足音、エフェクトのタイミングなど）は別途 RPC や NetworkVariable を通じて処理する必要がある。

- **レイヤーウェイト（Layer Weight）** の変更は同期されるが、ランタイムで Animator Controller のレイヤーを動的に追加・削除することはサポートされていない。

<br>

> **まとめると**、NetworkAnimator はシンプルなアニメーション同期には非常に便利だが、複雑なアニメーションシステムでは NetworkVariable ベースの状態同期パターンの方がより柔軟で効率的な場合がある。プロジェクトの複雑度と帯域幅の要件に応じて適切な方式を選択しよう。
