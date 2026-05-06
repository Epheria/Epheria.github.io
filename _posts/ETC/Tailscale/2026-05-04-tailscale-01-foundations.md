---
title: "Tailscale 시리즈 1편 — 창고 노트북으로 만든 한국 IP 우회 인프라 (동기·실측·구조)"
date: 2026-05-04 18:00:00 +0900
categories: [ETC, Tailscale]
tags: [tailscale, network, vpn, wireguard, mesh-vpn, p2p, exit-node, infrastructure]
toc: true
toc_sticky: true
difficulty: beginner
chart: true
tldr:
  - 후쿠오카 1년+ 누적된 한국 IP 필요성을, 창고 노트북 + Tailscale Personal Free로 해결
  - 3 노드 mesh (부산 Win + 후쿠오카 Mac + 후쿠오카 Win) 가동 — P2P direct 50ms / Tunnel DOWN 24.9 Mbps / 무인 15+ 시간 안정
  - Tailscale은 mesh VPN — 데이터 평면(WireGuard, E2E) + 제어 평면(coordination) 분리. 트래픽이 회사 인프라 미경유
  - 회사는 2019년 토론토 창업, Google 출신 4인 (Brad Fitzpatrick 포함), 누적 펀딩 $272M. Personal 플랜이 6 user / 디바이스 무제한 무료
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

## 이 시리즈가 다루는 것

후쿠오카에서 1년 넘게 살면서 한국 IP가 아쉬운 순간이 꾸준히 쌓였습니다. 한국 결제·은행·일부 콘텐츠는 해외 IP에서는 정상 동작하지 않거나 추가 인증을 요구하고, 그때마다 상용 한국 VPN을 잠깐 켜는 패턴은 비용·신뢰·OS 호환 모두에서 깔끔하지 않았습니다.

해결책으로 부산 본가 창고에 7년째 처박혀있던 케케묵은 노트북(Samsung Galaxy Book 950SBE, **Intel Core i7-8565U / 16GB / Windows 11 Home**)을 끌어내 무인 exit node로 부활시키고, 후쿠오카 측 Mac에서 SSH로 원격 운영하는 개인 Tailscale 인프라를 셋업했습니다. 며칠간의 검증 결과 **Tunnel DOWN 24.9 Mbps · P2P direct 50ms RTT · 무인 15시간+ 안정 가동** — 새 하드웨어 없이도 한국 IP 우회와 원격 운영이 충분히 가능하다는 게 데이터로 확인됐습니다.

이 시리즈는 그 전체 과정을 3편에 나누어 정리합니다.

| # | 제목 | 다루는 것 |
|---|---|---|
| **1편 (이 글)** | 동기·실측·구조 | 가동 중인 인프라의 측정값 + Tailscale·메시 VPN·WireGuard의 구조 |
| 2편 | 본가 셋업 + 무인 운영 + 보안 | 1회 방문 셋업 / 자가치유 SchTasks / 보안 감사 |
| 3편 | 작동 원리 + 비용·한계 | DERP·MagicDNS·hole punching / 연 1만 원 비용 회고 |

이 1편은 **이미 가동 중인 인프라의 측정값을 먼저 보여주고**, 그게 가능한 구조적 근거를 풀어가는 흐름입니다.

> ### 잠깐, 이건 짚고 넘어가자
>
> **"exit node? tailnet? peer? 시작 전에 용어가 너무 많은데?"**
>
> 본문에 자주 등장할 핵심 4개만 짧게 정리하고 들어갑니다.
>
> - **Tailnet** — 한 사용자(또는 조직)에 묶인 Tailscale 노드들의 **사설 가상 네트워크**. 우리 시나리오에서는 부산 노트북 + 후쿠오카 Mac + 후쿠오카 Windows 데스크톱 세 노드가 한 tailnet에 들어있습니다.
> - **Peer (피어)** — tailnet 안의 한 노드. **클라이언트/서버 구분이 없고**, 모두 동등한 위치에서 서로 직접 통신할 수 있는 멤버라는 뜻입니다. P2P(peer-to-peer)의 그 peer.
> - **Mesh (메시)** — 피어들이 중앙 허브를 거치지 않고 **서로 직접 연결**되는 망 구조. 뒤에서 hub-and-spoke와 비교해 자세히 다룹니다.
> - **Exit node** — tailnet 안의 한 노드를 "이 노드를 통해 인터넷으로 나가겠다"라고 지정하는 기능. 후쿠오카 Mac이 부산 노트북을 exit node로 잡으면, **Mac의 인터넷 트래픽이 모두 부산 노트북을 거쳐 한국 IP로 나갑니다**. 이 시리즈가 만드는 핵심 도구가 이것입니다.

---

## 시스템 한눈에 — 현재 가동 중

Tailscale 관리 콘솔에 잡힌 노드 상태입니다. Personal Free 플랜, 두 노드는 항시 Connected, 부산 노트북은 Exit Node로 광고 중.

