---
title: "Tailscale 시리즈 2편 — 본가 셋업·무인 운영·보안 (1회 방문에서 끝낼 일들)"
date: 2026-05-05 18:00:00 +0900
categories: [ETC, Tailscale]
tags: [tailscale, exit-node, windows, openssh, powershell, schtasks, security, infrastructure]
toc: true
toc_sticky: true
difficulty: intermediate
prerequisites:
  - /posts/tailscale-01-foundations/
tldr:
  - 본가 1회 방문 = install.ps1 한 번 + 5축 셋업 (Tailscale·전원·sshd·Windows Update·헬스체크)
  - 후쿠오카에서 무인 운영 = 5분 헬스체크 + 매일 23:59 자가치유 4종 (RestartTailscale·RestartSshd·AddSshKey·DiagnosticDump)
  - 새 SSH 키 등록은 SSH 한 줄 — 본가 안 가도 디바이스 추가 가능
  - 보안 감사 = security-audit.ps1의 13개 점검 항목, 24시간 SSH 인증 실패 0건 결과
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

## 이 편이 다루는 것

이 편은 **부산 본가 노트북을 무인 24/7 exit node로 만드는 운영 전체**를 한 번에 정리합니다. 작업은 세 단계로 나뉩니다.

| Phase | 어디서 | 무엇을 |
|---|---|---|
| **1. 셋업** | 부산 본가 (1회 방문) | install.ps1 한 번 실행 — 5축 통합 셋업 |
| **2. 운영** | 후쿠오카 (원격) | 5분 헬스체크 + 매일 23:59 자가치유 4종 + SSH 한 줄로 디바이스 추가 |
| **3. 보안** | 후쿠오카 (원격) | security-audit.ps1의 13개 점검을 정기적으로 |

대상 머신은 **Samsung Galaxy Book 950SBE (i7-8565U / 16GB / Windows 11 Home)**. 새 하드웨어 0대, 본가 가족이 노트북에 손을 안 대도 동작하는 상태가 목표입니다.

