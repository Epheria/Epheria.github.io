---
title: "Tailscale 시리즈 3편 — 작동 원리와 비용·한계 (DERP·MagicDNS·hole punching·연 1만 원 회고)"
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
  - Tailscale의 NAT 통과는 "전부 동시에 시도하고 가장 먼저 통하는 길" — STUN/ICE 표준 + UPnP/PMP/PCP 포트맵 + DERP fallback을 병렬 시도
  - Symmetric NAT(Hard NAT)는 birthday paradox로 통과 — 256개 포트 열고 무작위 probe, 2048회면 99.9% / ~20초
  - DERP는 P2P 실패 시 HTTPS 위에서 암호문 그대로 전달하는 fallback. E2E 보장 유지
  - MagicDNS는 100.100.100.100 stub resolver로 OS DNS를 가로채 짧은 호스트명을 100.64.x.x로 해석
  - 실제 비용 — 전기료 ~7,000원/년이 사실상 전부. 노트북·인터넷은 매몰 비용
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

## 이 편이 다루는 것

시리즈 마지막 편입니다. 두 가지를 묶습니다.

**Part 1 — 작동 원리**: 시리즈의 인프라가 가능한 메커니즘. 가정 NAT 두 겹 뒤의 노트북 두 대가 어떻게 직통으로 통신하는가. STUN·ICE·hole punching·DERP·MagicDNS를 한 묶음으로 정리합니다.

**Part 2 — 비용·한계·회고**: 연 1만 원 인프라의 실제 비용 분해, 검증 안 된 항목, 시리즈 전체 회고.

이 편 자체로도 읽을 수 있게 썼지만, 인프라가 무엇을 하는지의 큰 그림은 1·2편에 있습니다.

---

# Part 1 — 작동 원리

## 두 개의 NAT 분류 — 전통 vs 현대

NAT 통과를 이야기하려면 먼저 NAT의 종류를 짚어야 합니다. 흔히 들어본 분류는 1990년대 후반부터 쓰인 **cone 기반 4분류**입니다.

| 전통 분류 | 동작 |
|---|---|
| Full Cone | 외부 누구든지 NAT의 외부 포트로 보내면 내부로 전달됨 (가장 느슨) |
| Restricted Cone | 내부가 먼저 보낸 외부 IP에서만 들어올 수 있음 |
| Port-Restricted Cone | 내부가 먼저 보낸 외부 IP+port에서만 들어올 수 있음 |
| Symmetric | 목적지가 다르면 외부 포트도 다르게 매핑 (가장 빡빡) |

이 분류는 직관적이지만 실제 NAT 장비의 동작을 정확히 잡지 못한다는 비판이 있어, **RFC 4787**이 새 분류를 제시했고 Tailscale도 이쪽을 채택합니다.

