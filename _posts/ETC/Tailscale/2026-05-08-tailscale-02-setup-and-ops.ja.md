---
title: "Tailscaleシリーズ第2回 — 実家セットアップ・無人運用・セキュリティ（一度の訪問で済ませること）"
lang: ja
date: 2026-05-08 18:00:00 +0900
categories: [ETC, Tailscale]
tags: [tailscale, exit-node, windows, openssh, powershell, schtasks, security, infrastructure]
toc: true
toc_sticky: true
difficulty: intermediate
prerequisites:
  - /posts/tailscale-01-foundations/
tldr:
  - 実家1回訪問 = install.ps1の一回実行 + 五つの軸セットアップ（Tailscale・電源・sshd・Windows Update・ヘルスチェック）
  - 福岡からの無人運用 = 5分ヘルスチェック + 毎日23:59の自己修復4種（RestartTailscale・RestartSshd・AddSshKey・DiagnosticDump）
  - 新しいSSH鍵の登録はSSHコマンド一行 — 実家に行かずにデバイス追加が可能
  - セキュリティ監査 = security-audit.ps1の13項目チェック、24時間SSH認証失敗0件という結果
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

## この回が扱うもの

この回は、**釜山の実家ノートPCを無人24/7のexit nodeに仕立てる運用全体**を一気に整理します。作業は三つの段階に分かれます。

| Phase | どこで | 何を |
|---|---|---|
| **1. セットアップ** | 釜山の実家（1回訪問） | install.ps1を一度実行 — 五つの軸を統合セットアップ |
| **2. 運用** | 福岡（リモート） | 5分ヘルスチェック + 毎日23:59の自己修復4種 + SSH一行でデバイス追加 |
| **3. セキュリティ** | 福岡（リモート） | security-audit.ps1の13項目チェックを定期的に実施 |

対象マシンは **Samsung Galaxy Book 950SBE (i7-8565U / 16GB / Windows 11 Home)**。新規ハードウェア0台、実家の家族がノートPCに触らなくても動作し続ける状態を目標とします。

