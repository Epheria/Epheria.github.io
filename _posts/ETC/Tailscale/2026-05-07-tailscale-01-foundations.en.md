---
title: "Tailscale Series Part 1 — A Korean-IP Bypass Built on a Garage Laptop (Motivation, Measurements, Architecture)"
lang: en
date: 2026-05-07 18:00:00 +0900
categories: [ETC, Tailscale]
tags: [tailscale, network, vpn, wireguard, mesh-vpn, p2p, exit-node, infrastructure]
toc: true
toc_sticky: true
difficulty: beginner
chart: true
tldr:
  - Solving a year+ accumulated need for a Korean IP from Fukuoka, using a garage laptop and Tailscale's Personal Free plan
  - A 3-node mesh (Busan Win + Fukuoka Mac + Fukuoka Win) in operation — P2P direct 50ms / Tunnel DOWN 24.9 Mbps / 15+ hours of unattended stability
  - Tailscale is a mesh VPN — data plane (WireGuard, E2E) and control plane (coordination) are split. Traffic does not flow through company infrastructure
  - The company was founded in Toronto in 2019 by four ex-Googlers (including Brad Fitzpatrick), with $272M in cumulative funding. The Personal plan is free for 6 users / unlimited devices
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

## What this series covers

Living in Fukuoka for over a year, the moments when a Korean IP would have been useful kept piling up. Korean payments, banking, and some content services either don't behave properly from a foreign IP or demand additional verification. Briefly firing up a commercial Korean VPN every time was unsatisfying on cost, trust, and OS compatibility all at once.

The solution was to drag out an old laptop that had been gathering dust in a garage at my family home in Busan for seven years (Samsung Galaxy Book 950SBE, **Intel Core i7-8565U / 16GB / Windows 11 Home**), revive it as an unattended exit node, and operate it remotely over SSH from a Mac in Fukuoka. After a few days of validation, the data is in: **Tunnel DOWN 24.9 Mbps, P2P direct 50ms RTT, 15+ hours of unattended stable operation** — Korean-IP bypass and remote operation are entirely feasible without buying any new hardware.

This series breaks the whole process into three parts.

| # | Title | Coverage |
|---|---|---|
| **Part 1 (this post)** | Motivation, measurements, architecture | Live measurements from the running infrastructure + the structural foundations of Tailscale, mesh VPNs, and WireGuard |
| Part 2 | Family-home setup + unattended ops + security | Single-visit setup / self-healing SchTasks / security audit |
| Part 3 | How it works + costs and limits | DERP, MagicDNS, hole punching / a retrospective on annual cost (~$7) |

This Part 1 follows a flow of **showing the measurements from the already-running infrastructure first**, then unpacking the structural reasons that make those numbers possible.

> ### Hold on — let's pause here for a sec
>
> **"exit node? tailnet? peer? That's a lot of jargon before we even start."**
>
> Here are the four core terms that show up most often, briefly defined before we go further.
>
> - **Tailnet** — A **private virtual network** of Tailscale nodes belonging to one user (or organization). In our scenario, the Busan laptop, the Fukuoka Mac, and the Fukuoka Windows desktop are all in the same tailnet.
> - **Peer** — A node inside a tailnet. There is **no client/server distinction**; every member sits at an equal position and can talk directly to every other member. The same "peer" as in P2P (peer-to-peer).
> - **Mesh** — A network topology where peers connect **directly to one another** without going through a central hub. We compare it with hub-and-spoke in detail later.
> - **Exit node** — A feature that designates one node in the tailnet as the gateway through which "this node will go out to the Internet." When the Fukuoka Mac picks the Busan laptop as its exit node, **all of the Mac's Internet traffic exits through the Busan laptop and appears under a Korean IP**. This is the core tool the series is building.

---

## The system at a glance — currently running

Here is the node status as captured in the Tailscale admin console. Personal Free plan; two nodes are continuously Connected; the Busan laptop is advertising itself as an Exit Node.

