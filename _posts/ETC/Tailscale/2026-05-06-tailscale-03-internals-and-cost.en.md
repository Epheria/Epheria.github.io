---
title: "Tailscale Series Part 3 — Internals, Cost, and Limits (DERP·MagicDNS·hole punching·a $7-per-year retrospective)"
lang: en
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
  - Tailscale's NAT traversal is "try everything at once and pick whichever works first" — STUN/ICE standards + UPnP/PMP/PCP port mapping + DERP fallback all attempted in parallel
  - Symmetric NAT (Hard NAT) is defeated via the birthday paradox — open 256 ports and probe at random; 2,048 attempts give 99.9% success in ~20 seconds
  - DERP is a fallback that forwards already-encrypted packets over HTTPS when P2P fails. End-to-end guarantees stay intact
  - MagicDNS is a stub resolver at 100.100.100.100 that hijacks the OS DNS to resolve short hostnames into 100.64.x.x addresses
  - Real cost — electricity at ~$5 per year is essentially everything. The laptop and internet are sunk costs
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

## What this part covers

This is the final installment of the series. It bundles two things together.

**Part 1 — Internals**: the mechanism that makes the series' infrastructure possible. How do two laptops, each behind two layers of home NAT, communicate directly with each other? STUN, ICE, hole punching, DERP, and MagicDNS, all consolidated in one place.

**Part 2 — Cost, limits, retrospective**: a real cost breakdown of the $7-per-year infrastructure, items that haven't been verified, and a retrospective on the series as a whole.

This part is written so that it stands on its own, but the big picture of what the infrastructure actually does lives in Parts 1 and 2.

---

# Part 1 — Internals

## Two NAT classifications — traditional vs. modern

To talk about NAT traversal, we first have to address the kinds of NAT. The familiar classification is the **cone-based 4-class taxonomy** that's been around since the late 1990s.

| Traditional class | Behavior |
|---|---|
| Full Cone | Anyone on the outside who sends to the NAT's external port gets forwarded inside (most permissive) |
| Restricted Cone | Only inbound from external IPs the inside has previously sent to is allowed |
| Port-Restricted Cone | Only inbound from external IP+port pairs the inside has previously sent to is allowed |
| Symmetric | Different destinations get different external port mappings (most strict) |

This taxonomy is intuitive but has been criticized for failing to capture how real NAT devices actually behave, so **RFC 4787** introduced a new classification — and Tailscale adopts that one.

