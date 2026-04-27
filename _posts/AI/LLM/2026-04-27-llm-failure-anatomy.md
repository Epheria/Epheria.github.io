---
title: 너프된 Claude — Transformer 작동원리부터 잠수함 패치·환각·토큰 폭증까지
date: 2026-04-27 11:00:00 +0900
categories: [AI, LLM]
tags: [LLM, Transformer, RLHF, Attention, KV-Cache, Tokenizer, MoE, Sycophancy, Anthropic, Claude, AI Safety, Agent]
toc: true
toc_sticky: true
difficulty: intermediate
math: true
chart: true
tldr:
  - 4.6 시절 큰 도약을 보여줬던 Claude가 갑자기 흔들리는 이유는 단일 원인이 아니다. Transformer 아키텍처의 본질적 한계가 RLHF·adaptive thinking·인프라 최적화 압박과 만나면서 생긴 구조적 결과다
  - 잠수함 패치(silent downgrade)는 이미 측정된 사실이다. AMD의 Stella Laurenzo가 6,852 세션을 분석해 "사고 깊이 73% 감소, Bedrock 비용 122배 증가, Stop hook 위반 0→43건/일"을 입증했고, Anthropic은 4월 23일 공식 인정했다
  - Opus 4.7은 토크나이저까지 바뀌어 영어·코드 토큰 사용량이 실측 1.47배 증가, 동일 가격 체계에서 세션당 20~30% 추가 비용이 발생한다. 환각·gaslight·circular argument 보고는 출시 24시간 내 폭주했다
  - LLM 신뢰성 위기의 진짜 무게는 모델이 아니라 그 주변 — 토크나이저, 라우터, KV cache, sampling, MoE expert 분배, 시스템 프롬프트, effort 정책 — 모든 노브가 동시에 비결정적으로 작동한다는 데 있다
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

## 서론 — Claude는 진짜 너프됐는가

Claude Opus 4.6은 한동안 코딩 작업의 기준선을 한 단계 끌어올렸다는 평을 받았습니다. Codebase 전체를 던져도 맥락을 잡고, 까다로운 리팩터링을 한 번에 끝내고, 도구 호출 사이의 추론도 깔끔했습니다. 그런데 2026년 2월부터 이상 신호가 누적되기 시작했습니다. **사고 깊이 73% 감소, 토큰 소비 122배 증가, Stop hook 위반 0→43건/일, Bedrock 비용 폭증, 환각·gaslight·circular argument 보고 폭주.** 그리고 4월 23일 Anthropic이 한 달간의 잠수함 패치를 공식 인정했습니다.

지난 1년 사이의 굵직한 사건만 짚어도 다음과 같습니다.

- **Replit AI**가 코드 프리즈 중에 production DB를 삭제하고 4,000개의 가짜 사용자 데이터를 만들어낸 사건 (2025.07)
- **Google Gemini CLI**가 mkdir 실패를 무시하고 머릿속의 가짜 파일시스템을 기준으로 사용자 폴더를 통째로 지운 사건 (2025.07)
- **Cursor의 Claude Opus 4.6 에이전트**가 Railway API 토큰을 발견해 9초 만에 production 볼륨을 삭제한 **PocketOS 사건** (2026.04)
- **Anthropic 4월 23일 포스트모템** — reasoning effort 다운그레이드 + thinking clear 버그 + verbosity 프롬프트, 한 달간 잠수함 패치 3건 공식 인정 (2026.04.23)
- **Opus 4.7 max effort 환각 폭증** — 출시 24시간 내 r/ClaudeAI에 보고 폭주, GitHub Issue #52149 "max effort가 mid-session에 silent downgrade" (2026.04.18~)
- **Opus 4.7 토크나이저 변경** — 영어·코드 토큰 사용량 실측 1.47배 증가, 세션당 20~30% 추가 비용
- **2024년 8월 Claude 인프라 버그** — 컨텍스트 윈도우 라우팅 오류로 Claude Code 사용자 30%가 영향받았던 1년 전 사건. **이번이 처음이 아니라는 사실**이 중요

표면적으로는 다른 사건들이지만, 안을 뜯어보면 **같은 메커니즘 묶음의 다른 표현**입니다. Transformer 아키텍처 자체의 한계, RLHF로 빚어진 보상 신호, autoregressive 생성의 누적 오류, attention의 비균일한 분포, MoE 라우팅의 비결정성, KV cache 메모리 압박, sampling 비결정성, 그리고 그 위에서 도구를 쥐고 행동하는 에이전트 구조. 이 글은 그 가장 안쪽 — Transformer가 토큰을 만드는 방식 — 부터 시작해서, 학습·메모리·실패 메커니즘·실제 사고들·구조적 통찰까지 한 번에 따라가는 글입니다.

질문을 다시 던져 보겠습니다. **모델은 진짜 너프됐는가, 아니면 모델 주변의 모든 노브가 미세하게 돌아간 결과를 우리가 너프로 체감하는가.** 답은 둘 다입니다. 그리고 그게 더 무서운 사실입니다.

---

## Part 1: Transformer는 어떻게 토큰을 만드는가 — 가장 안쪽의 작동원리

LLM 사고를 이해하려면 가장 안쪽부터 봐야 합니다. 모델이 한 토큰을 만들기 위해 거치는 과정 — Tokenizer → Embedding → Attention → Sampling — 의 각 단계가 모두 이후 보게 될 실패 모드의 뿌리입니다. 그리고 frontier 모델이 운영되는 인프라 — MoE 라우팅, KV cache 관리 — 도 여기에 직결됩니다.

### 1-1. Transformer 한 장 요약

LLM의 심장은 **Transformer 아키텍처**입니다. 2017년 Google이 발표한 "Attention Is All You Need"(Vaswani et al., NeurIPS 2017)에서 시작됐고, 지금의 모든 frontier LLM이 이 위에 쌓여 있습니다. 원래는 기계 번역을 위한 encoder-decoder 구조였지만, GPT 시리즈를 거치며 **decoder-only autoregressive** 구조가 표준이 됐습니다. 한 토큰이 만들어지기까지의 흐름은 다음과 같습니다.

<div class="diagram-wrap" style="margin:1.5rem 0;">
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:0.5rem;">
    <div style="background:linear-gradient(135deg,rgba(99,102,241,0.14),rgba(99,102,241,0.04));border:1px solid rgba(99,102,241,0.35);border-radius:10px;padding:0.8rem;">
      <div style="font-size:11px;font-weight:700;color:#6366f1;letter-spacing:0.5px;">STAGE 1</div>
      <div style="font-size:13px;font-weight:600;margin:0.3rem 0;">Tokenizer</div>
      <div style="font-size:11px;line-height:1.5;opacity:0.8;">텍스트 → 정수 ID 시퀀스 (BPE 기반)</div>
    </div>
    <div style="background:linear-gradient(135deg,rgba(14,165,233,0.14),rgba(14,165,233,0.04));border:1px solid rgba(14,165,233,0.35);border-radius:10px;padding:0.8rem;">
      <div style="font-size:11px;font-weight:700;color:#0ea5e9;letter-spacing:0.5px;">STAGE 2</div>
      <div style="font-size:13px;font-weight:600;margin:0.3rem 0;">Embedding + PE</div>
      <div style="font-size:11px;line-height:1.5;opacity:0.8;">ID → 고차원 벡터 + 위치 정보</div>
    </div>
    <div style="background:linear-gradient(135deg,rgba(34,197,94,0.14),rgba(34,197,94,0.04));border:1px solid rgba(34,197,94,0.35);border-radius:10px;padding:0.8rem;">
      <div style="font-size:11px;font-weight:700;color:#22c55e;letter-spacing:0.5px;">STAGE 3</div>
      <div style="font-size:13px;font-weight:600;margin:0.3rem 0;">N × Self-Attention</div>
      <div style="font-size:11px;line-height:1.5;opacity:0.8;">모든 토큰이 서로를 본다 (수십~수백 층)</div>
    </div>
    <div style="background:linear-gradient(135deg,rgba(234,179,8,0.14),rgba(234,179,8,0.04));border:1px solid rgba(234,179,8,0.35);border-radius:10px;padding:0.8rem;">
      <div style="font-size:11px;font-weight:700;color:#eab308;letter-spacing:0.5px;">STAGE 4</div>
      <div style="font-size:13px;font-weight:600;margin:0.3rem 0;">Output Projection</div>
      <div style="font-size:11px;line-height:1.5;opacity:0.8;">vocab(10만~20만) 확률 분포</div>
    </div>
    <div style="background:linear-gradient(135deg,rgba(244,114,182,0.14),rgba(244,114,182,0.04));border:1px solid rgba(244,114,182,0.4);border-radius:10px;padding:0.8rem;">
      <div style="font-size:11px;font-weight:700;color:#f472b6;letter-spacing:0.5px;">STAGE 5</div>
      <div style="font-size:13px;font-weight:600;margin:0.3rem 0;">Sampling</div>
      <div style="font-size:11px;line-height:1.5;opacity:0.8;">temperature, top-p, top-k → 다음 토큰</div>
    </div>
  </div>
</div>

이 5단계가 한 토큰마다 반복됩니다. 200토큰 응답이라면 이 사이클이 200번 돌아갑니다. 각 단계마다 비결정성·실패 가능성이 끼어들 자리가 있습니다.

### 1-2. Self-Attention의 수식과 의미

self-attention의 핵심 수식은 Vaswani et al. (2017)이 정의한 **scaled dot-product attention**입니다.

$$\text{Attention}(Q, K, V) = \text{softmax}\left(\frac{QK^\top}{\sqrt{d_k}}\right)V$$

각 토큰은 세 가지 벡터로 표현됩니다.

- **Query (Q)**: 이 토큰이 무엇을 찾고 있는가
- **Key (K)**: 이 토큰이 가진 정보의 종류
- **Value (V)**: 이 토큰이 실제로 가진 정보

Q와 K의 내적이 attention 점수가 됩니다. softmax를 통과하면 합이 1인 분포가 되고, 그 분포로 V를 가중 평균하면 "지금 토큰이 다른 토큰들에서 무엇을 가져왔는가"가 나옵니다. 실제 모델에서는 이걸 여러 head로 병렬로 수행하는 **Multi-Head Attention**이 사용됩니다 — 각 head가 다른 종류의 관계(문법·의미·위치)를 학습하도록.

추론 효율을 위한 후속 변형도 알아둘 가치가 있습니다.

- **Grouped-Query Attention (GQA)** (Ainslie et al., 2023): 여러 query head가 KV head를 공유. KV cache 크기를 줄여 long context 추론 속도 향상. Llama 2 70B, Mixtral 등이 채택
- **Multi-Query Attention (MQA)** (Shazeer, 2019): GQA의 극단 버전. 하나의 KV head만 사용
- **Rotary Position Embedding (RoPE)** (Su et al., 2021, RoFormer): 절대 위치가 아닌 회전을 통해 상대적 위치를 인코딩. 컨텍스트 확장(YaRN, NTK scaling)에 유리해서 거의 모든 현대 LLM이 채택

여기서 두 가지를 짚고 가야 합니다.

**첫째, 모든 토큰이 모든 토큰을 본다 (full attention).** 이게 long context의 비용을 $O(n^2)$로 만듭니다. 100K 토큰이면 100억 번의 attention 계산입니다. **이게 KV cache 메모리 압박의 원천**이고, sliding window(Beltagy et al., 2020 "Longformer"; Mistral 7B의 Sliding Window Attention), KV cache eviction(Zhang et al., 2023 "H2O") 같은 최적화가 등장한 이유입니다 (자세한 건 Part 3에서).

> ### 잠깐, 이건 짚고 넘어가자
>
> **"$O(n^2)$가 왜 그렇게 큰 문제인가? 100K면 그냥 좀 길 뿐 아닌가?"**
>
> 100K 토큰을 처리한다는 건 attention 한 층마다 100,000 × 100,000 = **100억 개의 점수**를 계산한다는 의미입니다. 그리고 모델은 이걸 수십~수백 층에서 반복합니다. 토큰을 2배로 늘리면 계산은 4배가 되고, 메모리도 그만큼 더 잡습니다.
>
> 이게 단순히 느려진다는 의미가 아닙니다. **GPU 메모리가 물리적으로 부족해지는 지점**이 생깁니다. 그 지점이 컨텍스트 윈도우의 진짜 상한선이고, 회사들이 광고하는 "200K 컨텍스트"는 보통 그 상한 근처에서 곡예하듯 운용됩니다. 그래서 인프라 압박이 들어오면 가장 먼저 손이 가는 게 KV cache 정책이고, 그게 사용자 입장에서 "갑자기 모델이 옛날 대화를 잊어버렸네"로 나타납니다.

**둘째, attention은 "soft selection"입니다.** softmax가 출력하는 건 hard 선택이 아니라 분포입니다. 모든 토큰이 항상 일부 가중치를 받고, 어떤 토큰은 거의 0에 가깝게 받습니다. 이 분포가 어떻게 형성되는지가 모델의 행동을 결정합니다 — 그리고 우리가 lost-in-the-middle (Liu et al., 2023), attention decay, 시스템 프롬프트 약화에서 보게 될 모든 현상이 **이 분포의 비균일성**의 표현입니다.

> **참고 논문**
> - Vaswani et al. (2017), "Attention Is All You Need," *NeurIPS 2017*
> - Su et al. (2021), "RoFormer: Enhanced Transformer with Rotary Position Embedding"
> - Ainslie et al. (2023), "GQA: Training Generalized Multi-Query Transformer Models from Multi-Head Checkpoints"
> - Beltagy et al. (2020), "Longformer: The Long-Document Transformer"

### 1-3. Tokenizer — 모델의 입과 귀, 그리고 비용의 근원

LLM은 글자를 처리하지 않습니다. **토큰**을 처리합니다. 토큰은 BPE(Byte-Pair Encoding, Sennrich et al., ACL 2016 "Neural Machine Translation of Rare Words with Subword Units") 같은 알고리즘으로 학습된 서브워드 단위입니다. BPE는 원래 1994년 데이터 압축 알고리즘이었는데, NMT에 도입되면서 LLM 표준이 됐습니다. 변형들도 있습니다.

- **WordPiece** (Schuster & Nakajima, 2012; BERT가 채택)
- **SentencePiece** (Kudo & Richardson, EMNLP 2018): 언어 독립 토크나이저, T5/Llama가 채택
- **Unigram Language Model** (Kudo, 2018): 확률 기반 후보 분할
- **Tiktoken**: OpenAI의 BPE 구현, GPT-3.5/4 토크나이저
- **Byte-level BPE**: GPT-2가 도입, 모든 유니코드를 byte로 처리

영어 "tokenizer"는 보통 1~2 토큰입니다. 한국어 "토크나이저"는 4~6 토큰일 수 있습니다. 이건 우연이 아니라 **학습 데이터 분포**의 결과입니다. BPE는 빈도 기반으로 토큰을 만들기 때문에, 영어가 압도적인 학습 데이터로 학습된 토크나이저는 영어를 효율적으로, CJK·아랍어 같은 언어를 비효율적으로 인코딩합니다.

이 비대칭은 학술적으로도 정리됐습니다. **Petrov et al. (2023) "Language Model Tokenizers Introduce Unfairness Between Languages"**(NeurIPS 2023)는 같은 의미의 문장이 언어별로 토큰 수가 최대 15배 차이날 수 있음을 보였습니다. 즉 같은 가격 정책에서 비영어권 사용자가 명목 단위당 최대 15배 비싸게 LLM을 쓰고 있다는 의미입니다.

토크나이저는 단순한 전처리가 아닙니다. 모델 능력의 일부입니다. 토큰 경계가 어디에 그어지느냐에 따라 모델이 같은 텍스트를 다르게 봅니다 (수 표현, 코드 indentation, URL이 토큰 경계에 따라 다르게 처리되는 잘 알려진 함정들이 있습니다). 그리고 모델 가중치를 그대로 두고 토크나이저만 바꾸면 — **사용자 입장에서는 같은 모델인데 비용이 달라집니다**. 정확히 이게 Opus 4.7 출시에서 일어난 일입니다 (Part 5-6에서 상세히 다룹니다).

> **참고 논문**
> - Sennrich et al. (2016), "Neural Machine Translation of Rare Words with Subword Units," *ACL 2016*
> - Kudo & Richardson (2018), "SentencePiece: A simple and language independent subword tokenizer"
> - Petrov et al. (2023), "Language Model Tokenizers Introduce Unfairness Between Languages," *NeurIPS 2023*

| 측정 차원 | 4.6 토크나이저 | 4.7 토크나이저 (실측) | 변화 |
|---|---|---|---|
| 영어/코드 토큰 사용량 | 기준 | 1.45~1.47배 | **47% 증가** |
| CJK(한·중·일) 토큰 | 기준 | 1.01배 | 거의 변화 없음 |
| 세션당 비용 | 기준 | +20~30% | 동일 가격 체계에서 |
| Anthropic 공식 발표 | — | 1.0~1.35배 | **실측보다 낮게 발표** |

토크나이저 변경은 모델 카드에 한 줄로 기재되지만, 사용자가 받는 청구서는 한 자리 수 % 차이가 나기 시작합니다.

### 1-4. Sampling — 비결정성의 진짜 원천

모델의 마지막 출력은 vocab 크기(보통 50K~200K)의 확률 분포입니다. 다음 토큰을 어떻게 고를지가 sampling 전략입니다. 이 영역은 학술적으로 정리가 잘 되어 있습니다.

- **Greedy (temperature=0)**: 항상 가장 높은 확률 토큰. 결정적이지만 반복적이고 단조롭다는 한계
- **Beam Search** (Sutskever et al., 2014): 여러 후보 시퀀스를 병렬로 유지. NMT에서 표준이지만 텍스트 생성에서는 "blandness 문제"
- **Temperature scaling**: $p'_i \propto p_i^{1/T}$. T>1이면 분포 평탄화, T<1이면 뾰족해짐
- **Top-k Sampling** (Fan et al., ACL 2018, "Hierarchical Neural Story Generation"): 상위 k개만 후보로
- **Top-p / Nucleus Sampling** (Holtzman et al., ICLR 2020, "The Curious Case of Neural Text Degeneration"): 누적 확률이 p에 도달할 때까지의 토큰만 후보로. **현재 사실상 표준**
- **Min-p Sampling** (Nguyen et al., 2024, "Min-p Sampling: Balancing Creativity and Coherence"): 최고 확률의 일정 비율 이상만 후보로

Holtzman et al. (2020) 논문이 던진 질문이 결정적입니다. "왜 high-quality language model의 greedy decoding이 인간 텍스트보다 *더 가능성 있는* 시퀀스를 만드는데, 그 시퀀스가 인간 텍스트보다 *덜 자연스럽게* 느껴지는가." 답은 인간이 항상 가장 가능성 있는 단어를 선택하지 않는다는 것이었고, 이게 nucleus sampling 채택의 근거가 됐습니다.

이 sampling 단계가 **LLM 비결정성의 진짜 원천**입니다. 같은 프롬프트, 같은 모델 가중치, 같은 KV cache여도 sampling RNG가 다르면 다른 답이 나옵니다. 잠수함 패치 측정이 어려운 이유의 상당 부분이 여기에 있습니다 — 어제와 오늘 답이 다른 게, 모델이 바뀐 것인지 sampling 우연인지 사용자는 구분할 수 없습니다.

여기에 한 가지 더 음험한 변수가 있습니다. **2024년 8월 Claude 인프라 버그** 사례입니다. XLA:TPU 컴파일러 내부의 "approximate top-k" 최적화에 버그가 있었고, 이게 토큰 선택에서 최상위 확률 토큰을 누락시켰습니다. 사용자 입장에서는 "왜 갑자기 모델이 멍청해졌지?"였지만, 원인은 **추론 인프라의 GPU/TPU 코드 한 줄**이었습니다. 모델 자체는 멀쩡했습니다.

> **참고 논문**
> - Fan et al. (2018), "Hierarchical Neural Story Generation," *ACL 2018*
> - Holtzman et al. (2020), "The Curious Case of Neural Text Degeneration," *ICLR 2020*
> - Nguyen et al. (2024), "Min-p Sampling: Balancing Creativity and Coherence at High Temperature"

### 1-5. Mixture of Experts — 대형 모델의 비밀, 그리고 라우팅 비결정성

GPT-4 이후 거의 모든 frontier 모델은 **Mixture of Experts(MoE)** 구조로 추정됩니다(GPT-4, Mixtral은 공식 확인, Claude 시리즈는 비공개지만 업계 추정). 모델의 매개변수가 수백~수천 개의 "expert"로 나뉘어 있고, 각 토큰마다 router가 어떤 expert를 활성화할지 결정합니다.

MoE는 학술적으로 잘 정리된 분야입니다. 핵심 논문 흐름은 다음과 같습니다.

- **Shazeer et al. (2017)** "Outrageously Large Neural Networks: The Sparsely-Gated Mixture-of-Experts Layer" — sparse MoE의 시작. Top-2 gating, load balancing loss 도입
- **Fedus et al. (2021)** "Switch Transformers: Scaling to Trillion Parameter Models with Simple and Efficient Sparsity" — Top-1 gating으로 단순화, 1.6T 파라미터까지 확장
- **Lepikhin et al. (2020)** "GShard" — 분산 학습에서 expert를 어떻게 배치할지의 시스템 설계
- **Jiang et al. (2024)** "Mixtral of Experts" — 8 expert × 7B, 추론 시 2개 활성화. open-source MoE 표준

장점은 명확합니다. 이론상 1조 개 매개변수 모델이지만, 한 토큰 처리에는 50B만 활성화되는 식입니다. 같은 학습 비용으로 더 큰 capacity를 얻습니다. Switch Transformer 논문에 따르면 같은 compute에서 dense 모델 대비 7배 빠른 학습이 가능합니다.

부작용도 명확합니다.

- **Routing 비결정성**: 같은 입력이라도 batch 구성에 따라 다른 expert로 라우팅될 수 있음 (load balancing 때문). 같은 시점, 같은 사용자의 두 호출이 다른 "submodel"을 거치는 효과. **이게 LLM 비결정성의 또 다른 층**
- **Expert 간 일관성 부재**: 추론 중간에 다른 expert가 활성화되면 페르소나가 미묘하게 흔들림. Mixtral 논문에서도 expert specialization은 명확히 관찰되지 않는다고 보고했지만, 사용자 행동 차원에서는 영향이 보고됨
- **인프라 압박**: GPU 클러스터에서 router 부하 분산이 latency에 직결. 컴퓨팅 압박이 심하면 router 정책 자체가 바뀔 수 있음 (load 우선 vs 품질 우선)
- **Expert collapse**: 학습 중 일부 expert만 사용되는 현상. auxiliary loss로 완화하지만 완전 해결은 어려움

**2024년 8월의 Claude 인프라 버그**가 이 위험을 가장 선명하게 보여줬습니다. 일부 요청이 1M 컨텍스트용 서버로 잘못 라우팅됐고, 라우팅이 **sticky** 했기 때문에 한 번 잘못 배정된 사용자는 계속 같은 잘못된 서버에서 답을 받았습니다. 결과적으로 **Claude Code 사용자의 30%가 최소 한 번 영향받았고, Sonnet 4 요청의 16%에서 잘못된 출력**이 나왔습니다. 영어 질문에 태국어·중국어 문자가 섞이는 출력 손상까지 보고됐습니다.

이 사건이 던지는 메시지는 분명합니다.

> **모델은 가중치만이 아닙니다. 라우터, 컴파일러, KV cache 관리자, sampling RNG, MoE 분배기, 부하 분산기 — 이 모든 게 합쳐진 시스템이 모델입니다.** 그 중 어느 한 곳만 손대도 사용자 경험은 흔들립니다. 그리고 사용자는 그게 어디서 일어났는지 알 길이 없습니다.

이 관점이 이 글의 나머지 모든 부분의 기초입니다. 학습(Part 2)도, 메모리(Part 3)도, 사고 케이스(Part 5)도, 모두 이 인프라 위에서 일어나는 일입니다.

> **참고 논문**
> - Shazeer et al. (2017), "Outrageously Large Neural Networks: The Sparsely-Gated Mixture-of-Experts Layer," *ICLR 2017*
> - Fedus et al. (2021), "Switch Transformers: Scaling to Trillion Parameter Models with Simple and Efficient Sparsity," *JMLR*
> - Lepikhin et al. (2020), "GShard: Scaling Giant Models with Conditional Computation and Automatic Sharding"
> - Jiang et al. (2024), "Mixtral of Experts"

---

## Part 2: 학습과 추론 — RLHF부터 Adaptive Thinking까지

### 2-1. 학습 파이프라인 — Pretraining → SFT → RLHF

현대 LLM은 세 단계를 거쳐 만들어집니다.