![Tailscale admin console — Busan family-home laptop running as an Exit Node, Fukuoka Mac connected](/assets/img/post/ETC/Tailscale/admin-console-machines.png)
_A single admin-console screen with Win 11 (Busan) and macOS 26 (Fukuoka) bound to the same tailnet. **A mesh that is OS-agnostic** is one of Tailscale's core strengths._

The key numbers, summarized as four cards (based on 30 hours of continuous measurement, 2026-05-04 to 05-05).

<div class="metric-cards" style="margin:1.5rem 0">
  <div class="mc-grid">
    <div class="mc-card mc-blue">
      <div class="mc-label">Uptime (unattended)</div>
      <div class="mc-value">15h+</div>
      <div class="mc-sub">0 self-healing triggers</div>
    </div>
    <div class="mc-card mc-green">
      <div class="mc-label">Wi-Fi signal</div>
      <div class="mc-value">99%</div>
      <div class="mc-sub">All 365 samples held at 99%</div>
    </div>
    <div class="mc-card mc-purple">
      <div class="mc-label">DERP RTT (Tokyo)</div>
      <div class="mc-value">28ms</div>
      <div class="mc-sub">P2P direct (DERP not used)</div>
    </div>
    <div class="mc-card mc-orange">
      <div class="mc-label">Tunnel DOWN</div>
      <div class="mc-value">24.9 Mbps</div>
      <div class="mc-sub">5x 1080p · close to 4K</div>
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

## 3-node mesh topology

The tailnet currently has three nodes bound together: one exit node in Busan, two clients on the Fukuoka side (Mac + Windows). Nodes connect to each other over P2P direct, falling back to the Tokyo DERP only when a direct connection is impossible (the closest East Asian region).

<div class="mesh-topo" style="margin:1.5rem 0">
  <div class="mt-grid">
    <div class="mt-side">
      <div class="mt-tag">Korea (Exit Node)</div>
      <div class="mt-node mt-busan">
        <div class="mt-name">samsung-home-laptop</div>
        <div class="mt-os">Windows 11 Home</div>
        <div class="mt-spec">i7-8565U · 16GB</div>
        <div class="mt-loc">Busan family home · KT GiGA 5G</div>
      </div>
    </div>
    <div class="mt-center">
      <div class="mt-cloud">
        <div class="mt-cloud-title">tailnet</div>
        <div class="mt-cloud-sub">P2P direct<br>Tokyo DERP fallback</div>
      </div>
    </div>
    <div class="mt-side">
      <div class="mt-tag">Japan (Clients)</div>
      <div class="mt-node mt-japan">
        <div class="mt-name">jp1461npcl</div>
        <div class="mt-os">macOS 26.1</div>
        <div class="mt-spec">Main laptop</div>
        <div class="mt-loc">Fukuoka home</div>
      </div>
      <div class="mt-node mt-japan">
        <div class="mt-name">fukuoka-home-pc</div>
        <div class="mt-os">Windows 11</div>
        <div class="mt-spec">Desktop</div>
        <div class="mt-loc">Fukuoka home</div>
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

| Node | Role | OS | Location | Connection mode |
|---|---|---|---|---|
| samsung-home-laptop | Exit node (Korean-IP egress) | Windows 11 Home | Busan family home | direct |
| jp1461npcl | Main client | macOS 26.1 | Fukuoka home | direct |
| fukuoka-home-pc | Additional client | Windows 11 | Fukuoka home | direct |

All three nodes run **direct P2P** — they communicate directly without DERP relay. The mechanism that lets a direct path succeed even through two layers of home NAT is called hole punching, and Part 3 of the series covers it in depth.