> Tailscale phrasing — "**Endpoint-Independent Mapping (EIM)**, and the hard variant **Endpoint-Dependent Mapping (EDM)**" ([How NAT traversal works](https://tailscale.com/blog/how-nat-traversal-works))

<div class="nat-class" style="margin:1.5rem 0">
  <div class="nc-grid">
    <div class="nc-card nc-eim">
      <div class="nc-tag">Easy NAT (EIM)</div>
      <div class="nc-key">Endpoint-Independent Mapping</div>
      <div class="nc-detail">Reuses the same external port regardless of destination. Once discovered via STUN, that port works against any other peer.</div>
      <div class="nc-foot">Most home routers</div>
    </div>
    <div class="nc-card nc-edm">
      <div class="nc-tag">Hard NAT (EDM)</div>
      <div class="nc-key">Endpoint-Dependent Mapping</div>
      <div class="nc-detail">Assigns a different external port per destination. The port discovered via STUN is only good for the STUN server, and another port has to be discovered for each new peer.</div>
      <div class="nc-foot">Some ISP CGNATs, corporate NATs</div>
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

Why this classification matters — **"if both ends are EIM, hole punching is relatively easy; if either end is EDM, it gets hard"** is the first decision point in any NAT traversal strategy. The Busan KT router and the Fukuoka home router in this series are both classified EIM, so P2P direct connection succeeds without much fuss (based on the measurements from Part 1).

---

## STUN — "how do I look from the outside"

STUN (Session Traversal Utilities for NAT), in one line, is **"a protocol where you send a packet to an external STUN server and receive back the external IP and port that server saw you from."**

> ### Hold on — let's pause here for a sec
>
> **"STUN's RFC number is 8489, not 5389"**
>
> A lot of older material on the Internet still cites STUN as **RFC 5389**, but **RFC 8489**, published in February 2020, **obsoletes 5389**. So 8489 is the current standard.
>
> Key changes in 8489:
> - Added the **MESSAGE-INTEGRITY-SHA256** attribute — a SHA-256 option in addition to MD5-based authentication
> - The **USERHASH** attribute lets usernames be anonymized
> - The **PASSWORD-ALGORITHM** attribute allows the password protection algorithm to be selected
> - The **nonce cookie** mechanism defends against bid-down attacks
>
> The body of this series uses the RFC 8489 designation.

> Tailscale phrasing — "Your machine sends a 'what's my endpoint from your point of view?' request to a STUN server, and the server replies with 'here's the ip:port that I saw your UDP packet coming from.'"

<div class="stun-flow" style="margin:1.5rem 0">
  <div class="sf-row">
    <div class="sf-step">
      <div class="sf-num">1</div>
      <div class="sf-text"><strong>OUT</strong> The node sends a UDP packet from private IP <code>192.168.0.10:54321</code> to STUN server <code>X.X.X.X:3478</code></div>
    </div>
    <div class="sf-step">
      <div class="sf-num">2</div>
      <div class="sf-text"><strong>NAT</strong> The home router creates a mapping <code>192.168.0.10:54321 ↔ public:62000</code></div>
    </div>
    <div class="sf-step">
      <div class="sf-num">3</div>
      <div class="sf-text"><strong>STUN</strong> The server replies "you came from <code>public:62000</code>"</div>
    </div>
    <div class="sf-step">
      <div class="sf-num">4</div>
      <div class="sf-text"><strong>SHARE</strong> The node advertises <code>public:62000</code> to its peers via the control plane</div>
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

The key constraint is that the STUN discovery result **has to be used on that very socket** — using a different socket causes the NAT to create a different mapping, rendering the discovered port useless. So Tailscale follows the pattern of "send STUN packets directly from the same socket that will carry traffic."

On EIM NAT, that's the end of it — the discovered `public:62000` works for any other peer too. On EDM NAT, this isn't very helpful — you have to move on to the birthday paradox in the next section.

---

## ICE — "try everything at once"

ICE (Interactive Connectivity Establishment, RFC 8445) is an algorithm that **gathers many candidates (candidate connection addresses) at once, tries them all in parallel, and picks the path that responds first**.

The five candidates Tailscale tries simultaneously per node are (per the official blog):

<div class="candidates" style="margin:1.5rem 0">
  <div class="cd-grid">
    <div class="cd-card cd-1">
      <div class="cd-num">1</div>
      <div class="cd-name">LAN address</div>
      <div class="cd-detail">If on the same network, NAT traversal isn't needed at all. Direct communication.</div>
    </div>
    <div class="cd-card cd-2">
      <div class="cd-num">2</div>
      <div class="cd-name">STUN WAN address</div>
      <div class="cd-detail">The public:port discovered through EIM NAT</div>
    </div>
    <div class="cd-card cd-3">
      <div class="cd-num">3</div>
      <div class="cd-name">Port-mapped address</div>
      <div class="cd-detail">An explicit forwarding request to the router via UPnP-IGD / NAT-PMP / PCP</div>
    </div>
    <div class="cd-card cd-4">
      <div class="cd-num">4</div>
      <div class="cd-name">NAT64 path</div>
      <div class="cd-detail">For an IPv6-only environment communicating with an IPv4 peer</div>
    </div>
    <div class="cd-card cd-5">
      <div class="cd-num">5</div>
      <div class="cd-name">DERP relay</div>
      <div class="cd-detail">Fallback when all four above fail. Always preselected</div>
    </div>
  </div>
  <p class="cd-cap">Tailscale picks the path with the lowest round-trip latency and immediately upgrades whenever a better path is found.</p>
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

The crux of this model is **"all connections start out with DERP preselected"** — every connection at startup is already flowing over DERP, and the moment a better path (LAN/STUN/port-map) is discovered, the data plane is upgraded immediately. In other words, even if NAT traversal takes a while, **communication starts from the very first packet**.

> Avery Pennarun's one-liner — "**try everything at once, and pick the best thing that works**"

---

## Hole Punching — both peers go outbound at the same time

Most home NATs (EIM) follow a stateful firewall pattern of "allow inbound from external IP/port pairs that the inside has previously sent to." That behavior is the foothold for hole punching.

<div class="hole-punch" style="margin:1.5rem 0">
  <div class="hp-row">
    <div class="hp-side">
      <div class="hp-tag">Peer A (behind NAT)</div>
      <div class="hp-box">
        <div class="hp-line">1. Receives B's public address from the control plane</div>
        <div class="hp-line">2. Sends an outbound UDP packet toward B</div>
        <div class="hp-line">3. The NAT creates a mapping; its own firewall allows responses from B</div>
      </div>
    </div>
    <div class="hp-mid">
      <div class="hp-arrow">⟷</div>
      <div class="hp-arrow-text">simultaneous</div>
    </div>
    <div class="hp-side">
      <div class="hp-tag">Peer B (behind NAT)</div>
      <div class="hp-box">
        <div class="hp-line">1. Receives A's public address from the control plane</div>
        <div class="hp-line">2. Sends an outbound UDP packet toward A</div>
        <div class="hp-line">3. The NAT creates a mapping; its own firewall allows responses from A</div>
      </div>
    </div>
  </div>
  <p class="hp-cap">"packets must flow out before packets can flow back in" — Tailscale's hole punching principle</p>
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

In this process, **the very first outbound packet is dropped by the other side's NAT** (no mapping yet, so it can't arrive). But that dropped packet still creates a mapping on the sender's own NAT, and when the other peer's outbound packet then arrives at our NAT, **the firewall recognizes it as "a response from somewhere we've sent to first"** and lets it through.

After that, both sides exchange a keep-alive ping every 30 seconds to maintain the NAT mapping — typical home NATs expire mappings after 30 seconds to a few minutes of inactivity.

---

## Symmetric NAT and the Birthday Paradox

EDM NAT (Hard NAT) **doesn't yield to that hole-punching technique on its own** — since each destination gets a different external port, the port the control plane shared with the peer doesn't match the port the peer will actually receive from.

The fix is **probabilistic**. One side opens 256 ports simultaneously, and the other side fires probes randomly into that 256-port pool. When a match (a birthday collision) hits, a hole opens.

<div class="bday" style="margin:1.5rem 0">
  <div class="bd-table-wrap">
    <table class="bd-table">
      <thead><tr><th>Probes</th><th>Success probability</th><th>Time (at 100 pkt/s)</th></tr></thead>
      <tbody>
        <tr><td>174</td><td>50%</td><td>1.7s</td></tr>
        <tr><td>256</td><td>64%</td><td>2.6s</td></tr>
        <tr><td>1,024</td><td>98%</td><td>10s</td></tr>
        <tr class="bd-hl"><td>2,048</td><td>99.9%</td><td>~20s</td></tr>
      </tbody>
    </table>
  </div>
  <p class="bd-cap">Official Tailscale numbers. Probability of success when probing randomly into a 256-port pool.</p>
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

The math: the port space is 65,535, and when one side opens 256 ports, a single random probe has a 256/65,535 ≈ 0.39% chance of hitting one of them. The probability 1 - (1 - 256/65535)^N exceeds 0.999 at N = 2,048 (it's called the `birthday paradox` because the search space shrinks by the square root — √N — rather than linearly).

At 100 packets/second, 2,048 probes = roughly 20 seconds. In practice, Tailscale reports that more than half the time it gets through in under 2 seconds.

> Tailscale's measurement — "half the time we'll get through in under 2 seconds" (How NAT traversal works)

**The harder case — both sides EDM**: the search space multiplies and reaching 99.9% takes roughly 28 minutes (170,000 probes / 100 pkt/s). In that case, things effectively fall back to DERP.

In this series' setup, the Busan KT router is EIM and the Fukuoka home router is also EIM, so the birthday paradox never has to kick in — STUN alone does the job.

---

## DERP — the last-resort safety net

When P2P direct fails on every front, **DERP (Designated Encrypted Relay for Packets)** kicks in as the fallback. Here's what makes DERP distinctive, organized as a table.

| Aspect | DERP behavior |
|---|---|
| Protocol | **HTTPS (TCP/443)** — passes through environments where UDP is blocked |
| Data handling | **Forwards encrypted packets verbatim** — no decryption (E2E guarantee preserved) |
| Node-side keys | DERP servers **never receive private keys** — they only ever exist on the nodes |
| Relation to TURN | "DERP plays the same role as TURN, but uses HTTPS streams + WireGuard keys" |
| Global infrastructure | Tailscale runs 28+ regions, **included in the free Personal plan** |
| Behavior at startup | **"DERP is always preselected"** — communication begins from the very first packet |

That DERP runs on **TCP/443 (HTTPS)** has real operational weight — it's the reason Tailscale works in cafés, hotels, and corporate networks where UDP is blocked. The traffic looks like ordinary HTTPS, and the packets are already WireGuard-encrypted, so anything in the middle can't see in.

> Tailscale phrasing — "Your traffic remains end-to-end encrypted when it passes through a relay server."

### TURN vs DERP — what's the same and what's different

DERP occupies the same slot as the IETF standard **TURN (Traversal Using Relays around NAT, RFC 8656)**, but the implementation differs. A comparison:

| Aspect | TURN (RFC 8656) | Tailscale DERP |
|---|---|---|
| Standardization | IETF standard | Tailscale's own implementation (open source) |
| Transport | UDP / TCP / TLS | **HTTPS (TCP/443)** only |
| Authentication | TURN credentials (username/credential) | WireGuard keys |
| Data plane | Both ciphertext and plaintext possible | **Ciphertext only (E2E preserved)** |
| Common use | WebRTC video conferencing fallback | Mesh VPN inter-node fallback |
| Operating cost | Requires a separate TURN server | Tailscale's global infrastructure (included in the free plan) |

**The key difference is the decision to be "HTTPS over TLS only."** TURN uses both UDP and TCP, but some corporate firewalls recognize TURN's standard ports (3478, 5349) and block them, whereas DERP rides on **HTTPS that's indistinguishable from ordinary web traffic**, so it makes it through almost any environment. That's why it's guaranteed to work on café, hotel, and airport Wi-Fi.

> ### Hold on — let's pause here for a sec
>
> **"DERP servers actually double as STUN responders — both roles on a single host"**
>
> Above we treated STUN and DERP as separate mechanisms, but on the operational side, they sit on nearly the same infrastructure — Tailscale's global DERP nodes **provide HTTPS relay and STUN responder roles together on a single host**. The same node responds as a DERP relay over TCP/443 (HTTPS) and as a STUN responder over UDP/3478.
>
> So "putting one DERP node in the Tokyo region" means — (a) in environments where UDP works, that node helps **discover external IP/port via STUN** and establish P2P direct, and (b) in environments where UDP is blocked, that node accepts the **HTTPS relay fallback**. One node handling both roles at once is one of the reasons the global DERP infrastructure cost stays bounded.
>
> The reason `tailscale netcheck` in Part 1 of the series measures RTT against all 28 DERP regions in one shot is the same — there's no need to call separate endpoints for STUN and DERP because both roles are measured on the same host.

### Same family as WebRTC

One interesting observation — **the NAT traversal technologies covered in this series stand on the same standards as WebRTC (browser video conferencing)**.

| Technology | Use |
|---|---|
| **STUN (RFC 8489)** | Discovers your public IP for WebRTC calls / discovers a Tailscale node's external address |
| **ICE (RFC 8445)** | Gathers candidates and tries them in parallel for WebRTC calls / collects connection candidates for a Tailscale node |
| **TURN (RFC 8656)** | Fallback relay for WebRTC calls / Tailscale uses its own DERP in the same slot |

Put another way, the mechanism that lets two users on a Google Meet or Zoom call punch through NAT and form a P2P video stream and **the mechanism this series uses to form Busan↔Fukuoka SSH and video streams stand on essentially the same family of IETF standards**. Mesh VPN and video conferencing turn out to be close cousins.

The difference is the **data plane** — WebRTC uses SRTP (for media), Tailscale uses WireGuard. But the NAT traversal layer shares the same standards family.

---

## MagicDNS — why short hostnames work

The reason this series can reach the Busan laptop with the single line `ssh samsung-home-laptop` is MagicDNS. It's the feature that **automatically maps short hostnames of tailnet nodes to 100.64.x.x**.

How it works:

<div class="magic-dns" style="margin:1.5rem 0">
  <div class="md-flow">
    <div class="md-step">
      <div class="md-num">1</div>
      <div class="md-body">
        <strong>The Tailscale client hijacks the OS DNS</strong><br>
        When the client starts, it registers itself in the OS DNS settings as a stub resolver (on Linux/macOS at `100.100.100.100`; on Windows on a separate adapter's DNS).
      </div>
    </div>
    <div class="md-step">
      <div class="md-num">2</div>
      <div class="md-body">
        <strong>Tailnet domain queries are handled locally</strong><br>
        Queries like <code>samsung-home-laptop</code> or <code>samsung-home-laptop.tailba1ca3.ts.net</code> are answered by the client using the mapping table fetched from the control plane — it returns <code>100.64.88.55</code>.
      </div>
    </div>
    <div class="md-step">
      <div class="md-num">3</div>
      <div class="md-body">
        <strong>Regular Internet DNS is forwarded as-is</strong><br>
        Queries like <code>naver.com</code> are delegated to the OS's original DNS (8.8.8.8, the ISP DNS, etc.). When using a global nameserver, traffic is automatically encrypted via <strong>DoH (DNS-over-HTTPS)</strong>.
      </div>
    </div>
    <div class="md-step">
      <div class="md-num">4</div>
      <div class="md-body">
        <strong>Search domain auto-appended</strong><br>
        When you type a short name like <code>ssh samsung-home-laptop</code>, the OS automatically appends <code>.tailba1ca3.ts.net</code> to the query — that's why short names reach their target.
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

The crux is the split-horizon DNS model where **the Tailscale client hijacks the OS DNS but lets ordinary traffic flow through**. The user can type `ssh samsung-home-laptop` with no extra setup, and at the same time normal web browsing isn't affected.

> ### Hold on — let's pause here for a sec
>
> **"Why don't macOS's `host` / `nslookup` see MagicDNS?"**
>
> Some macOS CLI tools (`host`, `nslookup`) **bypass the system DNS resolver and query DNS servers directly**, so they don't pass through Tailscale's stub resolver. Tailscale's official documentation explicitly notes this limitation.
>
> Regular apps (browsers, SSH clients, `ping`) go through the system resolver and work normally.

---

## Internals — wrap-up

That's the complete story of how all the magic in this series' infrastructure happens. Bundled into a single frame:

| Mechanism | Role | Included in free plan? |
|---|---|---|
| LAN direct | Direct on the same network | (n/a) |
| STUN | Discovery of NAT external address (sufficient on EIM) | Yes |
| UPnP-IGD / NAT-PMP / PCP | Explicit port forwarding requests to the router | Yes |
| Hole punching | Both ends sending outbound at once to create simultaneous NAT mappings | Yes |
| Birthday paradox probe | Probabilistic port search to traverse EDM NAT | Yes |
| **DERP relay** | HTTPS-based fallback when all of the above fail (E2E preserved) | Yes (28+ global regions) |
| **MagicDNS** | Resolves short hostnames into tailnet IPs | Yes |
| **WireGuard** | The data plane for all traffic (Curve25519 + ChaCha20-Poly1305) | Yes |

These eight pieces are **automatically combined inside a single client**. The user only needs the one line `tailscale up` and a single exit-node approval in the admin console.

---

# Part 2 — Cost, limits, retrospective

## Annual cost breakdown

Here is the actual breakdown of the cost the series has been calling "$0 infrastructure" or "$7-per-year infrastructure."

<div class="cost-table" style="margin:1.5rem 0">
  <div class="ct-grid">
    <div class="ct-card ct-1">
      <div class="ct-num">~5.5</div>
      <div class="ct-unit">USD/year</div>
      <div class="ct-name">Electricity (essentially everything)</div>
      <div class="ct-detail">7W × 24h × 365 days = 61.32 kWh × Korean residential tier-1 rate ~$0.09/kWh</div>
    </div>
    <div class="ct-card ct-2">
      <div class="ct-num">0</div>
      <div class="ct-unit">USD/year</div>
      <div class="ct-name">Tailscale</div>
      <div class="ct-detail">Personal plan is free (unlimited devices)</div>
    </div>
    <div class="ct-card ct-3">
      <div class="ct-num">0</div>
      <div class="ct-unit">USD/year</div>
      <div class="ct-name">Internet line</div>
      <div class="ct-detail">The KT GiGA line at the family home that the family is already paying for. No marginal cost.</div>
    </div>
    <div class="ct-card ct-4">
      <div class="ct-num">0</div>
      <div class="ct-unit">USD/year</div>
      <div class="ct-name">Hardware</div>
      <div class="ct-detail">A 7-year-old closet laptop (Galaxy Book 950SBE) — sunk cost</div>
    </div>
  </div>
  <p class="ct-cap">Total: roughly <strong>$5–7 per year</strong>. The laptop's battery aging is mitigated by an 80% charge cap.</p>
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

For comparison — **typical pricing for Korean commercial VPN services** is ~$4–9 per month, or ~$45–110 per year. So **this series' annual cost is roughly 5~12% of a commercial VPN**.

The advantage holds against other self-host options too.

| Option | Yearly cost | Limitations |
|---|---|---|
| **This series (closet laptop + Tailscale Free)** | ~$5–7 | Only one Korean IP location |
| AWS Lightsail VPN ($3.50/mo, Korean region) | ~$42 | Korean IP works, but some games and banks block data center IPs |
| Self-hosted OpenVPN (Lightsail + your time) | ~$42 + setup/operations time | Hub-and-spoke; no automatic NAT traversal |
| Buying a new Raspberry Pi 4 for the Korean home + operating it | ~$60 (Pi 4 + case + SD) + electricity | Same result as this series, but the new hardware cost |
| Commercial VPN (Korean server option) | ~$45–110 | Some Korean sites explicitly block commercial VPN IPs |

There are some pitfalls in this comparison, though.

- **The comparison isn't apples-to-apples** — commercial VPNs are about IP redirection through global servers, while this series only provides a single Korean IP. If you need a Japanese IP or a US IP, that requires separate nodes.
- **Time cost isn't included in the comparison** — broken out in the next section.
- **"A by-product of studying"** — honestly, the biggest value of this series isn't the result of bypassing to a Korean IP, it's the **hands-on practice with NAT, DNS, SSH, PowerShell, and SchTasks** as a by-product. From that angle, the time investment is also recouped as personal-learning cost.


### Time cost breakdown

An honest accounting that includes my own time:

| Stage | Time spent | Notes |
|---|---|---|
| Setup (one visit to the family home) | ~4h | One run of install.ps1 + admin console work + verification |
| Series writing | ~40h (broken out below) | Cumulative writing time across all 3 parts of this series |
| Daily operations (per month) | ~10 min | Self-healing handles most of it; a quick status check is enough |
| Incident response (so far) | 0h | Zero self-healing triggers |

**Series writing time — broken out by part and activity**

| Activity | Part 1 (motivation·measurements·structure) | Part 2 (setup·operations·security) | Part 3 (internals·retrospective) | Total |
|---|---|---|---|---|
| Research and verification (RFCs, Tailscale official, Wikipedia) | ~3h | ~2h | ~5h | ~10h |
| Drafting (Korean body) | ~4h | ~5h | ~5h | ~14h |
| Visualization (HTML/CSS diagrams) | ~3h | ~2h | ~3h | ~8h |
| Polishing pass (additional external sources, citation consistency) | ~2h | ~2h | ~3h | ~7h |
| **Per-part total** | **~12h** | **~11h** | **~16h** | **~39h** |

Part 3 ended up being the longest because **the internals — NAT classes, STUN, ICE, the birthday paradox — require more careful cross-checking against external sources than the other parts**. The table above is an estimate, but the sense that the whole series was a 30~40-hour piece of work is accurate. Coding time (install.ps1, setup-helpers.ps1, security-audit.ps1) is separate, and that time accumulated in Fukuoka outside the family-home visit, so I've kept it out of the table.

If I price that time at ¥3,000/hour (a rough Japanese average), setup plus series writing dominates by far. But that time was recouped as **hands-on learning of NAT, DNS, Windows automation, SchTasks, and PowerShell**, and the series itself is time saved for anyone trying to do the same thing.

**So the real cost comparison really comes down to "how often do you need a Korean IP"**:

- **Often (5+ times/week)**: this series' setup is clearly ahead
- **Sometimes (1~2 times/month)**: a commercial VPN is reasonable on the time front
- **Almost never**: both are overkill

---

## Limits and unverified items

The infrastructure in this series isn't omnipotent. Here is a summary of items that haven't been explicitly verified plus known limitations.

| Item | Status | Mitigation |
|---|---|---|
| Auto power-on after a power outage | **Not verified** — depends on the BIOS's AC Power Recovery setting | No way to verify other than visiting the family home |
| Wi-Fi password change | **Cannot auto-recover** — have to ask family to share the new password and reconnect manually | Not solved by redundancy either |
| 30+ days of unattended operation | Unverified (only ~15 hours measured at the time of writing) | A retrospective once enough time passes |
| Effectiveness of the Korean-IP bypass for sites like Linkkf | Only a 30-second traffic measurement; site-by-site unblocking is unverified | Needs case-by-case checks during everyday Fukuoka use |
| Carelessness scenarios at the Busan family home | Cannot be experimented on | Mitigated by talking to family in advance |
| Bypass of Japan-IP-blocked sites (the reverse direction) | No Japanese exit node set up | Possible by advertising the Fukuoka desktop as an exit node; not configured |

The biggest real risk is **the first row — auto power-on after a power outage**. If that doesn't work, a single outage forces a trip to the family home. Explicitly enabling AC Power Recovery in the BIOS on the next family-home visit is the top item on the next reinforcement list.

---

## The next 6-month / 1-year roadmap

Just because this series ended doesn't mean the infrastructure is done. Items being considered for the next stage:

<div class="roadmap" style="margin:1.5rem 0">
  <div class="rm-grid">
    <div class="rm-card rm-1">
      <div class="rm-when">Next family-home visit</div>
      <div class="rm-name">Enable BIOS AC Power Recovery</div>
      <div class="rm-detail">Verify auto power-on behavior after a power outage. Direct fix for item 1 in the limitations table.</div>
    </div>
    <div class="rm-card rm-2">
      <div class="rm-when">Short term (1~2 months)</div>
      <div class="rm-name">Advertise the Fukuoka desktop as a Japan-IP exit node</div>
      <div class="rm-detail">A single line: <code>tailscale up --advertise-exit-node</code>. Lets us bypass Korean sites blocked from Japan (the reverse direction). Doable from Fukuoka without a family-home visit.</div>
    </div>
    <div class="rm-card rm-3">
      <div class="rm-when">Short term (1~2 months)</div>
      <div class="rm-name">Permission separation via ACL JSON definitions</div>
      <div class="rm-detail">Apply Part 2's ACL pattern. Use tag:exit-node + tag:client to make the SSH policy explicit. Deny-by-default minimizes blast radius.</div>
    </div>
    <div class="rm-card rm-4">
      <div class="rm-when">Mid term (3~6 months)</div>
      <div class="rm-name">Try a subnet router — access other devices on the family-home LAN</div>
      <div class="rm-detail">Reach other devices at the family home (parents' PC, NAS, etc.) through the laptop without joining them directly to Tailscale. <code>--advertise-routes=192.168.0.0/24</code>.</div>
    </div>
    <div class="rm-card rm-5">
      <div class="rm-when">Long term (6~12 months)</div>
      <div class="rm-name">Collect 30+ days of unattended operation data + retrospective</div>
      <div class="rm-detail">Currently only ~15 hours measured. metrics-collector.ps1 will accumulate 7 months of data on a 5-minute cadence — long-term stability patterns can be analyzed from that.</div>
    </div>
    <div class="rm-card rm-6">
      <div class="rm-when">Conditional (out of series)</div>
      <div class="rm-name">Evaluate self-hosting Headscale</div>
      <div class="rm-detail">An option for those who want to drop the dependency on the Tailscale company. Trade-off: coordinator operating burden plus the loss of free DERP infrastructure.</div>
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

Of these six, **items 1, 2, and 3 are the short-term priorities** — auto power-on, Japan-IP exit node, and ACL all yield large effects. Items 4 and 5 are time-driven, data-based retrospectives, and item 6 only matters if the user wants to drop the dependency on the company itself.

---

## Series retrospective — what was learned

The final section is a retrospective on the series as a whole. **What I learned in the process of building it** turned out to be bigger than the result — building an infrastructure that bypasses to a Korean IP.

### 1. The combination of free SaaS and a home environment

The most interesting find is that Tailscale's free plan is **"individuals being given enterprise-grade infrastructure to use as-is"**. 6 users / unlimited devices / Exit Node, MagicDNS, ACL all included — the rationale for how that's free (separation of control plane and data plane) was unpacked in Part 1. The end result is a demo that you can build a Busan↔Fukuoka P2P mesh VPN **behind two layers of home NAT, with no new hardware, for under $7 per year**.

### 2. Even a 7-year-old closet laptop can come back to life

Another result of the series is that the Samsung Galaxy Book 950SBE (released in 2018, i7-8565U with 15W TDP) **performs adequately as an unattended 24/7 exit node**. The WireGuard cap of ~100~200 Mbps is well above the home line, and 7W of clamshell idle is in the single digits compared to 100W+ on a desktop. **Not needing new hardware** is the heart of the cost model.

### 3. The pitfalls and workarounds of unattended Windows operation

Running a Windows 11 laptop as an unattended server is surprisingly tricky — Modern Standby's partial sleep, Windows Update auto-reboot, OpenSSH's administrators_authorized_keys ACL, PowerShell's `'""'` passphrase trap — all of these were measurements I bumped into while writing the series. Each workaround is documented in Part 2, and they apply directly to anyone trying to do the same.

### 4. PowerShell privilege-separation pattern

In an environment without Linux's `sudo`, separating things into **"regular SSH sessions get everyday privileges, privilege escalation happens via SchTasks SYSTEM"** turns out to be operationally clean. Daily SSH doesn't carry administrator privileges, so the incident surface is small, and privilege escalation only happens inside vetted scripts, so auditing is easy. The pattern applies to general remote Windows operations regardless of Tailscale.

### 5. Writing down incident scenarios in advance makes automation possible

`tailnet-ops/docs/recovery.md` lays out recovery trees for six scenarios (no SSH / lost key / power outage / Wi-Fi change / key expiry / self-healing broken). Writing that document first led naturally to designing the four self-healing SchTasks — **imagining incidents is the starting point of automation**, a small case study of that general pattern.

---

## Series summary

| Part | Key |
|---|---|
| [Part 1 — Motivation·Measurements·Structure](/posts/tailscale-01-foundations/) | Cumulative experience over 1+ year in Fukuoka / operational results (P2P 50ms, Tunnel DOWN 24.9 Mbps, unattended 15h+) / structure of Tailscale·WireGuard·mesh VPN |
| [Part 2 — Setup·Unattended Operation·Security](/posts/tailscale-02-setup-and-ops/) | One-time family-home visit with five-axis setup / four self-healing SchTasks / 13 security checks |
| Part 3 (this post) | Internals (NAT classes·STUN·ICE·hole punching·birthday paradox·DERP·MagicDNS) / $7-per-year cost breakdown / limits and retrospective |

The series wraps up as a 3-part bundle. More than the result of bypassing to a Korean IP, I hope it stays as a small case study of **how far you can take the combination of two layers of home NAT, a 7-year-old closet laptop, and a free SaaS**.

---

## References

- [`Epheria/tailnet-ops`](https://github.com/Epheria/tailnet-ops) — All operational code for this series
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

> **End of series**. Thank you for reading Parts 1, 2, and 3.
{: .prompt-info }
