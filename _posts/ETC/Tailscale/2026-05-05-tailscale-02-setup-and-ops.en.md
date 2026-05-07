---
title: "Tailscale Series Part 2 — Family Home Setup, Unattended Operation, and Security (What to Finish in One Visit)"
lang: en
date: 2026-05-05 18:00:00 +0900
categories: [ETC, Tailscale]
tags: [tailscale, exit-node, windows, openssh, powershell, schtasks, security, infrastructure]
toc: true
toc_sticky: true
difficulty: intermediate
prerequisites:
  - /posts/tailscale-01-foundations/
tldr:
  - One trip to the family home = run install.ps1 once + 5-axis setup (Tailscale, power, sshd, Windows Update, healthcheck)
  - Unattended operation from Fukuoka = 5-minute healthcheck + 4 daily 23:59 self-healing tasks (RestartTailscale, RestartSshd, AddSshKey, DiagnosticDump)
  - Registering a new SSH key takes one SSH line — adding devices does not require a family home visit
  - Security audit = 13 checks in security-audit.ps1, with 0 failed SSH auth attempts over 24 hours
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

## What This Part Covers

This part wraps up **the entire operational flow that turns a Busan family-home laptop into an unattended 24/7 exit node**, all in one go. The work splits into three phases.

| Phase | Where | What |
|---|---|---|
| **1. Setup** | Busan family home (one trip) | Run install.ps1 once — unified 5-axis setup |
| **2. Operation** | Fukuoka (remote) | 5-minute healthcheck + 4 daily 23:59 self-healing tasks + add devices via one SSH line |
| **3. Security** | Fukuoka (remote) | Run the 13 checks in security-audit.ps1 regularly |

The target machine is a **Samsung Galaxy Book 950SBE (i7-8565U / 16GB / Windows 11 Home)**. Zero new hardware, and the goal is for the system to keep running even if the family at home never touches the laptop.