> Tailscale의 표현 — "**Endpoint-Independent Mapping (EIM)**, and the hard variant **Endpoint-Dependent Mapping (EDM)**" ([How NAT traversal works](https://tailscale.com/blog/how-nat-traversal-works))

<div class="nat-class" style="margin:1.5rem 0">
  <div class="nc-grid">
    <div class="nc-card nc-eim">
      <div class="nc-tag">Easy NAT (EIM)</div>
      <div class="nc-key">Endpoint-Independent Mapping</div>
      <div class="nc-detail">목적지가 어디든 같은 외부 port를 재사용. STUN으로 한 번 발견하면 다른 피어와도 그 port가 통한다.</div>
      <div class="nc-foot">대부분의 가정 라우터</div>
    </div>
    <div class="nc-card nc-edm">
      <div class="nc-tag">Hard NAT (EDM)</div>
      <div class="nc-key">Endpoint-Dependent Mapping</div>
      <div class="nc-detail">목적지마다 다른 외부 port 부여. STUN으로 발견한 port는 STUN 서버 전용이고 다른 피어와는 다른 port를 또 찾아야 한다.</div>
      <div class="nc-foot">일부 ISP의 CGNAT, 기업 NAT</div>
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

이 분류가 중요한 이유 — **"양쪽 다 EIM이면 hole punching이 비교적 쉽고, 한쪽이라도 EDM이면 어렵다"**가 NAT 통과 전략의 첫 분기점이기 때문입니다. 본 시리즈의 부산 KT 라우터와 후쿠오카 가정 라우터는 모두 EIM 계열로 잡혀있어 P2P direct가 별 어려움 없이 성립합니다(1편의 측정 기준).

---

## STUN — "내가 인터넷에서 어떻게 보이는가"

STUN(Session Traversal Utilities for NAT)은 한 줄로 요약하면 **"외부 STUN 서버에 패킷을 쏴서, 그 서버가 본 자기 외부 IP·port를 돌려받는 프로토콜"** 입니다.

> ### 잠깐, 이건 짚고 넘어가자
>
> **"STUN의 RFC 번호는 5389가 아니라 8489다"**
>
> 인터넷의 오래된 자료 다수가 STUN을 **RFC 5389**로 인용하지만, 2020년 2월 발행된 **RFC 8489가 5389를 obsolete**(폐기)했습니다. 즉 8489가 현재 표준입니다.
>
> 8489의 주요 변경점:
> - **MESSAGE-INTEGRITY-SHA256** 속성 추가 — MD5 기반 인증 외 SHA-256 옵션
> - **USERHASH** 속성으로 사용자명 익명화 가능
> - **PASSWORD-ALGORITHM** 속성으로 비밀번호 보호 알고리즘 선택 가능
> - **nonce cookie** 메커니즘으로 비드다운(bid-down) 공격 방어
>
> 본 시리즈 본문은 RFC 8489 표기를 따릅니다.

> Tailscale 표현 — "Your machine sends a 'what's my endpoint from your point of view?' request to a STUN server, and the server replies with 'here's the ip:port that I saw your UDP packet coming from.'"

<div class="stun-flow" style="margin:1.5rem 0">
  <div class="sf-row">
    <div class="sf-step">
      <div class="sf-num">1</div>
      <div class="sf-text"><strong>OUT</strong> 노드가 사설 IP <code>192.168.0.10:54321</code>에서 STUN 서버 <code>X.X.X.X:3478</code>로 UDP 패킷 발송</div>
    </div>
    <div class="sf-step">
      <div class="sf-num">2</div>
      <div class="sf-text"><strong>NAT</strong> 가정 라우터가 <code>192.168.0.10:54321 ↔ public:62000</code> 매핑 생성</div>
    </div>
    <div class="sf-step">
      <div class="sf-num">3</div>
      <div class="sf-text"><strong>STUN</strong> 서버가 "너는 <code>public:62000</code>에서 왔다"고 응답</div>
    </div>
    <div class="sf-step">
      <div class="sf-num">4</div>
      <div class="sf-text"><strong>SHARE</strong> 노드가 <code>public:62000</code>을 control plane을 통해 피어에게 알림</div>
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

핵심 제약은 STUN 발견 결과를 **그 socket으로만 써야 한다**는 점입니다 — 다른 socket을 쓰면 NAT가 다른 매핑을 만들어버려 발견한 port가 무용지물이 됩니다. 그래서 Tailscale은 "통신에 쓸 socket으로 STUN 패킷을 직접 쏘는" 패턴을 따릅니다.

EIM NAT에서는 이걸로 끝입니다 — 발견한 `public:62000`이 다른 피어와도 그대로 통합니다. EDM NAT에서는 별 도움이 안 됩니다 — 다음 섹션의 birthday paradox로 넘어가야 합니다.

---

## ICE — "전부 동시에 시도하기"

ICE(Interactive Connectivity Establishment, RFC 8445)는 **여러 candidate(연결 후보 주소)를 동시에 모아서 전부 시도하고, 가장 먼저 응답이 돌아온 경로를 채택**하는 알고리즘입니다.

Tailscale이 한 노드에 대해 동시에 시도하는 candidate는 다음 5가지입니다(공식 블로그).

<div class="candidates" style="margin:1.5rem 0">
  <div class="cd-grid">
    <div class="cd-card cd-1">
      <div class="cd-num">1</div>
      <div class="cd-name">LAN 주소</div>
      <div class="cd-detail">같은 네트워크면 직접 통신. NAT 통과 불필요.</div>
    </div>
    <div class="cd-card cd-2">
      <div class="cd-num">2</div>
      <div class="cd-name">STUN WAN 주소</div>
      <div class="cd-detail">EIM NAT에서 STUN으로 발견한 public:port</div>
    </div>
    <div class="cd-card cd-3">
      <div class="cd-num">3</div>
      <div class="cd-name">포트맵 주소</div>
      <div class="cd-detail">UPnP-IGD / NAT-PMP / PCP로 라우터에 명시적 포워딩 요청</div>
    </div>
    <div class="cd-card cd-4">
      <div class="cd-num">4</div>
      <div class="cd-name">NAT64 경로</div>
      <div class="cd-detail">IPv6-only 환경 전용</div>
    </div>
    <div class="cd-card cd-5">
      <div class="cd-num">5</div>
      <div class="cd-name">DERP relay</div>
      <div class="cd-detail">다른 4개가 실패해도 동작. <strong>항상 preselected</strong> — 첫 패킷부터 DERP로 통신 시작, 빠른 경로 발견 시 즉시 업그레이드. UDP가 막힌 환경에서도 보장.</div>
    </div>
  </div>
  <p class="cd-cap">Tailscale은 round-trip latency 기준으로 가장 빠른 경로를 선택하고, 더 좋은 경로가 발견되면 즉시 업그레이드한다.</p>
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

이 모델의 핵심은 **"all connections start out with DERP preselected"** — 모든 연결이 시작 시점에는 DERP를 통해 흐르고 있고, 더 좋은 경로(LAN/STUN/포트맵)가 발견되면 그 시점에 데이터 평면을 즉시 업그레이드합니다. 즉 NAT 통과가 늦어져도 **첫 패킷부터 통신은 시작**됩니다.

> Avery Pennarun의 한 줄 요약 — "**try everything at once, and pick the best thing that works**"

---

## Hole Punching — 두 피어가 동시에 outbound

대부분의 가정 NAT(EIM)는 "내부에서 먼저 외부로 패킷을 보낸 적이 있는 외부 IP·port에서 들어오는 inbound는 허용"하는 방화벽 동작을 보입니다(stateful firewall). 이 동작이 hole punching의 단서입니다.

<div class="hole-punch" style="margin:1.5rem 0">
  <div class="hp-row">
    <div class="hp-side">
      <div class="hp-tag">Peer A (NAT 뒤)</div>
      <div class="hp-box">
        <div class="hp-line">1. control plane으로부터 B의 public 주소 받음</div>
        <div class="hp-line">2. B로 outbound UDP 패킷 발송</div>
        <div class="hp-line">3. NAT가 매핑 생성, 자기 방화벽도 B의 응답 허용</div>
      </div>
    </div>
    <div class="hp-mid">
      <div class="hp-arrow">⟷</div>
      <div class="hp-arrow-text">동시</div>
    </div>
    <div class="hp-side">
      <div class="hp-tag">Peer B (NAT 뒤)</div>
      <div class="hp-box">
        <div class="hp-line">1. control plane으로부터 A의 public 주소 받음</div>
        <div class="hp-line">2. A로 outbound UDP 패킷 발송</div>
        <div class="hp-line">3. NAT가 매핑 생성, 자기 방화벽도 A의 응답 허용</div>
      </div>
    </div>
  </div>
  <p class="hp-cap">"packets must flow out before packets can flow back in" — Tailscale의 hole punching 원리</p>
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

이 과정에서 **첫 outbound 패킷은 상대방의 NAT에서 거부**됩니다(아직 매핑이 없으니 도착 못 함). 그러나 그 거부된 패킷이 자기 NAT에는 매핑을 만들어두고, 곧이어 상대방이 보내는 outbound 패킷이 우리 NAT에 도착할 때 **방화벽이 "이건 우리가 먼저 보낸 곳에서 오는 응답"으로 인식**해서 통과시킵니다.

이후 양쪽이 30초마다 keep-alive ping을 주고받으며 NAT 매핑을 유지합니다 — 일반적인 가정 NAT가 무통신 30초~수 분이면 매핑을 만료시키기 때문입니다.

---

## Symmetric NAT와 Birthday Paradox

EDM NAT(Hard NAT)는 위 hole punching이 **단순히는 안 통합니다** — 각 목적지마다 다른 외부 port를 부여하므로, control plane이 알려준 port와 실제 상대방이 받게 될 port가 다릅니다.

해결은 **확률에 의존**합니다. 한쪽이 256개 port를 동시에 열어두고, 상대방이 그 256개 중 어딘가에 무작위로 probe를 던집니다. 일치(birthday collision)가 일어나면 hole이 뚫립니다.

<div class="bday" style="margin:1.5rem 0">
  <div class="bd-table-wrap">
    <table class="bd-table">
      <thead><tr><th>Probe 횟수</th><th>성공 확률</th><th>소요 시간 (100 pkt/s)</th></tr></thead>
      <tbody>
        <tr><td>174</td><td>50%</td><td>1.7s</td></tr>
        <tr><td>256</td><td>64%</td><td>2.6s</td></tr>
        <tr><td>1,024</td><td>98%</td><td>10s</td></tr>
        <tr class="bd-hl"><td>2,048</td><td>99.9%</td><td>~20s</td></tr>
      </tbody>
    </table>
  </div>
  <p class="bd-cap">Tailscale 공식 수치. 256 port 풀에서 무작위 probe 시 성공 확률.</p>
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

수학적으로 보면: 가능한 port 공간이 65,535이고 한쪽이 256개를 열었을 때, 무작위 probe 한 번이 그중 하나에 맞을 확률은 256/65,535 ≈ 0.39%. 1 - (1 - 256/65535)^N 이 확률이 N=2,048에서 0.999를 넘습니다 (`birthday paradox`라고 부르는 이유는 √N 효과로 검색 공간이 제곱근으로 줄기 때문 — 선형이 아니라).

100 패킷/초 송신 기준으로 2,048 probe = 약 20초. 실측에서는 절반 이상이 2초 안에 통과한다고 Tailscale이 보고합니다.

> Tailscale의 실측 — "half the time we'll get through in under 2 seconds" (How NAT traversal works)

**더 어려운 케이스 — 양쪽 다 EDM**: 검색 공간이 곱해져 99.9% 도달에 약 28분이 걸립니다(170,000 probes / 100 pkt/s). 양쪽 다 EDM인 케이스에서는 사실상 DERP fallback으로 떨어집니다.

본 시리즈 시나리오에서는 부산 KT 라우터가 EIM, 후쿠오카 가정 라우터도 EIM이라 birthday paradox가 발동할 일이 없습니다 — STUN 한 번에 끝납니다.

---

## DERP — 마지막 안전망

P2P direct가 모두 실패하면 **DERP(Designated Encrypted Relay for Packets)** 가 fallback으로 작동합니다. DERP의 특이성을 표로 정리합니다.

| 측면 | DERP의 동작 |
|---|---|
| 프로토콜 | **HTTPS 위 (TCP/443)** — UDP 차단 환경도 통과 |
| 데이터 처리 | **암호화된 패킷 그대로 전달** — 복호화 불가 (E2E 보장 유지) |
| 노드 측 키 | DERP 서버에는 **개인 키 미전송** — 노드 안에만 존재 |
| TURN과의 관계 | "DERP는 TURN과 같은 역할이지만 HTTPS 스트림 + WireGuard 키 사용" |
| 글로벌 인프라 | Tailscale이 28개+ 리전에서 운영, **Personal 무료 플랜에 포함** |
| 시작 시 동작 | **"항상 DERP가 preselected"** — 첫 패킷부터 통신 시작 |

DERP가 **TCP/443 (HTTPS)** 위에 동작한다는 점이 운영적으로 중요합니다 — UDP가 막혀있는 카페·호텔·기업 네트워크에서도 Tailscale이 동작하는 이유입니다. 도메인은 일반 HTTPS 트래픽처럼 보이고, 패킷 안은 이미 WireGuard로 암호화되어 있어 중간자가 볼 수 없습니다.

> Tailscale 표현 — "Your traffic remains end-to-end encrypted when it passes through a relay server."

### TURN vs DERP — 무엇이 같고 무엇이 다른가

DERP는 IETF 표준 **TURN(Traversal Using Relays around NAT, RFC 8656)** 의 같은 자리를 차지하지만, 구현은 다릅니다. 비교 표:

| 측면 | TURN (RFC 8656) | Tailscale DERP |
|---|---|---|
| 표준화 | IETF 표준 | Tailscale 자체 구현 (오픈소스) |
| 트랜스포트 | UDP / TCP / TLS | **HTTPS (TCP/443)** 전용 |
| 인증 | TURN 자격증명 (username/credential) | WireGuard 키 |
| 데이터 평면 | 암호문/평문 모두 가능 | **암호문만 (E2E 보장)** |
| 일반적 용도 | WebRTC 화상회의 fallback | 메시 VPN 노드 간 fallback |
| 운영 비용 | 별도 TURN 서버 필요 | Tailscale 글로벌 인프라 (무료 플랜 포함) |

**핵심 차이는 "TLS 위 HTTPS 전용"**이라는 결정입니다. TURN은 UDP·TCP 모두 쓰지만 일부 기업 방화벽은 TURN의 표준 포트(3478, 5349)를 알아채고 차단할 수 있는 반면, DERP는 **일반 웹 트래픽과 구분 불가능한 HTTPS** 위에 있어서 거의 모든 환경에서 통과합니다. 카페·호텔·공항 Wi-Fi에서도 동작이 보장되는 이유.

> ### 잠깐, 이건 짚고 넘어가자
>
> **"DERP 서버는 사실 STUN responder도 겸한다 — 한 호스트에서 두 역할 동시에"**
>
> 위에서 STUN과 DERP를 별도 메커니즘으로 다뤘지만, 운영 측면에선 둘이 거의 같은 인프라 위에 있습니다 — Tailscale의 글로벌 DERP 노드는 **HTTPS relay와 STUN responder를 한 호스트에서 같이 제공**합니다. 같은 노드 host가 TCP/443(HTTPS) 위 DERP relay로도 응답하고, UDP/3478(STUN)으로도 응답합니다.
>
> 즉 "Tokyo 리전에 DERP 노드 한 대를 두면" — (a) UDP가 통하는 환경에서는 그 노드가 **STUN으로 외부 IP·port 발견**을 도와 P2P direct를 성립시키고, (b) UDP가 막힌 환경에서는 그 노드가 **HTTPS relay로 fallback**을 받아냅니다. 한 노드가 두 역할을 동시에 처리하는 구조가 글로벌 DERP 인프라 비용을 일정 수준에 묶어두는 근거 중 하나입니다.
>
> 본 시리즈 1편의 `tailscale netcheck`가 28개 리전 모든 DERP에 대해 RTT를 한 번에 측정한 것도 같은 이유 — STUN과 DERP에 별도 endpoint를 호출하지 않고 한 host에서 두 역할이 같이 측정됩니다.

### WebRTC와 같은 가족

흥미로운 점 하나 — **본 시리즈가 다루는 NAT 통과 기술이 WebRTC(브라우저 화상회의)와 같은 표준 위에 서있다**는 사실입니다.

| 기술 | 용도 |
|---|---|
| **STUN (RFC 8489)** | WebRTC 통화 시 자기 공인 IP 발견 / Tailscale 노드의 외부 주소 발견 |
| **ICE (RFC 8445)** | WebRTC 통화 후보 수집 + 동시 시도 / Tailscale 노드의 connection candidate |
| **TURN (RFC 8656)** | WebRTC 통화 fallback relay / Tailscale은 같은 자리에 자체 DERP 사용 |

즉 Google Meet·Zoom 통화에서 두 사용자가 NAT을 뚫고 P2P 영상 스트림을 만드는 메커니즘과, **본 시리즈가 부산↔후쿠오카 SSH·영상 스트림을 만드는 메커니즘이 거의 동일한 IETF 표준 위에 서있습니다**. 메시 VPN과 화상회의가 가까운 친척이라는 인사이트.

다른 점은 **데이터 평면**입니다 — WebRTC는 SRTP(미디어용), Tailscale은 WireGuard. 하지만 NAT 통과 layer는 같은 표준 가족을 공유합니다.

---

## MagicDNS — 짧은 호스트명이 동작하는 이유

본 시리즈가 `ssh samsung-home-laptop` 한 줄로 부산 노트북에 닿을 수 있는 이유가 MagicDNS입니다. tailnet 노드의 **짧은 호스트명을 100.64.x.x로 자동 매핑**하는 기능입니다.

작동 원리:

<div class="magic-dns" style="margin:1.5rem 0">
  <div class="md-flow">
    <div class="md-step">
      <div class="md-num">1</div>
      <div class="md-body">
        <strong>Tailscale 클라이언트가 OS의 DNS를 가로챈다</strong><br>
        클라이언트가 시작될 때 OS의 DNS 설정에 자기 자신을 stub resolver로 등록 (Linux/macOS는 `100.100.100.100`, Windows는 별도 어댑터의 DNS).
      </div>
    </div>
    <div class="md-step">
      <div class="md-num">2</div>
      <div class="md-body">
        <strong>tailnet 도메인 쿼리는 자기가 처리</strong><br>
        <code>samsung-home-laptop</code> 또는 <code>samsung-home-laptop.tailba1ca3.ts.net</code> 같은 쿼리가 들어오면, 클라이언트가 control plane에서 받아둔 매핑 테이블을 보고 <code>100.64.88.55</code> 응답.
      </div>
    </div>
    <div class="md-step">
      <div class="md-num">3</div>
      <div class="md-body">
        <strong>일반 인터넷 DNS는 그대로 흘려보냄</strong><br>
        <code>naver.com</code> 같은 쿼리는 OS가 원래 쓰던 DNS(8.8.8.8, ISP DNS 등)로 그대로 위임. 글로벌 nameserver 사용 시에는 <strong>DoH(DNS-over-HTTPS)</strong>로 자동 암호화.
      </div>
    </div>
    <div class="md-step">
      <div class="md-num">4</div>
      <div class="md-body">
        <strong>검색 도메인 자동 추가</strong><br>
        <code>ssh samsung-home-laptop</code> 같이 짧은 이름을 치면 OS가 자동으로 <code>.tailba1ca3.ts.net</code>을 붙여서 쿼리 — 그래서 짧은 이름으로 닿는다.
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

핵심은 **Tailscale 클라이언트가 OS의 DNS를 가로채되 일반 트래픽은 흘려보낸다**는 split-horizon DNS 모델입니다. 사용자는 별도 설정 없이 `ssh samsung-home-laptop`을 칠 수 있고, 동시에 일반 웹 브라우징도 영향받지 않습니다.

> ### 잠깐, 이건 짚고 넘어가자
>
> **"왜 macOS의 `host` / `nslookup`은 MagicDNS에 안 잡혀?"**
>
> macOS의 일부 CLI 도구(`host`, `nslookup`)는 **시스템 DNS resolver를 우회하고 직접 DNS 서버에 쿼리**를 던지는 구조라서 Tailscale의 stub resolver를 통과하지 않습니다. Tailscale 공식 문서가 이 한계를 명시합니다.
>
> 일반 앱(브라우저·SSH 클라이언트·`ping`)은 시스템 resolver를 거치므로 정상 동작합니다.

---

## 작동 원리 정리

여기까지가 본 시리즈 인프라의 모든 마법이 어떻게 일어나는지의 정리입니다. 한 컷으로 묶으면:

| 메커니즘 | 역할 | 무료 플랜 포함 여부 |
|---|---|---|
| LAN direct | 같은 네트워크 직통 | (해당 없음) |
| STUN | NAT 외부 주소 발견 (EIM에서 충분) | ○ |
| UPnP-IGD / NAT-PMP / PCP | 라우터에 명시적 포트 포워딩 요청 | ○ |
| Hole punching | 양쪽이 동시에 outbound로 NAT 매핑 동시 생성 | ○ |
| Birthday paradox probe | EDM NAT 통과를 위한 확률적 port 탐색 | ○ |
| **DERP relay** | 위 모두 실패 시 HTTPS 위 fallback (E2E 유지) | ○ (28개+ 글로벌 리전) |
| **MagicDNS** | 짧은 호스트명을 tailnet IP로 해석 | ○ |
| **WireGuard** | 모든 통신의 데이터 평면 (Curve25519 + ChaCha20-Poly1305) | ○ |

이 8가지가 한 클라이언트 안에서 동시에 동작하지만, 역할이 같지 않습니다. **데이터 평면(WireGuard)이 모든 통신의 기반**이고 나머지 7개는 모두 "WireGuard 패킷이 어디로 가야 하는가"를 푸는 도구입니다. 그중 **DERP는 다른 모두가 실패해도 첫 패킷부터 통신을 시작**시키는 안전망 — 별도 모드가 따로 있는 게 아니라 **모든 연결이 시작 시점에 DERP로 흐르고**, 더 빠른 경로(LAN/STUN/포트맵/hole punching)가 발견되면 그 시점에 데이터 평면을 즉시 업그레이드합니다.

흔한 오해 하나 — "P2P direct가 안 되면 Tailscale은 못 쓴다"가 아닙니다. 본 시리즈는 양쪽 라우터가 모두 EIM이라 P2P가 잡혔지만, 양쪽 다 EDM이라 birthday paradox가 28분 걸리는 환경에서도 DERP relay로 통신은 그대로 가능합니다(속도만 떨어짐).

사용자 입장에서는 `tailscale up` 한 줄과 admin 콘솔의 exit node 승인 한 번이지만, 그 한 줄 뒤에서 8개 도구가 경쟁·협력하고 있다는 점이 본 시리즈가 풀고 싶었던 그림입니다.

---

# Part 2 — 비용·한계·회고

## 연 비용 분해

본 시리즈가 "0원 인프라" 또는 "연 1만 원 인프라"라고 묘사한 비용의 실제 분해입니다.

<div class="cost-table" style="margin:1.5rem 0">
  <div class="ct-grid">
    <div class="ct-card ct-1">
      <div class="ct-num">~7,360</div>
      <div class="ct-unit">원/년</div>
      <div class="ct-name">전기료 (사실상 전부)</div>
      <div class="ct-detail">7W × 24h × 365일 = 61.32 kWh × 한국 가정용 누진 1단계 ~120원/kWh</div>
    </div>
    <div class="ct-card ct-2">
      <div class="ct-num">0</div>
      <div class="ct-unit">원/년</div>
      <div class="ct-name">Tailscale</div>
      <div class="ct-detail">Personal 플랜 무료 (디바이스 무제한)</div>
    </div>
    <div class="ct-card ct-3">
      <div class="ct-num">0</div>
      <div class="ct-unit">원/년</div>
      <div class="ct-name">인터넷 회선</div>
      <div class="ct-detail">본가 가족이 어차피 쓰는 KT GiGA 회선. 추가 비용 없음</div>
    </div>
    <div class="ct-card ct-4">
      <div class="ct-num">0</div>
      <div class="ct-unit">원/년</div>
      <div class="ct-name">하드웨어</div>
      <div class="ct-detail">7년 묵은 창고 노트북 (Galaxy Book 950SBE) — 매몰 비용</div>
    </div>
  </div>
  <p class="ct-cap">합계: <strong>연 7,000원~1만 원</strong> 수준. 노트북 배터리 노화는 80% 충전 제한으로 완화 중.</p>
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

비교 — **시중 한국 VPN 서비스의 일반적인 가격**은 월 5,000~12,000원, 연 60,000~144,000원 수준입니다. 즉 **본 시리즈 인프라의 연 비용은 상용 VPN의 약 5~12% 수준**입니다.

다른 자가 호스트 옵션과 비교해도 우위가 명확합니다.

| 옵션 | 연 비용 | 한계 |
|---|---|---|
| **본 시리즈 (창고 노트북 + Tailscale Free)** | ~7,000~10,000원 | 한국 IP 한 군데만 |
| AWS Lightsail VPN ($3.50/mo, 한국 리전) | ~52,000원 | 한국 IP는 잡히지만 게임·은행 일부에서 데이터센터 IP 차단 사례 있음 |
| 자가 호스트 OpenVPN (Lightsail + 본인 시간) | ~52,000원 + 셋업·운영 시간 | hub-and-spoke, NAT 통과 자동화 없음 |
| 한국 가정에 라즈베리 파이 4 신규 구매 + 운영 | ~80,000원 (Pi 4 + 케이스 + SD) + 전기 | 본 시리즈와 같은 결과지만 새 하드웨어 비용 |
| 시중 상용 VPN (한국 서버 옵션) | 60,000~144,000원 | 일부 한국 사이트는 상용 VPN IP를 명시적 차단 |

다만 이 비교에는 함정이 있습니다.

- **비교 대상이 같지 않다** — 상용 VPN은 글로벌 서버를 통한 IP 우회가 본질이고, 본 시리즈는 한국 IP 한 군데만 내준다는 점이 다릅니다. 일본 IP나 미국 IP가 필요하면 별도 노드가 필요합니다.
- **시간 비용이 비교에 포함 안 됨** — 다음 단락에서 분리해서 봅니다.
- **"공부의 부산물"** — 사실 본 시리즈의 가장 큰 가치는 한국 IP 우회라는 결과보다 **NAT/DNS/SSH/PowerShell/SchTasks의 실측 연습**이라는 부산물입니다. 그 측면에서는 시간 투자도 자기 학습 비용으로 회수됩니다.

### 시간 비용 분해

자기 시간을 고려한 솔직한 회계:

| 단계 | 소요 시간 | 비고 |
|---|---|---|
| 셋업 (본가 1회 방문) | ~4시간 | install.ps1 한 번 + admin 콘솔 작업 + 검증 |
| 시리즈 작성 | ~40시간 (아래 분해) | 본 블로그 시리즈 3편의 누적 작성 시간 |
| 일상 운영 (월) | ~10분 | 자가치유가 대부분 처리, status 한 번 확인 정도 |
| 사고 대응 (현재까지) | 0시간 | 자가치유 트리거 0건 |

**시리즈 작성 시간 — 편·활동별 분해**

| 활동 | 1편 (동기·실측·구조) | 2편 (셋업·운영·보안) | 3편 (작동 원리·회고) | 합계 |
|---|---|---|---|---|
| 자료조사·검증 (RFC, Tailscale 공식, Wikipedia) | ~3h | ~2h | ~5h | ~10h |
| 초안 작성 (한국어 본문) | ~4h | ~5h | ~5h | ~14h |
| 시각화 (HTML/CSS 다이어그램) | ~3h | ~2h | ~3h | ~8h |
| 보강 패스 (외부 자료 추가, 인용 정합성) | ~2h | ~2h | ~3h | ~7h |
| **편당 합계** | **~12h** | **~11h** | **~16h** | **~39h** |

3편이 가장 길어진 이유 — **NAT 분류·STUN·ICE·birthday paradox 같은 작동 원리는 외부 자료 정합성 검증이 다른 편보다 까다롭다**는 점입니다. 위 표는 추정이지만 시리즈 전체가 30~40시간 단위 작업이었다는 감각은 정확합니다. 코드(install.ps1·setup-helpers.ps1·security-audit.ps1)를 짜는 시간은 별도로 들었고 그건 본가 방문 외 후쿠오카에서 누적된 시간이라 위 표에서는 분리해 두었습니다.

시간을 시급 ¥3,000(편의상 일본 평균)으로 환산하면 셋업+시리즈 작성이 압도적으로 큽니다. 그러나 그 시간은 **NAT·DNS·Windows 자동화·SchTasks·PowerShell의 실측 학습**으로 회수되었고, 시리즈 결과물 자체가 같은 일을 하려는 다른 사람에게 절약되는 시간입니다.

**즉 진짜 비용 비교는 "한국 IP가 얼마나 자주 필요한가"에 달려있습니다**:

- **자주 (주 5회+)**: 본 시리즈 셋업이 명확히 우위
- **가끔 (월 1~2회)**: 상용 VPN이 시간 측면에서 합리적
- **거의 안 씀**: 둘 다 과잉

---

## 한계와 검증 안 된 항목

본 시리즈의 인프라가 만능은 아닙니다. 명시적으로 검증되지 않은 항목 + 알려진 한계를 정리합니다.

| 항목 | 상태 | 대응 |
|---|---|---|
| 정전 후 노트북 자동 ON | **검증 안 됨** — BIOS의 AC Power Recovery 설정에 의존 | 본가 직접 방문 외 검증법 없음 |
| Wi-Fi 비밀번호 변경 | **자동 복구 불가** — 가족에게 새 비번 안내해서 재연결 요청 | 다중화로도 해결 안 됨 |
| 30일+ 장기 무인 운영 | 미검증 (시리즈 작성 시점 기준 ~15시간만 측정) | 시간 경과 후 추후 회고 |
| 한국 IP 우회 실효성 (Linkkf 등) | 30초 트래픽 측정만 됨, 실제 사이트별 차단 풀림은 미검증 | 후쿠오카 일상 사용에서 케이스별 확인 필요 |
| 부산 본가 가족 부주의 시나리오 | 실험 불가 | 가족과의 사전 안내로 완화 |
| 일본 IP 차단 사이트 우회 (반대 방향) | 일본 IP exit node 미설치 | 후쿠오카 데스크톱을 exit node로 광고하면 가능, 미설정 |

가장 큰 실제 리스크는 **첫째 줄 정전 후 자동 ON** — 이게 안 되면 정전 한 번에 본가 방문이 강제됩니다. 다음번 본가 방문 시 BIOS의 AC Power Recovery를 명시적으로 활성화하는 게 다음 1순위 보강 항목입니다.

---

## 다음 6개월 / 1년 로드맵

본 시리즈가 끝났다고 인프라가 끝난 건 아닙니다. 다음 단계로 검토 중인 항목들:

<div class="roadmap" style="margin:1.5rem 0">
  <div class="rm-grid">
    <div class="rm-card rm-1">
      <div class="rm-when">다음 본가 방문 시</div>
      <div class="rm-name">BIOS AC Power Recovery 활성화</div>
      <div class="rm-detail">정전 후 자동 ON 동작 확인. 위 한계 표 1번 항목의 직접 해결.</div>
    </div>
    <div class="rm-card rm-2">
      <div class="rm-when">단기 (1~2개월)</div>
      <div class="rm-name">후쿠오카 데스크톱을 일본 IP exit node로 광고</div>
      <div class="rm-detail"><code>tailscale up --advertise-exit-node</code> 한 줄. 일본에서 차단되는 한국 사이트(반대 방향)도 우회 가능. 본가 방문 없이 후쿠오카에서 즉시 가능.</div>
    </div>
    <div class="rm-card rm-3">
      <div class="rm-when">단기 (1~2개월)</div>
      <div class="rm-name">ACL JSON 정의로 권한 분리</div>
      <div class="rm-detail">2편의 ACL 패턴 적용. tag:exit-node + tag:client 분류로 ssh 정책 명시화. deny-by-default로 폭발 반경 최소화.</div>
    </div>
    <div class="rm-card rm-4">
      <div class="rm-when">중기 (3~6개월)</div>
      <div class="rm-name">subnet router 시도 — 본가 LAN의 다른 디바이스 접근</div>
      <div class="rm-detail">본가의 다른 디바이스(예: 부모 PC, NAS)를 Tailscale에 직접 합류시키지 않고도 노트북 경유로 접근 가능. <code>--advertise-routes=192.168.0.0/24</code>.</div>
    </div>
    <div class="rm-card rm-5">
      <div class="rm-when">장기 (6~12개월)</div>
      <div class="rm-name">30일+ 장기 무인 운영 데이터 수집 + 회고</div>
      <div class="rm-detail">현재 ~15시간만 측정됨. metrics-collector.ps1이 5분 주기로 7개월치 데이터를 누적할 예정 — 그 자료 기반으로 장기 안정성 패턴 분석.</div>
    </div>
    <div class="rm-card rm-6">
      <div class="rm-when">조건부 (시리즈 외)</div>
      <div class="rm-name">Headscale 자가 호스트 검토</div>
      <div class="rm-detail">Tailscale 회사 의존을 빼고 싶은 경우 옵션. 단 조정 서버 운영 부담 + 무료 DERP 인프라 손실 트레이드오프.</div>
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

이 6개 항목 중 **1·2·3번은 단기 우선순위** — 정전 자동 ON, 일본 IP exit node, ACL은 모두 효과 큰 작업입니다. 4·5번은 시간이 만들어주는 데이터 기반 회고고, 6번은 사용자가 회사 의존도 자체를 빼고 싶을 때만 의미 있는 옵션입니다.

---

## 시리즈 회고 — 무엇을 배웠나

마지막으로 시리즈 전체 회고입니다. 한국 IP 우회 인프라를 만든 결과물보다 **만드는 과정에서 배운 것**이 더 큽니다.

### 1. 무료 SaaS와 가정 환경의 결합

Tailscale의 무료 플랜이 **"개인 사용자가 기업급 인프라를 그대로 쓸 수 있게 풀어둔 것"** 이라는 점이 가장 흥미로운 발견입니다. 6 user / 디바이스 무제한 / Exit Node·MagicDNS·ACL 모두 포함 — 이게 0원으로 가능한 비용 구조의 근거(control/data plane 분리)는 1편에서 풀었습니다. 결과적으로 부산↔후쿠오카 P2P 메시 VPN을 **가정 NAT 두 겹 뒤에서, 새 하드웨어 없이, 비용 1만 원 이내로** 만들 수 있다는 데모가 됐습니다.

### 2. 7년 묵은 창고 노트북도 부활할 수 있다

Samsung Galaxy Book 950SBE (2018년 출시, i7-8565U 15W TDP)가 **무인 24/7 exit node로 충분히 동작**한다는 것이 시리즈의 또 다른 결과입니다. WireGuard cap이 ~100~200 Mbps로 가정 회선보다 한참 빠르고, 클램쉘 idle 7W는 데스크톱 100W+ 대비 한 자릿수입니다. **새 하드웨어가 필요 없는 인프라**라는 점이 비용 모델의 핵심입니다.

### 3. Windows 무인 운영의 함정과 우회

Windows 11 노트북을 무인 서버로 쓰는 것은 의외로 까다롭습니다 — Modern Standby의 부분 슬립, Windows Update 자동 재부팅, OpenSSH의 administrators_authorized_keys ACL, PowerShell의 `'""'` 패스프레이즈 함정 — 이런 것들이 모두 시리즈 작성 중에 부딪힌 실측입니다. 각각의 우회법은 2편에 정리되어 있고, 같은 일을 하려는 다른 사람에게 그대로 도움이 됩니다.

### 4. PowerShell 권한 분리 패턴

Linux의 `sudo`가 없는 환경에서 **"일반 SSH 세션은 일상 권한, 권한 상승은 SchTasks SYSTEM"**으로 분리하는 패턴이 운영적으로 깔끔하다는 발견. 일상 SSH가 관리자 권한을 갖지 않으니 사고 표면이 작고, 권한 상승은 검증된 스크립트 안에서만 일어나니 audit이 쉽습니다. 이 패턴은 Tailscale과 무관하게 Windows 원격 운영 일반에 응용 가능합니다.

### 5. 사고 시나리오를 미리 적어두면 자동화가 가능해진다

`tailnet-ops/docs/recovery.md`에 정리한 6개 시나리오(SSH 안 됨 / 키 분실 / 정전 / Wi-Fi 변경 / 키 만료 / 자가치유 망가짐) 각각에 대한 복구 트리가 있습니다. 이 문서를 먼저 적어두니 자가치유 SchTasks 4종이 자연스럽게 설계되었고 — **사고를 상상하는 일이 자동화의 출발점**이라는 일반 패턴의 작은 사례가 됐습니다.

---

## 시리즈 정리

| 편 | 핵심 |
|---|---|
| [1편 — 동기·실측·구조](/posts/tailscale-01-foundations/) | 후쿠오카 1년+ 누적 / 가동 결과 (P2P 50ms, Tunnel DOWN 24.9 Mbps, 무인 15h+) / Tailscale·WireGuard·메시 VPN의 구조 |
| [2편 — 셋업·무인 운영·보안](/posts/tailscale-02-setup-and-ops/) | 본가 1회 방문 5축 셋업 / 자가치유 4종 SchTasks / 13개 보안 점검 |
| 3편 (이 글) | 작동 원리 (NAT 분류·STUN·ICE·hole punching·birthday paradox·DERP·MagicDNS) / 연 1만 원 비용 분해 / 한계와 회고 |

3편 묶음으로 시리즈가 마무리됐습니다. 한국 IP 우회라는 결과 자체보다, **가정 NAT 두 겹과 7년 묵은 창고 노트북, 그리고 무료 SaaS의 조합으로 어디까지 갈 수 있는지**의 작은 케이스 스터디로 남기를 바랍니다.

---

## 참고 자료

- [`Epheria/tailnet-ops`](https://github.com/Epheria/tailnet-ops) — 본 시리즈의 운영 코드 일체
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

> **시리즈 종료**. 1·2·3편 모두 읽어주셔서 감사합니다.
{: .prompt-info }
