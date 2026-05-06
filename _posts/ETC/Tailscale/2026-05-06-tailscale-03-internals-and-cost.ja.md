---
title: "Tailscaleシリーズ第3編 — 動作原理とコスト・限界 (DERP・MagicDNS・hole punching・年1,100円振り返り)"
lang: ja
date: 2026-05-06 18:00:00 +0900
categories: [ETC, Tailscale]
tags: [tailscale, nat-traversal, hole-punching, derp, magicdns, stun, ice, infrastructure]
toc: true
toc_sticky: true
difficulty: intermediate
prerequisites:
  - /posts/tailscale-01-foundations/
  - /posts/tailscale-02-setup-and-ops/
tldr:
  - TailscaleのNAT越えは「全部同時に試して最初に通った経路」 — STUN/ICE標準 + UPnP/PMP/PCPポートマップ + DERP fallbackを並列に試行する
  - Symmetric NAT(Hard NAT)はbirthday paradoxで突破 — 256個のポートを開いて無作為にprobe、2,048回で99.9% / 約20秒
  - DERPはP2P失敗時にHTTPSの上で暗号文をそのまま転送するfallback。E2E保証は維持
  - MagicDNSは100.100.100.100のstub resolverでOSのDNSを横取りし、短いホスト名を100.64.x.xに解決する
  - 実コスト — 電気代 約770円/年が事実上すべて。ノートPC・インターネットは埋没コスト
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

## この編で扱うこと

シリーズ最終編です。2つのテーマをまとめます。

**Part 1 — 動作原理**: 本シリーズのインフラを成立させているメカニズム。家庭NAT 2重の奥にあるノートPC 2台がどうやって直通で通信するのか。STUN・ICE・hole punching・DERP・MagicDNSをひとまとめに整理します。

**Part 2 — コスト・限界・振り返り**: 年間1,100円インフラの実コスト分解、未検証項目、シリーズ全体の振り返り。

この編単独でも読めるように書いていますが、インフラが何をしているかという全体像は第1・2編にあります。

---

# Part 1 — 動作原理

## 2つのNAT分類 — 伝統 vs 現代

NAT越えを語るにはまずNATの種類を押さえる必要があります。よく耳にする分類は1990年代後半から使われてきた **cone系の4分類** です。

| 伝統的な分類 | 動作 |
|---|---|
| Full Cone | 外部の誰からでもNATの外部ポート宛に送れば内部に届く (最も緩い) |
| Restricted Cone | 内部が先に送った外部IPからのみ着信可能 |
| Port-Restricted Cone | 内部が先に送った外部IP+ポートからのみ着信可能 |
| Symmetric | 宛先が違えば外部ポートも別マッピング (最も厳しい) |

この分類は直感的ですが、実際のNAT機器の動きを正確に捉えきれないという批判があり、 **RFC 4787** が新しい分類を提案し、Tailscaleもこちらを採用しています。