The full code lives in the [`Epheria/tailnet-ops`](https://github.com/Epheria/tailnet-ops) repository, and this part walks through that operational logic with a focus on structure and the reasoning behind each decision.

> ### Hold on — let's pause here for a sec
>
> **"Why a laptop instead of a desktop?"**
>
> A desktop is more powerful, but for unattended 24/7 exit-node duty, **the laptop is the rational choice**.
>
> - **Power**: i7-8565U (15W TDP) clamshell idle is ~7W, single-digit watts versus 100W+ for a desktop
> - **Built-in UPS**: The battery absorbs short power outages (a few minutes) automatically — no separate UPS needed
> - **Small and silent**: Can be tucked into a corner of the family home with the lid closed
> - **Plenty of headroom**: WireGuard tunnel cap is ~100–200 Mbps and the home line is even slower → CPU is not the bottleneck

---

## Phase 1 — The Five Axes of Setup

Below are the five axes that `install.ps1` handles in one shot. They are not independent — **leave any one out and unattended operation breaks**.

<div class="setup-axes" style="margin:1.5rem 0">
  <div class="sa-grid">
    <div class="sa-card sa-1">
      <div class="sa-num">1</div>
      <div class="sa-title">Tailscale</div>
      <div class="sa-key">Install · Sign in · Advertise Exit Node</div>
      <div class="sa-detail">tailnet membership + advertise "use this node as your internet egress"</div>
    </div>
    <div class="sa-card sa-2">
      <div class="sa-num">2</div>
      <div class="sa-title">Power · Clamshell</div>
      <div class="sa-key">Lid=0 · Sleep=0 · Modern Standby OFF</div>
      <div class="sa-detail">No sleep when lid closed / no sleep on long idle</div>
    </div>
    <div class="sa-card sa-3">
      <div class="sa-num">3</div>
      <div class="sa-title">sshd · Key Auth</div>
      <div class="sa-key">OpenSSH Server · Firewall · DefaultShell=PowerShell</div>
      <div class="sa-detail">Allow only 100.64.0.0/10 + block password auth</div>
    </div>
    <div class="sa-card sa-4">
      <div class="sa-num">4</div>
      <div class="sa-title">Windows Update</div>
      <div class="sa-key">Block forced reboots</div>
      <div class="sa-detail">No forced reboot when a user is logged in</div>
    </div>
    <div class="sa-card sa-5">
      <div class="sa-num">5</div>
      <div class="sa-title">Healthcheck</div>
      <div class="sa-key">SchTasks · 5-min cycle · SYSTEM privilege</div>
      <div class="sa-detail">Restart tailscaled / sshd immediately if they die</div>
    </div>
  </div>
  <p class="sa-cap">Only with all five axes in place do the "stable for 15+ unattended hours / 0 self-healing triggers" metrics show up. <strong>Among them, axis 5 (healthcheck) is the decisive one</strong> — axes 1 through 4 are "setup axes" that get the system installed correctly, while axis 5 is the "operations axis" that recovers when something installed correctly later breaks. That's the one tied directly to Part 1's <em>SchTasks Ready 5/5</em> metric.</p>
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

### Axis 1 — Install Tailscale + Advertise Exit Node

```powershell
winget install --id tailscale.tailscale --silent `
    --accept-package-agreements --accept-source-agreements

& 'C:\Program Files\Tailscale\tailscale.exe' up `
    --advertise-exit-node `
    --ssh `
    --hostname=samsung-home-laptop
```

What each of the three options means:

| Option | Meaning | If omitted |
|---|---|---|
| `--advertise-exit-node` | Advertise to the tailnet "this node can be used as an internet egress for others" | Will not be considered as an exit-node candidate |
| `--ssh` | Enable Tailscale's own SSH (SSH authenticated by Tailscale) | Only OpenSSH remains. One backup channel is gone |
| `--hostname=` | The hostname visible inside the tailnet | Defaults to the Windows computer name (`DESKTOP-...`), which makes identification hard |

Finally, **explicitly approve the exit-node advertisement in the Tailscale admin console** + **check Disable key expiry** (to prevent the automatic 90-day logout). Skip this and the advertisement goes out but other nodes cannot use it, and the node will drop out of the tailnet automatically after 90 days.

> ### Hold on — let's pause here for a sec
>
> **"The standard practice is to register an unattended server as a 'tagged resource', not as a user device"**
>
> Tailscale categorizes nodes into two types ([official docs](https://tailscale.com/kb/1068/acl-tags)):
>
> - **User device** — A laptop or phone owned by a single user. The **default 90-day key expiry** is in effect, requiring periodic re-authentication. If the user account is deleted, the device is removed too.
> - **Tagged resource** — An unattended server. **Key expiry is disabled by default** so it stays around indefinitely. A service-based identity decoupled from any user account.
>
> Tailscale's wording — "When you apply a tag to a device for the first time and authenticate it, the tagged device's key expiry is disabled by default."
>
> This series registers the Busan laptop as a user device and then manually checks **Disable key expiry** in the admin console (chosen for setup simplicity). The more standard approach is to register it as a **tagged resource** from the start.
>
> ```powershell
> # How to register as a tagged resource (for reference)
> & 'C:\Program Files\Tailscale\tailscale.exe' login --advertise-tags=tag:exit-node
> ```
>
> This requires defining tagOwners in the ACL JSON, so for the single-operator setup in this series I went with the simpler path. But for a long-term unattended + multi-operator scenario, the tag approach is the right answer.

### Axis 2 — Power and Clamshell

The system needs to keep running even when the family at home closes the lid. We knock every sleep trigger down to zero.

```powershell
powercfg /change standby-timeout-ac 0       # Sleep timeout = never
powercfg /change disk-timeout-ac 0          # Disk power-saving = never
powercfg /hibernate off                     # Disable hibernate

# Lid closed -> do nothing (both AC and DC)
powercfg /setacvalueindex SCHEME_CURRENT SUB_BUTTONS LIDACTION 0
powercfg /setdcvalueindex SCHEME_CURRENT SUB_BUTTONS LIDACTION 0
powercfg /setactive SCHEME_CURRENT

# Disable Modern Standby (S0) — a Windows 11 laptop trap
reg add "HKLM\System\CurrentControlSet\Control\Power" `
    /v PlatformAoAcOverride /t REG_DWORD /d 0 /f
```

Two lines are decisive.

- **`LIDACTION 0` (lid closed = keep running)** — The default value of 1 (sleep) means the moment a family member closes the lid the laptop sleeps → Wi-Fi drops → SSH from Fukuoka can no longer reach it. Both AC and DC must be set to 0 to prevent sleep even during brief outages.
- **`PlatformAoAcOverride 0` (disable Modern Standby)** — Modern Standby on Win 11 laptops can bypass LidAction and trigger a partial sleep, so this registry value falls back to traditional S3 sleep behavior.

> ### Hold on — let's pause here for a sec
>
> **"Is sleep really that dangerous? Can't you just wake it up?"**
>
> In unattended remote operation, sleep equals **death**. A laptop that has gone into sleep does not maintain its Wi-Fi connection, and to wake it via SSH from Fukuoka you need to reach it first — but **being unreachable is the very definition of sleep**. The moment it sleeps once, you have to ask the family at home to "give the laptop a tap," so it must be treated as a system failure.

### Axis 3 — sshd, Key Auth, Firewall

Even with Tailscale's own SSH available, **OpenSSH is also kept up** — if the Tailscale daemon dies for some reason, OpenSSH provides a recovery path, and standard tools like `scp` and `rsync` work only on top of OpenSSH.

```powershell
# Install OpenSSH Server + autostart
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
Start-Service sshd
Set-Service -Name sshd -StartupType Automatic

# Set default shell to PowerShell
New-ItemProperty -Path "HKLM:\SOFTWARE\OpenSSH" -Name DefaultShell `
    -Value "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" `
    -PropertyType String -Force

# Firewall — allow only the Tailscale range
Get-NetFirewallRule -Name "OpenSSH-Server-In-TCP" |
    Set-NetFirewallRule -Enabled False
New-NetFirewallRule -Name "sshd-tailscale" `
    -DisplayName "OpenSSH SSH (Tailscale only)" `
    -Enabled True -Direction Inbound -Protocol TCP -LocalPort 22 `
    -RemoteAddress 100.64.0.0/10 -Action Allow
```

The crucial bit is **`RemoteAddress 100.64.0.0/10`** — a single line that allows SSH only from the Tailscale CGNAT range. Knocking on the laptop's public IP port 22 from the open internet gets no response at all, which means **bruteforce attempts drop to zero** (see the security audit results later).

`sshd_config` also blocks password auth and only allows key auth.

```
PasswordAuthentication no
ChallengeResponseAuthentication no
KbdInteractiveAuthentication no
PermitEmptyPasswords no
MaxAuthTries 3
LoginGraceTime 30s
```

> ### Hold on — let's pause here for a sec
>
> **"If the ACL on `administrators_authorized_keys` is wrong, sshd silently rejects authentication"**
>
> Windows OpenSSH reads SSH keys for members of the administrators group not from the user's home `~/.ssh/authorized_keys` but from **`C:\ProgramData\ssh\administrators_authorized_keys`**. And if the ACL on that file is too loose — for instance if regular users (`Users`) or the `Authenticated Users` group have read permission — sshd ignores the key and rejects authentication **without any error message**.
>
> The recommended ACL keeps only these two entries:
>
> ```powershell
> icacls $KeyFile /inheritance:r                  # Disable inheritance
> icacls $KeyFile /grant 'Administrators:F'       # Administrators only, Full
> icacls $KeyFile /grant 'SYSTEM:F'               # SYSTEM only, Full
> icacls $KeyFile /remove '*S-1-5-32-545'         # Remove Users group
> icacls $KeyFile /remove '*S-1-5-11'             # Remove Authenticated Users
> ```
>
> The reason `tailnet-ops/windows/install/add-ssh-key.ps1` re-applies this ACL explicitly every time a key is added — sshd rejects without any debug log on its end, so **proactively enforcing it every single time is the operationally safe move**.

> ### Hold on — let's pause here for a sec
>
> **"Watch out when creating an ssh-keygen passphrase from PowerShell"**
>
> When generating a key on another Windows machine, do not write `ssh-keygen -N '""'` from PowerShell to give an empty passphrase — PowerShell's single-quoted `'""'` ends up baking **a literal two-character `""` passphrase** into the key.
>
> The result: the SSH client fails to unlock the key and gets blocked with `Permission denied (publickey)`, and `-vvv` shows `read_passphrase: can't open /dev/tty`. **Debug output even prints `Server accepts key`, which makes it easy to misdiagnose as a server-side ACL problem.**
>
> The correct usage is `-N ''` (single-quoted empty string). Recover a botched key with `ssh-keygen -p -P '""' -N '' -f keyfile`.

### Axis 4 — Block Windows Update Forced Reboots

Windows Update's default behavior of force-rebooting in the early morning hours can clash with the sleep policy and healthcheck, leading to scenarios where sshd does not come back up after boot.

```powershell
# Set Active Hours to 0-23 — effectively always active
Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings" `
    -Name ActiveHoursStart -Value 0 -Type DWord
Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings" `
    -Name ActiveHoursEnd -Value 23 -Type DWord

# Block forced reboots when a user is logged in
$auPath = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU"
New-Item -Path $auPath -Force
Set-ItemProperty -Path $auPath -Name NoAutoRebootWithLoggedOnUsers -Value 1 -Type DWord
```

The crux is **`NoAutoRebootWithLoggedOnUsers = 1`** — since the family-home laptop always has the user (`Sehyup`) logged in, this single line disables every kind of forced reboot. Patches still install but reboots only happen when a human triggers them, and that human is us (running `shutdown /r /t 5` remotely).

### Axis 5 — Healthcheck (5-Minute Cycle)

A task that automatically revives the Tailscale daemon and sshd when they die. **5-minute cycle / SYSTEM privilege / independent of user login**.

```powershell
# C:\Users\Sehyup\tailscale-setup\healthcheck.ps1 (excerpt)
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

Decision values for scheduler registration:

| Item | Value | Why |
|---|---|---|
| `UserId` | SYSTEM | Runs regardless of user login. Essential for unattended clamshell operation |
| `RunLevel` | Highest | Need privilege to restart services |
| Triggers | AtStartup + 5-minute interval | Run once right after boot + then every 5 minutes |
| `AllowStartIfOnBatteries` | True | Keep healthcheck running even on battery during a brief outage |
| `DontStopIfGoingOnBatteries` | True | Same reason |

**SYSTEM privilege** is especially decisive — registering under a user account leads to cases where, on a clamshell-closed laptop (locked state), tasks queue up but never actually execute.

---

## Phase 2 — Unattended Operation from Fukuoka

On top of the 5-minute healthcheck we layer **four self-healing tasks that run daily at 23:59**. Together, these enable "operations where you can add new devices without ever going to the family home."

### The Four Self-Healing Tasks

<div class="self-heal" style="margin:1.5rem 0">
  <div class="sh-grid">
    <div class="sh-card sh-1">
      <div class="sh-name">RestartTailscale</div>
      <div class="sh-when">Daily 23:59</div>
      <div class="sh-what">Force-restart the Tailscale daemon + log status</div>
      <div class="sh-why">Daily cleanup of cumulative issues like memory leaks or session tangles that the 5-minute healthcheck cannot catch</div>
    </div>
    <div class="sh-card sh-2">
      <div class="sh-name">RestartSshd</div>
      <div class="sh-when">Daily 23:59</div>
      <div class="sh-what">Force-restart sshd</div>
      <div class="sh-why">Guarantee newly registered keys take effect + clear accumulated sessions</div>
    </div>
    <div class="sh-card sh-3">
      <div class="sh-name">AddSshKey</div>
      <div class="sh-when">Daily 23:59 (or manual trigger)</div>
      <div class="sh-what">If pending-key.txt exists, append it to administrators_authorized_keys + reset permissions + restart sshd</div>
      <div class="sh-why">Add new devices — register keys to the family-home laptop with one SSH line from Fukuoka</div>
    </div>
    <div class="sh-card sh-4">
      <div class="sh-name">DiagnosticDump</div>
      <div class="sh-when">Daily 23:59</div>
      <div class="sh-what">Dump system, network, services, schedules, and logs into dump.txt</div>
      <div class="sh-why">When something goes wrong, pull diagnostics in one SSH call from Fukuoka</div>
    </div>
  </div>
  <p class="sh-cap">All four run with SYSTEM privilege / WakeToRun / battery mode allowed / RestartCount 3.</p>
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

These 4 + the 5-minute healthcheck = 5 SchTasks total. The "**SchTasks Ready 5/5**" on the metrics card in Part 1 refers to these five.

### Operational Pattern 1 — Registering a New SSH Key (the Most Common Flow)

When you want to add a new device — a Fukuoka desktop, a new phone — to the tailnet, you need to register that device's public SSH key into the Busan laptop's `administrators_authorized_keys`. We handle this without going to the family home, with a single SSH line from Fukuoka.

```bash
# From the Fukuoka Mac
ssh samsung-home-laptop "Set-Content C:\Users\Sehyup\tailscale-setup\pending-key.txt '<one line of public key>'; schtasks /Run /TN AddSshKey"
sleep 5
ssh samsung-home-laptop "Get-Content C:\Users\Sehyup\tailscale-setup\add-ssh-key.log -Tail 5"
```

Why this one-liner works:

1. A normal SSH session does not have permission to write `C:\ProgramData\ssh\administrators_authorized_keys` directly (admin ACL)
2. So we just write to `pending-key.txt` with normal privileges
3. **Trigger the `AddSshKey` task with SYSTEM privilege** → SYSTEM reads that file and appends it to `administrators_authorized_keys`
4. Reset permissions (`icacls /inheritance:r` + Administrators/SYSTEM only with Full Control)
5. Restart sshd
6. Delete `pending-key.txt`

Here is what the `AddSshKey` task actually does, in code (excerpt from `tailnet-ops/windows/install/add-ssh-key.ps1`):

```powershell
# Validate key format
if ($line -notmatch '^(ssh-ed25519|ssh-rsa|ecdsa-sha2-)') {
    L "invalid key format: ..."
    Remove-Item $Pending -Force; exit 1
}

# Duplicate check
$keyOnly = ($line -split '\s+')[1]
foreach ($existing in (Get-Content $KeyFile)) {
    if (($existing -split '\s+')[1] -eq $keyOnly) { $dup = $true; break }
}

if (-not $dup) {
    Add-Content -Path $KeyFile -Value $line -Encoding ASCII
    icacls $KeyFile /inheritance:r
    icacls $KeyFile /grant 'Administrators:F'
    icacls $KeyFile /grant 'SYSTEM:F'
    icacls $KeyFile /remove '*S-1-5-32-545'  # Remove Users group
    Restart-Service sshd
}
Remove-Item $Pending -Force
```

Three safety nets — **(a) sanity check the key format, (b) prevent duplicate entries, (c) reset the ACL every time**. The last one — re-applying the ACL — is the critical piece, because a too-loose ACL on Windows OpenSSH's `administrators_authorized_keys` causes **sshd to silently reject authentication**, an area that is hard to debug.

> ### Hold on — let's pause here for a sec
>
> **"Why bother routing through SYSTEM privilege? Isn't there something like sudo?"**
>
> Windows does not have a standard mechanism like Linux's `sudo` for elevating a single command line (some support arrived in 2024 but Windows 11 Home is not supported).
>
> Two alternatives existed:
>
> 1. Open the SSH session as an **administrator PowerShell** — security risk. Running daily SSH sessions as administrator widens the blast surface
> 2. **Privilege separation** — the normal-privilege SSH session only writes a file; privilege elevation is handled by a SYSTEM SchTask
>
> This series picked option 2. As a result, **SSH sessions stay at everyday privilege**, and **privilege elevation only happens inside a vetted script (`add-ssh-key.ps1`)**. This is also operationally cleaner.

### Operational Pattern 2 — Diagnostic Dump

When you want a comprehensive snapshot of the laptop's state from afar:

```bash
ssh samsung-home-laptop "schtasks /Run /TN DiagnosticDump"
sleep 3
ssh samsung-home-laptop "Get-Content C:\Users\Sehyup\tailscale-setup\dump.txt -Encoding UTF8"
```

`DiagnosticDump` bundles the following nine sections into a single file (`tailnet-ops/windows/install/setup-helpers.ps1`).

| Section | Contents |
|---|---|
| Hostname / Boot | Hostname, last boot time, current time |
| Tailscale status | Output of `tailscale status` |
| Tailscale netcheck | RTT to all 28 DERP regions |
| Services | Tailscale and sshd service states |
| Network adapters Up | Active network adapters + LinkSpeed |
| IP Forwarding | Forwarding settings required for exit-node operation |
| Power state | Active power policy + sleep requests + last wake |
| Scheduled tasks | State of all 5 SchTasks |
| Health log (last 30) | Last 30 lines of the healthcheck log |
| OpenSSH events (last 20) | Recent SSH events |

This single snapshot makes it possible to figure out what happened to the laptop, instantly, from Fukuoka.

### Operational Pattern 3 — Incident Recovery Scenarios

Four representative scenarios and their recovery paths:

| Scenario | Recovery path | Family-home visit needed? |
|---|---|---|
| Tailscale alive but only SSH dead | Auto-recovered by daily 23:59 `RestartSshd` / immediately fall back to Tailscale SSH | No |
| SSH key lost (Mac wiped) | Register a new key from the Fukuoka desktop's key / if both are blocked, family-home visit | (conditional) |
| Laptop won't power on after outage | Depends on BIOS AC Power Recovery setting — **no way to verify other than visiting the family home** | Yes |
| Wi-Fi password changed | No automatic recovery — share the new password with family and ask them to reconnect | (family cooperation) |

Redundancy is the key — **keeping both the Mac key and the Fukuoka desktop key registered** means that if one device dies, all operations are still possible from the other.

---

## Phase 3 — Security Audit (13 Checks)

`security-audit.ps1` checks 13 areas — SSH, accounts, firewall, RDP, Defender, Tailscale ACL, and more. Here is what each area means.

| # | Check area | What it verifies |
|---|---|---|
| 1 | sshd config | PasswordAuth=no, MaxAuthTries=3, LoginGraceTime=30s, KbdInteractive=no |
| 2 | authorized_keys | SHA256 fingerprints of registered keys + ACL |
| 3 | Listening TCP ports | Whether any unintended ports are open beyond 22 |
| 4 | Firewall (Inbound Allow) | Only sshd-tailscale / default SSH rule is Disabled |
| 5 | Local user accounts | Administrator group members + password policy |
| 6 | RDP status | `fDenyTSConnections=1` (RDP disabled) |
| 7 | SMB / file sharing | Any exposed shared folders |
| 8 | Windows Defender | Real-time protection + Tamper Protection + age of definitions |
| 9 | **Failed SSH (24h)** | Number of failed auth attempts in the last 24 hours (target: 0) |
| 10 | Tailscale ACL | This node's tags + exit-node advertisement + WhoIs |
| 11 | UAC settings | EnableLUA, ConsentPromptBehavior |
| 12 | Recent successful SSH (24h) | List of source IPs for successful logins (investigate immediately if any unexpected IPs) |
| 13 | Suspicious outbound processes | Whether remote-control tools like TeamViewer/AnyDesk/VNC are running |

Key results (measured in 2026-05):

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
      <div class="ar-val">0</div>
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
      <div class="ar-val">none</div>
    </div>
    <div class="ar-card ar-pass">
      <div class="ar-icon">✓</div>
      <div class="ar-name">Password bruteforce</div>
      <div class="ar-val">rejected</div>
    </div>
  </div>
  <p class="ar-cap">All 13 checks pass. The 0 failed SSH authentications is the result of a single-line Tailscale-only firewall.</p>
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

**0 failed SSH authentications over 24 hours** is the most meaningful result. A typical internet-exposed SSH endpoint receives thousands to tens of thousands of bruteforce attempts daily, but here **a single-line Tailscale-only firewall blocks those attempts at the router level**, so they never even reach the sshd log.

For reference, here are typical bruteforce statistics for internet-exposed SSH (general industry reports):

| Environment | Daily bruteforce attempts |
|---|---|
| Exposed port 22 on a typical home line | ~1,000 to 10,000 |
| Exposed port 22 on a cloud VM (AWS/GCP/Azure) | ~10,000 to 50,000 |
| This series (Tailscale-only firewall) | **0** (never even reach the sshd log) |

Because the router firewall denies the packets, the Busan laptop's sshd has no idea those attempts even exist. Key auth + MaxAuthTries 3 + LoginGraceTime 30s only matter as the **second and third lines of defense in case that perimeter is breached**.

> ### Hold on — let's pause here for a sec
>
> **"How do you actually verify that port 22 on the public IP is closed?"**
>
> From inside the family home you are on the same LAN, so the test is meaningless. You have to knock on the Busan laptop's public IP port 22 **from a different network (e.g. a cafe's 4G or mobile network)**.
>
> ```bash
> nc -zv <Busan public IP> 22  # timeout or connection refused = expected
> ssh samsung-home-laptop      # immediate connect via Tailscale 100.64.x.x = expected
> ```
>
> Both results need to show up at the same time for the setup to be working as intended — unreachable from the internet, reachable from inside the tailnet.

### Tailscale ACL — Another Layer of Defense

If the firewall filters by IP range at the router level, **the Tailscale ACL controls who inside the tailnet can reach which port on which node**. ACL policy is defined in the policy file (JSON) on the admin console.

> Tailscale's wording — "ACLs are deny-by-default, directional, and locally enforced." ([official docs](https://tailscale.com/kb/1018/acls))

**deny-by-default** is significant — without an ACL the default policy is "every node in the tailnet can reach every port on every other node," but once you write an ACL, **anything not explicitly allowed is denied**. SSH is the same — you must allow it via an **explicit ssh policy** for it to reach.

A recommended ACL pattern for the single-operator setup in this series:

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

What this ACL enforces:

- **Only devices owned by `group:admin` users** can reach tailnet nodes (any other invitee is automatically blocked)
- **Tag-based node classification** — exit-node and client are separated and can carry different policies
- **SSH is allowed only when `group:admin`** connects to `tag:exit-node` as `sehyup` or a non-root user — root SSH is automatically blocked

Writing this ACL JSON once strengthens checks 4 (firewall), 9 (failed SSH), and 12 (successful SSH) of the 13 security checks all at the same time.

### Tailscale's Own Security Incident History

The honest answer to "Can Tailscale itself be trusted?" — **flaws have been found in it before, and the company has responded with public security advisories**. Notable items from the public [Security Bulletins](https://tailscale.com/security-bulletins):

| ID | Impact | Response |
|---|---|---|
| **CVE-2022-41924** (Critical) | Remote code execution via local API reconstruction in the Windows client | Patch + auto-update advisory |
| **TS-2024-005** | Insufficient inbound LAN device filtering on Linux nodes acting as subnet routers | Upgrade to 1.66.0+ |
| **TS-2025-005** | MDM auth keys uploaded to log servers | Fixed in 1.86.4+, key rotation recommended |
| **TS-2026-001** | Privilege escalation and arbitrary command execution via macOS `tssentineld` | Upgrade to 1.94.0+ |

Among these, **CVE-2022-41924** was the heaviest incident, but the company moved promptly with a public advisory and patch and recommended auto-updating — a reasonable response pattern. **Operational recommendations for this series' infrastructure**:

- Enable Tailscale auto-updates (`tailscale set --auto-update`)
- Periodically check security advisories at [tailscale.com/security-bulletins](https://tailscale.com/security-bulletins)
- Use the ACL policy above to minimize blast radius in case of an incident

**What matters isn't "no flaws" but "flaws that close quickly."** CVE-2022-41924 went through the cycle of discovery → public security advisory → auto-update recommendation → patch rollout, and the company executed it normally; TS-2025-005's key-rotation advisory followed the same pattern. As long as that cycle stays unbroken — and as long as this series keeps auto-updates enabled, monitors security advisories regularly, and maintains ACL deny-by-default — Tailscale can sit inside the trust model.

---

## Verification — One Run of `status.ps1`

With the five axes applied and the self-healing tasks registered, running `status.ps1` once shows the entire system state on a single screen. We capture this output right before leaving the family home and use it as a baseline for comparison from Fukuoka.

```bash
ssh samsung-home-laptop 'powershell -NoProfile -ExecutionPolicy Bypass `
    -File C:\Users\Sehyup\tailscale-setup\status.ps1'
```

Expected output (conceptual form):

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

If all eight sections are healthy, you can leave the family home.

---

## Pre-Departure Checklist

| # | Item | Verification |
|---|---|---|
| 1 | Computer name set to `samsung-home-laptop` | `hostname` |
| 2 | Tailscale node registered in admin console + Exit Node approved + Disable key expiry | Browser |
| 3 | sshd service Running + Automatic | `Get-Service sshd` |
| 4 | Firewall: `sshd-tailscale` Enabled / default rule Disabled | `Get-NetFirewallRule "sshd-*"` |
| 5 | **From a different network**, SSH connects successfully (4G, etc.) | `ssh samsung-home-laptop` |
| 6 | Capture `status.ps1` baseline with the lid closed | the command above |
| 7 | `NoAutoRebootWithLoggedOnUsers=1` applied | Check the registry |
| 8 | **Redundancy**: SSH also works from the Fukuoka desktop | `ssh samsung-home-laptop` (different machine) |
| 9 | Mac SSH key backed up (1Password / iCloud Keychain) | Check the backup tool |
| 10 | (Optional) Cap battery charging at 80% in Samsung Settings | Microsoft Store app |

Item 5 is the most important — only by connecting from a different network and confirming that the Busan IP is reported as the Tailscale exit node do you have real verification.

Item 10 prevents laptop battery aging — keeping a laptop fully charged at 100% under always-on AC power degrades battery cell lifespan quickly. Enabling Samsung Settings' "Battery Life Extender" mode caps charging at 80%.

---

## Wrap-Up

What this part accomplished, in one table:

| Phase | Key decisions | One-line reason |
|---|---|---|
| Setup | `--advertise-exit-node`, `LIDACTION=0`, `100.64.0.0/10` only, `NoAutoRebootWithLoggedOnUsers=1`, `RunAs=SYSTEM` | Five axes set up once enables unattended 24/7 |
| Operation | 5-minute healthcheck + 4 daily 23:59 self-healing tasks | Add devices, run diagnostics, recover — all without visiting the family home |
| Security | Tailscale-only firewall + key auth + 13 regular checks | 0 failed SSH auths in 24h. Bruteforce blocked at the router level |

That is everything that needs to fit into one trip to the family home. With this state in place, you can close the lid and head back to Fukuoka, and unattended operation just keeps running — and adding new devices is a single SSH line away.

The next part wraps the series with two topics — **how the system actually works** (DERP, MagicDNS, hole punching) — and **a cost retrospective at ~$7 per year** (electricity, internet, laptop wear, time cost).

---

## References

- [`Epheria/tailnet-ops`](https://github.com/Epheria/tailnet-ops) — all the operational code for this series
  - [`windows/install/install.ps1`](https://github.com/Epheria/tailnet-ops/blob/main/windows/install/install.ps1) — unified setup script
  - [`windows/install/setup-helpers.ps1`](https://github.com/Epheria/tailnet-ops/blob/main/windows/install/setup-helpers.ps1) — registers the 4 self-healing tasks
  - [`windows/install/add-ssh-key.ps1`](https://github.com/Epheria/tailnet-ops/blob/main/windows/install/add-ssh-key.ps1) — privilege-separated key registration logic
  - [`windows/ops/status.ps1`](https://github.com/Epheria/tailnet-ops/blob/main/windows/ops/status.ps1) — comprehensive state verification
  - [`windows/ops/security-audit.ps1`](https://github.com/Epheria/tailnet-ops/blob/main/windows/ops/security-audit.ps1) — the 13 security checks
  - [`docs/decisions.md`](https://github.com/Epheria/tailnet-ops/blob/main/docs/decisions.md) — the "why" behind each decision
  - [`docs/runbook-busan-laptop.md`](https://github.com/Epheria/tailnet-ops/blob/main/docs/runbook-busan-laptop.md) — standard daily operating procedures
  - [`docs/recovery.md`](https://github.com/Epheria/tailnet-ops/blob/main/docs/recovery.md) — recovery flows by incident scenario
- Tailscale Docs. *Exit nodes.* ([tailscale.com/kb/1103/exit-nodes](https://tailscale.com/kb/1103/exit-nodes))
- Tailscale Docs. *Tailscale SSH.* ([tailscale.com/kb/1193/tailscale-ssh](https://tailscale.com/kb/1193/tailscale-ssh))
- Tailscale Docs. *Tailnet policy file (ACL).* ([tailscale.com/kb/1018/acls](https://tailscale.com/kb/1018/acls))
- Tailscale Docs. *Tags — Identity for unattended devices.* ([tailscale.com/kb/1068/acl-tags](https://tailscale.com/kb/1068/acl-tags))
- Tailscale. *Security Bulletins.* ([tailscale.com/security-bulletins](https://tailscale.com/security-bulletins))
- Microsoft Docs. *OpenSSH for Windows overview.* ([learn.microsoft.com/windows-server/administration/openssh](https://learn.microsoft.com/windows-server/administration/openssh/openssh-overview))

---

## Next Up

Part 3 is the final part of the series and bundles two topics — **how this system actually works** (DERP relay, MagicDNS, NAT hole punching) — and **a cost and limits retrospective for an infrastructure that runs at ~$7 a year**.

> Part 3 — How It Works + Cost & Limits Retrospective (coming soon)
{: .prompt-info }
