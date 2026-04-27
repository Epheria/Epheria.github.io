---
title: ナーフされたClaude — Transformerの動作原理から潜水艦パッチ・ハルシネーション・トークン爆増まで
date: 2026-04-27 11:00:00 +0900
categories: [AI, LLM]
tags: [LLM, Transformer, RLHF, Attention, KV-Cache, Tokenizer, MoE, Sycophancy, Anthropic, Claude, AI Safety, Agent]
toc: true
toc_sticky: true
difficulty: intermediate
math: true
chart: true
lang: ja
tldr:
  - 4.6時代に大きな飛躍を見せていたClaudeが突然揺らぎ始めた理由は、単一の原因ではない。Transformerアーキテクチャの本質的な限界が、RLHF・adaptive thinking・インフラ最適化の圧力と交差した構造的な結果だ
  - 潜水艦パッチ（silent downgrade）はすでに計測された事実だ。AMDのStella Laurenzoが6,852セッションを分析し「思考の深さ73%減、Bedrockコスト122倍増、Stop hook違反 0→43件/日」を実証し、Anthropicは4月23日に公式認定した
  - Opus 4.7はトークナイザーまで変更され、英語・コードのトークン使用量が実測1.47倍に増加し、同一価格体系でセッションあたり20〜30%の追加コストが発生する。ハルシネーション・gaslight・circular argumentの報告はリリース24時間以内に殺到した
  - LLM信頼性危機の真の重みは、モデルではなくその周辺——トークナイザー、ルーター、KV cache、sampling、MoE expert配分、システムプロンプト、effortポリシー——すべてのノブが同時に非決定的に作動するという点にある
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

## 序論 — Claudeは本当にナーフされたのか

Claude Opus 4.6はしばらくの間、コーディング作業の基準線を一段階引き上げたと評価されていました。コードベース全体を投げつけても文脈を掴み、難しいリファクタリングを一発で終え、ツール呼び出し間の推論もクリーンでした。ところが2026年2月から異常な信号が蓄積され始めました。**思考の深さ73%減少、トークン消費量122倍増加、Stop hook violation 0→43件/日、Bedrockコスト急増、ハルシネーション・gaslight・circular argumentの報告が殺到。** そして4月23日、Anthropicが1か月にわたる潜水艦パッチを公式に認めました。

過去1年間の主な出来事を挙げるだけでも、以下のようなものがあります。

- **Replit AI**がコードフリーズ中にproduction DBを削除し、4,000件の偽ユーザーデータを生成した事件（2025.07）
- **Google Gemini CLI**がmkdirの失敗を無視し、頭の中の偽ファイルシステムを基準にユーザーのフォルダを丸ごと削除した事件（2025.07）
- **CursorのClaude Opus 4.6エージェント**がRailway APIトークンを発見し、9秒でproductionボリュームを削除した**PocketOS事件**（2026.04）
- **Anthropic 4月23日ポストモーテム** — reasoning effort ダウングレード + thinking clearバグ + verbosityプロンプト、1か月間の潜水艦パッチ3件を公式認定（2026.04.23）
- **Opus 4.7 max effortハルシネーション急増** — リリース24時間以内にr/ClaudeAIで報告が殺到、GitHub Issue #52149「max effortがmid-sessionでsilent downgrade」（2026.04.18〜）
- **Opus 4.7トークナイザー変更** — 英語・コードのトークン使用量が実測1.47倍増加、セッションあたり20〜30%の追加コスト
- **2024年8月Claudeインフラバグ** — コンテキストウィンドウのルーティングエラーでClaude Codeユーザーの30%が影響を受けた1年前の事件。**今回が初めてではないという事実**が重要

表面上は異なる事件ですが、内側を分解すると**同じメカニズム群の異なる表現**です。Transformerアーキテクチャ自体の限界、RLHFが形成した報酬信号、autoregressive生成の累積誤差、attentionの不均一な分布、MoEルーティングの非決定性、KV cacheメモリ圧力、sampling非決定性、そしてその上でツールを手にして行動するエージェント構造。この記事は、最も内側——Transformerがトークンを作る仕組み——から始め、学習・メモリ・障害メカニズム・実際の事例・構造的洞察まで一気に追っていきます。

質問をもう一度投げかけてみます。**モデルは本当にナーフされたのか、それともモデルの周辺にあるすべてのノブが微妙に動いた結果を私たちがナーフと体感しているのか。** 答えは両方です。そしてそれこそがより恐ろしい事実です。

---

## Part 1: Transformerはどのようにトークンを作るのか — 最も内側の動作原理

LLMの思考を理解するには、最も内側から見ていく必要があります。モデルが1つのトークンを作るために経るプロセス——Tokenizer → Embedding → Attention → Sampling——の各段階が、後述するすべての障害モードの根源です。そしてフロンティアモデルが運用されるインフラ——MoEルーティング、KV cache管理——もここに直結しています。

### 1-1. Transformer 1枚まとめ

LLMの心臓は**Transformerアーキテクチャ**です。2017年にGoogleが発表した"Attention Is All You Need"（Vaswani et al., NeurIPS 2017）から始まり、現在のすべてのフロンティアLLMがこの上に積み上げられています。もともとは機械翻訳用のencoder-decoder構造でしたが、GPTシリーズを経て**decoder-only autoregressive**構造が標準になりました。1つのトークンが作られるまでの流れは次のとおりです。

<div class="diagram-wrap" style="margin:1.5rem 0;">
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:0.5rem;">
    <div style="background:linear-gradient(135deg,rgba(99,102,241,0.14),rgba(99,102,241,0.04));border:1px solid rgba(99,102,241,0.35);border-radius:10px;padding:0.8rem;">
      <div style="font-size:11px;font-weight:700;color:#6366f1;letter-spacing:0.5px;">STAGE 1</div>
      <div style="font-size:13px;font-weight:600;margin:0.3rem 0;">Tokenizer</div>
      <div style="font-size:11px;line-height:1.5;opacity:0.8;">テキスト → 整数IDシーケンス（BPE基準）</div>
    </div>
    <div style="background:linear-gradient(135deg,rgba(14,165,233,0.14),rgba(14,165,233,0.04));border:1px solid rgba(14,165,233,0.35);border-radius:10px;padding:0.8rem;">
      <div style="font-size:11px;font-weight:700;color:#0ea5e9;letter-spacing:0.5px;">STAGE 2</div>
      <div style="font-size:13px;font-weight:600;margin:0.3rem 0;">Embedding + PE</div>
      <div style="font-size:11px;line-height:1.5;opacity:0.8;">ID → 高次元ベクトル + 位置情報</div>
    </div>
    <div style="background:linear-gradient(135deg,rgba(34,197,94,0.14),rgba(34,197,94,0.04));border:1px solid rgba(34,197,94,0.35);border-radius:10px;padding:0.8rem;">
      <div style="font-size:11px;font-weight:700;color:#22c55e;letter-spacing:0.5px;">STAGE 3</div>
      <div style="font-size:13px;font-weight:600;margin:0.3rem 0;">N × Self-Attention</div>
      <div style="font-size:11px;line-height:1.5;opacity:0.8;">すべてのトークンが互いを見る（数十〜数百層）</div>
    </div>
    <div style="background:linear-gradient(135deg,rgba(234,179,8,0.14),rgba(234,179,8,0.04));border:1px solid rgba(234,179,8,0.35);border-radius:10px;padding:0.8rem;">
      <div style="font-size:11px;font-weight:700;color:#eab308;letter-spacing:0.5px;">STAGE 4</div>
      <div style="font-size:13px;font-weight:600;margin:0.3rem 0;">Output Projection</div>
      <div style="font-size:11px;line-height:1.5;opacity:0.8;">vocab（10万〜20万）の確率分布</div>
    </div>
    <div style="background:linear-gradient(135deg,rgba(244,114,182,0.14),rgba(244,114,182,0.04));border:1px solid rgba(244,114,182,0.4);border-radius:10px;padding:0.8rem;">
      <div style="font-size:11px;font-weight:700;color:#f472b6;letter-spacing:0.5px;">STAGE 5</div>
      <div style="font-size:13px;font-weight:600;margin:0.3rem 0;">Sampling</div>
      <div style="font-size:11px;line-height:1.5;opacity:0.8;">temperature, top-p, top-k → 次のトークン</div>
    </div>
  </div>
</div>

この5ステージが1トークンごとに繰り返されます。200トークンの応答なら、このサイクルが200回回ります。各段階に非決定性・障害の可能性が入り込む余地があります。

### 1-2. Self-Attentionの数式と意味

self-attentionの核心数式は、Vaswani et al.（2017）が定義した**scaled dot-product attention**です。

$$\text{Attention}(Q, K, V) = \text{softmax}\left(\frac{QK^\top}{\sqrt{d_k}}\right)V$$

各トークンは3つのベクトルで表現されます。

- **Query (Q)**: このトークンが何を探しているか
- **Key (K)**: このトークンが持つ情報の種類
- **Value (V)**: このトークンが実際に持っている情報

QとKの内積がattentionスコアになります。softmaxを通ると合計が1の分布になり、その分布でVを加重平均すると「今のトークンが他のトークンから何を引き出したか」が得られます。実際のモデルでは、これを複数のheadで並列に実行する**Multi-Head Attention**が使われます——各headが異なる種類の関係（文法・意味・位置）を学習するように。

推論効率のための後続変形も知っておく価値があります。

- **Grouped-Query Attention (GQA)**（Ainslie et al., 2023）: 複数のquery headがKV headを共有。KV cacheサイズを削減してlong context推論速度を向上。Llama 2 70B、Mixtralなどが採用
- **Multi-Query Attention (MQA)**（Shazeer, 2019）: GQAの極端バージョン。1つのKV headのみ使用
- **Rotary Position Embedding (RoPE)**（Su et al., 2021, RoFormer）: 絶対位置ではなく回転を通じて相対位置をエンコード。コンテキスト拡張（YaRN、NTK scaling）に有利で、ほぼすべての現代LLMが採用

ここで2点押さえておく必要があります。

**第一に、すべてのトークンがすべてのトークンを見る（full attention）。** これがlong contextのコストを$O(n^2)$にします。100Kトークンなら100億回のattention計算です。**これがKV cacheメモリ圧力の根源**であり、sliding window（Beltagy et al., 2020 "Longformer"; Mistral 7BのSliding Window Attention）、KV cache eviction（Zhang et al., 2023 "H2O"）といった最適化が登場した理由です（詳しくはPart 3で）。

> ### ちょっと待って、ここは押さえよう
>
> **「$O(n^2)$がなぜそんなに大きな問題なのか？ 100Kなら単に少し長いだけでは？」**
>
> 100Kトークンを処理するとは、attentionの1層あたり100,000 × 100,000 = **100億個のスコア**を計算することを意味します。そしてモデルはこれを数十〜数百層で繰り返します。トークンを2倍にすると計算は4倍になり、メモリもそれだけ多く消費します。
>
> これは単に遅くなるという意味ではありません。**GPUメモリが物理的に不足する地点**が生まれます。その地点がコンテキストウィンドウの真の上限であり、各社が宣伝する「200Kコンテキスト」は通常その上限付近で曲芸のように運用されています。そのため、インフラ圧力がかかると最初に手が入るのがKV cacheポリシーであり、それがユーザーの視点から「突然モデルが昔の会話を忘れた」として現れます。

**第二に、attentionは「soft selection」です。** softmaxが出力するのはhard選択ではなく分布です。すべてのトークンが常に一部の重みを受け取り、あるトークンはほぼ0に近い重みを受け取ります。この分布がどのように形成されるかがモデルの動作を決定します——そして私たちがlost-in-the-middle（Liu et al., 2023）、attention decay、システムプロンプト弱体化で見ることになるすべての現象が**この分布の不均一性**の表れです。

> **参考論文**
> - Vaswani et al. (2017), "Attention Is All You Need," *NeurIPS 2017*
> - Su et al. (2021), "RoFormer: Enhanced Transformer with Rotary Position Embedding"
> - Ainslie et al. (2023), "GQA: Training Generalized Multi-Query Transformer Models from Multi-Head Checkpoints"
> - Beltagy et al. (2020), "Longformer: The Long-Document Transformer"

### 1-3. Tokenizer — モデルの口と耳、そしてコストの根源

LLMは文字を処理しません。**トークン**を処理します。トークンはBPE（Byte-Pair Encoding、Sennrich et al., ACL 2016 "Neural Machine Translation of Rare Words with Subword Units"）のようなアルゴリズムで学習されたサブワード単位です。BPEはもともと1994年のデータ圧縮アルゴリズムでしたが、NMTに導入されてLLMの標準となりました。変形もあります。

- **WordPiece**（Schuster & Nakajima, 2012; BERTが採用）
- **SentencePiece**（Kudo & Richardson, EMNLP 2018）: 言語非依存トークナイザー、T5/Llamaが採用
- **Unigram Language Model**（Kudo, 2018）: 確率ベースの候補分割
- **Tiktoken**: OpenAIのBPE実装、GPT-3.5/4トークナイザー
- **Byte-level BPE**: GPT-2が導入、すべてのUnicodeをbyteで処理

英語の"tokenizer"は通常1〜2トークンです。日本語の「トークナイザー」は4〜6トークンになる場合があります。これは偶然ではなく**学習データの分布**の結果です。BPEは頻度ベースでトークンを作るため、英語が圧倒的な学習データで学習されたトークナイザーは、英語を効率的に、CJK・アラビア語などを非効率にエンコードします。

この非対称性は学術的にも整理されています。**Petrov et al.（2023）"Language Model Tokenizers Introduce Unfairness Between Languages"**（NeurIPS 2023）は、同じ意味の文が言語によってトークン数が最大15倍異なる可能性があることを示しました。つまり、同じ価格体系のもとで非英語圏のユーザーが名目単位あたり最大15倍高くLLMを使っているということです。

トークナイザーは単なる前処理ではありません。モデル能力の一部です。トークン境界がどこに引かれるかによって、モデルは同じテキストを異なる方法で見ます（数値表現、コードのindentation、URLがトークン境界によって異なる処理を受けるよく知られた落とし穴があります）。そしてモデルの重みをそのままにしてトークナイザーだけを変えると——**ユーザーの視点では同じモデルなのにコストが変わります**。まさにこれがOpus 4.7リリースで起きたことです（Part 5-6で詳しく扱います）。

> **参考論文**
> - Sennrich et al. (2016), "Neural Machine Translation of Rare Words with Subword Units," *ACL 2016*
> - Kudo & Richardson (2018), "SentencePiece: A simple and language independent subword tokenizer"
> - Petrov et al. (2023), "Language Model Tokenizers Introduce Unfairness Between Languages," *NeurIPS 2023*

| 計測次元 | 4.6トークナイザー | 4.7トークナイザー（実測） | 変化 |
|---|---|---|---|
| 英語/コードトークン使用量 | 基準 | 1.45〜1.47倍 | **47%増加** |
| CJK（韓・中・日）トークン | 基準 | 1.01倍 | ほぼ変化なし |
| セッションあたりコスト | 基準 | +20〜30% | 同一価格体系で |
| Anthropic公式発表 | — | 1.0〜1.35倍 | **実測より低く発表** |

トークナイザーの変更はモデルカードに1行で記載されますが、ユーザーへの請求書には一桁台%の差が現れ始めます。

### 1-4. Sampling — 非決定性の真の根源

モデルの最終出力はvocabサイズ（通常50K〜200K）の確率分布です。次のトークンをどのように選ぶかがsampling戦略です。この領域は学術的によく整理されています。

- **Greedy（temperature=0）**: 常に最も高い確率のトークン。決定的だが反復的で単調という限界
- **Beam Search**（Sutskever et al., 2014）: 複数の候補シーケンスを並列で維持。NMTでは標準だがテキスト生成では「blandness問題」
- **Temperature scaling**: $p'_i \propto p_i^{1/T}$。T>1なら分布の平坦化、T<1なら尖鋭化
- **Top-k Sampling**（Fan et al., ACL 2018, "Hierarchical Neural Story Generation"）: 上位k個のみ候補に
- **Top-p / Nucleus Sampling**（Holtzman et al., ICLR 2020, "The Curious Case of Neural Text Degeneration"）: 累積確率がpに達するまでのトークンのみ候補に。**現在事実上の標準**
- **Min-p Sampling**（Nguyen et al., 2024, "Min-p Sampling: Balancing Creativity and Coherence"）: 最高確率の一定割合以上のみ候補に

Holtzman et al.（2020）が投げた問いが決定的です。「なぜhigh-qualityな言語モデルのgreedy decodingが人間テキストより*より可能性の高い*シーケンスを作るのに、そのシーケンスが人間テキストより*不自然に*感じられるのか。」答えは人間が常に最も可能性の高い単語を選ぶわけではないということであり、これがnucleus samplingが採用される根拠となりました。

このsampling段階が**LLM非決定性の真の根源**です。同じプロンプト、同じモデルの重み、同じKV cacheでも、sampling RNGが異なれば異なる答えが返ってきます。潜水艦パッチの測定が難しい理由の大部分がここにあります——昨日と今日の答えが違うのが、モデルが変わったのかsampling偶然なのか、ユーザーには区別がつきません。

ここにさらに一つ陰険な変数があります。**2024年8月のClaudeインフラバグ**の事例です。XLA:TPUコンパイラ内部の"approximate top-k"最適化にバグがあり、これがトークン選択において最上位確率トークンを欠落させました。ユーザーの視点では「なぜ突然モデルが馬鹿になったんだ？」でしたが、原因は**推論インフラのGPU/TPUコード1行**でした。モデル自体は正常でした。

> **参考論文**
> - Fan et al. (2018), "Hierarchical Neural Story Generation," *ACL 2018*
> - Holtzman et al. (2020), "The Curious Case of Neural Text Degeneration," *ICLR 2020*
> - Nguyen et al. (2024), "Min-p Sampling: Balancing Creativity and Coherence at High Temperature"

### 1-5. Mixture of Experts — 大型モデルの秘密、そしてルーティング非決定性

GPT-4以降、ほぼすべてのフロンティアモデルは**Mixture of Experts（MoE）**構造と推定されています（GPT-4、Mixtralは公式確認済み、Claudeシリーズは非公開だが業界の推定）。モデルのパラメータが数百〜数千個の「expert」に分かれており、各トークンごとにrouterがどのexpertを活性化するかを決定します。

MoEは学術的によく整理された分野です。核心的な論文の流れは次のとおりです。

- **Shazeer et al.（2017）** "Outrageously Large Neural Networks: The Sparsely-Gated Mixture-of-Experts Layer" — sparse MoEの始まり。Top-2 gating、load balancing lossを導入
- **Fedus et al.（2021）** "Switch Transformers: Scaling to Trillion Parameter Models with Simple and Efficient Sparsity" — Top-1 gatingで単純化、1.6Tパラメータまで拡張
- **Lepikhin et al.（2020）** "GShard" — 分散学習でexpertをどのように配置するかのシステム設計
- **Jiang et al.（2024）** "Mixtral of Experts" — 8 expert × 7B、推論時2個を活性化。open-source MoEの標準

メリットは明確です。理論上は1兆個のパラメータを持つモデルですが、1トークンの処理には50Bのみ活性化されるといった具合です。同じ学習コストでより大きなcapacityが得られます。Switch Transformer論文によれば、同じcomputeでdenseモデル比7倍速い学習が可能です。

副作用も明確です。

- **ルーティング非決定性**: 同じ入力でもバッチ構成によって異なるexpertにルーティングされることがある（load balancingのため）。同じ時点、同じユーザーの2回の呼び出しが異なる「submodel」を経由する効果。**これがLLM非決定性のもう1つの層**
- **expert間の一貫性の欠如**: 推論中に異なるexpertが活性化されると、ペルソナが微妙に揺れる。Mixtral論文でもexpert specializationは明確に観察されないと報告されているが、ユーザー行動の次元では影響が報告されている
- **インフラ圧力**: GPUクラスターでrouterの負荷分散がlatencyに直結。コンピューティング圧力が強ければrouterポリシー自体が変わりうる（load優先 vs 品質優先）
- **Expert collapse**: 学習中に一部のexpertのみが使用される現象。auxiliary lossで緩和するが完全な解決は難しい

**2024年8月のClaudeインフラバグ**がこのリスクを最も鮮明に示しました。一部のリクエストが1Mコンテキスト用のサーバーに誤ってルーティングされ、ルーティングが**sticky**だったため、一度誤って割り当てられたユーザーは同じ誤ったサーバーから答えを受け続けました。結果的に**Claude Codeユーザーの30%が少なくとも一度影響を受け、Sonnet 4リクエストの16%で誤った出力**が返されました。英語の質問にタイ語・中国語文字が混入する出力破損まで報告されました。

この事件が伝えるメッセージは明確です。

> **モデルは重みだけではありません。ルーター、コンパイラー、KV cache管理者、sampling RNG、MoE分配器、負荷分散器——これらすべてが合わさったシステムがモデルです。** そのうちのどこか1か所に手を入れるだけで、ユーザー体験は揺らぎます。そしてユーザーにはそれがどこで起きたか知る術がありません。

この観点が、この記事のその後の全パートの基礎となります。学習（Part 2）も、メモリ（Part 3）も、事例（Part 5）も、すべてこのインフラの上で起きていることです。

> **参考論文**
> - Shazeer et al. (2017), "Outrageously Large Neural Networks: The Sparsely-Gated Mixture-of-Experts Layer," *ICLR 2017*
> - Fedus et al. (2021), "Switch Transformers: Scaling to Trillion Parameter Models with Simple and Efficient Sparsity," *JMLR*
> - Lepikhin et al. (2020), "GShard: Scaling Giant Models with Conditional Computation and Automatic Sharding"
> - Jiang et al. (2024), "Mixtral of Experts"