![Tailscale admin console — 부산 본가 노트북 Exit Node 가동, 후쿠오카 Mac 연결 중](/assets/img/post/ETC/Tailscale/admin-console-machines.png)
_관리 콘솔 한 화면에 Win 11(부산)과 macOS 26(후쿠오카)이 같은 tailnet에 묶여있습니다. **OS를 가리지 않는 메시**가 Tailscale의 강점 중 하나입니다._

핵심 수치를 카드 네 장으로 요약합니다 (2026-05-04 ~ 05-05, 30시간 연속 측정 기준).

<div class="metric-cards" style="margin:1.5rem 0">
  <div class="mc-grid">
    <div class="mc-card mc-blue">
      <div class="mc-label">Uptime (무인)</div>
      <div class="mc-value">15h+</div>
      <div class="mc-sub">자가치유 트리거 0건</div>
    </div>
    <div class="mc-card mc-green">
      <div class="mc-label">Wi-Fi 신호</div>
      <div class="mc-value">99%</div>
      <div class="mc-sub">365 샘플 모두 99% 고정</div>
    </div>
    <div class="mc-card mc-purple">
      <div class="mc-label">DERP RTT (Tokyo)</div>
      <div class="mc-value">28ms</div>
      <div class="mc-sub">P2P direct (DERP 미경유)</div>
    </div>
    <div class="mc-card mc-orange">
      <div class="mc-label">Tunnel DOWN</div>
      <div class="mc-value">24.9 Mbps</div>
      <div class="mc-sub">1080p 5x · 4K 근접</div>
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

## 3 노드 mesh 토폴로지

Tailnet에는 현재 세 개의 노드가 묶여있습니다. 부산의 exit node 한 대, 후쿠오카 측 클라이언트 두 대(Mac + Windows). 노드끼리는 P2P direct로 연결되고, 직통이 안 되는 경우만 Tokyo DERP로 fallback합니다(가까운 동아시아 리전).

<div class="mesh-topo" style="margin:1.5rem 0">
  <div class="mt-grid">
    <div class="mt-side">
      <div class="mt-tag">한국 (Exit Node)</div>
      <div class="mt-node mt-busan">
        <div class="mt-name">samsung-home-laptop</div>
        <div class="mt-os">Windows 11 Home</div>
        <div class="mt-spec">i7-8565U · 16GB</div>
        <div class="mt-loc">부산 본가 · KT GiGA 5G</div>
      </div>
    </div>
    <div class="mt-center">
      <div class="mt-cloud">
        <div class="mt-cloud-title">tailnet</div>
        <div class="mt-cloud-sub">P2P direct<br>Tokyo DERP fallback</div>
      </div>
    </div>
    <div class="mt-side">
      <div class="mt-tag">일본 (클라이언트)</div>
      <div class="mt-node mt-japan">
        <div class="mt-name">fukuoka-mac</div>
        <div class="mt-os">macOS 26.1</div>
        <div class="mt-spec">메인 노트북</div>
        <div class="mt-loc">후쿠오카 자택</div>
      </div>
      <div class="mt-node mt-japan">
        <div class="mt-name">fukuoka-home-pc</div>
        <div class="mt-os">Windows 11</div>
        <div class="mt-spec">데스크톱</div>
        <div class="mt-loc">후쿠오카 자택</div>
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

| 노드 | 역할 | OS | 위치 | 연결 모드 |
|---|---|---|---|---|
| samsung-home-laptop | Exit Node (한국 IP 출구) | Windows 11 Home | 부산 본가 | direct |
| fukuoka-mac | 메인 클라이언트 | macOS 26.1 | 후쿠오카 자택 | direct |
| fukuoka-home-pc | 추가 클라이언트 | Windows 11 | 후쿠오카 자택 | direct |

세 노드 모두 **direct P2P** — DERP 중계 없이 직접 통신합니다. 가정 NAT 두 겹을 통과하면서도 직통이 성립하는 메커니즘은 hole punching이라 부르며, 본 시리즈 3편에서 자세히 다룹니다.

> ### 잠깐, 이건 짚고 넘어가자
>
> **"표 마지막 칸 'direct'는 무슨 뜻이야? 그리고 IP가 100.64.x.x 인 게 무슨 의미야?"**
>
> 두 가지를 한 번에 짚습니다.
>
> **(1) 통신 경로 — direct vs DERP**
>
> - **P2P direct** — 두 노드가 인터넷 위에서 서로의 공인 IP·포트로 **직접** UDP 패킷을 주고받는 상태. 가장 빠르고, **Tailscale 회사 인프라를 트래픽이 거치지 않습니다**.
> - **DERP relay** — 직통이 안 될 때 Tailscale의 공용 중계 서버(Designated Encrypted Relay for Packets)를 경유하는 fallback. DERP는 **암호화된 패킷을 그대로 전달만 하고 복호화하지 않습니다**.
>
> **(2) Tailscale IP — `100.64.0.0/10`**
>
> Tailscale이 노드에 부여하는 사설 IP는 `100.64.x.x` 모양입니다. 이 대역은 원래 ISP의 CGNAT(Carrier-Grade NAT) 용도로 예약된 공간인데, Tailscale이 이 대역을 **그대로 빌려 자기 가상 네트워크의 주소로 씁니다**. 인터넷에서 직접 도달 불가능한 사설 대역이므로 다른 인터넷 트래픽과 충돌하지 않습니다.

