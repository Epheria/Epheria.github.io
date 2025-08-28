---
title: AI(ML/DL) 조사 보고서
date: 2024-4-14 10:00:00 +/-TTTT
categories: [ML, Supervised Machine Learning]
tags: [AI, ML, DL, Report]     # TAG names should always be lowercase

toc: true
toc_sticky: true
math: true  
use_math: true
mermaid: true

---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

---


## 목차

> [AI, ML, DL 정리](#ai-ml-dl-정리)      
> [AI 개발 개념, 툴 정리](#ai-개발-개념-툴-정리)     
> [필요한 수학 지식](#필요한-수학-지식)

<br>
<br>

## AI, ML, DL 정리

- AI, ML, DL 이 세 가지 용어 중 가장 넓은 범주를 가진 용어는 인공지능인 AI 입니다.

<br>

![Desktop View](/assets/img/post/ml/ml001.png){: : width="500" .normal }     

<br>

- AI (Artificial Intelligence) 는 크게 다음 범주로 구분됩니다.
1. ANI(인공협소지능) - 약인공지능
2. 일반 인공지능(AGI) - 강인공지능
3. 인공슈퍼지능(ASI) - 실현 불가..하지 않을까요..

- 현재까지 나온 AI 는 전부 ANI 약인공지능입니다. 아이폰의 Siri, Open AI 의 ChatGPT, 자율주행과 같이 각종 자연어 처리, 컴퓨터 비전으로 구현한 인공지능이 이에 해당합니다.

- AGI는 강인공지능으로 인간의 어조와 감정을 해석하거나 통합하는 능력을 가진다고 정의합니다. 인간과 완전 동등한 성능을 발휘한다고 생각하시면 됩니다. AGI 에 대해 수많은 연구자들 과학자들이 연구를 진행하고 있으나 실현 불가능하다는 의견이 주류라고 알고있습니다. 하지만, 엔비디아의 젠슨황이나 OepnAI 의 샘 올트먼 같이 AI 의 권위자들은 대부분 2050년 이전에는 실현이 가능할 것이다라고 보고있습니다.

- ASI 는 지사장님께서 지식과 지능의 차이점에 대해 알고 계시듯이, 인간의 지능과 능력을 초월하는 존재입니다. 이 분야에 대해서도 연구가 이루어지고있습니다.

<br>

#### ML : Machine Learning 기계 학습
#### DL : Deep Learning 심층 학습

- ML,DL 은 여러가지 학습 방법 즉 알고리즘들을 묶어서 구분하는 부모 카테고리라고 생각하면 편합니다.

- 여기서 짚고 넘어가야할 부분은 DL은 ML의 하위 집합인 것입니다.

- ML 과 DL 의 주요 차이점은 각 알고리즘이 학습하는 방식과 데이터 양입니다.

- 우선 ML 알고리즘에 대해 간단히 설명드리면, 다음과 같이 크게 4가지로 구분됩니다.

1. Supervised Learning  지도 학습
2. Unsupervised Learning 비지도 학습
3. Recommender System 추천 시스템
4. Reinforcement Learning  강화 학습

- **Supervised Learning** 은 대표적으로 Regression (회귀),  Classification (분류)가 있고 여기서 Gradient Desecent (경사 하강법) 이 등장합니다. Regression 은 linear regression (선형 회귀), logistic regression (로지스틱 회귀) 등 일반적인 하나의 데이터만 X→Y mapping 처럼 선형적으로 피팅할 것인지, 다양한 변수들을 피팅할 것인지에 대한 구분입니다. 

- 여기서 가장 중요한점은 Supervised Learning은 주어진 label 이 지정된 데이터셋을 입력하여 결과값을 예측한다고 생각하시면 됩니다. 예를 들어 평방미터 → 집값 과 같이 x → y 즉 domain 과 codomain 이 존재하는 함수라고 보면됩니다.

<br>


- **Unsupervised Learning** 은 데이터 입력 x만 있고, 출력 레이블 y 는 제공하지 않고 여기서 알고리즘을 사용하여 데이터에서 구조나 패턴 또는 흥미로운 포인트를 찾습니다. 

- 대표적으로 Clustering Algorithm (클러스터링 알고리즘), Anomaly Detection (예외 항목 탐지), Dimensionality Reduction (차원 축소) 등이 있으며 Clustering Algorithm 은 특정 군집,집단을 그룹화합니다. label 이 지정되지 않은 데이터를 여러 클러스터에 배치하기 때문에 응용 분야에서 많이 사용됩니다. Anomaly Detection 은 비정상적인 이벤트를 탐지하는데 사용됩니다. Dimensionality Reduction 은 큰 데이터 집합을 가져와서 정보를 최대한 적게 손실하면서 더 작은 데이터 집합으로 압축합니다.

<br>

- **Recommender System** 은 유튜브 추천 알고리즘, 구글 검색 혹은 아마존 에서 물건을 구입 시 추천 항목 제안 등과 같이 다양한 분야에서 응용하고 있습니다.

<br>

- **Reinforcement Learning** 은 주변 환경 요소에 상호 작용하여 해당 작업에 대한 피드백(보상, 처벌)을 받아 학습하는 강화 학습입니다. 대표적으로 알파고가 있습니다.

<br>

- DL 은 인간의 뇌를 본따 만든 Deep Neural Network System , DNN (인공 신경망)을 기반으로 신경망을 구현하여 학습을 진행합니다.

- DL 과 신경망은 또 다른데, DL 의 Deep 은 신경망의 layer depth (레이어 깊이)를 의미합니다. 따라서, 입력과 출력을 포함하여 3개 이상의 레이어로 구성된 신경망은 DL 알고리즘으로 간주될 수 있습니다.

- 대부분의 심층 신경망은 피드포워드 방식입니다. 즉, 입력에서 출력으로 한 방향으로만 흐릅니다.
- 하지만, 출력에서 입력으로 반대 방향으로 이동하는 역전파를 통해 모델을 학습 시킬 수도 있습니다. 역전파를 사용하여 각 뉴런과 관련된 오류를 계산하고 특성을 지정할 수 있습니다.


- DL 을 응용하는 사용 사례를 다음과 같이 범주를 나눌 수 있습니다.
        
> Computer Vision (컴퓨터 비전)      
> Voice Recognition (음성 인식)     
> Large Language Model, LLM (자연어 처리)     
> Recommender System (추천 시스템,엔진)     
> Computer Graphics (컴퓨터 그래픽스)     
> Generative AI (생성형 인공지능)

<br>

- Computer Vision은 이미지와 동영상에서 정보와 인사이트를 추출하는 기능입니다. 이미지 or 동영상을 검열하거나 뜬 눈, 안경, 수염과 같은 속성을 인식하고 얼굴을 식별하거나, 심지어 브랜드 로고, 의상, 안전 장비 등 다양한 분야에 대한 연구가 이루어지고 있습니다.

<br>

- Voice Recognition 은 다양한 음성 패턴, 높낮이, 톤, 언어 및 억양에도 불구하고 인간의 음성을 분석할 수 있습니다. 
고객 센터 상담원 지원 및 자동으로 통화 분류, 음성 대화를 실시간으로 문서화, 유튜브 동영상 및 회의 녹화본에 정확한 자막 제공등이 있습니다.

<br>

- Large Language Model, LLM 은 텍스트 데이터와 문서에서 인사이트를 찾고 수집합니다. Open AI 의 Chat GPT와 같은 자동화된 가상 에이전트 혹은 챗봇, 문서 또는 뉴스 기사의 자동 요약등이 있습니다. 

<br>

- Recommender System 은 사용자 활동을 추적하고 개인화된 추천(개인의 패턴을 학습하여 추천 목록 제시)을 개발할 수 있습니다. 다양한 사용장의 행동을 분석하여 사용자가 새로운 제품이나 서비스를 찾는데 도움을 줄 수 있습니다. Netflix, Youtube 등 과 같은 엔터테인먼트 회사들이 딥러닝을 사용하여 개인화된 비디오를 추천합니다.

<br>

- Computer Graphics 는  Image (pixel grid), Volume (voxel grid), Meshes (vertices,edges,faces), Point Clouds, 애니메이션, 물리 시뮬레이션, 렌더링 기술등에서 발생하는 복잡한 문제들을 딥러닝에 접목시켜 해결합니다. 

<br>

- Generative AI 는 텍스트 프롬프트를 통해 이미지를 생성하고 2D 이미지를 기반으로 3D 모델을 만들고 다양한 머테리얼과 텍스쳐들을 생성하기도 하며 최근에는 sora 에서 동영상,영화를 만들기도 합니다. 현재 게임업계 에서 활발하게 응용하고 서비스를 진행하는 분야이기도 합니다. 
- 특히 유니티에서 Material, Mesh 등을 다양한 패턴을 적용시켜 만들어 내고 디자이너가 선택하도록 하거나, InWord 에셋 중에서는 특정 세계관의 스토리나 설명 세력 구도등을 입력하면 다양한 NPC 들이 그에 맞춰 성격과 배경 스토리들을 생성하고 연기하기도 합니다. 또한 스프라이트 이미지 한장을 입력하면 다양한 스프라이트 애니메이션으로 생성해주는 기능도 있습니다.

<br>
<br>


## AI 개발 개념, 툴 정리

<br>

#### 개발 개념

<br>

- MLOPs 는 ML 모델의 개발, 배포 및 유지보수를 간소화하기 위해 ML과 DevOps 관행을 결합한 방법론입니다. MLOps는 DevOps와 다음과 같은 몇 가지 주요 특성은 다음과 같습니다.

> CI/CD     
> 자동화     
> 협업     
> 인프라     
> 테스트 및 모니터링     
> 유연성 및 민첩성     

<br>

#### 개발 툴

<br>

- **Python Libararies 파이썬 라이브러리**

- Numpy, Scipy - 주로 데이터 계산을 처리, 행렬 계산 등 (linalg 선형대수 계산)

- Pandas - 데이터 분석 도구

- Matplotlib - 데이터 분석 계산 결과 값인 플롯들을 시각화

- TensorFlow, Keras, PyTorch - 인공지능 라이브러리, 인공신경망 구축, 오차 역전파에 의한 학습 같은 구조 설계들이나 절차들을 편리하게 하기 위해 만든 패키지입니다.

- Jupyter Notebook (주피터 노트북) - 공부용 학습용 실험용으로 널리 쓰입니다. 파이썬을 실행시키는 IDE 라고 생각하셔도 됩니다.

- Google Colab (구글 코랩) - 가장 널리 쓰이기도 하고 구글에서 제공하는 클라우드 기반의 Jupyter Notebook 환경입니다. kaggle 부터 인공지능 대학원까지 널리 쓰이고있습니다. 연구를 위한 엄청 많은 대량의 데이터는 연산속도가 빠른 A-100 과 같은 고급 컴퓨터를 통해 하는 것으로 알고 있지만, 구글 코랩으로도 충분한 결과물을 볼 수 있는걸로 알고있습니다. 

- Sphinx (스핑크스) - 파이썬 기반의 Jupyter Notebook 파일인 ipynb 를 html 파일로 변환하여 웹에 배포가능

<br>
<br>

## 필요한 수학 지식

<br>

수학과 키워드들에 대해 나열했습니다.

- 기본
> Linear Algebra - 선형 대수학 : 행렬과 벡터의 계산, 행렬의 특성과 row reduction (가우시안 소거법), 행렬의 분해 알고리즘들 (LU, QR), 행렬의 Determinant, Diagonalization(대각화), eigenvector 고유 벡터, eigenvalue 고유값, Least Squares Process, Gram-Schimidt, SVD(Singular Value Decomposition)      
>      
> Calculus - 미적분학 : 벡터 미적분, 다변량 미적분, 체인룰, 자코비안, Power Method, 다변량 미적분 테일러 정리, 경사 하강, 회귀 등      
>      
> Probability - 확률론 : 확률 및 확률 분포, 이항 분포, 베르누이 분포, 확률 밀도 함수, 정규 분포, 카이제곱 분포, 베이즈 정리, 중앙값, 기대값, 분산, 표준 편차, 가우시안 합, 커널 밀도, 가우스 분포, 포아송 분포      
>     
> Statistics - 통계학 : 샘플링, 중심 극한 정리, MLE, 베이지안 통계, 신뢰 구간, p-value, t-분배 등...

<br>

- 심화 

> Mathematical Statistics - 수리 통계학     
> Mathematical Analysis - 해석학