전체 코드는 [`Epheria/tailnet-ops`](https://github.com/Epheria/tailnet-ops) 리포지토리에 있고, 이 편은 그 운영 로직을 구조와 결정 사유 중심으로 풉니다.

> ### 잠깐, 이건 짚고 넘어가자
>
> **"왜 데스크톱이 아니라 노트북이야?"**
>
> 데스크톱이 더 강력하지만, 무인 24/7 exit node 용도로는 **노트북 쪽이 합리적**입니다.
>
> - **전력**: i7-8565U(15W TDP) 클램쉘 idle은 ~7W, 데스크톱 100W+ 대비 한 자릿수
> - **UPS 내장**: 배터리가 있어 짧은 정전(수 분) 동안 자동 흡수 — 별도 UPS 불필요
> - **소형·무소음**: 본가 한 구석에 두고 닫아둘 수 있음
> - **충분한 성능**: WireGuard 터널 cap이 ~100~200 Mbps이고 가정 회선이 그보다 낮음 → CPU가 병목 안 됨

---

## Phase 1 — 셋업의 다섯 축

`install.ps1`이 한 번에 처리하는 작업을 다섯 축으로 정리합니다. 각 축이 따로 동작하는 게 아니라 **한 축이라도 빠지면 무인 운영이 깨지는** 의존 관계입니다.

<div class="setup-axes" style="margin:1.5rem 0">
  <div class="sa-grid">
    <div class="sa-card sa-1">
      <div class="sa-num">1</div>
      <div class="sa-title">Tailscale</div>
      <div class="sa-key">설치 · Sign in · Exit Node 광고</div>
      <div class="sa-detail">tailnet 멤버 자격 + "이 노드를 인터넷 출구로" 라우트 광고</div>
    </div>
    <div class="sa-card sa-2">
      <div class="sa-num">2</div>
      <div class="sa-title">전원·클램쉘</div>
      <div class="sa-key">Lid=0 · Sleep=0 · Modern Standby OFF</div>
      <div class="sa-detail">덮개 닫혀도 / idle 길어도 슬립 안 들어감</div>
    </div>
    <div class="sa-card sa-3">
      <div class="sa-num">3</div>
      <div class="sa-title">sshd · 키 인증</div>
      <div class="sa-key">OpenSSH Server · 방화벽 · DefaultShell=PowerShell</div>
      <div class="sa-detail">100.64.0.0/10 만 허용 + 패스워드 차단</div>
    </div>
    <div class="sa-card sa-4">
      <div class="sa-num">4</div>
      <div class="sa-title">Windows Update</div>
      <div class="sa-key">자동 재부팅 차단</div>
      <div class="sa-detail">로그인 사용자 있을 때 강제 재부팅 금지</div>
    </div>
    <div class="sa-card sa-5">
      <div class="sa-num">5</div>
      <div class="sa-title">헬스체크</div>
      <div class="sa-key">SchTasks · 5분 주기 · SYSTEM 권한</div>
      <div class="sa-detail">tailscaled / sshd 죽으면 즉시 재시작</div>
    </div>
  </div>
  <p class="sa-cap">이 다섯 축이 모두 적용된 상태에서야 "무인 15시간+ 안정 / 자가치유 트리거 0건" 메트릭이 나옵니다. <strong>그중 5번 헬스체크가 결정적</strong> — 1~4번이 "처음에 잘 깔아두는" 셋업 축이라면, 5번은 "깔아둔 것이 깨졌을 때 복구하는" 운영 축이라 1편의 <em>SchTasks Ready 5/5</em> 메트릭으로 직결됩니다.</p>
</div>
<style>
.setup-axes .sa-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:.6rem}
.setup-axes .sa-card{border-radius:12px;padding:.85rem .7rem;color:#fff;box-shadow:0 2px 8px rgba(0,0,0,.08);display:flex;flex-direction:column;text-align:center}
.setup-axes .sa-1{background:linear-gradient(135deg,#1976d2,#1565c0)}
.setup-axes .sa-2{background:linear-gradient(135deg,#388e3c,#2e7d32)}
.setup-axes .sa-3{background:linear-gradient(135deg,#7b1fa2,#6a1b9a)}
.setup-axes .sa-4{background:linear-gradient(135deg,#ef6c00,#e65100)}
.setup-axes .sa-5{background:linear-gradient(135deg,#c62828,#b71c1c)}
.setup-axes .sa-num{font-size:11.5px;font-weight:700;background:rgba(255,255,255,.22);width:22px;height:22px;line-height:22px;border-radius:50%;margin:0 auto}
.setup-axes .sa-title{font-size:13.5px;font-weight:800;margin:.45rem 0 .2rem;letter-spacing:.02em}
.setup-axes .sa-key{font-family:'SF Mono',Consolas,monospace;font-size:10.5px;background:rgba(255,255,255,.15);padding:3px 6px;border-radius:5px;margin:.2rem 0;line-height:1.35}
.setup-axes .sa-detail{font-size:11px;opacity:.92;line-height:1.5;margin-top:.35rem}
.setup-axes .sa-cap{text-align:center;margin-top:.7rem;font-size:12px;color:var(--text-muted-color,#888);font-style:italic}
@media(max-width:768px){.setup-axes .sa-grid{grid-template-columns:1fr 1fr}}
</style>

### 축 1 — Tailscale 설치 + Exit Node 광고

```powershell
winget install --id tailscale.tailscale --silent `
    --accept-package-agreements --accept-source-agreements

& 'C:\Program Files\Tailscale\tailscale.exe' up `
    --advertise-exit-node `
    --ssh `
    --hostname=samsung-home-laptop
```

옵션 세 개의 의미:

| 옵션 | 의미 | 안 붙이면 |
|---|---|---|
| `--advertise-exit-node` | "다른 노드의 인터넷 출구로 쓸 수 있다"고 tailnet에 광고 | exit node 후보로 안 잡힘 |
| `--ssh` | Tailscale 자체 SSH 활성 (Tailscale 인증으로 SSH) | OpenSSH만 남음. 백업 채널 1줄 줄어듦 |
| `--hostname=` | tailnet 안에서 보이는 호스트명 | Windows 컴퓨터 이름 그대로(`DESKTOP-...`)라 식별 어려움 |

마지막으로 **Tailscale 관리 콘솔에서 exit node 광고를 명시적으로 승인** + **Disable key expiry** 체크(90일 자동 로그아웃 방지). 이걸 안 하면 광고만 나가고 다른 노드가 못 쓰며, 90일 뒤에 노드가 자동으로 tailnet에서 빠집니다.

> ### 잠깐, 이건 짚고 넘어가자
>
> **"무인 서버는 사용자 디바이스(user device)가 아니라 'tagged resource'로 분류해야 표준이다"**
>
> Tailscale은 노드를 두 가지로 분류합니다 ([공식 문서](https://tailscale.com/kb/1068/acl-tags)):
>
> - **User device** — 한 사용자가 소유하는 노트북·폰. **기본 90일 key expiry**가 걸려 정기적으로 재인증 필요. 사용자 계정이 삭제되면 그 디바이스도 함께 제거됨.
> - **Tagged resource** — 무인 서버. **key expiry가 기본 비활성화**되어 영구 유지. 사용자 계정과 분리된 service-based identity.
>
> Tailscale 공식 표현 — "When you apply a tag to a device for the first time and authenticate it, the tagged device's key expiry is disabled by default."
>
> 본 시리즈는 부산 노트북을 user device로 등록한 뒤 admin 콘솔에서 **Disable key expiry**를 수동으로 체크하는 방식을 택했습니다(셋업 단순성). 더 표준적인 운영은 처음부터 **tagged resource**로 등록하는 것입니다.
>
> ```powershell
> # tagged resource로 등록하는 방법 (참고)
> & 'C:\Program Files\Tailscale\tailscale.exe' login --advertise-tags=tag:exit-node
> ```
>
> tagOwners를 ACL JSON에 정의해야 하므로 본 시리즈의 1인 운영에서는 단순 방식을 쓰지만, 장기 무인 + 다중 운영자 시나리오라면 tag 방식이 정답입니다.

### 축 2 — 전원·클램쉘

본가 가족이 노트북 덮개를 닫아도 동작이 유지되어야 합니다. 모든 슬립 트리거를 0으로 깎습니다.

```powershell
powercfg /change standby-timeout-ac 0       # 슬립 타임아웃 = 안 함
powercfg /change disk-timeout-ac 0          # 디스크 절전 = 안 함
powercfg /hibernate off                     # 하이버네이트 비활성화

# 덮개 닫음 → 아무것도 안 함 (AC, DC 양쪽)
powercfg /setacvalueindex SCHEME_CURRENT SUB_BUTTONS LIDACTION 0
powercfg /setdcvalueindex SCHEME_CURRENT SUB_BUTTONS LIDACTION 0
powercfg /setactive SCHEME_CURRENT

# Modern Standby (S0) 비활성화 — Windows 11 노트북의 함정
reg add "HKLM\System\CurrentControlSet\Control\Power" `
    /v PlatformAoAcOverride /t REG_DWORD /d 0 /f
```

두 줄이 결정적입니다.

- **`LIDACTION 0` (덮개 닫음 = 동작 유지)** — 기본값 1(슬립)이면 가족이 노트북 덮개를 닫는 순간 슬립 → Wi-Fi 끊김 → 후쿠오카에서 SSH 안 닿음. AC와 DC 양쪽을 모두 0으로 설정해야 짧은 정전 시에도 슬립을 막습니다.
- **`PlatformAoAcOverride 0` (Modern Standby 비활성화)** — Win 11 노트북의 모던 스탠바이가 LidAction을 우회해 부분 슬립을 트리거할 수 있어, 이 레지스트리 값으로 전통적 S3 슬립으로 회귀시킵니다.

> ### 잠깐, 이건 짚고 넘어가자
>
> **"슬립이 그렇게 위험해? 깨우면 되는 거 아니야?"**
>
> 무인 원격 운영에서는 슬립이 곧 **사망**입니다. 슬립에 들어간 노트북은 Wi-Fi 연결을 유지하지 않고, 후쿠오카에서 SSH로 깨우려면 일단 닿아야 하는데 **닿을 수 없는 것 자체가 슬립의 정의**입니다. 슬립이 한 번 들어간 순간 본가 가족에게 "노트북 한 번 만져줘"라고 부탁해야 하므로, 시스템 실패로 봐야 합니다.

### 축 3 — sshd · 키 인증 · 방화벽

Tailscale 자체 SSH가 있어도 **OpenSSH도 같이 띄워둡니다** — Tailscale 데몬이 어떤 이유로 죽었을 때 OpenSSH로 복구할 수 있고, `scp`·`rsync` 같은 표준 도구가 OpenSSH 위에서만 동작하기 때문입니다.

```powershell
# OpenSSH Server 설치 + 자동 시작
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
Start-Service sshd
Set-Service -Name sshd -StartupType Automatic

# 기본 셸을 PowerShell로
New-ItemProperty -Path "HKLM:\SOFTWARE\OpenSSH" -Name DefaultShell `
    -Value "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" `
    -PropertyType String -Force

# 방화벽 — Tailscale 대역만 허용
Get-NetFirewallRule -Name "OpenSSH-Server-In-TCP" |
    Set-NetFirewallRule -Enabled False
New-NetFirewallRule -Name "sshd-tailscale" `
    -DisplayName "OpenSSH SSH (Tailscale only)" `
    -Enabled True -Direction Inbound -Protocol TCP -LocalPort 22 `
    -RemoteAddress 100.64.0.0/10 -Action Allow
```

핵심은 **`RemoteAddress 100.64.0.0/10`** — Tailscale CGNAT 대역에서 들어오는 SSH만 허용하는 한 줄입니다. 인터넷에서 노트북 공인 IP의 22번 포트를 두드려도 절대 응답하지 않으므로, **bruteforce 시도가 0건이 됩니다**(뒤 보안 감사 결과 참고).

`sshd_config`도 패스워드 인증을 차단하고 키 인증만 허용합니다.

```
PasswordAuthentication no
ChallengeResponseAuthentication no
KbdInteractiveAuthentication no
PermitEmptyPasswords no
MaxAuthTries 3
LoginGraceTime 30s
```

> ### 잠깐, 이건 짚고 넘어가자
>
> **"`administrators_authorized_keys`의 ACL이 잘못되면 sshd가 묵묵히 인증을 거부한다"**
>
> Windows OpenSSH는 관리자 그룹 멤버의 SSH 키를 사용자 홈의 `~/.ssh/authorized_keys`가 아니라 **`C:\ProgramData\ssh\administrators_authorized_keys`**에서 읽습니다. 그런데 이 파일의 ACL이 너무 느슨하면 — 예를 들어 일반 사용자(`Users`)나 `Authenticated Users` 그룹이 읽기 권한을 가지면 — sshd가 **에러 메시지 없이** 키를 무시하고 인증을 거부합니다.
>
> 권장 ACL은 다음과 같이 두 항목만 남깁니다:
>
> ```powershell
> icacls $KeyFile /inheritance:r                  # 상속 비활성화
> icacls $KeyFile /grant 'Administrators:F'       # Administrators만 Full
> icacls $KeyFile /grant 'SYSTEM:F'               # SYSTEM만 Full
> icacls $KeyFile /remove '*S-1-5-32-545'         # Users 그룹 제거
> icacls $KeyFile /remove '*S-1-5-11'             # Authenticated Users 제거
> ```
>
> `tailnet-ops/windows/install/add-ssh-key.ps1`이 매번 키를 추가할 때마다 이 ACL을 명시적으로 재설정하는 이유 — sshd 측에서 디버그 로그 없이 거부되므로 **선제적으로 매번 강제하는 게 운영 안전**합니다.

> ### 잠깐, 이건 짚고 넘어가자
>
> **"PowerShell에서 ssh-keygen 패스프레이즈 만들 때 주의점"**
>
> 다른 Windows 머신에서 키를 만들 때, PowerShell에서 빈 패스프레이즈를 주려고 `ssh-keygen -N '""'` 라고 쓰면 안 됩니다 — PowerShell의 single-quoted `'""'`는 **리터럴 두 글자 `""` 패스프레이즈**가 키에 박혀버립니다.
>
> 결과적으로 SSH 클라이언트가 키 unlock에 실패해 `Permission denied (publickey)`로 막히고, `-vvv`에 `read_passphrase: can't open /dev/tty`가 보입니다. **디버그에 `Server accepts key`까지 찍혀서 서버 ACL 문제로 오진하기 쉽습니다**.
>
> 올바른 사용은 `-N ''` (single-quoted 빈 문자열). 잘못 만든 키는 `ssh-keygen -p -P '""' -N '' -f keyfile`로 복구.

### 축 4 — Windows Update 자동 재부팅 차단

Windows Update가 새벽에 강제 재부팅하는 게 기본 동작인데, 그게 슬립 정책·헬스체크와 충돌해 부팅 후 sshd가 안 살아나는 시나리오가 생길 수 있습니다.

```powershell
# 활성 시간(Active Hours)을 0~23시로 — 사실상 항상 활성
Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings" `
    -Name ActiveHoursStart -Value 0 -Type DWord
Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings" `
    -Name ActiveHoursEnd -Value 23 -Type DWord

# 로그인 사용자 있을 때 자동 재부팅 금지
$auPath = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU"
New-Item -Path $auPath -Force
Set-ItemProperty -Path $auPath -Name NoAutoRebootWithLoggedOnUsers -Value 1 -Type DWord
```

핵심은 **`NoAutoRebootWithLoggedOnUsers = 1`** — 본가 노트북에 사용자(`Sehyup`) 계정이 항상 로그인된 상태이므로 이 한 줄로 강제 재부팅이 모조리 무력화됩니다. 패치는 받지만 재부팅은 사람이 트리거해야만 일어나고, 그 사람이 우리(원격에서 `shutdown /r /t 5`)입니다.

### 축 5 — 헬스체크 (5분 주기)

Tailscale 데몬과 sshd가 죽었을 때 자동으로 살리는 작업. **5분 주기 / SYSTEM 권한 / 사용자 로그인 무관**.

```powershell
# C:\Users\Sehyup\tailscale-setup\healthcheck.ps1 (요약)
$ts = Get-Service Tailscale
if ($ts -and $ts.Status -ne 'Running') {
    Start-Service Tailscale
    HealthLog "[Tailscale] restarted (was $($ts.Status))"
}

$sshd = Get-Service sshd
if ($sshd -and $sshd.Status -ne 'Running') {
    Start-Service sshd
    HealthLog "[sshd] restarted (was $($sshd.Status))"
}

$st = & 'C:\Program Files\Tailscale\tailscale.exe' status --json |
        ConvertFrom-Json
if ($st.BackendState -ne 'Running') {
    HealthLog "[Tailscale] BackendState=$($st.BackendState)"
}
```

스케줄러 등록 시 결정값 표:

| 항목 | 값 | 왜 |
|---|---|---|
| `UserId` | SYSTEM | 사용자 로그인 여부와 무관하게 실행. 클램쉘 무인의 필수 |
| `RunLevel` | Highest | 서비스 재시작 권한 필요 |
| 트리거 | AtStartup + 5분 주기 | 부팅 후 즉시 1회 + 이후 5분 cadence |
| `AllowStartIfOnBatteries` | True | 짧은 정전 시 배터리 모드여도 헬스체크 계속 |
| `DontStopIfGoingOnBatteries` | True | 동일 사유 |

특히 **SYSTEM 권한**이 결정적입니다 — 사용자 권한으로 등록하면 클램쉘 닫힌 노트북(잠금 상태)에서 작업이 큐에만 쌓이고 실행 안 되는 케이스가 있습니다.

---

## Phase 2 — 후쿠오카에서 무인 운영

5분 헬스체크 위에 **매일 23:59에 도는 자가치유 4종**을 더 얹습니다. 이게 있어서 "본가에 한 번도 안 가도 새 디바이스를 추가할 수 있는 운영"이 성립합니다.

### 자가치유 4종 작업 표

<div class="self-heal" style="margin:1.5rem 0">
  <div class="sh-grid">
    <div class="sh-card sh-1">
      <div class="sh-name">RestartTailscale</div>
      <div class="sh-when">매일 23:59</div>
      <div class="sh-what">Tailscale 데몬 강제 재시작 + status 로그</div>
      <div class="sh-why">메모리 누수·세션 꼬임 등 5분 헬스체크가 못 잡는 누적 이슈를 매일 한 번 클린업</div>
    </div>
    <div class="sh-card sh-2">
      <div class="sh-name">RestartSshd</div>
      <div class="sh-when">매일 23:59</div>
      <div class="sh-what">sshd 강제 재시작</div>
      <div class="sh-why">새 키 등록 후 반영 보장 + 누적 세션 정리</div>
    </div>
    <div class="sh-card sh-3">
      <div class="sh-name">AddSshKey</div>
      <div class="sh-when">매일 23:59 (또는 수동 트리거)</div>
      <div class="sh-what">pending-key.txt 있으면 administrators_authorized_keys에 추가 + 권한 재설정 + sshd 재시작</div>
      <div class="sh-why">새 디바이스 추가 — 후쿠오카에서 SSH 한 줄로 본가 노트북에 키 등록</div>
    </div>
    <div class="sh-card sh-4">
      <div class="sh-name">DiagnosticDump</div>
      <div class="sh-when">매일 23:59</div>
      <div class="sh-what">시스템·네트워크·서비스·스케줄·로그 전체를 dump.txt에 덤프</div>
      <div class="sh-why">사고 시 후쿠오카에서 SSH 한 번으로 진단 받음</div>
    </div>
  </div>
  <p class="sh-cap">4개 모두 SYSTEM 권한 / WakeToRun / 배터리 모드 허용 / RestartCount 3.</p>
</div>
<style>
.self-heal .sh-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:.7rem}
.self-heal .sh-card{border-radius:12px;padding:.95rem .9rem;color:#fff;box-shadow:0 2px 8px rgba(0,0,0,.08)}
.self-heal .sh-1{background:linear-gradient(135deg,#1976d2,#1565c0)}
.self-heal .sh-2{background:linear-gradient(135deg,#7b1fa2,#6a1b9a)}
.self-heal .sh-3{background:linear-gradient(135deg,#388e3c,#2e7d32)}
.self-heal .sh-4{background:linear-gradient(135deg,#ef6c00,#e65100)}
.self-heal .sh-name{font-family:'SF Mono',Consolas,monospace;font-size:14px;font-weight:800;letter-spacing:.01em}
.self-heal .sh-when{font-size:11.5px;background:rgba(255,255,255,.18);padding:2px 8px;border-radius:10px;display:inline-block;margin:.3rem 0 .5rem;letter-spacing:.02em}
.self-heal .sh-what{font-size:12.5px;line-height:1.5;margin-bottom:.45rem;font-weight:600}
.self-heal .sh-why{font-size:11.5px;line-height:1.55;opacity:.92}
.self-heal .sh-cap{text-align:center;margin-top:.7rem;font-size:12px;color:var(--text-muted-color,#888);font-style:italic}
@media(max-width:768px){.self-heal .sh-grid{grid-template-columns:1fr}}
</style>

이 4개 + 5분 헬스체크 = SchTasks 5종. 1편 메트릭 카드의 "**SchTasks Ready 5/5**"가 이 5개를 가리킵니다.

### 운영 패턴 1 — 새 SSH 키 등록 (가장 자주 쓰는 흐름)

후쿠오카 데스크톱이든 새 폰이든 새 디바이스를 tailnet에 합류시킬 때, 그 디바이스의 SSH 공개 키를 부산 노트북의 `administrators_authorized_keys`에 등록해야 합니다. 본가에 안 가고 후쿠오카에서 SSH 한 줄로 처리합니다.

```bash
# 후쿠오카 Mac에서
ssh samsung-home-laptop "Set-Content C:\Users\Sehyup\tailscale-setup\pending-key.txt '<공개키 한 줄>'; schtasks /Run /TN AddSshKey"
sleep 5
ssh samsung-home-laptop "Get-Content C:\Users\Sehyup\tailscale-setup\add-ssh-key.log -Tail 5"
```

이 한 줄이 동작하는 이유:

1. 일반 SSH 세션의 권한으로는 `C:\ProgramData\ssh\administrators_authorized_keys`에 직접 못 씀 (관리자 ACL)
2. 그래서 `pending-key.txt`만 일반 권한으로 작성
3. **`AddSshKey` 작업을 SYSTEM 권한으로 트리거** → SYSTEM이 그 파일을 읽어 `administrators_authorized_keys`에 추가
4. 권한 재설정 (`icacls /inheritance:r` + Administrators/SYSTEM만 Full Control)
5. sshd 재시작
6. `pending-key.txt` 삭제

`AddSshKey` 작업이 하는 일을 코드로 보면 (`tailnet-ops/windows/install/add-ssh-key.ps1` 발췌):

```powershell
# 키 형식 검증
if ($line -notmatch '^(ssh-ed25519|ssh-rsa|ecdsa-sha2-)') {
    L "invalid key format: ..."
    Remove-Item $Pending -Force; exit 1
}

# 중복 체크
$keyOnly = ($line -split '\s+')[1]
foreach ($existing in (Get-Content $KeyFile)) {
    if (($existing -split '\s+')[1] -eq $keyOnly) { $dup = $true; break }
}

if (-not $dup) {
    Add-Content -Path $KeyFile -Value $line -Encoding ASCII
    icacls $KeyFile /inheritance:r
    icacls $KeyFile /grant 'Administrators:F'
    icacls $KeyFile /grant 'SYSTEM:F'
    icacls $KeyFile /remove '*S-1-5-32-545'  # Users 그룹 제거
    Restart-Service sshd
}
Remove-Item $Pending -Force
```

세 가지 안전장치 — **(a) 키 형식 sanity check, (b) 중복 등록 방지, (c) 매번 ACL 재설정**. 마지막 ACL 재설정이 핵심인데, Windows OpenSSH의 `administrators_authorized_keys`는 권한이 너무 느슨하면 **sshd가 묵묵히 인증을 거부**해서 디버깅이 어려운 영역입니다.

> ### 잠깐, 이건 짚고 넘어가자
>
> **"왜 굳이 SYSTEM 권한으로 우회하나? sudo 같은 게 없어?"**
>
> Windows에는 Linux의 `sudo`처럼 한 줄 명령어를 권한 상승해 실행하는 표준 메커니즘이 없습니다(2024년부터 일부 도입됐지만 11 Home 미지원).
>
> 대안은 두 가지였습니다:
>
> 1. SSH 세션을 **관리자 PowerShell로** 띄우기 — 보안 측면에서 위험. 일상 SSH 세션이 관리자 권한이면 사고 표면이 커짐
> 2. **권한 분리** — 일반 권한 SSH 세션은 파일만 작성하고, 권한 상승은 SYSTEM SchTasks가 담당
>
> 본 시리즈는 2를 택했습니다. 결과적으로 **SSH 세션은 일상 권한으로 유지**되고, **권한 상승은 검증된 스크립트(`add-ssh-key.ps1`) 안에서만** 일어납니다. 이게 운영적으로도 깔끔합니다.

### 운영 패턴 2 — 진단 덤프

원격에서 노트북 상태를 종합으로 받고 싶을 때:

```bash
ssh samsung-home-laptop "schtasks /Run /TN DiagnosticDump"
sleep 3
ssh samsung-home-laptop "Get-Content C:\Users\Sehyup\tailscale-setup\dump.txt -Encoding UTF8"
```

`DiagnosticDump`는 다음 9개 섹션을 한 파일에 묶습니다 (`tailnet-ops/windows/install/setup-helpers.ps1`).

| 섹션 | 내용 |
|---|---|
| Hostname / Boot | 호스트명, 마지막 부팅 시각, 현재 시각 |
| Tailscale status | `tailscale status` 출력 |
| Tailscale netcheck | DERP 28개 리전 RTT |
| Services | Tailscale, sshd 서비스 상태 |
| Network adapters Up | 활성 네트워크 어댑터 + LinkSpeed |
| IP Forwarding | exit node로 동작하기 위한 forwarding 설정 |
| Power state | 활성 전원 정책 + 슬립 요청 + 마지막 wake |
| Scheduled tasks | 5종 SchTasks 상태 |
| Health log (last 30) | 헬스체크 로그 마지막 30줄 |
| OpenSSH events (last 20) | 최근 SSH 이벤트 |

이 한 컷으로 노트북에 무슨 일이 있었는지 후쿠오카에서 즉시 파악 가능합니다.

### 운영 패턴 3 — 사고 시나리오 복구

대표적 4개 시나리오와 복구 경로:

| 시나리오 | 복구 경로 | 본가 직접 방문 필요? |
|---|---|---|
| Tailscale 살아있는데 SSH만 죽음 | 매일 23:59 `RestartSshd`로 자동 복구 / 즉시는 Tailscale SSH 활용 | × |
| SSH 키 분실 (Mac 포맷) | 후쿠오카 데스크톱 키로 새 키 등록 / 둘 다 막히면 본가 방문 | (조건부) |
| 정전 후 노트북 안 켜짐 | BIOS의 AC Power Recovery 설정에 의존 — **본가 방문 외 검증법 없음** | ○ |
| Wi-Fi 비밀번호 변경 | 자동 복구 불가, 가족에게 새 비번 안내해서 재연결 요청 | (가족 협조) |

다중화가 핵심입니다 — **Mac 키 + 후쿠오카 데스크톱 키 둘 다 등록 유지**해두면 한 디바이스가 죽어도 다른 디바이스에서 모든 운영이 가능합니다.

---

## Phase 3 — 보안 감사 (13개 점검)

`security-audit.ps1`은 SSH·계정·방화벽·RDP·Defender·Tailscale ACL 등 13개 영역을 체크합니다. 각 영역의 의미를 짚어둡니다.

| # | 점검 영역 | 무엇을 확인 |
|---|---|---|
| 1 | sshd 설정 | PasswordAuth=no, MaxAuthTries=3, LoginGraceTime=30s, KbdInteractive=no |
| 2 | authorized_keys | 등록 키 SHA256 fingerprint + ACL |
| 3 | Listening TCP ports | 22번 외에 의도하지 않은 포트가 열려있는지 |
| 4 | Firewall (Inbound Allow) | sshd-tailscale만 / 기본 SSH 룰은 Disabled |
| 5 | Local user accounts | 관리자 그룹 멤버 + 패스워드 정책 |
| 6 | RDP status | `fDenyTSConnections=1` (RDP 비활성) |
| 7 | SMB / file sharing | 노출된 공유 폴더 |
| 8 | Windows Defender | 실시간 보호 + Tamper Protection + 정의 파일 나이 |
| 9 | **Failed SSH (24h)** | 최근 24시간 인증 실패 횟수 (목표: 0건) |
| 10 | Tailscale ACL | 자기 노드 태그 + exit node 광고 + WhoIs |
| 11 | UAC settings | EnableLUA, ConsentPromptBehavior |
| 12 | Recent successful SSH (24h) | 정상 접속 IP 목록 (예상 외 IP가 있으면 즉시 조사) |
| 13 | Outbound 의심 프로세스 | TeamViewer/AnyDesk/VNC 같은 원격 제어 도구가 돌고 있지 않은지 |

핵심 결과 (2026-05 측정 기준):

<div class="audit-results" style="margin:1.5rem 0">
  <div class="ar-grid">
    <div class="ar-card ar-pass">
      <div class="ar-icon">✓</div>
      <div class="ar-name">sshd PasswordAuth</div>
      <div class="ar-val">no</div>
    </div>
    <div class="ar-card ar-pass">
      <div class="ar-icon">✓</div>
      <div class="ar-name">MaxAuthTries</div>
      <div class="ar-val">3</div>
    </div>
    <div class="ar-card ar-pass">
      <div class="ar-icon">✓</div>
      <div class="ar-name">Tailscale-only Firewall</div>
      <div class="ar-val">100.64.0.0/10</div>
    </div>
    <div class="ar-card ar-pass">
      <div class="ar-icon">✓</div>
      <div class="ar-name">Failed SSH (24h)</div>
      <div class="ar-val">0건</div>
    </div>
    <div class="ar-card ar-pass">
      <div class="ar-icon">✓</div>
      <div class="ar-name">Defender + Tamper</div>
      <div class="ar-val">ON</div>
    </div>
    <div class="ar-card ar-pass">
      <div class="ar-icon">✓</div>
      <div class="ar-name">RDP</div>
      <div class="ar-val">Disabled</div>
    </div>
    <div class="ar-card ar-pass">
      <div class="ar-icon">✓</div>
      <div class="ar-name">Remote-control SW</div>
      <div class="ar-val">없음</div>
    </div>
    <div class="ar-card ar-pass">
      <div class="ar-icon">✓</div>
      <div class="ar-name">Patchword bruteforce</div>
      <div class="ar-val">즉시 거부</div>
    </div>
  </div>
  <p class="ar-cap">13개 점검 항목 모두 통과. SSH 인증 실패 0건은 Tailscale-only firewall 한 줄의 결과입니다.</p>
</div>
<style>
.audit-results .ar-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:.6rem}
.audit-results .ar-card{background:linear-gradient(135deg,#e8f5e9,#c8e6c9);border-radius:10px;padding:.7rem .55rem;color:#1b5e20;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,.06)}
.audit-results .ar-icon{font-size:18px;font-weight:800;line-height:1;margin-bottom:.3rem}
.audit-results .ar-name{font-size:11.5px;font-weight:700;margin-bottom:.25rem}
.audit-results .ar-val{font-family:'SF Mono',Consolas,monospace;font-size:11.5px;background:rgba(56,142,60,.18);padding:2px 7px;border-radius:5px;display:inline-block}
.audit-results .ar-cap{text-align:center;margin-top:.7rem;font-size:12px;color:var(--text-muted-color,#888);font-style:italic}
[data-mode="dark"] .audit-results .ar-card{background:linear-gradient(135deg,#1a3320,#263e2a);color:#a5d6a7}
[data-mode="dark"] .audit-results .ar-val{background:rgba(165,214,167,.15)}
@media(max-width:768px){.audit-results .ar-grid{grid-template-columns:1fr 1fr}}
</style>

**24시간 SSH 인증 실패 0건**이 가장 의미 있는 결과입니다. 일반적인 인터넷 노출 SSH는 하루 수천~수만 건의 bruteforce 시도가 들어오는데, **Tailscale-only firewall 한 줄로 그 시도가 라우터 단에서 차단**되어 sshd 로그에 도달조차 못 합니다.

참고로 인터넷 노출 SSH의 일반적인 bruteforce 통계 (보안 업계 일반 보고치):

| 환경 | 일평균 bruteforce 시도 |
|---|---|
| 일반 가정 회선의 노출 22번 포트 | ~1,000 ~ 10,000건 |
| 클라우드 VM (AWS/GCP/Azure) 22번 포트 | ~10,000 ~ 50,000건 |
| 본 시리즈 (Tailscale-only firewall) | **0건** (sshd 로그 도달 자체 안 됨) |

라우터 firewall이 패킷을 거부하므로, 부산 노트북의 sshd는 그런 시도가 존재한다는 사실조차 모릅니다. 키 인증 + MaxAuthTries 3 + LoginGraceTime 30s는 **그것이 뚫렸을 때를 대비한 2차·3차 방어선**으로만 의미가 있습니다.

> ### 잠깐, 이건 짚고 넘어가자
>
> **"공인 IP의 22번 포트가 막혀있는지 어떻게 검증해?"**
>
> 본가 안에서는 같은 LAN이라 의미 있는 검증이 안 되니, **다른 네트워크(예: 카페 4G·이동통신)에서** 부산 노트북의 공인 IP 22번 포트를 두드려봐야 합니다.
>
> ```bash
> nc -zv <부산 공인 IP> 22  # 타임아웃 또는 connection refused 가 정상
> ssh samsung-home-laptop   # Tailscale 100.64.x.x 로 즉시 접속 (정상)
> ```
>
> 두 결과가 동시에 나와야 셋업이 의도대로 동작합니다 — 인터넷에서는 안 닿고, tailnet 안에서는 닿습니다.

### Tailscale ACL — 또 한 겹의 방어선

방화벽이 라우터 단에서 IP 대역을 거른다면, **Tailscale ACL은 tailnet 안에서 누가 어느 노드의 어느 포트에 닿을 수 있는지를 제어**합니다. ACL 정책은 admin 콘솔의 정책 파일(JSON)로 정의됩니다.

> Tailscale의 표현 — "ACLs are deny-by-default, directional, and locally enforced." ([공식 문서](https://tailscale.com/kb/1018/acls))

**deny-by-default**의 의미가 큽니다 — ACL을 정의하지 않으면 기본 정책은 "tailnet 안의 모든 노드가 서로의 모든 포트에 접근 가능"이지만, 한 번 ACL을 적었다면 그 안에서 **명시적으로 허용된 것 외의 모든 트래픽이 거부**됩니다. SSH도 마찬가지로 **명시적 ssh 정책**으로 허용해야 닿습니다.

본 시리즈의 1인 운영용 권장 ACL 패턴 예시:

```json
{
  "groups": {
    "group:admin": ["epheria@github"]
  },
  "tagOwners": {
    "tag:exit-node":   ["group:admin"],
    "tag:client":      ["group:admin"]
  },
  "acls": [
    {
      "action": "accept",
      "src":    ["group:admin"],
      "dst":    ["tag:exit-node:*", "tag:client:*"]
    }
  ],
  "ssh": [
    {
      "action": "accept",
      "src":    ["group:admin"],
      "dst":    ["tag:exit-node"],
      "users":  ["sehyup", "autogroup:nonroot"]
    }
  ]
}
```

이 ACL이 강제하는 것:

- **`group:admin` 사용자의 디바이스만** tailnet 노드들에 접근 가능 (다른 invitee가 추가되어도 자동 차단)
- **tag 기반 노드 분류** — exit-node와 client를 분리, 각각의 정책을 따로 줄 수 있음
- **SSH는 `group:admin`이 `tag:exit-node`의 `sehyup` 또는 비-root 사용자로만** 가능 — root SSH는 자동 차단

ACL JSON 한 번 적는 것이 결과적으로 13개 보안 점검의 4번(방화벽), 9번(SSH 실패), 12번(SSH 성공) 항목 모두를 강화합니다.

### Tailscale 자체의 보안 사건 이력

"Tailscale을 신뢰할 수 있는가"라는 질문에 솔직한 답은 — **그 자체로 결함이 발견된 적이 있고, 회사가 공개 보안 권고로 대응**해왔다는 것입니다. 공개된 [Security Bulletins](https://tailscale.com/security-bulletins) 중 주요 항목:

| ID | 영향 | 대응 |
|---|---|---|
| **CVE-2022-41924** (Critical) | Windows 클라이언트 로컬 API 재구성으로 원격 코드 실행 | 패치 + 자동 업데이트 권고 |
| **TS-2024-005** | 서브넷 라우터의 Linux 노드에서 LAN 기기 인바운드 필터링 부족 | 1.66.0+로 업그레이드 |
| **TS-2025-005** | MDM 인증 키가 로그 서버에 업로드 | 1.86.4+ 수정, 키 로테이션 권장 |
| **TS-2026-001** | macOS의 `tssentineld` 권한 상향 임의 명령 실행 | 1.94.0+ 업그레이드 |

이 중 **CVE-2022-41924**가 가장 무거운 사건이었지만, 발견 후 회사가 공개 권고와 패치를 빠르게 내놓고 자동 업데이트를 권장하는 대응 패턴이 정상적이었습니다. **본 시리즈 인프라의 운영 측 권장**:

- Tailscale 자동 업데이트 활성화 (`tailscale set --auto-update`)
- 보안 권고는 [tailscale.com/security-bulletins](https://tailscale.com/security-bulletins) 정기 확인
- 위 ACL 정책으로 사고 시 폭발 반경(blast radius) 최소화

**중요한 것은 "결함이 없는 것"이 아니라 "결함이 빠르게 닫히는 것"**입니다. CVE-2022-41924는 발견 → 공개 보안 권고 → 자동 업데이트 권장 → 패치 배포의 사이클을 회사가 정상적으로 돌렸고, TS-2025-005의 키 로테이션 권고도 같은 패턴이었습니다. 이 사이클이 깨지지 않는 한 — 그리고 본 시리즈가 자동 업데이트 활성화 + 보안 권고 정기 확인 + ACL deny-by-default를 유지하는 한 — Tailscale을 신뢰 모델 안에 둘 수 있습니다.

---

## 검증 — `status.ps1` 한 컷

다섯 축이 적용되고 자가치유까지 등록된 상태에서 `status.ps1`을 한 번 돌리면 시스템 전체 상태가 한 화면에 나옵니다. 본가 떠나기 직전에 이 출력을 캡처해서 후쿠오카에서 비교용 baseline으로 씁니다.

```bash
ssh samsung-home-laptop 'powershell -NoProfile -ExecutionPolicy Bypass `
    -File C:\Users\Sehyup\tailscale-setup\status.ps1'
```

기대 출력 (개념 형태):

```
=== System ===
ComputerName       : samsung-home-laptop
Uptime             : 0d 0h 5m
PowerSource        : AC

=== Tailscale ===
Service            : Running / Automatic
BackendState       : Running
ExitNodeAdvertised : True
TailscaleIP        : 100.64.88.55

=== SSHD ===
Service            : Running / Automatic
Listening          : 0.0.0.0:22
Firewall           : sshd-tailscale (RemoteAddress=100.64.0.0/10) Enabled
                     OpenSSH-Server-In-TCP Disabled

=== Power ===
LidAction (AC, DC) : DoNothing
StandbyTimeout AC  : 0 (Never)
ModernStandby      : Disabled

=== ScheduledTasks (5/5 Ready) ===
TailscaleHealthcheck : Ready / RunAs=SYSTEM
RestartTailscale     : Ready / RunAs=SYSTEM
RestartSshd          : Ready / RunAs=SYSTEM
AddSshKey            : Ready / RunAs=SYSTEM
DiagnosticDump       : Ready / RunAs=SYSTEM
```

이 8개 영역이 다 정상이면 본가를 떠나도 됩니다.

---

## 본가 떠나기 직전 체크리스트

| # | 항목 | 검증 방법 |
|---|---|---|
| 1 | 컴퓨터 이름이 `samsung-home-laptop`으로 적용 | `hostname` |
| 2 | Tailscale 노드 admin 콘솔 등록 + Exit Node 승인 + Disable key expiry | 브라우저 |
| 3 | sshd 서비스 Running + Automatic | `Get-Service sshd` |
| 4 | 방화벽: `sshd-tailscale` Enabled / 기본 룰 Disabled | `Get-NetFirewallRule "sshd-*"` |
| 5 | **다른 네트워크에서** SSH 접속 성공 (4G 등) | `ssh samsung-home-laptop` |
| 6 | 클램쉘 상태에서 `status.ps1` baseline 캡처 | 위 명령 |
| 7 | `NoAutoRebootWithLoggedOnUsers=1` 적용 | 레지스트리 확인 |
| 8 | **다중화**: 후쿠오카 데스크톱에서도 SSH 가능 | `ssh samsung-home-laptop` (다른 머신) |
| 9 | Mac SSH 키 백업 (1Password / iCloud Keychain) | 백업 도구 확인 |
| 10 | (선택) Samsung Settings에서 배터리 80% 충전 제한 | Microsoft Store 앱 |

체크리스트의 5번이 가장 중요합니다 — 다른 네트워크에서 들어가서 Tailscale exit node로 부산 IP가 나오는지 확인해야 진짜 검증입니다.

10번은 노트북 배터리 노화 방지 — 24/7 AC 연결 환경에서 100% 풀충 유지는 배터리 셀 수명을 빠르게 깎습니다. Samsung Settings의 "배터리 수명 연장 모드"를 켜두면 80%에서 충전을 멈춥니다.

---

## 정리

이 편이 한 일을 한 표로:

| Phase | 핵심 결정값 | 한 줄 이유 |
|---|---|---|
| 셋업 | `--advertise-exit-node`, `LIDACTION=0`, `100.64.0.0/10` only, `NoAutoRebootWithLoggedOnUsers=1`, `RunAs=SYSTEM` | 다섯 축 한 번 셋업으로 무인 24/7 가능 |
| 운영 | 5분 헬스체크 + 매일 23:59 자가치유 4종 | 본가에 안 가도 디바이스 추가·진단·복구 가능 |
| 보안 | Tailscale-only firewall + 키 인증 + 13개 정기 점검 | SSH 인증 실패 24h 0건. bruteforce가 라우터 단에서 차단 |

본가 1회 방문에서 끝낼 일은 여기까지입니다. 이 상태에서 노트북 덮개를 닫고 후쿠오카로 돌아가도 무인 운영이 그대로 굴러가고, 새 디바이스 추가도 SSH 한 줄로 처리됩니다.

다음 편에서는 이 시스템이 동작하는 **작동 원리**(DERP·MagicDNS·hole punching)와 **연 1만 원 비용 회고**(전기료·인터넷·노트북 노화·시간 비용)로 시리즈를 마무리합니다.

---

## 참고 자료

- [`Epheria/tailnet-ops`](https://github.com/Epheria/tailnet-ops) — 본 시리즈의 운영 코드 일체
  - [`windows/install/install.ps1`](https://github.com/Epheria/tailnet-ops/blob/main/windows/install/install.ps1) — 통합 셋업 스크립트
  - [`windows/install/setup-helpers.ps1`](https://github.com/Epheria/tailnet-ops/blob/main/windows/install/setup-helpers.ps1) — 자가치유 4종 등록
  - [`windows/install/add-ssh-key.ps1`](https://github.com/Epheria/tailnet-ops/blob/main/windows/install/add-ssh-key.ps1) — 권한 분리 키 등록 로직
  - [`windows/ops/status.ps1`](https://github.com/Epheria/tailnet-ops/blob/main/windows/ops/status.ps1) — 상태 종합 검증
  - [`windows/ops/security-audit.ps1`](https://github.com/Epheria/tailnet-ops/blob/main/windows/ops/security-audit.ps1) — 13개 보안 점검
  - [`docs/decisions.md`](https://github.com/Epheria/tailnet-ops/blob/main/docs/decisions.md) — 각 결정값의 "왜"
  - [`docs/runbook-busan-laptop.md`](https://github.com/Epheria/tailnet-ops/blob/main/docs/runbook-busan-laptop.md) — 일상 운영 표준 절차
  - [`docs/recovery.md`](https://github.com/Epheria/tailnet-ops/blob/main/docs/recovery.md) — 사고 시나리오별 복구
- Tailscale Docs. *Exit nodes.* ([tailscale.com/kb/1103/exit-nodes](https://tailscale.com/kb/1103/exit-nodes))
- Tailscale Docs. *Tailscale SSH.* ([tailscale.com/kb/1193/tailscale-ssh](https://tailscale.com/kb/1193/tailscale-ssh))
- Tailscale Docs. *Tailnet policy file (ACL).* ([tailscale.com/kb/1018/acls](https://tailscale.com/kb/1018/acls))
- Tailscale Docs. *Tags — Identity for unattended devices.* ([tailscale.com/kb/1068/acl-tags](https://tailscale.com/kb/1068/acl-tags))
- Tailscale. *Security Bulletins.* ([tailscale.com/security-bulletins](https://tailscale.com/security-bulletins))
- Microsoft Docs. *OpenSSH for Windows overview.* ([learn.microsoft.com/windows-server/administration/openssh](https://learn.microsoft.com/windows-server/administration/openssh/openssh-overview))

---

## 다음 편

3편은 시리즈 마지막 편으로 두 가지를 묶습니다 — **이 시스템이 동작하는 작동 원리**(DERP relay, MagicDNS, NAT hole punching)와 **연 1만 원 인프라의 비용·한계 회고**입니다.

> 3편 — 작동 원리 + 비용·한계 (작성 예정)
{: .prompt-info }