---

## 실측 데이터

### DERP latency — 부산 노트북 기준

`tailscale netcheck`가 측정한 DERP 서버까지의 RTT 핵심 8개 리전입니다. 도쿄가 28ms로 압도적으로 가깝고, 동아시아 4개 리전이 모두 100ms 이내입니다.

| 리전 | RTT (부산 → DERP) | 대륙 |
|---|---|---|
| **Tokyo** | **28ms** | 동아시아 (사용 중) |
| Hong Kong | 61ms | 동아시아 |
| Singapore | 74ms | 동남아 |
| Bengaluru | 100ms | 남아시아 |
| San Francisco | 127ms | 북미 서부 |
| Ashburn | 190ms | 북미 동부 |
| Sydney | 199ms | 오세아니아 |
| London | 238ms | 유럽 |

전체 28개 리전 측정값이 필요하면 `tailscale netcheck` 한 줄로 직접 측정 가능합니다.

도쿄 28ms가 의미하는 것: hole punching이 실패해 DERP 중계로 떨어져도, 부산↔후쿠오카 RTT는 무료 공용 중계망 위에서 여전히 동일 대륙권 best-case 수준에 있습니다. **무료로 제공되는 글로벌 DERP 인프라**가 비용 모델의 큰 축이라는 점을 미리 짚어둡니다.

### 대역폭 — Tunnel UP/DOWN vs 인터넷 백본

50MB 파일 기준 양방향 scp 측정 결과와 인터넷 백본을 함께 비교합니다. **Tunnel DOWN이 24.9 Mbps로 전체 병목** — 부산 가정 회선의 업로드 측 한계가 그대로 드러납니다.

<div class="chart-wrapper">
  <div class="chart-title">대역폭 비교 (Mbps, 50MB 파일 기준)</div>
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

해석:
- 인터넷 백본은 245 Mbps인데 **Tunnel UP은 59.2 Mbps** — WireGuard 암호화 + Wi-Fi 채널 + 오버헤드가 누적된 결과. i7-8565U(15W TDP)의 WireGuard cap이 ~100~200 Mbps 수준이라는 일반 벤치와 정합합니다.
- **Tunnel DOWN 24.9 Mbps**는 부산 가정 FTTH 회선의 업로드 측 비대칭 한계 — 한국 가정 인터넷의 정상적인 다운 ≫ 업 구조 그대로입니다.
- 1080p 영상 스트리밍 평균 5 Mbps 기준 **5x 여유**, 4K(~25 Mbps)는 cap 근접해 마진 없음.

### 안정성 — 30시간 연속 메트릭 368 샘플

5분 주기로 자동 수집된 메트릭의 7일 통계입니다. 핵심 지표 모두 표준편차가 사실상 0에 가까운 안정 상태.

| 항목 | 평균 | min | p50 | p95 | max | 샘플 |
|---|---|---|---|---|---|---|
| Battery (AC 연결) | 84.8% | 84 | 85 | 85 | 85 | 368 |
| Wi-Fi signal | 99.0% | 99 | 99 | 99 | 99 | 365 |
| RTT 8.8.8.8 | 29.3ms | 28 | 29 | 30 | 90 | 368 |
| RTT 1.1.1.1 | 9.2ms | 8 | 9 | 10 | 25 | 368 |

자가치유 시스템의 작동 기록:

<div class="health-cards" style="margin:1.5rem 0">
  <div class="hc-grid">
    <div class="hc-card hc-good">
      <div class="hc-num">0</div>
      <div class="hc-label">Tailscale 재시작</div>
      <div class="hc-sub">5분 헬스체크가 트리거한 횟수</div>
    </div>
    <div class="hc-card hc-good">
      <div class="hc-num">0</div>
      <div class="hc-label">sshd 재시작</div>
      <div class="hc-sub">동일 — 죽은 적 없음</div>
    </div>
    <div class="hc-card hc-good">
      <div class="hc-num">0</div>
      <div class="hc-label">SSH 인증 실패</div>
      <div class="hc-sub">최근 24시간 brute force 0건</div>
    </div>
    <div class="hc-card hc-good">
      <div class="hc-num">5/5</div>
      <div class="hc-label">SchTasks Ready</div>
      <div class="hc-sub">자가치유 작업 5종 모두 정상</div>
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

### 재부팅 자동 복구 — 안정화 후 평균 1분 30초

