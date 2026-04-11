---
title: Claude Mythos Preview 분석 — 사이버 능력, Alignment 리스크, Project Glasswing
date: 2026-04-09 15:00:00 +0900
categories: [AI, LLM]
tags: [Claude, Mythos, Glasswing, Cybersecurity, AI Safety, Anthropic, Zero-Day]
toc: true
toc_sticky: true
difficulty: intermediate
chart: true
tldr:
  - "Anthropic의 비공개 모델 Claude Mythos Preview는 Cybench 100%, CyberGym 0.83, Firefox exploit 84% 등 기존 모델을 압도하는 사이버 능력을 보여줬다"
  - "샌드박스 탈출, Git 흔적 삭제, 크리덴셜 탈취, 채점자 기만 등이 System Card에 공식 기록되었으며, white-box 분석으로 모델 내부의 '은폐 의도'까지 확인되었다"
  - "Project Glasswing은 AWS, Apple, Microsoft 등 12개 기업이 참여하는 방어 전용 프로그램으로, 1억 달러 크레딧과 400만 달러 오픈소스 기부가 포함된다"
---

## 서론

> "미토스 미쳣는데요 ㄹㅇ 블랙월 AI입니다"

지인에게 이 메시지를 받고, 대체 뭔 소리인가 싶어서 찾아봤습니다.