全コードは [`Epheria/tailnet-ops`](https://github.com/Epheria/tailnet-ops) リポジトリにあり、この回ではその運用ロジックを構造と決定理由を中心に解きほぐします。

> ### ちょっと待って、これだけ確認しておこう
>
> **「なぜデスクトップではなくノートPCなのか？」**
>
> デスクトップの方が強力ですが、無人24/7のexit node用途では **ノートPCの方が合理的** です。
>
> - **電力**: i7-8565U（15W TDP）クラムシェルアイドルは約7W、デスクトップ100W+に比べて一桁少ない
> - **UPS内蔵**: バッテリーがあるため短い停電（数分）を自動で吸収 — 別途UPS不要
> - **小型・無音**: 実家の片隅に置いて閉じておける
> - **十分な性能**: WireGuardトンネルのcapが約100〜200 Mbpsで家庭回線がそれより低い → CPUがボトルネックにならない

---

## Phase 1 — セットアップの五つの軸

`install.ps1`が一気に処理する作業を五つの軸に整理します。各軸が独立して動作するのではなく、**どれか一つでも欠けると無人運用が崩れる**依存関係になっています。

<div class="setup-axes" style="margin:1.5rem 0">
  <div class="sa-grid">
    <div class="sa-card sa-1">
      <div class="sa-num">1</div>
      <div class="sa-title">Tailscale</div>
      <div class="sa-key">インストール · Sign in · Exit Node 広告</div>
      <div class="sa-detail">tailnetメンバー資格 + 「このノードをインターネット出口に」のルート広告</div>
    </div>
    <div class="sa-card sa-2">
      <div class="sa-num">2</div>
      <div class="sa-title">電源・クラムシェル</div>
      <div class="sa-key">Lid=0 · Sleep=0 · Modern Standby OFF</div>
      <div class="sa-detail">蓋を閉じても / アイドルが長くてもスリープに入らない</div>
    </div>
    <div class="sa-card sa-3">
      <div class="sa-num">3</div>
      <div class="sa-title">sshd · 鍵認証</div>
      <div class="sa-key">OpenSSH Server · ファイアウォール · DefaultShell=PowerShell</div>
      <div class="sa-detail">100.64.0.0/10 のみ許可 + パスワード遮断</div>
    </div>
    <div class="sa-card sa-4">
      <div class="sa-num">4</div>
      <div class="sa-title">Windows Update</div>
      <div class="sa-key">自動再起動の遮断</div>
      <div class="sa-detail">ログイン中ユーザーがいる時の強制再起動を禁止</div>
    </div>
    <div class="sa-card sa-5">
      <div class="sa-num">5</div>
      <div class="sa-title">ヘルスチェック</div>
      <div class="sa-key">SchTasks · 5分周期 · SYSTEM権限</div>
      <div class="sa-detail">tailscaled / sshdが落ちたら即座に再起動</div>
    </div>
  </div>
  <p class="sa-cap">この五つの軸がすべて適用された状態で初めて「無人15時間+ 安定 / 自己修復トリガー0件」のメトリクスが出ます。</p>
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

### 軸1 — Tailscaleインストール + Exit Node広告

```powershell
winget install --id tailscale.tailscale --silent `
    --accept-package-agreements --accept-source-agreements

& 'C:\Program Files\Tailscale\tailscale.exe' up `
    --advertise-exit-node `
    --ssh `
    --hostname=samsung-home-laptop
```

三つのオプションの意味:

| オプション | 意味 | 付けないと |
|---|---|---|
| `--advertise-exit-node` | 「他のノードのインターネット出口として使える」とtailnetに広告 | exit node候補に挙がらない |
| `--ssh` | Tailscale独自のSSHを有効化（Tailscale認証によるSSH） | OpenSSHのみ残る。バックアップチャネルが一本減る |
| `--hostname=` | tailnet内で表示されるホスト名 | Windowsのコンピュータ名のまま（`DESKTOP-...`）で識別が難しい |

最後に **Tailscale管理コンソールでexit node広告を明示的に承認** + **Disable key expiryのチェック**（90日自動ログアウト防止）。これをしないと広告だけ出て他のノードが使えず、90日後にノードが自動的にtailnetから外れます。

> ### ちょっと待って、これだけ確認しておこう
>
> **「無人サーバーは user device ではなく 'tagged resource' として分類するのが標準だ」**
>
> Tailscaleはノードを二種類に分類します（[公式ドキュメント](https://tailscale.com/kb/1068/acl-tags)）:
>
> - **User device** — 一人のユーザーが所有するノートPC・スマホ。**デフォルトで90日のkey expiry**がかかり定期的に再認証が必要。ユーザーアカウントが削除されるとそのデバイスも一緒に削除される。
> - **Tagged resource** — 無人サーバー。**key expiryがデフォルトで無効化**され永続維持。ユーザーアカウントから分離されたservice-based identity。
>
> Tailscale公式の表現 — "When you apply a tag to a device for the first time and authenticate it, the tagged device's key expiry is disabled by default."
>
> 本シリーズでは釜山のノートPCをuser deviceとして登録した後、adminコンソールで **Disable key expiry** を手動でチェックする方式を採用しました（セットアップの簡潔さのため)。より標準的な運用は最初から **tagged resource** として登録することです。
>
> ```powershell
> # tagged resource として登録する方法（参考）
> & 'C:\Program Files\Tailscale\tailscale.exe' login --advertise-tags=tag:exit-node
> ```
>
> tagOwnersをACL JSONに定義する必要があるため本シリーズの一人運用ではシンプルな方式を取りますが、長期無人 + 多人数運用シナリオであればtag方式が正解です。

### 軸2 — 電源・クラムシェル

実家の家族がノートPCの蓋を閉じても動作が維持されないといけません。すべてのスリープトリガーを0に削ぎ落とします。

```powershell
powercfg /change standby-timeout-ac 0       # スリープタイムアウト = なし
powercfg /change disk-timeout-ac 0          # ディスク省電力 = なし
powercfg /hibernate off                     # ハイバネート無効化

# 蓋を閉じる → 何もしない (AC、DC両方)
powercfg /setacvalueindex SCHEME_CURRENT SUB_BUTTONS LIDACTION 0
powercfg /setdcvalueindex SCHEME_CURRENT SUB_BUTTONS LIDACTION 0
powercfg /setactive SCHEME_CURRENT

# Modern Standby (S0) 無効化 — Windows 11 ノートPCの落とし穴
reg add "HKLM\System\CurrentControlSet\Control\Power" `
    /v PlatformAoAcOverride /t REG_DWORD /d 0 /f
```

二行が決定的です。

- **`LIDACTION 0`（蓋を閉じる = 動作維持）** — デフォルト値1（スリープ）だと家族がノートPCの蓋を閉じた瞬間にスリープ → Wi-Fi切断 → 福岡からSSHが届かない。ACとDC両方を0に設定して初めて、短い停電時にもスリープを防げます。
- **`PlatformAoAcOverride 0`（Modern Standby無効化）** — Win 11ノートPCのモダンスタンバイがLidActionをバイパスして部分スリープをトリガーすることがあるため、このレジストリ値で従来のS3スリープに戻します。

> ### ちょっと待って、これだけ確認しておこう
>
> **「スリープってそんなに危険？起こせばいいんじゃない？」**
>
> 無人リモート運用ではスリープがすなわち **死** です。スリープに入ったノートPCはWi-Fi接続を維持しないため、福岡からSSHで起こすにはまず届かないといけないのに **届けないこと自体がスリープの定義** です。一度スリープに入った瞬間、実家の家族に「ノートPCにちょっと触ってくれない？」と頼まなければならないため、システム障害として扱うべきです。

### 軸3 — sshd・鍵認証・ファイアウォール

Tailscale独自のSSHがあっても **OpenSSHも同時に立ち上げておきます** — Tailscaleデーモンが何らかの理由で落ちた時にOpenSSHで復旧でき、`scp`・`rsync`のような標準ツールがOpenSSHの上でしか動作しないからです。

```powershell
# OpenSSH Server インストール + 自動起動
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
Start-Service sshd
Set-Service -Name sshd -StartupType Automatic

# デフォルトシェルを PowerShell に
New-ItemProperty -Path "HKLM:\SOFTWARE\OpenSSH" -Name DefaultShell `
    -Value "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" `
    -PropertyType String -Force

# ファイアウォール — Tailscale 帯域のみ許可
Get-NetFirewallRule -Name "OpenSSH-Server-In-TCP" |
    Set-NetFirewallRule -Enabled False
New-NetFirewallRule -Name "sshd-tailscale" `
    -DisplayName "OpenSSH SSH (Tailscale only)" `
    -Enabled True -Direction Inbound -Protocol TCP -LocalPort 22 `
    -RemoteAddress 100.64.0.0/10 -Action Allow
```

肝は **`RemoteAddress 100.64.0.0/10`** — Tailscale CGNAT帯域から入ってくるSSHのみ許可するこの一行です。インターネットからノートPCのグローバルIPの22番ポートを叩いても絶対に応答しないため、**bruteforce試行が0件になります**（後のセキュリティ監査結果を参照）。

`sshd_config`もパスワード認証を遮断し、鍵認証のみ許可します。

```
PasswordAuthentication no
ChallengeResponseAuthentication no
KbdInteractiveAuthentication no
PermitEmptyPasswords no
MaxAuthTries 3
LoginGraceTime 30s
```

> ### ちょっと待って、これだけ確認しておこう
>
> **「`administrators_authorized_keys`のACLが間違っているとsshdが黙って認証を拒否する」**
>
> Windows OpenSSHはAdministratorsグループのメンバーのSSH鍵を、ユーザーホームの`~/.ssh/authorized_keys`ではなく **`C:\ProgramData\ssh\administrators_authorized_keys`** から読み込みます。ところがこのファイルのACLが緩すぎる場合 — 例えば一般ユーザー（`Users`）や`Authenticated Users`グループに読み取り権限があると — sshdは **エラーメッセージを出さずに** 鍵を無視して認証を拒否します。
>
> 推奨ACLは次のように二項目だけ残します:
>
> ```powershell
> icacls $KeyFile /inheritance:r                  # 継承を無効化
> icacls $KeyFile /grant 'Administrators:F'       # Administrators のみ Full
> icacls $KeyFile /grant 'SYSTEM:F'               # SYSTEM のみ Full
> icacls $KeyFile /remove '*S-1-5-32-545'         # Users グループ削除
> icacls $KeyFile /remove '*S-1-5-11'             # Authenticated Users 削除
> ```
>
> `tailnet-ops/windows/install/add-ssh-key.ps1`が毎回鍵を追加するたびにこのACLを明示的に再設定する理由 — sshd側でデバッグログ無しで拒否されるため、**先制的に毎回強制するのが運用的に安全** だからです。

> ### ちょっと待って、これだけ確認しておこう
>
> **「PowerShellでssh-keygenのパスフレーズを作る時の注意点」**
>
> 別のWindowsマシンで鍵を作る際、PowerShellで空のパスフレーズを与えようと`ssh-keygen -N '""'`と書いてはいけません — PowerShellのsingle-quoted `'""'`は **リテラルな2文字 `""` のパスフレーズ** が鍵に埋め込まれてしまいます。
>
> 結果としてSSHクライアントが鍵のunlockに失敗して`Permission denied (publickey)`で弾かれ、`-vvv`に`read_passphrase: can't open /dev/tty`が見えます。**デバッグに`Server accepts key`まで出るためサーバーACL問題と誤診しやすいです**。
>
> 正しい使い方は`-N ''`（single-quotedの空文字列）。誤って作った鍵は`ssh-keygen -p -P '""' -N '' -f keyfile`で復旧。

### 軸4 — Windows Update自動再起動の遮断

Windows Updateが深夜に強制再起動するのがデフォルト動作ですが、それがスリープポリシー・ヘルスチェックと衝突して、起動後にsshdが復活しないシナリオが起こり得ます。

```powershell
# アクティブ時間 (Active Hours) を 0〜23 時に — 実質常時アクティブ
Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings" `
    -Name ActiveHoursStart -Value 0 -Type DWord
Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings" `
    -Name ActiveHoursEnd -Value 23 -Type DWord

# ログイン中ユーザーがいる時の自動再起動を禁止
$auPath = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU"
New-Item -Path $auPath -Force
Set-ItemProperty -Path $auPath -Name NoAutoRebootWithLoggedOnUsers -Value 1 -Type DWord
```

肝は **`NoAutoRebootWithLoggedOnUsers = 1`** — 実家のノートPCにユーザー（`Sehyup`）アカウントが常にログインされた状態のため、この一行で強制再起動がすべて無力化されます。パッチは受信しますが再起動は人がトリガーした時にだけ起こり、その人物が私たち（リモートから`shutdown /r /t 5`）です。

### 軸5 — ヘルスチェック（5分周期）

Tailscaleデーモンとsshdが落ちた時に自動で生き返らせる作業。**5分周期 / SYSTEM権限 / ユーザーログイン状態に無関係**。

```powershell
# C:\Users\Sehyup\tailscale-setup\healthcheck.ps1 (要約)
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

スケジューラ登録時の決定値テーブル:

| 項目 | 値 | なぜ |
|---|---|---|
| `UserId` | SYSTEM | ユーザーログインの有無に関係なく実行。クラムシェル無人運用の必須条件 |
| `RunLevel` | Highest | サービス再起動権限が必要 |
| トリガー | AtStartup + 5分周期 | 起動直後に1回 + 以降5分のcadence |
| `AllowStartIfOnBatteries` | True | 短い停電でバッテリーモードでもヘルスチェックを継続 |
| `DontStopIfGoingOnBatteries` | True | 同上の理由 |

特に **SYSTEM権限** が決定的です — ユーザー権限で登録するとクラムシェルを閉じたノートPC（ロック状態）でタスクがキューに溜まるだけで実行されないケースがあります。

---

## Phase 2 — 福岡からの無人運用

5分ヘルスチェックの上に **毎日23:59に回る自己修復4種** をさらに重ねます。これがあるおかげで「実家に一度も行かなくても新しいデバイスを追加できる運用」が成立します。

### 自己修復4種のタスク表

<div class="self-heal" style="margin:1.5rem 0">
  <div class="sh-grid">
    <div class="sh-card sh-1">
      <div class="sh-name">RestartTailscale</div>
      <div class="sh-when">毎日 23:59</div>
      <div class="sh-what">Tailscaleデーモンの強制再起動 + statusログ</div>
      <div class="sh-why">メモリリーク・セッションのもつれなど、5分ヘルスチェックでは捕まえられない累積問題を毎日一度クリーンアップ</div>
    </div>
    <div class="sh-card sh-2">
      <div class="sh-name">RestartSshd</div>
      <div class="sh-when">毎日 23:59</div>
      <div class="sh-what">sshdの強制再起動</div>
      <div class="sh-why">新しい鍵登録後の反映を保証 + 累積セッションの整理</div>
    </div>
    <div class="sh-card sh-3">
      <div class="sh-name">AddSshKey</div>
      <div class="sh-when">毎日 23:59 (または手動トリガー)</div>
      <div class="sh-what">pending-key.txtがあれば administrators_authorized_keys に追加 + 権限再設定 + sshd再起動</div>
      <div class="sh-why">新規デバイスの追加 — 福岡からSSH一行で実家ノートPCに鍵を登録</div>
    </div>
    <div class="sh-card sh-4">
      <div class="sh-name">DiagnosticDump</div>
      <div class="sh-when">毎日 23:59</div>
      <div class="sh-what">システム・ネットワーク・サービス・スケジュール・ログ一式を dump.txt にダンプ</div>
      <div class="sh-why">事故時に福岡からSSH一回で診断を受け取る</div>
    </div>
  </div>
  <p class="sh-cap">4つすべて SYSTEM権限 / WakeToRun / バッテリーモード許可 / RestartCount 3.</p>
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

この4つ + 5分ヘルスチェック = SchTasks 5種。第1回のメトリクスカードの「**SchTasks Ready 5/5**」がこの5つを指します。

### 運用パターン1 — 新しいSSH鍵の登録（最も頻繁に使う流れ）

福岡のデスクトップでも新しいスマホでも、新規デバイスをtailnetに合流させる時、そのデバイスのSSH公開鍵を釜山ノートPCの`administrators_authorized_keys`に登録する必要があります。実家に行かず、福岡からSSH一行で処理します。

```bash
# 福岡の Mac から
ssh samsung-home-laptop "Set-Content C:\Users\Sehyup\tailscale-setup\pending-key.txt '<公開鍵 1行>'; schtasks /Run /TN AddSshKey"
sleep 5
ssh samsung-home-laptop "Get-Content C:\Users\Sehyup\tailscale-setup\add-ssh-key.log -Tail 5"
```

この一行が動作する理由:

1. 一般SSHセッションの権限では`C:\ProgramData\ssh\administrators_authorized_keys`に直接書けない（管理者ACL）
2. そのため`pending-key.txt`だけを一般権限で作成
3. **`AddSshKey`タスクをSYSTEM権限でトリガー** → SYSTEMがそのファイルを読んで`administrators_authorized_keys`に追加
4. 権限再設定（`icacls /inheritance:r` + Administrators/SYSTEMのみFull Control）
5. sshd再起動
6. `pending-key.txt`削除

`AddSshKey`タスクが行うことをコードで見ると（`tailnet-ops/windows/install/add-ssh-key.ps1`抜粋）:

```powershell
# 鍵フォーマット検証
if ($line -notmatch '^(ssh-ed25519|ssh-rsa|ecdsa-sha2-)') {
    L "invalid key format: ..."
    Remove-Item $Pending -Force; exit 1
}

# 重複チェック
$keyOnly = ($line -split '\s+')[1]
foreach ($existing in (Get-Content $KeyFile)) {
    if (($existing -split '\s+')[1] -eq $keyOnly) { $dup = $true; break }
}

if (-not $dup) {
    Add-Content -Path $KeyFile -Value $line -Encoding ASCII
    icacls $KeyFile /inheritance:r
    icacls $KeyFile /grant 'Administrators:F'
    icacls $KeyFile /grant 'SYSTEM:F'
    icacls $KeyFile /remove '*S-1-5-32-545'  # Users グループ削除
    Restart-Service sshd
}
Remove-Item $Pending -Force
```

三つの安全装置 — **(a) 鍵フォーマットのsanity check、(b) 重複登録防止、(c) 毎回ACL再設定**。最後のACL再設定が肝で、Windows OpenSSHの`administrators_authorized_keys`は権限が緩すぎると **sshdが黙って認証を拒否する** ためデバッグの難しい領域です。

> ### ちょっと待って、これだけ確認しておこう
>
> **「なぜわざわざSYSTEM権限で迂回するのか？sudoのようなものは無いの？」**
>
> WindowsにはLinuxの`sudo`のように一行コマンドを権限昇格して実行する標準メカニズムがありません（2024年から一部導入されましたが11 Homeでは未対応）。
>
> 代替は二つでした:
>
> 1. SSHセッションを **管理者PowerShellで** 立ち上げる — セキュリティ面でリスクあり。日常SSHセッションが管理者権限だと事故の表面積が広がる
> 2. **権限分離** — 一般権限のSSHセッションはファイル作成のみ担当し、権限昇格はSYSTEMのSchTasksが担う
>
> 本シリーズでは2を採用しました。結果として **SSHセッションは日常権限のまま維持** され、**権限昇格は検証済みスクリプト（`add-ssh-key.ps1`）の中だけで** 起こります。これが運用的にもクリーンです。

### 運用パターン2 — 診断ダンプ

リモートからノートPCの状態を総合的に取得したい時:

```bash
ssh samsung-home-laptop "schtasks /Run /TN DiagnosticDump"
sleep 3
ssh samsung-home-laptop "Get-Content C:\Users\Sehyup\tailscale-setup\dump.txt -Encoding UTF8"
```

`DiagnosticDump`は次の9セクションを一つのファイルにまとめます（`tailnet-ops/windows/install/setup-helpers.ps1`）。

| セクション | 内容 |
|---|---|
| Hostname / Boot | ホスト名、最終起動時刻、現在時刻 |
| Tailscale status | `tailscale status`の出力 |
| Tailscale netcheck | DERP 28リージョンのRTT |
| Services | Tailscale、sshdサービスの状態 |
| Network adapters Up | 有効なネットワークアダプタ + LinkSpeed |
| IP Forwarding | exit nodeとして動作するためのforwarding設定 |
| Power state | 有効な電源ポリシー + スリープ要求 + 最終wake |
| Scheduled tasks | 5種のSchTasksの状態 |
| Health log (last 30) | ヘルスチェックログ最終30行 |
| OpenSSH events (last 20) | 直近のSSHイベント |

このワンショットでノートPCに何が起きたかを福岡から即座に把握できます。

### 運用パターン3 — 事故シナリオの復旧

代表的な4つのシナリオと復旧経路:

| シナリオ | 復旧経路 | 実家への直接訪問が必要？ |
|---|---|---|
| Tailscaleは生きているがSSHだけ死亡 | 毎日23:59の`RestartSshd`で自動復旧 / 即時にはTailscale SSHを活用 | × |
| SSH鍵紛失（Mac再フォーマット） | 福岡デスクトップの鍵で新しい鍵を登録 / 両方塞がれたら実家訪問 | (条件付き) |
| 停電後ノートPCが起動しない | BIOSのAC Power Recovery設定に依存 — **実家訪問以外に検証手段なし** | ○ |
| Wi-Fiパスワード変更 | 自動復旧不可、家族に新パスワードを案内して再接続を依頼 | (家族の協力) |

多重化が肝です — **Mac鍵 + 福岡デスクトップ鍵を両方とも登録維持** しておくと、片方のデバイスが死んでももう片方ですべての運用が可能です。

---

## Phase 3 — セキュリティ監査（13項目チェック）

`security-audit.ps1`はSSH・アカウント・ファイアウォール・RDP・Defender・Tailscale ACLなど13領域をチェックします。各領域の意味を整理しておきます。

| # | チェック領域 | 何を確認 |
|---|---|---|
| 1 | sshd 設定 | PasswordAuth=no, MaxAuthTries=3, LoginGraceTime=30s, KbdInteractive=no |
| 2 | authorized_keys | 登録鍵のSHA256 fingerprint + ACL |
| 3 | Listening TCP ports | 22番以外に意図しないポートが開いていないか |
| 4 | Firewall (Inbound Allow) | sshd-tailscaleのみ / デフォルトSSHルールはDisabled |
| 5 | Local user accounts | Administratorsグループのメンバー + パスワードポリシー |
| 6 | RDP status | `fDenyTSConnections=1`（RDP無効化） |
| 7 | SMB / file sharing | 公開された共有フォルダ |
| 8 | Windows Defender | リアルタイム保護 + Tamper Protection + 定義ファイルの更新日数 |
| 9 | **Failed SSH (24h)** | 直近24時間の認証失敗回数（目標: 0件） |
| 10 | Tailscale ACL | 自ノードのタグ + exit node広告 + WhoIs |
| 11 | UAC settings | EnableLUA, ConsentPromptBehavior |
| 12 | Recent successful SSH (24h) | 正常接続のIP一覧（想定外IPがあれば即座に調査） |
| 13 | Outbound suspicious processes | TeamViewer/AnyDesk/VNC のような遠隔制御ツールが動いていないか |

主要な結果（2026-05計測時点）:

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
      <div class="ar-val">0件</div>
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
      <div class="ar-val">なし</div>
    </div>
    <div class="ar-card ar-pass">
      <div class="ar-icon">✓</div>
      <div class="ar-name">Patchword bruteforce</div>
      <div class="ar-val">即時拒否</div>
    </div>
  </div>
  <p class="ar-cap">13項目すべてパス。SSH認証失敗0件はTailscale-only firewall一行の成果です。</p>
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

**24時間SSH認証失敗0件** が最も意味のある結果です。一般的なインターネット露出SSHは1日に数千〜数万件のbruteforce試行が押し寄せますが、**Tailscale-only firewall一行でその試行がルーター段で遮断** され、sshdログに到達することすらできません。

参考までに、インターネット露出SSHの一般的なbruteforce統計（セキュリティ業界の一般的な報告値）:

| 環境 | 1日あたりのbruteforce試行 |
|---|---|
| 一般家庭回線で露出した22番ポート | 約1,000〜10,000件 |
| クラウドVM (AWS/GCP/Azure) の22番ポート | 約10,000〜50,000件 |
| 本シリーズ (Tailscale-only firewall) | **0件** (sshdログに到達すらしない) |

ルーターのファイアウォールがパケットを拒否するため、釜山ノートPCのsshdはそのような試行が存在することすら知りません。鍵認証 + MaxAuthTries 3 + LoginGraceTime 30sは **それが破られた時に備えた2次・3次防衛線** としてのみ意味を持ちます。

> ### ちょっと待って、これだけ確認しておこう
>
> **「グローバルIPの22番ポートが塞がっているかどうやって検証する？」**
>
> 実家の中では同じLANなので意味のある検証ができないため、**別のネットワーク（例: カフェの4G・モバイル通信）から** 釜山ノートPCのグローバルIPの22番ポートを叩いてみる必要があります。
>
> ```bash
> nc -zv <釜山のグローバルIP> 22  # タイムアウト or connection refused が正常
> ssh samsung-home-laptop          # Tailscale 100.64.x.x で即接続 (正常)
> ```
>
> 二つの結果が同時に出て初めて、セットアップが意図通りに動いていることになります — インターネットからは届かず、tailnet内では届きます。

### Tailscale ACL — もう一枚の防衛線

ファイアウォールがルーター段でIP帯域を濾すなら、**Tailscale ACLはtailnet内で誰がどのノードのどのポートに到達できるかを制御** します。ACLポリシーはadminコンソールのポリシーファイル（JSON）で定義します。

> Tailscaleの表現 — "ACLs are deny-by-default, directional, and locally enforced." ([公式ドキュメント](https://tailscale.com/kb/1018/acls))

**deny-by-default** の意味が大きいです — ACLを定義しなければデフォルトポリシーは「tailnet内のすべてのノードが互いの全ポートにアクセス可能」ですが、一度ACLを書いた途端にその中で **明示的に許可されたもの以外のすべてのトラフィックが拒否** されます。SSHも同様に **明示的なsshポリシー** で許可しないと届きません。

本シリーズの一人運用向けの推奨ACLパターン例:

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

このACLが強制するもの:

- **`group:admin`ユーザーのデバイスのみ** がtailnetノード群にアクセス可能（他のinviteeが追加されても自動で遮断）
- **タグベースのノード分類** — exit-nodeとclientを分離し、それぞれ別のポリシーを与えられる
- **SSHは`group:admin`が`tag:exit-node`の`sehyup`または非rootユーザーとしてのみ** 可能 — root SSHは自動遮断

ACL JSONを一度書いておくことが、結果として13項目セキュリティチェックの4番（ファイアウォール）、9番（SSH失敗）、12番（SSH成功）のすべてを強化します。

### Tailscale本体のセキュリティ事案履歴

「Tailscaleは信頼できるか」という問いに対する正直な答えは — **それ自身に欠陥が発見された前例があり、会社が公開のセキュリティ勧告で対応** してきたということです。公開されている [Security Bulletins](https://tailscale.com/security-bulletins) のうち主な項目:

| ID | 影響 | 対応 |
|---|---|---|
| **CVE-2022-41924** (Critical) | Windowsクライアントのローカル API再構成によるリモートコード実行 | パッチ + 自動更新の推奨 |
| **TS-2024-005** | サブネットルーターのLinuxノードでLAN機器のインバウンドフィルタリングが不足 | 1.66.0+へアップグレード |
| **TS-2025-005** | MDM認証鍵がログサーバーにアップロード | 1.86.4+で修正、鍵ローテーション推奨 |
| **TS-2026-001** | macOSの`tssentineld`権限昇格による任意コマンド実行 | 1.94.0+へアップグレード |

このうち **CVE-2022-41924** が最も重い事案でしたが、発見後に会社が公開勧告とパッチを素早く出し、自動更新を推奨する対応パターンは正常でした。**本シリーズインフラの運用側の推奨**:

- Tailscale自動更新の有効化（`tailscale set --auto-update`）
- セキュリティ勧告は [tailscale.com/security-bulletins](https://tailscale.com/security-bulletins) を定期的に確認
- 上のACLポリシーで事故時の爆風半径（blast radius）を最小化

「無料 + E2E暗号化 + SOC 2認証」だからといって無欠ではないという点 — これが日常運用の現実です。

---

## 検証 — `status.ps1` 一発

五つの軸が適用され自己修復まで登録された状態で`status.ps1`を一度回せば、システム全体の状態が一画面に表示されます。実家を発つ直前にこの出力をキャプチャして、福岡で比較用のbaselineとして使います。

```bash
ssh samsung-home-laptop 'powershell -NoProfile -ExecutionPolicy Bypass `
    -File C:\Users\Sehyup\tailscale-setup\status.ps1'
```

期待される出力（概念形式）:

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

この8領域すべてが正常であれば実家を離れて大丈夫です。

---

## 実家を発つ直前のチェックリスト

| # | 項目 | 検証方法 |
|---|---|---|
| 1 | コンピュータ名が`samsung-home-laptop`で適用 | `hostname` |
| 2 | Tailscaleノードのadminコンソール登録 + Exit Node承認 + Disable key expiry | ブラウザ |
| 3 | sshdサービスが Running + Automatic | `Get-Service sshd` |
| 4 | ファイアウォール: `sshd-tailscale` Enabled / デフォルトルール Disabled | `Get-NetFirewallRule "sshd-*"` |
| 5 | **別ネットワークから** SSH接続成功（4Gなど） | `ssh samsung-home-laptop` |
| 6 | クラムシェル状態で`status.ps1` baselineをキャプチャ | 上記コマンド |
| 7 | `NoAutoRebootWithLoggedOnUsers=1`が適用されている | レジストリ確認 |
| 8 | **多重化**: 福岡デスクトップからもSSH可能 | `ssh samsung-home-laptop`（別マシン） |
| 9 | Mac SSH鍵のバックアップ（1Password / iCloud Keychain） | バックアップツール確認 |
| 10 | (任意) Samsung Settingsでバッテリー80%充電制限 | Microsoft Storeアプリ |

チェックリストの5番が最も重要です — 別ネットワークから入って、Tailscale exit node経由で釜山のIPが出てくるかを確認して初めて本当の検証になります。

10番はノートPCのバッテリー劣化防止 — 24/7 AC接続環境で100%フル充電維持はバッテリーセル寿命を急速に削ります。Samsung Settingsの「バッテリー寿命延長モード」をONにしておくと80%で充電を停止します。

---

## まとめ

この回でやったことを一つの表に:

| Phase | 主要決定値 | 一行の理由 |
|---|---|---|
| セットアップ | `--advertise-exit-node`, `LIDACTION=0`, `100.64.0.0/10` only, `NoAutoRebootWithLoggedOnUsers=1`, `RunAs=SYSTEM` | 五つの軸を一度セットアップすれば無人24/7が可能 |
| 運用 | 5分ヘルスチェック + 毎日23:59の自己修復4種 | 実家に行かなくてもデバイス追加・診断・復旧が可能 |
| セキュリティ | Tailscale-only firewall + 鍵認証 + 13項目の定期チェック | SSH認証失敗24h 0件。bruteforceがルーター段で遮断 |

実家1回訪問で済ませる仕事はここまでです。この状態でノートPCの蓋を閉じて福岡に戻っても無人運用がそのまま回り、新規デバイス追加もSSH一行で処理できます。

次回は、このシステムが動作する **作動原理**（DERP・MagicDNS・hole punching）と **年間1,100円コスト振り返り**（電気代・インターネット・ノートPCの劣化・時間コスト）でシリーズを締めくくります。

---

## 参考資料

- [`Epheria/tailnet-ops`](https://github.com/Epheria/tailnet-ops) — 本シリーズの運用コード一式
  - [`windows/install/install.ps1`](https://github.com/Epheria/tailnet-ops/blob/main/windows/install/install.ps1) — 統合セットアップスクリプト
  - [`windows/install/setup-helpers.ps1`](https://github.com/Epheria/tailnet-ops/blob/main/windows/install/setup-helpers.ps1) — 自己修復4種の登録
  - [`windows/install/add-ssh-key.ps1`](https://github.com/Epheria/tailnet-ops/blob/main/windows/install/add-ssh-key.ps1) — 権限分離による鍵登録ロジック
  - [`windows/ops/status.ps1`](https://github.com/Epheria/tailnet-ops/blob/main/windows/ops/status.ps1) — 状態の総合検証
  - [`windows/ops/security-audit.ps1`](https://github.com/Epheria/tailnet-ops/blob/main/windows/ops/security-audit.ps1) — 13項目のセキュリティチェック
  - [`docs/decisions.md`](https://github.com/Epheria/tailnet-ops/blob/main/docs/decisions.md) — 各決定値の「なぜ」
  - [`docs/runbook-busan-laptop.md`](https://github.com/Epheria/tailnet-ops/blob/main/docs/runbook-busan-laptop.md) — 日常運用の標準手順
  - [`docs/recovery.md`](https://github.com/Epheria/tailnet-ops/blob/main/docs/recovery.md) — 事故シナリオ別の復旧
- Tailscale Docs. *Exit nodes.* ([tailscale.com/kb/1103/exit-nodes](https://tailscale.com/kb/1103/exit-nodes))
- Tailscale Docs. *Tailscale SSH.* ([tailscale.com/kb/1193/tailscale-ssh](https://tailscale.com/kb/1193/tailscale-ssh))
- Tailscale Docs. *Tailnet policy file (ACL).* ([tailscale.com/kb/1018/acls](https://tailscale.com/kb/1018/acls))
- Tailscale Docs. *Tags — Identity for unattended devices.* ([tailscale.com/kb/1068/acl-tags](https://tailscale.com/kb/1068/acl-tags))
- Tailscale. *Security Bulletins.* ([tailscale.com/security-bulletins](https://tailscale.com/security-bulletins))
- Microsoft Docs. *OpenSSH for Windows overview.* ([learn.microsoft.com/windows-server/administration/openssh](https://learn.microsoft.com/windows-server/administration/openssh/openssh-overview))

---

## 次回

第3回はシリーズ最終回として二つを束ねます — **このシステムが動作する作動原理**（DERP relay、MagicDNS、NAT hole punching）と、**年間1,100円インフラのコスト・限界の振り返り** です。

> 第3回 — 作動原理 + コスト・限界 (執筆予定)
{: .prompt-info }