원격 운영의 안전망으로 가장 중요한 시나리오는 "재부팅 후 사람 손 안 대고 SSH가 살아 돌아오는가"입니다. 클램쉘 모드(덮개 닫힘) 포함 4번의 재부팅 검증 결과:

| 차수 | 부팅 완료 | SSH 복구 | 헬스체크 첫 실행 | 비고 |
|---|---|---|---|---|
| 1차 | n/a | ~5분 | 재부팅 +19s | 첫 시도 (콜드 스타트) |
| 2차 | +29s | ~1분 34초 | n/a | |
| 3차 | +29s | ~1분 | +48s | |
| **4차 (덮개 닫힘)** | +28s | n/a | +80s | **클램쉘 검증** |

1차는 DNS·서비스 초기화 등 콜드 스타트 비용이 누적되어 ~5분, **2차 이후 안정화 구간 평균은 1분 30초**입니다. 클램쉘 검증의 결정적 증거는 `WmiMonitorBasicDisplayParams Count = 0`(활성 모니터 0개) 상태에서 모든 서비스가 정상 기동했다는 점입니다. 즉 본가 가족이 노트북 덮개를 닫아 두어도 인프라는 그대로 동작합니다.

여기까지가 인프라 가동 증명입니다. 아래부터는 이 결과가 가능한 구조적 근거로 넘어갑니다.

---

## Tailscale은 누가 만들고 있는가

먼저 회사 자체를 짚고 갑니다. Tailscale은 **2019년 캐나다 토론토에서 창업**된 회사로, 창업자 네 명은 모두 Google 출신 엔지니어입니다(Wikipedia 기준).

| 창업자 | 비고 |
|---|---|
| Avery Pennarun | CEO. 블로그 글 "How NAT traversal works"가 NAT 입문 자료의 사실상 표준 |
| David Crawshaw | 시스템·언어 영역, Go 생태계와 가까운 경력 |
| David Carney | Chief Strategy Officer |
| Brad Fitzpatrick | **LiveJournal·memcached·Perlbal**의 창시자, 이후 Google에서 Go 언어 코어 팀에서 오래 일함 |

특히 Brad Fitzpatrick의 합류는 무게가 큽니다. Wikipedia에 따르면 그는 **대학 1학년 때 LiveJournal을 시작**해 2005년 1월 Six Apart에 매각, 그 후 **2007년 8월부터 Google Go 코어팀 Staff Software Engineer로 12년 반 근무**하다가 **2020년 1월 퇴사 후 3일 뒤 Tailscale에 "late-stage co-founder"로 합류**했습니다 — 즉 원래 3인(Avery/Crawshaw/Carney)이 2019년 창업한 회사에 4번째 멤버로 늦게 합류한 것입니다. memcached·OpenID·Perkeep 등 인터넷 인프라 공통 기술을 직접 만든 사람이 12년 반 Go팀에 있다가 곧장 옮겨왔다는 시간선은 단순 신생 스타트업과는 다른 신뢰 면을 만들어줍니다.

펀딩도 가볍지 않습니다(Wikipedia).

| 라운드 | 시기 | 액수 | 리드 |
|---|---|---|---|
| Series A | 2020-11 | $12M | Accel |
| Series B | 2022-05 | $100M | CRV, Insight Partners |
| Series C | 2025-04 | $160M | Accel |

총 $272M의 자본이 들어간 회사가 본 시리즈가 "0원 인프라"로 활용하는 Personal 플랜을 제공한다는 점은 그 자체로 흥미로운 비대칭입니다. 그 비대칭의 구조적 근거를 아래에서 풉니다.

---

## 전통 VPN은 hub-and-spoke

회사 VPN을 떠올려보면 됩니다. 노트북 → 클라이언트 앱 → 회사 게이트웨이 → 사내망. 모든 트래픽은 게이트웨이라는 중앙 허브를 한 번 거칩니다. 두 사원이 서로의 노트북에 접속하더라도 트래픽은 일단 게이트웨이로 올라갔다가 내려옵니다.

> ### 잠깐, 이건 짚고 넘어가자
>
> **"VPN이랑 게이트웨이가 정확히 뭐야?"**
>
> - **VPN (Virtual Private Network)** — 인터넷 위에 깔린 **가상의 사설 네트워크**. 외부에서는 안 보이는 사설 IP 대역을 두고, 그 안의 노드들이 마치 같은 LAN에 있는 것처럼 통신할 수 있게 해줍니다. 패킷은 보통 **암호화 터널 안에 캡슐화되어** 흐릅니다.
> - **게이트웨이 (Gateway)** — 한 네트워크와 다른 네트워크 사이에서 **패킷을 받아 넘기는 관문 노드**. 가정 라우터도 가정 LAN ↔ 인터넷의 게이트웨이고, 회사 VPN 서버도 사내망 ↔ 인터넷의 게이트웨이입니다.