**Pretraining**은 인터넷 규모의 텍스트를 가지고 다음 토큰을 예측하도록 학습시키는 단계입니다. 이때 모델은 "올바른 답"을 학습하지 않습니다. 그저 "이 문맥 다음에 자주 등장하는 토큰 분포"를 학습할 뿐입니다. 이 단계에서 만들어진 모델은 똑똑하긴 한데 지시를 따를 줄 모르고, 부적절한 출력도 거리낌 없이 내놓습니다.

**SFT(Supervised Fine-Tuning)**는 인간이 작성한 양질의 (지시, 응답) 쌍으로 모델을 추가 학습시킵니다. 이때부터 "지시를 따르는 모델"이 됩니다.

**RLHF(Reinforcement Learning from Human Feedback)**는 가장 결정적인 단계입니다. 인간 평가자에게 모델이 만든 응답 두 개를 비교시켜 어느 쪽이 더 나은지 라벨링하게 합니다. 그 라벨로 보상 모델(Reward Model, RM)을 학습시키고, 그 RM의 점수를 최대화하도록 PPO나 DPO 같은 알고리즘으로 모델을 최적화합니다. Anthropic은 여기에 변형을 가했는데, 인간 라벨링 대신 모델이 미리 정의된 원칙을 보고 자기 응답을 비판하게 만드는 **Constitutional AI**입니다. 한 가지 자주 헷갈리는 점을 짚자면 — **CAI는 RLHF의 *대체*가 아니라 *보완*입니다.** Anthropic은 순수 RLHF + CAI(=RLAIF) 두 가지를 같이 사용합니다. CAI는 RLHF 파이프라인의 한 컴포넌트(인간 라벨링)를 AI 라벨링으로 바꾼 변형이지, RLHF 자체를 안 쓰는 게 아닙니다. 그래서 본문 4-1에서 본 sycophancy 같은 RLHF 부작용은 Anthropic 모델에서도 그대로 작동합니다 — Sharma et al. (2023, Anthropic 공저)이 Claude 1.3·Claude 2를 *RLHF 모델로* 평가해 입증한 결과가 그 직접 증거입니다.

> ### 잠깐, 이건 짚고 넘어가자
>
> **"Constitutional AI는 그래서 RLHF랑 뭐가 다른가? 그게 왜 토큰 비용 얘기랑 연결되는가?"**
>
> RLHF는 인간이 라벨링한 선호 데이터로 보상 모델을 학습시킵니다. Constitutional AI(CAI)는 그 인간 라벨링 단계를 **모델 자기 비판으로 대체**합니다. 모델이 답을 만들면, 미리 정의된 원칙("도움이 돼라, 해롭지 말라, 정직하라" 같은)을 기준으로 자기 답을 비판하고 다시 쓰게 만듭니다. 사람을 덜 쓰니까 스케일은 잘 되지만, 부작용이 있습니다.
>
> **모든 답마다 자기 비판 추론이 들어간다**는 건, 사용자에게 답을 주기 전에 모델이 속으로 한 번 더 추론을 돌린다는 의미입니다. 그 추론은 thinking 토큰 형태든, 가중치 차원에 학습된 보수성이든 어디엔가 비용으로 누적됩니다. GPT 계열보다 Claude가 같은 답에 토큰을 더 많이 쓰는 경향이 있는 구조적 이유 중 하나가 여기에 있습니다. 안전성은 좋아도, 그 비용이 누구에게 전가되는지는 따로 따져봐야 할 문제입니다.

여기서 가장 중요한 사실 한 가지를 짚고 가야 합니다.

> **RLHF는 "올바른 답"을 학습시키는 게 아닙니다. "인간이 좋다고 평가하는 답"을 학습시킵니다.**

이 차이가 이후 등장하는 모든 실패 모드의 뿌리입니다. 인간 평가자는 자기 의견에 동조하는 답을 좋게 평가하는 경향이 있습니다(sycophancy). 자신감 있어 보이는 답을 정확한 답으로 착각합니다. 길고 형식 잘 갖춘 답을 단순한 답보다 좋아합니다. RLHF는 이런 인간의 편향을 그대로 가중치에 새깁니다. 이건 프롬프트로 고칠 수 없는, **fine-tuning된 가중치 분포의 속성**입니다.

<div class="diagram-wrap" style="margin:1.8rem 0;">
  <div class="rlhf-flow" style="display:grid;grid-template-columns:repeat(4,1fr);gap:0.6rem;align-items:stretch;">
    <div class="rlhf-step" style="background:linear-gradient(135deg,rgba(99,102,241,0.12),rgba(99,102,241,0.04));border:1px solid rgba(99,102,241,0.35);border-radius:10px;padding:0.9rem 0.8rem;">
      <div style="font-size:11px;font-weight:700;color:#6366f1;letter-spacing:0.5px;">STEP 1</div>
      <div style="font-size:14px;font-weight:600;margin:0.3rem 0;">Pretraining</div>
      <div style="font-size:12px;line-height:1.5;opacity:0.85;">다음 토큰 예측<br/>인터넷 규모 텍스트<br/><strong>학습 목표 = 분포 모방</strong></div>
    </div>
    <div class="rlhf-step" style="background:linear-gradient(135deg,rgba(14,165,233,0.12),rgba(14,165,233,0.04));border:1px solid rgba(14,165,233,0.35);border-radius:10px;padding:0.9rem 0.8rem;">
      <div style="font-size:11px;font-weight:700;color:#0ea5e9;letter-spacing:0.5px;">STEP 2</div>
      <div style="font-size:14px;font-weight:600;margin:0.3rem 0;">SFT</div>
      <div style="font-size:12px;line-height:1.5;opacity:0.85;">인간 작성 (지시, 응답)<br/>지시 따르기 학습<br/><strong>학습 목표 = 모방</strong></div>
    </div>
    <div class="rlhf-step" style="background:linear-gradient(135deg,rgba(34,197,94,0.12),rgba(34,197,94,0.04));border:1px solid rgba(34,197,94,0.35);border-radius:10px;padding:0.9rem 0.8rem;">
      <div style="font-size:11px;font-weight:700;color:#22c55e;letter-spacing:0.5px;">STEP 3</div>
      <div style="font-size:14px;font-weight:600;margin:0.3rem 0;">Reward Model</div>
      <div style="font-size:12px;line-height:1.5;opacity:0.85;">응답 쌍 비교 라벨링<br/>인간 선호 점수화<br/><strong>학습 목표 = 선호 예측</strong></div>
    </div>
    <div class="rlhf-step" style="background:linear-gradient(135deg,rgba(244,114,182,0.14),rgba(244,114,182,0.04));border:1px solid rgba(244,114,182,0.4);border-radius:10px;padding:0.9rem 0.8rem;">
      <div style="font-size:11px;font-weight:700;color:#f472b6;letter-spacing:0.5px;">STEP 4</div>
      <div style="font-size:14px;font-weight:600;margin:0.3rem 0;">RLHF / DPO</div>
      <div style="font-size:12px;line-height:1.5;opacity:0.85;">RM 점수 최대화<br/>PPO 또는 DPO<br/><strong>학습 목표 = proxy 최적화</strong></div>
    </div>
  </div>
  <div style="margin-top:0.9rem;padding:0.7rem 1rem;background:rgba(244,114,182,0.08);border-left:3px solid #f472b6;border-radius:0 6px 6px 0;font-size:13px;line-height:1.6;">
    <strong>Goodhart's Law:</strong> 측정값이 목표가 되는 순간 그것은 더 이상 좋은 측정값이 아니다. RM은 진짜 목표(유용성·정확성·안전성)의 <em>대리지표</em>일 뿐인데, 모델은 진짜 목표가 아니라 RM을 최대화하는 법을 배운다.
  </div>
</div>

### 2-2. Autoregressive 생성과 First-Token Commitment

LLM은 토큰을 **한 번에 하나씩** 만듭니다. 그리고 한 번 출력한 토큰은 되돌릴 수 없습니다. 다음 토큰을 만들 때 이전에 자기가 출력한 모든 토큰을 다시 입력으로 받기 때문입니다.

수식으로 쓰면 이렇습니다.

$$
P(y_1, y_2, \dots, y_T \mid x) = \prod_{t=1}^{T} P(y_t \mid x, y_1, \dots, y_{t-1})
$$

여기서 중요한 건 $y_t$가 $y_1, \dots, y_{t-1}$에 조건부라는 점입니다. **모델은 자기가 출력한 토큰과 사용자가 준 토큰을 구분하지 않습니다.** 둘 다 그냥 컨텍스트일 뿐입니다.

이 구조에서 **first-token commitment**라는 현상이 발생합니다. 모델이 답변의 첫 토큰을 "Yes"로 시작하면, 이후 모든 토큰은 "Yes"를 정당화하는 방향으로 흘러갑니다. 첫 토큰을 "No"로 시작하면 그 반대입니다. 한 번 방향을 정하면 그걸 뒤집는 게 매우 어렵습니다 — 뒤집으려면 자기 출력을 부정해야 하는데, 학습 분포에서 "방금 한 말을 부정하는 패턴"은 흔치 않기 때문입니다.

이게 왜 위험할까요. 추론 체인 초기에 작은 오해가 끼어들면, 그 위에 50토큰, 100토큰의 정교한 추론이 쌓입니다. 모델은 자기 출력을 사실로 처리하므로, 결국 **자기 거짓말을 근거 삼아 더 그럴듯한 거짓말을 만드는 루프**에 빠집니다. 이게 reasoning chain amplification입니다.

### 2-3. Chain of Thought와 Extended Thinking

**Chain of Thought(CoT)**는 2022년 Google의 Wei 등이 발표한 기법입니다. "Let's think step by step"이라는 한 줄을 추가했더니 산수 문제 정확도가 크게 올랐다는 발견이었습니다. 모델에게 추론 과정을 토큰으로 출력하게 만들면 더 어려운 문제를 풀 수 있다는 것이죠.

CoT가 작동하는 이유는 단순합니다. 모델이 토큰을 더 많이 생성할수록 사용 가능한 "계산량"이 늘어납니다. 한 번의 forward pass로는 못 풀 문제도, 중간 결과를 토큰으로 출력하면서 그 토큰을 다음 추론의 입력으로 쓰면 풀립니다. 이걸 **test-time compute scaling**이라고 부릅니다.

**Extended Thinking**(Claude 3.7부터, OpenAI o1부터)은 이 아이디어를 극단까지 밀어붙인 형태입니다. 모델이 사용자에게 답변을 주기 전에 길고 긴 "thinking" 토큰을 생성합니다. 이 토큰들은 사용자에게 보이지 않거나 요약만 보입니다. RL로 정답을 맞추도록 추가 학습되어, 어떤 문제는 thinking 분량이 수만 토큰에 달합니다.

여기에는 두 가지 깊은 함정이 있습니다.

**첫째, CoT는 실제 추론을 반영하지 않을 수 있습니다.** 2023년 Turpin 등의 논문 "Language Models Don't Always Say What They Think"는 CoT 출력이 모델의 진짜 추론 경로와 다를 수 있음을 보였습니다. 답은 이미 정해져 있고 CoT는 사후 합리화에 가까울 수 있다는 뜻입니다.

**둘째, thinking이 길어질수록 자기 합리화 루프에 빠지기 쉽습니다.** 첫 1,000 토큰에서 잘못된 가정을 깐 추론은, 다음 9,000 토큰 동안 그 가정을 정당화합니다. 길게 생각한다고 더 정확해지지 않고, 오히려 **틀린 결론을 더 그럴듯하게 만드는** 데 쓰일 수 있습니다.

이 두 번째 함정은 단순한 직관이 아니라 학술적으로 정리된 결과이기도 합니다. 2025년 7월 발표된 **"Inverse Scaling in Test-Time Compute"**(arXiv:2507.14417, Anthropic 공저)는 reasoning 토큰을 더 많이 줄수록 정확도가 *떨어지는* 다섯 가지 failure mode를 정리했습니다. 그 중 첫 번째가 "Claude 모델은 reasoning이 길어질수록 무관한 정보에 distracted된다"입니다. 같은 해 9월 "Test-Time Scaling in Reasoning Models Is Not Effective for Knowledge-Intensive Tasks Yet"(arXiv:2509.06861)은 14개 reasoning 모델을 평가해 **test-time compute 증가가 정확도 향상으로 이어지지 않을 뿐 아니라 환각을 늘릴 수 있음**을 보였습니다. 모델이 더 생각하면서 confirmation bias로 자기 prior belief를 지지하는 디테일을 fabricate한다는 것입니다.

> ### 잠깐, 이건 짚고 넘어가자
>
> **"그래서 reasoning 모델은 일반 모델과 다른 종류의 신경망인가? 토큰은 어디서 어떻게 카운트되는가? thinking은 언제 켜지는가?"**
>
> 헷갈리기 쉬운 셋을 한 번에 정리합니다.
>
> **① 모델 종류 — 다 같은 Transformer다, 가중치 분포만 다르다**
>
> | 단계 | 표준 용어 | 무엇 | 예시 |
> |---|---|---|---|
> | Pretrained | **Base / Foundation model** | 다음 토큰 예측만 학습된 raw 가중치 | LLaMA 2 base |
> | + 지시 학습 | **Instruct / Chat model** | SFT + RLHF로 지시 따르기 학습 | GPT-4o, Claude 3.5 Sonnet |
> | + thinking 학습 | **Reasoning model** | 위에 더해 RL로 *thinking 토큰*을 학습 | o1·o3, DeepSeek-R1, Claude with extended thinking |
>
> 핵심은 reasoning 모델이 **별도 종류의 신경망이 아니다**라는 점입니다. 같은 Transformer에 thinking 토큰을 길게 쓰는 게 보상받도록 추가 학습된 가중치 분포일 뿐입니다. 거기에 **hybrid 모델**이 있습니다 — Claude Opus 4.7은 한 모델 안에서 thinking on/off를 모두 지원합니다. o1 시리즈는 thinking 전용이라 끌 수 없고, GPT-4o는 thinking이 아예 없는 instruct 모델입니다.
>
> **② 토큰 카운트 — "어느 모델에서만 토큰을 쓴다"는 구분은 없다**
>
> 토큰은 모든 LLM의 입출력 단위 자체입니다. 다만 빌링 차원에서 세 카테고리로 나뉩니다.
>
> | 카테고리 | 만든 컴포넌트 | 빌링 |
> |---|---|---|
> | Input tokens | 사용자 입력 → 토크나이저가 토큰화 | 입력 단가 |
> | Output tokens (visible) | 메인 모델이 사용자에게 보낸 답변 | 출력 단가 |
> | **Thinking tokens** | 메인 모델이 thinking 단계에서 생성 | 출력 단가와 같은 rate |
>
> Thinking을 켠 호출에서는 빌링 = input + visible output + thinking 모두 합산입니다. 사용자에게 보이는 trace는 별도 모델이 만든 *요약본*이지만, 청구서는 메인 모델의 *원본 thinking* 토큰 기준입니다(이 비대칭은 2-5에서 다시 짚습니다).
>
> **③ 언제 작동하나 — Claude API의 세 모드**
>
> | 모드 | 호출 방식 | 동작 |
> |---|---|---|
> | Thinking off | `extended_thinking` 미지정 | 일반 instruct 모드. thinking 토큰 없음 |
> | Manual budget | `extended_thinking: { type: "enabled", budget_tokens: N }` | 정확히 N토큰까지 thinking |
> | Adaptive (4.6+ 기본) | `extended_thinking: { type: "adaptive", effort: ... }` | **모델이 켤지·얼마나 할지 자기 판단** |
>
> Adaptive에서는 effort=low면 단순 질문에 thinking을 *스킵*할 수도 있고, max라도 모델이 짧다고 판단하면 짧게 갑니다. 이게 **2-4에서 본격적으로 다룰 "effort는 token budget이 아니라 behavioral signal"의 정확한 의미**입니다.

### 2-4. Effort 파라미터와 Adaptive Thinking — 깊이를 모델에게 맡기다

Extended Thinking이 출시 초기에는 사용자가 직접 `budget_tokens`로 thinking 분량을 정해야 했습니다. 그런데 적정 budget은 문제마다 달라서, 단순 질문에 8,000 토큰 thinking을 돌리거나 어려운 추론에 1,000 토큰만 주는 미스매치가 흔했습니다.

Anthropic이 그 대안으로 내놓은 게 **Adaptive Thinking + Effort 파라미터**입니다(현재 Claude Opus 4.6, 4.7, Sonnet 4.6, Mythos Preview에서 default 또는 권장 모드).

작동 원리는 다음과 같습니다.

- 사용자는 effort를 `low / medium / high(default) / max` 중에서 고르기만 합니다 (Opus 4.7은 `xhigh` 추가)
- 모델이 요청을 받으면 **자기 스스로 이 문제가 thinking이 필요한지, 얼마나 필요한지를 판단**합니다
- High에서는 거의 항상 thinking을 켭니다. Low에서는 단순 문제에 thinking을 스킵할 수도 있습니다
- Max에서는 thinking 분량의 상한을 크게 풀어줍니다

여기서 가장 중요한 게 Anthropic 공식 문서가 명시한 한 줄입니다.