> ### Hold on — let's pause here for a sec
>
> **"What does 'direct' mean in the last column? And what does the 100.64.x.x IP signify?"**
>
> Two things at once.
>
> **(1) Communication path — direct vs DERP**
>
> - **P2P direct** — A state where two nodes exchange UDP packets **directly** over the Internet using each other's public IP and port. Fastest, and **no traffic crosses Tailscale's company infrastructure**.
> - **DERP relay** — A fallback through Tailscale's public relay server (Designated Encrypted Relay for Packets) when direct doesn't work. DERP **only forwards already-encrypted packets — it never decrypts them**.
>
> **(2) Tailscale IPs — `100.64.0.0/10`**
>
> The private IPs Tailscale assigns to nodes look like `100.64.x.x`. This range was originally reserved for ISP CGNAT (Carrier-Grade NAT) use, but Tailscale **simply borrows it as the addressing space for its own virtual network**. Since the range is unreachable directly from the Internet, it doesn't collide with other Internet traffic.

---

## Measurements

### DERP latency — 28 regions, measured from the Busan laptop

Here are the RTTs to all 28 regional DERP servers, as measured by `tailscale netcheck`. Tokyo is overwhelmingly the closest at 28ms, and all four East Asian regions are within 100ms.

<div class="chart-wrapper">
  <div class="chart-title">DERP latency (ms, Busan laptop → each region)</div>
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

What 28ms to Tokyo means: even if hole punching fails and traffic falls back to DERP relay, the Busan↔Fukuoka RTT over a free public relay network still sits at the best-case range for the same regional cluster. **The fact that this global DERP infrastructure is provided for free** is, as we'll see later, a major axis of the cost model.

### Bandwidth — Tunnel UP/DOWN vs Internet backbone

Here are the results of bidirectional scp on a 50MB file, compared against the Internet backbone. **Tunnel DOWN at 24.9 Mbps is the overall bottleneck** — the upload-side limit of the home line in Busan shows through directly.

<div class="chart-wrapper">
  <div class="chart-title">Bandwidth comparison (Mbps, 50MB file)</div>
  <canvas id="bandwidthCompare" class="chart-canvas" height="280"></canvas>