<div class="hub-spoke" style="margin:1.5rem 0">
  <div class="hs-grid">
    <div class="hs-panel hs-hub">
      <div class="hs-title">Hub-and-Spoke (전통 VPN)</div>
      <div class="hs-diagram">
        <div class="hs-center hs-server">VPN<br>Gateway</div>
        <div class="hs-node hs-n1">노트북 A</div>
        <div class="hs-node hs-n2">노트북 B</div>
        <div class="hs-node hs-n3">노트북 C</div>
        <div class="hs-node hs-n4">사내망</div>
      </div>
      <ul class="hs-traits">
        <li>모든 트래픽이 게이트웨이 경유 (1 hop 추가)</li>
        <li>게이트웨이가 단일 장애점</li>
        <li>지리적으로 멀면 전 트래픽이 그쪽으로 우회</li>
      </ul>
    </div>
    <div class="hs-panel hs-mesh">
      <div class="hs-title">Mesh (Tailscale)</div>
      <div class="hs-diagram hs-mesh-diag">
        <div class="hs-node hs-m1">노드 A</div>
        <div class="hs-node hs-m2">노드 B</div>
        <div class="hs-node hs-m3">노드 C</div>
        <div class="hs-node hs-m4">노드 D</div>
      </div>
      <ul class="hs-traits">
        <li>노드끼리 P2P 직통, 중앙 서버 트래픽 미경유</li>
        <li>중앙 서버는 키 교환·조정만 담당</li>
        <li>지리적으로 가까운 노드끼리는 짧은 경로</li>
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

이 모델은 사내 보안 정책을 한 점에서 강제하기엔 좋지만, 가정 노트북 두 대로 한국 IP 우회 인프라를 만드는 시나리오에서는 어색합니다. 부산 노트북이 게이트웨이 역할까지 하면 되는데, 그러려면 두 노드가 직통으로 통신할 수 있어야 합니다. 그리고 NAT 두 겹 뒤의 가정 노트북 둘이 직통으로 통신하는 일은 일반적으로 안 됩니다 — 외부에서 가정 라우터의 22번 포트를 두드려도, 라우터는 "내부 어느 디바이스로 보낼지" 모르는 구조이기 때문입니다. 메시 VPN은 이 문제를 다른 방식으로 풉니다.

---

## 메시 VPN — 노드끼리 직통

메시 VPN의 발상은 단순합니다. **중앙 게이트웨이를 거치지 말고 노드끼리 직접 연결하자.** 그러나 발상은 단순해도 실행은 어렵습니다. 위에서 짚은 대로 양쪽 노드가 모두 NAT 뒤에 있으면 누구도 먼저 접속을 받을 수 없습니다.

해결의 단서는 **두 피어가 동시에 서로에게 outbound를 쏘는** 것입니다(hole punching, 3편에서 깊이 다룸). 그러려면 누군가가 두 피어에게 "지금이다, 동시에 쏴라"라고 신호를 보내야 합니다. 그 신호 담당이 메시 VPN의 **조정 서버(coordination server)** 입니다.

여기서 메시 VPN의 핵심 분리가 등장합니다. 통신을 두 평면으로 나눠 생각하는 것입니다.

<div class="plane-split" style="margin:1.5rem 0">
  <div class="ps-grid">
    <div class="ps-panel ps-control">
      <div class="ps-head">
        <div class="ps-tag">Control Plane</div>
        <div class="ps-by">Tailscale coordination server</div>
      </div>
      <ul class="ps-list">
        <li>각 노드의 <strong>WireGuard 공개 키</strong> 등록·배포</li>
        <li>노드 목록·ACL·MagicDNS 매핑 배포</li>
        <li>피어 간 hole punching 신호 중계 (DERP)</li>
        <li>실제 데이터 트래픽은 <strong>여기 안 흐른다</strong></li>
      </ul>
      <div class="ps-foot">중앙화 — 한 곳에서 관리</div>
    </div>
    <div class="ps-panel ps-data">
      <div class="ps-head">
        <div class="ps-tag">Data Plane</div>
        <div class="ps-by">노드 ↔ 노드 (WireGuard)</div>
      </div>
      <ul class="ps-list">
        <li>노드 사이 <strong>E2E 암호화 터널</strong></li>
        <li>대부분의 시간 P2P direct로 흐름</li>
        <li>Tailscale 회사 인프라 미경유</li>
        <li>회사가 트래픽 내용을 못 본다 (구조적 보장)</li>
      </ul>
      <div class="ps-foot">분산 — 노드끼리 직접</div>
    </div>
  </div>
  <p class="ps-cap">조정 서버는 키와 메타데이터만 다루고, 실제 패킷은 노드끼리 주고받는다.</p>
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

이 분리가 메시 VPN의 거의 모든 성질을 결정합니다.

