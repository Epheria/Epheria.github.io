---
title: "Tailscale シリーズ 第1回 — 押し入れのノートPCで作る韓国IP経由インフラ（動機・実測・構造）"
lang: ja
date: 2026-05-07 18:00:00 +0900
categories: [ETC, Tailscale]
tags: [tailscale, network, vpn, wireguard, mesh-vpn, p2p, exit-node, infrastructure]
toc: true
toc_sticky: true
difficulty: beginner
chart: true
tldr:
  - 福岡で1年以上暮らす中で積み重なった韓国IPの必要性を、押し入れのノートPC + Tailscale Personal Free で解決
  - 3ノードメッシュ（釜山 Win + 福岡 Mac + 福岡 Win）が稼働中 — P2P direct 50ms / Tunnel DOWN 24.9 Mbps / 無人で15時間以上の安定動作
  - Tailscale はメッシュVPN — データプレーン（WireGuard、E2E）+ コントロールプレーン（coordination）を分離。トラフィックは会社インフラを経由しない
  - 会社は2019年トロントで創業、Google 出身の4人（Brad Fitzpatrick を含む）、累計調達額 $272M。Personal プランは 6 user / デバイス無制限で無料
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

## このシリーズで扱うこと

福岡で1年以上暮らしてきた中で、韓国IPが必要になる場面が地味に積み重なってきました。韓国の決済・銀行・一部のコンテンツは海外IPからは正常に動作しなかったり追加認証を要求してきたりして、そのたびに商用の韓国向けVPNを一時的にONにするやり方は、コスト・信頼性・OS互換性のどれを取ってもすっきりしませんでした。

解決策として、釜山の実家の押し入れに7年眠っていた古いノートPC（Samsung Galaxy Book 950SBE、**Intel Core i7-8565U / 16GB / Windows 11 Home**）を引っ張り出してきて無人 exit node として復活させ、福岡側の Mac から SSH でリモート運用する個人 Tailscale インフラをセットアップしました。数日間の検証の結果、**Tunnel DOWN 24.9 Mbps · P2P direct 50ms RTT · 無人で15時間以上の安定動作** — 新しいハードウェアを購入することなく、韓国IP経由とリモート運用が十分に成り立つことがデータで確認できました。

このシリーズではその全工程を3編に分けて整理します。

| # | タイトル | 扱う内容 |
|---|---|---|
| **第1回（本記事）** | 動機・実測・構造 | 稼働中インフラの実測値 + Tailscale・メッシュVPN・WireGuard の構造 |
| 第2回 | 実家セットアップ + 無人運用 + セキュリティ | 1回の訪問で済ませるセットアップ / 自己修復 SchTasks / セキュリティ監査 |
| 第3回 | 動作原理 + コスト・限界 | DERP・MagicDNS・hole punching / 年1,100円のコスト振り返り |

この第1回は **すでに稼働しているインフラの実測値を先に提示し**、それが可能となる構造的な根拠を解いていく流れです。

> ### ちょっと待って、これだけ確認しておこう
>
> **「exit node? tailnet? peer? 始める前から用語が多すぎない？」**
>
> 本文に頻出する核となる4つだけ短くまとめてから入ります。
>
> - **Tailnet** — 一人のユーザー（または組織）に紐づく Tailscale ノード群の **プライベート仮想ネットワーク**。本シナリオでは釜山ノートPC + 福岡 Mac + 福岡 Windows デスクトップの3ノードが1つの tailnet に入っています。
> - **Peer（ピア）** — tailnet 内の1ノード。**クライアント／サーバーの区別がなく**、すべてが対等な立場で互いに直接通信できるメンバー、という意味です。P2P（peer-to-peer）の peer です。
> - **Mesh（メッシュ）** — ピア同士が中央ハブを経由せず **互いに直接接続される** 網構造。後ほど hub-and-spoke と比較しながら詳しく扱います。
> - **Exit node** — tailnet 内の1ノードを「このノード経由でインターネットに出ていく」と指定する機能。福岡 Mac が釜山ノートPCを exit node に指定すると、**Mac のインターネットトラフィックがすべて釜山ノートPCを経由して韓国IPで出ていきます**。このシリーズが作る中核ツールがこれです。

---

## システムを一目で — 現在稼働中

Tailscale 管理コンソールに表示されているノードの状態です。Personal Free プラン、2ノードは常時 Connected、釜山ノートPCは Exit Node として広告中。

![Tailscale admin console — 釜山実家のノートPCが Exit Node として稼働、福岡 Mac が接続中](/assets/img/post/ETC/Tailscale/admin-console-machines.png)
_管理コンソールの1画面に Win 11（釜山）と macOS 26（福岡）が同じ tailnet にまとめられています。**OSを問わないメッシュ** が Tailscale の強みの1つです。_

主要な数値をカード4枚で要約します（2026-05-04 ～ 05-05、30時間連続測定基準）。

<div class="metric-cards" style="margin:1.5rem 0">
  <div class="mc-grid">
    <div class="mc-card mc-blue">
      <div class="mc-label">Uptime（無人）</div>
      <div class="mc-value">15h+</div>
      <div class="mc-sub">自己修復トリガー 0件</div>
    </div>
    <div class="mc-card mc-green">
      <div class="mc-label">Wi-Fi 信号</div>
      <div class="mc-value">99%</div>
      <div class="mc-sub">365 サンプルすべて 99% 固定</div>
    </div>
    <div class="mc-card mc-purple">
      <div class="mc-label">DERP RTT (Tokyo)</div>
      <div class="mc-value">28ms</div>
      <div class="mc-sub">P2P direct（DERP 非経由）</div>
    </div>
    <div class="mc-card mc-orange">
      <div class="mc-label">Tunnel DOWN</div>
      <div class="mc-value">24.9 Mbps</div>
      <div class="mc-sub">1080p 5x · 4K 近接</div>
    </div>
  </div>