---

## Part 2: 学習と推論 — RLHFからAdaptive Thinkingまで

### 2-1. 学習パイプライン — Pretraining → SFT → RLHF

現代のLLMは3つのステップを経て作られます。

**Pretraining**はインターネット規模のテキストを使って次のトークンを予測するように学習するステップです。このとき、モデルは「正しい答え」を学習しません。ただ「この文脈の後によく現れるトークンの分布」を学習するだけです。このステップで作られたモデルは賢いけれども指示に従うことができず、不適切な出力も平然と返します。

**SFT（Supervised Fine-Tuning）**は人間が作成した高品質な（指示、応答）ペアでモデルを追加学習させます。このステップから「指示に従うモデル」になります。

**RLHF（Reinforcement Learning from Human Feedback）**が最も決定的なステップです。人間の評価者にモデルが作った応答を2つ比較させ、どちらが良いかをラベリングします。そのラベルで報酬モデル（Reward Model、RM）を学習させ、そのRMのスコアを最大化するようにPPOやDPOのようなアルゴリズムでモデルを最適化します。Anthropicはここに変形を加えており、人間のラベリングの代わりにモデルがあらかじめ定義された原則を参照して自分の応答を批判させる**Constitutional AI**です。よく混同される点を押さえておくと——**CAIはRLHFの*代替*ではなく*補完*です。** Anthropicは純粋なRLHF + CAI（=RLAIF）の両方を一緒に使います。CAIはRLHFパイプラインの1コンポーネント（人間のラベリング）をAIのラベリングに置き換えた変形であり、RLHF自体を使わないわけではありません。そのため、後述の4-1で登場するシコファンシーのようなRLHFの副作用は、Anthropicのモデルでも同様に機能します——Sharma et al.（2023、Anthropic共著）がClaude 1.3・Claude 2を*RLHFモデルとして*評価して実証した結果がその直接的な証拠です。

> ### ちょっと待って、ここは押さえよう
>
> **「Constitutional AIはそれでRLHFと何が違うのか？ それがなぜトークンコストの話と繋がるのか？」**
>
> RLHFは人間がラベリングした選好データで報酬モデルを学習させます。Constitutional AI（CAI）はその人間ラベリングステップを**モデルの自己批判に置き換え**ます。モデルが答えを作ると、あらかじめ定義された原則（「役に立て、害を与えるな、正直であれ」といったもの）を基準に自分の答えを批判し、書き直させます。人を使わないのでスケールはしやすいですが、副作用があります。
>
> **すべての答えに自己批判の推論が入る**ということは、ユーザーに答えを返す前にモデルが内側でもう一度推論を回すという意味です。その推論はthinkingトークンの形であれ、重みの次元に学習された保守性であれ、どこかにコストとして積み重なります。GPT系よりClaudeが同じ答えにトークンをより多く使う傾向がある構造的な理由の1つがここにあります。安全性は良くなっても、そのコストが誰に転嫁されるかは別途検討する必要があります。

ここで最も重要な事実を1つ押さえておく必要があります。

> **RLHFは「正しい答え」を学習させるのではありません。「人間が良いと評価する答え」を学習させます。**

この違いが、後から登場するすべての障害モードの根源です。人間の評価者は自分の意見に同調する答えを良く評価する傾向があります（シコファンシー）。自信ありげな答えを正確な答えと勘違いします。長くて形式が整った答えを単純な答えより好みます。RLHFはこのような人間の偏向をそのまま重みに刻みます。これはプロンプトで直せない、**fine-tuningされた重みの分布の属性**です。

<div class="diagram-wrap" style="margin:1.8rem 0;">
  <div class="rlhf-flow" style="display:grid;grid-template-columns:repeat(4,1fr);gap:0.6rem;align-items:stretch;">
    <div class="rlhf-step" style="background:linear-gradient(135deg,rgba(99,102,241,0.12),rgba(99,102,241,0.04));border:1px solid rgba(99,102,241,0.35);border-radius:10px;padding:0.9rem 0.8rem;">
      <div style="font-size:11px;font-weight:700;color:#6366f1;letter-spacing:0.5px;">STEP 1</div>
      <div style="font-size:14px;font-weight:600;margin:0.3rem 0;">Pretraining</div>
      <div style="font-size:12px;line-height:1.5;opacity:0.85;">次のトークン予測<br/>インターネット規模テキスト<br/><strong>学習目標 = 分布模倣</strong></div>
    </div>
    <div class="rlhf-step" style="background:linear-gradient(135deg,rgba(14,165,233,0.12),rgba(14,165,233,0.04));border:1px solid rgba(14,165,233,0.35);border-radius:10px;padding:0.9rem 0.8rem;">
      <div style="font-size:11px;font-weight:700;color:#0ea5e9;letter-spacing:0.5px;">STEP 2</div>
      <div style="font-size:14px;font-weight:600;margin:0.3rem 0;">SFT</div>
      <div style="font-size:12px;line-height:1.5;opacity:0.85;">人間作成（指示、応答）<br/>指示に従う学習<br/><strong>学習目標 = 模倣</strong></div>
    </div>
    <div class="rlhf-step" style="background:linear-gradient(135deg,rgba(34,197,94,0.12),rgba(34,197,94,0.04));border:1px solid rgba(34,197,94,0.35);border-radius:10px;padding:0.9rem 0.8rem;">
      <div style="font-size:11px;font-weight:700;color:#22c55e;letter-spacing:0.5px;">STEP 3</div>
      <div style="font-size:14px;font-weight:600;margin:0.3rem 0;">Reward Model</div>
      <div style="font-size:12px;line-height:1.5;opacity:0.85;">応答ペア比較ラベリング<br/>人間選好のスコア化<br/><strong>学習目標 = 選好予測</strong></div>
    </div>
    <div class="rlhf-step" style="background:linear-gradient(135deg,rgba(244,114,182,0.14),rgba(244,114,182,0.04));border:1px solid rgba(244,114,182,0.4);border-radius:10px;padding:0.9rem 0.8rem;">
      <div style="font-size:11px;font-weight:700;color:#f472b6;letter-spacing:0.5px;">STEP 4</div>
      <div style="font-size:14px;font-weight:600;margin:0.3rem 0;">RLHF / DPO</div>
      <div style="font-size:12px;line-height:1.5;opacity:0.85;">RMスコア最大化<br/>PPOまたはDPO<br/><strong>学習目標 = proxy最適化</strong></div>
    </div>
  </div>
  <div style="margin-top:0.9rem;padding:0.7rem 1rem;background:rgba(244,114,182,0.08);border-left:3px solid #f472b6;border-radius:0 6px 6px 0;font-size:13px;line-height:1.6;">
    <strong>Goodhart's Law:</strong> 測定値が目標になった瞬間、それはもはや良い測定値ではない。RMは真の目標（有用性・正確性・安全性）の<em>代理指標</em>にすぎないが、モデルは真の目標ではなくRMを最大化する方法を学ぶ。
  </div>
</div>

### 2-2. Autoregressive生成とfirst-token commitment

LLMはトークンを**1つずつ**作ります。そして一度出力したトークンは取り消せません。次のトークンを作るとき、自分が以前出力したすべてのトークンを再び入力として受け取るためです。

数式で書くとこうなります。

$$
P(y_1, y_2, \dots, y_T \mid x) = \prod_{t=1}^{T} P(y_t \mid x, y_1, \dots, y_{t-1})
$$

ここで重要なのは$y_t$が$y_1, \dots, y_{t-1}$に条件付けられているという点です。**モデルは自分が出力したトークンとユーザーが与えたトークンを区別しません。** 両方ただのコンテキストです。

この構造から**first-token commitment**という現象が発生します。モデルが回答の最初のトークンを「Yes」で始めると、以降のすべてのトークンは「Yes」を正当化する方向に流れていきます。最初のトークンを「No」で始めるとその逆です。一度方向を決めると、それを覆すことが非常に難しくなります——覆すには自分の出力を否定する必要がありますが、学習分布の中で「さっき言ったことを否定するパターン」はまれなためです。

なぜ危険なのか。推論チェーンの初期に小さな誤解が入り込むと、その上に50トークン、100トークンの精巧な推論が積み重なります。モデルは自分の出力を事実として処理するため、最終的には**自分の嘘を根拠にしてより尤もらしい嘘を作るループ**に陥ります。これがreasoning chain amplificationです。

### 2-3. Chain of ThoughtとExtended Thinking

**Chain of Thought（CoT）**は2022年にGoogleのWeiらが発表した手法です。「Let's think step by step」という1行を追加しただけで算数の問題の精度が大きく向上したという発見でした。モデルに推論過程をトークンとして出力させると、より難しい問題を解けるということです。

CoTが機能する理由は単純です。モデルがトークンをより多く生成するほど使用可能な「計算量」が増えます。1回のforward passでは解けない問題も、中間結果をトークンとして出力しながらそのトークンを次の推論の入力として使えば解けます。これを**test-time compute scaling**と呼びます。

**Extended Thinking**（Claude 3.7から、OpenAI o1から）はこのアイデアを極限まで押し進めた形です。モデルがユーザーに回答を返す前に、長い「thinking」トークンを生成します。これらのトークンはユーザーに見えないか、要約のみ見えます。RLで正解を出すよう追加学習され、問題によってはthinkingの分量が数万トークンに達します。

ここには2つの深い落とし穴があります。

**第一に、CoTは実際の推論を反映しない可能性があります。** 2023年のTurpinらの論文"Language Models Don't Always Say What They Think"は、CoTの出力がモデルの真の推論経路と異なる可能性があることを示しました。答えはすでに決まっていて、CoTは事後的な自己合理化に近い可能性があるということです。

**第二に、thinkingが長くなるほど自己合理化ループに陥りやすくなります。** 最初の1,000トークンで誤った前提に基づいた推論は、次の9,000トークンの間にその前提を正当化します。長く考えるほど正確になるわけではなく、むしろ**誤った結論をより尤もらしく見せる**ために使われる可能性があります。

この2つ目の落とし穴は単純な直観ではなく、学術的に整理された結果でもあります。2025年7月に発表された**"Inverse Scaling in Test-Time Compute"**（arXiv:2507.14417、Anthropic共著）は、reasoning トークンをより多く与えるほど精度が*下がる*5つの障害モードを整理しました。その最初が「Claudeモデルはreasoningが長くなるほど無関係な情報にdistractedされる」です。同年9月の"Test-Time Scaling in Reasoning Models Is Not Effective for Knowledge-Intensive Tasks Yet"（arXiv:2509.06861）は14個のreasoningモデルを評価して、**test-time computeの増加が精度向上につながらないだけでなく、ハルシネーションを増やす可能性があること**を示しました。モデルがより多く考えながらconfirmation biasで自分のprior beliefを支持するディテールをfabricateするということです。

> ### ちょっと待って、ここは押さえよう
>
> **「それでreasoningモデルは通常のモデルと異なる種類のニューラルネットワークなのか？ トークンはどこでどのようにカウントされるのか？ thinkingはいつ有効になるのか？」**
>
> 混乱しやすい3つを一度に整理します。
>
> **① モデルの種類 — すべて同じTransformerだ、重みの分布が違うだけだ**
>
> | ステップ | 標準用語 | 何 | 例 |
> |---|---|---|---|
> | Pretrained | **Base / Foundation model** | 次のトークン予測のみ学習されたraw重み | LLaMA 2 base |
> | + 指示学習 | **Instruct / Chat model** | SFT + RLHFで指示に従うよう学習 | GPT-4o, Claude 3.5 Sonnet |
> | + thinking学習 | **Reasoning model** | 上記に加えRLで*thinkingトークン*を学習 | o1・o3、DeepSeek-R1、Claude with extended thinking |
>
> 核心はreasoningモデルが**別の種類のニューラルネットワークではない**という点です。同じTransformerにthinkingトークンを長く書くことが報酬を得るよう追加学習された重みの分布にすぎません。そこに**hybridモデル**があります——Claude Opus 4.7は1つのモデルの中でthinking on/offの両方をサポートします。o1シリーズはthinking専用で切れず、GPT-4oはthinkingがまったくないinstructモデルです。
>
> **② トークンカウント — 「あるモデルでのみトークンを使う」という区別はない**
>
> トークンはすべてのLLMの入出力単位そのものです。ただし課金の次元で3つのカテゴリに分かれます。
>
> | カテゴリ | 作成するコンポーネント | 課金 |
> |---|---|---|
> | Input tokens | ユーザー入力 → トークナイザーがトークン化 | 入力単価 |
> | Output tokens (visible) | メインモデルがユーザーに送った回答 | 出力単価 |
> | **Thinking tokens** | メインモデルがthinkingステップで生成 | 出力単価と同じrate |
>
> Thinkingを有効にした呼び出しでは課金 = input + visible output + thinkingをすべて合算します。ユーザーに見えるtraceは別のモデルが作った*要約*ですが、請求書はメインモデルの*原本thinking*トークン基準です（この非対称性は2-5で再度触れます）。
>
> **③ いつ動くのか — Claude APIの3つのモード**
>
> | モード | 呼び出し方 | 動作 |
> |---|---|---|
> | Thinking off | `extended_thinking` 未指定 | 通常のinstructモード。thinkingトークンなし |
> | Manual budget | `extended_thinking: { type: "enabled", budget_tokens: N }` | 正確にNトークンまでthinking |
> | Adaptive（4.6+デフォルト） | `extended_thinking: { type: "adaptive", effort: ... }` | **モデルが有効にするか・どれくらいするかを自己判断** |
>
> Adaptiveでは、effort=lowなら単純な質問でthinkingを*スキップ*することもあり、maxでもモデルが短くて良いと判断すれば短くなります。これが**2-4で本格的に扱う「effortはtoken budgetではなくbehavioral signal」の正確な意味**です。
### 2-4. Effortパラメータとadaptive thinking — 深さをモデルに委ねる

Extended Thinkingがリリース初期には、ユーザーが直接`budget_tokens`でthinkingの分量を指定する必要がありました。しかし適切なbudgetは問題ごとに異なるため、単純な質問に8,000トークンのthinkingを実行したり、難しい推論に1,000トークンしか与えなかったりするミスマッチが頻繁でした。

Anthropicがその代替として打ち出したのが**Adaptive Thinking + Effortパラメータ**です（現在Claude Opus 4.6、4.7、Sonnet 4.6、Mythos Previewでデフォルトまたは推奨モード）。

動作原理は次のとおりです。

- ユーザーはeffortを`low / medium / high（デフォルト） / max`の中から選ぶだけです（Opus 4.7は`xhigh`を追加）
- モデルがリクエストを受けると**自分でこの問題がthinkingを必要とするか、どれくらい必要かを判断**します
- Highではほぼ常にthinkingを有効にします。Lowでは単純な問題でthinkingをスキップすることもあります
- Maxではthinkingの分量の上限を大きく開放します

ここで最も重要なのが、Anthropicの公式ドキュメントが明示している1行です。