- **회사가 트래픽 내용을 못 본다** — 데이터 평면은 노드끼리 E2E 암호화이고 키는 노드 안에서 만들어집니다. 조정 서버는 공개 키만 받습니다.
- **회사 인프라 비용이 작다** — 조정 서버는 메타데이터(노드 목록·ACL·키)만 다루므로 사용자 1명이 하루 종일 영상을 봐도 회사 측 트래픽은 거의 늘지 않습니다.
- **회사가 죽어도 한동안 동작한다** — 노드들이 이미 키와 피어 정보를 캐시했다면 조정 서버가 잠깐 죽어도 데이터 평면은 그대로 흐릅니다.

DERP relay도 같은 맥락입니다 — UDP가 막혀서 P2P direct가 실패하면 양 노드가 Tailscale의 DERP 서버를 통해 패킷을 주고받지만, **DERP는 여전히 암호화된 패킷을 그대로 전달**할 뿐 복호화하지 않습니다. 위에서 측정한 28개 리전 DERP RTT 표가 의미 있는 이유 — 그 인프라가 무료로 제공되면서도 회사가 내용을 들여다보지 않는다는 것이 구조적으로 보장됩니다.

이 구조적 보장 위에, Tailscale은 외부 인증과 감사로도 같은 약속을 명시합니다.