> Tailscaleの表現 — "**Endpoint-Independent Mapping (EIM)**, and the hard variant **Endpoint-Dependent Mapping (EDM)**" ([How NAT traversal works](https://tailscale.com/blog/how-nat-traversal-works))

<div class="nat-class" style="margin:1.5rem 0">
  <div class="nc-grid">
    <div class="nc-card nc-eim">
      <div class="nc-tag">Easy NAT (EIM)</div>
      <div class="nc-key">Endpoint-Independent Mapping</div>
      <div class="nc-detail">宛先がどこでも同じ外部ポートを再利用する。STUNで一度発見すれば、他のピアともそのポートで通る。</div>
      <div class="nc-foot">大半の家庭用ルーター</div>
    </div>
    <div class="nc-card nc-edm">
      <div class="nc-tag">Hard NAT (EDM)</div>
      <div class="nc-key">Endpoint-Dependent Mapping</div>
      <div class="nc-detail">宛先ごとに異なる外部ポートを割り当てる。STUNで発見したポートはSTUNサーバー専用で、別のピア向けには別ポートを改めて探す必要がある。</div>
      <div class="nc-foot">一部ISPのCGNAT、企業NAT</div>
    </div>
  </div>
</div>
<style>
.nat-class .nc-grid{display:grid;grid-template-columns:1fr 1fr;gap:1rem}
.nat-class .nc-card{border-radius:14px;padding:1.1rem 1rem;color:#fff;box-shadow:0 2px 10px rgba(0,0,0,.08);display:flex;flex-direction:column}
.nat-class .nc-eim{background:linear-gradient(135deg,#388e3c,#2e7d32)}
.nat-class .nc-edm{background:linear-gradient(135deg,#c62828,#b71c1c)}
.nat-class .nc-tag{font-size:13.5px;font-weight:800;letter-spacing:.04em;text-transform:uppercase;margin-bottom:.3rem}
.nat-class .nc-key{font-family:'SF Mono',Consolas,monospace;font-size:11.5px;background:rgba(255,255,255,.18);padding:3px 8px;border-radius:5px;align-self:flex-start;margin-bottom:.6rem}
.nat-class .nc-detail{font-size:12.5px;line-height:1.6;flex:1}
.nat-class .nc-foot{font-size:11.5px;opacity:.85;margin-top:.6rem;font-style:italic}
@media(max-width:768px){.nat-class .nc-grid{grid-template-columns:1fr}}
</style>

この分類が重要なのは、 **「両端EIMならhole punchingが比較的容易、片方でもEDMなら困難」** がNAT越え戦略の最初の分岐点だからです。本シリーズの釜山KTルーターと福岡の家庭ルーターはどちらもEIM系として観測されており、P2P directが大きな苦労なく成立します(第1編の測定基準による)。

---

## STUN — 「自分はインターネット上でどう見えているか」

STUN(Session Traversal Utilities for NAT)を一言でまとめると、 **「外部のSTUNサーバーへパケットを投げ、そのサーバーが見た自分の外部IP・ポートを返してもらうプロトコル」** です。

> ### ちょっと待って、これだけ確認しておこう
>
> **「STUNのRFC番号は5389ではなく8489」**
>
> ネット上の古い資料の多くがSTUNを **RFC 5389** として引用していますが、2020年2月発行の **RFC 8489が5389をobsolete** (廃止)しています。つまり現在の標準は8489です。
>
> 8489の主な変更点:
> - **MESSAGE-INTEGRITY-SHA256** 属性の追加 — MD5ベースの認証に加えてSHA-256オプション
> - **USERHASH** 属性によるユーザー名の匿名化
> - **PASSWORD-ALGORITHM** 属性によるパスワード保護アルゴリズムの選択
> - **nonce cookie** メカニズムによるbid-down攻撃への防御
>
> 本シリーズ本文ではRFC 8489表記に従います。

> Tailscaleの表現 — "Your machine sends a 'what's my endpoint from your point of view?' request to a STUN server, and the server replies with 'here's the ip:port that I saw your UDP packet coming from.'"

<div class="stun-flow" style="margin:1.5rem 0">
  <div class="sf-row">
    <div class="sf-step">
      <div class="sf-num">1</div>
      <div class="sf-text"><strong>OUT</strong> ノードがプライベートIP <code>192.168.0.10:54321</code> からSTUNサーバー <code>X.X.X.X:3478</code> へUDPパケットを送信</div>
    </div>
    <div class="sf-step">
      <div class="sf-num">2</div>
      <div class="sf-text"><strong>NAT</strong> 家庭ルーターが <code>192.168.0.10:54321 ↔ public:62000</code> のマッピングを生成</div>
    </div>
    <div class="sf-step">
      <div class="sf-num">3</div>
      <div class="sf-text"><strong>STUN</strong> サーバーが「あなたは <code>public:62000</code> から来た」と応答</div>
    </div>
    <div class="sf-step">
      <div class="sf-num">4</div>
      <div class="sf-text"><strong>SHARE</strong> ノードが <code>public:62000</code> をcontrol plane経由でピアに通知</div>
    </div>
  </div>
</div>
<style>
.stun-flow .sf-row{display:grid;grid-template-columns:repeat(4,1fr);gap:.6rem}
.stun-flow .sf-step{background:linear-gradient(135deg,#e3f2fd,#bbdefb);border-radius:10px;padding:.8rem .7rem;position:relative}
.stun-flow .sf-step:not(:last-child)::after{content:"→";position:absolute;right:-.85rem;top:50%;transform:translateY(-50%);color:#1976d2;font-size:18px;font-weight:700;z-index:1}
.stun-flow .sf-num{display:inline-block;width:22px;height:22px;border-radius:50%;background:#1976d2;color:#fff;text-align:center;line-height:22px;font-size:12px;font-weight:700;margin-bottom:.4rem}
.stun-flow .sf-text{font-size:12px;line-height:1.5;color:#0d47a1}
.stun-flow .sf-text code{background:rgba(255,255,255,.65);padding:1px 5px;border-radius:4px;font-size:11px}
[data-mode="dark"] .stun-flow .sf-step{background:linear-gradient(135deg,#0d2a4a,#10355a)}
[data-mode="dark"] .stun-flow .sf-text{color:#90caf9}
[data-mode="dark"] .stun-flow .sf-text code{background:rgba(255,255,255,.1);color:#e3f2fd}
@media(max-width:768px){.stun-flow .sf-row{grid-template-columns:1fr 1fr}.stun-flow .sf-step:not(:last-child)::after{display:none}}
</style>

核心となる制約は、STUNの発見結果は **そのsocketでのみ使わなければならない** という点です — 別のsocketを使うとNATが別のマッピングを作ってしまい、せっかく発見したポートが無意味になります。そのためTailscaleは「通信に使うsocketからSTUNパケットを直接投げる」パターンを採ります。

EIM NATではこれで終わりです — 発見した `public:62000` が他のピアともそのまま通用します。EDM NATではあまり役に立たず — 次節のbirthday paradoxへ進む必要があります。

---

## ICE — 「全部同時に試す」

ICE(Interactive Connectivity Establishment, RFC 8445)は、 **複数のcandidate(接続候補アドレス)を同時に集めてすべて試行し、最初に応答が返ってきた経路を採用する** アルゴリズムです。

Tailscaleが1ノードに対して同時に試行するcandidateは以下の5種類です(公式ブログより)。

<div class="candidates" style="margin:1.5rem 0">
  <div class="cd-grid">
    <div class="cd-card cd-1">
      <div class="cd-num">1</div>
      <div class="cd-name">LANアドレス</div>
      <div class="cd-detail">同一ネットワークならNAT越え自体が不要。直接通信。</div>
    </div>
    <div class="cd-card cd-2">
      <div class="cd-num">2</div>
      <div class="cd-name">STUN WANアドレス</div>
      <div class="cd-detail">EIM NATで発見した public:port</div>
    </div>
    <div class="cd-card cd-3">
      <div class="cd-num">3</div>
      <div class="cd-name">ポートマップアドレス</div>
      <div class="cd-detail">UPnP-IGD / NAT-PMP / PCPでルーターに明示的にフォワーディングを要求</div>
    </div>
    <div class="cd-card cd-4">
      <div class="cd-num">4</div>
      <div class="cd-name">NAT64経路</div>
      <div class="cd-detail">IPv6-only環境からIPv4ピアと通信</div>
    </div>
    <div class="cd-card cd-5">
      <div class="cd-num">5</div>
      <div class="cd-name">DERP relay</div>
      <div class="cd-detail">上の4つすべてが失敗した時のfallback。常にpreselected</div>
    </div>
  </div>
  <p class="cd-cap">Tailscaleはround-trip latency基準で最速の経路を選び、より良い経路が見つかれば即座にアップグレードする。</p>
</div>
<style>
.candidates .cd-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:.55rem}
.candidates .cd-card{border-radius:11px;padding:.8rem .7rem;color:#fff;box-shadow:0 2px 8px rgba(0,0,0,.08);text-align:center}
.candidates .cd-1{background:linear-gradient(135deg,#388e3c,#2e7d32)}
.candidates .cd-2{background:linear-gradient(135deg,#1976d2,#1565c0)}
.candidates .cd-3{background:linear-gradient(135deg,#7b1fa2,#6a1b9a)}
.candidates .cd-4{background:linear-gradient(135deg,#ef6c00,#e65100)}
.candidates .cd-5{background:linear-gradient(135deg,#37474f,#263238)}
.candidates .cd-num{font-size:11.5px;font-weight:700;background:rgba(255,255,255,.22);width:22px;height:22px;line-height:22px;border-radius:50%;margin:0 auto}
.candidates .cd-name{font-size:13px;font-weight:800;margin:.4rem 0 .25rem;letter-spacing:.01em}
.candidates .cd-detail{font-size:11px;line-height:1.5;opacity:.92}
.candidates .cd-cap{text-align:center;margin-top:.7rem;font-size:12px;color:var(--text-muted-color,#888);font-style:italic}
@media(max-width:768px){.candidates .cd-grid{grid-template-columns:1fr 1fr}}
</style>

このモデルの核心は **"all connections start out with DERP preselected"** — すべての接続は開始時点でDERP経由で流れており、より良い経路(LAN/STUN/ポートマップ)が見つかった瞬間にデータプレーンを即座にアップグレードします。つまりNAT越えが遅れても、 **最初のパケットから通信は始まっている** わけです。

> Avery Pennarunの一行要約 — "**try everything at once, and pick the best thing that works**"

---

## Hole Punching — 2つのピアが同時にoutbound

大半の家庭用NAT(EIM)は「内部から先に外向きに送ったことのある外部IP・ポートからのinboundは許可する」というステートフルファイアウォールの動作を示します。これがhole punchingの手がかりです。

<div class="hole-punch" style="margin:1.5rem 0">
  <div class="hp-row">
    <div class="hp-side">
      <div class="hp-tag">Peer A (NATの内側)</div>
      <div class="hp-box">
        <div class="hp-line">1. control planeからBのpublicアドレスを受け取る</div>
        <div class="hp-line">2. Bへ向けてoutbound UDPパケットを送出</div>
        <div class="hp-line">3. NATがマッピングを生成、自身のファイアウォールもBからの応答を許可</div>
      </div>
    </div>
    <div class="hp-mid">
      <div class="hp-arrow">⟷</div>
      <div class="hp-arrow-text">同時</div>
    </div>
    <div class="hp-side">
      <div class="hp-tag">Peer B (NATの内側)</div>
      <div class="hp-box">
        <div class="hp-line">1. control planeからAのpublicアドレスを受け取る</div>
        <div class="hp-line">2. Aへ向けてoutbound UDPパケットを送出</div>
        <div class="hp-line">3. NATがマッピングを生成、自身のファイアウォールもAからの応答を許可</div>
      </div>
    </div>
  </div>
  <p class="hp-cap">"packets must flow out before packets can flow back in" — Tailscaleのhole punchingの原理</p>
</div>
<style>
.hole-punch .hp-row{display:grid;grid-template-columns:1fr auto 1fr;gap:.7rem;align-items:center}
.hole-punch .hp-side{display:flex;flex-direction:column;gap:.4rem}
.hole-punch .hp-tag{font-size:12px;font-weight:700;color:var(--text-muted-color,#666);text-align:center;letter-spacing:.04em;text-transform:uppercase}
.hole-punch .hp-box{background:linear-gradient(135deg,#fff3e0,#ffe0b2);border-radius:10px;padding:.85rem .8rem}
.hole-punch .hp-line{font-size:12.5px;line-height:1.6;color:#5d4037;border-bottom:1px dashed rgba(93,64,55,.2);padding:.25rem 0}
.hole-punch .hp-line:last-child{border-bottom:none}
.hole-punch .hp-mid{display:flex;flex-direction:column;align-items:center}
.hole-punch .hp-arrow{font-size:24px;font-weight:700;color:#ef6c00}
.hole-punch .hp-arrow-text{font-size:11px;color:#ef6c00;font-weight:700;letter-spacing:.06em}
.hole-punch .hp-cap{text-align:center;margin-top:.7rem;font-size:12px;color:var(--text-muted-color,#888);font-style:italic}
[data-mode="dark"] .hole-punch .hp-box{background:linear-gradient(135deg,#3a2410,#4a2f15)}
[data-mode="dark"] .hole-punch .hp-line{color:#ffcc80;border-bottom-color:rgba(255,204,128,.2)}
@media(max-width:768px){.hole-punch .hp-row{grid-template-columns:1fr}.hole-punch .hp-mid{transform:rotate(90deg);padding:.3rem 0}}
</style>

この過程で **最初のoutboundパケットは相手のNATで拒否されます** (まだマッピングが無いため到達できない)。しかしその拒否されたパケットは自分のNATにマッピングを作り、続いて相手から飛んでくるoutboundパケットが自分のNATに届いた際に、 **ファイアウォールが「これは我々が先に送った先からの応答だ」と認識** して通します。

以降は両端が30秒ごとにkeep-alive pingをやり取りしてNATマッピングを維持します — 一般的な家庭用NATは無通信30秒〜数分でマッピングを失効させるためです。

---

## Symmetric NATとBirthday Paradox

EDM NAT(Hard NAT)では上述のhole punchingが **そのままでは通用しません** — 宛先ごとに別の外部ポートを割り当てるため、control planeが伝えたポートと相手が実際に受け取るポートが食い違います。

解決策は **確率に頼ること** です。片方が256個のポートを同時に開けておき、相手側はその256個のどこかに無作為にprobeを投げます。一致(birthday collision)が起これば穴が開きます。

<div class="bday" style="margin:1.5rem 0">
  <div class="bd-table-wrap">
    <table class="bd-table">
      <thead><tr><th>Probe回数</th><th>成功確率</th><th>所要時間 (100 pkt/s)</th></tr></thead>
      <tbody>
        <tr><td>174</td><td>50%</td><td>1.7s</td></tr>
        <tr><td>256</td><td>64%</td><td>2.6s</td></tr>
        <tr><td>1,024</td><td>98%</td><td>10s</td></tr>
        <tr class="bd-hl"><td>2,048</td><td>99.9%</td><td>~20s</td></tr>
      </tbody>
    </table>
  </div>
  <p class="bd-cap">Tailscale公式の数値。256ポートのプール上で無作為にprobeした際の成功確率。</p>
</div>
<style>
.bday .bd-table-wrap{overflow-x:auto}
.bday .bd-table{margin:0 auto;border-collapse:collapse;font-size:13px}
.bday .bd-table th,.bday .bd-table td{padding:.55rem 1.2rem;border:1px solid rgba(128,128,128,.25);text-align:center}
.bday .bd-table th{background:linear-gradient(135deg,#7b1fa2,#6a1b9a);color:#fff;font-weight:700;letter-spacing:.02em}
.bday .bd-table td{font-family:'SF Mono',Consolas,monospace}
.bday .bd-hl td{background:rgba(123,31,162,.12);font-weight:800;color:#4a148c}
[data-mode="dark"] .bday .bd-hl td{background:rgba(206,147,216,.15);color:#ce93d8}
.bday .bd-cap{text-align:center;margin-top:.7rem;font-size:12px;color:var(--text-muted-color,#888);font-style:italic}
</style>

数学的に見ると、可能なポート空間が65,535で片方が256個を開いた場合、無作為なprobe 1回がそのいずれかに当たる確率は256/65,535 ≈ 0.39%。 1 - (1 - 256/65535)^N がN=2,048で0.999を超えます ( `birthday paradox` と呼ばれるのは √N 効果で探索空間が平方根で縮むため — 線形ではなく)。

100パケット/秒の送信ペースで2,048 probe = およそ20秒。実測では半分以上が2秒以内に通過するとTailscaleが報告しています。

> Tailscaleの実測 — "half the time we'll get through in under 2 seconds" (How NAT traversal works)

**より厳しいケース — 両端ともEDM**: 探索空間が掛け算になり、99.9%到達まで約28分かかります(170,000 probes / 100 pkt/s)。このようなケースでは事実上DERP fallbackに落ち込みます。

本シリーズのシナリオでは釜山KTルーターがEIM、福岡の家庭ルーターもEIMなので、birthday paradoxが発動する出番はありません — STUN一発で終わります。

---

## DERP — 最後のセーフティネット

P2P directがすべて失敗した場合、 **DERP(Designated Encrypted Relay for Packets)** がfallbackとして作動します。DERPの特殊性を表で整理します。

| 観点 | DERPの動作 |
|---|---|
| プロトコル | **HTTPS上 (TCP/443)** — UDP遮断環境でも通過 |
| データ処理 | **暗号化されたパケットをそのまま転送** — 復号不可 (E2E保証は維持) |
| ノード側の鍵 | DERPサーバーには **秘密鍵を渡さない** — ノード内にのみ存在 |
| TURNとの関係 | 「DERPはTURNと同じ役割だが、HTTPSストリーム + WireGuard鍵を使う」 |
| グローバルインフラ | Tailscaleが28以上のリージョンで運用、 **Personal無料プランに含まれる** |
| 開始時の動作 | **「常にDERPがpreselected」** — 最初のパケットから通信開始 |

DERPが **TCP/443 (HTTPS)** の上で動作するという点が運用上重要です — UDPが塞がれているカフェ・ホテル・企業ネットワークでもTailscaleが動作する理由です。ドメインは普通のHTTPSトラフィックに見え、パケットの中身は既にWireGuardで暗号化されているので中間者には見えません。

> Tailscaleの表現 — "Your traffic remains end-to-end encrypted when it passes through a relay server."

### TURN vs DERP — 何が同じで何が違うか

DERPはIETF標準の **TURN(Traversal Using Relays around NAT, RFC 8656)** と同じポジションを占めますが、実装は別物です。比較表:

| 観点 | TURN (RFC 8656) | Tailscale DERP |
|---|---|---|
| 標準化 | IETF標準 | Tailscale独自実装 (オープンソース) |
| トランスポート | UDP / TCP / TLS | **HTTPS (TCP/443)** 専用 |
| 認証 | TURN認証情報 (username/credential) | WireGuard鍵 |
| データプレーン | 暗号文/平文ともに可 | **暗号文のみ (E2E保証)** |
| 一般的な用途 | WebRTCビデオ会議のfallback | メッシュVPNノード間のfallback |
| 運用コスト | 別途TURNサーバーが必要 | Tailscaleグローバルインフラ (無料プランに含まれる) |

**核心の差は「TLS上のHTTPS専用」** という決定です。TURNはUDP・TCPいずれも使いますが、一部の企業ファイアウォールはTURNの標準ポート(3478, 5349)を見抜いて遮断する可能性がある一方、DERPは **一般的なWebトラフィックと区別できないHTTPS** の上にあるため、ほぼあらゆる環境で通過します。カフェ・ホテル・空港Wi-Fiでも動作が保証される理由がこれです。

> ### ちょっと待って、これだけ確認しておこう
>
> **「DERPサーバーは実はSTUN responderも兼ねている — 1ホストで2役を同時に」**
>
> 上ではSTUNとDERPを別個のメカニズムとして扱いましたが、運用面では両者はほぼ同じインフラの上にあります — Tailscaleのグローバル DERPノードは **HTTPS relayとSTUN responderを1ホストで併設提供** しています。同じノードホストがTCP/443(HTTPS)上のDERP relayとしても応答し、UDP/3478(STUN)としても応答します。
>
> つまり「Tokyoリージョンに DERPノードを1台置く」と — (a) UDPが通る環境ではそのノードが **STUNで外部IP・ポート発見** を助けてP2P directを成立させ、(b) UDPが塞がれている環境ではそのノードが **HTTPS relayとしてfallback** を引き受けます。1ノードが2役を同時にこなす構造が、グローバルDERPインフラのコストを一定水準に抑える根拠の一つになっています。
>
> 本シリーズ第1編の `tailscale netcheck` が28リージョンすべてのDERPに対してRTTを一度に計測できたのも同じ理由 — STUNとDERPで別々のエンドポイントを呼ばずに、1ホストで両方の役割が同時に計測されます。

### WebRTCと同じファミリー

興味深い点が一つ — **本シリーズが扱うNAT越え技術は、WebRTC(ブラウザのビデオ会議)と同じ標準の上に立っている** という事実です。

| 技術 | 用途 |
|---|---|
| **STUN (RFC 8489)** | WebRTC通話時の自身の公的IP発見 / Tailscaleノードの外部アドレス発見 |
| **ICE (RFC 8445)** | WebRTC通話の候補収集 + 同時試行 / Tailscaleノードのconnection candidate |
| **TURN (RFC 8656)** | WebRTC通話のfallback relay / Tailscaleは同じポジションに自前のDERPを使用 |

つまりGoogle Meet・Zoom通話で2人のユーザーがNATを抜けてP2P映像ストリームを成立させるメカニズムと、 **本シリーズが釜山↔福岡のSSH・映像ストリームを成立させるメカニズムは、ほぼ同じIETF標準の上に立っている** わけです。メッシュVPNとビデオ会議が近い親戚だというインサイトです。

異なるのは **データプレーン** です — WebRTCはSRTP(メディア用)、TailscaleはWireGuard。しかしNAT越えのレイヤは同じ標準ファミリーを共有しています。

---

## MagicDNS — 短いホスト名が動く理由

本シリーズで `ssh samsung-home-laptop` の一行で釜山のノートPCに辿り着けるのはMagicDNSのおかげです。tailnetノードの **短いホスト名を100.64.x.xに自動マッピング** する機能です。

動作原理:

<div class="magic-dns" style="margin:1.5rem 0">
  <div class="md-flow">
    <div class="md-step">
      <div class="md-num">1</div>
      <div class="md-body">
        <strong>TailscaleクライアントがOSのDNSを横取りする</strong><br>
        クライアント起動時にOSのDNS設定へ自分自身をstub resolverとして登録 (Linux/macOSは `100.100.100.100` 、Windowsは別アダプタのDNS)。
      </div>
    </div>
    <div class="md-step">
      <div class="md-num">2</div>
      <div class="md-body">
        <strong>tailnetドメインのクエリは自分で処理</strong><br>
        <code>samsung-home-laptop</code> あるいは <code>samsung-home-laptop.tailba1ca3.ts.net</code> のようなクエリが来ると、クライアントがcontrol planeから受け取っておいたマッピングテーブルを参照して <code>100.64.88.55</code> を応答。
      </div>
    </div>
    <div class="md-step">
      <div class="md-num">3</div>
      <div class="md-body">
        <strong>一般のインターネットDNSはそのまま流す</strong><br>
        <code>naver.com</code> のようなクエリはOSが元々使っていたDNS(8.8.8.8、ISP DNSなど)へそのまま委任。グローバルnameserver利用時は <strong>DoH(DNS-over-HTTPS)</strong> で自動的に暗号化。
      </div>
    </div>
    <div class="md-step">
      <div class="md-num">4</div>
      <div class="md-body">
        <strong>検索ドメインの自動付与</strong><br>
        <code>ssh samsung-home-laptop</code> のように短い名前を打つと、OSが自動的に <code>.tailba1ca3.ts.net</code> を補ってクエリ — だから短い名前で届く。
      </div>
    </div>
  </div>
</div>
<style>
.magic-dns .md-flow{display:flex;flex-direction:column;gap:.6rem}
.magic-dns .md-step{display:flex;gap:.85rem;background:linear-gradient(135deg,#e3f2fd,#bbdefb);border-radius:11px;padding:.85rem .9rem;align-items:flex-start}
.magic-dns .md-num{flex:none;width:28px;height:28px;border-radius:50%;background:#1976d2;color:#fff;text-align:center;line-height:28px;font-size:13px;font-weight:700}
.magic-dns .md-body{font-size:13px;line-height:1.65;color:#0d47a1}
.magic-dns .md-body code{background:rgba(255,255,255,.65);padding:1px 5px;border-radius:4px;font-size:11.5px;font-family:'SF Mono',Consolas,monospace}
[data-mode="dark"] .magic-dns .md-step{background:linear-gradient(135deg,#0d2a4a,#10355a)}
[data-mode="dark"] .magic-dns .md-body{color:#90caf9}
[data-mode="dark"] .magic-dns .md-body code{background:rgba(255,255,255,.1);color:#e3f2fd}
</style>

要点は、 **TailscaleクライアントがOSのDNSを横取りしつつ一般トラフィックは流す** というsplit-horizon DNSモデルです。ユーザーは設定なしで `ssh samsung-home-laptop` と打てて、同時に普段のWebブラウジングにも影響しません。

> ### ちょっと待って、これだけ確認しておこう
>
> **「なぜmacOSの `host` / `nslookup` はMagicDNSを通らないのか」**
>
> macOSの一部CLIツール( `host`, `nslookup` )は **システムのDNS resolverを迂回して直接DNSサーバーにクエリを投げる** 構造のため、Tailscaleのstub resolverを経由しません。Tailscaleの公式ドキュメントもこの制約を明記しています。
>
> 通常のアプリ(ブラウザ・SSHクライアント・ `ping` )はシステムのresolverを経由するので正常に動作します。

---

## 動作原理のまとめ

ここまでが本シリーズインフラのあらゆる魔法がどう起こっているかの整理です。一枚にまとめると:

| メカニズム | 役割 | 無料プラン同梱 |
|---|---|---|
| LAN direct | 同一ネットワーク内で直通 | (該当なし) |
| STUN | NAT外部アドレス発見 (EIMでは十分) | ○ |
| UPnP-IGD / NAT-PMP / PCP | ルーターへの明示的ポートフォワーディング要求 | ○ |
| Hole punching | 両端が同時にoutboundでNATマッピングを生成 | ○ |
| Birthday paradox probe | EDM NAT越えのための確率的ポート探索 | ○ |
| **DERP relay** | 上記すべてが失敗した時のHTTPS上fallback (E2E維持) | ○ (28以上のグローバルリージョン) |
| **MagicDNS** | 短いホスト名をtailnet IPに解決 | ○ |
| **WireGuard** | 全通信のデータプレーン (Curve25519 + ChaCha20-Poly1305) | ○ |

この8つが **1つのクライアント内部で自動的に組み合わされて** 動作します。ユーザーは `tailscale up` の一行とadminコンソールでのexit node承認を一度行えばよいだけです。

---

# Part 2 — コスト・限界・振り返り

## 年間コストの分解

本シリーズが「0円インフラ」あるいは「年間1,100円インフラ」と呼んできたコストの実分解です。

<div class="cost-table" style="margin:1.5rem 0">
  <div class="ct-grid">
    <div class="ct-card ct-1">
      <div class="ct-num">~810</div>
      <div class="ct-unit">円/年</div>
      <div class="ct-name">電気代 (事実上すべて)</div>
      <div class="ct-detail">7W × 24h × 365日 = 61.32 kWh × 韓国家庭用累進1段 約13円/kWh</div>
    </div>
    <div class="ct-card ct-2">
      <div class="ct-num">0</div>
      <div class="ct-unit">円/年</div>
      <div class="ct-name">Tailscale</div>
      <div class="ct-detail">Personalプラン無料 (デバイス無制限)</div>
    </div>
    <div class="ct-card ct-3">
      <div class="ct-num">0</div>
      <div class="ct-unit">円/年</div>
      <div class="ct-name">インターネット回線</div>
      <div class="ct-detail">実家の家族がもとから使っているKT GiGA回線。追加コストなし</div>
    </div>
    <div class="ct-card ct-4">
      <div class="ct-num">0</div>
      <div class="ct-unit">円/年</div>
      <div class="ct-name">ハードウェア</div>
      <div class="ct-detail">7年物の物置ノートPC (Galaxy Book 950SBE) — 埋没コスト</div>
    </div>
  </div>
  <p class="ct-cap">合計: <strong>年間約800〜1,100円</strong>水準。ノートPCのバッテリー劣化は80%充電制限で緩和中。</p>
</div>
<style>
.cost-table .ct-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:.65rem}
.cost-table .ct-card{border-radius:11px;padding:.95rem .8rem;color:#fff;box-shadow:0 2px 8px rgba(0,0,0,.08);text-align:center}
.cost-table .ct-1{background:linear-gradient(135deg,#ef6c00,#e65100)}
.cost-table .ct-2{background:linear-gradient(135deg,#388e3c,#2e7d32)}
.cost-table .ct-3{background:linear-gradient(135deg,#1976d2,#1565c0)}
.cost-table .ct-4{background:linear-gradient(135deg,#7b1fa2,#6a1b9a)}
.cost-table .ct-num{font-size:26px;font-weight:800;font-family:'SF Mono',Consolas,monospace;letter-spacing:-.02em;line-height:1}
.cost-table .ct-unit{font-size:11px;font-weight:700;opacity:.85;margin:.2rem 0 .35rem;letter-spacing:.04em}
.cost-table .ct-name{font-size:12.5px;font-weight:700;margin-bottom:.3rem}
.cost-table .ct-detail{font-size:11px;opacity:.92;line-height:1.5}
.cost-table .ct-cap{text-align:center;margin-top:.7rem;font-size:12.5px;color:var(--text-muted-color,#888)}
@media(max-width:768px){.cost-table .ct-grid{grid-template-columns:1fr 1fr}}
</style>

比較として — **市販VPNサービスの一般的な価格** は月~550〜1,300円、年~6,600〜15,800円の水準です。つまり **本シリーズのインフラの年間コストは商用VPNの約5〜12%水準** ということになります。

他のセルフホストオプションと比べても優位は明らかです。

| オプション | 年間コスト | 限界 |
|---|---|---|
| **本シリーズ (物置ノートPC + Tailscale Free)** | 約800〜1,100円 | 韓国IPは1か所だけ |
| AWS Lightsail VPN ($3.50/mo, 韓国リージョン) | 約5,700円 | 韓国IPは取れるが、ゲーム・銀行の一部でデータセンターIPが遮断される事例あり |
| セルフホストOpenVPN (Lightsail + 自身の時間) | 約5,700円 + セットアップ・運用時間 | hub-and-spoke、NAT越え自動化なし |
| 韓国の家庭にRaspberry Pi 4を新規購入 + 運用 | 約8,800円 (Pi 4 + ケース + SD) + 電気 | 本シリーズと同じ結果だが新規ハード費用 |
| 市販の商用VPN (韓国サーバーオプション) | ~6,600〜15,800円 | 一部の韓国サイトは商用VPN IPを明示的に遮断 |

ただし、この比較には落とし穴があります。

- **比較対象が同一ではない** — 商用VPNはグローバルなサーバーを通じたIP回避が本質、本シリーズは韓国IP1か所のみという違いがあります。日本IPや米国IPが必要なら別途ノードが必要です。
- **時間コストが比較に入っていない** — 次の段で分けて見ます。
- **「学習の副産物」** — 実は本シリーズの最大の価値は韓国IP回避という結果よりも、 **NAT/DNS/SSH/PowerShell/SchTasksの実測練習** という副産物にあります。その面では時間投資も自分の学習コストとして回収されています。

### 時間コストの分解

自分の時間を考慮した正直な会計:

| 段階 | 所要時間 | 備考 |
|---|---|---|
| セットアップ (実家1回訪問) | 約4時間 | install.ps1の1回実行 + adminコンソール作業 + 検証 |
| シリーズ執筆 | 約40時間 (下記分解) | 本ブログシリーズ3編の累積執筆時間 |
| 日常運用 (月) | 約10分 | 自己修復が大半を処理、statusを一度確認する程度 |
| 障害対応 (現在まで) | 0時間 | 自己修復のトリガー0件 |

**シリーズ執筆時間 — 編・活動別の分解**

| 活動 | 第1編 (動機・実測・構造) | 第2編 (セットアップ・運用・セキュリティ) | 第3編 (動作原理・振り返り) | 合計 |
|---|---|---|---|---|
| 資料調査・検証 (RFC、Tailscale公式、Wikipedia) | 約3h | 約2h | 約5h | 約10h |
| 初稿作成 (韓国語本文) | 約4h | 約5h | 約5h | 約14h |
| 視覚化 (HTML/CSSダイアグラム) | 約3h | 約2h | 約3h | 約8h |
| 補強パス (外部資料追加、引用整合性) | 約2h | 約2h | 約3h | 約7h |
| **編ごと合計** | **約12h** | **約11h** | **約16h** | **約39h** |

第3編が最も長くなった理由 — **NAT分類・STUN・ICE・birthday paradoxといった動作原理は外部資料との整合性検証が他編より厄介** だからです。上の表は推定ですが、シリーズ全体が30〜40時間単位の作業だったという感覚は正確です。コード(install.ps1・setup-helpers.ps1・security-audit.ps1)を書く時間は別にかかっており、それは実家訪問とは別に福岡で累積した時間なので上の表からは分離してあります。

時間を時給¥3,000(便宜的に日本平均)で換算すると、セットアップ+シリーズ執筆が圧倒的に大きいです。しかしその時間は **NAT・DNS・Windows自動化・SchTasks・PowerShellの実測学習** として回収されており、シリーズの成果物自体が同じことをやろうとする他の人にとって節約される時間でもあります。

**つまり真のコスト比較は「韓国IPがどれくらいの頻度で必要か」に依存します**:

- **頻繁 (週5回以上)**: 本シリーズのセットアップが明確に優位
- **時々 (月1〜2回)**: 商用VPNが時間面で合理的
- **ほぼ使わない**: どちらも過剰

---

## 限界と未検証項目

本シリーズのインフラは万能ではありません。明示的に未検証の項目 + 既知の限界を整理します。

| 項目 | 状態 | 対応 |
|---|---|---|
| 停電後のノートPC自動ON | **未検証** — BIOSのAC Power Recovery設定に依存 | 実家直接訪問以外に検証手段なし |
| Wi-Fiパスワード変更 | **自動復旧不可** — 家族に新しいパスワードを伝えて再接続を依頼 | 多重化でも解決不可 |
| 30日以上の長期無人運用 | 未検証 (シリーズ執筆時点で約15時間しか測定していない) | 時間経過後に追加で振り返り |
| 韓国IP回避の実効性 (Linkkfなど) | 30秒のトラフィック測定のみ、実際のサイト別の遮断解除は未検証 | 福岡日常使用でケースごとに確認が必要 |
| 釜山実家の家族の不注意シナリオ | 実験不可 | 家族との事前案内で緩和 |
| 日本IP遮断サイトの回避 (逆方向) | 日本IP exit node未設置 | 福岡デスクトップをexit nodeとして広告すれば可能、未設定 |

最大の実リスクは **1行目の停電後の自動ON** — これが効かないと停電1回で実家訪問が強制されます。次回の実家訪問時にBIOSのAC Power Recoveryを明示的に有効化することが、補強項目としての次の最優先です。

---

## これからの6か月 / 1年ロードマップ

シリーズが終わったからといってインフラが終わったわけではありません。次段階として検討中の項目:

<div class="roadmap" style="margin:1.5rem 0">
  <div class="rm-grid">
    <div class="rm-card rm-1">
      <div class="rm-when">次回の実家訪問時</div>
      <div class="rm-name">BIOS AC Power Recoveryの有効化</div>
      <div class="rm-detail">停電後の自動ON動作を確認。上の限界表1番項目の直接解決。</div>
    </div>
    <div class="rm-card rm-2">
      <div class="rm-when">短期 (1〜2か月)</div>
      <div class="rm-name">福岡デスクトップを日本IPのexit nodeとして広告</div>
      <div class="rm-detail"><code>tailscale up --advertise-exit-node</code> の一行。日本で遮断される韓国サイト(逆方向)も回避可能。実家訪問なしに福岡側で即時可能。</div>
    </div>
    <div class="rm-card rm-3">
      <div class="rm-when">短期 (1〜2か月)</div>
      <div class="rm-name">ACL JSON定義による権限分離</div>
      <div class="rm-detail">第2編のACLパターンの適用。tag:exit-node + tag:client分類でssh ポリシーを明示化。deny-by-defaultで爆発半径を最小化。</div>
    </div>
    <div class="rm-card rm-4">
      <div class="rm-when">中期 (3〜6か月)</div>
      <div class="rm-name">subnet routerの試行 — 実家LANの他デバイスへのアクセス</div>
      <div class="rm-detail">実家の他デバイス(例: 親のPC、NAS)をTailscaleに直接合流させずとも、ノートPC経由で到達可能になる。<code>--advertise-routes=192.168.0.0/24</code>。</div>
    </div>
    <div class="rm-card rm-5">
      <div class="rm-when">長期 (6〜12か月)</div>
      <div class="rm-name">30日以上の長期無人運用データ収集 + 振り返り</div>
      <div class="rm-detail">現在は約15時間しか測定していない。metrics-collector.ps1が5分間隔で7か月分のデータを蓄積する予定 — その資料に基づく長期安定性パターンの分析。</div>
    </div>
    <div class="rm-card rm-6">
      <div class="rm-when">条件付き (シリーズ外)</div>
      <div class="rm-name">Headscaleセルフホストの検討</div>
      <div class="rm-detail">Tailscale社への依存を外したい場合のオプション。ただし調整サーバー運用の負担 + 無料DERPインフラ喪失というトレードオフがある。</div>
    </div>
  </div>
</div>
<style>
.roadmap .rm-grid{display:grid;grid-template-columns:1fr 1fr;gap:.7rem}
.roadmap .rm-card{border-radius:11px;padding:.95rem .9rem;background:linear-gradient(135deg,#e3f2fd,#bbdefb);color:#0d47a1;box-shadow:0 2px 8px rgba(0,0,0,.06)}
.roadmap .rm-when{font-size:11px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;background:rgba(25,118,210,.18);color:#0d47a1;padding:3px 8px;border-radius:10px;display:inline-block;margin-bottom:.5rem}
.roadmap .rm-name{font-size:13.5px;font-weight:800;margin-bottom:.4rem;line-height:1.4}
.roadmap .rm-detail{font-size:12px;line-height:1.6}
.roadmap .rm-detail code{background:rgba(255,255,255,.6);padding:1px 5px;border-radius:4px;font-size:11px;font-family:'SF Mono',Consolas,monospace}
[data-mode="dark"] .roadmap .rm-card{background:linear-gradient(135deg,#0d2a4a,#10355a);color:#90caf9}
[data-mode="dark"] .roadmap .rm-when{background:rgba(144,202,249,.15);color:#90caf9}
[data-mode="dark"] .roadmap .rm-detail code{background:rgba(255,255,255,.1);color:#e3f2fd}
@media(max-width:768px){.roadmap .rm-grid{grid-template-columns:1fr}}
</style>

この6項目のうち **1・2・3番が短期の優先順位** — 停電自動ON、日本IP exit node、ACLはいずれも効果の大きい作業です。4・5番は時間が作ってくれるデータに基づく振り返り、6番は会社依存自体を外したい場合にのみ意味のあるオプションです。

---

## シリーズ振り返り — 何を学んだか

最後にシリーズ全体の振り返りです。韓国IP回避インフラを作った成果物以上に、 **作る過程で学んだこと** の方が大きいです。

### 1. 無料SaaSと家庭環境の組み合わせ

Tailscaleの無料プランが **「個人ユーザーでも企業級インフラをそのまま使えるよう開放したもの」** だという点が最も興味深い発見です。6 user / デバイス無制限 / Exit Node・MagicDNS・ACLのすべてを含む — これが0円で可能なコスト構造の根拠(control/data planeの分離)は第1編で解いてあります。結果的に、釜山↔福岡のP2PメッシュVPNを **家庭NAT 2重の奥で、新規ハードウェアなしに、コスト1,100円以内で** 作れるというデモになりました。

### 2. 7年物の物置ノートPCも復活できる

Samsung Galaxy Book 950SBE (2018年発売、i7-8565U 15W TDP)が **無人24/7のexit nodeとして十分に動く** という事実が、本シリーズのもう一つの成果です。WireGuard capが約100〜200 Mbpsで家庭回線よりずっと速く、クラムシェルidleの7Wはデスクトップ100W+に対して一桁です。 **新しいハードウェアが要らないインフラ** という点がコストモデルの肝です。

### 3. Windows無人運用の落とし穴と回避策

Windows 11ノートPCを無人サーバーとして使うのは意外と厄介です — Modern Standbyの部分スリープ、Windows Updateの自動再起動、OpenSSHの administrators_authorized_keys のACL、PowerShellの `'""'` パスフレーズ落とし穴 — これらはすべてシリーズ執筆中にぶつかった実測です。それぞれの回避策は第2編にまとめてあり、同じことをしようとする他の人にそのまま役立ちます。

### 4. PowerShell権限分離パターン

Linuxの `sudo` のない環境で **「通常のSSHセッションは日常権限、権限昇格はSchTasks SYSTEM」** に分離するパターンが運用上きれいだという発見。日常SSHが管理者権限を持たないので事故面が小さく、権限昇格は検証済みスクリプト内でのみ起きるのでauditが容易です。このパターンはTailscaleとは無関係に、Windowsリモート運用一般に応用可能です。

### 5. 障害シナリオを先に書いておくと自動化が可能になる

`tailnet-ops/docs/recovery.md` に整理した6つのシナリオ(SSH不通 / 鍵紛失 / 停電 / Wi-Fi変更 / 鍵失効 / 自己修復破損)それぞれに復旧ツリーを用意しています。この文書を先に書いておいたことで、自己修復用のSchTasks 4種が自然と設計でき — **障害を想像することが自動化の出発点になる** という一般パターンの小さな事例になりました。

---

## シリーズ整理

| 編 | 核心 |
|---|---|
| [第1編 — 動機・実測・構造](/posts/tailscale-01-foundations/) | 福岡1年+の累積 / 稼働結果 (P2P 50ms, Tunnel DOWN 24.9 Mbps, 無人15h+) / Tailscale・WireGuard・メッシュVPNの構造 |
| [第2編 — セットアップ・無人運用・セキュリティ](/posts/tailscale-02-setup-and-ops/) | 実家1回訪問の5軸セットアップ / 自己修復4種SchTasks / 13項目のセキュリティチェック |
| 第3編 (本記事) | 動作原理 (NAT分類・STUN・ICE・hole punching・birthday paradox・DERP・MagicDNS) / 年間1,100円コスト分解 / 限界と振り返り |

3編まとめでシリーズが完結しました。韓国IP回避という結果そのものよりも、 **家庭NAT 2重と7年物の物置ノートPC、そして無料SaaSの組み合わせでどこまで行けるか** の小さなケーススタディとして残れば嬉しく思います。

---

## 参考資料

- [`Epheria/tailnet-ops`](https://github.com/Epheria/tailnet-ops) — 本シリーズの運用コード一式
- Pennarun, A. *How NAT traversal works.* Tailscale Blog. ([tailscale.com/blog/how-nat-traversal-works](https://tailscale.com/blog/how-nat-traversal-works))
- Tailscale. *How Tailscale works.* Tailscale Blog. ([tailscale.com/blog/how-tailscale-works](https://tailscale.com/blog/how-tailscale-works))
- Tailscale Docs. *MagicDNS.* ([tailscale.com/kb/1081/magicdns](https://tailscale.com/kb/1081/magicdns))
- Tailscale Docs. *DNS in Tailscale.* ([tailscale.com/kb/1054/dns](https://tailscale.com/kb/1054/dns))
- Tailscale. *Security overview.* ([tailscale.com/security](https://tailscale.com/security))
- IETF. *RFC 4787 — NAT Behavioral Requirements for Unicast UDP.* ([datatracker.ietf.org/doc/html/rfc4787](https://datatracker.ietf.org/doc/html/rfc4787))
- IETF. *RFC 8489 — Session Traversal Utilities for NAT (STUN).* (Obsoletes RFC 5389) ([datatracker.ietf.org/doc/html/rfc8489](https://datatracker.ietf.org/doc/html/rfc8489))
- IETF. *RFC 8445 — Interactive Connectivity Establishment (ICE).* ([datatracker.ietf.org/doc/html/rfc8445](https://datatracker.ietf.org/doc/html/rfc8445))
- IETF. *RFC 8656 — Traversal Using Relays around NAT (TURN).* ([datatracker.ietf.org/doc/html/rfc8656](https://datatracker.ietf.org/doc/html/rfc8656))
- IETF. *RFC 6886 — NAT Port Mapping Protocol (NAT-PMP).* ([datatracker.ietf.org/doc/html/rfc6886](https://datatracker.ietf.org/doc/html/rfc6886))
- IETF. *RFC 6887 — Port Control Protocol (PCP).* ([datatracker.ietf.org/doc/html/rfc6887](https://datatracker.ietf.org/doc/html/rfc6887))

> **シリーズ完結**。第1・2・3編すべてお読みいただきありがとうございました。
{: .prompt-info }