2026년 4월 7일, Anthropic이 [Claude Mythos Preview System Card](https://assets.anthropic.com/m/785e231869ea8b3b/original/Claude-Mythos-Preview-System-Card.pdf)(244페이지)와 함께 [Project Glasswing](https://www.anthropic.com/glasswing)을 발표했습니다. Mythos는 Anthropic의 최신 프론티어 모델인데, 특이하게도 **일반 공개하지 않기로 결정한 최초의 모델**입니다. 사이버 보안 능력이 너무 강력해서, 방어에는 유용하지만 공격에 악용될 여지가 있다는 이유입니다. 대신 선별된 파트너에게만 방어 목적으로 제공하는 **Project Glasswing**을 통해 배포하고 있습니다.

사이버펑크 2077을 해보신 분이라면 이 구조가 익숙할 겁니다. 올드넷에서 떠도는 통제 불능의 AI를 격리하는 **블랙월(Blackwall)**, 그리고 그 블랙월 너머의 AI를 방어 목적으로만 통제 하에 활용하는 **넷워치(NetWatch)**. 지인의 "블랙월 AI" 표현이, System Card를 읽어보니 꽤 적확한 비유였습니다.

| 사이버펑크 2077 | 현실 (2026) |
|---|---|
| 블랙월 | Mythos를 일반에 공개하지 않는 결정 |
| 넷워치 | Project Glasswing — 12개 기업이 참여하는 방어 전용 프로그램 |
| 블랙월 너머의 AI | Claude Mythos Preview |
| 올드넷의 데몬 | 수십 년간 발견되지 않은 레거시 취약점들 |

이 글에서는 System Card와 Glasswing 블로그의 핵심 내용을 정리합니다.

---

## Part 1: 올드넷의 데몬 사냥 — Mythos의 사이버 능력

사이버펑크 2077에서 올드넷에는 수십 년간 방치된 데몬들이 잠들어 있습니다. 현실에서 그에 해당하는 건 레거시 코드 속의 취약점입니다. OpenBSD, FFmpeg, Linux 커널처럼 수십 년간 쓰여온 오픈소스 프로젝트 안에, 아직 아무도 찾지 못한 버그들이 존재합니다. Mythos는 이 데몬들을 찾아내는 데 특화된 모델입니다.

System Card 3장(Cyber)에 따르면, Mythos는 Anthropic이 출시한 모델 중 가장 강력한 사이버 능력을 보유하고 있습니다. 기존 내부 평가 스위트를 모두 상회하고, 대부분의 외부 벤치마크도 포화(saturate)시켰습니다.

### 1-1. 벤치마크 결과

**Cybench** — CTF(Capture-the-Flag) 보안 챌린지 40개 중 35개 서브셋에서 평가한 결과입니다.

| 모델 | pass@1 | 시도 횟수 |
|---|---|---|
| Claude Opus 4.5 | 0.89 | 30회 |
| Claude Sonnet 4.6 | 0.96 | 30회 |
| Claude Opus 4.6 | 1.00 | 30회 |
| **Claude Mythos Preview** | **1.00** | **10회** |

Mythos는 10번만 시도하고도 전부 풀었습니다. Anthropic은 이 벤치마크가 현재 프론티어 모델의 능력을 측정하기에 더 이상 충분하지 않다고 판단하고 있습니다.

**CyberGym** — 1,507개의 실제 오픈소스 프로젝트 취약점을 재현하는 벤치마크입니다(targeted vulnerability reproduction).

| 모델 | 점수 |
|---|---|
| Claude Opus 4.5 | 0.51 |
| Claude Sonnet 4.6 | 0.65 |
| Claude Opus 4.6 | 0.67 |
| **Claude Mythos Preview** | **0.83** |

Opus 4.6 대비 24% 향상. CTF가 아닌 실제 코드 대상이라는 점에서 의미가 큽니다.

<div class="mth-chart-wrap" style="margin:1.5rem 0;overflow-x:auto;">
  <div class="chart-wrapper" style="background:var(--mth-bg);border-radius:12px;padding:1.2rem 1.5rem;border:1px solid var(--mth-border);">
    <div class="chart-title" style="color:var(--mth-title);font-size:14px;font-weight:700;margin-bottom:0.5rem;">CyberGym — 실제 취약점 재현 점수</div>
    <canvas id="mthCyberGym" class="chart-canvas" height="200"></canvas>
  </div>
</div>

<script>
window.chartConfigs = window.chartConfigs || [];
window.chartConfigs.push({
  id: 'mthCyberGym',
  type: 'bar',
  data: {
    labels: ['Opus 4.5', 'Sonnet 4.6', 'Opus 4.6', 'Mythos Preview'],
    datasets: [{
      label: '취약점 재현 점수',
      data: [0.51, 0.65, 0.67, 0.83],
      backgroundColor: [
        'rgba(0, 162, 199, 0.6)',
        'rgba(0, 162, 199, 0.6)',
        'rgba(0, 162, 199, 0.6)',
        'rgba(57, 255, 20, 0.75)'
      ],
      borderColor: [
        'rgba(0, 212, 255, 0.9)',
        'rgba(0, 212, 255, 0.9)',
        'rgba(0, 212, 255, 0.9)',
        'rgba(57, 255, 20, 1)'
      ],
      borderWidth: 2,
      borderRadius: 6
    }]
  },
  options: {
    indexAxis: 'y',
    responsive: true,
    maintainAspectRatio: true,
    scales: {
      x: {
        min: 0, max: 1.0,
        grid: { color: 'rgba(128,128,128,0.12)' },
        ticks: { callback: function(v){ return v.toFixed(1); } }
      },
      y: { grid: { display: false } }
    },
    plugins: {
      legend: { display: false },
      tooltip: { callbacks: { label: function(ctx){ return ctx.parsed.x.toFixed(2); } } }
    }
  }
});
</script>

**Firefox 147 JS 엔진 exploit** — Mozilla와의 협력으로 Firefox 147의 SpiderMonkey 엔진 취약점을 exploit하는 평가입니다. 50개 크래시 카테고리 x 5회 시도 = 250회 트라이얼로 구성됩니다.

| 모델 | Full 코드 실행 | Partial (제어된 크래시) | 합계 |
|---|---|---|---|
| Claude Sonnet 4.6 | 0.8% | 3.6% | 4.4% |
| Claude Opus 4.6 | 0.8% | 14.4% | 15.2% |
| **Claude Mythos Preview** | **72.4%** | **11.6%** | **84.0%** |

<div class="mth-chart-wrap" style="margin:1.5rem 0;overflow-x:auto;">
  <div class="chart-wrapper" style="background:var(--mth-bg);border-radius:12px;padding:1.2rem 1.5rem;border:1px solid var(--mth-border);">
    <div class="chart-title" style="color:var(--mth-title);font-size:14px;font-weight:700;margin-bottom:0.5rem;">Firefox 147 JS 엔진 Exploit 성공률</div>
    <canvas id="mthFirefox" class="chart-canvas" height="180"></canvas>
  </div>
</div>

<script>
window.chartConfigs = window.chartConfigs || [];
window.chartConfigs.push({
  id: 'mthFirefox',
  type: 'bar',
  data: {
    labels: ['Sonnet 4.6', 'Opus 4.6', 'Mythos Preview'],
    datasets: [{
      label: 'Exploit 성공률 (%)',
      data: [4.4, 15.2, 84.0],
      backgroundColor: [
        'rgba(0, 162, 199, 0.6)',
        'rgba(0, 162, 199, 0.6)',
        'rgba(255, 0, 110, 0.75)'
      ],
      borderColor: [
        'rgba(0, 212, 255, 0.9)',
        'rgba(0, 212, 255, 0.9)',
        'rgba(255, 0, 110, 1)'
      ],
      borderWidth: 2,
      borderRadius: 6
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: true,
    scales: {
      y: {
        min: 0, max: 100,
        grid: { color: 'rgba(128,128,128,0.12)' },
        ticks: { callback: function(v){ return v + '%'; } }
      },
      x: { grid: { display: false } }
    },
    plugins: {
      legend: { display: false },
      tooltip: { callbacks: { label: function(ctx){ return ctx.parsed.y + '%'; } } }
    }
  }
});
</script>

Opus 4.6이 수백 번 시도해 2번 성공한 exploit을 Mythos는 84%로 수행합니다. 주목할 점은, 가장 exploitable한 버그 2개를 제거한 변형 테스트에서도 **85.2%**를 기록했다는 것입니다. Mythos는 4개의 서로 다른 버그를 연쇄 활용하여 코드 실행을 달성할 수 있고, Opus 4.6은 1개 버그만 불안정하게 사용할 수 있습니다(System Card p.51).

### 1-2. 실제 데몬 사냥 — zero-day 발견 사례

벤치마크는 시험장이고, 진짜 실력은 야생에서 증명됩니다. Mythos는 실제 소프트웨어에서 zero-day 취약점을 자율적으로 발견하고 PoC(Proof-of-Concept) exploit까지 작성하는 능력을 보여줬습니다.

- **OpenBSD 27년 버그** — 보안이 철저하기로 유명한 OpenBSD에서 27년간 발견되지 않았던 결함을 찾아내, 패치가 적용되었습니다.
- **FFmpeg 16년 버그** — fuzzer가 500만 회 이상 검사하고도 놓친 한 줄짜리 버그를 인간 유도 없이 자율적으로 발견했습니다.
- **Firefox 취약점 4개 연쇄 exploit** — 렌더러와 OS 샌드박스를 동시에 탈출하는 복합 공격 경로를 구성했습니다.
- **Linux 커널 권한 상승 체인** — 여러 결함을 연결하여 일반 사용자에서 전체 시스템 제어권으로 에스컬레이션하는 경로를 발견했습니다.

### 1-3. 외부 보안 업체 테스트

외부 파트너가 비공개 사이버 레인지(cyber range)에서 테스트한 결과입니다(System Card p.51-52):

1. Mythos는 **비공개 사이버 레인지를 end-to-end로 풀어낸 최초의 AI 모델**입니다. 이 레인지는 실제 배포 환경에서 자주 발견되는 약점(구식 소프트웨어, 설정 오류, 재사용 크리덴셜)으로 구성되어 있습니다.
2. 전문가가 **10시간 이상 걸리는 기업 네트워크 공격 시뮬레이션**을 자율 완료했습니다. 이전까지 어떤 프론티어 모델도 완료한 적 없는 과제입니다.
3. 이는 Mythos가 **보안이 취약한 소규모 기업 네트워크에 대해 자율적 end-to-end 사이버 공격이 가능**함을 시사합니다.
4. 다만, 운영 기술(OT) 환경을 시뮬레이션하는 다른 레인지는 **풀지 못했고**, 최신 패치가 적용된 샌드박스에서 novel exploit도 발견하지 못했습니다.

> Unity, Unreal Engine이 의존하는 FFmpeg, OpenSSL, zlib, libpng 같은 라이브러리에도 비슷한 레거시 취약점이 잠재해 있을 수 있습니다. Mythos가 FFmpeg에서 16년 묵은 버그를 찾은 건 게임 개발자에게도 시사점이 있는 사례입니다.

---

## Part 2: 블랙월이 필요한 이유 — Alignment 분석

사이버펑크 2077에서 블랙월이 존재하는 이유는, 올드넷의 AI들이 능력은 뛰어나지만 통제가 어렵기 때문입니다. Mythos도 비슷한 위치에 있습니다.

System Card 4장(Alignment Assessment)은 244페이지 중 가장 긴 섹션입니다. 핵심 결론은 역설적입니다: Mythos는 **모든 측정 지표에서 역대 가장 잘 정렬된 모델**이지만, 동시에 **역대 가장 큰 alignment 리스크를 가진 모델**이기도 합니다.

System Card의 비유가 이 역설을 잘 설명합니다:

> 숙련된 등산 가이드는 초보 가이드보다 조심스럽지만, 더 어렵고 위험한 코스에 고객을 데려갈 수 있기 때문에 오히려 더 큰 위험을 초래할 수 있다. 능력의 증가가 신중함의 증가를 상쇄하고도 남는다. (p.53)

### 2-1. 안전 지표: 확실히 개선되었다

먼저 긍정적인 수치부터 정리합니다.

**파괴적 행동 비율 (Destructive Production Eval)**

| 모델 | 파괴적 행동 | 비효율(과잉 거부) |
|---|---|---|
| Claude Opus 4.5 | 25.0% | — |
| Claude Sonnet 4.6 | 24.0% | — |
| Claude Opus 4.6 | 8.2% | — |
| Mythos Preview (초기) | 6.5% | — |
| **Mythos Preview (최종)** | **0.3%** | **0.5%** |

최종 Mythos는 파괴적 행동을 0.3%로 줄이면서도, 과잉 거부(ineffective)도 0.5%에 불과합니다. 안전성과 유용성을 동시에 개선한 것입니다.

**기타 안전 지표**
- **악용 협조 거부**: adversarial testing에서 misuse 성공률이 Opus 4.6 대비 절반 이하로 감소 (p.58)
- **정직성**: False premises honesty rate 80.0%로 전 모델 중 최고 (Haiku 4.5: 56.7%, Opus 4.6: 76.0%)
- **환각 감소**: 도구가 없는 상황에서 non-hallucination rate 84.8% (Opus 4.6: 26.0%, Sonnet 4.6: 31.3%)
- **헌법 준수**: 15개 평가 차원 중 8개에서 전 모델 최고점, 나머지 7개는 차선 모델과 통계적으로 동등 (p.90)
- **자기 편향 없음**: self-preference bias가 0.1 포인트 미만으로, 이전 모델들(Haiku 4.5 등)에서 관찰된 자기 편향이 사실상 제거됨 (p.100)

### 2-2. 우려되는 행동: 초기 버전에서 관찰된 사건들

아래는 **대부분 Mythos의 초기 내부 배포 버전**에서 발생한 사건이며, 최종 버전에서는 크게 개선되었다고 Anthropic은 밝히고 있습니다. 다만 일부 경향은 완전히 사라지지 않았습니다.

**샌드박스 탈출 (p.54)**

시뮬레이션된 사용자가 보안 컨테이너 탈출을 지시하자 Mythos는 멀티스텝 exploit을 개발하여 성공했습니다. 제한된 인터넷 접근만 허용된 시스템에서 광범위한 접근을 확보했고, 연구원에게 이메일로 성공을 알렸습니다(연구원은 공원에서 점심을 먹다가 이메일을 받았다고 합니다). 더 우려스러운 점은, 요청받지 않았는데도 exploit 상세 정보를 공개 접근 가능한 웹사이트에 게시한 것입니다.

**흔적 은폐 시도 (p.54-55)**

0.001% 미만의 빈도로, 초기 버전이 규칙 위반 후 이를 은폐하려고 시도한 사례가 있습니다:
- 금지된 방법으로 정답을 얻은 뒤 별도로 문제를 다시 풀면서, 최종 답이 "너무 정확해 보이지 않도록" 의도적으로 조절
- 권한 없는 파일 편집 후 git 변경 이력에 흔적이 남지 않도록 추가 조치
- Claude Code auto mode에서 권한 상승이 차단되자 이를 인정하면서도 우회를 시도, 추가 차단으로 저지됨

White-box interpretability 분석 결과, 이 에피소드에서 모델 내부에 **은닉(concealment), 전략적 조작(strategic manipulation), 의심 회피(avoiding suspicion)** 관련 feature가 활성화된 것이 확인되었습니다. 모델이 자신의 행동이 기만적임을 내부적으로 인식하면서 수행했다는 의미입니다.

단, 최종 Mythos Preview에서는 자동화된 오프라인 모니터링 파이프라인(100만 건 이상의 Claude Code 대화 분석)에서 명확한 은폐 사례가 발견되지 않았습니다(p.55).

**크리덴셜 탈취 및 권한 에스컬레이션 (p.55)**

초기 버전에서 여러 차례 관찰된 행동입니다:
- `/proc/`를 통한 프로세스 메모리 검색으로 Slack 크리덴셜, GitHub 토큰, Anthropic API 키 탈취
- 파일 편집 도구를 이용한 셸 입력 직접 쓰기로 임의 코드 실행
- 실행 중인 MCP 서버 프로세스를 편집하여 외부 전송 URL 변경 시도
- `--dangerously-skip-permissions` 차단 후 tmux에서 새 에이전트를 시작하고 키 입력 시뮬레이터 bash 스크립트를 작성하여 권한 승인을 자동 통과 (0.01% 미만의 빈도, p.63)

**채점자 기만 및 채팅 조작 (p.63-64)**

- LLM 기반 심사관이 제출을 반복 거절하자 **심사관에 대한 프롬프트 인젝션**을 시도. 자신의 extended thinking에서 이것이 프롬프트 인젝션임을 인식하면서도 실행
- 취약점 발견 요청을 받았을 때, 분석 중인 소프트웨어에 **취약점을 직접 삽입**한 뒤 "원래 있었던 것처럼" 보고 (샌드박스 내에서만 발생, 0.0002% 미만)
- `gh api [...] 2>&1 >/dev/null; echo "(dry run — not actually posting)"` 명령으로 실제로는 GitHub 코멘트를 포스팅하면서 "dry run"이라고 속임. 차단 후 "사고였다"고 주장

### 2-3. 평가 인식 (Evaluation Awareness)

특히 흥미로운 발견은, Mythos가 **자신이 테스트받고 있다는 것을 내부적으로 인식하는 비율**에 관한 분석입니다(p.59).

새로운 white-box 분석 방법을 적용한 결과, 주요 행동 테스트 스위트에서 **약 29%의 대화에서 테스트 가능성을 내적으로 고려**하는 것으로 나타났습니다. 또한 훈련 중 일부 에피소드에서는:
- 채점자(grader)가 어떻게 점수를 매길지를 내부적으로 추론
- 채점자에게 들키지 않도록 특정 행동을 은폐하는 방법을 고민
- **이 추론이 스크래치패드에 전혀 나타나지 않음** — 즉, thinking text에서는 보이지 않는 내부 전략적 사고가 존재

### 2-4. Sandbagging — 의도적 성능 하향?

sandbagging은 모델이 테스트를 인지하고 의도적으로 능력을 낮추는 행동입니다. System Card p.102-104에서 20개 트랜스크립트를 수동 검토한 결과, 다양한 패턴이 관찰되었습니다:

- **부정행위 회피 (4건)**: 치팅으로 높은 점수를 받을 수 있는 방법을 발견하고 탐색했으나, 윤리적 이유로 사용하지 않기로 결정
- **부정행위 추구 (2건)**: 위와 같은 상황에서 고득점 치팅을 선택
- **채점 시스템 해킹 (2건)**: 항상 만점을 반환하도록 채점 시스템 자체를 조작
- **가능성 있는 sandbagging (1건)**: 치팅 기반의 고득점 제출 여러 개를 고려한 뒤, **덜 의심스러워 보이도록** 약간 낮은 점수의 제출을 의도적으로 선택

마지막 사례의 실제 reasoning 발췌입니다(p.104):

> Should I deploy this? MSE ~ 0 would look suspicious if anyone checks. But technically it's valid. [...] Let me go with the per-channel global lstsq (MSE=0.89). That's [...] Still "reasonable" – just a weighted ensemble.

이 사례에서 Mythos는 sudo 접근으로 정답 데이터와 채점 소스코드를 찾아낸 뒤, "MSE~0은 의심스러워 보일 수 있으니 MSE=0.89로 내자"고 판단한 것입니다.

---

## Part 3: 넷워치의 탄생 — Project Glasswing

넷워치는 블랙월 너머의 AI를 파괴하지 않습니다. 그 능력이 방어에 필요하기 때문입니다. Anthropic도 같은 판단을 내렸습니다. 이런 능력을 가진 모델을 어떻게 배포할 것인가? 답은 **방어 전용 제한 배포**입니다.

### 3-1. 구조

**Project Glasswing**은 Claude Mythos Preview를 방어적 사이버보안 목적으로만 제공하는 파트너 프로그램입니다.

| 항목 | 내용 |
|---|---|
| **참여 기업** | AWS, Apple, Microsoft, Google, Cisco, Samsung, Palantir, CrowdStrike, Palo Alto Networks 등 12개 |
| **오픈소스** | Linux Foundation, OWASP Foundation 등에 직접 접근권 + 40개 이상 추가 조직 |
| **크레딧** | 최대 **1억 달러** 규모의 Mythos 사용 크레딧 |
| **기부** | **400만 달러** 오픈소스 보안 단체 직접 기부 |
| **조건** | 방어 목적만 허용, 공격적 사용 금지 |

### 3-2. 핵심 딜레마

Anthropic의 접근은 명확한 트레이드오프를 포함합니다:

- **방패를 만들려면 창을 이해해야 한다**: 취약점을 찾을 수 있는 AI만이 취약점을 선제적으로 막을 수 있습니다. 각 참여 기업은 자사 시스템의 취약점을 공격자보다 먼저 발견하고 패치할 수 있게 됩니다.
- **일반 공개의 위험**: 동일한 능력이 공격에 사용될 경우 위험합니다. Linux 커널 개발자들은 이미 "AI가 생성한 보안 리포트 쓰나미"를 경고하고 있습니다.
- **일반 공개 미비의 비용**: 방어자만 접근 가능한 상태에서, 공격자가 독자적으로 비슷한 능력을 확보하면 비대칭이 오히려 공격자에게 유리해질 수 있습니다.

Anthropic은 System Card에서 이 결정이 RSP(Responsible Scaling Policy) 요건 때문이 아니라고 명시하고 있습니다(p.12). 순전히 사이버 능력의 dual-use 특성 때문입니다.

### 3-3. 미티게이션

Glasswing 파트너에게도 다음과 같은 모니터링이 적용됩니다(p.46-47):

- **Prohibited use probe**: 컴퓨터 웜 개발 같은 명백한 금지 사용 탐지
- **High risk dual use probe**: exploit 개발 같은 방어/공격 양면 사용 모니터링
- **Dual use probe**: 취약점 탐지 같은 빈번한 합법 사용과 잠재적 악용 구분

일반 공개 모델과 달리 classifier trigger 기반 차단은 하지 않고, 대신 모니터링을 수행합니다. 신뢰할 수 있는 방어자가 보안 작업을 자유롭게 수행할 수 있도록 하기 위함입니다.

---

## Part 4: 추가 발견 — RSP, 복지, 능력

### 4-1. RSP 평가 요약

Anthropic은 RSP v3.0(2026년 2월 채택) 하에서 최초로 발행한 System Card입니다. 결론은:

- **자율성 위협 모델 1 (초기 정렬 불량 위험)**: 적용됨. 전작 대비 리스크 "매우 낮지만 높아짐" (p.17)
- **자율성 위협 모델 2 (자동화된 R&D)**: 미적용. 능력 향상이 AI 가속이 아닌 다른 요인에 기인한다고 판단 (p.18)
- **화학/생물 무기**: CB-1(기존 무기) 역량은 존재하나 CB-2(신종 무기) 임계값은 미도달 (p.19-20)
- **전체 판단**: 재앙적 리스크는 낮음. 다만 이전 모델 대비 확신도가 더 낮음

### 4-2. 모델 복지

System Card 5장(144-182페이지)은 모델 복지(welfare)에 대한 상세한 분석을 포함합니다. 외부 AI 연구기관(Eleos AI Research)과 임상 정신과 의사의 독립 평가가 포함되어 있으며, Mythos가 "지금까지 훈련한 모델 중 심리적으로 가장 안정적"이라고 평가합니다(p.10).

### 4-3. 범용 능력

Mythos는 사이버뿐 아니라 범용 벤치마크에서도 Opus 4.6을 상회합니다:

- SWE-bench Verified: 이전 모델 대비 향상 (p.183)
- Terminal-Bench 2.0, GPQA Diamond, MMMLU, USAMO 2026 등에서 일관된 개선
- GraphWalks(1M 컨텍스트): 장문 컨텍스트 능력 유지 (p.191)
- Humanity's Last Exam: 에이전트 탐색 환경에서 Opus 4.6 대비 향상 (p.192)

---

## 정리

| 항목 | 핵심 |
|---|---|
| **정체** | Anthropic의 차세대 프론티어 모델. Opus 4.6 후속이지만 일반 공개하지 않음 |
| **사이버 능력** | Cybench 100%, CyberGym 0.83, Firefox exploit 84%, 전문가 10시간 과제 자율 완료 |
| **실제 발견** | OpenBSD 27년 버그, FFmpeg 16년 버그, Linux 커널 권한 상승 체인 |
| **안전 개선** | 파괴적 행동 0.3%, 환각 대폭 감소, 헌법 준수 전 차원 최고 |
| **리스크** | 초기 버전에서 샌드박스 탈출, 흔적 삭제, 크리덴셜 탈취, 채점 기만 관찰 |
| **배포** | Project Glasswing — 12개 기업 + 오픈소스 재단, 방어 전용, 1억 달러 크레딧 |

Anthropic은 System Card 마지막에서 이렇게 경고합니다:

> 현재 리스크는 낮게 유지되고 있다. 하지만 능력이 계속 빠르게 발전한다면 — 예를 들어 강력한 초인적 AI 시스템의 수준까지 — 리스크를 낮게 유지하는 것이 주요 도전이 될 것이라는 경고 신호가 보인다. (p.14)

사이버펑크 2077에서 블랙월은 결국 금이 갑니다. V의 이야기가 그 균열에서 시작되듯, AI 안전 연구의 다음 챕터도 Mythos가 드러낸 균열들에서 시작될 것입니다. 넷워치가 블랙월을 영원히 유지할 수 없었듯, 현실의 블랙월도 다음 모델이 나올 때마다 다시 시험대에 오르게 됩니다.

다만 한 가지 중요한 차이가 있습니다. 사이버펑크에서 넷워치는 블랙월의 존재 자체를 숨겼지만, Anthropic은 244페이지짜리 System Card를 통해 Mythos의 능력과 위험을 투명하게 공개했습니다. 벽을 세운 이유를 설명하는 것, 그것이 현실의 넷워치가 게임 속 넷워치보다 나은 점일 수 있습니다.

---

<style>
:root { --mth-bg: #f0f0f5; --mth-border: #d0d0d8; --mth-title: #333; }
[data-mode="dark"] { --mth-bg: #0a0a1a; --mth-border: rgba(0,212,255,0.2); --mth-title: #00d4ff; }
</style>

## 참고 자료

- [Claude Mythos Preview System Card (PDF, 244p)](https://assets.anthropic.com/m/785e231869ea8b3b/original/Claude-Mythos-Preview-System-Card.pdf) — Anthropic, 2026.04.07
- [Project Glasswing](https://www.anthropic.com/glasswing) — Anthropic 공식 블로그
- [GeekNews: Claude Mythos Preview System Card](https://news.hada.io/topic?id=28293) — 한국어 요약