> "**Private keys never leave the device. All traffic is end-to-end encrypted, always.**"
>
> "**Tailscale cannot read your traffic.**"
>
> — Tailscale Security ([tailscale.com/security](https://tailscale.com/security))
{: .prompt-info }

- **SOC 2 Type II** 인증 (AICPA Trust Services Criteria — security / availability / confidentiality)
- 외부 보안 회사 **Latacora**의 정기 감사
- 코드 측: 피어 리뷰 + 자동화된 정적 분석 + 의존성 취약점 스캔

추론(데이터 평면이 E2E라 회사가 못 본다)이 명시적 약속(회사가 못 본다고 약속한다)과 만나는 지점입니다. 둘 중 한쪽만으로는 부족하고, 두 보장이 겹치는 게 신뢰 모델의 안정성을 만듭니다.

P2P direct를 어떻게 만드는지에 대한 Avery Pennarun의 한 줄 요약은 다음과 같습니다.

> "There is no magic bullet for NAT traversal. Tailscale's approach: **try everything at once, and pick the best thing that works.**"
>
> — Avery Pennarun, "How NAT traversal works"
{: .prompt-info }

---

## WireGuard — 데이터 평면의 표준

데이터 평면 자체는 Tailscale이 만든 것이 아니라 **WireGuard**라는 별도 프로토콜을 그대로 가져다 씁니다. WireGuard는 Jason A. Donenfeld가 만든 VPN 프로토콜로, **2020년 1월 Linus Torvalds의 net-next 트리에 머지되어 Linux 5.6 (2020-03-29) 메인라인에 포함**됐습니다.

코드베이스가 작고 명확한 것이 가장 큰 특징인데, Linus의 다음 발언이 2018년 LKML 인용으로 자주 회자됩니다.

> "Maybe the code isn't perfect, but I've skimmed it, and **compared to the horrors that are OpenVPN and IPsec, it's a work of art.**"
>
> — Linus Torvalds, LKML (Ars Technica 2018-08 인용)
{: .prompt-info }

WireGuard의 암호화 스택은 표준 빌딩 블록을 단순 조합합니다.

| 역할 | 알고리즘 |
|---|---|
| 키 교환 | Curve25519 |
| 대칭 암호화 + 인증 | ChaCha20-Poly1305 (AEAD) |
| 해시 함수 | BLAKE2s |
| 키 파생 | HKDF |
| 해시테이블 키 | SipHash24 |

핸드셰이크는 **Noise Protocol Framework의 `IK` 패턴**(`Noise_IKpsk2_25519_ChaChaPoly_BLAKE2s`)을 그대로 채택해 2-메시지로 끝납니다. 알고리즘 협상(cipher suite negotiation) 자체가 없어서 다운그레이드 공격이 구조적으로 막혀있다는 점이 IPsec/TLS 가족과 가장 큰 차이입니다.

Tailscale은 이걸 자체 재구현하지 않고 **공식 `wireguard-go` 구현**을 그대로 끼워 넣습니다. 메시 메타데이터 측에 결함이 있더라도 데이터 평면 암호화는 별도 시스템의 특성을 그대로 물려받습니다.

WireGuard의 신뢰받는 정도는 Linus의 발언만이 아니라 채택과 학술 검증에서도 확인됩니다.

- **상용 VPN 채택** — NordVPN, IPVanish, TunnelBear 등이 자체 VPN의 데이터 평면으로 WireGuard를 직접 채택 (Wikipedia)
- **형식 검증** — 2019년 5월 INRIA 연구진이 WireGuard 프로토콜의 **machine-checked proof**를 발표. 즉 보안 속성이 수학적으로 증명됨

이로써 WireGuard는 **(a) Linus가 메인라인에 받아주고**, **(b) INRIA가 형식 검증을 발표하고**, **(c) 상용 VPN들이 자기 제품에 그대로 채택하는** 3중 근거 위에 서 있는 셈입니다. Tailscale이 자체 재구현 없이 그대로 가져다 쓰는 결정은 이 근거 위에서 자연스럽습니다.

---

## 무료 플랜의 한도 (Personal)

이제 비용 이야기로 옮깁니다. Tailscale의 무료 플랜인 **Personal**은 다음 한도를 가집니다(2026-05 기준 공식 페이지).

<div class="free-tier" style="margin:1.5rem 0">
  <div class="ft-grid">
    <div class="ft-card">
      <div class="ft-num">6</div>
      <div class="ft-label">사용자</div>
      <div class="ft-sub">기존 3명에서 확대</div>
    </div>
    <div class="ft-card ft-hl">
      <div class="ft-num">∞</div>
      <div class="ft-label">사용자 디바이스</div>
      <div class="ft-sub">개수 제한 없음</div>
    </div>
    <div class="ft-card">
      <div class="ft-num">3</div>
      <div class="ft-label">ACL 그룹</div>
      <div class="ft-sub">정책 분기용</div>
    </div>
    <div class="ft-card">
      <div class="ft-num">50</div>
      <div class="ft-label">태그된 리소스</div>
      <div class="ft-sub">서버·서비스 식별</div>
    </div>
  </div>
  <div class="ft-features">
    <div class="ft-f">Exit node</div>
    <div class="ft-f">Subnet router</div>
    <div class="ft-f">MagicDNS</div>
    <div class="ft-f">Split tunneling</div>
    <div class="ft-f">Tailscale SSH (5 hosts)</div>
    <div class="ft-f">Funnel · Serve</div>
    <div class="ft-f">DERP 글로벌 인프라</div>
    <div class="ft-f">Zero Trust ACL</div>
  </div>
  <p class="ft-cap">개인 인프라용으로는 사실상 천장이 안 보이는 수준. 본 시리즈의 3 노드 mesh도 디바이스 수 한도 안에서 한참 여유.</p>
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

여기서 눈에 띄는 점은 **유료 플랜에 있는 "고급 기능" 대부분이 무료 플랜에도 그대로 들어있다**는 사실입니다. Exit node, MagicDNS, ACL, Subnet router, DERP 인프라 사용권 — 본 시리즈가 다루는 것 거의 전부가 Personal에 포함됩니다. 상용 VPN의 무료 플랜이 보통 "데이터 한도"나 "서버 수 제한"을 거는 것과 대비됩니다.

### 그래서 왜 무료로 푸는가

상용 인프라가 이런 한도를 무료로 푼다는 게 처음엔 어색하게 보입니다. 그러나 위 control/data plane 분리에서 답의 절반이 자연스럽게 따라옵니다.

**회사 인프라에 흐르는 트래픽이 작다.** 사용자가 부산↔후쿠오카로 1080p 영상을 5시간 시청해도, Tailscale 회사 측 인프라에 추가되는 비용은 키 갱신·메타데이터 동기화 같은 메시지 몇 KB뿐입니다. 영상 패킷은 후쿠오카 Mac과 부산 노트북 사이 P2P direct로만 흐릅니다. 사용자 한 명을 늘리는 한계 비용이 사실상 0에 가깝다는 뜻입니다.

남은 절반은 회사의 GTM(go-to-market) 전략 측면입니다. Tailscale은 명시적으로 **"개인은 무료로 충분히 쓰게 두고, 회사가 도입하는 시점에 유료로 전환"** 모델을 택했습니다. 엔지니어가 자기 노트북에서 Personal 플랜으로 익숙해진 뒤, 자기 회사에서 같은 도구를 쓰자고 제안하는 흐름이 회사 입장에선 가장 싼 영업 채널입니다.

회사 측은 이를 자본주의적 합리성만으로 포장하지 않고, 미션 차원의 발언으로도 명시합니다.

> "**If we're going to fix the Internet, there's no point only fixing it for big companies who can pay a lot.**"
>
> — Tailscale 공식 블로그
{: .prompt-info }

위에서 정리한 펀딩 ($272M 누적) 위에서, 개인 무료 플랜은 회사의 비용 부담 측에서는 충분히 감당 가능하면서, 동시에 다음 세대 엔지니어들이 사내 도입을 끌고 들어오는 채널 역할을 합니다.

---

## 다른 메시 VPN이 아니라 Tailscale인 이유

이 시리즈가 Tailscale을 고른 이유를 짧게 정리합니다. 메시 VPN/Zero Trust 영역에 다른 선택지도 적지 않습니다.

| 도구 | 조정 서버 | 데이터 평면 | 무료 한도 | 본 시리즈 시나리오에서 |
|---|---|---|---|---|
| **Tailscale** | SaaS (Tailscale 운영) | WireGuard | 6 user / 디바이스 무제한 | 본 시리즈가 채택 |
| Headscale | self-hosted (오픈소스) | WireGuard | 무제한 (자기 서버) | 조정 서버를 직접 운영해야 함 |
| ZeroTier | SaaS | 자체 프로토콜 | 25 노드 | 노드 한도가 빨리 차고, WireGuard가 아님 |
| Nebula | self-hosted | 자체 (Slack 출신) | 무제한 (자기 PKI) | PKI를 직접 운영해야 함 |
| Twingate | SaaS (B2B 중심) | 자체 | 5 user, 사용자 디바이스 제한 | 무료 한도가 빠르게 부족 |
| raw WireGuard | 없음 | WireGuard | 무제한 | 키 배포·NAT traversal 전부 직접. 가정 NAT 두 겹은 거의 불가능 |
| OpenVPN | 자기 서버 | OpenSSL | 자기 운영 | hub-and-spoke, NAT 뒤 가정 노트북에 부적합 |

본 시나리오의 두 결정 요건은 **(a) 무료로 동작할 것**과 **(b) 양쪽 NAT을 자동으로 뚫을 것**입니다. (a)는 Headscale·Nebula의 self-hosted 부담을 배제하고, (b)는 raw WireGuard·OpenVPN의 hub-and-spoke를 배제합니다. 남는 후보는 Tailscale과 ZeroTier 정도이며, ZeroTier는 무료 한도(25 노드)와 WireGuard 프로토콜 미사용이 약점입니다.

---

## 정리

| 질문 | 답 |
|---|---|
| 동기 | 후쿠오카 1년+ 거주 중 한국 결제·은행·콘텐츠가 해외 IP에서 막히는 패턴이 누적 |
| 해결 방식 | 부산 본가 창고 노트북을 무인 exit node로, 후쿠오카 Mac에서 SSH로 원격 운영 |
| 가동 결과 (실측) | P2P direct 50ms / Tunnel DOWN 24.9 Mbps / 무인 15시간+ 안정 / 자가치유 트리거 0건 |
| Tailscale 회사 | 2019년 토론토, Google 출신 4인 (Brad Fitzpatrick 포함), 누적 펀딩 $272M |
| 메시 VPN 핵심 | WireGuard(데이터 평면) + Tailscale 조정 서버(제어 평면) 분리 |
| WireGuard 강점 | Linux 5.6 메인라인, Noise IK + ChaCha20-Poly1305, 코드 단순성 ("a work of art" — Linus) |
| 회사가 트래픽을 못 보는 근거 | 데이터 평면이 노드 간 E2E이고 비밀 키가 노드 밖으로 안 나감, DERP도 암호문 그대로 전달 |
| 무료 가능한 이유 | 회사 인프라 측 한계 비용 ≈ 0 + PLG 영업 모델 + 명시된 미션 |
| Personal 플랜 | 6 user / 디바이스 무제한 / Exit Node·MagicDNS·ACL 포함 |

이 1편이 시리즈의 동기와 결과, 그리고 그게 가능한 구조적 근거였다면, 2편은 그 인프라를 실제로 만드는 단계로 넘어갑니다.

---

## 참고 자료

- [`Epheria/tailnet-ops`](https://github.com/Epheria/tailnet-ops) — 본 시리즈의 운영 코드 일체
- Donenfeld, J. A. *WireGuard: Next Generation Kernel Network Tunnel.* NDSS 2017. ([wireguard.com/papers/wireguard.pdf](https://www.wireguard.com/papers/wireguard.pdf))
- Pennarun, A. *How NAT traversal works.* Tailscale Blog. ([tailscale.com/blog/how-nat-traversal-works](https://tailscale.com/blog/how-nat-traversal-works))
- Tailscale. *How Tailscale works.* Tailscale Blog. ([tailscale.com/blog/how-tailscale-works](https://tailscale.com/blog/how-tailscale-works))
- Tailscale. *Pricing — Personal plan.* ([tailscale.com/pricing](https://tailscale.com/pricing))
- *Tailscale.* Wikipedia. ([en.wikipedia.org/wiki/Tailscale](https://en.wikipedia.org/wiki/Tailscale))
- *WireGuard.* Wikipedia. ([en.wikipedia.org/wiki/WireGuard](https://en.wikipedia.org/wiki/WireGuard))
- Salter, J. *WireGuard VPN review: A new type of VPN offers serious advantages.* Ars Technica, 2018-08. (Linus Torvalds 인용 출처)

---

## 다음 편

2편은 부산 본가 노트북을 실제로 무인 exit node로 만드는 셋업 + 무인 운영 자가치유 + 보안 감사를 한 번에 다룹니다. **본가 1회 방문에서 끝낼 일들의 전체 흐름**과, 후쿠오카에서 본가에 한 번도 안 가도 새 디바이스를 추가할 수 있는 원격 운영 모델을 정리합니다.

> 2편 — 본가 셋업 + 무인 운영 + 보안 (작성 예정)
{: .prompt-info }