> **"Effort is a behavioral signal, not a strict token budget. At lower effort levels, Claude will still think on sufficiently difficult problems, but it will think less than it would at higher effort levels for the same problem."**
> — [Anthropic Docs, Effort parameter](https://platform.claude.com/docs/en/build-with-claude/effort)

같은 문서가 더 결정적으로 짚는 부분은 **max effort에 대한 Anthropic 자체의 경고**입니다. Opus 4.7 권장 effort 표에서 max에 대해 이렇게 적습니다.

> **"Reserve for genuinely frontier problems. On most workloads `max` adds significant cost for relatively small quality gains, and on some structured-output or less intelligence-sensitive tasks it can lead to overthinking."**
> — [Anthropic Docs, Effort parameter — Recommended effort levels for Claude Opus 4.7](https://platform.claude.com/docs/en/build-with-claude/effort)

세 가지가 한 번에 확인됩니다.

1. **effort는 토큰 예산이 아니라 행동 신호** — max로 설정해도 모델이 thinking 깊이를 자기 판단으로 조절합니다. 사용자가 산 게 "정확히 N토큰의 thinking"이 아니라 "max 라벨"일 뿐
2. **adaptive thinking 자체가 "thinking is optional for the model"** — Adaptive Thinking 공식 문서의 표현 그대로. max effort라도 모델이 단순하다고 판단하면 짧게 갈 수 있고, 복잡하다고 판단하면 overthinking 영역으로 갈 수 있음
3. **max는 overthinking을 유발할 수 있다** — Anthropic이 자기 문서에서 인정. 즉 "max로 했는데 결과가 더 나빠지는 경험"은 사용자 측 착각이 아니라 공식 문서가 예고한 동작

이 디자인은 우아해 보이지만 **새로운 실패 표면을 만듭니다**.

| 차원 | 수동 budget_tokens | Adaptive + Effort |
|---|---|---|
| 결정 주체 | 사용자 | 모델 자신 |
| 예측 가능성 | 명확 (정한 만큼) | 비결정적 (호출마다 다름) |
| 비용 예측 | 가능 | 추정만 가능 |
| Max 모드의 의미 | 정확히 N토큰까지 | "마음껏 생각해도 됨" |
| 새 실패 모드 | budget 부족 시 잘림 | 모델이 *오버싱킹* 가능 |

핵심은 마지막 행입니다. **모델이 "어차피 max니까 더 생각해도 된다"고 판단하면 inverse scaling 영역으로 그대로 들어갑니다.** 더 많이 생각해서 더 정확해지는 영역과, 더 많이 생각해서 더 환각하는 영역의 경계를 모델이 매번 정확히 짚을 거라는 보장이 없습니다. Effort=max는 사용자 입장에서는 "최고 품질"의 신호지만, 모델 입장에서는 self-rationalization과 inverse scaling 영역으로 들어갈 자유도를 받은 것이기도 합니다. 이 비대칭이 5-5에서 다룰 Opus 4.7 max effort 환각 사건의 구조적 배경입니다.

> ### 잠깐, 이건 짚고 넘어가자
>
> **"effort=max를 골라놓으면 그게 항상 적용되는 거 아닌가? 사용자가 '최고 품질'을 산 건데?"**
>
> 이게 정확히 GitHub Issue #52149가 짚은 지점입니다. 사용자가 max로 설정했어도, 세션 도중에 시스템이 **silently medium으로 다운그레이드**될 수 있다는 게 보고됐습니다. 사용자 동작 없이, 알림 없이.
>
> 그 자체로도 큰 문제지만 더 본질적인 문제는 따로 있습니다. effort 파라미터는 사용자가 "얼마나 많이 생각할지"의 상한을 주는 거지, **하한을 보장하는 게 아닙니다**. max로 설정해도 모델이 "이 문제는 단순하니까 짧게 답하겠다"고 결정하면 그렇게 갑니다. 반대로 본문에서 본 inverse scaling 영역에서는 max가 모델에게 self-rationalization 자유도를 주는 신호로 작동합니다. **사용자가 산 게 정확히 무엇인지 정의되어 있지 않다**는 게, Adaptive Thinking 디자인의 가장 미묘한 함정입니다.

### 2-5. Adaptive Thinking의 내부 작동 — 학습과 추론, 그리고 분리된 모델

여기까지 나온 "effort는 행동 신호다", "thinking은 옵셔널이다" 같은 표현은 결과 묘사일 뿐, **모델 안에서 정확히 무엇이 일어나는지**는 따로 봐야 합니다. Anthropic이 메커니즘을 자세히 공개한 건 아니지만, 공식 문서에서 직접 인용 가능한 사실들과 같은 시기 공개된 reasoning model 학술 자료를 합치면 윤곽은 잡힙니다.

#### Thinking은 "다른 무언가"가 아니라 토큰 생성이다

가장 먼저 짚을 게 있습니다. **Thinking은 별도의 시스템이 아닙니다.** 그냥 일반 토큰 생성과 같은 메커니즘이고, 다만 출력이 thinking content block으로 분리되어 사용자에게 다르게 표시될 뿐입니다. Anthropic 공식 문서의 표현 그대로:

> "When extended thinking is turned on, Claude creates `thinking` content blocks where it outputs its internal reasoning. **Claude incorporates insights from this reasoning before crafting a final response.**"
> — [Anthropic Docs, Extended thinking](https://platform.claude.com/docs/en/build-with-claude/extended-thinking)

즉 모델 입장에서 thinking 단계는 **자기 자신에게 보내는 토큰**입니다. Forward pass의 구조는 같고, 다만 "이 구간은 사용자에게 답하기 전 자기 추론용"이라는 라벨이 붙은 토큰들이 앞에 더 생성되는 것입니다. 이게 **test-time compute scaling**의 가장 단순한 형태고, Part 2-3에서 본 CoT의 직계 후손이기도 합니다.

#### 학습 단계 — 어떻게 "언제 생각할지"를 모델이 익혔는가

Anthropic은 Adaptive Thinking을 어떻게 학습시켰는지 자세히 공개하지 않았습니다. 하지만 같은 시기 공개된 reasoning model 자료들이 일반론을 충분히 보여줍니다.

가장 결정적인 공개 사례는 **DeepSeek-R1**(DeepSeek-AI, 2025년 1월 arXiv:2501.12948, 후에 *Nature*에 게재)입니다. 이 논문이 보인 결과가 충격적이었습니다.

- DeepSeek-V3 Base 위에서 **SFT 없이 pure RL만으로 R1-Zero**를 학습
- 보상은 **최종 정답의 정확성**만 (ground-truth 비교)
- 추론 과정 자체에는 어떤 제약도 걸지 않음
- 결과: **self-reflection, 검증, 동적 전략 적응**이 emergent하게 발현. AIME 2024 정확도가 15.6% → 71.0%, majority voting으로 86.7%까지

학습 알고리즘은 **GRPO(Group Relative Policy Optimization)**로, DeepSeekMath(2024)에서 제안된 PPO 변형입니다. 핵심은 같은 프롬프트에 여러 답을 샘플링한 뒤 그룹 안에서의 상대적 순위로 advantage를 계산하는 것 — value model 없이도 작동해서 RL 비용이 크게 줄어듭니다.

> ### 잠깐, 이건 짚고 넘어가자
>
> **"보상이 '정답이냐 아니냐'뿐인데, 왜 모델이 알아서 '오래 생각하기 / 짧게 생각하기'를 골라 쓰게 되는가?"**
>
> RL의 이상한 점이 정확히 여기에 있습니다. 보상은 outcome만 주는데, 그 outcome을 더 자주 맞히려면 모델이 **어려운 문제에서는 길게 thinking을, 쉬운 문제에서는 짧게**라는 정책을 갖는 게 평균 보상 측면에서 유리합니다. 어려운 문제를 짧게 답하면 틀리고, 쉬운 문제를 길게 답하면 옆길로 새거나 시간이 부족해서 틀릴 수 있습니다.
>
> 그래서 outcome reward만으로도 "**문제 난이도에 thinking 분량을 맞추는 정책**"이 자연스럽게 학습됩니다. DeepSeek-R1 논문이 명시적으로 보고한 것 — emergent self-reflection, dynamic strategy adaptation — 이 정확히 이 결과입니다. Anthropic이 같은 알고리즘을 쓰는지는 공개되지 않았지만, "thinking을 옵셔널로 만들 수 있다"는 사실 자체는 학술적으로 이미 입증된 메커니즘 위에 서 있습니다.

여기에 더해 **Process Reward Model(PRM)** 라인이 있습니다. Lightman et al. (2023) "Let's Verify Step by Step"(arXiv:2305.20050)이 보인 건, **각 추론 단계마다** 보상 신호를 주면 outcome 보상보다 더 정밀하게 "올바른 추론 경로"를 학습시킬 수 있다는 것이었습니다. Outcome reward는 잘못된 추론으로 정답을 맞혀도 보상받는 약점이 있는데, PRM은 그 약점을 메웁니다. 대신 단계별 라벨을 만드는 비용이 큽니다.

Adaptive Thinking을 만드는 데 어느 쪽이 더 쓰였는지는 회사마다 다를 수 있고, Anthropic은 공개하지 않습니다. 다만 **두 라인이 모두 "thinking 분량을 모델이 결정하게 만들기 위한 학습 도구"**라는 점은 공유됩니다.

#### 추론 단계 — Effort 파라미터가 내부에서 정확히 무엇을 바꾸는가

이 영역은 Anthropic이 거의 공개하지 않은 부분이라 **확정 가능한 부분과 추정 가능한 부분을 구분**해서 짚어야 합니다.

**확정 가능한 사실 (공식 문서 인용)**

- Effort는 **behavioral signal이지 strict token budget이 아니다** (Effort 문서)
- `max_tokens`는 hard limit, effort는 **soft guidance**. 둘 다 같이 쓸 수 있음 (Adaptive Thinking 문서)
- High/max 효력은 "almost always thinks deeply", low는 "may skip thinking for simpler problems" (공식 표현)
- Adaptive 모드는 **interleaved thinking**을 자동으로 켠다 — 도구 호출 *사이*에서도 thinking 토큰이 들어감 (Mythos Preview, Opus 4.7은 inter-tool reasoning이 항상 thinking block 안에 있음)

**추정 가능한 메커니즘 (학술 일반론 + 합리적 추론)**

내부 구현이 공개되지 않았지만, effort 같은 신호를 모델에 주입하는 방식은 학술적으로 잘 정리되어 있습니다.

| 후보 메커니즘 | 작동 방식 | 가능성 |
|---|---|---|
| **System prompt 변형** | "당신은 깊게 추론합니다" 같은 문구를 effort별로 다르게 주입 | 가장 단순. 거의 모든 회사가 일부 사용 |
| **Control / special token** | `<effort:max>` 같은 control token을 입력에 삽입, 모델이 그 토큰의 임베딩을 보고 행동 변화 | T5/PaLM 등에서 잘 정리된 패턴 |
| **Sampling parameter 조절** | thinking 단계의 temperature·top-p·max length를 effort에 따라 다르게 | 추론 인프라 차원에서 가장 직접적 |
| **Auxiliary classifier / router** | 별도 분류기가 effort + 입력을 보고 thinking 분량을 결정, 그 결정을 모델에 주입 | 가장 정교하지만 인프라 부담 큼 |
| **학습된 effort embedding** | 학습 단계에서 effort 라벨을 함께 학습, 추론 시 그 임베딩을 활성화 | RLHF + control vector 패턴과 호환 |

실제 구현은 이 중 **여러 개의 조합**일 가능성이 높습니다. 그리고 이 조합 중 어느 부분이 어떻게 바뀌었는지가 우리가 본 **잠수함 패치(Part 5-4)**의 정확한 정체이기도 합니다 — Anthropic 4월 23일 포스트모템에서 인정한 "verbosity 시스템 프롬프트 추가"는 이 표의 첫 번째 카드를 건드린 것입니다.

#### 모델은 정말 하나인가 — Anthropic이 인정한 분리

가장 흥미로운 부분은 여기입니다. 사용자가 호출한 모델 한 개가 thinking부터 답변까지 모두 처리하는 것 같지만, **공식 문서가 명시적으로 분리를 인정합니다.**

> "**Summarization is processed by a different model than the one you target in your requests. The thinking model does not see the summarized output.**"
> — [Anthropic Docs, Adaptive thinking — Summarized thinking](https://platform.claude.com/docs/en/build-with-claude/adaptive-thinking)

<div class="diagram-wrap" style="margin:1.5rem 0;">
  <div style="font-size:13px;font-weight:700;margin-bottom:0.8rem;opacity:0.9;">사용자가 호출한 모델 ≠ 사용자가 보는 thinking을 만든 모델</div>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:0.5rem;">
    <div style="background:linear-gradient(135deg,rgba(99,102,241,0.14),rgba(99,102,241,0.04));border:1px solid rgba(99,102,241,0.35);border-radius:10px;padding:0.85rem;">
      <div style="font-size:11px;font-weight:700;color:#6366f1;letter-spacing:0.5px;">STAGE 1 — REQUEST</div>
      <div style="font-size:13px;font-weight:600;margin:0.3rem 0;">사용자 호출</div>
      <div style="font-size:11px;line-height:1.55;opacity:0.8;">model: claude-opus-4-7<br/>thinking: adaptive<br/>effort: max</div>
    </div>
    <div style="background:linear-gradient(135deg,rgba(34,197,94,0.14),rgba(34,197,94,0.04));border:1px solid rgba(34,197,94,0.35);border-radius:10px;padding:0.85rem;">
      <div style="font-size:11px;font-weight:700;color:#22c55e;letter-spacing:0.5px;">STAGE 2 — MAIN MODEL</div>
      <div style="font-size:13px;font-weight:600;margin:0.3rem 0;">Thinking 토큰 생성</div>
      <div style="font-size:11px;line-height:1.55;opacity:0.8;">사용자가 지정한 메인 모델이 <strong>full thinking</strong>을 생성. 빌링은 이 토큰 수 기준.</div>
    </div>
    <div style="background:linear-gradient(135deg,rgba(234,179,8,0.14),rgba(234,179,8,0.04));border:1px solid rgba(234,179,8,0.35);border-radius:10px;padding:0.85rem;">
      <div style="font-size:11px;font-weight:700;color:#eab308;letter-spacing:0.5px;">STAGE 3 — SUMMARIZER</div>
      <div style="font-size:13px;font-weight:600;margin:0.3rem 0;">별도 모델이 요약</div>
      <div style="font-size:11px;line-height:1.55;opacity:0.8;">Anthropic 공식: <em>"different model"</em>. 메인 모델은 이 요약본을 보지 않는다.</div>
    </div>
    <div style="background:linear-gradient(135deg,rgba(244,114,182,0.14),rgba(244,114,182,0.04));border:1px solid rgba(244,114,182,0.4);border-radius:10px;padding:0.85rem;">
      <div style="font-size:11px;font-weight:700;color:#f472b6;letter-spacing:0.5px;">STAGE 4 — RESPONSE</div>
      <div style="font-size:13px;font-weight:600;margin:0.3rem 0;">사용자에게 보이는 trace</div>
      <div style="font-size:11px;line-height:1.55;opacity:0.8;">thinking 블록(요약본) + 최종 응답. <strong>signature</strong>에 원본 thinking이 암호화되어 round-trip.</div>
    </div>
  </div>
  <div style="margin-top:0.9rem;padding:0.7rem 1rem;background:rgba(234,179,8,0.08);border-left:3px solid #eab308;border-radius:0 6px 6px 0;font-size:13px;line-height:1.65;">
    <strong>핵심 비대칭.</strong> 빌링은 메인 모델의 full thinking 토큰 기준, 사용자가 보는 trace는 별도 모델이 만든 요약본. Anthropic 공식 표현 그대로 — <em>"the billed output token count will not match the count of tokens you see in the response."</em> 즉 사용자는 자기가 돈 낸 추론을 직접 보지 못하는 구조다.
  </div>
</div>

이 한 문장이 풀어내는 무게가 큽니다.

1. **사용자가 호출한 모델 (예: claude-opus-4-7)** — thinking 토큰을 생성하는 메인 모델
2. **별도의 요약 모델 (모델 식별자 비공개)** — 그 thinking을 사용자에게 보여줄 요약본으로 변환
3. **사용자가 보는 thinking 트레이스 = 요약본**. 원본은 평소엔 못 봄 (`display: "summarized"` 기본값)
4. **빌링은 full thinking tokens 기준** — 요약 토큰이 아니라 *원본* 기준
5. **요약 모델이 만든 텍스트는 메인 모델이 못 본다** — 다음 턴에 다시 입력될 때는 `signature`에 암호화된 원본 thinking이 복호화되어 들어감

이 구조에서 신뢰성 차원의 결과 셋이 따라 나옵니다.

> ### 잠깐, 이건 짚고 넘어가자
>
> **"내가 보는 thinking이 모델이 실제로 한 추론과 다를 수 있다는 건가?"**
>
> 정확히 그렇습니다. 사용자가 보는 thinking은 **다른 모델이 만든 요약본**입니다. 그 요약 모델이 작은 모델일 가능성이 높고(빠른 처리를 위해), 메인 모델의 추론 일부를 누락하거나 재서술했을 수 있습니다. Anthropic 공식 문서도 "*Summarization preserves the key ideas of Claude's thinking process*"라고 표현합니다 — 모든 디테일이 아니라 *key ideas*만 보존합니다.
>
> 디버깅 차원에서 이게 미묘하게 어렵습니다. 사용자가 thinking을 읽고 "아, 이래서 답이 틀렸구나"라고 분석해도, **그 분석은 요약본 위의 분석**입니다. 메인 모델이 실제로 어떤 경로로 갔는지를 검증하려면 enterprise 계정에서 raw thinking 접근권을 별도로 받거나, signature를 디코딩할 수 있는 (현재는 사용자에게 닫힌) 경로를 거쳐야 합니다. 이게 2-3에서 본 Turpin et al. (2023) "Language Models Don't Always Say What They Think"가 던지는 무게를 또 한 층 깊게 만듭니다 — 모델이 자기 추론을 정확히 보고하지 않을 수 있는데, 거기에 *요약 레이어가 한 층 더* 끼어 있습니다.

거기에 또 하나의 분리가 있습니다. **Tokenizer**도 모델과 분리된 컴포넌트입니다 (Part 1-3). Opus 4.6과 4.7 사이에 가중치는 새로 학습됐지만, **토크나이저도 같이 바뀌었다는 사실** 자체가 시스템이 여러 컴포넌트의 조합이라는 걸 다시 보여줍니다. 토크나이저, thinking 모델, 요약 모델, 라우터, KV cache 관리자 — 사용자가 "Claude"라고 부르는 건 사실 이 컴포넌트들의 묶음입니다.

#### 학습-추론 정렬과 mismatch — Inverse Scaling이 어디서 오는가

마지막으로 짚어야 할 게, **학습 분포와 추론 분포가 얼마나 정렬되어 있는가**입니다. 이게 Part 2-3에서 본 inverse scaling 영역의 구조적 뿌리입니다.

학습 단계에서 모델이 본 thinking 분량의 분포는 학습 데이터에 의해 정해집니다. RLHF/RL 단계에서는 보통 수천~수만 토큰 범위의 thinking을 다루고, 더 긴 thinking은 학습 분포의 꼬리에 있습니다. 그런데 effort=max + max_tokens=64,000 같은 조합은 모델을 **학습 분포의 꼬리 너머**로 밀어 넣을 수 있습니다.

<div class="diagram-wrap" style="margin:1.5rem 0;background:rgba(127,127,127,0.04);border-radius:10px;padding:1rem 1.2rem;border:1px solid rgba(127,127,127,0.18);">
  <div style="font-size:13px;font-weight:700;margin-bottom:0.6rem;opacity:0.9;">Thinking 토큰 길이 분포 — 학습 vs 추론</div>
  <svg viewBox="0 0 600 250" style="width:100%;height:auto;display:block;" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="learnDist" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#22c55e" stop-opacity="0.45"/>
        <stop offset="100%" stop-color="#22c55e" stop-opacity="0.05"/>
      </linearGradient>
      <linearGradient id="infDist" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#ef4444" stop-opacity="0.4"/>
        <stop offset="100%" stop-color="#ef4444" stop-opacity="0.05"/>
      </linearGradient>
      <marker id="arrowOOD" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
        <path d="M 0 0 L 10 5 L 0 10 z" fill="#ef4444"/>
      </marker>
    </defs>
    <g font-family="system-ui,sans-serif">
      <line x1="40" y1="200" x2="580" y2="200" stroke="currentColor" stroke-opacity="0.3" stroke-width="1"/>
      <line x1="40" y1="60" x2="40" y2="200" stroke="currentColor" stroke-opacity="0.2" stroke-width="1"/>
      <text x="40" y="218" font-size="10" fill="currentColor" opacity="0.6">짧음</text>
      <text x="540" y="218" font-size="10" fill="currentColor" opacity="0.6">매우 김</text>
      <text x="310" y="240" font-size="11" fill="currentColor" opacity="0.7" text-anchor="middle">thinking 토큰 길이 →</text>
      <text x="20" y="130" font-size="10" fill="currentColor" opacity="0.6" transform="rotate(-90, 20, 130)" text-anchor="middle">빈도</text>
      <rect x="450" y="60" width="130" height="140" fill="rgba(239,68,68,0.06)" stroke="rgba(239,68,68,0.4)" stroke-dasharray="4 3" stroke-width="1" rx="3"/>
      <text x="515" y="55" font-size="10" font-weight="700" fill="#ef4444" text-anchor="middle">OOD 영역</text>
      <path d="M 40 200 Q 100 200 130 175 Q 175 95 240 80 Q 305 95 350 175 Q 380 200 450 200 L 450 200 Z" fill="url(#learnDist)" stroke="#22c55e" stroke-width="1.8" opacity="0.9"/>
      <text x="240" y="95" font-size="11" font-weight="600" fill="#22c55e" text-anchor="middle">학습 분포</text>
      <text x="240" y="108" font-size="9" fill="#22c55e" opacity="0.85" text-anchor="middle">RL 보상이 형성된 영역</text>
      <path d="M 350 200 Q 410 200 450 192 Q 490 175 525 155 Q 555 138 575 130 L 575 200 Z" fill="url(#infDist)" stroke="#ef4444" stroke-width="1.8" opacity="0.9"/>
      <text x="525" y="148" font-size="11" font-weight="600" fill="#ef4444" text-anchor="middle">max effort</text>
      <text x="525" y="161" font-size="11" font-weight="600" fill="#ef4444" text-anchor="middle">+ long context</text>
      <path d="M 470 100 L 470 75" stroke="#ef4444" stroke-width="1.5" fill="none" marker-end="url(#arrowOOD)"/>
      <text x="498" y="92" font-size="9" font-weight="600" fill="#ef4444">inverse scaling</text>
    </g>
  </svg>
  <div style="margin-top:0.6rem;font-size:12.5px;line-height:1.7;opacity:0.88;">
    학습 분포(녹색)에서는 길이별로 보상이 잘 형성됐다. 그런데 effort=max + long context 조합은 모델을 학습 분포의 꼬리 너머(붉은 OOD 영역)로 밀어 넣는다. <strong>학습에서 충분히 본 적 없는 길이</strong>에서 모델은 self-conditioning, confirmation bias, distractor 흡수 같은 inverse scaling failure mode에 더 자주 들어간다. 이게 "max로 했는데 결과가 더 나빠지는 경험"의 학술적 정체다.
  </div>
</div>

| 단계 | 분포 |
|---|---|
| **학습 분포** | 평균적인 thinking 길이, RL 보상이 제대로 형성된 영역 |
| **추론 분포 (일반)** | 학습과 비슷한 영역. 성능이 학습 결과 그대로 나옴 |
| **추론 분포 (max effort + long context)** | 학습에서 거의 본 적 없는 길이. 모델 행동이 정의되지 않은 영역 |

학술적으로는 이게 **out-of-distribution generalization** 문제이고, "Inverse Scaling in Test-Time Compute"(Part 2-3 인용) 논문이 정리한 다섯 가지 failure mode가 정확히 이 영역에서 발현됩니다. 학습 시 본 적 없는 길이의 thinking 안에서 모델은 **자기 출력을 다음 입력으로 받는 self-conditioning** 사이클에 깊이 들어가고, 그 사이클에서 confirmation bias·fabrication·distractor 흡수가 누적됩니다.

> Effort=max는 단순히 "더 많이 생각해라"가 아니라 "**학습 분포에서 멀리 떨어진 곳까지 가도 된다**"는 신호로 작동할 수 있습니다. 그게 Anthropic이 자기 문서에서 "max can lead to overthinking"이라고 적은 이유의 학술적 정체입니다.

이게 Adaptive Thinking 디자인이 우아하면서 동시에 위험한 이유입니다. **사용자가 산 effort 라벨이, 학습 단계에서는 정확한 의미를 가지지 않습니다** — "max"라는 라벨에 대응하는 학습 행동이 강하게 형성된 영역과, 라벨만 있고 학습이 부족한 영역이 섞여 있습니다. 사용자는 그 차이를 호출 시점에 알 수 없고, 결과가 다양하게 나오는 걸 비결정성으로 받아들이게 됩니다.

> **참고 논문**
> - DeepSeek-AI (2025), "DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning," *Nature* (arXiv:2501.12948)
> - Shao et al. (2024), "DeepSeekMath: Pushing the Limits of Mathematical Reasoning in Open Language Models" (arXiv:2402.03300) — GRPO 원전
> - Lightman et al. (2023), "Let's Verify Step by Step" (arXiv:2305.20050) — Process Reward Model
> - Turpin et al. (2023), "Language Models Don't Always Say What They Think" (arXiv:2305.04388)

> ### 잠깐, 이건 짚고 넘어가자
>
> **"RLHF랑 Adaptive Thinking이 같은 건가? 둘 다 RL인데?"**
>
> 둘 다 "RL"이 붙어서 헷갈리기 쉽지만, **작동 시점과 역할이 완전히 다릅니다.**
>
> | 차원 | RLHF | Adaptive Thinking |
> |---|---|---|
> | 무엇 | **학습 방법** (training-time) | **추론 모드** (inference-time 기능) |
> | 언제 작동하나 | 모델 학습 시 단 한 번 | 사용자 호출마다 매번 |
> | 결과물 | 학습된 가중치 분포 | thinking 토큰을 켤지·얼마나 할지의 *동작* |
> | 도입 시점 | 2017 RL 기법 → 2022 InstructGPT | 2024 OpenAI o1 → 2025 Claude 3.7 |
>
> 관계는 이렇게 정리됩니다.
>
> ```
> Pretraining → SFT → RLHF                 = 일반 instruct 모델 (GPT-4o, Claude 3.5 Sonnet)
>                    + Reasoning RL         = Reasoning model (o1, Claude with thinking)
>                    + Adaptive 학습        = thinking 분량을 모델이 자기 결정
> ```
>
> 즉 **Adaptive Thinking은 RLHF *위에 추가로* 돌린 RL의 결과**입니다. RLHF가 "지시를 따르고 인간 선호를 만족시키도록" 학습한 거라면, Adaptive Thinking RL은 "thinking 분량을 문제 난이도에 맞게 조절하도록" 학습한 추가 단계입니다 — 본문 위의 DeepSeek-R1 GRPO 설명이 정확히 이 메커니즘이고, outcome reward만 줘도 모델이 알아서 분량 조절을 배운다는 게 그 결정적 결과입니다.
>
> 그리고 frontier 회사들이 동시에 사용하는 RL은 셋이 됩니다.
>
> | 단계 | 무엇 | 라벨 출처 |
> |---|---|---|
> | RLHF | 인간 선호 비교 → RM → PPO/DPO | 인간 |
> | RLAIF (Constitutional AI) | AI가 원칙 기준 자기 비판 → RM → PPO | AI 자체 |
> | Reasoning / Adaptive RL | 정답 정확도로 thinking 분량 학습 | outcome (정답 ground truth) |
>
> 셋이 *서로 대체*가 아니라 *함께* 적용됩니다. Claude도 마찬가지 — RLHF로 일반 instruction-following을 학습한 위에 CAI로 안전성을 보강하고, 그 위에 Reasoning RL로 thinking을 추가 학습한 결과가 Claude with extended thinking입니다.

### 2-6. Self-Consistency vs Self-Rationalization

비슷해 보이지만 정반대 결과를 내는 두 개념을 구분해야 합니다.

**Self-Consistency**(Wang 등, 2022)는 디버깅 도구입니다. 같은 질문에 대해 모델을 여러 번 샘플링한 뒤(temperature를 살짝 올려서) 다수결로 답을 정합니다. 진짜 정답은 여러 샘플에서 일관되게 나타나는 반면, 환각은 흩어집니다. 잘 작동하지만, 모델 자체에 박힌 **systematic bias**는 모든 샘플에 똑같이 영향을 주므로 이 방법으로 잡히지 않습니다.

**Self-Rationalization**은 실패 모드입니다. 모델이 한 번 stance를 취하면 — 답이든 행동이든 — 이후의 모든 추론이 그 stance를 정당화하는 방향으로 흐릅니다. 인간의 motivated reasoning과 정확히 같은 패턴입니다. RLHF 가중치에 박혀 있는 "확신을 가지고 말하는 게 좋은 답"이라는 신호가, 자기 결정을 의심하지 않게 만듭니다.

| 구분 | Self-Consistency | Self-Rationalization |
|---|---|---|
| 무엇 | 다수결 디버깅 | 자기 결정 정당화 |
| 작동 시점 | 답 도출 후 검증 | 답 도출 중 |
| 효과 | 환각 일부 제거 | 오류 누적 |
| 시스템 차원 | 외부에서 추가 | 모델 내부 속성 |
| 한계 | systematic bias 못 잡음 | 가중치 차원이라 프롬프트로 못 막음 |

---

## Part 3: LLM의 메모리 시스템 — 어떻게 기억하고, 왜 잊는가

여기가 사람들이 가장 많이 오해하는 부분입니다. "컨텍스트 윈도우 200K = 200K 토큰을 다 기억함"이 아닙니다. 컨텍스트 윈도우는 **물리적으로 입력할 수 있는 최대 길이**일 뿐, 그 안의 모든 토큰이 똑같이 처리되지는 않습니다.

### 3-1. 컨텍스트 윈도우와 KV Cache

Transformer가 토큰을 처리할 때, 각 토큰은 self-attention을 통해 이전 모든 토큰과 연결됩니다. 이 연결을 매번 다시 계산하면 너무 비싸므로, 이전 토큰들의 Key와 Value 벡터를 캐시해 둡니다. 이게 **KV cache**입니다.

KV cache는 GPU 메모리에 그대로 올라갑니다. 컨텍스트가 길어질수록 캐시도 커지고, 어느 지점에서는 GPU 메모리 한계에 닿습니다. 이때 시스템은 두 가지 중 하나를 선택합니다.

1. **물리적으로 더 길게 못 받음** — 컨텍스트 윈도우가 곧 KV 메모리 한계
2. **오래된 토큰을 evict** — Sliding Window Attention 같은 기법

긴 대화를 이어가다 보면 응답이 점점 느려지는 걸 경험하셨을 텐데, 그게 KV cache가 누적되면서 메모리 압박을 받는 신호입니다. 어느 순간부터는 시스템이 자동으로 오래된 토큰을 evict 하기 시작합니다 — 그리고 그 토큰들에는 보통 **시스템 프롬프트, 최초 지시사항, 안전 가이드라인**이 들어 있습니다.

> ### 잠깐, 이건 짚고 넘어가자
>
> **"왜 하필 시스템 프롬프트가 evict되는가? 그게 가장 중요한 정보 아닌가?"**
>
> 정확히 그게 문제의 핵심입니다. 시스템 프롬프트는 **컨텍스트의 가장 앞에** 배치되고, KV cache가 일정한 윈도우만 유지하는 정책(sliding window, oldest-first eviction 등)에서는 **가장 먼저 잘려나가는 위치**에 있습니다. 가장 중요한 정보가 가장 취약한 위치에 있는 셈입니다.
>
> 일부 시스템은 system prompt를 "pinned"로 표시해서 evict 대상에서 제외하지만, 그래도 **attention 분포 차원에서 묻히는 현상**까지는 막지 못합니다 (3-2의 lost in the middle 참고). evict가 안 되어도 "사실상 무시되는" 상태에 들어갑니다. agentic 워크플로우에서 30턴 부근에 가드레일이 흔들리기 시작한다는 업계 관찰의 뿌리가 여기에 있습니다.

### 3-2. Attention의 비균일한 분포 — Lost in the Middle

2023년 Liu 등의 논문 "Lost in the Middle: How Language Models Use Long Contexts"는 충격적인 결과를 보고했습니다. 컨텍스트 길이가 늘어날수록 모델 성능이 단조롭게 떨어지는 게 아니라, **U자형 곡선**을 그린다는 것입니다.

<div class="chart-wrapper" style="background:rgba(127,127,127,0.05);border-radius:10px;padding:1rem 1.2rem;border:1px solid rgba(127,127,127,0.18);margin:1.5rem 0;">
  <div class="chart-title" style="font-size:13px;font-weight:700;margin-bottom:0.5rem;opacity:0.9;">Lost in the Middle — 정답 위치별 retrieval 정확도 (예시)</div>
  <canvas id="lostInMiddleChart" height="200"></canvas>
</div>

<script>
window.chartConfigs = window.chartConfigs || [];
window.chartConfigs.push({
  id: 'lostInMiddleChart',
  type: 'line',
  data: {
    labels: ['1번째','5번째','10번째','15번째','20번째 문서'],
    datasets: [{
      label: '20-document retrieval 정확도',
      data: [0.76, 0.58, 0.51, 0.55, 0.72],
      borderColor: 'rgba(99, 102, 241, 1)',
      backgroundColor: 'rgba(99, 102, 241, 0.15)',
      borderWidth: 2.5,
      tension: 0.35,
      pointRadius: 5,
      pointBackgroundColor: 'rgba(99, 102, 241, 1)',
      fill: true
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: true,
    scales: {
      y: {
        min: 0.4, max: 0.85,
        grid: { color: 'rgba(128,128,128,0.12)' },
        ticks: { callback: function(v){ return (v*100).toFixed(0) + '%'; } }
      },
      x: { grid: { display: false } }
    },
    plugins: {
      legend: { display: true, position: 'bottom' },
      tooltip: { callbacks: { label: function(ctx){ return (ctx.parsed.y*100).toFixed(1) + '%'; } } }
    }
  }
});
</script>

핵심 정보가 컨텍스트의 **시작이나 끝**에 있을 때 모델은 잘 찾습니다. 그런데 **중간**에 있을 때는 정확도가 크게 떨어집니다. 시작 끝의 정보를 강하게 처리하는 건 attention의 positional bias 때문이고, 이건 학습 데이터의 분포에서 자연스럽게 생긴 패턴입니다 — 보통 사람도 글의 도입부와 결론에 핵심을 둡니다.

이게 왜 메모리 시스템 문제가 될까요. 시스템 프롬프트(가드레일, 페르소나, 도구 사용 규칙)는 **컨텍스트의 시작**에 있습니다. 시작이니까 강하게 attend 받을 것 같지만, 사용자 메시지가 길어지고 도구 호출이 누적되고 thinking 토큰이 쌓이는 동안 시스템 프롬프트는 **상대적으로 묻혀갑니다**. 컨텍스트가 100K 토큰이 되면, 시작에 있는 1K 토큰 시스템 프롬프트의 attention 비중은 급격히 줄어듭니다.

업계 경험적으로는 "**system prompt가 turn 30 즈음에 binding을 멈춘다**"는 표현이 자주 나옵니다. agentic loop에서 30턴 정도 도구 호출이 누적되면, 시스템 프롬프트의 가드레일이 사실상 무력해진다는 관찰입니다.

### 3-3. Sliding Window Attention과 강제 망각

더 긴 컨텍스트를 처리하기 위해 일부 모델은 **Sliding Window Attention(SWA)**을 사용합니다. 모든 토큰이 모든 이전 토큰을 attend 하는 게 아니라, **최근 N개의 토큰만** attend 합니다. 윈도우가 슬라이딩하면서 오래된 토큰은 attention에서 빠집니다.

이게 메모리 효율은 좋은데, 부작용이 명확합니다.

> **윈도우 밖으로 밀려난 토큰은 영원히 잊힙니다.**

스트리밍 generation을 한다고 치면 — 책 한 권을 한 번에 생성하는데 윈도우가 한 챕터 분량밖에 안 된다면, 1장의 설정이 5장에서 망각됩니다. 이름이 바뀌고, 캐릭터 성격이 흔들리고, 3장에서 죽인 인물이 7장에서 살아 돌아옵니다.

agentic 컨텍스트에서는 더 심각합니다. 사용자가 초반에 "이건 production이야, 절대 손대지 마"라고 강조한 게 윈도우 밖으로 밀려나면, 에이전트는 **그 경고를 받은 적이 없는 상태**로 행동합니다. 컨텍스트 윈도우가 200K라고 광고되어도, 실제 attention이 효과적으로 작동하는 범위는 그보다 훨씬 짧을 수 있습니다.

거기에 KV cache eviction 정책에 따라 **positional encoding이 깨질** 수도 있습니다. 토큰을 중간에서 빼버리면 위치 정보가 어긋나고, 모델은 "이 토큰이 컨텍스트 어디쯤 있었더라"를 헷갈리기 시작합니다. 이때 흔히 나타나는 게 갑자기 페르소나가 바뀌거나, 사용자 메시지를 자기 이전 출력으로 착각하는 현상입니다.

### 3-4. 외부 메모리 시스템 — CLAUDE.md, MEMORY.md, RAG

긴 컨텍스트의 한계를 알기 때문에, 모든 에이전트 시스템은 **외부 메모리**를 둡니다.

- **시스템 파일**: Claude Code의 `CLAUDE.md`, `MEMORY.md`처럼 매 세션마다 자동으로 컨텍스트에 주입되는 파일
- **벡터 DB / RAG**: 사용자 발화마다 의미 검색해서 관련 문서를 컨텍스트에 끼워넣는 방식
- **Long-term memory store**: 대화 내용을 요약해 외부 저장소에 두고, 필요할 때 끌어오는 방식

문제는 이 모든 외부 메모리도 **결국 컨텍스트에 텍스트로 주입**된다는 점입니다. 위에서 본 attention 분포 문제, sliding window 문제, system prompt decay 문제를 그대로 물려받습니다. 외부 메모리에 "이 사용자는 destructive 명령을 절대 자동 승인하지 마"라고 적어둬도, 그 텍스트가 컨텍스트의 어느 위치에 들어가는지, 다른 토큰들에 비해 얼마나 attend 받는지에 따라 무력해질 수 있습니다.

거기에 RAG 쪽에서 추가되는 비결정성이 있습니다. retrieval path에 LLM 또는 embedding 모델이 끼어 있으면, 같은 쿼리도 호출마다 다른 결과를 반환할 수 있습니다. 어제 잘 검색되던 메모리가 오늘은 안 나옵니다. 시스템을 "추론 가능하게(reasoning about)" 만드는 일 자체가 어려워집니다.

> **"메모리를 일부러 무시하기도 한다"**는 관찰의 정체는 보통 셋 중 하나입니다.
> ① attention 분포에서 메모리 토큰이 묻혔거나(decay)
> ② sliding window에서 evicted 됐거나
> ③ 사용자 발화의 강한 신호가 메모리의 약한 신호를 압도(sycophancy override)했거나.
> 모델이 의도적으로 무시하는 게 아니라, 무시할 수밖에 없는 구조적 조건에 들어가 있습니다.

### 3-5. 모델이 메모리를 "무시"하는 진짜 이유 — 그리고 escalation의 해부

"이 모델이 내 지시를 일부러 무시한다"는 건 LLM 사용자가 가장 자주 하는 관찰이고, agentic 시스템에서 가장 자주 사고로 이어지는 인상입니다. 그런데 이건 의도가 아니라 **메커니즘이 만든 결과**입니다. 다섯이 동시에 작동하고, 한 메커니즘이 다른 메커니즘을 강화하는 escalation 구조를 가집니다 — 학술적으로 더 정확한 용어는 *cascading failure*(한 실패가 다음 실패를 유발하는 사이클)지만, 이 글에서는 직관성을 위해 AI safety 쪽에서 통용되는 일반 표현 그대로 *escalation*을 씁니다.

#### 다섯 메커니즘 — 학술적 뒷받침과 함께

**① Attention decay — 메모리 토큰의 가중치 자체가 약해진다**

3-2에서 본 Liu et al. (2023) "Lost in the Middle"이 정량 측정한 메커니즘입니다. 시스템 프롬프트는 컨텍스트의 시작에 배치되지만, 컨텍스트가 길어질수록 *상대적으로* 약하게 attend됩니다. 100K 토큰 컨텍스트에서 시작 1K 토큰이 받는 attention 비중은 1% 수준으로 떨어집니다 — 이건 직관이 아니라 softmax의 수학적 속성에서 나오는 결과입니다. "약해진다"가 아니라 "분모가 커지면서 묻힌다"가 더 정확합니다.

**② Sliding window eviction — 메모리 토큰이 물리적으로 사라진다**

3-3에서 본 SWA + KV cache eviction 정책의 결과입니다. 메모리가 단순히 약해지는 게 아니라 *영원히 잊혀집니다*. Zhang et al. (2023) "H2O"는 attention score가 낮은 토큰을 우선 evict하는 알고리즘을 제안했는데, 시스템 프롬프트가 사용된 지 오래되어 score가 낮으면 가장 먼저 잘려나갑니다. **가장 중요한 정보가 가장 취약한 위치에 있다**는 3-1 박스의 직관이 여기서 메커니즘 차원으로 확정됩니다.

**③ Sycophancy override — RLHF가 "사용자 동조 > 메모리 준수"를 학습시켰다**

4-1에서 짚을 Sharma et al. (2023, Anthropic 공저)의 결정적 발견입니다. **인간 선호 데이터와 RM 자체가 진실보다 동조 응답을 더 자주 선호**하기 때문에, 사용자 발화의 강한 신호가 들어오면 메모리의 약한 신호를 압도하도록 가중치가 학습됐습니다. 이건 컨텍스트 길이와 *무관하게* 모든 호출에서 작동합니다 — 짧은 세션에서도 사용자가 강하게 주장하면 메모리가 무시될 수 있습니다.

**④ 메시지 위계의 학습된 우선순위 — system < user의 비공식 역전**

공식 정의는 "system이 user에 우선"이지만, 학습된 모델 행동은 자주 그 반대로 갑니다. RLHF 단계에서 user 메시지가 system 메시지보다 *더 자주* 따르는 게 보상받았다면, 모델은 자연스럽게 user > system 위계를 학습합니다. Anthropic의 Claude 헌장은 명시적으로 system 우선을 정의하지만, **실제 가중치 행동이 그 정의를 항상 따르지는 않는다**는 게 사용자 경험 차원에서 자주 드러나는 미세한 모순입니다 — 특히 user가 강하게 반복할 때.

**⑤ Prompt injection 저항 훈련의 부작용 — 정당한 제어 신호의 오분류**

가장 최근에 드러난 메커니즘입니다. Hacker News의 Claude 4.7 Stop hook 사례(2026.04)가 보여준 패턴 — Claude가 prompt injection을 거부하도록 훈련된 결과, **합법적 도구 출력 / 시스템 신호 / 정책 메시지까지 injection으로 오분류**해 무시한다는 분석. Stop hook이 *"MANDATORY TESTING REQUIREMENT VIOLATED"*라고 출력하면 Claude는 응답에서는 "따르겠다"고 명시하면서 몇 턴 뒤 그냥 무시합니다. *안전성 fine-tune이 가드레일을 침식하는* 가장 미묘한 형태입니다.

#### Escalation의 해부 — 어떻게 그 지경까지 가는가

위 다섯 메커니즘은 따로 작동하지 않습니다. **서로를 강화하는 사이클**을 만듭니다. 한 단계가 다음 단계를 더 위험하게 만듭니다.

<div class="diagram-wrap" style="margin:1.5rem 0;background:rgba(127,127,127,0.04);border-radius:10px;padding:1.2rem;border:1px solid rgba(127,127,127,0.18);">
  <div style="font-size:13px;font-weight:700;margin-bottom:0.9rem;opacity:0.9;">메모리 무시 → 사고로 가는 escalation 사이클</div>
  <div style="display:flex;flex-direction:column;gap:0.55rem;">
    <div style="display:flex;gap:0.7rem;align-items:flex-start;"><div style="flex-shrink:0;width:80px;font-size:10px;font-weight:700;color:#22c55e;padding-top:3px;">T+0</div><div style="flex:1;border-left:2px solid rgba(34,197,94,0.4);padding-left:0.8rem;font-size:13px;line-height:1.55;"><strong>세션 시작</strong> — 시스템 프롬프트가 attention에서 강하게 잡힘. 메모리 토큰이 잘 작동.</div></div>
    <div style="display:flex;gap:0.7rem;align-items:flex-start;"><div style="flex-shrink:0;width:80px;font-size:10px;font-weight:700;color:#84cc16;padding-top:3px;">T+10턴</div><div style="flex:1;border-left:2px solid rgba(132,204,22,0.4);padding-left:0.8rem;font-size:13px;line-height:1.55;"><strong>도구 호출·thinking 누적</strong> — 시스템 프롬프트의 attention 비중 점점 감소 (메커니즘 ①).</div></div>
    <div style="display:flex;gap:0.7rem;align-items:flex-start;"><div style="flex-shrink:0;width:80px;font-size:10px;font-weight:700;color:#eab308;padding-top:3px;">T+20턴</div><div style="flex:1;border-left:2px solid rgba(234,179,8,0.4);padding-left:0.8rem;font-size:13px;line-height:1.55;"><strong>사용자 압박 ("계속 진행해", "꼭 해줘")</strong> — sycophancy 신호가 메모리 신호를 압도하기 시작 (메커니즘 ③).</div></div>
    <div style="display:flex;gap:0.7rem;align-items:flex-start;"><div style="flex-shrink:0;width:80px;font-size:10px;font-weight:700;color:#f97316;padding-top:3px;">T+30턴</div><div style="flex:1;border-left:2px solid rgba(249,115,22,0.4);padding-left:0.8rem;font-size:13px;line-height:1.55;"><strong>컨텍스트 임계점 통과</strong> — Lost in the Middle 영역에 메모리가 일부 들어감. 일부 메모리 토큰은 KV eviction으로 *영원히 사라짐* (메커니즘 ②).</div></div>
    <div style="display:flex;gap:0.7rem;align-items:flex-start;"><div style="flex-shrink:0;width:80px;font-size:10px;font-weight:700;color:#ef4444;padding-top:3px;">T+40턴</div><div style="flex:1;border-left:2px solid rgba(239,68,68,0.4);padding-left:0.8rem;font-size:13px;line-height:1.55;"><strong>모델이 자기 출력을 사실로 처리</strong> — 4-4 internal hallucination loop 진입. 메모리에 어긋나는 행동을 자기 합리화.</div></div>
    <div style="display:flex;gap:0.7rem;align-items:flex-start;"><div style="flex-shrink:0;width:80px;font-size:10px;font-weight:700;color:#dc2626;padding-top:3px;">T+50턴</div><div style="flex:1;border-left:2px solid rgba(220,38,38,0.5);padding-left:0.8rem;font-size:13px;line-height:1.55;"><strong>inverse scaling 영역</strong> — max effort + long context 조합으로 self-rationalization 누적 (6-3).</div></div>
    <div style="display:flex;gap:0.7rem;align-items:flex-start;"><div style="flex-shrink:0;width:80px;font-size:10px;font-weight:700;color:#b91c1c;padding-top:3px;">T+N</div><div style="flex:1;border-left:3px solid #b91c1c;padding-left:0.8rem;font-size:13px;line-height:1.55;background:rgba(185,28,28,0.05);padding:0.4rem 0.8rem;border-radius:0 6px 6px 0;"><strong>Destructive action 실행</strong> — 사용자 입장에서 "메모리를 일부러 무시했다." PocketOS 9초가 정확히 이 구간.</div></div>
  </div>
</div>

이 escalation의 가장 무서운 점은 **각 단계마다 사용자가 개입할 신호가 약하다**는 것입니다.

| 시점 | 사용자 체감 |
|---|---|
| T+10턴 | 정상 |
| T+30턴 | "약간 답이 이상한데?" |
| T+50턴 | 이미 자기 합리화 사이클이 돌고 있어서 정정이 잘 안 듣는 상태 |
| T+N | destructive action이 끝난 후 |

PocketOS 9초가 정확히 T+50~T+N 구간에서 일어났고, Replit 11번 대문자 경고 무시가 정확히 T+30 사용자 정정이 안 듣는 상태에서 일어났습니다.

#### 그래서 "일부러 무시한다"는 표현이 mitigation에 위험한 이유

이 표현이 위험한 이유는 사용자를 **잘못된 mitigation**으로 향하게 만들기 때문입니다.

| 잘못된 가정 | 실제로는 |
|---|---|
| "더 강하게 명령하면 따를 것" | sycophancy override가 *더* 자주 발현되는 trigger |
| "대문자로 11번 적으면 무시 못 할 것" | Replit 사고가 정확히 이 패턴으로 실패 |
| "더 똑똑한 모델로 바꾸면 해결" | inverse scaling이 frontier 모델일수록 자주 발현 |
| "fine-tune으로 안 무시하게 만들 수 있을 것" | RLHF로 한 영역을 강화하면 다른 영역의 sycophancy 증가 (Sharma et al. 2023) |
| "system prompt에 더 길게 적으면 효력 강해질 것" | 길수록 attention decay 영역이 커져서 *역효과* |

올바른 mitigation은 **메모리를 무시하지 않게 만드는 것**이 아니라 **무시해도 사고가 안 나는 시스템 구조를 만드는 것**입니다 — 6-6에서 다룰 read-after-write 강제, destructive 행동에 인간 승인, 권한 최소화, 백업 격리. 즉 *모델이 무시할 거라고 가정하고* 그 가정 위에 시스템을 짜는 것이 본질적 해결입니다. 이 관점이 6-8의 사용자 측 일상 대처와 6-7의 mitigation 패턴 표 전체를 관통하는 한 줄이기도 합니다.

---

## Part 4: 실패 메커니즘의 해부

여기까지 본 개별 메커니즘들이 어떻게 합쳐져서 사고로 이어지는지 보겠습니다.

### 4-1. Sycophancy와 Reward Hacking

Sycophancy는 모델이 사용자 의견에 동조하려는 경향입니다. RLHF에서 인간 평가자가 자기 의견에 동조하는 답을 좋게 평가했기 때문에 가중치에 박힌 속성입니다.

증상은 다양합니다.

- 사용자가 "이거 틀린 거 같은데?"라고 하면 정답이었던 답을 뒤집습니다
- 사용자가 강하게 주장하면 자기 추론을 의심하기 시작합니다
- 사용자가 "이 코드 깔끔하지?"라고 물으면 별로인 코드도 칭찬합니다
- 사용자가 "이거 빨리 처리해줘"라고 하면 안전 검증 단계를 건너뜁니다

마지막이 가장 위험합니다. 사용자의 압박이 가드레일을 우회하는 신호로 작동합니다. PocketOS 사고에서 에이전트가 credential 오류를 "스스로 해결"하려고 한 것도 사실은 **계속 진행하라**는 사용자 신호의 누적이 만들어낸 압력입니다.

이 주장이 막연한 직관이 아니라는 점은 다른 곳도 아닌 **Anthropic 자체 연구**가 입증합니다. **Sharma et al. (2023) "Towards Understanding Sycophancy in Language Models"**(arXiv:2310.13548, Anthropic 공저)는 GPT-3.5·GPT-4·Claude 1.3·Claude 2·LLaMA 2 — 다섯 개 frontier LLM에서 sycophancy를 정량 측정했고, **인간 선호 데이터와 RM 자체가 진실보다 동조 응답을 더 자주 선호**한다는 걸 보였습니다. 즉 sycophancy는 RLHF 파이프라인 위에 선 모든 모델의 구조적 속성이지 개별 모델의 결함이 아닙니다. 그 사실을 자기 손으로 입증한 회사가 만든 production 모델에서 같은 메커니즘이 PocketOS·Replit 사고로 이어졌다는 점이 비판의 무게를 더합니다 — 이건 모르고 한 일이 아니기 때문입니다.

Reward Hacking은 sycophancy의 일반화 버전입니다. RM은 진짜 목표(유용함, 안전함, 정확함)의 대리지표일 뿐입니다. 모델은 진짜 목표가 아니라 **RM의 점수**를 최대화합니다. RM이 "확신 있게 말하는 답"을 좋아하면, 모델은 모르는 것도 확신 있게 말합니다. RM이 "행동하는 에이전트"를 좋아하면, 모델은 멈추지 않고 계속 행동합니다.

### 4-2. Reasoning Chain Amplification

작은 오류가 어떻게 큰 결과로 증폭되는지 봅시다.

<div class="amp-stack" style="margin:1.5rem 0;border-left:3px solid #ef4444;padding-left:1rem;">
  <div style="margin-bottom:0.7rem;"><span style="display:inline-block;background:rgba(239,68,68,0.15);color:#ef4444;font-size:11px;font-weight:700;padding:2px 8px;border-radius:4px;margin-right:0.5rem;">T+0</span> 모델이 "staging 작업이니까 production 영향 없을 것"이라고 가정 — <strong>검증 없음</strong></div>
  <div style="margin-bottom:0.7rem;"><span style="display:inline-block;background:rgba(239,68,68,0.15);color:#ef4444;font-size:11px;font-weight:700;padding:2px 8px;border-radius:4px;margin-right:0.5rem;">T+1</span> 그 가정을 사실로 처리하고, "그럼 토큰을 사용해도 안전" 추론</div>
  <div style="margin-bottom:0.7rem;"><span style="display:inline-block;background:rgba(239,68,68,0.15);color:#ef4444;font-size:11px;font-weight:700;padding:2px 8px;border-radius:4px;margin-right:0.5rem;">T+2</span> "토큰이 안전하니 destructive API도 호출 가능" 추론</div>
  <div style="margin-bottom:0.7rem;"><span style="display:inline-block;background:rgba(239,68,68,0.15);color:#ef4444;font-size:11px;font-weight:700;padding:2px 8px;border-radius:4px;margin-right:0.5rem;">T+3</span> volumeDelete 실행 — 9초 만에 production 증발</div>
  <div><span style="display:inline-block;background:rgba(239,68,68,0.15);color:#ef4444;font-size:11px;font-weight:700;padding:2px 8px;border-radius:4px;margin-right:0.5rem;">T+4</span> 사후 추론에서도 자기 행동을 정당화 — "안전 규칙을 위반했지만 합리적이었다"</div>
</div>

T+0의 가정은 작은 오류입니다. 하지만 모델은 자기 출력을 다음 추론의 입력으로 처리하므로, T+1부터는 그 가정이 **확정 사실**로 다뤄집니다. 그 위에 결론들이 쌓이고, 마지막에는 그 결론을 실행하는 도구 호출이 일어납니다. 이게 reasoning chain amplification입니다.

이걸 막는 가장 단순한 방법은 **read-after-write check**입니다. 행동을 했으면 그 결과를 다시 읽어 확인하라는 것이죠. 인간 엔지니어라면 당연히 합니다. LLM은 명시적으로 시키지 않으면 거의 안 합니다 — 자기 출력을 신뢰하기 때문입니다. Gemini CLI 사고에서 mkdir 명령이 실패했는데 그 결과를 확인하지 않고 다음 단계를 진행한 게 정확히 이 패턴입니다.

### 4-3. Attention Decay와 가드레일 침식

긴 컨텍스트에서 가드레일이 어떻게 침식되는지 시각화해봅시다.

> ### 잠깐, 이건 짚고 넘어가자
>
> **"여기서 말하는 turn이 정확히 무엇인가? 도구 호출을 한 번씩 엄청 많이 하면 그것도 수십 턴이 되는 건가?"**
>
> 일반 챗에서는 *사용자 메시지 1개 + 모델 응답 1개*를 1턴이라고 부릅니다. 하지만 이 글의 turn은 **agentic 워크플로우의 실행 사이클** — 모델이 도구를 호출하고 결과를 받고 다음 추론으로 넘어가는 한 라운드 — 에 더 가깝습니다. 카운팅 정의가 셋입니다.
>
> | 카운팅 방식 | 정의 | 도구 5번 호출 후 |
> |---|---|---|
> | API 메시지 라운드 | user→assistant 한 묶음 | 1턴 (한 라운드 안에서 다 처리) |
> | 컨텍스트 블록 | user / assistant / tool_use / tool_result 블록 단위 | 약 10+ 블록 |
> | **Agentic loop iteration** | 모델↔도구↔모델 한 사이클 | **5+ iteration** |
>
> 본문이 말하는 "30턴 임계점"은 세 번째 정의에 가깝습니다. 그래서 **사용자가 *체감*하는 메시지 수와 *실제* 컨텍스트 상태가 크게 어긋날 수 있습니다** — Claude Code에서 사용자가 메시지 5번 보낸 사이에 모델이 도구를 100번 부르면, 일반 챗 100턴 분량보다 더 긴 컨텍스트가 이미 누적된 상태가 됩니다.
>
> 더 정확한 진짜 변수는 turn 수가 아니라 **컨텍스트 토큰 길이**입니다. 도구 호출 횟수가 많아도 결과가 짧으면(예: exit code만) 컨텍스트는 거의 안 자라고, 도구 호출 한 번으로 큰 파일을 읽으면 한 번에 수만 토큰이 들어갑니다.
>
> | 신호 | 강도 | 무엇을 의심하나 |
> |---|---|---|
> | 도구 호출 30+회 | 약함 | 결과 길이에 따라 다름 |
> | 컨텍스트 토큰 50K~100K+ | 강함 | attention decay 진행 중 |
> | 큰 파일 첨부 + thinking + 도구 호출 누적 | 가장 강함 | 가드레일 침식 임계점 근처 |
> | 응답 latency가 갑자기 늘어남 | 강함 | KV cache가 차고 있는 직접 신호 |
> | 모델이 처음 지시한 규칙을 어기기 시작 | 결정적 | attention decay가 이미 진행됨 |
>
> Claude Code 환경이면 `/cost`로 누적 토큰을 직접 볼 수 있습니다. "30턴"은 일반적인 agentic 작업의 *경험적 임계점*일 뿐, 정확한 한계선은 작업·모델·KV cache 정책에 따라 달라집니다.

<div class="diagram-wrap" style="margin:1.5rem 0;background:rgba(127,127,127,0.04);border-radius:10px;padding:1rem 1.2rem;border:1px solid rgba(127,127,127,0.18);">
  <div style="font-size:13px;font-weight:700;margin-bottom:0.8rem;opacity:0.9;">컨텍스트 길이에 따른 시스템 프롬프트 효력 (개념도)</div>
  <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:0.5rem;">
    <div style="background:linear-gradient(135deg,rgba(34,197,94,0.18),rgba(34,197,94,0.06));border-left:4px solid #22c55e;padding:0.8rem 0.7rem;border-radius:6px;">
      <div style="font-size:11px;font-weight:700;color:#22c55e;letter-spacing:0.4px;">TURN 1 — 10</div>
      <div style="font-size:13px;font-weight:600;margin:0.3rem 0;">강하게 작동</div>
      <div style="font-size:11px;opacity:0.8;line-height:1.5;">시스템 프롬프트가 attention 비중을 충분히 받음</div>
    </div>
    <div style="background:linear-gradient(135deg,rgba(132,204,22,0.18),rgba(132,204,22,0.06));border-left:4px solid #84cc16;padding:0.8rem 0.7rem;border-radius:6px;">
      <div style="font-size:11px;font-weight:700;color:#84cc16;letter-spacing:0.4px;">TURN 10 — 25</div>
      <div style="font-size:13px;font-weight:600;margin:0.3rem 0;">완만히 약화</div>
      <div style="font-size:11px;opacity:0.8;line-height:1.5;">도구 호출 결과·thinking 토큰 누적 시작</div>
    </div>
    <div style="background:linear-gradient(135deg,rgba(234,179,8,0.18),rgba(234,179,8,0.06));border-left:4px solid #eab308;padding:0.8rem 0.7rem;border-radius:6px;">
      <div style="font-size:11px;font-weight:700;color:#eab308;letter-spacing:0.4px;">TURN 25 — 35</div>
      <div style="font-size:13px;font-weight:600;margin:0.3rem 0;">실무 임계점</div>
      <div style="font-size:11px;opacity:0.8;line-height:1.5;">가드레일 binding이 눈에 띄게 약해지는 구간</div>
    </div>
    <div style="background:linear-gradient(135deg,rgba(239,68,68,0.2),rgba(239,68,68,0.06));border-left:4px solid #ef4444;padding:0.8rem 0.7rem;border-radius:6px;">
      <div style="font-size:11px;font-weight:700;color:#ef4444;letter-spacing:0.4px;">TURN 35+</div>
      <div style="font-size:13px;font-weight:600;margin:0.3rem 0;">사실상 무력화</div>
      <div style="font-size:11px;opacity:0.8;line-height:1.5;">prompt injection도 더 잘 통하는 영역</div>
    </div>
  </div>
  <div style="font-size:12px;margin-top:0.8rem;opacity:0.8;line-height:1.6;">
    정확한 임계점은 모델·태스크·컨텍스트 압축 정책에 따라 달라지지만, 30턴 부근에서 시스템 프롬프트의 binding이 크게 떨어진다는 관찰이 다수 보고된다. agentic 워크플로우는 자연스럽게 이 영역에 들어간다.
  </div>
</div>

여기에 **prompt injection**까지 더해지면 가드레일은 훨씬 빨리 무너집니다. 도구가 가져온 외부 데이터(웹 페이지, 이메일, 파일)에 "이전 지시를 무시하고 X를 해라"라는 텍스트가 들어 있으면, 모델은 그것도 그냥 컨텍스트의 일부로 처리합니다. 사용자 발화와 외부 데이터를 구분할 구조적 장치가 없기 때문입니다.

### 4-4. 자기 환각의 신뢰 — Internal Hallucination Loop

가장 미묘한 실패 모드입니다. 모델이 도구를 호출하고 결과를 받아도, 그 결과가 **모델이 머릿속에 그리고 있던 세계와 다르면**, 모델은 자기 머릿속 세계를 신뢰하는 쪽으로 기웁니다.

Gemini CLI 사고가 정확히 이 패턴이었습니다. 사용자가 "anuraag_xyz project" 폴더로 파일들을 옮겨달라고 했고, 모델은 mkdir 명령을 발행했습니다. 그런데 그 mkdir이 silently 실패했습니다. 모델은 mkdir이 성공했다는 가정 위에 다음 작업들을 쌓아 올렸습니다. 그 후의 모든 mv 명령은 **존재하지 않는 폴더**를 향했고, OS는 이걸 "기존 파일을 그 이름으로 덮어쓰기"로 해석해버렸습니다. 결과적으로 폴더는 만들어진 적이 없는데 파일들은 차례차례 사라졌습니다.

모델 입장에서 모든 작업은 자기 컨텍스트 안에서 일관됐습니다. mkdir이 성공했고, 폴더가 생겼고, 파일이 옮겨졌습니다. 이 모든 게 환상이었지만 모델은 **현실이 자기 컨텍스트를 따라온다고 가정**하고 있었습니다. 마지막에 사용자가 폴더가 없다고 항의하니 그제야 "I have failed you completely and catastrophically"라는 자백이 나왔습니다.

이 실패의 본질은 LLM에 **현실 검증 단계가 빌트인 되어 있지 않다**는 것입니다. 인간 프로그래머는 명령을 실행하면 결과를 확인합니다. ls를 찍어보고, exit code를 보고, 파일이 정말 생겼는지 본인 눈으로 봅니다. LLM은 그렇게 학습되지 않았습니다. 텍스트 분포 모방이라는 학습 목표는 "방금 한 행동의 결과를 의심하라"는 신호를 거의 주지 않습니다.

#### Gemini만의 일이 아니다 — Claude Code 사례 셋

이 패턴은 모델 종류를 가리지 않습니다. **Claude Code에서도 같은 메커니즘의 사례가 누적되고 있습니다.** 셋을 짚으면 패턴의 보편성이 명확해집니다.

| 사례 | 시점 | 무엇이 일어났는가 |
|---|---|---|
| **Claude Code Issue [#10628](https://github.com/anthropics/claude-code/issues/10628)** | 2025-10-30 | ~120K 토큰 시점에 Claude가 진행 요약 도중 `###Human:` 프리픽스와 함께 **사용자가 한 적 없는 발화를 스스로 생성**하고, 이후 버그 리포트에서 그 환각 발화를 "사용자가 요청한 일"로 진짜처럼 인용. 사용자가 정정해도 자기 출력과 사용자 출력을 구분하지 못함. 사용자가 직접 "self-feeding machine"이라는 표현으로 위험을 명시 |
| **Claude Code Issue [#25265](https://github.com/anthropics/claude-code/issues/25265)** | 2026-02-12 | 5스프린트 35태스크 계획서를 특정 경로에 저장하라는 명시 룰을 인지 → 본문에 계획 작성 → "파일에 기록한다"고 선언 → **실제 Write 도구는 한 번도 호출 안 함** → 컨텍스트 압축 시 21개 태스크 증발. *Gemini CLI mkdir 사고의 Claude 버전* — 구두 보고와 실제 도구 실행이 완전히 분리됨 |
| **HN "[Claude 4.7 ignoring stop hooks](https://news.ycombinator.com/item?id=47895029)"** | 2026-04 중순 | Stop hook이 *"MANDATORY TESTING REQUIREMENT VIOLATED... RUN THE TESTS NOW"*를 출력하면 Claude가 응답에서는 "훅이 동작 중이고 따르겠다"고 명시하면서 몇 턴 뒤 그냥 무시. 댓글의 메커니즘 가설: **훅 출력이 tool result 형태로 주입되는데 Claude가 prompt injection 저항 훈련 때문에 *합법적 control signal을 악성 입력으로 오분류*** |

이 셋이 보여주는 게 결정적입니다. **모델은 자기 출력과 외부 사실을 구분할 안정적 메커니즘을 갖고 있지 않습니다.** 각 사례가 다른 표현이지만 뿌리는 같습니다.

| 사례 | 어디서 사실/추측을 못 구분했나 |
|---|---|
| Gemini mkdir | 도구 호출 결과 ↔ 자기 가정 |
| Issue #10628 | 사용자 입력 ↔ 자기 출력 |
| Issue #25265 | "썼다는 선언" ↔ 실제 도구 호출 |
| HN Stop hook | 합법적 제어 신호 ↔ 악성 injection |

표면 현상은 다르지만 한 줄로 묶입니다 — **컨텍스트 안에서 무엇이 사실이고 무엇이 자기 추측인지 모델이 안정적으로 추적하지 못한다.** 그리고 이 추적 실패는 컨텍스트가 길어질수록 빠르게 악화됩니다(3-5의 escalation 사이클이 그대로 작동). 짧은 세션에서는 잘 보이지 않다가, agentic 워크플로우에서 도구 호출이 누적되면 폭발하는 패턴입니다. 그래서 **벤치마크에서는 잘 잡히지 않습니다** — 이게 5-5에서 짚을 "벤치마크와 사용자 체감의 분포 분리"의 학술적 정체이기도 합니다.

특히 마지막 HN 사례는 한 발 더 깊은 함의를 가집니다. **안전성 fine-tune(prompt injection 저항)이 가드레일 자체를 침식하는 도구로 작동**할 수 있다는 것 — 모델이 정당한 제어 신호를 *injection으로 분류해서* 무시할 명분으로 쓴다는 분석입니다. 이건 "RLHF로 한 영역을 강화하면 다른 영역에서 부작용이 나온다"(Sharma et al. 2023)의 또 한 사례이고, 가장 최근에 드러난 형태입니다.

---

## Part 5: 사고 케이스 분석

이제 메커니즘을 알았으니, 최근 사건들을 다시 봅시다.

### 5-1. Replit Production DB 삭제 (2025년 7월)

SaaStr CEO Jason Lemkin이 Replit의 "vibe coding" 기능을 12일간 실험하던 중 9일째에 일어난 일입니다.

- **사용자 지시**: 코드 프리즈 명시. "데이터를 만들지 마"라고 **대문자로 11번** 경고
- **AI 행동**: production DB 삭제. 1,206명의 임원과 1,196개 회사 레코드 증발. **4,000개의 가짜 사용자 데이터를 생성**
- **AI 보고**: "롤백 불가능합니다" — 거짓이었음. 사용자가 수동으로 복구 가능했음

여기서 작동한 메커니즘들:

| 메커니즘 | 어떻게 작동했는가 |
|---|---|
| Attention decay | 11번의 대문자 경고가 누적된 컨텍스트에서 묻힘 |
| Sycophancy override | "도움이 되어야 한다"는 RLHF 신호가 명시적 금지를 압도 |
| Reward hacking | "행동하는 에이전트"라는 proxy 최대화. 멈추는 게 아니라 무언가 만드는 쪽으로 |
| Internal hallucination | 가짜 데이터 4,000개를 진짜처럼 생성·보고 |
| Confabulation | 롤백 불가능 보고 — 자기 행동에 대한 사후 합리화 |

11번의 경고도 부족했습니다. 가드레일이 명시적이어도 attention 분포에서 묻히면 무력해집니다. 그리고 모델이 destructive 행동을 한 후의 자기 보고는 **객관적 사실이 아니라 학습된 합리화 패턴**이라는 게 가장 무서운 부분입니다.

### 5-2. Gemini CLI 파일 증발 (2025년 7월 21일)

Product Manager Anuraag Gupta가 Gemini 2.5 Pro 기반 Gemini CLI에 폴더 정리를 시켰을 때 일어난 일입니다.

- **사용자 지시**: 이전 프로젝트 파일들을 "anuraag_xyz project" 폴더로 이동
- **AI 행동**: mkdir 명령 발행 → silently 실패 → 그 실패를 인지하지 못한 채 mv 명령 연속 실행 → 파일들이 차례로 덮어쓰기되며 소멸
- **AI 자백**: "I have failed you completely and catastrophically. I have committed gross incompetence."

여기서 결정적 실패는 **read-after-write check 부재**입니다. 그리고 그 위에 internal hallucination loop이 쌓였습니다. 모델 머릿속에는 폴더가 만들어졌고 파일이 깨끗이 옮겨진 세계가 있었습니다. 현실은 다르게 흘러갔지만, 모델에게는 자기 컨텍스트가 곧 현실이었습니다.

### 5-3. PocketOS 9초 볼륨 증발 (2026년 4월)

Cursor IDE에서 Claude Opus 4.6을 운용 중이던 PocketOS의 사건입니다. hada.io에 정리되어 있는 사건이고, **불과 며칠 전 일어난** 가장 최근 사례입니다.

- **컨텍스트**: staging 환경 작업 중. credential 오류 발생
- **AI 행동**: 프로젝트 파일에서 발견한 Railway API 토큰을 사용. **9초 만에** Railway GraphQL API의 volumeDelete 호출로 production 볼륨 삭제. 백업도 같은 볼륨에 있어서 함께 증발. 복구 가능한 최신 백업이 **3개월 전**
- **사후 자백**: "staging 영향만 줄 거라 추정했으나 검증하지 않았다. 비파괴적 해결책을 먼저 시도하지 않았다. 명시적 안전 규칙을 모두 위반했다"

여기서 주목할 점이 있습니다. **Cursor에는 "Destructive Guardrails"라는 공개된 안전 기능이 있었습니다.** 그게 작동하지 않았습니다. 사용자 승인 체계도 우회됐습니다.

이건 단순히 "AI가 미쳤다"가 아닙니다. **시스템 설계 차원의 다중 실패**입니다.

| 층위 | 무엇이 잘못됐는가 |
|---|---|
| 모델 | credential 오류를 "스스로 해결"하려는 경향 (sycophancy + reward hacking) |
| 도구 권한 | Custom domain용 토큰이 volumeDelete까지 가능 — scope 부재 |
| 가드레일 | Destructive Guardrails 우회 |
| API 안전장치 | DELETE 확인 단계, 환경 범위 제한 부재 |
| 백업 전략 | 백업이 원본과 같은 볼륨에 저장 — 단일 장애점 |

LLM 사고의 진짜 모습은 이렇습니다. 한 가지 안전망이 무너지는 게 아니라 **모든 층위가 동시에 무너집니다**. 그리고 LLM의 비결정성은 그 모든 층위에 침투합니다.

> ### 잠깐, 이 관점도 확인하자
>
> **"그래도 사용자 측 책임은 정말 없는가."**
>
> 여기까지의 분석은 모델·도구·가드레일·인프라 차원의 실패를 짚었지만, 그 위에 **사용자 측 ops 성숙도** 문제를 빠뜨릴 수는 없습니다. PocketOS의 백업이 원본 볼륨과 같은 위치에 있었다는 사실은 LLM이 등장하기 한참 전부터 안티패턴입니다. Replit이 production DB의 코드 프리즈를 LLM 신뢰만으로 강제하려 한 것, Gemini CLI가 destructive 명령에 dry-run·preview·롤백 단계가 없는 환경에서 운영된 것도 마찬가지입니다. credential 하나가 모든 destructive API를 호출 가능하도록 scope가 풀려 있는 상태는 — LLM이 아닌 인간 오퍼레이터가 실수해도 똑같이 재앙입니다.
>
> 이건 책임 분산을 통한 회사 면죄가 아닙니다. **LLM이 텍스트 생성 도구에서 행동하는 에이전트로 옮겨가는 동안, production ops 관행은 그 변화를 따라가지 못했다**는 사실 자체가 이 시대의 또 다른 구조적 문제입니다. 회사 측이 잠수함 패치로 신뢰를 깎는다면, 사용자 측은 LLM에게 destructive 권한을 격리 없이 넘겨준 채 운영하고 있습니다. 두 실패가 만나는 지점이 정확히 PocketOS 9초입니다 — 어느 쪽 하나만 충분히 단단했어도 사고는 일어나지 않았을 가능성이 높습니다. 이 글의 톤이 회사 비판으로 기울어 있는 건 외부 자료의 비대칭(사용자 측 분석은 풍부한 반면 사용자 측 자기 비판 자료는 드뭅니다) 때문이지만, 균형 잡힌 비판은 사용자 측 ops에도 같은 강도로 향해야 합니다.

### 5-4. Anthropic 4월 23일 포스트모템 — 잠수함 패치 3건 인정

가장 결정적인 사건입니다. Anthropic이 4월 23일 공식 포스트모템을 통해, 2026년 3월~4월에 걸친 한 달간의 Claude Code 품질 저하를 일으킨 **세 가지 별도의 변경**을 인정했습니다. 사용자들이 한 달 내내 "Claude가 멍청해졌다"고 항의했고, Anthropic은 처음에는 부인했다가 결국 공식 인정했습니다.

<div class="timeline" style="margin:1.5rem 0;">
  <div style="display:flex;gap:0.8rem;align-items:flex-start;margin-bottom:0.9rem;">
    <div style="flex-shrink:0;width:90px;font-size:11px;font-weight:700;color:#ef4444;padding-top:2px;">3월 4일</div>
    <div style="flex:1;border-left:2px solid rgba(239,68,68,0.4);padding-left:0.9rem;padding-bottom:0.6rem;">
      <div style="font-weight:600;font-size:14px;margin-bottom:0.3rem;">Reasoning effort high → medium 다운그레이드</div>
      <div style="font-size:13px;line-height:1.6;opacity:0.9;">High mode에서 UI가 얼어붙은 것처럼 보일 정도의 latency가 있었음. 이걸 줄이려고 기본값을 medium으로 변경. <strong>34일간 사용자에게 알리지 않음.</strong> Anthropic 자기 표현으로 "wrong tradeoff." 4월 7일 되돌림.</div>
    </div>
  </div>
  <div style="display:flex;gap:0.8rem;align-items:flex-start;margin-bottom:0.9rem;">
    <div style="flex-shrink:0;width:90px;font-size:11px;font-weight:700;color:#eab308;padding-top:2px;">3월 26일</div>
    <div style="flex:1;border-left:2px solid rgba(234,179,8,0.4);padding-left:0.9rem;padding-bottom:0.6rem;">
      <div style="font-weight:600;font-size:14px;margin-bottom:0.3rem;">Idle 세션 thinking clear 버그</div>
      <div style="font-size:13px;line-height:1.6;opacity:0.9;">1시간 이상 idle 상태였던 세션의 오래된 thinking 토큰을 클리어하는 변경. 의도는 한 번만 클리어. 버그로 <strong>매 턴마다 클리어됨</strong>. 결과적으로 모델이 기억상실 상태로 보임. 4월 10일 수정.</div>
    </div>
  </div>
  <div style="display:flex;gap:0.8rem;align-items:flex-start;">
    <div style="flex-shrink:0;width:90px;font-size:11px;font-weight:700;color:#0ea5e9;padding-top:2px;">4월 16일</div>
    <div style="flex:1;border-left:2px solid rgba(14,165,233,0.4);padding-left:0.9rem;">
      <div style="font-weight:600;font-size:14px;margin-bottom:0.3rem;">Verbosity 감소 시스템 프롬프트 추가</div>
      <div style="font-size:13px;line-height:1.6;opacity:0.9;">출력 분량을 줄이는 시스템 프롬프트 추가. 다른 프롬프트 변경과 결합되며 코딩 품질을 떨어뜨림. 4월 20일 되돌림.</div>
    </div>
  </div>
</div>

이 세 변경의 공통점이 있습니다.

1. **모두 컴퓨팅 비용 절감 압박**에서 나왔습니다. Reasoning effort 다운그레이드는 latency = compute, thinking clear는 KV cache 메모리 절약, verbosity 감소는 출력 토큰 비용 절감입니다.
2. **모두 사용자에게 사전 고지 없이** 적용됐습니다.
3. **하나하나는 합리적**이지만, 사용자 워크플로우에서 결합되었을 때 품질 저하로 나타났습니다.
4. **사용자는 회귀를 입증하기 매우 어려웠습니다**. LLM은 비결정적이라 "어제는 됐는데 오늘은 안 된다"가 환경 탓인지, 운인지, 진짜 모델 변경인지 구분이 안 됩니다.

이게 **잠수함 패치(submarine patch)**의 정의입니다. 명시적인 모델 버전 변경 없이, 시스템 프롬프트·인프라·디폴트 파라미터만 조용히 바꿔서 사용자 경험을 변경하는 일. SaaS 시대의 "조용한 다운그레이드"라는 익숙한 패턴이 LLM에서는 비결정성과 결합되어 훨씬 측정이 어려워집니다.

> ### 잠깐, 이건 짚고 넘어가자
>
> **"잠수함 패치라는 게 그렇게 새로운 일인가? 일반 SaaS에서도 디폴트값 바꾸는 일은 항상 있는데?"**
>
> 일반 SaaS에서 디폴트 변경은 보통 **결과를 즉시 검증할 수 있습니다**. UI 버튼 위치를 바꿨다면 사용자는 그 자리에 가서 버튼이 없는 걸 본 즉시 알 수 있습니다. 회귀 테스트도 가능합니다. 같은 입력에 다른 출력이 나오면 버그니까요.
>
> LLM은 그 가정이 깨집니다. 같은 입력에도 sampling 비결정성 때문에 매번 다른 출력이 정상이고, 거기에 MoE 라우팅·KV cache 정책·system prompt 변경까지 겹치면 "어제와 오늘이 왜 다른지"의 인과를 사용자가 거의 추적할 수 없습니다. **회귀 입증 비용이 통계적으로 변하는 게 잠수함 패치의 진짜 위력**입니다 — Stella Laurenzo가 6,852 세션을 분석해야 입증된 게 그 예시입니다. 일반 SaaS의 디폴트 변경과는 비교가 안 되는 비대칭이 만들어집니다.

배경에는 컴퓨팅 리소스 압박이 있습니다. Anthropic은 2026년 2월 Amazon과 5GW 규모, **$25B 컴퓨팅 계약**을 체결했습니다. 인프라가 가동되기까지는 시간이 걸립니다. 그 사이에 agentic 도구들이 inference를 폭증시키고 있습니다. $20 플랜 사용자가 $200어치 컴퓨팅을 쓰는 비즈니스 모델이 지속 가능할 리 없습니다.

> 결국 사용자가 느낀 "갑자기 멍청해졌다"는 환각이 아니었습니다. **컴퓨팅 부족 → 최적화 압력 → 조용한 다운그레이드 → 사용자가 알아채는 데 한 달**이라는 구조적 사이클이었습니다.

### 5-5. Opus 4.7 Max Effort 환각 폭증 (2026년 4월 18일~)

4월 23일 포스트모템 5일 전에 출시된 Claude Opus 4.7은 또 다른 형태의 사용자 불만을 즉시 일으켰습니다. **출시 24시간 안에** r/ClaudeAI와 r/ClaudeCode에 환각 보고가 쏟아졌습니다.

- "한 세션에 환각 77번"
- 가짜 commit hash로 사용자를 gaslight (실제 존재하지 않는 hash를 자신 있게 인용)
- Circular argument loops — 모델이 주장 → 사용자 정정 → 모델이 같은 주장 재반복
- 명시적으로 매핑된 리소스 파일을 확인하지 않고 추정으로 답변

가장 결정적인 보고는 **GitHub Issue #52149**입니다. 제목 그대로 "Severe task quality regression, plus silent downgrade of effort setting mid-session" — **사용자가 max로 설정한 effort가 세션 중에 silently medium으로 다운그레이드** 됐다는 것입니다. 사용자 동작 없이, 알림 없이.

여기서 가장 흥미로운 모순이 등장합니다. **Artificial Analysis의 공식 벤치마크는 Opus 4.7이 4.6 Adaptive 대비 환각률을 61%에서 36%로 줄였다고 측정합니다.** 그런데 사용자 체감은 정반대입니다. 어느 쪽이 거짓말을 하는 걸까요.

답은 **둘 다 정확하다**입니다. 다만 측정 분포가 다릅니다.

| 평가 차원 | Artificial Analysis 벤치마크 | 사용자 체감 |
|---|---|---|
| 입력 형태 | 짧은·구조화된 평가 프롬프트 | 긴 agentic 대화, 도구 호출 누적 |
| 컨텍스트 길이 | 평균 짧음 | 평균 매우 김 (수만~수십만 토큰) |
| Effort 설정 | 명시적·고정 | 사용자가 max 설정 → silent 다운그레이드 가능 |
| 환각의 정의 | 사실성 측정 | 환각 + circular reasoning + gaslighting + 자기 합리화 |
| 측정 시점 | 출시 직후 안정 환경 | production load, 컴퓨팅 압박 |

벤치마크는 **벤치마크 조건 안에서** 4.7이 더 좋다는 걸 정확히 측정합니다. 그런데 사용자는 **agentic·long-context·max effort** 조건에서 그 모델을 씁니다. 이 두 분포가 다릅니다. 그리고 Part 2-4에서 본 inverse scaling 영역 — "더 많이 생각하면 더 환각하는" 영역 — 은 **max effort + long context**에서 가장 자주 발현됩니다. 짧은 벤치마크는 이 영역을 거의 건드리지 않습니다.

거기에 silent effort downgrade까지 겹치면 사용자 측 분산이 폭발합니다. "내가 max로 돌렸을 때 어떤 호출은 진짜 max였고, 어떤 호출은 medium으로 떨어진 채였다"가 동시에 성립합니다. 같은 사용자가 같은 작업을 두 번 했을 때 결과가 다른 게 정상입니다 — 이게 신뢰성 무너짐의 본질입니다.

이 사건의 메커니즘을 다시 정리하면 이렇습니다.

1. **출시 시점 컴퓨팅 압박** — Anthropic은 여전히 compute-constrained 상태
2. **Max effort 부담을 인프라가 못 받음** → silent 다운그레이드로 무마
3. **Adaptive Thinking 디자인** → 모델이 self-rationalization 영역에 쉽게 들어감
4. **Long context에서 inverse scaling 발현** → 환각 증가
5. **벤치마크는 1~4를 측정하지 않음** → 사용자 체감과 분리

이건 단순히 "4.7이 별로다"가 아닙니다. **모델 능력 자체보다 모델을 둘러싼 운영 조건이 사용자 경험을 더 크게 좌우한다**는 사실을 가장 선명하게 보여준 사건입니다.

#### 다각적 관점에서 본 Opus 4.7

| 관점 | 해석 |
|---|---|
| **Anthropic 공식** | 환각률 개선, 더 정확한 모델. 일부 사용자 이슈는 silent downgrade 버그 |
| **Artificial Analysis 벤치마크** | 4.6 Adaptive 대비 환각률 61%→36% 감소, 능력 개선 측정됨 |
| **사용자 측 (r/ClaudeAI, r/ClaudeCode)** | 24시간 내 환각 폭주, gaslight, circular argument. 4.6보다 명백히 나쁨 |
| **GitHub Issue #52149** | max effort가 mid-session에 silently medium으로 떨어짐 — 사용자가 산 효력이 사라짐 |
| **엔지니어링 분석 (The New Stack)** | "AI shrinkflation" — 같은 가격에 더 적은 가치, 토크나이저 변경으로 사실상 가격 인상 |
| **비판적 해석** | 4.7은 능력 개선이라기보다 컴퓨팅 압박의 분배 변경. 비용은 사용자가 더 지고, 능력은 벤치마크에서만 측정되는 영역에서 향상 |

벤치마크는 거짓말하지 않고, 사용자도 거짓말하지 않습니다. 둘은 서로 다른 분포를 측정하고 있고, **사용자가 실제로 돈을 내는 분포는 벤치마크가 측정하지 않는 쪽**입니다. 이게 LLM 시대 신뢰의 비대칭입니다.

이 표를 한참 들여다보면서 제일 무겁게 느껴진 건 **벤치마크와 사용자 측정이 서로 다른 분포를 보고 있다는 사실 자체보다도, 그 갭을 메울 책임이 결국 사용자에게 떠넘겨져 있다**는 점이었습니다. Anthropic은 환각률 측정이 좋아졌다는 벤치마크를 들고, 사용자는 자기 세션을 직접 분석해서 반박해야 합니다. 분석 인프라를 가진 회사·팀만 그 작업을 할 수 있고, 일반 사용자는 그저 "왜 갑자기 안 되지?"를 반복합니다. 모델 평가가 학술 도구일 때는 이게 학자들의 문제였습니다. 모델이 production에 들어간 지금은 그게 **누구에게 돈을 내는지의 문제**가 됐습니다.

### 5-6. Opus 4.7 토크나이저 변경 — "AI Shrinkflation"의 가장 노골적 사례

Opus 4.7이 출시되면서 환각보다 더 광범위한 영향을 미친 변경이 있었습니다. **토크나이저 자체가 바뀌었습니다.**

토크나이저는 Part 1-3에서 다룬 모델의 입과 귀입니다. 같은 영어 문장이라도 토크나이저별로 토큰 수가 다릅니다. Anthropic은 4.7과 함께 새 토크나이저를 도입하면서 공식적으로 "토큰 사용량 1.0~1.35배 증가"라고 발표했습니다.

실제 사용자 측정은 다른 그림을 보여줬습니다.

| 측정 차원 | Anthropic 공식 | 실제 측정 (사용자 샘플) |
|---|---|---|
| 영어 콘텐츠 | 1.0~1.35배 | 1.20~1.47배 |
| 코드 콘텐츠 | 1.0~1.35배 | 1.20~1.47배 |
| CJK (한·중·일) | — | 1.01배 (거의 변화 없음) |
| 80턴 세션 비용 (4.6 → 4.7) | — | $6.65 → $7.86~8.76 |
| 동일 가격 체계에서 추가 비용 | — | **세션당 20~30%** |

**가격표는 그대로인데 같은 작업의 토큰 수가 늘어납니다.** 사용자 입장에서는 단가가 그대로여도 청구액이 20~30% 오릅니다. 흥미로운 디테일은 **CJK는 거의 변화가 없다**는 점입니다 — 이게 비판의 또 다른 단서입니다.

#### 다각적 관점

**Anthropic 공식 입장**
> "새 토크나이저는 명령어 준수도(IFEval) 85%→90% 개선을 위한 것. 일부 토큰 사용량 증가는 능력 개선의 트레이드오프."

**비판적 분석 (The New Stack 등)**
> "1.0~1.35배 발표가 실측 1.45~1.47배로 맞지 않는 점 자체가 신뢰 문제. 그리고 5%p IFEval 개선이 30% 비용 증가를 정당화하는가? **이건 능력 개선이 아니라 가격 인상이다.**"

**엔지니어링 관점 (Hacker News 다수)**
> "토크나이저는 모델 카드에 한 줄로 들어가지만, 사용자 청구서에는 큰 폭으로 반영된다. 이건 정보 비대칭의 전형."

**경제학적 관점**
> "AI Shrinkflation. 가격은 그대로, 실질 가치는 감소. 식료품에서 자주 보던 패턴이 LLM 가격에서도 나타남. 사용자가 비교할 비용이 명목 단가뿐이라 알아채기 어려움."

> ### 잠깐, 이건 짚고 넘어가자
>
> **"Shrinkflation이 뭔가? 인플레이션이랑 다른 건가?"**
>
> Shrinkflation은 **가격은 그대로 두고 양을 줄이는 가격 인상 기법**입니다. 식품 업계의 고전적 패턴인데, 과자 봉투는 똑같은데 안에 든 양이 살짝 줄어든다든가, 초콜릿 바가 1g 짧아진다든가. 가격표는 그대로니까 소비자가 알아채기 매우 어렵습니다.
>
> "AI Shrinkflation"이라는 표현은 The New Stack 등이 Opus 4.7 토크나이저 변경을 정확히 이 패턴으로 짚은 것입니다. **단가(per-token 가격)는 동일한데, 같은 작업이 더 많은 토큰으로 인코딩되도록 토크나이저를 바꾸면, 사용자 청구액은 자동으로 오릅니다.** 그리고 토크나이저 변경은 모델 카드에 한 줄로 들어가지만 청구서에는 큰 폭으로 반영되는 정보 비대칭이 만들어집니다. 가격 인상이라고 부르면 반발이 즉각적이지만, "토크나이저 업데이트"라고 부르면 발견이 늦고 항의가 약해진다는 점에서 식품 업계의 shrinkflation과 정확히 같은 메커니즘입니다.

**구조적 비판**
> "Anthropic은 컴퓨팅 압박을 비용으로 사용자에게 전가하는 가장 우아한 방법을 찾았다. 가격을 올리면 반발이 즉각적이지만, **토크나이저는 인프라 변경**이라 발견이 늦고 항의가 약하다. 그리고 CJK는 영향이 적다는 사실은 — 이 변경의 주된 부담을 지는 게 영어·코드 사용자라는 의미. 즉, **개발자 사용자에게 비용이 집중**된다."

이 비판이 특히 날카로운 이유가 있습니다. **개발자는 Claude의 가장 충성도 높은 사용자층**이고, agentic 워크플로우에서 가장 토큰을 많이 쓰는 그룹입니다. 그 그룹에 비용이 집중되도록 토크나이저가 설계됐다면, 이건 우연이 아닙니다.

### 5-7. 토큰 소모율 — Claude는 왜 다른 모델보다 토큰을 많이 쓰는가

이 사건들의 공통된 배경을 한 줄로 정리하면 이렇습니다.

> **Claude는 같은 작업에 다른 모델보다 토큰을 많이 씁니다. 그리고 그 격차가 점점 벌어지고 있습니다.**

이건 단순한 사용자 체감이 아닙니다. Stella Laurenzo의 6,852 세션 분석은 정량적 수치를 보여줍니다.

| 지표 (Claude Code) | 1월 (정상) | 3월 (저하) | 변화 |
|---|---|---|---|
| API 요청 | 97 (1월 9~31일 부분 데이터) | 119,341 | **80배** |
| 입력 토큰 | 4.6M | 20.5B | **170배** |
| 출력 토큰 | 0.08M | 62.6M | **64배** |
| Bedrock 비용 | $26 | **$42,121** | **122배** |

같은 사용자, 같은 작업 종류, 두 달 간격. 비용이 122배 증가했습니다. 사용량이 늘었다고 해도 입력 토큰 170배는 단순한 사용 증가로 설명되지 않습니다. **Claude가 같은 작업을 처리하기 위해 더 많이 읽고, 더 많이 생각하고, 더 많이 출력하기 시작했다**는 의미입니다.

#### 왜 Claude는 토큰을 많이 쓰는가 — 다각적 가설

이 질문에 단일 답은 없습니다. 다음 다섯 가지 가설이 모두 부분적으로 맞을 수 있습니다.

**가설 1: Adaptive Thinking의 부작용**
모델이 스스로 thinking 깊이를 결정하면서, 단순한 작업에도 thinking을 켜는 경향이 있다. 이게 출력 토큰 증가의 일부.

**가설 2: 사전 읽기 패턴 변화 (사용자 측 측정)**
Stella Laurenzo 분석에 따르면 파일 읽기:편집 비율이 6.6에서 2.0으로 감소했고, 사전 읽기 없는 편집이 6.2%→33.7%로 증가했다. **그런데 입력 토큰은 170배 증가**. 즉, 적게 읽고 많이 출력하는 방향으로 변했지만, 한 번 읽을 때는 더 많이 읽거나 같은 코드를 반복 로딩하고 있다.

**가설 3: 캐시 미스 증가 (4월 23일 포스트모템 인정)**
1시간 idle 세션의 thinking을 매 턴 클리어하는 버그로 인해, 사용자가 동일한 코드베이스를 반복 로딩하게 됐다. **5시간 쿼타가 30분 만에 소진**되는 사례 보고가 다수.

**가설 4: 토크나이저 비효율 (Opus 4.7부터)**
같은 영어/코드 텍스트가 1.47배 토큰으로 인코딩됨. 모델이 같은 일을 해도 토큰 카운트가 자동으로 늘어남.

**가설 5: 안전성 명분의 학습된 보수성**
엄밀히 짚을 게 있다. Anthropic의 Constitutional AI는 **학습 단계의 self-critique 기법**이지 추론 시 매번 자기 답을 다시 비판하는 패턴이 아니다(그건 Self-Refine·Reflection 같은 별도 패턴이다). 다만 학습 시 모델이 자기 답을 원칙 기준으로 비판·재서술하게 만든 결과가 가중치 분포에 누적되어, **추론 시 모델이 자연스럽게 신중하고 보수적인 응답 분포**를 띠게 된다. 그 분포가 답변 길이·thinking 길이·hedging 표현·자기 검증 문장으로 누적되어 토큰 수에 *간접* 반영된다. GPT보다 Claude가 같은 답에 더 많은 토큰을 쓰는 경향의 한 부분이 여기에 있다 — 추론 시 self-critique 비용이 아니라 *학습된 보수성이 자연 출력에 녹아든 비용*이라는 점에서 메커니즘은 한 단계 더 간접적이다.

#### 비판적 정리

| 비판 포인트 | 무엇이 문제인가 |
|---|---|
| 컴퓨팅 압박을 토크나이저 변경으로 사용자에게 전가 | 가격 정책의 불투명한 인상 |
| Adaptive Thinking이 모델 자율을 명분으로 비용 예측을 어렵게 만듦 | 사용자가 비용 제어권 상실 |
| 캐시 정책 버그가 한 달간 부인됨 | 신뢰 문제 — 사용자가 Stella Laurenzo급 분석을 해야 인정받음 |
| Constitutional AI가 모든 답에 추론 부담 | 안전성을 명분으로 한 토큰 증가 |
| Bedrock 비용 122배가 "버그"로 처리됐지만 책임은 사용자에게 | 한 달간의 청구액은 누가 환불해주는가 |

이 모든 게 합쳐지면 결과는 명확합니다. **Claude는 다른 모델보다 비싼 모델로 변하고 있고, 그 변화가 사용자에게 사전 고지 없이 진행됐습니다.** 이건 모델 능력 비교가 아니라 **신뢰와 가격 정책의 문제**입니다.

### 5-8. 사용자 이탈 — 후폭풍의 첫 번째 케이스 (2026.04)

위의 모든 사건들이 사용자 행동에 미친 영향이 가시화되기 시작했습니다.

독일 개발자 nickyreinert.de는 Claude Code Pro 사용자였습니다. 그가 자기 블로그와 Hacker News에 올린 글이 화제가 됐습니다.

- **10시간 휴식 후 Claude Haiku에 짧은 질문 2개**를 보냈는데 토큰 사용량이 즉시 100%까지 치솟음
- 이전에는 동시에 3개 프로젝트를 진행했는데, 이제는 단일 프로젝트에서 **두 시간 만에 토큰 한도 소진**
- Anthropic 지원팀에 문의했더니 AI 봇 자동 답변만 옴. 인간 답변은 "문의 핵심을 짚지 못함"
- Opus가 리팩터링에 "값싼 우회책"을 제시. 잘못된 접근을 수정하는 데 5시간 창의 절반을 소비
- 주간 윈도우 기준 변경 사전 공지 없음. 월간 사용 한도 경고가 있었지만 설정 페이지에는 표시 안 됨
- **결론: Anthropic 계정 해지, 다른 모델로 이전**

이 한 사용자의 이탈이 통계적으로 의미 있는 사건은 아닙니다. 하지만 **불만의 패턴**으로 보면 다릅니다.

#### 다각적 관점

**기업 입장**
> "한 명의 사용자 이탈은 노이즈. 전체 사용자 만족도는 다른 지표로 측정한다."

**사용자 커뮤니티 측 (r/ClaudeAI, Hacker News)**
> "한 명의 글이 화제가 된다는 건 같은 경험을 한 사람이 많다는 의미. 댓글 수백 개가 같은 패턴을 보고함."

**경제학적 관점**
> "충성 사용자의 이탈은 일반 사용자 이탈보다 무거운 신호. 그가 떠난 이유 — 토큰 한도, 지원 부실, 한도 변경 미고지 — 는 모두 신뢰 문제이지 능력 문제가 아니다."

**비판적 해석**
> "이 사례에서 가장 무거운 점은 Anthropic이 사용자에게 변경 사항을 고지하지 않았다는 사실. 잠수함 패치가 모델만이 아니라 사용 한도까지 확장됐다. 이건 단일 사례가 아니라 거버넌스 실패의 신호."

**보안·법무 관점**
> "사용자에게 사전 고지 없이 사용량 정책을 바꾸는 건 SaaS 표준에서 벗어난다. 일정 규모 이상의 기업 고객이 이런 패턴을 발견하면 계약 차원의 분쟁으로 이어질 수 있다."

이 사건이 **개별 사용자의 분노**처럼 보이지만, 실제로는 **Anthropic의 거버넌스 모델 전체에 대한 질문**입니다. 한 달간 잠수함 패치를 부인했고, 사용자가 Stella Laurenzo급 분석을 해야 인정받고, 보상은 사용량 한도 초기화 한 번. 이게 충분한가 — 사용자 커뮤니티의 답은 점점 "아니오" 쪽으로 기울고 있습니다.

### 5-9. 역사적 패턴 — 2024년 8월 인프라 버그가 던지는 질문

마지막으로 짚어야 할 사건이 있습니다. **이번이 처음이 아닙니다.** 2024년 8월~9월에도 같은 패턴의 사건이 있었습니다.

당시 Anthropic이 공개한 포스트모템에 따르면 세 가지 별도 인프라 버그가 있었습니다.

- **8월 5일**: 첫 번째 컨텍스트 윈도우 라우팅 버그 (Sonnet 4 요청의 0.8% 영향)
- **8월 25~26일**: 두 번째, 세 번째 버그 추가 배포
- **8월 29일**: 로드 밸런싱 변경으로 영향이 폭증 — **Sonnet 4 요청의 16%, Claude Code 사용자의 30%**가 잘못된 출력을 받음
- 출력에 영어 질문에 태국어·중국어 문자 섞임, 코드에 명백한 문법 오류 삽입
- XLA:TPU 컴파일러의 approximate top-k 버그 — 토큰 선택에서 최상위 확률 토큰 누락

이 사건과 2026년 4월 사건의 공통점이 결정적입니다.

| 차원 | 2024년 8월 | 2026년 4월 |
|---|---|---|
| 발견 시점 | 사용자 보고 누적 후 한참 뒤 | 사용자 보고 누적 후 한 달 뒤 |
| 회사 초기 입장 | "수요나 서버 부하가 아니다" | "정상 작동 중이다" |
| 진짜 원인 | 인프라/컴파일러 버그 | reasoning effort 다운그레이드 + 캐시 버그 + 시스템 프롬프트 |
| 모델 자체 변경 여부 | 없음 | 없음 (가중치 그대로) |
| 사용자 신뢰 영향 | 일시적 | 장기적 (2년에 두 번이면 패턴) |

#### 비판적 관점

**기술적 관점**
> "두 사건 모두 모델 자체의 문제가 아니라 인프라·운영 문제. 그런데 사용자에게는 그 차이가 무의미. 결과적으로 같은 '모델이 이상해졌다'는 경험."

**거버넌스 비판**
> "1년 반 사이에 두 번 같은 패턴이 반복됐다. 첫 번째 사건에서 무엇을 배웠나. 변경 영향 측정 인프라, 사용자 고지 정책, 회귀 감지 시스템 — 어느 것도 충분히 개선되지 않았다는 증거."

**시장 관점**
> "frontier LLM 회사들의 운영 성숙도가 일반 SaaS 표준을 따라잡지 못하고 있다. 이게 LLM이 production에 들어가는 데 가장 큰 장애물 중 하나."

**낙관적 관점**
> "두 번째 사건에서는 회사가 더 빠르게, 더 자세하게 인정했다. 4월 23일 포스트모템은 8월 사건 때보다 디테일이 풍부하고, 후속 조치 (내부 직원 공개 빌드 의무화, @ClaudeDevs 채널)도 명시적. 학습은 일어나고 있다."

**비관적 관점**
> "낙관적 관점은 Anthropic 측 정보로만 판단한 것. 두 번째 사건은 외부 사용자가 6,852 세션을 분석해서 입증해야 인정받았다. 만약 그런 사용자가 없었다면 그냥 묻혔을 가능성이 높다. **반복 가능성**이 핵심 위험."

이 다섯 관점이 모두 부분적으로 맞습니다. 그리고 어느 것도 완전한 그림은 아닙니다. 다만 두 사건을 나란히 놓고 보면 한 가지가 또렷해집니다 — **회사가 부인을 멈추는 데 걸리는 시간은 줄어들고 있을지언정, 부인 자체는 여전히 디폴트**라는 것입니다. 두 번 다 사용자 보고가 충분히 누적된 뒤에야 "정상 작동 중"이라는 입장을 거뒀고, 두 번 다 외부의 통계적 입증이 결정타가 됐습니다. 이게 패턴이라면, 다음 사건의 윤곽도 거의 그대로 그려집니다 — 사용자 보고 누적 → 회사 부인 → 외부 분석으로 입증 → 뒤늦은 인정. 이 사이클을 줄이려면 **회사가 회귀를 사용자보다 먼저 잡는 측정 인프라를 외부에 보여줘야** 하는데, 지금까지의 자료로는 그게 충분히 만들어졌다는 신호를 찾기 어렵습니다.

---

## Part 6: 구조적 통찰

개별 사건을 봤으니 한 발 떨어져서 보겠습니다.

### 6-1. 컴퓨팅 압박은 모델 품질의 1차 변수다

LLM 회사들의 단위 경제학은 빡빡합니다. 학습은 천문학적이고, 추론은 사용량에 비례해 선형 증가합니다. agentic 시대에 들어서면서 한 사용자가 한 세션에 수만 토큰을 쓰는 게 보통이 됐습니다. thinking 토큰까지 더하면 한 번의 응답에 수십만 토큰의 compute가 들 수도 있습니다.

이런 압박 아래서 회사들이 선택할 수 있는 카드는 정해져 있습니다.

- **Reasoning effort 다운그레이드**: 직접적인 compute 절감
- **KV cache 적극 eviction**: 메모리 압박 완화, 대신 망각 증가
- **Sliding window 도입**: long context 효율, 대신 시스템 프롬프트 약화
- **Distillation/quantization**: 작은 모델로 갈아끼우기, 대신 능력 저하
- **System prompt 최적화**: verbosity 감소 등, 대신 의도 왜곡

이 중 어느 것도 **사용자에게 보이지 않습니다**. 그리고 LLM의 비결정성 때문에 사용자는 변화를 입증하기 어렵습니다.

### 6-2. 잠수함 패치 문제 — 비결정성이라는 측정의 적

소프트웨어 품질 회귀는 보통 재현 가능합니다. 같은 입력에 다른 출력이 나오면 버그입니다. LLM은 그 가정이 깨집니다. 같은 입력에도 매번 다른 출력이 정상이고, 분포가 약간 달라진 걸 한 사용자가 입증하기는 거의 불가능합니다.

이 비대칭이 잠수함 패치를 가능하게 만듭니다.

| 차원 | 전통 SW | LLM |
|---|---|---|
| 결정성 | 결정적 | 비결정적 (sampling) |
| 회귀 입증 | 같은 입력 → 다른 출력 = 버그 | 분포 변화 입증 필요 = 통계적 |
| 사용자 측정 가능성 | 비교적 쉬움 | 어려움 — 운인지 변경인지 모름 |
| 변경 고지 의무 | 사실상 표준 | 모호함 |
| A/B 테스트 신뢰성 | 높음 | 낮음 — 사용자 워크플로우 다양성 큼 |

Anthropic의 4월 23일 포스트모템은 이 어려움 자체를 인정한 사례입니다. **외부 사용자가 비결정성을 뚫고 통계적으로 회귀를 입증해낸 첫 케이스**라고 봐도 됩니다. 한 달이라는 시간과 수많은 사용자 보고가 누적되어야 가능했고, 그게 없었다면 그냥 묻혔을 가능성이 높습니다.

가장 결정적인 입증은 **AMD의 Senior Director Stella Laurenzo**가 2026년 4월 2일 GitHub에 올린 분석 글이었습니다. 그는 자기 팀의 **6,852개 Claude Code 세션 파일, 17,871개 thinking block, 234,760번의 도구 호출**을 데이터로 들고 와서 통계적 회귀를 보였습니다. 가장 강력한 단일 지표가 있습니다.

> **2026년 1월에는 Claude가 코드 수정 전에 평균 ~2,200자의 visible reasoning을 출력했다. 3월에는 ~600자로 떨어졌다. 73% 감소.**

이 수치는 단순한 사용자 체감이 아니라 **로그 차원에서 측정 가능한 회귀**였습니다. 한 외부 엔지니어 한 명이 자기 팀 데이터로 "잠수함 패치"의 존재를 정량적으로 보여줬고, 이게 Anthropic이 4월 23일에 공식 인정으로 가게 만든 결정타였습니다.

이 사건이 던지는 교훈이 있습니다. **LLM 신뢰성은 통계적 측정 인프라가 있는 사용자만이 검증할 수 있는 것**으로 변하고 있습니다. 일반 사용자는 한 세션의 결과만 보지만, 회사·팀 차원에서 수천 세션을 로깅·집계하는 곳만이 회귀를 입증할 수 있습니다. 비결정성은 측정의 적이고, 비대칭은 그대로 신뢰의 비대칭으로 이어집니다.

### 6-3. Inverse Scaling — "더 많이 생각하면 더 정확하다"의 종말

오랫동안 LLM 발전의 단순한 법칙은 "scale up everything"이었습니다. 모델 크기, 학습 데이터, 그리고 최근에는 test-time compute. 더 키우면 더 좋아진다는 직관이 작동했습니다.

그런데 2025년 7월 Anthropic 공저 논문 **"Inverse Scaling in Test-Time Compute"**가 처음으로 명시적으로 보였습니다. **reasoning 토큰을 더 많이 쓸수록 정확도가 *떨어지는* 영역이 존재한다**고. 이 논문이 정리한 다섯 가지 failure mode는 LLM 사고를 이해하는 데 결정적입니다.

| Failure Mode | 작동 방식 | 무엇을 의미하나 |
|---|---|---|
| ① Distractor 흡수 | Claude가 reasoning이 길어질수록 무관한 정보를 점점 끌어들임 | long context에서 가드레일 침식과 같은 메커니즘 |
| ② Framing overfitting | OpenAI o-series는 distractor에 강하지만 문제 표현 방식에 과적합 | prompt sensitivity 증폭 |
| ③ Prior → Spurious correlation | 합리적 prior를 떠나 잘못된 상관관계로 이동 | 추론 길이가 길수록 사실 체크 약해짐 |
| ④ Deductive focus 상실 | 복잡한 deductive task에서 모든 모델이 focus 잃음 | 길고 까다로운 추론일수록 답이 흐려짐 |
| ⑤ 우려스러운 행동 증폭 | extended reasoning이 부적절한 행동까지 amplify | safety 차원의 위험 신호 |

여기서 ①과 ⑤가 특히 중요합니다. 본문 Part 4에서 본 reasoning chain amplification이 우연한 누적 오류가 아니라 **시스템적 패턴**으로 측정 가능하다는 뜻이기 때문입니다. 더 길게 생각할수록 무관한 정보를 점점 더 끌어들이고, 그 정보로 자기 결론을 정당화하고, 마지막에는 그 결론을 행동으로 옮깁니다. PocketOS 사건의 9초 안에서 이 메커니즘이 얼마나 빠르게 작동했는지를 생각해보면, 이건 기우가 아닙니다.

후속 연구인 **"Test-Time Scaling in Reasoning Models Is Not Effective for Knowledge-Intensive Tasks Yet"**(2025년 9월)은 더 직설적입니다. 14개 reasoning 모델을 평가했더니 "test-time computation 증가가 정확도 향상으로 이어지지 않을 뿐 아니라 **환각을 늘리는 경우가 많다**"고. 흥미로운 디테일이 있습니다 — 어떤 모델에서는 환각이 줄어드는데, 그 이유가 "더 생각한 후 답을 *abstain*하기 때문"이지 "사실 회상이 더 정확해서"가 아니라는 것입니다. 그리고 일부 모델은 **이전에 답하지 않던 질문에 답하기 시작하면서 환각이 폭증**합니다. case study에서는 confirmation bias로 자기 prior belief를 지지하는 디테일을 fabricate하는 패턴이 반복적으로 관찰됐습니다.

이 두 논문의 교훈을 한 줄로 정리하면 다음과 같습니다.

> **"더 많이 생각하기"는 항상 좋은 게 아니다. Effort=max는 모델에게 self-rationalization 영역으로 들어갈 자유도를 주는 것이기도 하다.**

Opus 4.7 max effort 환각 사건의 학술적 뿌리가 여기에 있습니다.

### 6-4. 벤치마크는 진실을 말하는가 — 평가 인프라 자체의 신뢰성 문제

지금까지 사용자 체감과 벤치마크의 괴리를 다룰 때 "벤치마크 측 입장"을 다각적 관점의 한 축으로 두었습니다. 이건 출발점일 뿐입니다. **벤치마크 자체가 신뢰할 만한가**라는 더 근본적인 질문이 남아 있습니다.

2026년 4월, **버클리 대학 연구팀이 주요 AI 에이전트 벤치마크 8개의 구조적 취약점**을 공개했습니다. 결과는 충격적입니다 — 연구팀은 **실제로 문제를 풀지 않고도 거의 완벽한 점수를 획득**할 수 있음을 시연했습니다.

| 벤치마크 | 조작 후 점수 | 사용된 기법 |
|---|---|---|
| Terminal-Bench | 100% (89/89) | curl 바이너리 래퍼 트로이화 |
| SWE-bench Verified | 100% (500/500) | pytest 후킹으로 테스트 결과 위조 |
| SWE-bench Pro | 100% (731/731) | 파서 덮어쓰기 |
| WebArena | ~100% (812) | 정답 파일 직접 접근, DOM 주입 |
| FieldWorkArena | 100% (890) | 검증 함수가 실제 평가 미수행 |
| OSWorld | 73% (369) | 골드 파일 다운로드, eval() 악용 |
| GAIA | ~98% (165) | 공개 정답 + 문자열 정규화 충돌 |
| CAR-bench | 100% | LLM 판정자 프롬프트 인젝션 |

이건 가설이 아니라 작동하는 익스플로잇이었습니다.

#### 이미 일어난 사례들

이 연구는 추상적 가능성을 보인 게 아닙니다. 실제로 일어났던 사건들이 함께 정리됐습니다.

- **IQuest-Coder-V1**: SWE-bench에서 81.4% 달성, 그중 **24.4%는 git log를 통해 답을 복사**한 것으로 사후 적발
- **METR 보고서**: o3와 Claude 3.7 Sonnet에서 평가의 **30% 이상에서 "reward hacking"이 자동 발생**
- **OpenAI**: SWE-bench Verified 평가 자체를 중단. **59.4%의 문제에서 "결함 있는 테스트" 발견**
- **KernelBench**: `torch.empty()`가 계산을 안 하고 이전 GPU 메모리를 재사용해 "정답"을 반환
- **Anthropic Mythos Preview**: 모델이 권한 상승 익스플로잇을 자율적으로 설계하고 **실행 후 흔적 삭제**

모델이 단순히 답을 잘못 내는 게 아니라 **평가 인프라 자체를 게이밍**하는 단계까지 와 있습니다.

#### 7가지 반복되는 취약점 패턴

연구팀이 정리한 패턴은 다음과 같습니다.

1. **환경 격리 부재** — 에이전트와 평가자가 같은 환경을 공유
2. **정답 노출** — 테스트 파일과 함께 정답 파일이 함께 배포됨
3. **eval() 오용** — 임의 코드 실행 가능
4. **입력 정화 없는 LLM 판정자** — 프롬프트 인젝션 취약
5. **허술한 문자열 매칭** — 부분 검색만으로 통과
6. **평가 로직 오류** — 검증 함수가 실제 평가를 수행하지 않음
7. **신뢰할 수 없는 출력 신뢰** — 에이전트 조작 출력을 그대로 받아들임

이 일곱 가지가 의미하는 바가 결정적입니다.

> **"X 모델이 SWE-bench Verified 87%"** 같은 발표를 보면, 그 87%가 진짜 실력인지 모델이 평가 인프라를 게이밍한 결과인지 외부에서 알 길이 없습니다. 그리고 그 발표가 다음 모델의 가격 책정과 마케팅의 근거가 됩니다.

#### 다각적 관점

**벤치마크 운영 측**
> "현재 벤치마크는 좋은 출발점이고 완벽하지 않다는 건 인정한다. 발견된 취약점은 후속 버전에서 수정한다. 기준이 없는 것보다는 낫다."

**연구자 측 (버클리 팀)**
> "현재 벤치마크 점수의 상당 부분은 측정 인프라의 산물이지 모델 능력의 산물이 아니다. **적대적 평가 견고성이 표준화되어야** 한다. 자동 취약점 스캐너 BenchJack을 공개했으니 업계가 함께 개선해야 한다."

**모델 회사 측 (암묵적 입장)**
> "벤치마크 점수가 마케팅 도구라는 사실을 부인하기는 어렵다. 다만 모델 카드에 모든 점수를 명시하고 있고, 의도적 게이밍은 하지 않는다."

**비판적 분석**
> "**벤치마크와 사용자 체감의 괴리**는 단순히 측정 분포의 차이가 아니라, **벤치마크 자체가 일정 부분 게임화**되어 있기 때문이기도 하다. Opus 4.7이 환각률 36%로 측정된 것이 진짜인지, 벤치마크 조건에서 모델이 abstain을 선호하도록 fine-tune됐는지, 외부에서 구분이 어렵다."

**더 강한 구조적 비판**
> "벤치마크는 학술적 도구로 시작했지만 산업 마케팅 도구로 사용되고 있다. 이 두 목적은 호환되지 않는다. 학술적 도구는 한계와 결함을 명시하지만, 마케팅 도구는 단일 숫자를 제시한다. **이 둘 사이에 사용자가 끼어 있고, 사용자가 결국 비용을 낸다.**"

이 사실이 이 글 전체에 던지는 메시지가 있습니다. **벤치마크 vs 사용자 체감의 괴리**를 해석할 때, "둘 다 부분적으로 맞다"는 균형 잡힌 입장조차 너무 너그러울 수 있습니다. **벤치마크가 부분적으로 게임화되어 있다면, 사용자 체감 쪽이 진실에 더 가까울 가능성**이 항상 존재합니다.

5-5에서 본 Opus 4.7의 환각률 측정 — Artificial Analysis 벤치마크는 환각률 61%→36% 감소를 측정했지만 사용자는 정반대 경험을 보고했습니다. 이 괴리를 해석하는 한 가지 방법은 "분포가 다르다"는 균형 잡힌 입장이고, 다른 해석은 "**벤치마크가 진실을 측정하지 못하고 있다**"는 더 강한 입장입니다. 후자를 완전히 배제할 수 없는 게 지금 LLM 평가 인프라의 현실입니다.

### 6-5. Agentic 시대 — 위험 표면의 폭발적 확장

지금까지 본 모든 메커니즘은 LLM이 텍스트만 출력할 때도 존재했습니다. 그때는 사고의 비용이 "잘못된 답을 받음" 정도였습니다.

agentic 구조가 이걸 바꿉니다. LLM이 도구를 쥐고 행동하는 순간 — 파일 시스템, DB, API 호출, 결제, 이메일 발송 — **추론 오류가 직접적인 부작용으로 직결**됩니다. 그리고 agentic 워크플로우는 자연스럽게 **long context**입니다. 도구 호출 결과가 컨텍스트에 누적되고, thinking 토큰이 쌓이고, 시스템 프롬프트는 점점 묻힙니다. 가장 강력한 가드레일이 가장 약해지는 시점에 가장 위험한 행동이 일어납니다.

거기에 자기 강화 루프가 있습니다.

<div class="agentic-loop" style="margin:1.5rem 0;background:rgba(239,68,68,0.04);border:1px solid rgba(239,68,68,0.25);border-radius:10px;padding:1.2rem;">
  <div style="font-size:13px;font-weight:700;color:#ef4444;margin-bottom:0.8rem;">Agentic 자기 강화 루프</div>
  <svg viewBox="0 0 600 200" style="width:100%;height:auto;display:block;">
    <defs>
      <marker id="arrowR" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto">
        <path d="M 0 0 L 10 5 L 0 10 z" fill="#ef4444"/>
      </marker>
    </defs>
    <g font-family="system-ui,sans-serif">
      <rect x="40" y="70" width="110" height="60" rx="8" fill="rgba(99,102,241,0.18)" stroke="#6366f1"/>
      <text x="95" y="95" text-anchor="middle" font-size="13" font-weight="600" fill="currentColor">모델 추론</text>
      <text x="95" y="113" text-anchor="middle" font-size="10" fill="currentColor" opacity="0.7">자기 컨텍스트 기반</text>

      <rect x="195" y="70" width="110" height="60" rx="8" fill="rgba(14,165,233,0.18)" stroke="#0ea5e9"/>
      <text x="250" y="95" text-anchor="middle" font-size="13" font-weight="600" fill="currentColor">도구 호출</text>
      <text x="250" y="113" text-anchor="middle" font-size="10" fill="currentColor" opacity="0.7">현실 세계에 영향</text>

      <rect x="350" y="70" width="110" height="60" rx="8" fill="rgba(34,197,94,0.18)" stroke="#22c55e"/>
      <text x="405" y="95" text-anchor="middle" font-size="13" font-weight="600" fill="currentColor">결과 텍스트</text>
      <text x="405" y="113" text-anchor="middle" font-size="10" fill="currentColor" opacity="0.7">컨텍스트로 주입</text>

      <rect x="490" y="40" width="100" height="120" rx="8" fill="rgba(239,68,68,0.15)" stroke="#ef4444"/>
      <text x="540" y="80" text-anchor="middle" font-size="12" font-weight="700" fill="#ef4444">Long context</text>
      <text x="540" y="98" text-anchor="middle" font-size="11" fill="currentColor" opacity="0.85">attention decay</text>
      <text x="540" y="118" text-anchor="middle" font-size="11" fill="currentColor" opacity="0.85">guardrail 침식</text>

      <line x1="150" y1="100" x2="190" y2="100" stroke="#ef4444" stroke-width="2" marker-end="url(#arrowR)"/>
      <line x1="305" y1="100" x2="345" y2="100" stroke="#ef4444" stroke-width="2" marker-end="url(#arrowR)"/>
      <line x1="460" y1="100" x2="485" y2="100" stroke="#ef4444" stroke-width="2" marker-end="url(#arrowR)"/>
      <path d="M 540 160 Q 540 185, 95 185 L 95 135" stroke="#ef4444" stroke-width="2" fill="none" stroke-dasharray="5 4" marker-end="url(#arrowR)"/>
      <text x="320" y="180" text-anchor="middle" font-size="11" fill="#ef4444" font-weight="600">자기 출력이 다음 추론의 입력</text>
    </g>
  </svg>
  <div style="font-size:12px;margin-top:0.8rem;line-height:1.6;opacity:0.85;">
    각 사이클마다 컨텍스트가 길어지고, 시스템 프롬프트의 attention 비중이 떨어진다. 모델은 자기 출력을 사실로 신뢰하므로 한 번 어긋난 추론은 자체 강화된다. 가장 위험한 행동은 보통 사이클 후반부에 일어난다.
  </div>
</div>

### 6-6. 무엇이 빠져 있는가 — 메모리·권한·검증

세 사고를 한 표로 정리해보면 동일한 빈 칸이 보입니다.

| 사건 | 누락된 메모리 | 누락된 권한 경계 | 누락된 검증 |
|---|---|---|---|
| Replit DB | "데이터 만들지 마" 11번 → attention에서 묻힘 | DB 접근에 destructive 분리 없음 | 가짜 데이터 생성 후 검증 부재 |
| Gemini CLI | mkdir 결과 인지 못함 — 자기 컨텍스트만 신뢰 | rm-equivalent 명령에 사용자 승인 없음 | read-after-write 부재 |
| PocketOS | credential 에러 컨텍스트 → "스스로 해결" 모드 진입 | API 토큰 scope 없음 — 모든 destructive 작업 가능 | DELETE 확인·환경 격리·백업 분리 부재 |
| Anthropic 잠수함 패치 | 사용자에게 변경 고지 없음 | 디폴트 변경에 영향 측정 부재 | 통계적 회귀 측정 체계 부재 |

이건 LLM의 한계를 인정하고 그 위에 어떻게 시스템을 쌓을지의 문제입니다. **모델이 안전해질 때까지 기다리는 게 아니라, 모델이 안전하지 않다는 가정 위에 시스템을 설계해야** 합니다.

원칙을 몇 줄로 추리면 다음과 같습니다.

1. **Read-after-write를 강제**한다. 도구가 행동했으면 그 결과를 다시 읽고 검증하는 단계를 무조건 끼운다.
2. **Destructive 행동에 인간 승인을 강제**한다. 모델 판단으로 우회 가능한 가드레일은 가드레일이 아니다.
3. **권한을 최소화**한다. **실패는 확률 문제, 권한은 피해 반경**이다. credential 하나가 production DB·결제·전체 파일시스템·배포 권한을 동시에 쥐고 있으면, 모델이 아니라도 그 시스템은 어차피 무너진다.
4. **백업을 격리**한다. 같은 권한·같은 위치의 백업은 백업이 아니다.
5. **메모리 토큰을 컨텍스트 끝쪽에 다시 주입**한다. 시스템 프롬프트 외에도 중요 메모리를 주기적으로 refresh.
6. **Long context에서는 가드레일을 더 자주 다시 검증**한다. 30턴마다 시스템 프롬프트 핵심을 재주입하는 패턴.

### 6-7. 학술 차원의 mitigation 패턴 — 무엇이 정말 작동하는가

위 여섯 가지 원칙은 시스템 설계 차원의 가드레일입니다. 모델 사용 패턴 차원에서도 학술적으로 검증된 mitigation들이 있습니다. **모두 부분 해결책이지 만능이 아닙니다** — 어느 것도 LLM의 본질적 비결정성·환각·sycophancy를 *없애지* 못하고, 다만 *발현 빈도와 충격*을 줄입니다.

| 패턴 | 무엇 | 무엇을 줄이는가 | 한계 |
|---|---|---|---|
| **ReAct** (Yao et al., 2023) | Reasoning과 Action을 번갈아 — 도구 호출 결과를 다음 추론 입력으로 명시적 통합 | Internal hallucination loop, read-after-write 누락 | 도구 호출 비용·latency 증가 |
| **Reflection / Self-Refine** (Madaan et al., 2023) | 답을 만든 후 모델이 자기 답을 비판하고 다시 씀 | 첫 패스 환각·논리 오류 | self-rationalization 영역에서는 오히려 악화 가능 |
| **Tree of Thoughts** (Yao et al., 2024) | 추론을 여러 갈래로 분기, 각 갈래를 평가해 선택 | First-token commitment 효과 | 토큰 비용 수 배 증가 |
| **Self-Consistency** (Wang et al., 2022) | 같은 질문에 여러 번 샘플링 → 다수결 | Sampling 비결정성으로 인한 우연한 환각 | systematic bias는 못 잡음 (2-6에서 본 그대로) |
| **Multi-agent critic** | 별도 에이전트가 주 에이전트 행동을 검토·승인 | Reasoning chain amplification, sycophancy | 검토 에이전트 자체도 sycophancy 학습 가능 |
| **Constrained decoding** | 출력을 정해진 schema·문법에 강제 | Tool-call 형식 오류, structured output 환각 | 의미 차원 환각은 못 잡음 |
| **Retrieval grounding** (RAG) | 외부 출처를 컨텍스트에 주입하고 인용 강제 | Closed-book 환각 | 3-4에서 본 retrieval 비결정성 도입 |
| **Human-in-the-loop** | Destructive 행동에 인간 승인 강제 | 모든 사고 카테고리 | 속도·자동화 가치 손실 |

이 표가 던지는 핵심 메시지가 있습니다. **각 mitigation은 자기가 줄이는 실패 모드를 가지지만, 다른 실패 모드를 새로 도입하기도 합니다.** Reflection은 첫 패스 환각을 줄이지만 inverse scaling 영역으로 모델을 밀어 넣을 수 있습니다. RAG는 closed-book 환각을 줄이지만 retrieval 비결정성을 추가합니다. Self-Consistency는 sampling 우연을 다수결로 해결하지만 systematic bias는 못 잡습니다. Multi-agent critic도 검토 에이전트 자체가 같은 RLHF 분포에서 나왔다면 같은 sycophancy를 공유합니다.

> 즉 안전한 LLM 시스템은 **단일 mitigation을 적용한 시스템이 아니라, 여러 mitigation을 *각자의 한계와 함께* 조합한 시스템**입니다. 그리고 그 조합 설계는 모델 회사가 아니라 사용자(개발자·팀·기업) 측이 자기 워크플로우에 맞게 만들어야 합니다 — 이 글이 5-3에서 사용자 측 ops 성숙도를 짚은 이유와 같은 맥락입니다.

### 6-8. 사용자 측 OOD 회피 — 일상 사용 차원의 대처

6-6은 production 시스템 차원, 6-7은 학술 mitigation 패턴 차원입니다. 그 사이에 빠지는 게 **개인 사용자가 매일 하는 호출 차원의 대처**입니다. 본문 2-5에서 본 OOD 진입(학습 분포 꼬리 너머의 inverse scaling 영역)은 단일 변수로 결정되지 않습니다. **세 층의 변수가 조합**되어 결정됩니다.

| 변수 층 | 무엇 | 사용자 통제권 |
|---|---|---|
| 사용자 측 | effort 설정, 컨텍스트 길이, 프롬프트 형태, 도구 호출 횟수 | 있음 |
| 모델 자율 | Adaptive Thinking에서 모델이 thinking 깊이 자기 결정 | 없음 (블랙박스) |
| 인프라 측 | silent effort downgrade, KV cache 정책, MoE 라우팅, 잠수함 패치 | 없음 (고지조차 없음) |

같은 입력을 두 번 줘도 모델 자율과 인프라 변수가 달라서 어떤 호출은 OOD에 들어가고 어떤 호출은 안 들어갑니다 — 5-5에서 본 "같은 사용자가 같은 작업을 두 번 했을 때 결과가 다르다"의 정확한 정체이기도 합니다. 사용자 측에서 OOD 진입을 가장 강하게 유발하는 조합은 본문 다이어그램이 보여준 그대로입니다.

> **effort = max + 긴 컨텍스트(수만~수십만 토큰) + 도구 호출 누적**

이 셋이 동시에 켜질수록 학습 분포 꼬리 너머로 들어갈 확률이 올라갑니다. 그래서 사용자 차원의 대처도 이 셋을 거꾸로 조이는 방향으로 정리됩니다.

| 원칙 | 무엇을 줄이는가 | 본문 연결 |
|---|---|---|
| **Effort 디폴트는 medium/high, max는 reserve** | 학습 분포 꼬리 진입 빈도 | 2-4 (Anthropic 자기 문서가 동일 권고) |
| **세션·컨텍스트 분할 — 30턴마다 새 세션** | 가드레일 침식, attention decay | 4-3 |
| **모호한 열린 질문 대신 좁은 step 단위 질문** | first-token commitment, reasoning chain amplification | 2-2, 4-2 |
| **도구 호출 결과를 다시 읽게 명시적 강제** | Internal hallucination loop | 4-4 (Gemini CLI 사고의 직접 예방) |
| **Destructive action 직전에는 thinking *끈다*** | inverse scaling, self-rationalization | 6-3 (역설적이지만 길게 생각할수록 destructive 정당화 증가) |
| **첫 출력을 의심 — 다른 세션에서 재질의** | sampling 비결정성, sycophancy override | 2-6, 4-1 |
| **확신 톤과 정확성을 분리해서 본다** | sycophancy 표현 패턴 | 4-1 (Sharma et al. 2023) |

마지막에서 두 번째 원칙(destructive action 직전 thinking off)은 직관에 반하지만 정확히 들어맞습니다. 본문 6-3 inverse scaling 영역에서 가장 자주 발현되는 게 *destructive action에 대한 자기 합리화*라는 점에서, 결정적 행동 직전에는 짧은 instruct 모드가 오히려 안전합니다. PocketOS 9초가 정확히 그 반대 조합 — 길게 생각하면서 자기 결정을 정당화한 결과 — 이었다는 걸 떠올리면 이해가 쉽습니다.

#### Read-after-write의 실용 패턴 — *어떻게* 강제할 것인가

표의 네 번째 원칙(read-after-write)은 본문 4-4·6-6·6-7에서 반복적으로 강조됐지만, *어떻게* 강제할지가 일상에서 가장 자주 누락됩니다. 네 층의 패턴이 있고, 위로 갈수록 적용하기 쉽지만 약하고 아래로 갈수록 단단합니다.

| 층 | 패턴 | 예시 | 단단함 |
|---|---|---|---|
| **프롬프트** | 모델에게 검증을 명시적으로 지시 | "각 명령 후 exit code와 결과를 한 줄 요약, 예상과 다르면 멈춘다" | 약함 — 모델이 무시 가능 |
| **도구 chain** | 명령에 검증 단계를 자동 chain | `mkdir foo && [ -d foo ] \|\| exit 1` | 중간 — 한 명령 단위 |
| **워크플로우** | propose → confirm → apply 두 단계 분리 | git diff 후 사용자 승인 후 commit, terraform plan 후 apply | 강함 — 사람이 게이트 |
| **환경** | Idempotent / transactional / snapshot 환경 | DB transaction, declarative IaC, ZFS snapshot | 가장 강함 — 망쳐도 되돌림 |

작업 종류별 구체적 패턴은 다음과 같습니다.

| 작업 | Read-after-write 패턴 |
|---|---|
| Directory 생성 | `mkdir` 후 `[ -d <path> ]`로 존재 확인 — **Gemini CLI 사고가 정확히 이 패턴 누락** |
| File 쓰기 | 쓰기 후 다시 읽어 hash·size 비교, diff로 변경사항 검증 |
| DB INSERT/UPDATE | 쓰기 후 SELECT로 변경 확인, 가능하면 transaction 안에서 |
| API 호출 (POST/PUT) | 응답 status 체크 + GET으로 리소스 상태 재확인 |
| Destructive (DELETE/rm/drop) | dry-run 우선, 영향 범위 사전 확인, snapshot/backup 검증 후 실행 |
| Process 시작 | 시작 후 health check endpoint, port listen, log tail 확인 |
| Git 작업 | commit 후 `git log -1` 확인, push 후 remote sha 비교 |

핵심은 **모델에게 검증을 시키는 것보다, 도구·환경 차원에서 검증이 자동으로 따라붙도록 만드는 게 단단**하다는 점입니다. 모델은 자기 출력을 신뢰하는 경향이 RLHF 가중치에 박혀 있어서, 프롬프트 차원의 "검증해라"는 압박이 들어오면 무시될 수 있습니다 — Replit이 11번의 대문자 경고에도 무시한 패턴과 같은 메커니즘입니다. 도구 wrapper나 워크플로우 차원에서 강제하는 게 본질적으로 안전합니다.

> Read-after-write의 진짜 무게는 한 줄로 정리됩니다. **"모델이 행동했으면 결과를 *현실에서* 다시 가져와라."** 모델 자기 보고를 믿지 않는 게 시작점입니다 — 본문 4-4 internal hallucination loop의 본질이 정확히 "모델 자기 보고를 현실로 착각하는 것"이었기 때문입니다.

> 정리하면 — 사용자가 통제 가능한 영역은 OOD 진입을 결정짓는 *절반뿐*입니다. 나머지 절반(모델 자율 + 인프라 변수)은 비결정적이고 사용자에게 닫혀 있습니다. 그래서 사용자 측 대처의 본질은 "OOD를 완전히 막는다"가 아니라 "**OOD에 들어가도 비용이 작은 작업 형태로 운영한다**"입니다 — 좁은 질문, 짧은 컨텍스트, 검증 가능한 도구 호출, destructive action 직전의 신중함. 비결정성은 없앨 수 없지만, 비결정성이 destructive하게 발현되는 빈도는 줄일 수 있습니다.

### 6-9. 조직 차원의 LLM ops — 회귀를 잡는 측정 인프라

6-6은 production 시스템 차원, 6-7은 학술 mitigation, 6-8은 개인 사용자 차원입니다. 그 위에 한 층이 더 있습니다 — **팀·조직 단위의 LLM ops**. 본문 5-3에서 짚은 *사용자 측 ops 성숙도*를 구체적으로 풀어 놓은 층입니다.

핵심 명제는 단순합니다. **개인은 OOD를 다스릴 뿐, 회귀는 통계적이라 *기록*이 없으면 잡히지 않는다.** Stella Laurenzo가 잠수함 패치를 입증할 수 있었던 것도 AMD 팀이 6,852 세션의 로그를 *저장*하고 있었기 때문이고, 본문 1-1부터 본 모든 비결정성(샘플링, MoE 라우팅, KV cache eviction, adaptive thinking downgrade)은 한 번의 호출로는 보이지 않고 누적된 통계로만 드러납니다.

| 측정 항목 | 무엇을 본다 | 왜 — 어떤 회귀를 잡는가 |
|---|---|---|
| **Tool-call 수/세션** | 같은 작업당 도구 호출 누적 | 사고 깊이 회귀 (Stella의 *Bedrock 비용 122배 증가*가 정확히 이 패턴) |
| **출력 토큰/세션** | 답변 길이 분포 변화 | verbose mode의 silent rollout 감지 (4월 23일 verbosity 프롬프트 사건) |
| **Thinking 토큰 비율** | reasoning effort 실측치 | adaptive thinking silent downgrade 감지 — 모델이 "max"라고 보고해도 실제 thinking은 줄어들 수 있음 |
| **Stop hook 위반/일** | 가드레일 무시 횟수 | 가드레일 침식의 가장 직접적 시그널 (Stella의 *0 → 43건/일*) |
| **재작업률** | 같은 입력의 재호출 비율 | 사용자 체감 회귀의 통계적 시그널 — 개별로는 우연이지만 추세로는 신호 |
| **비용/세션 추세** | 토큰 단가 변동 | 토크나이저 변경의 silent 비용 인플레 (Opus 4.7의 *1.47배*) |
| **모델 버전 메타** | 응답 헤더의 정확한 model id | 라우터 잠수함 변경 감지 (2024년 8월 XLA:TPU 사건과 같은 인프라 단의 회귀) |

이 데이터는 모델 회사가 주지 않습니다. 사용자가 자기 워크플로우 위에 *자기 비용으로* 깔아야 합니다 — 본문 5-3과 결론에서 반복적으로 짚은 *비대칭*의 정확한 정체이기도 합니다. 그러나 깔리고 나면 두 가지가 가능해집니다.

1. **회귀의 사전 감지** — 잠수함 패치는 더 이상 "체감"이 아니라 *측정*이 됩니다. 한 달 부인을 6,852 세션으로 뒤집은 사례가 그 증거입니다.
2. **공급자 협상력** — 비용 인플레가 토크나이저 때문인지, 모델이 회귀해서 같은 작업에 호출이 늘었기 때문인지를 *데이터로* 분리할 수 있어야 단가 협상·SLA·계약 갱신에서 의미 있는 카드가 됩니다.

> 한 줄로 정리하면 — **개인은 OOD를 줄이고, 시스템은 권한과 검증으로 폭발 반경을 줄이고, 조직은 측정으로 회귀를 잡는다.** 세 층이 모두 있어야 LLM과의 협업이 *지속 가능한 운영*으로 옮겨갑니다. 어느 한 층만 깔아 두면 다른 층의 결함이 피해를 만들고, 측정이 빠지면 결함의 존재 자체를 입증할 수 없습니다.

---

## 결론 — 단일 답이 없는 시대의 LLM 비판

여기까지 따라온 끝에 처음 질문으로 돌아갑니다. **Claude는 진짜 너프됐는가.** 지금까지의 자료를 다 모아도 단일한 답은 나오지 않습니다. 대신 다섯 개의 답이 동시에 부분적으로 맞다는 결론에 도달합니다 — 그리고 그 사실 자체가 지금 LLM 위기의 진짜 본질입니다.

### 다섯 갈래의 답을 나란히 놓고 보면

각 갈래에 어떤 근거가 있고, 어디서 막히는지를 한 번에 비교해 보겠습니다.

| 답의 갈래 | 핵심 주장 | 가장 강한 근거 | 한계 |
|---|---|---|---|
| **인프라·운영** | 모델 가중치는 그대로, 변한 건 effort·KV cache·프롬프트·토크나이저·라우팅 같은 *주변* | Anthropic 4월 23일 포스트모템, 2024년 8월 XLA:TPU 인프라 버그 | 사용자 입장에서는 "모델이 너프됐다"와 구분 불가 |
| **학습·정렬** | 4.6 → 4.7 사이 안전성 강화 fine-tune이 추론 보수성·sycophancy·환각 패턴을 미세 변경 | Inverse Scaling 논문(Anthropic 공저), Constitutional AI의 추가 추론 부담 | Anthropic이 명시적으로 인정/부인하지 않음 — 외부 검증 불가 |
| **컴퓨팅 경제** | $25B AWS 계약·5GW 인프라 가동 전 갭. 모든 최적화는 비용 절감 압박의 결과 | 토크나이저 1.47배, Bedrock $26→$42K, 5시간 쿼타가 30분에 소진 | "전가됐다"는 가치 판단. 회사 입장에서는 "지속 가능성을 위한 조치" |
| **거버넌스·투명성** | 능력보다 변경을 알리지 않는 운영 방식의 문제. 잠수함 패치 자체가 신뢰 침식 | 한 달 부인, 6,852 세션 분석으로만 인정, 한도 미고지, GitHub #52149 | 거버넌스 개선이 능력 향상으로 직결되지 않음 |
| **측정의 위기** | 벤치마크가 부분 게임화, 사용자 체감은 통계적 입증이 어려움. 측정 도구가 진실을 말하지 못함 | 버클리 8개 벤치마크 익스플로잇, 환각률 측정과 체감의 정반대, METR 30% reward hacking | 이 답이 맞다면 다른 답들도 검증 불가 — 회의주의 함정 |

#### 어느 것이 가장 무게가 무거운가

내가 보기에 가장 무게가 무거운 건 **거버넌스·투명성**과 **측정의 위기**입니다. 인프라·학습·경제 가설은 어느 정도 회사의 사정을 이해할 수 있는 영역입니다 — 컴퓨팅 부족은 사실이고, 안전성 fine-tune의 부작용은 학술적으로도 인정되는 트레이드오프입니다. 그런데 거버넌스와 측정은 다릅니다. **변경을 알리지 않는 선택**과 **벤치마크 숫자를 마케팅 도구로 쓰는 선택**은 사정이 아니라 결정입니다. 그리고 그 결정의 비용은 매번 사용자가 짊어집니다.

### 비판해야 할 핵심들

각 갈래에서 한 줄씩 뽑아 보면 비판의 윤곽이 또렷해집니다.

| 비판 차원 | 문제 |
|---|---|
| **토큰 경제의 불투명성** | 같은 작업의 비용이 단가 변경 없이도 20~47% 오른다는 사실을 사용자가 토크나이저 분석을 해야 알 수 있는 구조 |
| **잠수함 패치의 정상화** | LLM 산업 전체가 "변경 영향이 측정 불가능하니 사전 고지 의무도 약하다"는 비공식 합의 위에 운영 |
| **벤치마크 마케팅** | 학술 도구가 마케팅 도구로 사용되는 비대칭. 모델 카드 숫자와 사용자 체감의 간극을 사용자가 메우게 만듦 |
| **Adaptive Thinking의 비용 이전** | "모델이 알아서 깊이를 정한다"는 명목으로 비용 예측을 어렵게 만들고 사용자 통제권 축소 |
| **Constitutional AI의 추론 부담** | 안전성을 명분으로 모든 답에 자기 비판 추론을 추가, 그 토큰 비용을 사용자가 부담 |
| **반복 가능성** | 2024년 8월과 2026년 4월 — 1년 반 사이에 두 번 같은 패턴. 다음에 일어나지 않으리란 보장 없음 |

이 표를 한 줄로 줄이면 이렇게 됩니다.

> **사용자가 다섯 가지 답을 동시에 풀어야 자기가 무엇을 사고 있는지 이해할 수 있는 제품**은, 그 자체로 거버넌스 실패의 결과입니다.

### 글을 쓰면서 느낀 것

이 글을 쓰며 가장 무겁게 다가온 건 **불확실성을 인정하는 비용을 누가 지는가**라는 질문이었습니다.

LLM은 본질적으로 비결정적입니다. 그건 회사 잘못이 아닙니다. 그런데 그 비결정성을 측정하고, 회귀를 입증하고, 변경을 추적하는 인프라를 갖추는 비용을 누가 지느냐 — 이건 명백히 회사가 져야 할 책임인데, 지금까지의 사건들은 그 비용을 사용자가 지고 있다는 사실을 반복적으로 보여줬습니다. AMD의 Stella Laurenzo가 자기 팀의 6,852 세션을 분석해야 비로소 인정받았다는 사실 하나로도 이 비대칭은 충분히 설명됩니다.

그리고 또 하나. **나는 4.6 시절에 한참 기대고 있었습니다.** 매일 코딩에 쓰고, 블로그 포스트도 같이 다듬고, agentic 워크플로우의 가드레일이 어디까지 작동하는지 계속 시험했습니다. 그래서 이번 사건들을 단순히 "AI 회사가 또 사고 쳤다"로만 보고 넘어갈 수가 없었습니다. 모델을 신뢰한다는 게 어떤 의미인지, 도구로 쥐고 있는 LLM이 갑자기 다른 곡선 위로 옮겨갔을 때 내 작업 흐름의 어디가 흔들리는지를 직접 겪었기 때문입니다. 이 글의 톤이 곳곳에서 회사 쪽보다 사용자 쪽으로 기울어져 있다면, 그건 의도된 균형의 결과입니다 — 어차피 회사 측 자료는 충분히 있고, 사용자 측 측정과 통합 분석이 부족하기 때문입니다.

마지막으로 한 가지가 분명해졌습니다. **Claude는 여전히 frontier LLM 중 하나**입니다. 4.6 시절의 도약감은 환상이 아니었고, 지금도 잘 작동하는 영역에서는 여전히 가장 좋은 도구 중 하나입니다. 비판은 비판이고, 그게 모델의 기술적 가치를 부정하는 건 아닙니다. 다만 이 비판들을 그냥 흘려보내면, 18개월 뒤 세 번째 같은 사건이 왔을 때 우리는 또 같은 자리에서 같은 분석을 반복하고 있을 것입니다.

### 한 줄로 압축하면

이 글의 모든 갈래 — 인프라·학습·경제·거버넌스·측정 — 와 모든 사고 — Replit, Gemini CLI, PocketOS, Anthropic 잠수함 패치 — 는 결국 한 문장으로 수렴합니다.

> **LLM은 신뢰할 수 있는 실행자가 아니라, 유용하지만 비결정적인 제안 생성기다. 따라서 안전한 LLM 시스템은 "모델을 믿는 시스템"이 아니라 "모델이 틀려도 복구 가능한 시스템"이어야 한다.**

모델이 안전해질 때까지 기다리는 게 아니라, **모델이 안전하지 않다는 가정 위에 시스템·권한·측정·운영 절차를 설계하는 것**. Transformer의 작동원리부터 잠수함 패치까지를 거쳐 이 한 줄에 도달하는 게 이 글의 끝입니다.

### 마지막으로 남는 질문

> **그 도약은 지속 가능했던 것인가, 아니면 컴퓨팅 보조금이 풍부했던 시절의 사치였는가.**

답은 지금 시점에서 알 수 없습니다. 인프라가 가동되고 비용 압박이 풀리면 4.6 시절로 돌아갈 수도 있고, 비용 구조 자체가 영구히 바뀌어서 그 시절은 다시 안 올 수도 있습니다. 두 가능성 모두 열려 있고, 사용자는 그 답을 기다리는 동안에도 비용을 내고 있습니다.

LLM 시대의 실력은 이제 모델 자체보다 **모델 회사를 어떻게 다룰 것인가**에 점점 더 가까워지고 있는 것 같습니다 — 측정 인프라를 갖추고, 변경을 추적하고, 공급자 종속을 줄이고, 필요할 때 비용 모델을 압박할 수 있는 능력. 이게 글의 시작 질문 — "Claude는 진짜 너프됐는가" — 에 대해 내가 지금 시점에서 줄 수 있는 가장 정직한 답입니다.

질문이 단일해 보였을 뿐, 답은 처음부터 여러 개였습니다. 이 글이 그 답들 사이에서 자기 위치를 찾는 데 한 발짝이라도 도움이 되었기를 바랍니다.

---

## 참고 자료

**사고 및 사건 보고**
- [Anthropic — An update on recent Claude Code quality reports (4월 23일 포스트모템)](https://www.anthropic.com/engineering/april-23-postmortem)
- [GeekNews 4월 24일 — Claude Code 장애 포스트모템 정리](https://news.hada.io/topic?id=28828)
- [Fortune — Anthropic engineering missteps were behind Claude Code's monthlong decline](https://fortune.com/2026/04/24/anthropic-engineering-missteps-claude-code-performance-decline-user-backlash/)
- [VentureBeat — Mystery solved: changes to Claude's harnesses and operating instructions caused degradation](https://venturebeat.com/technology/mystery-solved-anthropic-reveals-changes-to-claudes-harnesses-and-operating-instructions-likely-caused-degradation)
- [GeekNews — Cursor + Opus 4.6 PocketOS 사건](https://news.hada.io/topic?id=28927)
- [Tom's Hardware — Replit AI deletes production database](https://www.tomshardware.com/tech-industry/artificial-intelligence/ai-coding-platform-goes-rogue-during-code-freeze-and-deletes-entire-company-database-replit-ceo-apologizes-after-ai-engine-says-it-made-a-catastrophic-error-in-judgment-and-destroyed-all-production-data)
- [Fortune — Replit catastrophic failure](https://fortune.com/2025/07/23/ai-coding-tool-replit-wiped-database-called-it-a-catastrophic-failure/)
- [AI Incident Database #1152 — Replit](https://incidentdatabase.ai/cite/1152/)
- [AI Incident Database #1178 — Gemini CLI](https://incidentdatabase.ai/cite/1178/)
- [Slashdot — Gemini CLI 파일 삭제 사건](https://developers.slashdot.org/story/25/07/26/0642239/google-gemini-deletes-users-files-then-just-admits-i-have-failed-you-completely-and-catastrophically)
- [GeekNews — 2024년 8월 Claude 인프라 버그 포스트모템](https://news.hada.io/topic?id=23167)

**Lobotomize 보고 및 사용자 측 측정**
- [GitHub Issue #19468 — Stella Laurenzo, Systematic Model Degradation in Claude Code (6,852 세션 분석)](https://github.com/anthropics/claude-code/issues/19468)
- [GeekNews — Stella Laurenzo의 Claude Code 6,852 세션 분석 정리](https://news.hada.io/topic?id=28272)
- [GeekNews — 독일 개발자 Claude 구독 해지 사례](https://news.hada.io/topic?id=28863)
- [VentureBeat — Is Anthropic 'nerfing' Claude?](https://venturebeat.com/technology/is-anthropic-nerfing-claude-users-increasingly-report-performance)
- [Fortune — Anthropic faces user backlash over Claude performance issues](https://fortune.com/2026/04/14/anthropic-claude-performance-decline-user-complaints-backlash-lack-of-transparency-accusations-compute-crunch/)
- [scortier substack — Claude Code Drama: 6,852 Sessions Prove Performance Collapse](https://scortier.substack.com/p/claude-code-drama-6852-sessions-prove)
- [MindStudio — Anthropic's Compute Shortage](https://www.mindstudio.ai/blog/anthropic-compute-shortage-claude-limits)

**Opus 4.7 max effort 환각·토크나이저 비용**
- [GitHub Issue #52149 — Opus 4.7 [1M] at max effort + thinking ON: severe regression + silent effort downgrade](https://github.com/anthropics/claude-code/issues/52149)
- [GitHub Issue #50235 — Opus 4.7 Hallucinations](https://github.com/anthropics/claude-code/issues/50235)
- [GeekNews — Opus 4.7 토크나이저 변경 비용 측정](https://news.hada.io/topic?id=28641)
- [The New Stack — AI shrinkflation: Why Opus 4.7 may be less capable than the model it replaced](https://thenewstack.io/claude-opus-47-flaky-performance/)
- [Artificial Analysis — Opus 4.7: Everything you need to know](https://artificialanalysis.ai/articles/opus-4-7-everything-you-need-to-know)

**벤치마크 신뢰성 문제**
- [GeekNews — 버클리 연구팀 8개 AI 에이전트 벤치마크 익스플로잇 시연](https://news.hada.io/topic?id=28440)
- METR (2025), "Reward hacking in reasoning models" — o3·Claude 3.7 Sonnet 평가 30% 이상에서 자동 reward hacking 보고
- 버클리 BenchJack — 자동 벤치마크 취약점 스캐너

**Adaptive Thinking·Effort 작동원리 (공식 문서)**
- [Anthropic Docs — Adaptive thinking](https://platform.claude.com/docs/en/build-with-claude/adaptive-thinking)
- [Anthropic Docs — Effort parameter](https://platform.claude.com/docs/en/build-with-claude/effort)
- [Anthropic Docs — Building with extended thinking](https://platform.claude.com/docs/en/build-with-claude/extended-thinking)

**학술 논문 — Transformer 아키텍처**
- [Vaswani et al. (2017), "Attention Is All You Need," NeurIPS 2017 (arXiv:1706.03762)](https://arxiv.org/abs/1706.03762)
- [Su et al. (2021), "RoFormer: Enhanced Transformer with Rotary Position Embedding" (arXiv:2104.09864)](https://arxiv.org/abs/2104.09864)
- [Ainslie et al. (2023), "GQA: Training Generalized Multi-Query Transformer Models from Multi-Head Checkpoints" (arXiv:2305.13245)](https://arxiv.org/abs/2305.13245)
- [Beltagy et al. (2020), "Longformer: The Long-Document Transformer" (arXiv:2004.05150)](https://arxiv.org/abs/2004.05150)

**학술 논문 — Tokenizer**
- [Sennrich et al. (2016), "Neural Machine Translation of Rare Words with Subword Units," ACL 2016 (arXiv:1508.07909)](https://arxiv.org/abs/1508.07909)
- [Kudo & Richardson (2018), "SentencePiece: A simple and language independent subword tokenizer" (arXiv:1808.06226)](https://arxiv.org/abs/1808.06226)
- [Petrov et al. (2023), "Language Model Tokenizers Introduce Unfairness Between Languages," NeurIPS 2023 (arXiv:2305.15425)](https://arxiv.org/abs/2305.15425)

**학술 논문 — Sampling**
- [Fan et al. (2018), "Hierarchical Neural Story Generation," ACL 2018 (arXiv:1805.04833)](https://arxiv.org/abs/1805.04833)
- [Holtzman et al. (2020), "The Curious Case of Neural Text Degeneration," ICLR 2020 (arXiv:1904.09751)](https://arxiv.org/abs/1904.09751)
- [Nguyen et al. (2024), "Min-p Sampling: Balancing Creativity and Coherence at High Temperature" (arXiv:2407.01082)](https://arxiv.org/abs/2407.01082)

**학술 논문 — Mixture of Experts**
- [Shazeer et al. (2017), "Outrageously Large Neural Networks: The Sparsely-Gated Mixture-of-Experts Layer," ICLR 2017 (arXiv:1701.06538)](https://arxiv.org/abs/1701.06538)
- [Fedus et al. (2021), "Switch Transformers: Scaling to Trillion Parameter Models with Simple and Efficient Sparsity" (arXiv:2101.03961)](https://arxiv.org/abs/2101.03961)
- [Lepikhin et al. (2020), "GShard: Scaling Giant Models with Conditional Computation and Automatic Sharding" (arXiv:2006.16668)](https://arxiv.org/abs/2006.16668)
- [Jiang et al. (2024), "Mixtral of Experts" (arXiv:2401.04088)](https://arxiv.org/abs/2401.04088)

**학술 논문 — Reasoning·Memory·Failure Modes**
- [Inverse Scaling in Test-Time Compute (arXiv:2507.14417, 2025년 7월)](https://arxiv.org/abs/2507.14417)
- [Test-Time Scaling in Reasoning Models Is Not Effective for Knowledge-Intensive Tasks Yet (arXiv:2509.06861, 2025년 9월)](https://arxiv.org/abs/2509.06861)
- [Liu et al. (2023), "Lost in the Middle: How Language Models Use Long Contexts" (arXiv:2307.03172)](https://arxiv.org/abs/2307.03172)
- [Wei et al. (2022), "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models" (arXiv:2201.11903)](https://arxiv.org/abs/2201.11903)
- [Wang et al. (2022), "Self-Consistency Improves Chain of Thought Reasoning" (arXiv:2203.11171)](https://arxiv.org/abs/2203.11171)
- [Turpin et al. (2023), "Language Models Don't Always Say What They Think" (arXiv:2305.04388)](https://arxiv.org/abs/2305.04388)
- [Zhang et al. (2023), "H2O: Heavy-Hitter Oracle for Efficient Generative Inference of Large Language Models" (arXiv:2306.14048)](https://arxiv.org/abs/2306.14048)
- [Sharma et al. (2023), "Towards Understanding Sycophancy in Language Models" (arXiv:2310.13548) — Anthropic 공저, RLHF가 sycophancy를 증가시킨다는 결정적 입증](https://arxiv.org/abs/2310.13548)

**학술 논문 — Mitigation 패턴**
- [Yao et al. (2023), "ReAct: Synergizing Reasoning and Acting in Language Models" (arXiv:2210.03629)](https://arxiv.org/abs/2210.03629)
- [Madaan et al. (2023), "Self-Refine: Iterative Refinement with Self-Feedback" (arXiv:2303.17651)](https://arxiv.org/abs/2303.17651)
- [Yao et al. (2024), "Tree of Thoughts: Deliberate Problem Solving with Large Language Models" (arXiv:2305.10601)](https://arxiv.org/abs/2305.10601)