</div>
<style>
.metric-cards .mc-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:.75rem}
.metric-cards .mc-card{border-radius:12px;padding:1rem .9rem;color:#fff;text-align:center;box-shadow:0 2px 10px rgba(0,0,0,.1)}
.metric-cards .mc-blue{background:linear-gradient(135deg,#1976d2,#1565c0)}
.metric-cards .mc-green{background:linear-gradient(135deg,#388e3c,#2e7d32)}
.metric-cards .mc-purple{background:linear-gradient(135deg,#7b1fa2,#6a1b9a)}
.metric-cards .mc-orange{background:linear-gradient(135deg,#ef6c00,#e65100)}
.metric-cards .mc-label{font-size:11.5px;font-weight:700;letter-spacing:.04em;opacity:.92;text-transform:uppercase}
.metric-cards .mc-value{font-size:28px;font-weight:800;margin:.45rem 0;font-family:'SF Mono',Consolas,monospace;letter-spacing:-.01em}
.metric-cards .mc-sub{font-size:11.5px;opacity:.92;line-height:1.45}
@media(max-width:768px){.metric-cards .mc-grid{grid-template-columns:1fr 1fr}}
</style>

---

## 3ノードメッシュのトポロジー

Tailnet には現在3つのノードが束ねられています。釜山の exit node 1台、福岡側のクライアント2台（Mac + Windows）です。ノード同士は P2P direct で接続され、直通が成立しない場合のみ Tokyo DERP にフォールバックします（最も近い東アジアリージョン）。

<div class="mesh-topo" style="margin:1.5rem 0">
  <div class="mt-grid">
    <div class="mt-side">
      <div class="mt-tag">韓国 (Exit Node)</div>
      <div class="mt-node mt-busan">
        <div class="mt-name">samsung-home-laptop</div>
        <div class="mt-os">Windows 11 Home</div>
        <div class="mt-spec">i7-8565U · 16GB</div>
        <div class="mt-loc">釜山実家 · KT GiGA 5G</div>
      </div>
    </div>
    <div class="mt-center">
      <div class="mt-cloud">
        <div class="mt-cloud-title">tailnet</div>
        <div class="mt-cloud-sub">P2P direct<br>Tokyo DERP fallback</div>
      </div>
    </div>
    <div class="mt-side">
      <div class="mt-tag">日本 (クライアント)</div>
      <div class="mt-node mt-japan">
        <div class="mt-name">jp1461npcl</div>
        <div class="mt-os">macOS 26.1</div>
        <div class="mt-spec">メインノートPC</div>
        <div class="mt-loc">福岡自宅</div>
      </div>
      <div class="mt-node mt-japan">
        <div class="mt-name">fukuoka-home-pc</div>
        <div class="mt-os">Windows 11</div>
        <div class="mt-spec">デスクトップ</div>
        <div class="mt-loc">福岡自宅</div>
      </div>
    </div>
  </div>
</div>
<style>
.mesh-topo .mt-grid{display:grid;grid-template-columns:1fr auto 1fr;gap:1rem;align-items:center}
.mesh-topo .mt-side{display:flex;flex-direction:column;gap:.6rem}
.mesh-topo .mt-tag{font-size:11px;font-weight:700;color:var(--text-muted-color,#666);text-align:center;letter-spacing:.06em;text-transform:uppercase}
.mesh-topo .mt-node{border-radius:10px;padding:.85rem 1rem;color:#fff;box-shadow:0 1px 4px rgba(0,0,0,.08)}
.mesh-topo .mt-busan{background:linear-gradient(135deg,#c62828,#b71c1c)}
.mesh-topo .mt-japan{background:linear-gradient(135deg,#1565c0,#0d47a1)}
.mesh-topo .mt-name{font-family:'SF Mono',Consolas,monospace;font-size:13.5px;font-weight:700;margin-bottom:.3rem}
.mesh-topo .mt-os{font-size:12px;opacity:.95;margin-bottom:.15rem}
.mesh-topo .mt-spec{font-size:11.5px;opacity:.85;margin-bottom:.15rem}
.mesh-topo .mt-loc{font-size:11.5px;opacity:.8}
.mesh-topo .mt-center{display:flex;justify-content:center}
.mesh-topo .mt-cloud{background:linear-gradient(135deg,#37474f,#263238);color:#fff;border-radius:50%;width:130px;height:130px;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:.5rem;box-shadow:0 2px 12px rgba(0,0,0,.15)}
.mesh-topo .mt-cloud-title{font-size:14px;font-weight:800;letter-spacing:.04em}
.mesh-topo .mt-cloud-sub{font-size:10.5px;line-height:1.4;opacity:.85;margin-top:.3rem}
@media(max-width:768px){.mesh-topo .mt-grid{grid-template-columns:1fr;gap:.6rem}.mesh-topo .mt-cloud{width:110px;height:110px}}
</style>

| ノード | 役割 | OS | 場所 | 接続モード |
|---|---|---|---|---|
| samsung-home-laptop | Exit Node（韓国IP出口） | Windows 11 Home | 釜山実家 | direct |
| jp1461npcl | メインクライアント | macOS 26.1 | 福岡自宅 | direct |
| fukuoka-home-pc | 追加クライアント | Windows 11 | 福岡自宅 | direct |

3ノードすべてが **direct P2P** — DERP 中継なしで直接通信しています。家庭用 NAT 二重越しでも直通が成立する仕組みは hole punching と呼ばれ、本シリーズ第3回で詳しく扱います。

> ### ちょっと待って、これだけ確認しておこう
>
> **「表の最後の列の『direct』は何のこと？ そして IP が 100.64.x.x なのはどういう意味？」**
>
> 2点を一度に押さえます。
>
> **(1) 通信経路 — direct vs DERP**
>
> - **P2P direct** — 2ノードがインターネット上でお互いのグローバルIP・ポートに **直接** UDPパケットを送り合っている状態。最速で、**Tailscale 社のインフラをトラフィックが経由しません**。
> - **DERP relay** — 直通が成立しない場合に Tailscale の公開中継サーバー（Designated Encrypted Relay for Packets）を経由するフォールバック。DERPは **暗号化されたパケットをそのまま転送するだけで復号しません**。
>
> **(2) Tailscale IP — `100.64.0.0/10`**
>
> Tailscale がノードに付与するプライベートIPは `100.64.x.x` の形をしています。この帯域はもともとISPの CGNAT（Carrier-Grade NAT）用途で予約された空間ですが、Tailscale はこの帯域を **そのまま借りて自分の仮想ネットワークのアドレスに使っています**。インターネットから直接到達できないプライベート帯域なので、他のインターネットトラフィックと衝突しません。

---

## 実測データ

### DERP latency — 釜山ノートPCを起点とした28リージョン

`tailscale netcheck` が測定した28リージョンの DERP サーバーまでの RTT です。東京が28msと圧倒的に近く、東アジア4リージョンがすべて100ms以内です。

<div class="chart-wrapper">
  <div class="chart-title">DERP latency (ms、釜山ノートPC → 各リージョン)</div>
  <canvas id="derpLatency" class="chart-canvas" height="380"></canvas>
</div>
<script>
window.chartConfigs = window.chartConfigs || [];
window.chartConfigs.push({
  id: 'derpLatency',
  type: 'bar',
  data: {
    labels: ['Tokyo','Hong Kong','Singapore','Bengaluru','San Francisco','Seattle','Los Angeles','Denver','Chicago','Dallas','Toronto','New York','Honolulu','Miami','Ashburn','Sydney','London','Paris','Frankfurt','Amsterdam','Madrid','Warsaw','Nuremberg','Helsinki','Dubai','São Paulo','Nairobi','Johannesburg'],
    datasets: [{
      label: 'RTT (ms)',
      data: [29,61.3,73.9,99.7,126.7,129.5,132.2,139.7,158.3,161.4,164.5,173.4,175.7,189.6,189.7,198.8,238.3,254.5,256.2,260.6,262.8,274.2,277.6,294,344.8,352,385.4,389.4],
      backgroundColor: function(ctx){
        var v = ctx.parsed && ctx.parsed.x !== undefined ? ctx.parsed.x : 0;
        if (v < 60)  return 'rgba(76,175,80,0.85)';
        if (v < 150) return 'rgba(255,193,7,0.8)';
        if (v < 250) return 'rgba(255,152,0,0.75)';
        return 'rgba(244,67,54,0.7)';
      },
      borderWidth: 0,
      borderRadius: 4
    }]
  },
  options: {
    indexAxis: 'y',
    scales: {
      x: {beginAtZero:true,title:{display:true,text:'RTT (ms)'},grid:{color:'rgba(128,128,128,0.12)'}},
      y: {grid:{display:false},ticks:{font:{size:11}}}
    },
    plugins: {
      legend: {display:false},
      tooltip: {callbacks:{label:function(ctx){return ctx.parsed.x + ' ms'}}}
    },
    responsive: true,
    maintainAspectRatio: false
  }
});
</script>

東京28msが意味するもの。hole punching が失敗してDERP中継に落ちても、釜山↔福岡のRTTは無料の公開中継網の上でも依然として同一大陸圏のベストケースに近い水準を保てる、ということです。**無料で提供されるグローバルDERPインフラ** がコストモデルの大きな柱であることを、ここで先に押さえておきます。

### 帯域幅 — Tunnel UP/DOWN vs インターネットバックボーン

50MBファイルでの双方向 scp 測定結果と、インターネットバックボーンを並べて比較します。**Tunnel DOWN が24.9 Mbpsで全体のボトルネック** — 釜山側の家庭回線のアップロード側の上限がそのまま現れています。

<div class="chart-wrapper">
  <div class="chart-title">帯域幅比較 (Mbps、50MBファイル基準)</div>
  <canvas id="bandwidthCompare" class="chart-canvas" height="280"></canvas>
</div>
<script>
window.chartConfigs = window.chartConfigs || [];
window.chartConfigs.push({
  id: 'bandwidthCompare',
  type: 'bar',
  data: {
    labels: ['Cloudflare 백본\n(부산 측 인터넷 egress)', 'Tunnel UP\n(후쿠오카 → 부산)', 'Tunnel DOWN\n(부산 → 후쿠오카, 병목)', '4K 스트리밍\n(참고)', '1080p 스트리밍\n(참고)'],
    datasets: [{
      label: 'Mbps',
      data: [245.2, 59.2, 24.9, 25, 5],
      backgroundColor: ['rgba(76,175,80,0.8)','rgba(33,150,243,0.8)','rgba(244,67,54,0.85)','rgba(120,120,120,0.5)','rgba(120,120,120,0.5)'],
      borderColor: ['rgb(76,175,80)','rgb(33,150,243)','rgb(244,67,54)','rgb(120,120,120)','rgb(120,120,120)'],
      borderWidth: 2,
      borderRadius: 6
    }]
  },
  options: {
    scales: {
      y: {beginAtZero:true,title:{display:true,text:'Mbps'},grid:{color:'rgba(128,128,128,0.12)'}},
      x: {grid:{display:false},ticks:{font:{size:11},autoSkip:false}}
    },
    plugins: {
      legend: {display:false},
      tooltip: {callbacks:{label:function(ctx){return ctx.parsed.y + ' Mbps'}}}
    },
    responsive: true,
    maintainAspectRatio: true
  }
});
</script>

解釈：
- インターネットバックボーンは245 Mbpsなのに **Tunnel UP は59.2 Mbps** — WireGuard の暗号化 + Wi-Fi チャネル + オーバーヘッドが累積した結果です。i7-8565U（15W TDP）のWireGuard上限が ~100~200 Mbps 程度という一般的なベンチマークと整合します。
- **Tunnel DOWN 24.9 Mbps** は釜山側の家庭用FTTH回線のアップロード側の非対称制限 — 韓国の家庭インターネットの典型的なダウン ≫ アップ構造そのものです。
- 1080p 動画ストリーミングの平均5 Mbps基準で **5倍の余裕**、4K（~25 Mbps）は上限近接でマージンなし。

### 安定性 — 30時間連続のメトリクス368サンプル

5分周期で自動収集されたメトリクスの7日間統計です。主要指標すべてが標準偏差ほぼ0の安定状態。

| 項目 | 平均 | min | p50 | p95 | max | サンプル |
|---|---|---|---|---|---|---|
| Battery（AC接続） | 84.8% | 84 | 85 | 85 | 85 | 368 |
| Wi-Fi signal | 99.0% | 99 | 99 | 99 | 99 | 365 |
| RTT 8.8.8.8 | 29.3ms | 28 | 29 | 30 | 90 | 368 |
| RTT 1.1.1.1 | 9.2ms | 8 | 9 | 10 | 25 | 368 |

自己修復システムの作動記録：

<div class="health-cards" style="margin:1.5rem 0">
  <div class="hc-grid">
    <div class="hc-card hc-good">
      <div class="hc-num">0</div>
      <div class="hc-label">Tailscale 再起動</div>
      <div class="hc-sub">5分ヘルスチェックがトリガーした回数</div>
    </div>
    <div class="hc-card hc-good">
      <div class="hc-num">0</div>
      <div class="hc-label">sshd 再起動</div>
      <div class="hc-sub">同様 — 落ちたことなし</div>
    </div>
    <div class="hc-card hc-good">
      <div class="hc-num">0</div>
      <div class="hc-label">SSH 認証失敗</div>
      <div class="hc-sub">直近24時間 brute force 0件</div>
    </div>
    <div class="hc-card hc-good">
      <div class="hc-num">5/5</div>
      <div class="hc-label">SchTasks Ready</div>
      <div class="hc-sub">自己修復ジョブ5種すべて正常</div>
    </div>
  </div>
</div>
<style>
.health-cards .hc-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:.75rem}
.health-cards .hc-card{border-radius:12px;padding:1rem .9rem;text-align:center;box-shadow:0 2px 8px rgba(0,0,0,.06)}
.health-cards .hc-good{background:linear-gradient(135deg,#e8f5e9,#c8e6c9);color:#1b5e20}
.health-cards .hc-num{font-size:32px;font-weight:800;font-family:'SF Mono',Consolas,monospace;letter-spacing:-.02em;line-height:1}
.health-cards .hc-label{font-size:12.5px;font-weight:700;margin:.5rem 0 .2rem}
.health-cards .hc-sub{font-size:11px;opacity:.85;line-height:1.4}
[data-mode="dark"] .health-cards .hc-good{background:linear-gradient(135deg,#1a3320,#263e2a);color:#a5d6a7}
@media(max-width:768px){.health-cards .hc-grid{grid-template-columns:1fr 1fr}}
</style>

### 再起動の自動復旧 — 安定区間で平均1分30秒

リモート運用のセーフティネットとして最も重要なシナリオは「再起動後に人手を介さずSSHが復活するか」です。クラムシェルモード（蓋を閉じた状態）を含む4回の再起動検証結果：

| 回 | ブート完了 | SSH 復旧 | ヘルスチェック初回実行 | 備考 |
|---|---|---|---|---|
| 1回目 | n/a | ~5分 | 再起動 +19s | 初回試行（コールドスタート） |
| 2回目 | +29s | ~1分34秒 | n/a | |
| 3回目 | +29s | ~1分 | +48s | |
| **4回目（蓋を閉じた状態）** | +28s | n/a | +80s | **クラムシェル検証** |

1回目はDNS・サービス初期化などコールドスタートのコストが累積して~5分、**2回目以降の安定区間の平均は1分30秒** です。クラムシェル検証の決定的な証拠は `WmiMonitorBasicDisplayParams Count = 0`（アクティブなモニタが0個）の状態ですべてのサービスが正常起動した、という点です。つまり実家の家族がノートPCの蓋を閉じておいてもインフラはそのまま動作するということです。

ここまでがインフラ稼働の証明です。以下からはこの結果を成り立たせる構造的な根拠に移ります。

---

## Tailscale を作っているのは誰か

まずは会社そのものを押さえておきます。Tailscale は **2019年カナダのトロントで創業** された会社で、創業者4人は全員Google出身のエンジニアです（Wikipedia 基準）。

| 創業者 | 備考 |
|---|---|
| Avery Pennarun | CEO。ブログ記事 "How NAT traversal works" は NAT 入門資料の事実上の標準 |
| David Crawshaw | システム・言語領域、Goエコシステムに近いキャリア |
| David Carney | Chief Strategy Officer |
| Brad Fitzpatrick | **LiveJournal・memcached・Perlbal** の創始者、その後Googleで Go 言語コアチームに長年在籍 |

特に Brad Fitzpatrick の合流は重みがあります。Wikipediaによると、彼は **大学1年生のときに LiveJournal を始め** 2005年1月に Six Apart に売却、その後 **2007年8月から Google Go コアチームの Staff Software Engineer として12年半勤務** し、**2020年1月の退職から3日後に Tailscale に "late-stage co-founder" として合流** しました — つまり元々の3人（Avery／Crawshaw／Carney）が2019年に創業した会社に4人目のメンバーとして遅れて合流した形です。memcached・OpenID・Perkeep などインターネットインフラ系の共通技術を自ら作った人物が、12年半 Go チームに在籍した直後にここへ移ってきたというタイムラインは、単なる新興スタートアップとは違う信頼の側面を作ります。

ファンディングも軽くはありません（Wikipedia）。

| ラウンド | 時期 | 金額 | リード |
|---|---|---|---|
| Series A | 2020-11 | $12M | Accel |
| Series B | 2022-05 | $100M | CRV, Insight Partners |
| Series C | 2025-04 | $160M | Accel |

総額 $272M の資本が入った会社が、本シリーズで「0円インフラ」として活用する Personal プランを提供している、という点はそれ自体が興味深い非対称です。その非対称の構造的な根拠を以下で解いていきます。

---

## 従来型VPNは hub-and-spoke

会社のVPNを思い浮かべてみてください。ノートPC → クライアントアプリ → 会社ゲートウェイ → 社内ネットワーク。すべてのトラフィックはゲートウェイという中央ハブを必ず1度経由します。社員2人がお互いのノートPCに接続する場合でも、トラフィックはいったんゲートウェイに上がってから降りてきます。

> ### ちょっと待って、これだけ確認しておこう
>
> **「VPN とゲートウェイって正確には何？」**
>
> - **VPN (Virtual Private Network)** — インターネットの上に敷かれた **仮想のプライベートネットワーク**。外部からは見えないプライベートIP帯域を持ち、その中のノード同士があたかも同じLAN上にいるように通信できるようにします。パケットは通常 **暗号化トンネル内にカプセル化されて** 流れます。
> - **ゲートウェイ (Gateway)** — あるネットワークと別のネットワークの間で **パケットを受けて流す関門ノード**。家庭用ルーターも家庭LAN ↔ インターネットのゲートウェイですし、会社のVPNサーバーも社内ネットワーク ↔ インターネットのゲートウェイです。

<div class="hub-spoke" style="margin:1.5rem 0">
  <div class="hs-grid">
    <div class="hs-panel hs-hub">
      <div class="hs-title">Hub-and-Spoke (従来型VPN)</div>
      <div class="hs-diagram">
        <div class="hs-center hs-server">VPN<br>Gateway</div>
        <div class="hs-node hs-n1">ノートPC A</div>
        <div class="hs-node hs-n2">ノートPC B</div>
        <div class="hs-node hs-n3">ノートPC C</div>
        <div class="hs-node hs-n4">社内ネット</div>
      </div>
      <ul class="hs-traits">
        <li>すべてのトラフィックがゲートウェイ経由（1 hop 追加）</li>
        <li>ゲートウェイが単一障害点</li>
        <li>地理的に遠いと全トラフィックがそちらへ迂回</li>
      </ul>
    </div>
    <div class="hs-panel hs-mesh">
      <div class="hs-title">Mesh (Tailscale)</div>
      <div class="hs-diagram hs-mesh-diag">
        <div class="hs-node hs-m1">ノード A</div>
        <div class="hs-node hs-m2">ノード B</div>
        <div class="hs-node hs-m3">ノード C</div>
        <div class="hs-node hs-m4">ノード D</div>
      </div>
      <ul class="hs-traits">
        <li>ノード同士が P2P 直通、中央サーバーをトラフィックが経由しない</li>
        <li>中央サーバーは鍵交換・調整のみを担当</li>
        <li>地理的に近いノード同士は短い経路</li>
      </ul>
    </div>
  </div>
</div>
<style>
.hub-spoke .hs-grid{display:grid;grid-template-columns:1fr 1fr;gap:1rem}
.hub-spoke .hs-panel{border-radius:14px;padding:1rem .9rem;box-shadow:0 2px 10px rgba(0,0,0,.06)}
.hub-spoke .hs-hub{background:linear-gradient(135deg,#fff3e0,#ffe0b2)}
.hub-spoke .hs-mesh{background:linear-gradient(135deg,#e8f5e9,#c8e6c9)}
.hub-spoke .hs-title{font-size:13.5px;font-weight:700;text-align:center;letter-spacing:.04em;text-transform:uppercase;color:#5d4037;margin-bottom:.7rem}
.hub-spoke .hs-mesh .hs-title{color:#1b5e20}
.hub-spoke .hs-diagram{position:relative;height:160px;margin:.5rem 0 .8rem}
.hub-spoke .hs-center{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);background:linear-gradient(135deg,#ef6c00,#e65100);color:#fff;border-radius:50%;width:62px;height:62px;display:flex;align-items:center;justify-content:center;text-align:center;font-size:10.5px;font-weight:700;line-height:1.2;box-shadow:0 2px 8px rgba(0,0,0,.15);z-index:2}
.hub-spoke .hs-node{position:absolute;background:#fff;border:2px solid #ef6c00;border-radius:8px;padding:.3rem .55rem;font-size:11px;font-weight:700;color:#5d4037;box-shadow:0 1px 4px rgba(0,0,0,.08)}
.hub-spoke .hs-mesh .hs-node{border-color:#388e3c;color:#1b5e20}
.hub-spoke .hs-n1{top:8%;left:6%}
.hub-spoke .hs-n2{top:8%;right:6%}
.hub-spoke .hs-n3{bottom:8%;left:6%}
.hub-spoke .hs-n4{bottom:8%;right:6%}
.hub-spoke .hs-hub .hs-diagram::before{content:"";position:absolute;top:50%;left:50%;width:88%;height:88%;transform:translate(-50%,-50%);background:
  linear-gradient(45deg,transparent calc(50% - 1px),#ef6c0066 calc(50% - 1px),#ef6c0066 calc(50% + 1px),transparent calc(50% + 1px)),
  linear-gradient(-45deg,transparent calc(50% - 1px),#ef6c0066 calc(50% - 1px),#ef6c0066 calc(50% + 1px),transparent calc(50% + 1px));
  z-index:1}
.hub-spoke .hs-m1{top:8%;left:50%;transform:translateX(-50%)}
.hub-spoke .hs-m2{top:50%;right:6%;transform:translateY(-50%)}
.hub-spoke .hs-m3{bottom:8%;left:50%;transform:translateX(-50%)}
.hub-spoke .hs-m4{top:50%;left:6%;transform:translateY(-50%)}
.hub-spoke .hs-mesh-diag::before{content:"";position:absolute;top:50%;left:50%;width:78%;height:78%;transform:translate(-50%,-50%);background:
  linear-gradient(45deg,transparent calc(50% - 1px),#388e3c66 calc(50% - 1px),#388e3c66 calc(50% + 1px),transparent calc(50% + 1px)),
  linear-gradient(-45deg,transparent calc(50% - 1px),#388e3c66 calc(50% - 1px),#388e3c66 calc(50% + 1px),transparent calc(50% + 1px)),
  linear-gradient(0deg,transparent calc(50% - 1px),#388e3c66 calc(50% - 1px),#388e3c66 calc(50% + 1px),transparent calc(50% + 1px)),
  linear-gradient(90deg,transparent calc(50% - 1px),#388e3c66 calc(50% - 1px),#388e3c66 calc(50% + 1px),transparent calc(50% + 1px));
  z-index:0}
.hub-spoke .hs-traits{list-style:disc;padding-left:1.2rem;margin:0;font-size:12px;line-height:1.7;color:#5d4037}
.hub-spoke .hs-mesh .hs-traits{color:#1b5e20}
[data-mode="dark"] .hub-spoke .hs-hub{background:linear-gradient(135deg,#3a2410,#4a2f15)}
[data-mode="dark"] .hub-spoke .hs-mesh{background:linear-gradient(135deg,#1a3320,#263e2a)}
[data-mode="dark"] .hub-spoke .hs-title{color:#ffcc80}
[data-mode="dark"] .hub-spoke .hs-mesh .hs-title{color:#a5d6a7}
[data-mode="dark"] .hub-spoke .hs-traits{color:#ffcc80}
[data-mode="dark"] .hub-spoke .hs-mesh .hs-traits{color:#a5d6a7}
[data-mode="dark"] .hub-spoke .hs-node{background:#1f1f1f;color:#ffcc80}
[data-mode="dark"] .hub-spoke .hs-mesh .hs-node{color:#a5d6a7}
@media(max-width:768px){.hub-spoke .hs-grid{grid-template-columns:1fr}}
</style>

このモデルは社内のセキュリティポリシーを1点で強制するには良いのですが、家庭用ノートPC2台で韓国IP経由インフラを作るシナリオではちぐはぐです。釜山ノートPCがゲートウェイの役割まで兼ねればよいだけなのですが、そうするには2ノードが直通で通信できる必要があります。そして NAT 二重越しの家庭用ノートPC2台が直通で通信することは一般には不可能です — 外部から家庭用ルーターの22番ポートを叩いても、ルーターは「内部のどのデバイスへ送るか」を知らない構造になっているからです。メッシュVPNはこの問題を別のやり方で解決します。

---

## メッシュVPN — ノード同士で直通

メッシュVPNの発想はシンプルです。**中央ゲートウェイを経由せず、ノード同士で直接接続しよう。** ただし発想がシンプルでも実行は難しい。先ほど押さえたとおり、両側のノードがどちらも NAT の裏にいると、誰も先に接続を受けることができません。

解決の手がかりは **2つのピアが同時にお互い向けに outbound を撃つ** ことです（hole punching、第3回で深掘り）。そのためには、誰かが2つのピアに「今だ、同時に撃て」と合図を出さなくてはなりません。その合図役がメッシュVPNの **コーディネーションサーバー（coordination server）** です。

ここでメッシュVPNの中核となる分離が現れます。通信を2つのプレーンに分けて考える、というものです。

<div class="plane-split" style="margin:1.5rem 0">
  <div class="ps-grid">
    <div class="ps-panel ps-control">
      <div class="ps-head">
        <div class="ps-tag">Control Plane</div>
        <div class="ps-by">Tailscale coordination server</div>
      </div>
      <ul class="ps-list">
        <li>各ノードの <strong>WireGuard 公開鍵</strong> の登録・配布</li>
        <li>ノード一覧・ACL・MagicDNS マッピングの配布</li>
        <li>ピア間の hole punching 合図中継 (DERP)</li>
        <li>実際のデータトラフィックは <strong>ここを流れない</strong></li>
      </ul>
      <div class="ps-foot">中央集権 — 1か所で管理</div>
    </div>
    <div class="ps-panel ps-data">
      <div class="ps-head">
        <div class="ps-tag">Data Plane</div>
        <div class="ps-by">ノード ↔ ノード (WireGuard)</div>
      </div>
      <ul class="ps-list">
        <li>ノード間の <strong>E2E 暗号化トンネル</strong></li>
        <li>大半の時間は P2P direct で流れる</li>
        <li>Tailscale 社のインフラを経由しない</li>
        <li>会社がトラフィック内容を見られない（構造的保証）</li>
      </ul>
      <div class="ps-foot">分散 — ノード同士で直接</div>
    </div>
  </div>
  <p class="ps-cap">コーディネーションサーバーは鍵とメタデータのみを扱い、実際のパケットはノード同士でやり取りする。</p>
</div>
<style>
.plane-split .ps-grid{display:grid;grid-template-columns:1fr 1fr;gap:1rem}
.plane-split .ps-panel{border-radius:14px;padding:1rem .9rem;box-shadow:0 2px 10px rgba(0,0,0,.06);display:flex;flex-direction:column}
.plane-split .ps-control{background:linear-gradient(135deg,#e3f2fd,#bbdefb)}
.plane-split .ps-data{background:linear-gradient(135deg,#f3e5f5,#e1bee7)}
.plane-split .ps-head{margin-bottom:.7rem}
.plane-split .ps-tag{font-size:13px;font-weight:800;letter-spacing:.04em;text-transform:uppercase;color:#0d47a1}
.plane-split .ps-data .ps-tag{color:#4a148c}
.plane-split .ps-by{font-family:'SF Mono',Consolas,monospace;font-size:11.5px;color:#1565c0;margin-top:.15rem}
.plane-split .ps-data .ps-by{color:#6a1b9a}
.plane-split .ps-list{list-style:disc;padding-left:1.2rem;margin:0 0 .7rem;font-size:12.5px;line-height:1.7;color:#0d47a1;flex:1}
.plane-split .ps-data .ps-list{color:#4a148c}
.plane-split .ps-foot{font-size:11.5px;font-weight:700;text-align:center;padding:.4rem;background:rgba(255,255,255,.55);border-radius:6px;color:#0d47a1}
.plane-split .ps-data .ps-foot{color:#4a148c}
.plane-split .ps-cap{text-align:center;margin-top:.7rem;font-size:12px;color:var(--text-muted-color,#888);font-style:italic}
[data-mode="dark"] .plane-split .ps-control{background:linear-gradient(135deg,#0d2a4a,#10355a)}
[data-mode="dark"] .plane-split .ps-data{background:linear-gradient(135deg,#2a1a35,#3a2545)}
[data-mode="dark"] .plane-split .ps-tag,[data-mode="dark"] .plane-split .ps-by,[data-mode="dark"] .plane-split .ps-list,[data-mode="dark"] .plane-split .ps-foot{color:#90caf9}
[data-mode="dark"] .plane-split .ps-data .ps-tag,[data-mode="dark"] .plane-split .ps-data .ps-by,[data-mode="dark"] .plane-split .ps-data .ps-list,[data-mode="dark"] .plane-split .ps-data .ps-foot{color:#ce93d8}
[data-mode="dark"] .plane-split .ps-foot{background:rgba(255,255,255,.06)}
@media(max-width:768px){.plane-split .ps-grid{grid-template-columns:1fr}}
</style>

この分離がメッシュVPNのほぼすべての性質を決めます。

- **会社がトラフィック内容を見られない** — データプレーンはノード間E2E暗号化で、鍵はノード内部で生成されます。コーディネーションサーバーは公開鍵だけを受け取ります。
- **会社のインフラ費用が小さい** — コーディネーションサーバーはメタデータ（ノード一覧・ACL・鍵）のみを扱うので、ユーザー1人が一日中動画を見ても会社側のトラフィックはほとんど増えません。
- **会社が落ちてもしばらくは動作する** — ノードたちがすでに鍵とピア情報をキャッシュしていれば、コーディネーションサーバーが一時的に落ちてもデータプレーンはそのまま流れ続けます。

DERP relay も同じ文脈です — UDPがブロックされてP2P directが失敗すると、両ノードは Tailscale の DERP サーバー経由でパケットをやり取りしますが、**DERP は依然として暗号化されたパケットをそのまま転送するだけ** で復号しません。先ほど測定した28リージョンの DERP RTT 表に意味があるのはこのためです — そのインフラが無料で提供されつつも、会社が中身を覗かないことが構造的に保証されている、ということです。

この構造的保証の上に、Tailscale は外部認証と監査によっても同じ約束を明示しています。

> "**Private keys never leave the device. All traffic is end-to-end encrypted, always.**"
>
> "**Tailscale cannot read your traffic.**"
>
> — Tailscale Security ([tailscale.com/security](https://tailscale.com/security))
{: .prompt-info }

- **SOC 2 Type II** 認証（AICPA Trust Services Criteria — security / availability / confidentiality）
- 外部セキュリティ会社 **Latacora** による定期監査
- コード側：ピアレビュー + 自動化された静的解析 + 依存関係の脆弱性スキャン

推論（データプレーンがE2Eだから会社からは見えない）が、明示的な約束（会社からは見えないと約束している）と出会う地点です。どちらか一方だけでは不十分で、2つの保証が重なることが信頼モデルの安定性を作ります。

P2P direct をどう成立させるかについての Avery Pennarun の一行要約はこちらです。

> "There is no magic bullet for NAT traversal. Tailscale's approach: **try everything at once, and pick the best thing that works.**"
>
> — Avery Pennarun, "How NAT traversal works"
{: .prompt-info }

---

## WireGuard — データプレーンの標準

データプレーン自体は Tailscale が作ったものではなく、**WireGuard** という別のプロトコルをそのまま使っています。WireGuard は Jason A. Donenfeld が作ったVPNプロトコルで、**2020年1月に Linus Torvalds の net-next ツリーにマージされ、Linux 5.6（2020-03-29）のメインラインに含まれました**。

コードベースが小さく明快であることが最大の特徴で、Linus の次の発言が2018年の LKML 引用としてよく参照されます。

> "Maybe the code isn't perfect, but I've skimmed it, and **compared to the horrors that are OpenVPN and IPsec, it's a work of art.**"
>
> — Linus Torvalds, LKML (Ars Technica 2018-08 引用)
{: .prompt-info }

WireGuard の暗号スタックは標準のビルディングブロックをシンプルに組み合わせています。

| 役割 | アルゴリズム |
|---|---|
| 鍵交換 | Curve25519 |
| 対称暗号 + 認証 | ChaCha20-Poly1305 (AEAD) |
| ハッシュ関数 | BLAKE2s |
| 鍵導出 | HKDF |
| ハッシュテーブル鍵 | SipHash24 |

ハンドシェイクは **Noise Protocol Framework の `IK` パターン**（`Noise_IKpsk2_25519_ChaChaPoly_BLAKE2s`）をそのまま採用し、2メッセージで完了します。アルゴリズム交渉（cipher suite negotiation）自体が存在しないため、ダウングレード攻撃が構造的にブロックされている点が IPsec/TLS ファミリーとの最大の違いです。

Tailscale はこれを自前で再実装せず、**公式の `wireguard-go` 実装** をそのまま組み込んでいます。メッシュのメタデータ側に欠陥があったとしても、データプレーンの暗号化は別システムの特性をそのまま受け継ぎます。

WireGuard が信頼されている度合いは、Linus の発言だけでなく採用例と学術的検証からも確認できます。

- **商用VPNでの採用** — NordVPN、IPVanish、TunnelBear などが自社VPNのデータプレーンとして WireGuard を直接採用（Wikipedia）
- **形式検証** — 2019年5月、INRIA の研究グループが WireGuard プロトコルの **machine-checked proof** を発表。すなわちセキュリティ特性が数学的に証明されました

これにより WireGuard は **(a) Linus がメインラインに受け入れ**、**(b) INRIA が形式検証を発表し**、**(c) 商用VPNが自社製品にそのまま採用する** という3重の根拠の上に立っています。Tailscale が自前で再実装せず、そのまま採用するという判断はこの根拠の上では自然です。

---

## 無料プランの上限（Personal）

ここからはコストの話に移ります。Tailscale の無料プランである **Personal** は次の上限を持っています（2026-05時点の公式ページ）。

<div class="free-tier" style="margin:1.5rem 0">
  <div class="ft-grid">
    <div class="ft-card">
      <div class="ft-num">6</div>
      <div class="ft-label">ユーザー</div>
      <div class="ft-sub">従来の3名から拡大</div>
    </div>
    <div class="ft-card ft-hl">
      <div class="ft-num">∞</div>
      <div class="ft-label">ユーザーデバイス</div>
      <div class="ft-sub">台数制限なし</div>
    </div>
    <div class="ft-card">
      <div class="ft-num">3</div>
      <div class="ft-label">ACL グループ</div>
      <div class="ft-sub">ポリシー分岐用</div>
    </div>
    <div class="ft-card">
      <div class="ft-num">50</div>
      <div class="ft-label">タグ付きリソース</div>
      <div class="ft-sub">サーバー・サービス識別</div>
    </div>
  </div>
  <div class="ft-features">
    <div class="ft-f">Exit node</div>
    <div class="ft-f">Subnet router</div>
    <div class="ft-f">MagicDNS</div>
    <div class="ft-f">Split tunneling</div>
    <div class="ft-f">Tailscale SSH (5 hosts)</div>
    <div class="ft-f">Funnel · Serve</div>
    <div class="ft-f">DERP グローバルインフラ</div>
    <div class="ft-f">Zero Trust ACL</div>
  </div>
  <p class="ft-cap">個人インフラ用途では事実上天井の見えない水準。本シリーズの3ノードメッシュもデバイス数の上限内で十分な余裕。</p>
</div>
<style>
.free-tier .ft-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:.7rem;margin-bottom:.9rem}
.free-tier .ft-card{background:linear-gradient(135deg,#e8f5e9,#c8e6c9);border-radius:12px;padding:.95rem .7rem;text-align:center;color:#1b5e20;box-shadow:0 1px 4px rgba(0,0,0,.06)}
.free-tier .ft-card.ft-hl{background:linear-gradient(135deg,#388e3c,#2e7d32);color:#fff}
.free-tier .ft-num{font-size:32px;font-weight:800;font-family:'SF Mono',Consolas,monospace;letter-spacing:-.02em;line-height:1}
.free-tier .ft-label{font-size:12.5px;font-weight:700;margin:.45rem 0 .15rem;letter-spacing:.02em}
.free-tier .ft-sub{font-size:11px;opacity:.85;line-height:1.4}
.free-tier .ft-features{display:flex;flex-wrap:wrap;gap:.45rem;justify-content:center;margin:.6rem 0 .3rem}
.free-tier .ft-f{background:rgba(56,142,60,.12);color:#2e7d32;border:1px solid rgba(56,142,60,.3);border-radius:14px;padding:.25rem .7rem;font-size:11.5px;font-weight:700}
.free-tier .ft-cap{text-align:center;margin-top:.5rem;font-size:12px;color:var(--text-muted-color,#888);font-style:italic}
[data-mode="dark"] .free-tier .ft-card{background:linear-gradient(135deg,#1a3320,#263e2a);color:#a5d6a7}
[data-mode="dark"] .free-tier .ft-card.ft-hl{background:linear-gradient(135deg,#2e7d32,#388e3c);color:#fff}
[data-mode="dark"] .free-tier .ft-f{background:rgba(165,214,167,.1);color:#a5d6a7;border-color:rgba(165,214,167,.25)}
@media(max-width:768px){.free-tier .ft-grid{grid-template-columns:1fr 1fr}}
</style>

ここで目を引くのは、**有料プランにある「上位機能」の大半が無料プランにもそのまま入っている** という事実です。Exit node、MagicDNS、ACL、Subnet router、DERPインフラ利用権 — 本シリーズが扱う内容のほぼ全部が Personal に含まれています。商用VPNの無料プランが通常「データ容量制限」や「サーバー数制限」をかけてくるのとは対照的です。

### では、なぜ無料で出すのか

商用インフラがこの規模の上限を無料で開放する、というのは最初は奇異に見えます。しかし上で扱った control / data plane の分離から、答えの半分は自然に導かれます。

**会社のインフラを流れるトラフィックが小さい。** ユーザーが釜山↔福岡で1080p動画を5時間視聴しても、Tailscale 社側のインフラに追加されるコストは鍵更新やメタデータ同期といったメッセージの数KB程度のみです。動画パケットは福岡 Mac と釜山ノートPC の間の P2P direct の上だけを流れます。ユーザーを1人増やすときの限界費用が事実上ゼロに近い、ということです。

残り半分は会社の GTM（go-to-market）戦略の側面です。Tailscale は明示的に **「個人は無料で十分に使ってもらい、会社で導入する段階で有料へ移行」** モデルを取っています。エンジニアが自分のノートPCで Personal プランに慣れた後、自分の会社で同じツールを使おうと提案する流れは、会社にとって最も安価な営業チャネルだからです。

会社側はこれを資本主義的な合理性だけで包装するのではなく、ミッション次元の発言としても明示しています。

> "**If we're going to fix the Internet, there's no point only fixing it for big companies who can pay a lot.**"
>
> — Tailscale 公式ブログ
{: .prompt-info }

上で整理したファンディング（累計 $272M）の上で、個人向け無料プランは会社のコスト負担側では十分に賄える一方、同時に次世代のエンジニアたちが社内導入を引っ張ってくるチャネルの役割を果たします。

---

## なぜ他のメッシュVPNではなく Tailscale なのか

このシリーズが Tailscale を選んだ理由を短くまとめます。メッシュVPN／Zero Trust 領域には他の選択肢も少なくありません。

| ツール | コーディネーションサーバー | データプレーン | 無料上限 | 本シリーズのシナリオでは |
|---|---|---|---|---|
| **Tailscale** | SaaS（Tailscale 運用） | WireGuard | 6 user / デバイス無制限 | 本シリーズで採用 |
| Headscale | self-hosted（オープンソース） | WireGuard | 無制限（自前サーバー） | コーディネーションサーバーを自前運用する必要あり |
| ZeroTier | SaaS | 独自プロトコル | 25 ノード | ノード上限がすぐ埋まり、WireGuard でない |
| Nebula | self-hosted | 独自（Slack 出身） | 無制限（自前 PKI） | PKI を自前運用する必要あり |
| Twingate | SaaS（B2B 中心） | 独自 | 5 user、ユーザーデバイス制限 | 無料上限がすぐに足りなくなる |
| raw WireGuard | なし | WireGuard | 無制限 | 鍵配布・NAT traversal をすべて自前。家庭用 NAT 二重越しはほぼ不可能 |
| OpenVPN | 自前サーバー | OpenSSL | 自前運用 | hub-and-spoke、NAT の裏の家庭用ノートPCには不向き |

本シナリオの2つの決定要件は **(a) 無料で動作すること** と **(b) 両側の NAT を自動で越えること** です。(a)は Headscale・Nebula の self-hosted 負担を排除し、(b)は raw WireGuard・OpenVPN の hub-and-spoke を排除します。残る候補は Tailscale と ZeroTier くらいで、ZeroTier は無料上限（25ノード）と WireGuard プロトコル非採用が弱点となります。

---

## まとめ

| 質問 | 答え |
|---|---|
| 動機 | 福岡で1年以上居住する中で、韓国の決済・銀行・コンテンツが海外IPで弾かれるパターンが累積 |
| 解決方式 | 釜山実家の押し入れのノートPCを無人 exit node に、福岡 Mac から SSH でリモート運用 |
| 稼働結果（実測） | P2P direct 50ms / Tunnel DOWN 24.9 Mbps / 無人で15時間以上の安定動作 / 自己修復トリガー 0件 |
| Tailscale 社 | 2019年トロント、Google 出身の4人（Brad Fitzpatrick を含む）、累計調達額 $272M |
| メッシュVPNの中核 | WireGuard（データプレーン）+ Tailscale コーディネーションサーバー（コントロールプレーン）の分離 |
| WireGuard の強み | Linux 5.6 メインライン、Noise IK + ChaCha20-Poly1305、コードのシンプルさ（"a work of art" — Linus） |
| 会社がトラフィックを見られない根拠 | データプレーンがノード間 E2E で、秘密鍵がノードの外に出ない、DERP も暗号文のまま転送 |
| 無料で成立する理由 | 会社インフラ側の限界費用 ≈ 0 + PLG 営業モデル + 明示されたミッション |
| Personal プラン | 6 user / デバイス無制限 / Exit Node・MagicDNS・ACL を含む |

この第1回がシリーズの動機・結果、そしてそれが可能となる構造的根拠だったとすれば、第2回はそのインフラを実際に作るステージへ進みます。

---

## 参考資料

- [`Epheria/tailnet-ops`](https://github.com/Epheria/tailnet-ops) — 本シリーズの運用コード一式
- Donenfeld, J. A. *WireGuard: Next Generation Kernel Network Tunnel.* NDSS 2017. ([wireguard.com/papers/wireguard.pdf](https://www.wireguard.com/papers/wireguard.pdf))
- Pennarun, A. *How NAT traversal works.* Tailscale Blog. ([tailscale.com/blog/how-nat-traversal-works](https://tailscale.com/blog/how-nat-traversal-works))
- Tailscale. *How Tailscale works.* Tailscale Blog. ([tailscale.com/blog/how-tailscale-works](https://tailscale.com/blog/how-tailscale-works))
- Tailscale. *Pricing — Personal plan.* ([tailscale.com/pricing](https://tailscale.com/pricing))
- *Tailscale.* Wikipedia. ([en.wikipedia.org/wiki/Tailscale](https://en.wikipedia.org/wiki/Tailscale))
- *WireGuard.* Wikipedia. ([en.wikipedia.org/wiki/WireGuard](https://en.wikipedia.org/wiki/WireGuard))
- Salter, J. *WireGuard VPN review: A new type of VPN offers serious advantages.* Ars Technica, 2018-08.（Linus Torvalds 引用元）

---

## 次回

第2回では、釜山実家のノートPCを実際に無人 exit node に仕立てるセットアップ + 無人運用の自己修復 + セキュリティ監査を一気に扱います。**実家への1回の訪問で済ませる作業の全体像** と、福岡から実家に一度も行かずに新しいデバイスを追加できるリモート運用モデルを整理します。

> 第2回 — 実家セットアップ + 無人運用 + セキュリティ（執筆予定）
{: .prompt-info }