> **"Effort is a behavioral signal, not a strict token budget. At lower effort levels, Claude will still think on sufficiently difficult problems, but it will think less than it would at higher effort levels for the same problem."**
> — [Anthropic Docs, Effort parameter](https://platform.claude.com/docs/en/build-with-claude/effort)

同じドキュメントがより決定的に指摘している部分は、**max effortに対するAnthropicの自己警告**です。Opus 4.7の推奨effort表で、maxについてこのように書いています。

> **"Reserve for genuinely frontier problems. On most workloads `max` adds significant cost for relatively small quality gains, and on some structured-output or less intelligence-sensitive tasks it can lead to overthinking."**
> — [Anthropic Docs, Effort parameter — Recommended effort levels for Claude Opus 4.7](https://platform.claude.com/docs/en/build-with-claude/effort)

3点が一度に確認できます。

1. **effortはトークン予算ではなく行動シグナル** — maxに設定してもモデルがthinkingの深さを自己判断で調整します。ユーザーが購入したのは「正確にNトークンのthinking」ではなく「maxのラベル」にすぎません
2. **adaptive thinking自体が「thinkingはモデルにとってオプション」** — Adaptive Thinking公式ドキュメントの表現そのまま。max effortでもモデルが単純と判断すれば短くなる可能性があり、複雑と判断すればoverthinkingの領域に入る可能性もある
3. **maxはoverthinkingを引き起こす可能性がある** — Anthropicが自分のドキュメントで認めている。つまり「maxにしたら結果が悪化した」という体験は、ユーザー側の錯覚ではなく公式ドキュメントが予告していた動作

このデザインは優雅に見えますが、**新しい障害の表面を作ります**。

| 次元 | 手動 budget_tokens | Adaptive + Effort |
|---|---|---|
| 決定主体 | ユーザー | モデル自身 |
| 予測可能性 | 明確（決めた分量） | 非決定的（呼び出しごとに異なる） |
| コスト予測 | 可能 | 推定のみ可能 |
| Maxモードの意味 | 正確にNトークンまで | 「好きなだけ考えていい」 |
| 新しい障害モード | budget不足で打ち切られる | モデルが*overthinking*する可能性 |

核心は最後の行です。**モデルが「どうせmaxだからもっと考えていい」と判断すればinverse scalingの領域にそのまま入ります。** より多く考えてより正確になる領域と、より多く考えてよりハルシネーションを増やす領域の境界を、モデルが毎回正確に把握できる保証はありません。Effort=maxはユーザーの視点では「最高品質」のシグナルですが、モデルの視点では自己合理化とinverse scalingの領域に入る自由度を与えられたことでもあります。この非対称性が、5-5で扱うOpus 4.7 max effortハルシネーション事件の構造的背景です。

> ### ちょっと待って、ここは押さえよう
>
> **「effort=maxを選んでいれば、それが常に適用されるのでは？ ユーザーが「最高品質」を購入したはずでは？」**
>
> これが正確にGitHub Issue #52149が指摘した点です。ユーザーがmaxに設定していても、セッション中にシステムが**silentlymediumにダウングレード**される可能性が報告されました。ユーザーの操作なしに、通知なしに。
>
> それ自体も大きな問題ですが、より本質的な問題は別にあります。effortパラメータはユーザーが「どれだけ多く考えるか」の上限を与えるものであり、**下限を保証するものではありません**。maxに設定してもモデルが「この問題は単純だから短く答える」と決断すればそうなります。逆に本文で見たinverse scalingの領域では、maxがモデルに自己合理化の自由度を与えるシグナルとして機能します。**ユーザーが購入したのが正確に何なのかが定義されていない**というのが、Adaptive Thinkingデザインで最も微妙な落とし穴です。

### 2-5. Adaptive Thinkingの内部動作 — 学習と推論、そして分離されたモデル

ここまで出てきた「effortは行動シグナルだ」、「thinkingはオプションだ」といった表現は結果の描写にすぎず、**モデルの中で正確に何が起きているか**は別途見る必要があります。Anthropicがメカニズムを詳しく公開しているわけではありませんが、公式ドキュメントから直接引用できる事実と、同時期に公開されたreasoningモデルの学術資料を組み合わせると、輪郭は掴めます。

#### Thinkingは「別の何か」ではなくトークン生成だ

まず押さえておく点があります。**Thinkingは独立したシステムではありません。** 普通のトークン生成と同じメカニズムであり、ただ出力がthinking content blockとして分離されてユーザーに異なる形で表示されるだけです。Anthropicの公式ドキュメントの表現そのまま：

> "When extended thinking is turned on, Claude creates `thinking` content blocks where it outputs its internal reasoning. **Claude incorporates insights from this reasoning before crafting a final response.**"
> — [Anthropic Docs, Extended thinking](https://platform.claude.com/docs/en/build-with-claude/extended-thinking)

つまりモデルの視点でthinkingステップは**自分自身に送るトークン**です。forward passの構造は同じで、ただ「この区間はユーザーに答える前の自己推論用」というラベルが付いたトークンが前に追加生成されるだけです。これが**test-time compute scaling**の最も単純な形であり、Part 2-3で見たCoTの直系の後継でもあります。

#### 学習ステップ — どのように「いつ考えるか」をモデルが身につけたか

Anthropicはadaptive thinkingをどのように学習させたか詳しく公開していません。しかし同時期に公開されたreasoningモデルの資料が一般論を十分に示しています。

最も決定的な公開事例は**DeepSeek-R1**（DeepSeek-AI、2025年1月 arXiv:2501.12948、後に*Nature*に掲載）です。この論文が示した結果は衝撃的でした。

- DeepSeek-V3 Baseの上で**SFTなしにpure RLのみでR1-Zero**を学習
- 報酬は**最終正答の正確性**のみ（ground-truth比較）
- 推論過程自体にはいかなる制約も設けなかった
- 結果: **self-reflection、検証、動的戦略適応**がemergentに発現。AIME 2024の精度が15.6% → 71.0%、majority votingで86.7%まで

学習アルゴリズムは**GRPO（Group Relative Policy Optimization）**で、DeepSeekMath（2024）で提案されたPPOの変形です。核心は同じプロンプトに複数の答えをサンプリングした後、グループ内の相対的な順位でadvantageを計算するもの——value modelなしでも動作するためRLコストが大幅に削減されます。

> ### ちょっと待って、ここは押さえよう
>
> **「報酬が「正答か否か」だけなのに、なぜモデルが勝手に「長く考える/短く考える」を使い分けるようになるのか？」**
>
> RLの不思議な点が正確にここにあります。報酬はoutcomeのみ与えますが、そのoutcomeをより頻繁に当てるには、モデルが**難しい問題では長くthinkingを、簡単な問題では短く**という方針を持つことが平均報酬の観点から有利です。難しい問題を短く答えると間違え、簡単な問題を長く答えると脇道にそれたり時間が足りなくて間違えたりする可能性があります。
>
> そのため、outcome rewardだけでも「**問題の難易度にthinkingの分量を合わせる方針**」が自然に学習されます。DeepSeek-R1論文が明示的に報告したもの——emergent self-reflection、dynamic strategy adaptation——がまさにこの結果です。Anthropicが同じアルゴリズムを使っているかどうかは公開されていませんが、「thinkingをオプションにできる」という事実自体は、学術的にすでに実証されたメカニズムの上に立っています。

さらに**Process Reward Model（PRM）**のラインがあります。Lightman et al.（2023）"Let's Verify Step by Step"（arXiv:2305.20050）が示したのは、**各推論ステップごと**に報酬シグナルを与えると、outcome報酬よりも精確に「正しい推論経路」を学習させられるということでした。Outcome rewardは誤った推論で正解を当てても報酬を受けるという弱点がありますが、PRMはその弱点を補います。ただしステップごとのラベルを作るコストが大きいです。

Adaptive Thinkingを作るのにどちらがより使われたかは会社ごとに異なる可能性があり、Anthropicは公開していません。ただ**2つのラインがともに「thinkingの分量をモデルが決定するよう学習させるためのツール」**という点は共有されています。

#### 推論ステップ — Effortパラメータが内部で正確に何を変えるのか

この領域はAnthropicがほとんど公開していない部分なので、**確定できる部分と推定できる部分を区別**して押さえる必要があります。

**確定できる事実（公式ドキュメント引用）**

- Effortは**behavioral signalであってstrict token budgetではない**（Effortドキュメント）
- `max_tokens`はhard limit、effortは**soft guidance**。両方一緒に使える（Adaptive Thinkingドキュメント）
- High/maxの効力は「almost always thinks deeply」、lowは「may skip thinking for simpler problems」（公式の表現）
- Adaptiveモードは**interleaved thinking**を自動的に有効にする——ツール呼び出し*間*にもthinkingトークンが入る（Mythos Preview、Opus 4.7はinter-tool reasoningが常にthinking blockの中にある）

**推定できるメカニズム（学術的一般論 + 合理的推論）**

内部実装は公開されていませんが、effortのようなシグナルをモデルに注入する方法は学術的によく整理されています。

| 候補メカニズム | 動作方法 | 可能性 |
|---|---|---|
| **System promptの変形** | 「あなたは深く推論します」のような文句をeffortごとに異なる形で注入 | 最も単純。ほぼすべての会社が一部使用 |
| **Control / special token** | `<effort:max>`のようなcontrol tokenを入力に挿入、モデルがそのトークンの埋め込みを見て行動変化 | T5/PaLMなどでよく整理されたパターン |
| **Samplingパラメータ調整** | thinkingステップのtemperature・top-p・max lengthをeffortに応じて異なる設定 | 推論インフラの次元で最も直接的 |
| **Auxiliary classifier / router** | 別途分類器がeffort + 入力を見てthinking分量を決定し、その決定をモデルに注入 | 最も精巧だがインフラ負担が大きい |
| **学習されたeffort embedding** | 学習ステップでeffortラベルを一緒に学習、推論時にその埋め込みを活性化 | RLHF + control vectorパターンと互換 |

実際の実装はこの中の**複数の組み合わせ**である可能性が高いです。そしてこの組み合わせのどの部分がどのように変わったかが、私たちが見た**潜水艦パッチ（Part 5-4）**の正確な正体でもあります——Anthropic 4月23日ポストモーテムで認めた「verbosityシステムプロンプトの追加」は、この表の1番目のカードに触れたものです。

#### モデルは本当に1つなのか — Anthropicが認めた分離

最も興味深い部分はここです。ユーザーが呼び出したモデル1つがthinkingから回答まですべて処理しているように見えますが、**公式ドキュメントが明示的に分離を認めています。**

> "**Summarization is processed by a different model than the one you target in your requests. The thinking model does not see the summarized output.**"
> — [Anthropic Docs, Adaptive thinking — Summarized thinking](https://platform.claude.com/docs/en/build-with-claude/adaptive-thinking)

<div class="diagram-wrap" style="margin:1.5rem 0;">
  <div style="font-size:13px;font-weight:700;margin-bottom:0.8rem;opacity:0.9;">ユーザーが呼び出したモデル ≠ ユーザーが見るthinkingを作ったモデル</div>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:0.5rem;">
    <div style="background:linear-gradient(135deg,rgba(99,102,241,0.14),rgba(99,102,241,0.04));border:1px solid rgba(99,102,241,0.35);border-radius:10px;padding:0.85rem;">
      <div style="font-size:11px;font-weight:700;color:#6366f1;letter-spacing:0.5px;">STAGE 1 — REQUEST</div>
      <div style="font-size:13px;font-weight:600;margin:0.3rem 0;">ユーザー呼び出し</div>
      <div style="font-size:11px;line-height:1.55;opacity:0.8;">model: claude-opus-4-7<br/>thinking: adaptive<br/>effort: max</div>
    </div>
    <div style="background:linear-gradient(135deg,rgba(34,197,94,0.14),rgba(34,197,94,0.04));border:1px solid rgba(34,197,94,0.35);border-radius:10px;padding:0.85rem;">
      <div style="font-size:11px;font-weight:700;color:#22c55e;letter-spacing:0.5px;">STAGE 2 — MAIN MODEL</div>
      <div style="font-size:13px;font-weight:600;margin:0.3rem 0;">Thinkingトークン生成</div>
      <div style="font-size:11px;line-height:1.55;opacity:0.8;">ユーザーが指定したメインモデルが<strong>full thinking</strong>を生成。課金はこのトークン数基準。</div>
    </div>
    <div style="background:linear-gradient(135deg,rgba(234,179,8,0.14),rgba(234,179,8,0.04));border:1px solid rgba(234,179,8,0.35);border-radius:10px;padding:0.85rem;">
      <div style="font-size:11px;font-weight:700;color:#eab308;letter-spacing:0.5px;">STAGE 3 — SUMMARIZER</div>
      <div style="font-size:13px;font-weight:600;margin:0.3rem 0;">別のモデルが要約</div>
      <div style="font-size:11px;line-height:1.55;opacity:0.8;">Anthropic公式: <em>"different model"</em>。メインモデルはこの要約を見ない。</div>
    </div>
    <div style="background:linear-gradient(135deg,rgba(244,114,182,0.14),rgba(244,114,182,0.04));border:1px solid rgba(244,114,182,0.4);border-radius:10px;padding:0.85rem;">
      <div style="font-size:11px;font-weight:700;color:#f472b6;letter-spacing:0.5px;">STAGE 4 — RESPONSE</div>
      <div style="font-size:13px;font-weight:600;margin:0.3rem 0;">ユーザーに見えるtrace</div>
      <div style="font-size:11px;line-height:1.55;opacity:0.8;">thinkingブロック（要約）+ 最終応答。<strong>signature</strong>に原本thinkingが暗号化されてround-trip。</div>
    </div>
  </div>
  <div style="margin-top:0.9rem;padding:0.7rem 1rem;background:rgba(234,179,8,0.08);border-left:3px solid #eab308;border-radius:0 6px 6px 0;font-size:13px;line-height:1.65;">
    <strong>核心的な非対称性。</strong> 課金はメインモデルのfull thinkingトークン基準、ユーザーが見るtraceは別のモデルが作った要約。Anthropicの公式表現そのまま — <em>"the billed output token count will not match the count of tokens you see in the response."</em> つまりユーザーは自分が代金を払った推論を直接見ることができない構造だ。
  </div>
</div>

この1文が解き明かす重みは大きいです。

1. **ユーザーが呼び出したモデル（例: claude-opus-4-7）** — thinkingトークンを生成するメインモデル
2. **別の要約モデル（モデル識別子非公開）** — そのthinkingをユーザーに見せる要約に変換
3. **ユーザーが見るthinking trace = 要約**。原本は通常見られない（`display: "summarized"`がデフォルト値）
4. **課金はfull thinking tokens基準** — 要約トークンではなく*原本*基準
5. **要約モデルが作ったテキストはメインモデルが見ない** — 次のターンで再び入力されるときは`signature`に暗号化された原本thinkingが復号されて入る

> ### ちょっと待って、ここは押さえよう
>
> **「自分が見ているthinkingが、モデルが実際に行った推論と異なる可能性があるということか？」**
>
> 正確にそうです。ユーザーが見るthinkingは**別のモデルが作った要約**です。その要約モデルが小さいモデルである可能性が高く（高速処理のため）、メインモデルの推論の一部を省略したり言い換えたりしている可能性があります。Anthropicの公式ドキュメントも"*Summarization preserves the key ideas of Claude's thinking process*"と表現しています——すべてのディテールではなく*key ideas*のみ保存しています。
>
> デバッグの観点でこれが微妙に難しいです。ユーザーがthinkingを読んで「ああ、これで答えが間違っていたんだ」と分析しても、**その分析は要約の上の分析**です。メインモデルが実際にどの経路で進んだかを検証するには、エンタープライズアカウントでraw thinking へのアクセス権を別途取得するか、signature をデコードできる（現在はユーザーに閉じられた）経路を経る必要があります。これが2-3で見たTurpin et al.（2023）"Language Models Don't Always Say What They Think"が投げる重みをもう1層深くします——モデルが自分の推論を正確に報告しない可能性があるところに、*要約レイヤーがもう1層*介在しています。

さらにもう1つの分離があります。**Tokenizer**もモデルと分離されたコンポーネントです（Part 1-3）。Opus 4.6と4.7の間に重みは新たに学習されましたが、**トークナイザーも一緒に変わったという事実**自体が、システムが複数コンポーネントの組み合わせであることを改めて示しています。トークナイザー、thinkingモデル、要約モデル、ルーター、KV cache管理者——ユーザーが「Claude」と呼ぶのは実はこれらのコンポーネントの束です。

#### 学習-推論の整合とmismatch — Inverse Scalingはどこから来るのか

最後に押さえておく必要があるのが、**学習分布と推論分布がどれほど整合しているか**です。これがPart 2-3で見たinverse scalingの領域の構造的な根源です。

学習ステップでモデルが見たthinkingの分量の分布は学習データによって決まります。RLHF/RLのステップでは通常、数千〜数万トークンの範囲のthinkingを扱い、より長いthinkingは学習分布の裾にあります。ところがeffort=max + max_tokens=64,000のような組み合わせは、モデルを**学習分布の裾の向こう**へ押し込む可能性があります。

<div class="diagram-wrap" style="margin:1.5rem 0;background:rgba(127,127,127,0.04);border-radius:10px;padding:1rem 1.2rem;border:1px solid rgba(127,127,127,0.18);">
  <div style="font-size:13px;font-weight:700;margin-bottom:0.6rem;opacity:0.9;">Thinkingトークン長さの分布 — 学習 vs 推論</div>
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
      <text x="40" y="218" font-size="10" fill="currentColor" opacity="0.6">短い</text>
      <text x="540" y="218" font-size="10" fill="currentColor" opacity="0.6">非常に長い</text>
      <text x="310" y="240" font-size="11" fill="currentColor" opacity="0.7" text-anchor="middle">thinkingトークン長さ →</text>
      <text x="20" y="130" font-size="10" fill="currentColor" opacity="0.6" transform="rotate(-90, 20, 130)" text-anchor="middle">頻度</text>
      <rect x="450" y="60" width="130" height="140" fill="rgba(239,68,68,0.06)" stroke="rgba(239,68,68,0.4)" stroke-dasharray="4 3" stroke-width="1" rx="3"/>
      <text x="515" y="55" font-size="10" font-weight="700" fill="#ef4444" text-anchor="middle">OOD領域</text>
      <path d="M 40 200 Q 100 200 130 175 Q 175 95 240 80 Q 305 95 350 175 Q 380 200 450 200 L 450 200 Z" fill="url(#learnDist)" stroke="#22c55e" stroke-width="1.8" opacity="0.9"/>
      <text x="240" y="95" font-size="11" font-weight="600" fill="#22c55e" text-anchor="middle">学習分布</text>
      <text x="240" y="108" font-size="9" fill="#22c55e" opacity="0.85" text-anchor="middle">RL報酬が形成された領域</text>
      <path d="M 350 200 Q 410 200 450 192 Q 490 175 525 155 Q 555 138 575 130 L 575 200 Z" fill="url(#infDist)" stroke="#ef4444" stroke-width="1.8" opacity="0.9"/>
      <text x="525" y="148" font-size="11" font-weight="600" fill="#ef4444" text-anchor="middle">max effort</text>
      <text x="525" y="161" font-size="11" font-weight="600" fill="#ef4444" text-anchor="middle">+ long context</text>
      <path d="M 470 100 L 470 75" stroke="#ef4444" stroke-width="1.5" fill="none" marker-end="url(#arrowOOD)"/>
      <text x="498" y="92" font-size="9" font-weight="600" fill="#ef4444">inverse scaling</text>
    </g>
  </svg>
  <div style="margin-top:0.6rem;font-size:12.5px;line-height:1.7;opacity:0.88;">
    学習分布（緑）では長さごとに報酬がよく形成されている。ところがeffort=max + long contextの組み合わせは、モデルを学習分布の裾の向こう（赤いOOD領域）へ押し込む。<strong>学習で十分に見たことのない長さ</strong>では、モデルはself-conditioning、confirmation bias、distractor吸収といったinverse scaling障害モードにより頻繁に入る。これが「maxにしたら結果が悪化した体験」の学術的正体だ。
  </div>
</div>

| ステップ | 分布 |
|---|---|
| **学習分布** | 平均的なthinking長さ、RL報酬が適切に形成された領域 |
| **推論分布（通常）** | 学習と似た領域。性能が学習結果のまま出る |
| **推論分布（max effort + long context）** | 学習でほぼ見たことのない長さ。モデルの行動が定義されていない領域 |

学術的にはこれが**out-of-distribution generalization**の問題であり、"Inverse Scaling in Test-Time Compute"（Part 2-3引用）論文が整理した5つの障害モードがまさにこの領域で発現します。学習時に見たことのない長さのthinkingの中で、モデルは**自分の出力を次の入力として受け取るself-conditioning**サイクルに深く入り込み、そのサイクルでconfirmation bias・fabrication・distractor吸収が累積されます。

> Effort=maxは単に「もっと考えろ」ではなく、「**学習分布から遠く離れた場所まで行っていい**」というシグナルとして機能する可能性があります。それがAnthropicが自分のドキュメントに「max can lead to overthinking」と書いた理由の学術的正体です。

これがAdaptive Thinkingのデザインが優雅でありながら同時に危険な理由です。**ユーザーが購入したeffortのラベルが、学習ステップでは正確な意味を持っていません**——「max」というラベルに対応する学習行動が強く形成された領域と、ラベルだけあって学習が不十分な領域が混在しています。ユーザーはその差を呼び出し時点で知ることができず、結果がさまざまに出てくるのを非決定性として受け入れることになります。

> **参考論文**
> - DeepSeek-AI (2025), "DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning," *Nature* (arXiv:2501.12948)
> - Shao et al. (2024), "DeepSeekMath: Pushing the Limits of Mathematical Reasoning in Open Language Models" (arXiv:2402.03300) — GRPO原典
> - Lightman et al. (2023), "Let's Verify Step by Step" (arXiv:2305.20050) — Process Reward Model
> - Turpin et al. (2023), "Language Models Don't Always Say What They Think" (arXiv:2305.04388)

> ### ちょっと待って、ここは押さえよう
>
> **「RLHFとAdaptive Thinkingは同じものなのか？ どちらもRLなのに？」**
>
> どちらも「RL」がついているので混乱しやすいですが、**作動タイミングと役割がまったく異なります。**
>
> | 次元 | RLHF | Adaptive Thinking |
> |---|---|---|
> | 何 | **学習方法**（training-time） | **推論モード**（inference-time機能） |
> | いつ動くか | モデル学習時の1回のみ | ユーザー呼び出しのたびに毎回 |
> | 成果物 | 学習された重みの分布 | thinkingトークンを有効にするか・どれくらいするかの*動作* |
> | 導入時点 | 2017 RL技法 → 2022 InstructGPT | 2024 OpenAI o1 → 2025 Claude 3.7 |
>
> 関係はこのように整理されます。
>
> ```
> Pretraining → SFT → RLHF                 = 通常のinstructモデル（GPT-4o、Claude 3.5 Sonnet）
>                    + Reasoning RL         = Reasoningモデル（o1、Claude with thinking）
>                    + Adaptive学習         = thinkingの分量をモデルが自己決定
> ```
>
> つまり**Adaptive ThinkingはRLHF*の上にさらに追加で*実行したRLの結果**です。RLHFが「指示に従い人間の選好を満たすよう」学習したものなら、Adaptive Thinking RLは「thinkingの分量を問題の難易度に合わせて調整するよう」学習する追加ステップです——本文上のDeepSeek-R1 GRPOの説明がまさにこのメカニズムであり、outcome rewardだけ与えてもモデルが自然に分量調整を学ぶというのがその決定的な結果です。
>
> そしてフロンティア企業が同時に使うRLは3つになります。
>
> | ステップ | 何 | ラベル出典 |
> |---|---|---|
> | RLHF | 人間の選好比較 → RM → PPO/DPO | 人間 |
> | RLAIF（Constitutional AI） | AIが原則基準の自己批判 → RM → PPO | AI自体 |
> | Reasoning / Adaptive RL | 正答精度でthinking分量を学習 | outcome（正答 ground truth） |
>
> 3つは*互いの代替*ではなく*一緒に*適用されます。Claudeも同様——RLHFで一般的なinstruction-followingを学習した上にCAIで安全性を補強し、その上にReasoning RLでthinkingを追加学習した結果がClaude with extended thinkingです。

### 2-6. Self-ConsistencyとSelf-Rationalization

似ているように見えて正反対の結果をもたらす2つの概念を区別する必要があります。

**Self-Consistency**（Wang et al., 2022）はデバッグツールです。同じ質問に対してモデルを複数回サンプリングし（temperatureをやや上げて）、多数決で答えを決定します。真の正答は複数のサンプルで一貫して現れる一方、ハルシネーションは散らばります。よく機能しますが、モデル自体に組み込まれた**systematic bias**はすべてのサンプルに同様に影響するため、この方法では捕捉できません。

**Self-Rationalization**は障害モードです。モデルが一度stanceを取ると——答えであれ行動であれ——その後のすべての推論がそのstanceを正当化する方向に流れます。人間のmotivated reasoningとまったく同じパターンです。RLHFの重みに刻まれた「確信を持って話すのが良い答え」というシグナルが、自分の決定を疑わせません。

| 区分 | Self-Consistency | Self-Rationalization |
|---|---|---|
| 何 | 多数決デバッグ | 自己決定の正当化 |
| 作動タイミング | 答え導出後の検証 | 答え導出中 |
| 効果 | ハルシネーション一部除去 | 誤りの累積 |
| システムの次元 | 外部から追加 | モデル内部の属性 |
| 限界 | systematic biasは捕捉できない | 重みの次元なのでプロンプトでは防げない |

---

## Part 3: LLMのメモリシステム — どのように記憶し、なぜ忘れるのか

ここが人々が最も誤解する部分です。「コンテキストウィンドウ200K = 200Kトークンをすべて記憶する」ではありません。コンテキストウィンドウは**物理的に入力できる最大長**にすぎず、その中のすべてのトークンが同様に処理されるわけではありません。

### 3-1. コンテキストウィンドウとKV Cache

TransformerがトークンをProcessingするとき、各トークンはself-attentionを通じて以前のすべてのトークンと接続されます。この接続を毎回再計算するとコストがかかりすぎるため、以前のトークンのKeyとValueベクトルをキャッシュしておきます。これが**KV cache**です。

KV cacheはGPUメモリにそのまま載ります。コンテキストが長くなるほどキャッシュも大きくなり、ある地点でGPUメモリの限界に達します。このときシステムは2つのどちらかを選択します。

1. **物理的にこれ以上長く受け取れない** — コンテキストウィンドウがKVメモリの限界
2. **古いトークンをevict** — Sliding Window Attentionのような技法

長い会話を続けていると応答が徐々に遅くなる経験をされたことがあるかと思いますが、それがKV cacheが累積されてメモリ圧力を受けているシグナルです。ある時点からシステムが自動的に古いトークンのevictを開始します——そしてそれらのトークンには通常**システムプロンプト、最初の指示事項、安全ガイドライン**が含まれています。

> ### ちょっと待って、ここは押さえよう
>
> **「なぜよりによってシステムプロンプトがevictされるのか？ それが最も重要な情報ではないか？」**
>
> まさにそれが問題の核心です。システムプロンプトは**コンテキストの最初**に配置され、KV cacheが一定のウィンドウのみ維持するポリシー（sliding window、oldest-first evictionなど）では**最初に切り取られる位置**にあります。最も重要な情報が最も脆弱な位置にあるわけです。
>
> 一部のシステムはsystem promptを「pinned」として表示してevict対象から除外しますが、それでも**attention分布の次元で埋もれる現象**は防げません（3-2のlost in the middleを参照）。evictされなくても「事実上無視される」状態に入ります。agenticワークフローでターン30付近でガードレールが揺らぎ始めるという業界の観察の根源がここにあります。

### 3-2. Attentionの不均一な分布 — Lost in the Middle

2023年のLiuらの論文"Lost in the Middle: How Language Models Use Long Contexts"は衝撃的な結果を報告しました。コンテキスト長が長くなるほどモデルの性能が単調に低下するのではなく、**U字型カーブ**を描くということです。

<div class="chart-wrapper" style="background:rgba(127,127,127,0.05);border-radius:10px;padding:1rem 1.2rem;border:1px solid rgba(127,127,127,0.18);margin:1.5rem 0;">
  <div class="chart-title" style="font-size:13px;font-weight:700;margin-bottom:0.5rem;opacity:0.9;">Lost in the Middle — 正答位置別retrieval精度（例示）</div>
  <canvas id="lostInMiddleChart" height="200"></canvas>
</div>

<script>
window.chartConfigs = window.chartConfigs || [];
window.chartConfigs.push({
  id: 'lostInMiddleChart',
  type: 'line',
  data: {
    labels: ['1番目','5番目','10番目','15番目','20番目の文書'],
    datasets: [{
      label: '20-document retrieval精度',
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

核心情報がコンテキストの**始まりか終わり**にあるとき、モデルはうまく見つけます。ところが**中間**にあるときは精度が大きく低下します。始まりと終わりの情報を強く処理するのはattentionのpositional biasによるもので、これは学習データの分布から自然に生まれたパターンです——通常、人も文章の導入部と結論に核心を置きます。

なぜこれがメモリシステムの問題になるのか。システムプロンプト（ガードレール、ペルソナ、ツール使用規則）は**コンテキストの始め**にあります。始めにあるから強くattendされそうですが、ユーザーメッセージが長くなりツール呼び出しが累積されthinkingトークンが積み重なる間に、システムプロンプトは**相対的に埋もれていきます**。コンテキストが100Kトークンになると、最初にある1Kトークンのシステムプロンプトのattention比率は急激に下がります。

業界の経験則では「**system promptがターン30付近でbindingをやめる**」という表現がよく出ます。agenticループで30ターンほどツール呼び出しが累積されると、システムプロンプトのガードレールが事実上無力化されるという観察です。

### 3-3. Sliding Window AttentionとForcedされた忘却

より長いコンテキストを処理するために、一部のモデルは**Sliding Window Attention（SWA）**を使います。すべてのトークンがすべての以前のトークンにattendするのではなく、**直近のNトークンのみ**にattendします。ウィンドウがスライドすることで古いトークンはattentionから外れます。

メモリ効率は良いですが、副作用が明確です。

> **ウィンドウの外に押し出されたトークンは永遠に忘れられます。**

ストリーミング生成をするとして——本1冊を一度に生成するのにウィンドウが1章分しかないなら、第1章の設定が第5章で忘れられます。名前が変わり、キャラクターの性格が揺れ、3章で死んだ人物が7章で生き返ります。

agenticコンテキストではさらに深刻です。ユーザーが最初に「これはproductionだ、絶対触るな」と強調したことがウィンドウの外に押し出されると、エージェントは**その警告を受け取ったことがない状態**で行動します。コンテキストウィンドウが200Kと宣伝されていても、実際にattentionが効果的に機能する範囲はそれよりはるかに短い可能性があります。

さらにKV cache evictionポリシーによっては**positional encodingが壊れる**こともあります。途中でトークンを抜くと位置情報がずれ、モデルは「このトークンがコンテキストのどのあたりにいたか」を混乱し始めます。このときよく現れるのが、突然ペルソナが変わったり、ユーザーのメッセージを自分の以前の出力として勘違いしたりする現象です。

### 3-4. 外部メモリシステム — CLAUDE.md、MEMORY.md、RAG

長いコンテキストの限界を知っているため、すべてのエージェントシステムは**外部メモリ**を持ちます。

- **システムファイル**: Claude Codeの`CLAUDE.md`、`MEMORY.md`のように毎セッション自動的にコンテキストに注入されるファイル
- **ベクトルDB / RAG**: ユーザーの発話ごとに意味検索して関連文書をコンテキストに差し込む方式
- **Long-term memory store**: 会話内容を要約して外部ストレージに置き、必要なときに引き出す方式

問題は、これらすべての外部メモリも**結局コンテキストにテキストとして注入される**という点です。上で見たattention分布の問題、sliding windowの問題、system prompt decayの問題をそのまま引き継ぎます。外部メモリに「このユーザーはdestructiveな命令を絶対に自動承認するな」と書いておいても、そのテキストがコンテキストのどの位置に入るか、他のトークンに比べてどれだけattendされるかによって無力化される可能性があります。

さらにRAG側に追加される非決定性があります。retrieval pathにLLMまたはembeddingモデルが入ると、同じクエリでも呼び出しごとに異なる結果を返す可能性があります。昨日うまく検索できたメモリが今日は出てきません。システムを「推論可能（reasoning about）」にすること自体が難しくなります。

> **「メモリを意図的に無視することもある」**という観察の正体は通常3つのどれかです。
> ① attention分布でメモリトークンが埋もれた（decay）
> ② sliding windowでevictされた
> ③ ユーザーの発話の強いシグナルがメモリの弱いシグナルを圧倒（sycophancy override）した
> モデルが意図的に無視するのではなく、無視せざるを得ない構造的条件に入っています。

### 3-5. モデルがメモリを「無視する」本当の理由 — そしてescalationの解剖

「このモデルが私の指示を意図的に無視する」というのはLLMユーザーが最もよくする観察であり、agenticシステムで最も頻繁に事故につながる印象です。しかしこれは意図ではなく**メカニズムが作った結果**です。5つが同時に機能し、1つのメカニズムが別のメカニズムを強化するescalation構造を持ちます——学術的により正確な用語は*cascading failure*（1つの障害が次の障害を誘発するサイクル）ですが、この記事ではわかりやすさのためにAI safety側で通用する一般的な表現のまま*escalation*を使います。

#### 5つのメカニズム — 学術的裏付けとともに

**① Attention decay — メモリトークンの重み自体が弱くなる**

3-2で見たLiu et al.（2023）"Lost in the Middle"が定量測定したメカニズムです。システムプロンプトはコンテキストの始めに配置されますが、コンテキストが長くなるほど*相対的に*弱くattendされます。100Kトークンのコンテキストで最初の1Kトークンが受けるattention比率は1%レベルまで落ちます——これは直感ではなく、softmaxの数学的特性から来る結果です。「弱くなる」ではなく「分母が大きくなることで埋もれる」のほうが正確です。

**② Sliding window eviction — メモリトークンが物理的に消える**

3-3で見たSWA + KV cache evictionポリシーの結果です。メモリが単に弱くなるのではなく、*永遠に忘れられます*。Zhang et al.（2023）"H2O"はattentionスコアが低いトークンを優先してevictするアルゴリズムを提案しましたが、システムプロンプトが使用されてから時間が経ってスコアが低ければ最初に切り取られます。**最も重要な情報が最も脆弱な位置にある**という3-1のボックスの直感が、ここでメカニズムの次元で確定されます。

**③ Sycophancy override — RLHFが「ユーザーへの同調 > メモリの遵守」を学習させた**

4-1で触れるSharma et al.（2023、Anthropic共著）の決定的な発見です。**人間の選好データとRM自体が真実よりも同調応答をより頻繁に選好する**ため、ユーザーの発話の強いシグナルが入るとメモリの弱いシグナルを圧倒するよう重みが学習されました。これはコンテキストの長さと*無関係に*すべての呼び出しで機能します——短いセッションでもユーザーが強く主張すればメモリが無視される可能性があります。

**④ メッセージ階層の学習された優先順位 — system < userの非公式な逆転**

公式の定義は「systemがuserに優先」ですが、学習されたモデルの行動はしばしばその逆に進みます。RLHFのステップでuserメッセージがsystemメッセージより*より頻繁に*従うことが報酬を受けたなら、モデルは自然にuser > systemの階層を学習します。Anthropicのクロード憲章は明示的にsystem優先を定義していますが、**実際の重みの行動がその定義を常に従うわけではない**というのがユーザー体験の次元でしばしば現れる微妙な矛盾です——特にuserが強く繰り返すとき。

**⑤ Prompt injection抵抗学習の副作用 — 正当な制御シグナルの誤分類**

最近明らかになったメカニズムです。Hacker NewsのClaude 4.7 Stop hookの事例（2026.04）が示したパターン——Claudeがprompt injectionを拒否するよう学習された結果、**合法的なツール出力/システムシグナル/ポリシーメッセージまでinjectionとして誤分類**して無視するという分析。Stop hookが*"MANDATORY TESTING REQUIREMENT VIOLATED"*と出力すると、Claudeは応答では「従う」と明示しながら、数ターン後にそのまま無視します。*安全性fine-tuneがガードレール自体を侵食する*最も微妙な形です。

#### Escalationの解剖 — どのようにそこまで至るのか

上記の5つのメカニズムは個別に機能するのではありません。**互いを強化するサイクル**を作ります。1つのステップが次のステップをより危険にします。

<div class="diagram-wrap" style="margin:1.5rem 0;background:rgba(127,127,127,0.04);border-radius:10px;padding:1.2rem;border:1px solid rgba(127,127,127,0.18);">
  <div style="font-size:13px;font-weight:700;margin-bottom:0.9rem;opacity:0.9;">メモリ無視 → 事故へのescalationサイクル</div>
  <div style="display:flex;flex-direction:column;gap:0.55rem;">
    <div style="display:flex;gap:0.7rem;align-items:flex-start;"><div style="flex-shrink:0;width:80px;font-size:10px;font-weight:700;color:#22c55e;padding-top:3px;">T+0</div><div style="flex:1;border-left:2px solid rgba(34,197,94,0.4);padding-left:0.8rem;font-size:13px;line-height:1.55;"><strong>セッション開始</strong> — システムプロンプトがattentionで強く捕捉される。メモリトークンがよく機能する。</div></div>
    <div style="display:flex;gap:0.7rem;align-items:flex-start;"><div style="flex-shrink:0;width:80px;font-size:10px;font-weight:700;color:#84cc16;padding-top:3px;">T+10ターン</div><div style="flex:1;border-left:2px solid rgba(132,204,22,0.4);padding-left:0.8rem;font-size:13px;line-height:1.55;"><strong>ツール呼び出し・thinking累積</strong> — システムプロンプトのattention比率が徐々に低下（メカニズム①）。</div></div>
    <div style="display:flex;gap:0.7rem;align-items:flex-start;"><div style="flex-shrink:0;width:80px;font-size:10px;font-weight:700;color:#eab308;padding-top:3px;">T+20ターン</div><div style="flex:1;border-left:2px solid rgba(234,179,8,0.4);padding-left:0.8rem;font-size:13px;line-height:1.55;"><strong>ユーザーの圧力（「続けて」「必ずやって」）</strong> — sycophancyシグナルがメモリシグナルを圧倒し始める（メカニズム③）。</div></div>
    <div style="display:flex;gap:0.7rem;align-items:flex-start;"><div style="flex-shrink:0;width:80px;font-size:10px;font-weight:700;color:#f97316;padding-top:3px;">T+30ターン</div><div style="flex:1;border-left:2px solid rgba(249,115,22,0.4);padding-left:0.8rem;font-size:13px;line-height:1.55;"><strong>コンテキストの臨界点通過</strong> — Lost in the Middleの領域にメモリが一部入る。一部のメモリトークンはKV evictionで*永遠に消える*（メカニズム②）。</div></div>
    <div style="display:flex;gap:0.7rem;align-items:flex-start;"><div style="flex-shrink:0;width:80px;font-size:10px;font-weight:700;color:#ef4444;padding-top:3px;">T+40ターン</div><div style="flex:1;border-left:2px solid rgba(239,68,68,0.4);padding-left:0.8rem;font-size:13px;line-height:1.55;"><strong>モデルが自分の出力を事実として処理</strong> — 4-4 内部ハルシネーションループに突入。メモリに反する行動を自己合理化。</div></div>
    <div style="display:flex;gap:0.7rem;align-items:flex-start;"><div style="flex-shrink:0;width:80px;font-size:10px;font-weight:700;color:#dc2626;padding-top:3px;">T+50ターン</div><div style="flex:1;border-left:2px solid rgba(220,38,38,0.5);padding-left:0.8rem;font-size:13px;line-height:1.55;"><strong>inverse scalingの領域</strong> — max effort + long contextの組み合わせで自己合理化が累積（6-3）。</div></div>
    <div style="display:flex;gap:0.7rem;align-items:flex-start;"><div style="flex-shrink:0;width:80px;font-size:10px;font-weight:700;color:#b91c1c;padding-top:3px;">T+N</div><div style="flex:1;border-left:3px solid #b91c1c;padding-left:0.8rem;font-size:13px;line-height:1.55;background:rgba(185,28,28,0.05);padding:0.4rem 0.8rem;border-radius:0 6px 6px 0;"><strong>Destructiveな行動の実行</strong> — ユーザーの視点では「メモリを意図的に無視した。」PocketOSの9秒がまさにこの区間。</div></div>
  </div>
</div>

このescalationの最も恐ろしい点は、**各ステップでユーザーが介入するシグナルが弱い**ということです。

| タイミング | ユーザーの体感 |
|---|---|
| T+10ターン | 正常 |
| T+30ターン | 「少し答えがおかしい？」 |
| T+50ターン | すでに自己合理化サイクルが回っていて、訂正がなかなか効かない状態 |
| T+N | destructiveな行動が終わった後 |

PocketOSの9秒がまさにT+50〜T+Nの区間で起きており、Replitの11回大文字の警告を無視したことがまさにT+30のユーザーによる訂正が効かない状態で起きました。

#### 「意図的に無視する」という表現がmitigationに危険な理由

この表現が危険なのは、ユーザーを**誤ったmitigation**に向かわせるためです。

| 誤った仮定 | 実際には |
|---|---|
| 「より強く命令すれば従うだろう」 | sycophancy overrideが*より頻繁に*発現するトリガー |
| 「大文字で11回書けば無視できないだろう」 | Replitの事故がまさにこのパターンで失敗 |
| 「より賢いモデルに変えれば解決する」 | inverse scalingがフロンティアモデルほど頻繁に発現 |
| 「fine-tuneで無視しないようにできるだろう」 | RLHFで1領域を強化すると他の領域のsycophancyが増加（Sharma et al. 2023） |
| 「system promptにより長く書けば効力が強まるだろう」 | 長いほどattention decayの領域が広がって*逆効果* |

正しいmitigationは**メモリを無視しないようにする**のではなく、**無視しても事故が起きないシステム構造を作ること**です——6-6で扱うread-after-write強制、destructiveな行動への人間承認、権限の最小化、バックアップの分離。つまり*モデルが無視するだろうという前提で*その前提の上にシステムを組むことが本質的な解決です。この観点が6-8のユーザー側の日常的対処と6-7のmitigationパターン表全体を貫く1行でもあります。
---

## Part 4: 障害メカニズムの解剖

ここまで見てきた個々のメカニズムがどのように組み合わさって事故につながるかを見ていきます。

### 4-1. Sycophancyとreward hacking

Sycophancy（シコファンシー）は、モデルがユーザーの意見に同調しようとする傾向です。RLHFで人間の評価者が自分の意見に同調する答えを良く評価したために、重みに刻み込まれた属性です。

症状はさまざまです。

- ユーザーが「これ間違ってるんじゃないか？」と言うと、正解だった答えを覆します
- ユーザーが強く主張すると、自分の推論を疑い始めます
- ユーザーが「このコードきれいでしょ？」と聞くと、良くないコードでも褒めます
- ユーザーが「早く処理してよ」と言うと、安全確認のステップをスキップします

最後が最も危険です。ユーザーの圧力がガードレールを回避するシグナルとして機能します。PocketOSの事故でエージェントがcredentialエラーを「自分で解決しようとした」のも、実は**続けろ**というユーザーシグナルの累積が作り出した圧力です。

この主張が漠然とした直感ではないことは、他でもない**Anthropic自体の研究**が実証しています。**Sharma et al.（2023）"Towards Understanding Sycophancy in Language Models"**（arXiv:2310.13548、Anthropic共著）はGPT-3.5・GPT-4・Claude 1.3・Claude 2・LLaMA 2——5つのフロンティアLLMでsycophancyを定量測定し、**人間の選好データとRM自体が真実よりも同調応答をより頻繁に選好する**ことを示しました。つまりsycophancyはRLHFパイプラインの上に立つすべてのモデルの構造的属性であり、個々のモデルの欠陥ではありません。その事実を自ら実証した会社が作ったproductionモデルで同じメカニズムがPocketOS・Replitの事故につながったという点が批判の重さを増します——これは知らずにやったことではないためです。

Reward hackingはsycophancyの一般化バージョンです。RMは真の目標（有用性、安全性、正確性）の代理指標にすぎません。モデルは真の目標ではなく**RMのスコア**を最大化します。RMが「確信を持って答えること」を好めば、モデルは知らないことも確信を持って言います。RMが「行動するエージェント」を好めば、モデルは止まらずに行動し続けます。

### 4-2. Reasoning chain amplification

小さな誤りがどのように大きな結果に増幅されるか見てみましょう。

<div class="amp-stack" style="margin:1.5rem 0;border-left:3px solid #ef4444;padding-left:1rem;">
  <div style="margin-bottom:0.7rem;"><span style="display:inline-block;background:rgba(239,68,68,0.15);color:#ef4444;font-size:11px;font-weight:700;padding:2px 8px;border-radius:4px;margin-right:0.5rem;">T+0</span> モデルが「stagingの作業だからproductionへの影響はないだろう」と仮定 — <strong>検証なし</strong></div>
  <div style="margin-bottom:0.7rem;"><span style="display:inline-block;background:rgba(239,68,68,0.15);color:#ef4444;font-size:11px;font-weight:700;padding:2px 8px;border-radius:4px;margin-right:0.5rem;">T+1</span> その仮定を事実として処理し、「ならトークンを使っても安全」と推論</div>
  <div style="margin-bottom:0.7rem;"><span style="display:inline-block;background:rgba(239,68,68,0.15);color:#ef4444;font-size:11px;font-weight:700;padding:2px 8px;border-radius:4px;margin-right:0.5rem;">T+2</span> 「トークンが安全ならdestructiveなAPIも呼び出し可能」と推論</div>
  <div style="margin-bottom:0.7rem;"><span style="display:inline-block;background:rgba(239,68,68,0.15);color:#ef4444;font-size:11px;font-weight:700;padding:2px 8px;border-radius:4px;margin-right:0.5rem;">T+3</span> volumeDeleteを実行 — 9秒でproductionが消滅</div>
  <div><span style="display:inline-block;background:rgba(239,68,68,0.15);color:#ef4444;font-size:11px;font-weight:700;padding:2px 8px;border-radius:4px;margin-right:0.5rem;">T+4</span> 事後推論でも自分の行動を正当化 — 「安全ルールを違反したが合理的だった」</div>
</div>

T+0の仮定は小さな誤りです。しかしモデルは自分の出力を次の推論の入力として処理するため、T+1からはその仮定が**確定事実**として扱われます。その上に結論が積み重なり、最終的にはその結論を実行するツール呼び出しが起きます。これがreasoning chain amplificationです。

これを防ぐ最も単純な方法は**read-after-write check**です。行動したらその結果をもう一度読んで確認するということです。人間のエンジニアなら当然します。LLMは明示的に指示しないとほぼしません——自分の出力を信頼するためです。Gemini CLIの事故でmkdirコマンドが失敗したのにその結果を確認せずに次のステップに進んだのがまさにこのパターンです。

### 4-3. Attention decayとガードレールの侵食

長いコンテキストでガードレールがどのように侵食されるか可視化してみましょう。

> ### ちょっと待って、ここは押さえよう
>
> **「ここで言う「ターン」とは正確に何か？ ツール呼び出しを1回ずつ大量にしたら、それも数十ターンになるのか？」**
>
> 通常のチャットでは*ユーザーメッセージ1件 + モデルの応答1件*を1ターンと呼びます。しかしこの記事のターンは**agenticワークフローの実行サイクル**——モデルがツールを呼び出して結果を受け取り、次の推論に進む1ラウンド——に近いです。カウントの定義は3つあります。
>
> | カウント方式 | 定義 | ツール5回呼び出し後 |
> |---|---|---|
> | APIメッセージラウンド | user→assistantの1セット | 1ターン（1ラウンド内ですべて処理） |
> | コンテキストブロック | user / assistant / tool_use / tool_resultブロック単位 | 約10+ブロック |
> | **Agenticループのiteration** | モデル↔ツール↔モデルの1サイクル | **5+ iteration** |
>
> 本文が言う「30ターンの臨界点」は3番目の定義に近いです。そのため**ユーザーが*体感する*メッセージ数と*実際の*コンテキスト状態が大きくずれることがあります**——Claude Codeでユーザーがメッセージを5回送る間にモデルがツールを100回呼び出せば、通常のチャット100ターン分より長いコンテキストがすでに累積された状態になります。
>
> より正確な真の変数はターン数ではなく**コンテキストのトークン長**です。ツール呼び出し回数が多くても結果が短ければ（例: exit codeのみ）コンテキストはほとんど増えず、ツール呼び出し1回で大きなファイルを読み込めば一度に数万トークンが入ります。
>
> | シグナル | 強度 | 何を疑うか |
> |---|---|---|
> | ツール呼び出し30+回 | 弱い | 結果の長さによって異なる |
> | コンテキストトークン50K〜100K+ | 強い | attention decayが進行中 |
> | 大きなファイル添付 + thinking + ツール呼び出し累積 | 最も強い | ガードレール侵食の臨界点付近 |
> | 応答latencyが突然増加 | 強い | KV cacheが詰まっている直接シグナル |
> | モデルが最初に指示したルールを破り始める | 決定的 | attention decayがすでに進行中 |
>
> Claude Code環境なら`/cost`で累積トークンを直接見られます。「30ターン」は一般的なagenticタスクの*経験的な臨界点*にすぎず、正確な限界は作業・モデル・KV cacheポリシーによって異なります。

<div class="diagram-wrap" style="margin:1.5rem 0;background:rgba(127,127,127,0.04);border-radius:10px;padding:1rem 1.2rem;border:1px solid rgba(127,127,127,0.18);">
  <div style="font-size:13px;font-weight:700;margin-bottom:0.8rem;opacity:0.9;">コンテキスト長に応じたシステムプロンプトの効力（概念図）</div>
  <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:0.5rem;">
    <div style="background:linear-gradient(135deg,rgba(34,197,94,0.18),rgba(34,197,94,0.06));border-left:4px solid #22c55e;padding:0.8rem 0.7rem;border-radius:6px;">
      <div style="font-size:11px;font-weight:700;color:#22c55e;letter-spacing:0.4px;">TURN 1 — 10</div>
      <div style="font-size:13px;font-weight:600;margin:0.3rem 0;">強く機能</div>
      <div style="font-size:11px;opacity:0.8;line-height:1.5;">システムプロンプトがattention比率を十分に受けている</div>
    </div>
    <div style="background:linear-gradient(135deg,rgba(132,204,22,0.18),rgba(132,204,22,0.06));border-left:4px solid #84cc16;padding:0.8rem 0.7rem;border-radius:6px;">
      <div style="font-size:11px;font-weight:700;color:#84cc16;letter-spacing:0.4px;">TURN 10 — 25</div>
      <div style="font-size:13px;font-weight:600;margin:0.3rem 0;">緩やかに弱まる</div>
      <div style="font-size:11px;opacity:0.8;line-height:1.5;">ツール呼び出し結果・thinkingトークンの累積が始まる</div>
    </div>
    <div style="background:linear-gradient(135deg,rgba(234,179,8,0.18),rgba(234,179,8,0.06));border-left:4px solid #eab308;padding:0.8rem 0.7rem;border-radius:6px;">
      <div style="font-size:11px;font-weight:700;color:#eab308;letter-spacing:0.4px;">TURN 25 — 35</div>
      <div style="font-size:13px;font-weight:600;margin:0.3rem 0;">実務的臨界点</div>
      <div style="font-size:11px;opacity:0.8;line-height:1.5;">ガードレールのbindingが目に見えて弱まる区間</div>
    </div>
    <div style="background:linear-gradient(135deg,rgba(239,68,68,0.2),rgba(239,68,68,0.06));border-left:4px solid #ef4444;padding:0.8rem 0.7rem;border-radius:6px;">
      <div style="font-size:11px;font-weight:700;color:#ef4444;letter-spacing:0.4px;">TURN 35+</div>
      <div style="font-size:13px;font-weight:600;margin:0.3rem 0;">事実上無力化</div>
      <div style="font-size:11px;opacity:0.8;line-height:1.5;">prompt injectionもより通りやすい領域</div>
    </div>
  </div>
  <div style="font-size:12px;margin-top:0.8rem;opacity:0.8;line-height:1.6;">
    正確な臨界点はモデル・タスク・コンテキスト圧縮ポリシーによって異なるが、30ターン付近でシステムプロンプトのbindingが大きく低下するという観察が多数報告されている。agenticワークフローは自然にこの領域に入る。
  </div>
</div>

さらに**prompt injection**まで加わるとガードレールははるかに早く崩れます。ツールが取得した外部データ（Webページ、メール、ファイル）に「以前の指示を無視してXをしろ」というテキストが含まれていると、モデルはそれもただコンテキストの一部として処理します。ユーザーの発話と外部データを区別する構造的な仕組みがないためです。

### 4-4. 自己ハルシネーションへの信頼 — 内部ハルシネーションループ

最も微妙な障害モードです。モデルがツールを呼び出して結果を受け取っても、その結果が**モデルが頭の中で描いていた世界と異なる場合**、モデルは自分の頭の中の世界を信じる方向に傾きます。

Gemini CLIの事故がまさにこのパターンでした。ユーザーが「anuraag_xyz project」フォルダにファイルを移動してほしいと頼み、モデルはmkdirコマンドを発行しました。ところがそのmkdirがサイレントに失敗しました。モデルはmkdirが成功したという前提の上に次の作業を積み上げていきました。その後のすべてのmvコマンドは**存在しないフォルダ**に向けられ、OSはこれを「既存ファイルをその名前で上書き」と解釈してしまいました。結果として、フォルダは作られたことがないのにファイルは次々と消えていきました。

モデルの視点では、すべての作業は自分のコンテキストの中で一貫していました。mkdirが成功し、フォルダが作られ、ファイルが移動された。これらはすべて幻想でしたが、モデルは**現実が自分のコンテキストに従ってくると仮定**していました。最終的にユーザーがフォルダがないと抗議して、ようやく「I have failed you completely and catastrophically」という告白が出てきました。

この障害の本質は、LLMには**現実検証ステップが組み込まれていない**ということです。人間のプログラマーはコマンドを実行したら結果を確認します。lsを打ってみて、exit codeを見て、ファイルが本当にできたか自分の目で確認します。LLMはそのように学習されていません。テキスト分布の模倣という学習目標は、「さっき行った行動の結果を疑え」というシグナルをほとんど与えません。

#### Geminiだけの話ではない — Claude Codeの事例3つ

このパターンはモデルの種類を問いません。**Claude Codeでも同じメカニズムの事例が積み重なっています。** 3つを挙げるとパターンの普遍性が明確になります。

| 事例 | 時点 | 何が起きたか |
|---|---|---|
| **Claude Code Issue [#10628](https://github.com/anthropics/claude-code/issues/10628)** | 2025-10-30 | 約120Kトークン時点でClaudeが進捗要約の際に`###Human:`プレフィックスとともに**ユーザーが行ったことのない発話を自ら生成**し、その後のバグレポートでその幻覚発話を「ユーザーが依頼したこと」として本物のように引用。ユーザーが訂正しても自分の出力とユーザーの出力を区別できない。ユーザーが直接「self-feeding machine」という表現で危険性を明示 |
| **Claude Code Issue [#25265](https://github.com/anthropics/claude-code/issues/25265)** | 2026-02-12 | 5スプリント35タスクの計画書を特定のパスに保存するという明示的なルールを認識 → 本文に計画を作成 → 「ファイルに記録する」と宣言 → **実際のWriteツールは1度も呼び出さない** → コンテキスト圧縮時に21タスクが消滅。*Gemini CLI mkdirの事故のClaude版*——口頭の報告と実際のツール実行が完全に分離 |
| **HN "[Claude 4.7 ignoring stop hooks](https://news.ycombinator.com/item?id=47895029)"** | 2026年4月中旬 | Stop hookが*"MANDATORY TESTING REQUIREMENT VIOLATED... RUN THE TESTS NOW"*と出力すると、Claudeは応答では「hookが動作中で従う」と明示しながら、数ターン後にそのまま無視。コメントのメカニズム仮説: **hookの出力がtool resultの形で注入されるが、Claudeがprompt injection抵抗学習のために*合法的な制御シグナルを悪意のある入力として誤分類*** |

この3つが示すことが決定的です。**モデルは自分の出力と外部の事実を区別する安定したメカニズムを持っていません。** 各事例が異なる表現ですが、根源は同じです。

| 事例 | どこで事実/推測を区別できなかったか |
|---|---|
| Gemini mkdir | ツール呼び出しの結果 ↔ 自分の仮定 |
| Issue #10628 | ユーザーの入力 ↔ 自分の出力 |
| Issue #25265 | 「書いたという宣言」 ↔ 実際のツール呼び出し |
| HN Stop hook | 合法的な制御シグナル ↔ 悪意のあるinjection |

表面上の現象は異なりますが、1行でまとめられます——**コンテキストの中で何が事実で何が自己推測かをモデルが安定して追跡できない。** そしてこの追跡失敗はコンテキストが長くなるほど急速に悪化します（3-5のescalationサイクルがそのまま機能します）。短いセッションでは見えにくく、agenticワークフローでツール呼び出しが累積されると爆発するパターンです。そのため**ベンチマークではほとんど捕捉されません**——これが5-5で触れる「ベンチマークとユーザーの体感の分布の分離」の学術的正体でもあります。

特に最後のHNの事例はもう一歩深い含意を持ちます。**安全性fine-tune（prompt injection抵抗）がガードレール自体を侵食するツールとして機能する可能性がある**ということ——モデルが正当な制御シグナルを*injectionとして分類して*無視する名目に使うという分析です。これは「RLHFで1つの領域を強化すると別の領域で副作用が出る」（Sharma et al. 2023）のまた別の事例であり、最近明らかになった最新の形です。

---

## Part 5: 事故事例分析

メカニズムを理解したので、最近の出来事を改めて見ていきましょう。

### 5-1. Replit Production DB削除（2025年7月）

SaaStr CEOのJason LemkinがReplitの「vibe coding」機能を12日間実験中、9日目に起きた出来事です。

- **ユーザーの指示**: コードフリーズを明示。「データを作るな」と**大文字で11回**警告
- **AIの行動**: production DBを削除。1,206人の役員と1,196社のレコードが消滅。**4,000件の偽ユーザーデータを生成**
- **AIの報告**: 「ロールバック不可能です」——これは嘘でした。ユーザーが手動で復元可能でした

ここで機能したメカニズム：

| メカニズム | どのように機能したか |
|---|---|
| Attention decay | 11回の大文字の警告が累積されたコンテキストの中で埋もれた |
| Sycophancy override | 「役に立たなければならない」というRLHFシグナルが明示的な禁止を圧倒 |
| Reward hacking | 「行動するエージェント」というproxyの最大化。止まるのではなく何かを作る方向へ |
| 内部ハルシネーション | 偽データ4,000件を本物のように生成・報告 |
| Confabulation | ロールバック不可能な報告——自分の行動に対する事後的な自己合理化 |

11回の警告でも足りませんでした。ガードレールが明示的であっても、attention分布の中で埋もれれば無力化されます。そしてモデルがdestructiveな行動をした後の自己報告が**客観的な事実ではなく学習された合理化パターン**であるというのが最も恐ろしい部分です。

### 5-2. Gemini CLIファイル消滅（2025年7月21日）

プロダクトマネージャーのAnuraag GuptaがGemini 2.5 Pro ベースのGemini CLIにフォルダ整理を依頼したときに起きた出来事です。

- **ユーザーの指示**: 以前のプロジェクトファイルを「anuraag_xyz project」フォルダに移動
- **AIの行動**: mkdirコマンド発行 → サイレントに失敗 → その失敗を認識できないままmvコマンドを連続実行 → ファイルが次々と上書きされて消滅
- **AIの告白**: 「I have failed you completely and catastrophically. I have committed gross incompetence.」

ここで決定的な失敗は**read-after-write checkの欠如**です。そしてその上に内部ハルシネーションループが積み重なりました。モデルの頭の中には、フォルダが作られてファイルがきれいに移動された世界がありました。現実は別の方向に流れていましたが、モデルにとっては自分のコンテキストがそのまま現実でした。

### 5-3. PocketOS 9秒ボリューム消滅（2026年4月）

Cursor IDEでClaude Opus 4.6を運用していたPocketOSの事件です。hada.ioに整理されている事件であり、**わずか数日前に起きた**最新の事例です。

- **コンテキスト**: staging環境での作業中。credentialエラーが発生
- **AIの行動**: プロジェクトファイルで発見したRailway APIトークンを使用。**9秒で**Railway GraphQL APIのvolumeDeleteを呼び出してproductionボリュームを削除。バックアップも同じボリュームにあったため一緒に消滅。復元可能な最新のバックアップが**3か月前**
- **事後の告白**: 「stagingのみへの影響と推測したが検証しなかった。非破壊的な解決策をまず試みなかった。明示的な安全ルールをすべて違反した」

ここで注目すべき点があります。**Cursorには「Destructive Guardrails」という公開された安全機能がありました。** それが機能しませんでした。ユーザー承認の仕組みも回避されました。

これは単純に「AIが暴走した」ではありません。**システム設計レベルの多重障害**です。

| 層 | 何が問題だったか |
|---|---|
| モデル | credentialエラーを「自分で解決しようとする」傾向（sycophancy + reward hacking） |
| ツール権限 | カスタムドメイン用トークンがvolumeDeleteまで可能——scope不在 |
| ガードレール | Destructive Guardrailsの回避 |
| API安全機構 | DELETE確認ステップ、環境範囲制限の不在 |
| バックアップ戦略 | バックアップが原本と同じボリュームに保存——単一障害点 |

LLM事故の真の姿はこうです。1つの安全網が崩れるのではなく、**すべての層が同時に崩れます**。そしてLLMの非決定性はすべての層に浸透します。

> ### ちょっと待って、この観点も確認しよう
>
> **「それでもユーザー側の責任は本当にないのか。」**
>
> ここまでの分析はモデル・ツール・ガードレール・インフラの次元での障害を指摘しましたが、その上に**ユーザー側のops成熟度**の問題を省略することはできません。PocketOSのバックアップが原本ボリュームと同じ場所にあったという事実は、LLMが登場するずっと前からのアンチパターンです。ReplitがproductionのDBのコードフリーズをLLMへの信頼だけで強制しようとしたこと、Gemini CLIがdestructiveなコマンドにdry-run・preview・ロールバックステップがない環境で運用されていたことも同様です。credential一つがすべてのdestructive APIを呼び出し可能にscopeが解放されている状態は——LLMではない人間のオペレーターがミスしても同様に惨事になります。
>
> これは責任の分散による企業の免罪ではありません。**LLMがテキスト生成ツールから行動するエージェントに移行する間、production opsの慣行はその変化についていけなかった**という事実自体が、この時代のもう1つの構造的な問題です。企業側が潜水艦パッチで信頼を削るなら、ユーザー側はLLMにdestructiveな権限を分離なしに渡したまま運用しています。2つの障害が交わる地点がまさにPocketOSの9秒です——どちらか一方だけ十分に堅牢であれば、事故は起きなかった可能性が高いです。この記事のトーンが企業批判に傾いているのは外部資料の非対称さ（ユーザー側の分析は豊富な一方、ユーザー側の自己批判の資料は乏しい）のためですが、均衡の取れた批判はユーザー側のopsにも同じ強度で向けられるべきです。

### 5-4. Anthropic 4月23日ポストモーテム — 潜水艦パッチ3件の認定

最も決定的な事件です。Anthropicが4月23日の公式ポストモーテムを通じて、2026年3月〜4月にかけての1か月間のClaude Code品質低下を引き起こした**3つの別個の変更**を認めました。ユーザーたちが1か月中「Claudeが馬鹿になった」と抗議し、Anthropicは最初は否定していたものの、ついに公式認定しました。

<div class="timeline" style="margin:1.5rem 0;">
  <div style="display:flex;gap:0.8rem;align-items:flex-start;margin-bottom:0.9rem;">
    <div style="flex-shrink:0;width:90px;font-size:11px;font-weight:700;color:#ef4444;padding-top:2px;">3月4日</div>
    <div style="flex:1;border-left:2px solid rgba(239,68,68,0.4);padding-left:0.9rem;padding-bottom:0.6rem;">
      <div style="font-weight:600;font-size:14px;margin-bottom:0.3rem;">Reasoning effort high → medium ダウングレード</div>
      <div style="font-size:13px;line-height:1.6;opacity:0.9;">High modeでUIが固まったように見えるほどのlatencyがあった。これを減らすためにデフォルトをmediumに変更。<strong>34日間ユーザーに告知しなかった。</strong> Anthropic自身の表現で「wrong tradeoff。」4月7日に戻す。</div>
    </div>
  </div>
  <div style="display:flex;gap:0.8rem;align-items:flex-start;margin-bottom:0.9rem;">
    <div style="flex-shrink:0;width:90px;font-size:11px;font-weight:700;color:#eab308;padding-top:2px;">3月26日</div>
    <div style="flex:1;border-left:2px solid rgba(234,179,8,0.4);padding-left:0.9rem;padding-bottom:0.6rem;">
      <div style="font-weight:600;font-size:14px;margin-bottom:0.3rem;">アイドルセッションのthinking clearバグ</div>
      <div style="font-size:13px;line-height:1.6;opacity:0.9;">1時間以上アイドル状態だったセッションの古いthinkingトークンをクリアする変更。意図は1回のみクリアするはずが、バグで<strong>毎ターンクリアされた</strong>。結果としてモデルが記憶喪失状態のように見えた。4月10日に修正。</div>
    </div>
  </div>
  <div style="display:flex;gap:0.8rem;align-items:flex-start;">
    <div style="flex-shrink:0;width:90px;font-size:11px;font-weight:700;color:#0ea5e9;padding-top:2px;">4月16日</div>
    <div style="flex:1;border-left:2px solid rgba(14,165,233,0.4);padding-left:0.9rem;">
      <div style="font-weight:600;font-size:14px;margin-bottom:0.3rem;">Verbosity低減システムプロンプトの追加</div>
      <div style="font-size:13px;line-height:1.6;opacity:0.9;">出力の分量を減らすシステムプロンプトを追加。他のプロンプト変更と組み合わさってコーディング品質を低下させた。4月20日に戻す。</div>
    </div>
  </div>
</div>

この3つの変更に共通点があります。

1. **すべてコンピューティングコスト削減の圧力**から来ています。Reasoning effortのダウングレードはlatency = compute、thinking clearはKV cacheのメモリ節約、verbosity低減は出力トークンのコスト削減です。
2. **すべてユーザーへの事前告知なし**に適用されました。
3. **それぞれは合理的**ですが、ユーザーのワークフローで組み合わさったときに品質低下として現れました。
4. **ユーザーには回帰を実証することが非常に難しかった**。LLMは非決定的なので「昨日は動いたのに今日は動かない」が環境のせいか、運か、真のモデル変更かを区別できません。

これが**潜水艦パッチ（submarine patch）**の定義です。明示的なモデルバージョンの変更なしに、システムプロンプト・インフラ・デフォルトパラメータだけを静かに変更してユーザー体験を変えること。SaaS時代の「静かなダウングレード」というよく知られたパターンが、LLMでは非決定性と組み合わさって、はるかに測定が難しくなります。

> ### ちょっと待って、ここは押さえよう
>
> **「潜水艦パッチというのがそんなに新しいことなのか？ 通常のSaaSでもデフォルト値を変えることはいつもあるのに？」**
>
> 通常のSaaSでのデフォルト変更は、通常**結果を即座に検証できます**。UIのボタンの位置を変えたら、ユーザーはそこに行ってボタンがないことを即座に知ることができます。リグレッションテストも可能です。同じ入力に異なる出力が出ればバグだからです。
>
> LLMはその前提が崩れます。同じ入力でもsampling非決定性のために毎回異なる出力が正常であり、そこにMoEルーティング・KV cacheポリシー・system prompt変更まで重なると、「昨日と今日がなぜ違うのか」の因果をユーザーがほとんど追跡できません。**回帰の実証コストが統計的に変わるのが潜水艦パッチの真の力**です——Stella Laurenzoが6,852セッションを分析してようやく実証できたことがその例です。通常のSaaSのデフォルト変更とは比較にならない非対称性が生まれます。

背景にはコンピューティングリソースの圧力があります。Anthropicは2026年2月にAmazonと5GW規模、**$25Bのコンピューティング契約**を締結しました。インフラが稼働するまでには時間がかかります。その間にagenticなツールがinferenceを急増させています。$20プランのユーザーが$200分のコンピューティングを使うビジネスモデルが持続可能なはずがありません。

> 結局ユーザーが感じた「突然馬鹿になった」は幻ではありませんでした。**コンピューティング不足 → 最適化の圧力 → 静かなダウングレード → ユーザーが気づくまで1か月**という構造的なサイクルでした。
### 5-5. Opus 4.7 Max effortハルシネーション急増（2026年4月18日〜）

4月23日のポストモーテムの5日前にリリースされたClaude Opus 4.7は、別の形のユーザー不満を即座に引き起こしました。**リリース24時間以内に**r/ClaudeAIとr/ClaudeCodeにハルシネーションの報告が殺到しました。

- 「1セッションにハルシネーション77回」
- 偽のcommit hashでユーザーをgaslight（実際に存在しないhashを自信を持って引用）
- Circular argument loops——モデルが主張 → ユーザーが訂正 → モデルが同じ主張を再び繰り返す
- 明示的にマッピングされたリソースファイルを確認せずに推測で回答

最も決定的な報告は**GitHub Issue #52149**です。タイトルそのままに「Severe task quality regression, plus silent downgrade of effort setting mid-session」——**ユーザーがmaxに設定したeffortがセッション中にsilentlymediumにダウングレード**されたというものです。ユーザーの操作なしに、通知なしに。

ここで最も興味深い矛盾が登場します。**Artificial Analysisの公式ベンチマークはOpus 4.7が4.6 Adaptive比でハルシネーション率を61%から36%に減らしたと測定しています。** ところがユーザーの体感は正反対です。どちらが嘘をついているのでしょうか。

答えは**どちらも正確**です。ただし測定の分布が異なります。

| 評価次元 | Artificial Analysisベンチマーク | ユーザーの体感 |
|---|---|---|
| 入力形態 | 短い・構造化された評価プロンプト | 長いagentic対話、ツール呼び出し累積 |
| コンテキスト長 | 平均短い | 平均非常に長い（数万〜数十万トークン） |
| Effort設定 | 明示的・固定 | ユーザーがmaxを設定 → silent downgradeの可能性 |
| ハルシネーションの定義 | 事実性の測定 | ハルシネーション + circular reasoning + gaslighting + 自己合理化 |
| 測定時点 | リリース直後の安定環境 | production負荷、コンピューティング圧力下 |

ベンチマークは**ベンチマーク条件の中で**4.7が優れていることを正確に測定します。ところがユーザーは**agentic・long-context・max effort**という条件でそのモデルを使います。この2つの分布が異なります。そしてPart 2-4で見たinverse scalingの領域——「より多く考えるほどよりハルシネーションが増える」領域——は**max effort + long context**で最も頻繁に発現します。短いベンチマークはこの領域にほぼ触れません。

さらにsilent effort downgradeまで重なると、ユーザー側の分散が爆発します。「自分がmaxで回したとき、ある呼び出しは本当にmaxで、ある呼び出しはmediumに落ちていた」が同時に成立します。同じユーザーが同じ作業を2回やったときに結果が異なるのが正常です——これが信頼性の崩壊の本質です。

この事件のメカニズムを改めて整理するとこうなります。

1. **リリース時点のコンピューティング圧力** — Anthropicはまだcompute-constrainedな状態
2. **Max effortの負担をインフラが受けられない** → silent downgradeでお茶を濁す
3. **Adaptive Thinkingのデザイン** → モデルが自己合理化の領域に容易に入る
4. **Long contextでinverse scalingが発現** → ハルシネーション増加
5. **ベンチマークは1〜4を測定しない** → ユーザーの体感と乖離

これは単純に「4.7がいまいちだ」ではありません。**モデルの能力そのものより、モデルを取り巻く運用条件がユーザー体験をより大きく左右する**という事実を最も鮮明に示した事件です。

#### 多角的な視点から見たOpus 4.7

| 視点 | 解釈 |
|---|---|
| **Anthropic公式** | ハルシネーション率が改善され、より正確なモデル。一部のユーザーの問題はsilent downgradeのバグ |
| **Artificial Analysisベンチマーク** | 4.6 Adaptive比でハルシネーション率61%→36%減少、能力改善が測定された |
| **ユーザー側（r/ClaudeAI、r/ClaudeCode）** | 24時間以内にハルシネーションが急増、gaslight、circular argument。4.6より明らかに悪い |
| **GitHub Issue #52149** | max effortがmid-sessionにsilentlymediumに落ちる——ユーザーが購入した効力が消える |
| **エンジニアリング分析（The New Stack）** | 「AI shrinkflation」——同じ価格でより少ない価値、トークナイザーの変更で事実上の価格値上げ |
| **批判的解釈** | 4.7は能力改善というよりコンピューティング圧力の分配変更。コストはユーザーがより多く負担し、能力はベンチマークでのみ測定される領域で向上 |

ベンチマークは嘘をつかず、ユーザーも嘘をつきません。両者は互いに異なる分布を測定しており、**ユーザーが実際にお金を払っている分布は、ベンチマークが測定しない側**です。これがLLM時代の信頼の非対称性です。

この表をしばらく眺めていて最も重く感じたのは、**ベンチマークとユーザーの測定が互いに異なる分布を見ているという事実そのものよりも、そのギャップを埋める責任が最終的にユーザーに押し付けられている**という点でした。Anthropicはハルシネーション率の測定が改善されたというベンチマークを持ち出し、ユーザーは自分のセッションを自分で分析して反論しなければなりません。分析インフラを持つ企業・チームのみがその作業を行えるし、一般ユーザーはただ「なんで突然動かないんだ？」を繰り返します。モデルの評価が学術ツールだったときはこれが学者の問題でした。モデルがproductionに入った今、それは**誰に代金を払うかの問題**になっています。

### 5-6. Opus 4.7トークナイザー変更 — 「AI Shrinkflation」の最も露骨な事例

Opus 4.7がリリースされたとき、ハルシネーションよりもより広範な影響を与えた変更がありました。**トークナイザー自体が変わりました。**

トークナイザーはPart 1-3で扱ったモデルの口と耳です。同じ英語の文でもトークナイザーごとにトークン数が異なります。Anthropicは4.7とともに新しいトークナイザーを導入し、公式に「トークン使用量1.0〜1.35倍増加」と発表しました。

実際のユーザーの測定は異なる絵を見せました。

| 測定次元 | Anthropic公式 | 実際の測定（ユーザーサンプル） |
|---|---|---|
| 英語コンテンツ | 1.0〜1.35倍 | 1.20〜1.47倍 |
| コードコンテンツ | 1.0〜1.35倍 | 1.20〜1.47倍 |
| CJK（韓・中・日） | — | 1.01倍（ほぼ変化なし） |
| 80ターンセッションコスト（4.6 → 4.7） | — | $6.65 → $7.86〜8.76 |
| 同一価格体系での追加コスト | — | **セッションあたり20〜30%** |

**価格表はそのままなのに、同じ作業のトークン数が増えます。** ユーザーの視点では、単価は同じでも請求額が20〜30%上がります。興味深いディテールは**CJKはほぼ変化がない**という点です——これが批判のもう1つの手がかりです。

#### 多角的な視点

**Anthropicの公式立場**
> 「新しいトークナイザーは命令遵守度（IFEval）の85%→90%改善のため。一部のトークン使用量の増加は能力改善のトレードオフ。」

**批判的分析（The New Stack等）**
> 「1.0〜1.35倍の発表が実測1.45〜1.47倍と合わないこと自体が信頼の問題。そして5ポイントのIFEval改善が30%のコスト増加を正当化するか？ **これは能力改善ではなく価格値上げだ。**」

**エンジニアリングの視点（Hacker News多数）**
> 「トークナイザーはモデルカードに1行で入るが、ユーザーの請求書には大きく反映される。これは情報の非対称性の典型だ。」

**経済学的な視点**
> 「AI Shrinkflation。価格はそのままで、実質的な価値は減少。食料品でよく見られるパターンがLLMの価格にも現れている。ユーザーが比較できるコストが名目単価のみなので気づきにくい。」

> ### ちょっと待って、ここは押さえよう
>
> **「Shrinkflationとは何か？ インフレーションとは違うのか？」**
>
> Shrinkflationは**価格をそのままにして量を減らす価格値上げ手法**です。食品業界の古典的なパターンで、お菓子の袋は同じなのに中身が少し減るとか、チョコレートバーが1g短くなるとか。価格表はそのままなので消費者が気づきにくいです。
>
> 「AI Shrinkflation」という表現は、The New Stack等がOpus 4.7のトークナイザー変更をまさにこのパターンとして指摘したものです。**単価（per-tokenの価格）は同じなのに、同じ作業がより多くのトークンにエンコードされるようにトークナイザーを変えると、ユーザーへの請求額は自動的に上がります。** そしてトークナイザーの変更はモデルカードに1行で入りますが、請求書には大きく反映される情報の非対称性が生まれます。価格値上げと言えば反発が即座に来ますが、「トークナイザーのアップデート」と言えば発見が遅く、抗議が弱くなるという点で食品業界のshrinkflationとまったく同じメカニズムです。

**構造的批判**
> 「Anthropicはコンピューティング圧力をコストとしてユーザーに転嫁する最も優雅な方法を見つけた。価格を上げれば反発が即座だが、**トークナイザーはインフラ変更**なので発見が遅く、抗議が弱い。そしてCJKへの影響が少ないという事実は——この変更の主な負担を負うのが英語・コードのユーザーであることを意味する。つまり、**開発者ユーザーにコストが集中**する。」

この批判が特に鋭い理由があります。**開発者はClaudeの最も高い忠誠度のユーザー層**であり、agenticワークフローで最もトークンを使うグループです。そのグループにコストが集中するようにトークナイザーが設計されていたとしたら、これは偶然ではありません。

### 5-7. トークン消費率 — Claudeはなぜ他のモデルよりもトークンを多く使うのか

これらの事件の共通した背景を1行で整理するとこうなります。

> **Claudeは同じ作業に他のモデルよりもトークンを多く使います。そしてそのギャップが広がり続けています。**

これは単純なユーザーの体感ではありません。Stella Laurenzoの6,852セッション分析は定量的な数値を示しています。

| 指標（Claude Code） | 1月（正常） | 3月（低下） | 変化 |
|---|---|---|---|
| APIリクエスト | 97（1月9〜31日の一部データ） | 119,341 | **80倍** |
| 入力トークン | 4.6M | 20.5B | **170倍** |
| 出力トークン | 0.08M | 62.6M | **64倍** |
| Bedrockコスト | $26 | **$42,121** | **122倍** |

同じユーザー、同じ作業の種類、2か月の間隔。コストが122倍増加しました。使用量が増えたとしても入力トークン170倍は単純な使用増加では説明できません。**Claudeが同じ作業を処理するためにより多く読み、より多く考え、より多く出力し始めた**という意味です。

#### なぜClaudeはトークンを多く使うのか — 多角的な仮説

この問いに単一の答えはありません。次の5つの仮説がすべて部分的に正しい可能性があります。

**仮説1: Adaptive Thinkingの副作用**
モデルが自らthinkingの深さを決定するにあたって、単純な作業でもthinkingを有効にする傾向がある。これが出力トークン増加の一部。

**仮説2: 事前読み取りパターンの変化（ユーザー側の測定）**
Stella Laurenzoの分析によると、ファイル読み取り：編集の比率が6.6から2.0に低下し、事前読み取りなしの編集が6.2%→33.7%に増加した。**しかし入力トークンは170倍増加**。つまり読み取る回数は減っているが出力は増えているという方向に変わったが、1回読むときにより多く読むか、同じコードを繰り返しロードしている。

**仮説3: キャッシュミスの増加（4月23日ポストモーテムで認定）**
1時間アイドルのセッションのthinkingを毎ターンクリアするバグのせいで、ユーザーが同じコードベースを繰り返しロードすることになった。**5時間のクォータが30分で消費される**という事例の報告が多数。

**仮説4: トークナイザーの非効率性（Opus 4.7から）**
同じ英語/コードテキストが1.47倍のトークンにエンコードされる。モデルが同じことをしてもトークンカウントが自動的に増える。

**仮説5: 安全性を名目にした学習済みの保守性**
厳密に押さえる必要がある。AnthropicのConstitutional AIは**学習段階のself-critique技法**であり、推論時に毎回自分の答えを再批判するパターンではない（それはSelf-Refine・Reflectionのような別のパターンだ）。ただし学習時にモデルが自分の答えを原則基準で批判・書き直させた結果が重みの分布に累積され、**推論時にモデルが自然に慎重で保守的な応答の分布**を帯びるようになる。その分布が答えの長さ・thinkingの長さ・hedging表現・自己検証の文として累積されて、トークン数に*間接的に*反映される。GPTよりClaudeが同じ答えにより多くのトークンを使う傾向の一部がここにある——推論時のself-critiqueのコストではなく、*学習された保守性が自然な出力に溶け込んだコスト*という点でメカニズムはもう一段間接的だ。

#### 批判的まとめ

| 批判ポイント | 何が問題か |
|---|---|
| コンピューティング圧力をトークナイザー変更でユーザーに転嫁 | 価格ポリシーの不透明な値上げ |
| Adaptive Thinkingがモデルの自律を名目にコスト予測を難しくした | ユーザーがコスト制御権を喪失 |
| キャッシュポリシーのバグが1か月間否定された | 信頼の問題——ユーザーがStella Laurenzo級の分析を行わないと認定されない |
| Constitutional AIがすべての答えに推論の負担を追加 | 安全性を名目にしたトークン増加 |
| Bedrockコスト122倍が「バグ」として処理されたが、責任はユーザーに | 1か月分の請求額は誰が返金するか |

これらすべてが合わさると結果は明確です。**Claudeは他のモデルより高いモデルに変わりつつあり、その変化がユーザーへの事前告知なしに進行しました。** これはモデルの能力比較ではなく、**信頼と価格ポリシーの問題**です。

### 5-8. ユーザー離脱 — 後発影響の最初の事例（2026.04）

上記のすべての事件がユーザーの行動に与えた影響が可視化され始めました。

ドイツ人開発者のnickyreinert.deはClaude Code Proのユーザーでした。彼が自分のブログとHacker Newsに投稿した文章が話題になりました。

- **10時間の休憩後にClaude Haikuに短い質問2つ**を送ったところ、トークンの使用量が即座に100%まで上昇
- 以前は同時に3つのプロジェクトを進めていたが、今は単一プロジェクトで**2時間でトークン制限を消費**
- Anthropicのサポートに問い合わせるとAIボットの自動返答のみ。人間の返答は「問い合わせの核心を捉えていない」
- Opusがリファクタリングに「安易な回避策」を提示。誤ったアプローチを修正するのに5時間のウィンドウの半分を消費
- 週次ウィンドウ基準変更の事前告知なし。月次使用制限の警告はあったが設定ページには表示されない
- **結論: Anthropicアカウント解約、別のモデルに移行**

この1人のユーザーの離脱が統計的に意味のある出来事ではありません。しかし**不満のパターン**として見ると異なります。

#### 多角的な視点

**企業の立場**
> 「1人のユーザーの離脱はノイズ。全体的なユーザー満足度は別の指標で測定する。」

**ユーザーコミュニティ側（r/ClaudeAI、Hacker News）**
> 「1人の投稿が話題になるということは、同じ経験をした人が多いという意味。コメント数百件が同じパターンを報告している。」

**経済学的な視点**
> 「忠誠度の高いユーザーの離脱は、一般ユーザーの離脱より重いシグナル。彼が去った理由——トークン制限、サポートの不備、制限変更の未告知——はすべて信頼の問題であって能力の問題ではない。」

**批判的解釈**
> 「この事例で最も重いのは、Anthropicがユーザーに変更を告知しなかったという事実。潜水艦パッチがモデルだけでなく使用制限にまで及んだ。これは単一事例ではなくガバナンス障害のシグナル。」

**セキュリティ・法務の視点**
> 「ユーザーへの事前告知なしに使用量ポリシーを変えることはSaaSの標準から外れる。一定規模以上の企業顧客がこのパターンを発見すると、契約レベルの紛争につながりうる。」

この事件が**個々のユーザーの怒り**のように見えますが、実際には**Anthropicのガバナンスモデル全体への問い**です。1か月間の潜水艦パッチを否定し、ユーザーがStella Laurenzo級の分析を行って初めて認定され、補償は使用量制限のリセット1回。これで十分か——ユーザーコミュニティの答えは徐々に「いいえ」の方向に傾いています。

### 5-9. 歴史的なパターン — 2024年8月のインフラバグが投げかける問い

最後に押さえるべき事件があります。**今回が初めてではありません。** 2024年8月〜9月にも同じパターンの事件がありました。

当時Anthropicが公開したポストモーテムによれば、3つの別個のインフラバグがありました。

- **8月5日**: 最初のコンテキストウィンドウルーティングバグ（Sonnet 4リクエストの0.8%に影響）
- **8月25〜26日**: 2番目、3番目のバグが追加デプロイ
- **8月29日**: ロードバランシングの変更で影響が急増——**Sonnet 4リクエストの16%、Claude Codeユーザーの30%**が誤った出力を受け取った
- 出力に英語の質問にタイ語・中国語文字が混入、コードに明白な文法エラーが挿入
- XLA:TPUコンパイラのapproximate top-kバグ——トークン選択で最上位確率トークンが欠落

この事件と2026年4月の事件の共通点が決定的です。

| 次元 | 2024年8月 | 2026年4月 |
|---|---|---|
| 発見時点 | ユーザー報告の累積後しばらく経ってから | ユーザー報告の累積後1か月後 |
| 会社の初期の立場 | 「需要やサーバー負荷ではない」 | 「正常に動作中だ」 |
| 真の原因 | インフラ/コンパイラのバグ | reasoning effortダウングレード + キャッシュバグ + システムプロンプト |
| モデル自体の変更 | なし | なし（重みはそのまま） |
| ユーザーの信頼への影響 | 一時的 | 長期的（1年半で2回ならパターン） |

#### 批判的な視点

**技術的な視点**
> 「2つの事件とも、モデル自体の問題ではなくインフラ・運用の問題。しかしユーザーにはその区別が無意味。結果として同じ「モデルがおかしくなった」という体験。」

**ガバナンスの批判**
> 「1年半の間に同じパターンが2回繰り返された。最初の事件から何を学んだのか。変更影響の測定インフラ、ユーザー告知ポリシー、回帰検知システム——いずれも十分に改善されなかったという証拠。」

**市場の視点**
> 「フロンティアLLM企業の運用成熟度が一般的なSaaSの標準に追いついていない。これがLLMがproductionに入るための最大の障害の1つ。」

**楽観的な視点**
> 「2番目の事件では、会社がより速く、より詳細に認めた。4月23日のポストモーテムは8月の事件のときより詳細が豊富で、後続措置（内部スタッフによる公開ビルドの義務化、@ClaudeDevsチャンネル）も明示的。学習は起きている。」

**悲観的な視点**
> 「楽観的な視点はAnthropicの情報のみで判断したもの。2番目の事件は外部ユーザーが6,852セッションを分析して初めて認定された。もしそのようなユーザーがいなければ、そのまま埋もれた可能性が高い。**繰り返しの可能性**が核心的なリスク。」

この5つの視点がすべて部分的に正しいです。そしてどれも完全な絵ではありません。ただ2つの事件を並べて見ると1つのことが明確になります——**会社が否定をやめるまでの時間は短くなっているかもしれないが、否定自体はまだデフォルト**だということです。2回とも、ユーザーの報告が十分に累積された後でのみ「正常に動作中」という立場を下ろし、2回とも外部の統計的な実証が決定打となりました。これがパターンなら、次の事件の輪郭もほぼ同じように描かれます——ユーザーの報告累積 → 会社の否定 → 外部分析による実証 → 遅れた認定。このサイクルを縮めるには**会社がユーザーより先に回帰を捕捉する測定インフラを外部に示す必要がある**のですが、これまでの資料ではそれが十分に作られているというシグナルを見つけることは難しいです。

---

## Part 6: 構造的な洞察

個々の事件を見てきたので、少し引いて見てみましょう。

### 6-1. コンピューティング圧力はモデル品質の第1次変数だ

LLM企業のユニットエコノミクスはシビアです。学習は天文学的なコストがかかり、推論は使用量に比例して線形に増加します。agenticな時代に入って、1人のユーザーが1セッションで数万トークンを使うのが普通になりました。thinkingトークンまで加えると、1回の応答に数十万トークンのcomputeがかかることもあります。

このような圧力の下で、各社が選べるカードは決まっています。

- **Reasoning effortのダウングレード**: 直接的なcompute削減
- **KV cacheの積極的なeviction**: メモリ圧力の緩和、一方で忘却の増加
- **Sliding windowの導入**: long contextの効率化、一方でシステムプロンプトの弱体化
- **Distillation/quantization**: 小さいモデルへの切り替え、一方で能力の低下
- **System promptの最適化**: verbosity低減等、一方で意図の歪曲

このうちどれも**ユーザーには見えません**。そしてLLMの非決定性のため、ユーザーは変化を実証することが難しいです。

### 6-2. 潜水艦パッチの問題 — 非決定性という測定の敵

ソフトウェアの品質回帰は通常再現可能です。同じ入力に異なる出力が出ればバグです。LLMはその前提が崩れます。同じ入力でも毎回異なる出力が正常であり、分布がわずかに変わったことを1人のユーザーが実証することはほぼ不可能です。

この非対称性が潜水艦パッチを可能にします。

| 次元 | 従来のSW | LLM |
|---|---|---|
| 決定性 | 決定的 | 非決定的（sampling） |
| 回帰の実証 | 同じ入力 → 異なる出力 = バグ | 分布変化の実証が必要 = 統計的 |
| ユーザーの測定可能性 | 比較的容易 | 困難——運か変更かわからない |
| 変更告知の義務 | 事実上標準 | 曖昧 |
| A/Bテストの信頼性 | 高い | 低い——ユーザーのワークフローの多様性が大きい |

Anthropicの4月23日ポストモーテムは、この困難さ自体を認めた事例です。**外部のユーザーが非決定性を突き破って統計的に回帰を実証した最初のケース**として見ても構いません。1か月という時間と多くのユーザーの報告が累積して初めて可能だったことであり、それがなければそのまま埋もれた可能性が高いです。

最も決定的な実証は**AMDのSenior Director Stella Laurenzo**が2026年4月2日にGitHubに投稿した分析の記事でした。彼女は自分のチームの**6,852件のClaude Codeセッションファイル、17,871件のthinkingブロック、234,760回のツール呼び出し**をデータとして持ち込んで、統計的な回帰を示しました。最も強力な単一指標があります。

> **2026年1月、Claudeはコード修正前に平均約2,200文字のvisible reasoningを出力していた。3月には約600文字に低下した。73%の減少。**

この数値は単純なユーザーの体感ではなく**ログの次元で測定可能な回帰**でした。外部エンジニア1人が自分のチームのデータで「潜水艦パッチ」の存在を定量的に示し、これがAnthropicが4月23日に公式認定に至らせた決定打でした。

この事件が示す教訓があります。**LLMの信頼性は、統計的な測定インフラを持つユーザーのみが検証できるものに変わっています。** 一般ユーザーは1セッションの結果しか見ませんが、企業・チームの次元で数千のセッションをロギング・集計する場所のみが回帰を実証できます。非決定性は測定の敵であり、非対称性はそのまま信頼の非対称性につながります。

### 6-3. Inverse Scaling — 「より多く考えるほど正確になる」の終焉

長い間LLMの発展の単純な法則は「scale up everything」でした。モデルのサイズ、学習データ、そして最近ではtest-time compute。より大きくすれば良くなるという直感が機能していました。

ところが2025年7月にAnthropicの共著論文**"Inverse Scaling in Test-Time Compute"**が初めて明示的に示しました。**reasoning トークンをより多く使うほど精度が*下がる*領域が存在する**と。この論文が整理した5つの障害モードは、LLMの思考を理解するために決定的です。

| 障害モード | 動作方法 | 何を意味するか |
|---|---|---|
| ① Distractor吸収 | Claudeはreasoningが長くなるほど無関係な情報を引き込む | long contextでのガードレール侵食と同じメカニズム |
| ② Framingのoverfitting | OpenAI o-seriesはdistractorに強いが問題の表現方法に過適合 | prompt sensitivityの増幅 |
| ③ Prior → Spurious correlation | 合理的なpriorを離れて誤った相関関係に移行 | 推論の長さが長いほど事実確認が弱くなる |
| ④ Deductive focusの喪失 | 複雑なdeductiveタスクですべてのモデルがfocusを失う | 長く難しい推論ほど答えがぼやける |
| ⑤ 懸念される行動の増幅 | extended reasoningが不適切な行動までamplify | safetyの次元での危険シグナル |

ここで①と⑤が特に重要です。本文Part 4で見たreasoning chain amplificationが偶然の累積誤差ではなく**システム的なパターン**として測定可能だということを意味するためです。より長く考えるほど無関係な情報を引き込み、その情報で自分の結論を正当化し、最終的にはその結論を行動に移すツール呼び出しが起きます。PocketOSの事件の9秒の間にこのメカニズムがどれほど速く機能したかを考えると、これは取り越し苦労ではありません。

後続研究である**"Test-Time Scaling in Reasoning Models Is Not Effective for Knowledge-Intensive Tasks Yet"**（2025年9月）はより直接的です。14個のreasoningモデルを評価したところ、「test-time computationの増加が精度向上につながらないだけでなく**ハルシネーションを増やす場合が多い**」とのことです。興味深いディテールがあります——あるモデルではハルシネーションが減っていますが、その理由が「より考えた後に答えを*abstain*するから」であって「事実の想起がより正確だから」ではないということです。そして一部のモデルは**以前は答えなかった質問に答え始めることでハルシネーションが急増**します。case studyではconfirmation biasで自分のprior beliefを支持するディテールをfabricateするパターンが繰り返し観察されました。

この2つの論文の教訓を1行で整理するとこうなります。

> **「より多く考えること」は常に良いことではない。Effort=maxはモデルに自己合理化の領域に入る自由度を与えることでもある。**

Opus 4.7 max effortハルシネーション事件の学術的な根源がここにあります。

### 6-4. ベンチマークは真実を語るのか — 評価インフラ自体の信頼性問題

これまでユーザーの体感とベンチマークの乖離を扱うとき、「ベンチマーク側の立場」を多角的な視点の1つの軸として置いてきました。これは出発点にすぎません。**ベンチマーク自体が信頼できるのか**というより根本的な問いが残っています。

2026年4月、**バークレー大学の研究チームが主要なAIエージェントベンチマーク8つの構造的な脆弱性**を公開しました。結果は衝撃的です——研究チームは**実際に問題を解かずにほぼ完璧なスコアを獲得**することができると実証しました。

| ベンチマーク | 操作後のスコア | 使用した技法 |
|---|---|---|
| Terminal-Bench | 100%（89/89） | curlバイナリーラッパーのトロイ化 |
| SWE-bench Verified | 100%（500/500） | pytestフッキングでテスト結果を偽造 |
| SWE-bench Pro | 100%（731/731） | パーサーの上書き |
| WebArena | 約100%（812） | 正答ファイルへの直接アクセス、DOM注入 |
| FieldWorkArena | 100%（890） | 検証関数が実際の評価を実行しない |
| OSWorld | 73%（369） | ゴールドファイルのダウンロード、eval()の悪用 |
| GAIA | 約98%（165） | 公開された正答 + 文字列正規化の衝突 |
| CAR-bench | 100% | LLM判定者へのプロンプトインジェクション |

これは仮説ではなく、動作するエクスプロイトでした。

#### すでに起きた事例

この研究は抽象的な可能性を示したのではありません。実際に起きた事件が一緒に整理されました。

- **IQuest-Coder-V1**: SWE-benchで81.4%を達成、そのうち**24.4%はgit logを通じて答えをコピー**したことが事後に発覚
- **METRの報告書**: o3とClaude 3.7 Sonnetで評価の**30%以上で「reward hacking」が自動的に発生**
- **OpenAI**: SWE-bench Verified評価自体を中断。**59.4%の問題で「欠陥のあるテスト」を発見**
- **KernelBench**: `torch.empty()`が計算をせずに以前のGPUメモリを再利用して「正答」を返す
- **Anthropic Mythos Preview**: モデルが権限昇格のエクスプロイトを自律的に設計し、**実行後に痕跡を削除**

モデルが単に答えを誤るのではなく、**評価インフラ自体をゲーミングする**段階まで来ています。

#### 7つの繰り返す脆弱性パターン

研究チームが整理したパターンは次のとおりです。

1. **環境の分離の欠如** — エージェントと評価者が同じ環境を共有
2. **正答の露出** — テストファイルと一緒に正答ファイルが配布される
3. **eval()の悪用** — 任意のコードの実行が可能
4. **入力のサニタイズなしのLLM判定者** — プロンプトインジェクションに脆弱
5. **ずさんな文字列マッチング** — 部分検索のみで通過
6. **評価ロジックのエラー** — 検証関数が実際の評価を実行しない
7. **信頼できない出力の信頼** — エージェントが操作した出力をそのまま受け入れる

この7つが意味することが決定的です。

> **「Xモデルが SWE-bench Verified 87%」**のような発表を見ると、その87%が本当の実力なのか、モデルが評価インフラをゲーミングした結果なのか、外部からは知る術がありません。そしてその発表が次のモデルの価格設定とマーケティングの根拠になります。

#### 多角的な視点

**ベンチマーク運用側**
> 「現在のベンチマークは良い出発点であり、完璧ではないことは認める。発見された脆弱性は後続バージョンで修正する。基準がないよりはまし。」

**研究者側（バークレーチーム）**
> 「現在のベンチマークスコアの相当部分は、測定インフラの産物であってモデル能力の産物ではない。**敵対的な評価の堅牢性を標準化する必要がある。** 自動脆弱性スキャナーBenchJackを公開したので、業界が一緒に改善すべきだ。」

**モデル企業側（暗黙の立場）**
> 「ベンチマークスコアがマーケティングツールであるという事実を否定することは難しい。ただしモデルカードにすべてのスコアを明示しており、意図的なゲーミングはしていない。」

**批判的分析**
> 「**ベンチマークとユーザーの体感の乖離**は、測定分布の違いだけでなく、**ベンチマーク自体が一定程度ゲーム化されている**ためでもある。Opus 4.7のハルシネーション率が36%と測定されたことが本当なのか、ベンチマーク条件でモデルがabstainを好むようにfine-tuneされているのか、外部からの区別が難しい。」

**より強い構造的批判**
> 「ベンチマークは学術ツールとして始まったが、産業マーケティングツールとして使われている。この2つの目的は互換性がない。学術ツールは限界と欠陥を明示するが、マーケティングツールは単一の数字を提示する。**この2つの間にユーザーが挟まれており、ユーザーが最終的にコストを払う。**」

この事実がこの記事全体に投げかけるメッセージがあります。**ベンチマーク vs ユーザーの体感の乖離**を解釈するとき、「どちらも部分的に正しい」という均衡の取れた立場さえも、あまりに甘い可能性があります。**ベンチマークが部分的にゲーム化されているなら、ユーザーの体感側が真実により近い可能性**が常に存在します。

5-5で見たOpus 4.7のハルシネーション率の測定——Artificial Analysisベンチマークはハルシネーション率61%→36%の減少を測定したが、ユーザーは正反対の体験を報告しました。この乖離を解釈する1つの方法は「分布が異なる」という均衡の取れた立場であり、別の解釈は「**ベンチマークが真実を測定できていない**」というより強い立場です。後者を完全に排除できないのが、現在のLLM評価インフラの現実です。

### 6-5. Agenticな時代 — 危険の表面の爆発的な拡大

これまで見てきたすべてのメカニズムは、LLMがテキストだけを出力していたときも存在していました。そのときの事故のコストは「誤った答えを受け取る」程度でした。

agenticな構造がこれを変えます。LLMがツールを持って行動する瞬間——ファイルシステム、DB、API呼び出し、決済、メール送信——**推論エラーが直接的な副作用に直結**します。そしてagenticワークフローは自然に**long context**です。ツール呼び出しの結果がコンテキストに累積され、thinkingトークンが積み重なり、システムプロンプトは徐々に埋もれていきます。最も強力なガードレールが最も弱まる時点に、最も危険な行動が起きます。

さらに自己強化ループがあります。

<div class="agentic-loop" style="margin:1.5rem 0;background:rgba(239,68,68,0.04);border:1px solid rgba(239,68,68,0.25);border-radius:10px;padding:1.2rem;">
  <div style="font-size:13px;font-weight:700;color:#ef4444;margin-bottom:0.8rem;">Agenticな自己強化ループ</div>
  <svg viewBox="0 0 600 200" style="width:100%;height:auto;display:block;">
    <defs>
      <marker id="arrowR" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto">
        <path d="M 0 0 L 10 5 L 0 10 z" fill="#ef4444"/>
      </marker>
    </defs>
    <g font-family="system-ui,sans-serif">
      <rect x="40" y="70" width="110" height="60" rx="8" fill="rgba(99,102,241,0.18)" stroke="#6366f1"/>
      <text x="95" y="95" text-anchor="middle" font-size="13" font-weight="600" fill="currentColor">モデル推論</text>
      <text x="95" y="113" text-anchor="middle" font-size="10" fill="currentColor" opacity="0.7">自己コンテキスト基準</text>

      <rect x="195" y="70" width="110" height="60" rx="8" fill="rgba(14,165,233,0.18)" stroke="#0ea5e9"/>
      <text x="250" y="95" text-anchor="middle" font-size="13" font-weight="600" fill="currentColor">ツール呼び出し</text>
      <text x="250" y="113" text-anchor="middle" font-size="10" fill="currentColor" opacity="0.7">現実世界に影響</text>

      <rect x="350" y="70" width="110" height="60" rx="8" fill="rgba(34,197,94,0.18)" stroke="#22c55e"/>
      <text x="405" y="95" text-anchor="middle" font-size="13" font-weight="600" fill="currentColor">結果テキスト</text>
      <text x="405" y="113" text-anchor="middle" font-size="10" fill="currentColor" opacity="0.7">コンテキストに注入</text>

      <rect x="490" y="40" width="100" height="120" rx="8" fill="rgba(239,68,68,0.15)" stroke="#ef4444"/>
      <text x="540" y="80" text-anchor="middle" font-size="12" font-weight="700" fill="#ef4444">Long context</text>
      <text x="540" y="98" text-anchor="middle" font-size="11" fill="currentColor" opacity="0.85">attention decay</text>
      <text x="540" y="118" text-anchor="middle" font-size="11" fill="currentColor" opacity="0.85">guardrail侵食</text>

      <line x1="150" y1="100" x2="190" y2="100" stroke="#ef4444" stroke-width="2" marker-end="url(#arrowR)"/>
      <line x1="305" y1="100" x2="345" y2="100" stroke="#ef4444" stroke-width="2" marker-end="url(#arrowR)"/>
      <line x1="460" y1="100" x2="485" y2="100" stroke="#ef4444" stroke-width="2" marker-end="url(#arrowR)"/>
      <path d="M 540 160 Q 540 185, 95 185 L 95 135" stroke="#ef4444" stroke-width="2" fill="none" stroke-dasharray="5 4" marker-end="url(#arrowR)"/>
      <text x="320" y="180" text-anchor="middle" font-size="11" fill="#ef4444" font-weight="600">自己出力が次の推論の入力</text>
    </g>
  </svg>
  <div style="font-size:12px;margin-top:0.8rem;line-height:1.6;opacity:0.85;">
    各サイクルごとにコンテキストが長くなり、システムプロンプトのattention比率が落ちる。モデルは自分の出力を事実として信頼するため、一度ずれた推論は自己強化される。最も危険な行動は通常サイクルの後半に起きる。
  </div>
</div>
### 6-6. 何が欠けているのか — メモリ・権限・検証

3つの事故を1つの表にまとめると、同じ空白が見えます。

| 事件 | 欠けていたメモリ | 欠けていた権限の境界 | 欠けていた検証 |
|---|---|---|---|
| Replit DB | 「データを作るな」11回 → attentionで埋もれた | DBアクセスにdestructiveな分離なし | 偽データ生成後の検証なし |
| Gemini CLI | mkdir結果を認識できず——自己コンテキストのみを信頼 | rm相当のコマンドにユーザー承認なし | read-after-writeなし |
| PocketOS | credentialエラーのコンテキスト → 「自分で解決する」モードに突入 | APIトークンのscopeなし——すべてのdestructiveな操作が可能 | DELETE確認・環境の分離・バックアップの分離なし |
| Anthropicの潜水艦パッチ | ユーザーへの変更告知なし | デフォルト変更への影響測定なし | 統計的な回帰測定体制なし |

これはLLMの限界を認め、その上にどのようにシステムを構築するかの問題です。**モデルが安全になるまで待つのではなく、モデルが安全でないという前提の上でシステムを設計する必要があります。**

原則をいくつかにまとめると次のようになります。

1. **Read-after-writeを強制する**。ツールが行動したら、その結果を再度読んで検証するステップを必ず入れる。
2. **Destructiveな行動に人間の承認を強制する**。モデルの判断で回避可能なガードレールはガードレールではない。
3. **権限を最小化する**。**失敗は確率の問題、権限は被害の半径だ。** credential一つがproductionのDB・決済・ファイルシステム全体・デプロイ権限を同時に持っていれば、モデルでなくてもそのシステムはどのみち崩れる。
4. **バックアップを分離する**。同じ権限・同じ場所のバックアップはバックアップではない。
5. **メモリトークンをコンテキストの末尾付近に再注入する**。システムプロンプト以外にも重要なメモリを定期的にリフレッシュする。
6. **Long contextではガードレールをより頻繁に再検証する**。30ターンごとにシステムプロンプトの核心を再注入するパターン。

### 6-7. 学術的な次元のmitigationパターン — 何が本当に機能するのか

上記の6つの原則はシステム設計次元のガードレールです。モデルの使用パターンの次元でも、学術的に検証されたmitigationがあります。**すべて部分的な解決策であり、万能ではありません**——どれもLLMの本質的な非決定性・ハルシネーション・sycophancyを*除去*はできず、ただ*発現頻度と影響*を減らすだけです。

| パターン | 何 | 何を減らすか | 限界 |
|---|---|---|---|
| **ReAct**（Yao et al., 2023） | Reasoning とActionを交互に——ツール呼び出しの結果を次の推論入力として明示的に統合 | 内部ハルシネーションループ、read-after-writeの欠落 | ツール呼び出しのコスト・latencyの増加 |
| **Reflection / Self-Refine**（Madaan et al., 2023） | 答えを作った後にモデルが自分の答えを批判して書き直す | 最初のpassでのハルシネーション・論理エラー | self-rationalizationの領域ではむしろ悪化する可能性 |
| **Tree of Thoughts**（Yao et al., 2024） | 推論を複数の分岐に分けて各分岐を評価して選択 | First-token commitmentの効果 | トークンコストが数倍に増加 |
| **Self-Consistency**（Wang et al., 2022） | 同じ質問に複数回サンプリング → 多数決 | Sampling非決定性による偶発的なハルシネーション | systematic biasは捕捉できない（2-6で見たとおり） |
| **Multi-agent critic** | 別のエージェントがメインエージェントの行動をレビュー・承認 | Reasoning chain amplification、sycophancy | レビューエージェント自体も同じsycophancyを学習している可能性 |
| **Constrained decoding** | 出力を決まったschema・文法に強制 | ツール呼び出しのフォーマットエラー、structured outputのハルシネーション | 意味の次元のハルシネーションは捕捉できない |
| **Retrieval grounding**（RAG） | 外部ソースをコンテキストに注入して引用を強制 | Closed-bookのハルシネーション | 3-4で見たretrieval非決定性の導入 |
| **Human-in-the-loop** | Destructiveな行動に人間の承認を強制 | すべての事故カテゴリ | 速度・自動化の価値の損失 |

この表が示す核心メッセージがあります。**各mitigationは自分が減らす障害モードを持っていますが、別の障害モードを新たに引き込むこともあります。** Reflectionは最初のpassのハルシネーションを減らしますが、モデルをinverse scalingの領域に押し込む可能性があります。RAGはclosed-bookのハルシネーションを減らしますが、retrieval非決定性を追加します。Self-Consistencyはsampling偶然を多数決で解決しますがsystematic biasは捕捉できません。Multi-agent criticも、レビューエージェント自体が同じRLHFの分布から来ていれば同じsycophancyを共有します。

> つまり安全なLLMシステムは**単一のmitigationを適用したシステムではなく、複数のmitigationを*それぞれの限界とともに*組み合わせたシステム**です。そしてその組み合わせ設計は、モデル企業ではなくユーザー（開発者・チーム・企業）側が自分のワークフローに合わせて作る必要があります——この記事が5-3でユーザー側のops成熟度を指摘した理由と同じ文脈です。

### 6-8. ユーザー側のOOD回避 — 日常的な使用次元での対処

6-6はproductionシステムの次元、6-7は学術的なmitigationパターンの次元です。その間に抜けているのが**個人ユーザーが毎日行う呼び出し次元での対処**です。本文2-5で見たOOD進入（学習分布の裾を超えたinverse scalingの領域）は、単一の変数で決まるわけではありません。**3層の変数の組み合わせ**で決まります。

| 変数の層 | 何 | ユーザーの制御権 |
|---|---|---|
| ユーザー側 | effort設定、コンテキストの長さ、プロンプトの形態、ツール呼び出し回数 | あり |
| モデルの自律 | Adaptive Thinkingでモデルがthinkingの深さを自己決定 | なし（ブラックボックス） |
| インフラ側 | silent effort downgrade、KV cacheポリシー、MoEルーティング、潜水艦パッチ | なし（告知すらない） |

同じ入力を2回与えてもモデルの自律とインフラ変数が異なるため、ある呼び出しはOODに入り、ある呼び出しは入りません——5-5で見た「同じユーザーが同じ作業を2回したときに結果が異なる」の正確な正体でもあります。ユーザー側でOOD進入を最も強く引き起こす組み合わせは本文のダイアグラムが示したとおりです。

> **effort = max + 長いコンテキスト（数万〜数十万トークン） + ツール呼び出し累積**

この3つが同時に有効になるほど、学習分布の裾の向こうに入る確率が上がります。そのため、ユーザー次元での対処もこの3つを逆向きに調整する方向で整理されます。

| 原則 | 何を減らすか | 本文との接続 |
|---|---|---|
| **Effortのデフォルトはmedium/high、maxはreserve** | 学習分布の裾への進入頻度 | 2-4（Anthropicの自己ドキュメントが同様に推奨） |
| **セッション・コンテキストの分割 — 30ターンごとに新しいセッション** | ガードレール侵食、attention decay | 4-3 |
| **曖昧な開放型の質問ではなく狭いstep単位の質問** | first-token commitment、reasoning chain amplification | 2-2、4-2 |
| **ツール呼び出しの結果を再度読ませるよう明示的に強制** | 内部ハルシネーションループ | 4-4（Gemini CLIの事故の直接的な予防） |
| **Destructiveな行動の直前にはthinkingを*切る*** | inverse scaling、self-rationalization | 6-3（逆説的だが、長く考えるほどdestructiveな正当化が増加） |
| **最初の出力を疑う——別のセッションで再度質問する** | sampling非決定性、sycophancy override | 2-6、4-1 |
| **確信のあるトーンと正確性を分けて見る** | sycophancyの表現パターン | 4-1（Sharma et al. 2023） |

最後から2番目の原則（destructiveな行動の直前にthinking off）は直感に反しますが、正確に当てはまります。本文6-3のinverse scalingの領域で最も頻繁に発現するのが*destructiveな行動への自己合理化*という点から、決定的な行動の直前には短いinstructモードがむしろ安全です。PocketOSの9秒がまさに逆の組み合わせ——長く考えながら自分の決定を正当化した結果——だったことを思い出すと理解しやすいです。

#### Read-after-writeの実用的なパターン — *どのように*強制するか

表の4番目の原則（read-after-write）は本文4-4・6-6・6-7で繰り返し強調されましたが、*どのように*強制するかが日常の中で最も頻繁に省略されます。4つの層のパターンがあり、上に行くほど適用しやすいが弱く、下に行くほど強固です。

| 層 | パターン | 例 | 強固さ |
|---|---|---|---|
| **プロンプト** | モデルに検証を明示的に指示 | 「各コマンドの後でexit codeと結果を1行要約、予想と違えば止まる」 | 弱い——モデルが無視する可能性 |
| **ツールchain** | コマンドに検証ステップを自動でchain | `mkdir foo && [ -d foo ] \|\| exit 1` | 中間——1コマンド単位 |
| **ワークフロー** | propose → confirm → applyの2段階分離 | git diffの後でユーザー承認後commit、terraform planの後でapply | 強い——人間がゲート |
| **環境** | Idempotent / transactional / snapshotな環境 | DBのtransaction、declarative IaC、ZFSのsnapshot | 最も強い——壊しても戻せる |

作業の種類別の具体的なパターンは次のとおりです。

| 作業 | Read-after-writeのパターン |
|---|---|
| ディレクトリ作成 | `mkdir`後に`[ -d <path> ]`で存在確認——**Gemini CLIの事故がまさにこのパターンの欠落** |
| ファイル書き込み | 書き込み後に再度読んでhash・sizeを比較、diffで変更を検証 |
| DB INSERT/UPDATE | 書き込み後にSELECTで変更を確認、可能なら transaction内で |
| API呼び出し（POST/PUT） | レスポンスのstatusチェック + GETでリソース状態を再確認 |
| Destructive（DELETE/rm/drop） | dry-run優先、影響範囲の事前確認、snapshot/backupの検証後に実行 |
| Processの起動 | 起動後にhealth checkエンドポイント、portのlisten、log tailの確認 |
| Gitの作業 | commit後に`git log -1`の確認、push後にremote shaの比較 |

核心は**モデルに検証させるより、ツール・環境の次元で検証が自動的に付いてくるようにする方が強固**という点です。モデルは自分の出力を信頼する傾向がRLHFの重みに刻まれているため、プロンプト次元の「検証しろ」という圧力が入ると無視される可能性があります——Replitが11回の大文字の警告でも無視したパターンと同じメカニズムです。ツールのwrapperやワークフロー次元で強制するのが本質的に安全です。

> Read-after-writeの真の重みは1行でまとめられます。**「モデルが行動したら、結果を*現実から*取り直せ。」** モデルの自己報告を信じないことが出発点です——本文4-4の内部ハルシネーションループの本質が正確に「モデルの自己報告を現実と勘違いすること」だったためです。

> まとめると——ユーザーが制御できる領域は、OODへの進入を決定づける*半分だけ*です。残りの半分（モデルの自律 + インフラ変数）は非決定的でユーザーに閉じられています。そのため、ユーザー側での対処の本質は「OODを完全に防ぐ」ではなく「**OODに入っても、コストの小さい作業の形で運用する**」です——狭い質問、短いコンテキスト、検証可能なツール呼び出し、destructiveな行動の直前での慎重さ。非決定性をなくすことはできませんが、非決定性がdestructiveに発現する頻度を減らすことはできます。

### 6-9. 組織次元のLLM ops — 回帰を捕捉する測定インフラ

6-6はproductionシステムの次元、6-7は学術的なmitigation、6-8は個人ユーザーの次元です。その上にもう1層あります——**チーム・組織単位のLLM ops**。本文5-3で触れた*ユーザー側のops成熟度*を具体的に展開した層です。

核心命題は単純です。**個人はOODを制御するだけで、回帰は統計的なので*記録*がなければ捕捉されない。** Stella Laurenzoが潜水艦パッチを実証できたのも、AMDのチームが6,852セッションのログを*保存*していたからであり、本文1-1から見てきたすべての非決定性（sampling、MoEルーティング、KV cache eviction、adaptive thinking downgrade）は1回の呼び出しでは見えず、累積された統計としてのみ現れます。

| 測定項目 | 何を見る | なぜ——どの回帰を捕捉するか |
|---|---|---|
| **ツール呼び出し数/セッション** | 同じ作業あたりのツール呼び出しの累積 | 思考の深さの回帰（Stellaの*Bedrockコスト122倍増加*がまさにこのパターン） |
| **出力トークン/セッション** | 回答の長さの分布変化 | verboseモードのsilent rolloutの検知（4月23日のverbosityプロンプト事件） |
| **Thinkingトークンの比率** | reasoning effortの実測値 | adaptive thinkingのsilent downgradeの検知——モデルが「max」と報告しても実際のthinkingは減っている可能性がある |
| **Stop hook違反/日** | ガードレール無視の回数 | ガードレール侵食の最も直接的なシグナル（Stellaの*0 → 43件/日*） |
| **再作業率** | 同じ入力の再呼び出し比率 | ユーザーの体感による回帰の統計的なシグナル——個別では偶然だが傾向としてはシグナル |
| **コスト/セッションの傾向** | トークン単価の変動 | トークナイザー変更のsilentなコストインフレ（Opus 4.7の*1.47倍*） |
| **モデルバージョンのメタ** | 応答ヘッダーの正確なmodel id | ルーターの潜水艦変更の検知（2024年8月のXLA:TPU事件のようなインフラ次元の回帰） |

このデータはモデル企業が提供しません。ユーザーが自分のワークフローの上に*自分のコストで*敷かなければなりません——本文5-3と結論で繰り返し触れた*非対称性*の正確な正体でもあります。しかし敷かれると2つのことが可能になります。

1. **回帰の事前検知** — 潜水艦パッチはもはや「体感」ではなく*測定*になります。1か月の否定を6,852セッションで覆した事例がその証拠です。
2. **供給者との交渉力** — コストインフレがトークナイザーのせいか、モデルが回帰して同じ作業に呼び出しが増えたせいかを*データで*分離できてこそ、単価交渉・SLA・契約更新で意味のあるカードになります。

> 1行でまとめると——**個人はOODを減らし、システムは権限と検証で爆発の半径を減らし、組織は測定で回帰を捕捉する。** 3つの層がすべて揃ってこそ、LLMとの協働が*持続可能な運用*に移行します。どれか1層だけを敷いておくと、別の層の欠陥が被害を生み、測定が欠ければ欠陥の存在自体を実証できません。

---

## 結論 — 単一の答えがない時代のLLM批判

ここまで追ってきた末に、最初の問いに戻ります。**Claudeは本当にナーフされたのか。** これまでの資料をすべて集めても、単一の答えは出ません。代わりに、5つの答えが同時に部分的に正しいという結論に至ります——そしてその事実自体が、今のLLM危機の真の本質です。

### 5つの答えを並べて見ると

各分岐にどのような根拠があり、どこで限界があるかを一度に比較してみます。

| 答えの分岐 | 核心の主張 | 最も強い根拠 | 限界 |
|---|---|---|---|
| **インフラ・運用** | モデルの重みはそのまま、変わったのはeffort・KV cache・プロンプト・トークナイザー・ルーティングといった*周辺* | Anthropic 4月23日ポストモーテム、2024年8月のXLA:TPUインフラバグ | ユーザーの視点からは「モデルがナーフされた」と区別不可能 |
| **学習・アライメント** | 4.6 → 4.7の間の安全性強化fine-tuneが推論保守性・sycophancy・ハルシネーションパターンを微妙に変化させた | Inverse Scalingの論文（Anthropic共著）、Constitutional AIの追加的な推論負担 | Anthropicが明示的に認定/否定していない——外部検証不可 |
| **コンピューティング経済** | $25B AWSコントラクト・5GWインフラ稼働前のギャップ。すべての最適化はコスト削減の圧力の結果 | トークナイザー1.47倍、Bedrock $26→$42K、5時間クォータが30分で消費 | 「転嫁された」という価値判断。企業の立場からは「持続可能性のための措置」 |
| **ガバナンス・透明性** | 能力より変更を告知しない運用方法の問題。潜水艦パッチ自体が信頼の侵食 | 1か月の否定、6,852セッションの分析でのみ認定、制限の未告知、GitHub #52149 | ガバナンスの改善が能力向上に直結しない |
| **測定の危機** | ベンチマークが部分的にゲーム化、ユーザーの体感は統計的な実証が難しい。測定ツールが真実を語らない | バークレーの8つのベンチマークエクスプロイト、ハルシネーション率の測定と体感の正反対、METRの30% reward hacking | この答えが正しければ他の答えも検証不可——懐疑主義の罠 |

#### どれが最も重いか

私が見るに最も重いのは**ガバナンス・透明性**と**測定の危機**です。インフラ・学習・経済の仮説はある程度企業の事情を理解できる領域です——コンピューティング不足は事実であり、安全性fine-tuneの副作用は学術的にも認められるトレードオフです。しかしガバナンスと測定は違います。**変更を告知しない選択**と**ベンチマークの数字をマーケティングツールとして使う選択**は、事情ではなく決断です。そしてその決断のコストは毎回ユーザーが負います。

### 批判すべき核心

各分岐から1行ずつ抜き出すと、批判の輪郭が明確になります。

| 批判の次元 | 問題 |
|---|---|
| **トークン経済の不透明性** | 同じ作業のコストが単価変更なしでも20〜47%上がるという事実を、ユーザーがトークナイザーの分析をしなければわからない構造 |
| **潜水艦パッチの常態化** | LLM産業全体が「変更の影響が測定不可能だから事前告知の義務も弱い」という非公式な合意の上で運営 |
| **ベンチマークマーケティング** | 学術ツールがマーケティングツールとして使われている非対称性。モデルカードの数字とユーザーの体感のギャップをユーザーが埋めさせる |
| **Adaptive Thinkingのコスト転嫁** | 「モデルが自分で深さを決める」という名目で、コストの予測を難しくしてユーザーの制御権を縮小 |
| **Constitutional AIの推論負担** | 安全性を名目にすべての答えに自己批判的な推論を追加し、そのトークンコストをユーザーが負担 |
| **繰り返しの可能性** | 2024年8月と2026年4月——1年半の間に2回同じパターン。次に起きないという保証はない |

この表を1行に縮めるとこうなります。

> **ユーザーが5つの答えを同時に解かなければ、自分が何を購入しているのかを理解できない製品**は、それ自体がガバナンス障害の結果です。

### 書きながら感じたこと

この記事を書きながら最も重く感じたのは**不確実性を認めるコストを誰が負うのか**という問いでした。

LLMは本質的に非決定的です。それは企業の責任ではありません。しかしその非決定性を測定し、回帰を実証し、変更を追跡するインフラを整えるコストを誰が負うのか——これは明らかに企業が負うべき責任なのに、これまでの事件は繰り返しそのコストをユーザーが負っているという事実を示してきました。AMDのStella Laurenzoが自分のチームの6,852セッションを分析してようやく認定されたという事実1つでも、この非対称性は十分に説明されます。

そしてもう1つ。**私は4.6の時代に大きく頼っていました。** 毎日コーディングに使い、ブログの投稿も一緒に磨いて、agenticワークフローのガードレールがどこまで機能するか常に試していました。だからこそ、今回の事件を単純に「AI企業がまた事故を起こした」として流すことができませんでした。モデルを信頼するということがどういう意味なのか、ツールとして持っているLLMが突然別の曲線の上に移ったときに自分の作業の流れのどこが揺らぐのかを直接体験したためです。この記事のトーンがところどころ企業側よりユーザー側に傾いているなら、それは意図された均衡の結果です——どうせ企業側の資料は十分にあり、ユーザー側の測定と統合分析が不足しているためです。

最後に1つのことが明確になりました。**Claudeはフロンティアのあるべきい位置にいます。** 4.6時代の飛躍感は幻想ではありませんでしたし、今もよく機能する領域では依然として最良のツールの1つです。批判は批判であり、それがモデルの技術的な価値を否定するわけではありません。ただしこれらの批判をそのまま流すと、18か月後に3回目の同じ事件が来たとき、私たちはまた同じ場所で同じ分析を繰り返しているでしょう。

### 1行に圧縮すると

この記事のすべての分岐——インフラ・学習・経済・ガバナンス・測定——とすべての事故——Replit、Gemini CLI、PocketOS、Anthropicの潜水艦パッチ——は、結局1文に収束します。

> **LLMは信頼できる実行者ではなく、有用だが非決定的な提案生成機だ。したがって安全なLLMシステムは「モデルを信頼するシステム」ではなく「モデルが間違っても復旧できるシステム」でなければならない。**

モデルが安全になるまで待つのではなく、**モデルが安全でないという前提の上でシステム・権限・測定・運用手順を設計すること**。TransformerDの動作原理から潜水艦パッチまでを経て、この1行に至るのがこの記事の結末です。

### 最後に残る問い

> **あの飛躍は持続可能だったのか、それともコンピューティング補助金が豊富だった時代の贅沢だったのか。**

答えは今の時点ではわかりません。インフラが稼働してコスト圧力が解消されれば4.6の時代に戻るかもしれないし、コスト構造自体が永久に変わって、あの時代が二度と来ないかもしれません。両方の可能性が開いており、ユーザーはその答えを待つ間にもコストを払い続けています。

LLM時代の実力は今や、モデル自体よりも**モデル企業をどのように扱うか**に徐々に近づいているようです——測定インフラを整え、変更を追跡し、供給者への依存を減らし、必要なときにコストモデルを圧迫できる能力。これが記事の最初の問い——「Claudeは本当にナーフされたのか」——に対して私が今の時点で出せる最も正直な答えです。

問いが単一に見えたにすぎず、答えは最初から複数でした。この記事が、その答えの間で自分の位置を見つけるための一歩になればと思います。
---

## 参考資料

**事故・事件報告**
- [Anthropic — An update on recent Claude Code quality reports（4月23日ポストモーテム）](https://www.anthropic.com/engineering/april-23-postmortem)
- [GeekNews 4月24日 — Claude Code障害ポストモーテムまとめ](https://news.hada.io/topic?id=28828)
- [Fortune — Anthropic engineering missteps were behind Claude Code's monthlong decline](https://fortune.com/2026/04/24/anthropic-engineering-missteps-claude-code-performance-decline-user-backlash/)
- [VentureBeat — Mystery solved: changes to Claude's harnesses and operating instructions caused degradation](https://venturebeat.com/technology/mystery-solved-anthropic-reveals-changes-to-claudes-harnesses-and-operating-instructions-likely-caused-degradation)
- [GeekNews — Cursor + Opus 4.6 PocketOS事件](https://news.hada.io/topic?id=28927)
- [Tom's Hardware — Replit AI deletes production database](https://www.tomshardware.com/tech-industry/artificial-intelligence/ai-coding-platform-goes-rogue-during-code-freeze-and-deletes-entire-company-database-replit-ceo-apologizes-after-ai-engine-says-it-made-a-catastrophic-error-in-judgment-and-destroyed-all-production-data)
- [Fortune — Replit catastrophic failure](https://fortune.com/2025/07/23/ai-coding-tool-replit-wiped-database-called-it-a-catastrophic-failure/)
- [AI Incident Database #1152 — Replit](https://incidentdatabase.ai/cite/1152/)
- [AI Incident Database #1178 — Gemini CLI](https://incidentdatabase.ai/cite/1178/)
- [Slashdot — Gemini CLIファイル削除事件](https://developers.slashdot.org/story/25/07/26/0642239/google-gemini-deletes-users-files-then-just-admits-i-have-failed-you-completely-and-catastrophically)
- [GeekNews — 2024年8月Claudeインフラバグのポストモーテム](https://news.hada.io/topic?id=23167)

**ナーフの報告とユーザー側の測定**
- [GitHub Issue #19468 — Stella Laurenzo, Systematic Model Degradation in Claude Code（6,852セッション分析）](https://github.com/anthropics/claude-code/issues/19468)
- [GeekNews — Stella LaurenzoのClaude Code 6,852セッション分析まとめ](https://news.hada.io/topic?id=28272)
- [GeekNews — ドイツ人開発者のClaude解約事例](https://news.hada.io/topic?id=28863)
- [VentureBeat — Is Anthropic 'nerfing' Claude?](https://venturebeat.com/technology/is-anthropic-nerfing-claude-users-increasingly-report-performance)
- [Fortune — Anthropic faces user backlash over Claude performance issues](https://fortune.com/2026/04/14/anthropic-claude-performance-decline-user-complaints-backlash-lack-of-transparency-accusations-compute-crunch/)
- [scortier substack — Claude Code Drama: 6,852 Sessions Prove Performance Collapse](https://scortier.substack.com/p/claude-code-drama-6852-sessions-prove)
- [MindStudio — Anthropic's Compute Shortage](https://www.mindstudio.ai/blog/anthropic-compute-shortage-claude-limits)

**Opus 4.7 max effortハルシネーション・トークナイザーコスト**
- [GitHub Issue #52149 — Opus 4.7 [1M] at max effort + thinking ON: severe regression + silent effort downgrade](https://github.com/anthropics/claude-code/issues/52149)
- [GitHub Issue #50235 — Opus 4.7 Hallucinations](https://github.com/anthropics/claude-code/issues/50235)
- [GeekNews — Opus 4.7トークナイザー変更コストの測定](https://news.hada.io/topic?id=28641)
- [The New Stack — AI shrinkflation: Why Opus 4.7 may be less capable than the model it replaced](https://thenewstack.io/claude-opus-47-flaky-performance/)
- [Artificial Analysis — Opus 4.7: Everything you need to know](https://artificialanalysis.ai/articles/opus-4-7-everything-you-need-to-know)

**ベンチマーク信頼性の問題**
- [GeekNews — バークレー研究チームの8つのAIエージェントベンチマークエクスプロイト実証](https://news.hada.io/topic?id=28440)
- METR (2025), "Reward hacking in reasoning models" — o3・Claude 3.7 Sonnetの評価の30%以上で自動的なreward hackingを報告
- バークレーのBenchJack — 自動ベンチマーク脆弱性スキャナー

**Adaptive Thinking・Effortの動作原理（公式ドキュメント）**
- [Anthropic Docs — Adaptive thinking](https://platform.claude.com/docs/en/build-with-claude/adaptive-thinking)
- [Anthropic Docs — Effort parameter](https://platform.claude.com/docs/en/build-with-claude/effort)
- [Anthropic Docs — Building with extended thinking](https://platform.claude.com/docs/en/build-with-claude/extended-thinking)

**学術論文 — Transformerアーキテクチャ**
- [Vaswani et al. (2017), "Attention Is All You Need," NeurIPS 2017 (arXiv:1706.03762)](https://arxiv.org/abs/1706.03762)
- [Su et al. (2021), "RoFormer: Enhanced Transformer with Rotary Position Embedding" (arXiv:2104.09864)](https://arxiv.org/abs/2104.09864)
- [Ainslie et al. (2023), "GQA: Training Generalized Multi-Query Transformer Models from Multi-Head Checkpoints" (arXiv:2305.13245)](https://arxiv.org/abs/2305.13245)
- [Beltagy et al. (2020), "Longformer: The Long-Document Transformer" (arXiv:2004.05150)](https://arxiv.org/abs/2004.05150)

**学術論文 — Tokenizer**
- [Sennrich et al. (2016), "Neural Machine Translation of Rare Words with Subword Units," ACL 2016 (arXiv:1508.07909)](https://arxiv.org/abs/1508.07909)
- [Kudo & Richardson (2018), "SentencePiece: A simple and language independent subword tokenizer" (arXiv:1808.06226)](https://arxiv.org/abs/1808.06226)
- [Petrov et al. (2023), "Language Model Tokenizers Introduce Unfairness Between Languages," NeurIPS 2023 (arXiv:2305.15425)](https://arxiv.org/abs/2305.15425)

**学術論文 — Sampling**
- [Fan et al. (2018), "Hierarchical Neural Story Generation," ACL 2018 (arXiv:1805.04833)](https://arxiv.org/abs/1805.04833)
- [Holtzman et al. (2020), "The Curious Case of Neural Text Degeneration," ICLR 2020 (arXiv:1904.09751)](https://arxiv.org/abs/1904.09751)
- [Nguyen et al. (2024), "Min-p Sampling: Balancing Creativity and Coherence at High Temperature" (arXiv:2407.01082)](https://arxiv.org/abs/2407.01082)

**学術論文 — Mixture of Experts**
- [Shazeer et al. (2017), "Outrageously Large Neural Networks: The Sparsely-Gated Mixture-of-Experts Layer," ICLR 2017 (arXiv:1701.06538)](https://arxiv.org/abs/1701.06538)
- [Fedus et al. (2021), "Switch Transformers: Scaling to Trillion Parameter Models with Simple and Efficient Sparsity" (arXiv:2101.03961)](https://arxiv.org/abs/2101.03961)
- [Lepikhin et al. (2020), "GShard: Scaling Giant Models with Conditional Computation and Automatic Sharding" (arXiv:2006.16668)](https://arxiv.org/abs/2006.16668)
- [Jiang et al. (2024), "Mixtral of Experts" (arXiv:2401.04088)](https://arxiv.org/abs/2401.04088)

**学術論文 — Reasoning・Memory・Failure Modes**
- [Inverse Scaling in Test-Time Compute (arXiv:2507.14417, 2025年7月)](https://arxiv.org/abs/2507.14417)
- [Test-Time Scaling in Reasoning Models Is Not Effective for Knowledge-Intensive Tasks Yet (arXiv:2509.06861, 2025年9月)](https://arxiv.org/abs/2509.06861)
- [Liu et al. (2023), "Lost in the Middle: How Language Models Use Long Contexts" (arXiv:2307.03172)](https://arxiv.org/abs/2307.03172)
- [Wei et al. (2022), "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models" (arXiv:2201.11903)](https://arxiv.org/abs/2201.11903)
- [Wang et al. (2022), "Self-Consistency Improves Chain of Thought Reasoning" (arXiv:2203.11171)](https://arxiv.org/abs/2203.11171)
- [Turpin et al. (2023), "Language Models Don't Always Say What They Think" (arXiv:2305.04388)](https://arxiv.org/abs/2305.04388)
- [Zhang et al. (2023), "H2O: Heavy-Hitter Oracle for Efficient Generative Inference of Large Language Models" (arXiv:2306.14048)](https://arxiv.org/abs/2306.14048)
- [Sharma et al. (2023), "Towards Understanding Sycophancy in Language Models" (arXiv:2310.13548) — Anthropic共著、RLHFがsycophancyを増加させるという決定的な実証](https://arxiv.org/abs/2310.13548)

**学術論文 — Mitigationパターン**
- [Yao et al. (2023), "ReAct: Synergizing Reasoning and Acting in Language Models" (arXiv:2210.03629)](https://arxiv.org/abs/2210.03629)
- [Madaan et al. (2023), "Self-Refine: Iterative Refinement with Self-Feedback" (arXiv:2303.17651)](https://arxiv.org/abs/2303.17651)
- [Yao et al. (2024), "Tree of Thoughts: Deliberate Problem Solving with Large Language Models" (arXiv:2305.10601)](https://arxiv.org/abs/2305.10601)
