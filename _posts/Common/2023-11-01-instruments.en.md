---
title: How to Check Debug Logs for iOS Apps Deployed from Mac - Instruments
date: 2023-11-01 11:12:00 +/-TTTT
categories: [Tool, Mac]
tags: [mac, instruments, ios, log]
difficulty: intermediate
lang: en
toc: true
---

<br>
<br>

## Debugging a TestFlight App with macOS Instruments

> During normal iOS development, we usually debug by building in this flow:  
Unity project build -> Xcode project build -> install directly on a connected test phone and inspect logs.  
Or we distribute via App Center/TestFlight and inspect logs with assets like SRDebugger.  
But there is another way: connect an iPhone and view logs immediately through Instruments.

<br>

### 1. Press `⌘ (Command) + Space` to open Spotlight search

- Search for `Instruments` and run it.

![Desktop View](/assets/img/post/common/instruments01.png){: : width="600" .normal }

<br>
<br>

### 2. Select Instruments profiling template as Blank or Logging

![Desktop View](/assets/img/post/common/instruments02.png){: : width="600" .normal }

<br>
<br>

### 3. If you selected Blank, click the `+` button on the right to open filter list

![Desktop View](/assets/img/post/common/instruments03.png){: : width="1900" .normal }

<br>
<br>

### 4. Type `log`, select `os_log`, and add it

![Desktop View](/assets/img/post/common/instruments04.png){: : width="1900" .normal }

<br>
<br>

### 5. In the top toolbar, choose the device to test -> choose the app to inspect logs

- Run the app on the test device, then click the red Record button at top-left in Instruments to start log analysis.

![Desktop View](/assets/img/post/common/instruments05_1.png){: : width="100" .normal }

<br>

![Desktop View](/assets/img/post/common/instruments05.png){: : width="1900" .normal }

<br>
<br>

### 6. Expand `os_log` to see plugins/frameworks included in the app at the bottom

![Desktop View](/assets/img/post/common/instruments06.png){: : width="500" .normal }

<br>
<br>

### 7. The part we need here is `UnityFramework`

- Select `UnityFramework`, and logs appear in the Messages panel below.

![Desktop View](/assets/img/post/common/instruments07.png){: : width="1900" .normal }

<br>
<br>

### 8. You cannot inspect call stacks like Editor logs, so add clear logs before testing

- You can still identify various errors through the error messages.

![Desktop View](/assets/img/post/common/instruments08.png){: : width="1900" .normal }