</div>
<script>
window.chartConfigs = window.chartConfigs || [];
window.chartConfigs.push({
  id: 'bandwidthCompare',
  type: 'bar',
  data: {
    labels: ['Cloudflare backbone\n(Busan-side Internet egress)', 'Tunnel UP\n(Fukuoka → Busan)', 'Tunnel DOWN\n(Busan → Fukuoka, bottleneck)', '4K streaming\n(reference)', '1080p streaming\n(reference)'],
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

Interpretation:
- The Internet backbone delivers 245 Mbps, but **Tunnel UP is 59.2 Mbps** — the cumulative result of WireGuard encryption, the Wi-Fi channel, and protocol overhead. This lines up with general benchmarks showing the i7-8565U (15W TDP) caps WireGuard around ~100–200 Mbps.
- **Tunnel DOWN at 24.9 Mbps** reflects the asymmetric upload-side cap of the Busan home FTTH line — Korean home Internet's standard "down ≫ up" structure showing through.
- Against an average of 5 Mbps for 1080p video streaming, that is **5x headroom**; for 4K (~25 Mbps) the cap is effectively reached, with no margin.

### Stability — 368 samples over 30 continuous hours of metrics

Here are the 7-day statistics of metrics auto-collected every 5 minutes. Every key indicator has a standard deviation that is essentially zero — a stable state.

| Metric | mean | min | p50 | p95 | max | samples |
|---|---|---|---|---|---|---|
| Battery (AC connected) | 84.8% | 84 | 85 | 85 | 85 | 368 |
| Wi-Fi signal | 99.0% | 99 | 99 | 99 | 99 | 365 |
| RTT 8.8.8.8 | 29.3ms | 28 | 29 | 30 | 90 | 368 |
| RTT 1.1.1.1 | 9.2ms | 8 | 9 | 10 | 25 | 368 |

Operational record of the self-healing system:

<div class="health-cards" style="margin:1.5rem 0">
  <div class="hc-grid">
    <div class="hc-card hc-good">
      <div class="hc-num">0</div>
      <div class="hc-label">Tailscale restarts</div>
      <div class="hc-sub">Times the 5-min health check triggered</div>
    </div>
    <div class="hc-card hc-good">
      <div class="hc-num">0</div>
      <div class="hc-label">sshd restarts</div>
      <div class="hc-sub">Same — never died</div>
    </div>
    <div class="hc-card hc-good">
      <div class="hc-num">0</div>
      <div class="hc-label">SSH auth failures</div>
      <div class="hc-sub">0 brute-force attempts in last 24h</div>
    </div>
    <div class="hc-card hc-good">
      <div class="hc-num">5/5</div>
      <div class="hc-label">SchTasks Ready</div>
      <div class="hc-sub">All 5 self-healing tasks healthy</div>
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

### Reboot auto-recovery — about 1 minute 30 seconds on average after warm-up

The most important scenario for a remote-operations safety net is "after a reboot, does SSH come back up without anyone touching the machine?" Validation across four reboots, including clamshell mode (lid closed):

| Run | Boot complete | SSH recovery | First health check | Notes |
|---|---|---|---|---|
| 1st | n/a | ~5 min | reboot +19s | First attempt (cold start) |
| 2nd | +29s | ~1 min 34 s | n/a | |
| 3rd | +29s | ~1 min | +48s | |
| **4th (lid closed)** | +28s | n/a | +80s | **Clamshell validation** |

The first run accumulated cold-start costs from DNS and service initialization, taking ~5 minutes; **after warm-up, the average from the second run onward is about 1 minute 30 seconds**. The decisive evidence for clamshell validation is that all services started cleanly with `WmiMonitorBasicDisplayParams Count = 0` (zero active monitors). That means even if family members close the laptop's lid at the home in Busan, the infrastructure keeps running.

That's the proof-of-operation for the infrastructure. From here, we move into the structural reasons why this result is possible.

---

## Who builds Tailscale

Let's start with the company itself. Tailscale was **founded in 2019 in Toronto, Canada**, by four engineers who had all worked at Google (per Wikipedia).

| Founder | Notes |
|---|---|
| Avery Pennarun | CEO. His blog post "How NAT traversal works" is, in practice, the standard introduction to NAT |
| David Crawshaw | Systems and languages, with a career closely tied to the Go ecosystem |
| David Carney | Chief Strategy Officer |
| Brad Fitzpatrick | Creator of **LiveJournal, memcached, and Perlbal**, later a long-tenured engineer on Google's core Go team |

Brad Fitzpatrick's joining especially carries weight. According to Wikipedia, he **started LiveJournal as a college freshman**, sold it to Six Apart in January 2005, then **worked as a Staff Software Engineer on Google's Go core team for 12.5 years from August 2007**, before **leaving in January 2020 and joining Tailscale as a "late-stage co-founder" three days later** — meaning he was the fourth member to join the original three (Avery / Crawshaw / Carney) who founded the company in 2019. The timeline of someone who personally created core Internet infrastructure (memcached, OpenID, Perkeep) spending 12.5 years on the Go team and then moving directly into Tailscale shapes a credibility profile distinct from a generic new startup.

The funding is also non-trivial (Wikipedia).

| Round | Date | Amount | Lead |
|---|---|---|---|
| Series A | 2020-11 | $12M | Accel |
| Series B | 2022-05 | $100M | CRV, Insight Partners |
| Series C | 2025-04 | $160M | Accel |

The fact that a company holding $272M of cumulative capital provides the Personal plan that this series uses as "zero-cost infrastructure" is, in itself, an interesting asymmetry. The structural reason for that asymmetry is unpacked below.

---

## Traditional VPNs are hub-and-spoke

Picture a corporate VPN. Laptop → client app → company gateway → internal network. Every packet passes through the central hub (the gateway) once. Even when two employees connect to each other's laptops, traffic first has to go up to the gateway and back down.

> ### Hold on — let's pause here for a sec
>
> **"What exactly are a VPN and a gateway?"**
>
> - **VPN (Virtual Private Network)** — A **virtual private network** layered on top of the Internet. It defines a private IP range that's invisible to outsiders, letting nodes inside it communicate as if they were on the same LAN. Packets typically flow **encapsulated inside an encrypted tunnel**.
> - **Gateway** — A **gatekeeper node that receives packets from one network and forwards them to another**. A home router is a gateway between the home LAN and the Internet; a corporate VPN server is a gateway between the company LAN and the Internet.

<div class="hub-spoke" style="margin:1.5rem 0">
  <div class="hs-grid">
    <div class="hs-panel hs-hub">
      <div class="hs-title">Hub-and-Spoke (traditional VPN)</div>
      <div class="hs-diagram">
        <div class="hs-center hs-server">VPN<br>Gateway</div>
        <div class="hs-node hs-n1">Laptop A</div>
        <div class="hs-node hs-n2">Laptop B</div>
        <div class="hs-node hs-n3">Laptop C</div>
        <div class="hs-node hs-n4">Internal LAN</div>
      </div>
      <ul class="hs-traits">
        <li>All traffic passes through the gateway (1 extra hop)</li>
        <li>Gateway is a single point of failure</li>
        <li>If geographically far, all traffic detours there</li>
      </ul>
    </div>
    <div class="hs-panel hs-mesh">
      <div class="hs-title">Mesh (Tailscale)</div>
      <div class="hs-diagram hs-mesh-diag">
        <div class="hs-node hs-m1">Node A</div>
        <div class="hs-node hs-m2">Node B</div>
        <div class="hs-node hs-m3">Node C</div>
        <div class="hs-node hs-m4">Node D</div>
      </div>
      <ul class="hs-traits">
        <li>Nodes talk P2P directly; no traffic touches a central server</li>
        <li>The central server only handles key exchange and coordination</li>
        <li>Geographically close nodes get a short path</li>
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

This model is great for enforcing corporate security policy at a single point, but it's awkward for a scenario where two home laptops set up a Korean-IP bypass. The Busan laptop could just play the gateway role itself — except that requires the two nodes to talk directly. And two home laptops behind two layers of NAT generally cannot talk directly. Even if the outside knocks on port 22 of the home router, the router has no way of knowing **which internal device to forward to**. Mesh VPNs solve this problem differently.

---

## Mesh VPN — nodes talk directly

The premise of a mesh VPN is simple: **skip the central gateway and let nodes connect to each other directly.** Simple to state, hard to execute. As noted above, when both nodes are behind NAT, neither can be the one to accept a connection first.

The trick is for **both peers to fire outbound packets at each other simultaneously** (hole punching, covered in depth in Part 3). For that to happen, somebody has to send a "now — fire at the same time" signal to both peers. The job of carrying that signal is the **coordination server** in a mesh VPN.

This is where the core split of a mesh VPN appears: think of communication as two distinct planes.

<div class="plane-split" style="margin:1.5rem 0">
  <div class="ps-grid">
    <div class="ps-panel ps-control">
      <div class="ps-head">
        <div class="ps-tag">Control Plane</div>
        <div class="ps-by">Tailscale coordination server</div>
      </div>
      <ul class="ps-list">
        <li>Registers and distributes each node's <strong>WireGuard public key</strong></li>
        <li>Distributes node lists, ACLs, and MagicDNS mappings</li>
        <li>Relays hole-punching signals between peers (DERP)</li>
        <li>Actual data traffic <strong>does not flow through here</strong></li>
      </ul>
      <div class="ps-foot">Centralized — managed in one place</div>
    </div>
    <div class="ps-panel ps-data">
      <div class="ps-head">
        <div class="ps-tag">Data Plane</div>
        <div class="ps-by">Node ↔ node (WireGuard)</div>
      </div>
      <ul class="ps-list">
        <li><strong>E2E-encrypted tunnel</strong> between nodes</li>
        <li>Most of the time flows P2P direct</li>
        <li>Does not pass through Tailscale's company infrastructure</li>
        <li>The company structurally cannot see traffic content</li>
      </ul>
      <div class="ps-foot">Distributed — node to node directly</div>
    </div>
  </div>
  <p class="ps-cap">The coordination server only handles keys and metadata; actual packets travel between nodes.</p>
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

This split determines almost every property of a mesh VPN.

- **The company cannot see traffic content** — the data plane is end-to-end encrypted between nodes, with keys generated inside the nodes themselves. The coordination server only receives public keys.
- **Company-side infrastructure costs are small** — the coordination server only handles metadata (node lists, ACLs, keys), so even if a single user watches video all day, the company-side traffic barely grows.
- **Things keep working for a while even if the company goes down** — if nodes have already cached keys and peer info, the data plane keeps flowing while the coordination server is briefly down.

DERP relay is in the same vein — when UDP is blocked and P2P direct fails, both nodes exchange packets through Tailscale's DERP server, but **DERP still only forwards already-encrypted packets** without decrypting them. That's why the table of 28 regional DERP RTTs above matters: that infrastructure is provided for free, while it's still structurally guaranteed that the company cannot inspect content.

On top of this structural guarantee, Tailscale also commits to the same promise via external authentication and audits.

> "**Private keys never leave the device. All traffic is end-to-end encrypted, always.**"
>
> "**Tailscale cannot read your traffic.**"
>
> — Tailscale Security ([tailscale.com/security](https://tailscale.com/security))
{: .prompt-info }

- **SOC 2 Type II** certification (AICPA Trust Services Criteria — security / availability / confidentiality)
- Periodic audits by external security firm **Latacora**
- On the code side: peer review + automated static analysis + dependency vulnerability scans

This is where deduction (the data plane is E2E, so the company can't see) meets explicit promise (the company commits not to look). Either alone wouldn't be enough; the trust model gains stability where both guarantees overlap.

For how P2P direct is actually achieved, here's Avery Pennarun's one-line summary.

> "There is no magic bullet for NAT traversal. Tailscale's approach: **try everything at once, and pick the best thing that works.**"
>
> — Avery Pennarun, "How NAT traversal works"
{: .prompt-info }

---

## WireGuard — the data plane standard

The data plane itself isn't something Tailscale invented; it's a separate protocol called **WireGuard**, used as-is. WireGuard is a VPN protocol created by Jason A. Donenfeld, **merged into Linus Torvalds' net-next tree in January 2020 and shipped in the Linux 5.6 mainline (2020-03-29)**.

Its defining feature is a small, clear codebase. Linus's remark, frequently quoted from the LKML in 2018, captures the sentiment.

> "Maybe the code isn't perfect, but I've skimmed it, and **compared to the horrors that are OpenVPN and IPsec, it's a work of art.**"
>
> — Linus Torvalds, LKML (cited in Ars Technica, 2018-08)
{: .prompt-info }

WireGuard's crypto stack is a simple composition of standard building blocks.

| Role | Algorithm |
|---|---|
| Key exchange | Curve25519 |
| Symmetric encryption + authentication | ChaCha20-Poly1305 (AEAD) |
| Hash function | BLAKE2s |
| Key derivation | HKDF |
| Hash table key | SipHash24 |

The handshake adopts the **Noise Protocol Framework's `IK` pattern** (`Noise_IKpsk2_25519_ChaChaPoly_BLAKE2s`) verbatim, finishing in 2 messages. Because there is no algorithm negotiation (no cipher-suite negotiation), downgrade attacks are structurally blocked — the most striking difference from the IPsec/TLS family.

Tailscale doesn't reimplement this; it embeds the **official `wireguard-go` implementation** as-is. Even if there were flaws on the mesh-metadata side, the data plane's encryption inherits the properties of a separate, independently-verified system.

WireGuard's level of trust is confirmed not just by Linus's quote but also by adoption and academic verification.

- **Commercial VPN adoption** — NordVPN, IPVanish, TunnelBear, and others adopt WireGuard as the data plane of their own VPN service (Wikipedia)
- **Formal verification** — In May 2019, INRIA researchers published a **machine-checked proof** of the WireGuard protocol — i.e. its security properties are mathematically proven

So WireGuard stands on three lines of evidence: **(a) Linus accepted it into mainline**, **(b) INRIA published a formal verification**, and **(c) commercial VPNs adopted it directly into their products**. Tailscale's decision to use it without reimplementing it is a natural consequence of that foundation.

---

## The free plan's limits (Personal)

Now to costs. Tailscale's free plan, **Personal**, has the following limits (as of 2026-05, per the official pricing page).

<div class="free-tier" style="margin:1.5rem 0">
  <div class="ft-grid">
    <div class="ft-card">
      <div class="ft-num">6</div>
      <div class="ft-label">Users</div>
      <div class="ft-sub">Up from the previous 3</div>
    </div>
    <div class="ft-card ft-hl">
      <div class="ft-num">∞</div>
      <div class="ft-label">User devices</div>
      <div class="ft-sub">No device count limit</div>
    </div>
    <div class="ft-card">
      <div class="ft-num">3</div>
      <div class="ft-label">ACL groups</div>
      <div class="ft-sub">For policy branching</div>
    </div>
    <div class="ft-card">
      <div class="ft-num">50</div>
      <div class="ft-label">Tagged resources</div>
      <div class="ft-sub">For server / service identification</div>
    </div>
  </div>
  <div class="ft-features">
    <div class="ft-f">Exit node</div>
    <div class="ft-f">Subnet router</div>
    <div class="ft-f">MagicDNS</div>
    <div class="ft-f">Split tunneling</div>
    <div class="ft-f">Tailscale SSH (5 hosts)</div>
    <div class="ft-f">Funnel · Serve</div>
    <div class="ft-f">Global DERP infrastructure</div>
    <div class="ft-f">Zero Trust ACL</div>
  </div>
  <p class="ft-cap">For personal infrastructure, the ceiling is effectively invisible. The 3-node mesh in this series sits well within the device-count limits.</p>
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

What stands out here is that **most of the "advanced features" found on paid plans are also included in the free plan**. Exit node, MagicDNS, ACL, subnet router, access to the DERP infrastructure — almost everything the series covers is in Personal. That contrasts with commercial VPNs, whose free tiers usually impose "data caps" or "server count limits".

### So why give it away

It seems strange at first that commercial infrastructure offers limits this generous for free. But half the answer falls out naturally from the control/data plane split above.

**The traffic flowing through company infrastructure is small.** Even if a user streams 1080p video for five hours between Busan and Fukuoka, the additional cost on Tailscale's company-side infrastructure is just a few KB of messages — key refreshes and metadata sync. Video packets only flow P2P direct between the Fukuoka Mac and the Busan laptop. Put differently, the marginal cost of adding one user is effectively zero.

The other half is the company's GTM (go-to-market) strategy. Tailscale has explicitly chosen the **"let individuals use it for free, convert to paid when their company adopts it"** model. An engineer who has gotten comfortable with the Personal plan on their own laptop, then proposes adopting the same tool at their company, is the cheapest possible sales channel for the company.

The company doesn't dress this up purely as capitalist rationality; it also states it as a mission-level commitment.

> "**If we're going to fix the Internet, there's no point only fixing it for big companies who can pay a lot.**"
>
> — Tailscale official blog
{: .prompt-info }

On top of the funding above ($272M cumulative), the personal free plan is something the company can comfortably absorb on the cost side, while simultaneously serving as the channel through which the next generation of engineers carry adoption into companies.

---

## Why Tailscale, not another mesh VPN

A short summary of why this series chose Tailscale. The mesh VPN / Zero Trust space has plenty of other options.

| Tool | Coordination server | Data plane | Free tier limits | In this series' scenario |
|---|---|---|---|---|
| **Tailscale** | SaaS (run by Tailscale) | WireGuard | 6 users / unlimited devices | What this series adopts |
| Headscale | Self-hosted (open source) | WireGuard | Unlimited (your server) | Need to operate the coordination server yourself |
| ZeroTier | SaaS | Custom protocol | 25 nodes | Node cap fills quickly, and not WireGuard |
| Nebula | Self-hosted | Custom (from Slack) | Unlimited (your PKI) | Need to operate PKI yourself |
| Twingate | SaaS (B2B-focused) | Custom | 5 users, user-device limits | Free tier runs out quickly |
| raw WireGuard | None | WireGuard | Unlimited | Key distribution and NAT traversal entirely DIY. Two-layer home NAT is essentially impossible |
| OpenVPN | Your server | OpenSSL | DIY ops | Hub-and-spoke; a poor fit for home laptops behind NAT |

The two decisive requirements for this scenario are **(a) it must work for free** and **(b) it must traverse NAT on both sides automatically**. (a) rules out the self-hosted operational burden of Headscale and Nebula; (b) rules out the hub-and-spoke shape of raw WireGuard and OpenVPN. The remaining candidates are Tailscale and ZeroTier; ZeroTier is weakened by its free-tier cap (25 nodes) and by not using the WireGuard protocol.

---

## Summary

| Question | Answer |
|---|---|
| Motivation | After 1+ year of living in Fukuoka, the pattern of Korean payments / banking / content being blocked from foreign IPs piled up |
| Solution | A garage laptop at the family home in Busan as an unattended exit node, operated remotely from a Mac in Fukuoka over SSH |
| Operational result (measured) | P2P direct 50ms / Tunnel DOWN 24.9 Mbps / 15+ hours of unattended stability / 0 self-healing triggers |
| Tailscale (the company) | Founded 2019 in Toronto, four ex-Googlers (including Brad Fitzpatrick), $272M cumulative funding |
| Mesh VPN core idea | WireGuard (data plane) + Tailscale coordination server (control plane), split apart |
| WireGuard's strengths | Linux 5.6 mainline, Noise IK + ChaCha20-Poly1305, code simplicity ("a work of art" — Linus) |
| Why the company can't see traffic | Data plane is E2E between nodes, private keys never leave the node, DERP only forwards ciphertext |
| Why "free" is feasible | Marginal cost on company infrastructure ≈ 0 + PLG sales model + stated mission |
| Personal plan | 6 users / unlimited devices / Exit Node, MagicDNS, ACL all included |

If Part 1 was the series' motivation, results, and the structural reasons that make them possible, Part 2 moves on to actually building that infrastructure.

---

## References

- [`Epheria/tailnet-ops`](https://github.com/Epheria/tailnet-ops) — All operational code for this series
- Donenfeld, J. A. *WireGuard: Next Generation Kernel Network Tunnel.* NDSS 2017. ([wireguard.com/papers/wireguard.pdf](https://www.wireguard.com/papers/wireguard.pdf))
- Pennarun, A. *How NAT traversal works.* Tailscale Blog. ([tailscale.com/blog/how-nat-traversal-works](https://tailscale.com/blog/how-nat-traversal-works))
- Tailscale. *How Tailscale works.* Tailscale Blog. ([tailscale.com/blog/how-tailscale-works](https://tailscale.com/blog/how-tailscale-works))
- Tailscale. *Pricing — Personal plan.* ([tailscale.com/pricing](https://tailscale.com/pricing))
- *Tailscale.* Wikipedia. ([en.wikipedia.org/wiki/Tailscale](https://en.wikipedia.org/wiki/Tailscale))
- *WireGuard.* Wikipedia. ([en.wikipedia.org/wiki/WireGuard](https://en.wikipedia.org/wiki/WireGuard))
- Salter, J. *WireGuard VPN review: A new type of VPN offers serious advantages.* Ars Technica, 2018-08. (Source for the Linus Torvalds quote)

---

## Next post

Part 2 covers, all in one go, actually turning the Busan family-home laptop into an unattended exit node, plus the self-healing system for unattended ops, plus the security audit. It walks through **the full flow of what to finish in a single visit to the family home**, along with the remote-ops model that lets you add new devices from Fukuoka without ever going back to Busan.

> Part 2 — Family-home setup + unattended ops + security (coming soon)
{: .prompt-info }
