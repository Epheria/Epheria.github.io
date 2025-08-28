---
title: Jenkins Build Pipeline
date: 2024-10-22 10:00:00 +/-TTTT
categories: [Unity, Build]
tags: [Unity, Build, Jenkins, Groovy, Pipeline]     # TAG names should always be lowercase

toc: true
toc_sticky: true
math: true  
use_math: true
mermaid: true
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

---

# Jenkins 플러그인 리스트

<details>
<summary>토글 접기/펼치기</summary>
<div markdown="1">

| **플러그인 이름** | **설명** |
|-------------------|-----------|
| [Active Choices Plug-in](https://plugins.jenkins.io/uno-choice) | 작업에 동적 매개변수를 제공하며 HTML 요소를 렌더링합니다. |
| [Ant Plugin](https://plugins.jenkins.io/ant) | Jenkins에서 Apache Ant 빌드를 실행합니다. |
| [Apache HttpComponents Client 4.x API Plugin](https://plugins.jenkins.io/apache-httpcomponents-client-4-api) | HTTP 클라이언트 라이브러리를 제공합니다. |
| [App Center](https://plugins.jenkins.io/appcenter) | 앱을 App Center에 업로드합니다. |
| [ASM API](https://plugins.jenkins.io/asm-api) | ASM 라이브러리를 제공합니다. |
| [Bootstrap 5 API Plugin](https://plugins.jenkins.io/bootstrap5-api) | Jenkins 플러그인에 Bootstrap 5를 제공합니다. |
| [bouncycastle API Plugin](https://plugins.jenkins.io/bouncycastle-api) | 암호화 작업을 위한 Bouncy Castle API를 제공합니다. |
| [Branch API Plugin](https://plugins.jenkins.io/branch-api) | 브랜치 기반 프로젝트를 지원하는 API를 제공합니다. |
| [Build Timeout](https://plugins.jenkins.io/build-timeout) | 빌드가 지정된 시간 이상 실행되면 자동으로 종료합니다. |
| [Build Timestamp Plugin](https://plugins.jenkins.io/build-timestamp) | 빌드에 타임스탬프를 추가합니다. |
| [Build Trigger Badge Plugin](https://plugins.jenkins.io/buildtriggerbadge) | 빌드 원인을 나타내는 아이콘을 표시합니다. |
| [build user vars plugin](https://plugins.jenkins.io/build-user-vars-plugin) | Jenkins 사용자 정보를 빌드 변수로 설정합니다. |
| [Caffeine API Plugin](https://plugins.jenkins.io/caffeine-api) | Jenkins 플러그인에 Caffeine API를 제공합니다. |
| [Checks API plugin](https://plugins.jenkins.io/checks-api) | SCM 플랫폼에 체크 상태를 게시하는 API를 제공합니다. |
| [Command Agent Launcher Plugin](https://plugins.jenkins.io/command-launcher) | 에이전트를 명령어로 실행할 수 있도록 합니다. |
| [Commons Compress API](https://plugins.jenkins.io/commons-compress-api) | 압축 작업을 위한 라이브러리를 제공합니다. |
| [commons-lang3 v3.x Jenkins API Plugin](https://plugins.jenkins.io/commons-lang3-api) | Apache Commons Lang 라이브러리를 제공합니다. |
| [commons-text API Plugin](https://plugins.jenkins.io/commons-text-api) | 텍스트 조작을 위한 라이브러리를 제공합니다. |
| [Copy Artifact Plugin](https://plugins.jenkins.io/copyartifact) | 다른 프로젝트의 아티팩트를 복사합니다. |
| [Credentials](https://plugins.jenkins.io/credentials) | Jenkins에서 자격 증명을 저장하고 관리합니다. |
| [Credentials Binding Plugin](https://plugins.jenkins.io/credentials-binding) | 자격 증명을 환경 변수에 바인딩합니다. |
| [Dark Theme](https://plugins.jenkins.io/dark-theme) | Jenkins에 다크 테마를 추가합니다. |
| [Dashboard View](https://plugins.jenkins.io/dashboard-view) | 작업 정보를 표시하는 대시보드를 제공합니다. |
| [DataTables.net API Plugin](https://plugins.jenkins.io/data-tables-api) | 테이블을 동적으로 렌더링합니다. |
| [Display URL API](https://plugins.jenkins.io/display-url-api) | 알림에 사용할 대체 URL을 제공합니다. |
| [Durable Task Plugin](https://plugins.jenkins.io/durable-task) | Jenkins 외부에서 실행되는 작업을 모니터링합니다. |
| [ECharts API](https://plugins.jenkins.io/echarts-api) | 데이터 시각화를 위한 도구를 제공합니다. |
| [EDDSA API Plugin](https://plugins.jenkins.io/eddsa-api) | EdDSA 서명을 지원하는 API를 제공합니다. |
| [Email Extension Plugin](https://plugins.jenkins.io/email-ext) | 이메일 알림을 확장하고 구성할 수 있습니다. |
| [Extended Choice Parameter Plugin](https://plugins.jenkins.io/extended-choice-parameter) | 선택 매개변수를 확장합니다. |
| [External Monitor Job Type Plugin](https://plugins.jenkins.io/external-monitor-job) | 외부에서 실행된 작업의 결과를 모니터링합니다. |
| [Folders Plugin](https://plugins.jenkins.io/cloudbees-folder) | 작업을 정리하기 위한 폴더를 만듭니다. |
| [Font Awesome API Plugin](https://plugins.jenkins.io/font-awesome-api) | Font Awesome 아이콘을 제공합니다. |
| [Git client plugin](https://plugins.jenkins.io/git-client) | Git 지원을 위한 유틸리티 플러그인입니다. |
| [Git Parameter Plug-In](https://plugins.jenkins.io/git-parameter) | 브랜치, 태그 또는 리비전을 선택할 수 있게 합니다. |
| [Git plugin](https://plugins.jenkins.io/git) | Git을 Jenkins와 통합합니다. |
| [Git Push Plugin](https://plugins.jenkins.io/git-push) | 빌드 후 Git 푸시 작업을 수행합니다. |
| [Git server Plugin](https://plugins.jenkins.io/git-server) | Jenkins를 Git 서버로 사용하도록 설정합니다. |
| [GitHub API Plugin](https://plugins.jenkins.io/github-api) | GitHub API를 제공합니다. |
| [GitHub Branch Source](https://plugins.jenkins.io/github-branch-source) | GitHub의 멀티브랜치 프로젝트를 지원합니다. |
| [GitHub plugin](https://plugins.jenkins.io/github) | GitHub와 Jenkins를 통합합니다. |
| [GitLab](https://plugins.jenkins.io/gitlab-plugin) | GitLab과 Jenkins를 통합합니다. |
| [GitLab API Plugin](https://plugins.jenkins.io/gitlab-api) | GitLab API를 제공합니다. |
| [GitLab Authentication](https://plugins.jenkins.io/gitlab-oauth) | GitLab OAuth를 통한 인증을 지원합니다. |
| [Google OAuth Credentials plugin](https://plugins.jenkins.io/google-oauth-plugin) | Google 서비스 계정 인증을 제공합니다. |
| [Google Play Android Publisher Plugin](https://plugins.jenkins.io/google-play-android-publisher) | Android 앱을 Google Play에 업로드합니다. |
| [Gradle](https://plugins.jenkins.io/gradle) | Gradle 빌드를 실행할 수 있습니다. |
| [Gson API](https://plugins.jenkins.io/gson-api) | Gson 라이브러리를 제공합니다. |
| [Instance Identity](https://plugins.jenkins.io/instance-identity) | Jenkins 간 인증을 위한 RSA 키 쌍을 유지합니다. |
| [Ionicons API](https://plugins.jenkins.io/ionicons-api) | Ionicons 아이콘을 제공합니다. |
| [Jackson 2 API Plugin](https://plugins.jenkins.io/jackson2-api) | JSON 처리를 위한 Jackson 2 API를 제공합니다. |
| [Jakarta Activation API](https://plugins.jenkins.io/jakarta-activation-api) | Jakarta Activation API를 제공합니다. |
| [Jakarta Mail API](https://plugins.jenkins.io/jakarta-mail-api) | Jakarta Mail API를 제공합니다. |
| [Java JSON Web Token (JJWT) Plugin](https://plugins.jenkins.io/jjwt-api) | JWT 토큰 처리를 지원합니다. |
| [JavaBeans Activation Framework (JAF) API](https://plugins.jenkins.io/javax-activation-api) | JAF API를 제공합니다. |
| [JavaMail API](https://plugins.jenkins.io/javax-mail-api) | JavaMail API를 제공합니다. |
| [JavaScript GUI Lib: ACE Editor bundle plugin](https://plugins.jenkins.io/ace-editor) | ACE 에디터 번들을 제공합니다. |
| [JavaScript GUI Lib: Handlebars bundle plugin](https://plugins.jenkins.io/handlebars) | Handlebars.js를 제공합니다. |
| [JavaScript GUI Lib: Moment.js bundle plugin](https://plugins.jenkins.io/momentjs) | Moment.js를 제공합니다. |
| [JAXB plugin](https://plugins.jenkins.io/jaxb) | JAXB 패키징을 제공합니다. |
| [Jersey 2 API](https://plugins.jenkins.io/jersey2-api) | JAX-RS와 Jersey API를 제공합니다. |
| [Job Configuration History Plugin](https://plugins.jenkins.io/jobConfigHistory) | 작업 설정 변경 이력을 저장합니다. |
| [Joda Time API](https://plugins.jenkins.io/joda-time-api) | Joda Time API를 제공합니다. |
| [jQuery plugin](https://plugins.jenkins.io/jquery) | 안정적인 jQuery 버전을 제공합니다. |
| [JQuery3 API Plugin](https://plugins.jenkins.io/jquery3-api) | jQuery 3.x 버전을 제공합니다. |
| [JSch dependency plugin](https://plugins.jenkins.io/jsch) | JSch 라이브러리를 사용한 SSH 인증을 지원합니다. |
| [JSON Api](https://plugins.jenkins.io/json-api) | JSON API를 제공합니다. |
| [JSON Path API](https://plugins.jenkins.io/json-path-api) | JSON Path API를 제공합니다. |
| [JUnit](https://plugins.jenkins.io/junit) | JUnit 테스트 결과를 게시합니다. |
| [LDAP Plugin](https://plugins.jenkins.io/ldap) | LDAP 인증을 지원합니다. |
| [List Git Branches Parameter PlugIn](https://plugins.jenkins.io/list-git-branches-parameter) | Git 브랜치 또는 태그를 선택할 수 있는 매개변수를 제공합니다. |
| [Locale plugin](https://plugins.jenkins.io/locale) | Jenkins의 언어 설정을 제어합니다. |
| [Lockable Resources plugin](https://plugins.jenkins.io/lockable-resources) | 외부 리소스를 빌드 간에 잠글 수 있게 합니다. |
| [Login Theme Plugin](https://plugins.jenkins.io/login-theme) | 로그인 페이지의 테마를 사용자 정의합니다. |
| [Mailer Plugin](https://plugins.jenkins.io/mailer) | 이메일 알림을 구성합니다. |
| [Matrix Authorization Strategy Plugin](https://plugins.jenkins.io/matrix-auth) | 역할 기반의 매트릭스 권한 부여 전략을 제공합니다. |
| [Matrix Project](https://plugins.jenkins.io/matrix-project) | 멀티 구성 프로젝트를 생성할 수 있습니다. |
| [Metrics Plugin](https://plugins.jenkins.io/metrics) | 시스템 및 빌드 성능 메트릭을 제공합니다. |
| [Mina SSHD API :: Common](https://plugins.jenkins.io/mina-sshd-api-common) | Apache Mina SSHD의 공통 모듈을 제공합니다. |
| [Mina SSHD API :: Core](https://plugins.jenkins.io/mina-sshd-api-core) | Apache Mina SSHD의 핵심 모듈을 제공합니다. |
| [Naginator](https://plugins.jenkins.io/naginator) | 실패한 빌드를 자동으로 재시도합니다. |
| [OAuth Credentials plugin](https://plugins.jenkins.io/oauth-credentials) | OAuth 자격 증명 인터페이스를 제공합니다. |
| [OkHttp Plugin](https://plugins.jenkins.io/okhttp-api) | OkHttp 라이브러리를 제공합니다. |
| [Oracle Java SE Development Kit Installer Plugin](https://plugins.jenkins.io/jdk-tool) | Oracle JDK를 설치할 수 있도록 지원합니다. |
| [OWASP Markup Formatter Plugin](https://plugins.jenkins.io/antisamy-markup-formatter) | 안전한 HTML 마크업을 허용합니다. |
| [PAM Authentication plugin](https://plugins.jenkins.io/pam-auth) | Unix PAM 인증을 추가합니다. |
| [Parameterized Trigger plugin](https://plugins.jenkins.io/parameterized-trigger) | 빌드가 완료된 후 다른 빌드를 트리거합니다. |
| [Pipeline Configuration History Plugin](https://plugins.jenkins.io/pipeline-config-history) | 파이프라인 설정 변경 내역을 저장합니다. |
| [Pipeline Graph Analysis Plugin](https://plugins.jenkins.io/pipeline-graph-analysis) | 파이프라인 분석 REST API를 제공합니다. |
| [Pipeline Graph View Plugin](https://plugins.jenkins.io/pipeline-graph-view) | 파이프라인 그래프를 시각화합니다. |
| [Pipeline REST API Plugin](https://plugins.jenkins.io/pipeline-rest-api) | 파이프라인 데이터에 접근할 수 있는 REST API를 제공합니다. |
| [Pipeline: API](https://plugins.jenkins.io/workflow-api) | 파이프라인 API를 정의합니다. |
| [Pipeline: Basic Steps](https://plugins.jenkins.io/workflow-basic-steps) | 파이프라인에서 자주 사용되는 기본 단계를 제공합니다. |
| [Pipeline: Build Step](https://plugins.jenkins.io/pipeline-build-step) | 다른 작업을 빌드할 수 있는 단계를 추가합니다. |
| [Pipeline: Declarative](https://plugins.jenkins.io/pipeline-model-definition) | 선언형 파이프라인을 제공합니다. |
| [Pipeline: Declarative Extension Points API](https://plugins.jenkins.io/pipeline-model-extensions) | 선언형 파이프라인 확장 포인트 API를 제공합니다. |
| [Pipeline: GitHub Groovy Libraries](https://plugins.jenkins.io/pipeline-github-lib) | GitHub에서 Groovy 라이브러리를 로드합니다. |
| [Pipeline: Input Step](https://plugins.jenkins.io/pipeline-input-step) | 사용자 입력을 대기하는 단계를 추가합니다. |
| [Pipeline: Job](https://plugins.jenkins.io/workflow-job) | 파이프라인 작업 유형을 정의합니다. |
| [Pipeline: Milestone Step](https://plugins.jenkins.io/pipeline-milestone-step) | 마일스톤 단계를 제공합니다. |
| [Pipeline: Model API](https://plugins.jenkins.io/pipeline-model-api) | 선언형 파이프라인 모델 API입니다. |
| [Pipeline: Multibranch](https://plugins.jenkins.io/workflow-multibranch) | 멀티 브랜치 파이프라인을 지원합니다. |
| [Pipeline: Nodes and Processes](https://plugins.jenkins.io/workflow-durable-task-step) | 노드와 외부 프로세스를 관리합니다. |
| [Pipeline: SCM Step](https://plugins.jenkins.io/workflow-scm-step) | 소스 제어에서 소스를 가져오는 단계를 추가합니다. |
| [Pipeline: Stage Step](https://plugins.jenkins.io/pipeline-stage-step) | 파이프라인 단계 구분을 제공합니다. |
| [Pipeline: Stage Tags Metadata](https://plugins.jenkins.io/pipeline-stage-tags-metadata) | 파이프라인 단계 태그 메타데이터를 지원합니다. |
| [Pipeline: Stage View Plugin](https://plugins.jenkins.io/pipeline-stage-view) | 파이프라인 단계 뷰를 제공합니다. |
| [Pipeline: Step API](https://plugins.jenkins.io/workflow-step-api) | 비동기 빌드 단계 API입니다. |
| [Pipeline: Supporting APIs](https://plugins.jenkins.io/workflow-support) | 파이프라인 플러그인에 필요한 공용 유틸리티를 제공합니다. |
| [Plain Credentials Plugin](https://plugins.jenkins.io/plain-credentials) | 단순한 문자열과 파일을 자격 증명으로 사용합니다. |
| [Plugin Utilities API Plugin](https://plugins.jenkins.io/plugin-util-api) | 플러그인 개발을 가속화하기 위한 유틸리티를 제공합니다. |
| [Popper.js 2 API Plugin](https://plugins.jenkins.io/popper2-api) | Popper.js를 사용해 툴팁과 팝업을 배치합니다. |
| [Popper.js API Plugin](https://plugins.jenkins.io/popper-api) | Popper.js를 Jenkins 플러그인에 제공합니다. |
| [Pre SCM BuildStep Plugin](https://plugins.jenkins.io/preSCMbuildstep) | 소스 제어 작업 이전에 빌드 단계를 실행할 수 있습니다. |
| [Rebuilder](https://plugins.jenkins.io/rebuild) | 동일한 매개변수를 사용해 빌드를 다시 실행합니다. |
| [Resource Disposer Plugin](https://plugins.jenkins.io/resource-disposer) | 삭제가 지연되는 자원을 비동기적으로 처리합니다. |
| [Role-based Authorization Strategy](https://plugins.jenkins.io/role-strategy) | 역할 기반 권한 부여 전략을 제공합니다. |
| [SCM API Plugin](https://plugins.jenkins.io/scm-api) | SCM 시스템과의 상호작용을 위한 API를 제공합니다. |
| [Script Security](https://plugins.jenkins.io/script-security) | Jenkins에서 실행할 스크립트의 보안을 관리합니다. |
| [Simple Theme Plugin](https://plugins.jenkins.io/simple-theme-plugin) | CSS와 JavaScript를 사용해 Jenkins의 테마를 커스터마이즈합니다. |
| [Slack Notification Plugin](https://plugins.jenkins.io/slack) | Slack과 통합해 빌드 상태와 메시지를 알립니다. |
| [SnakeYAML API](https://plugins.jenkins.io/snakeyaml-api) | YAML 파싱을 위한 라이브러리를 제공합니다. |
| [SSH Build Agents plugin](https://plugins.jenkins.io/ssh-slaves) | SSH를 통해 에이전트를 실행할 수 있습니다. |
| [SSH Credentials Plugin](https://plugins.jenkins.io/ssh-credentials) | SSH 자격 증명을 저장하고 관리합니다. |
| [SSH server](https://plugins.jenkins.io/sshd) | Jenkins를 SSH 서버로 사용해 CLI 명령을 제공합니다. |
| [Structs Plugin](https://plugins.jenkins.io/structs) | DSL 플러그인을 위한 데이터 구조를 제공합니다. |
| [Theme Manager](https://plugins.jenkins.io/theme-manager) | 사용자 및 전역 테마를 추가할 수 있는 확장 포인트를 제공합니다. |
| [ThinBackup](https://plugins.jenkins.io/thinBackup) | 글로벌 및 작업별 설정 파일을 백업합니다. |
| [Throttle Concurrent Builds Plug-in](https://plugins.jenkins.io/throttle-concurrents) | 빌드 동시 실행을 제한할 수 있습니다. |
| [Timestamper](https://plugins.jenkins.io/timestamper) | 콘솔 출력에 타임스탬프를 추가합니다. |
| [Token Macro Plugin](https://plugins.jenkins.io/token-macro) | 재사용 가능한 매크로 확장 기능을 추가합니다. |
| [Trilead API Plugin](https://plugins.jenkins.io/trilead-api) | Trilead SSH 라이브러리를 제공합니다. |
| [Unity3d plugin](https://plugins.jenkins.io/unity3d-plugin) | Unity 3D 에디터 빌드를 실행할 수 있습니다. |
| [Variant Plugin](https://plugins.jenkins.io/variant) | 여러 모드에 맞게 플러그인의 동작을 변경합니다. |
| [View Job Filters](https://plugins.jenkins.io/view-job-filters) | 작업 필터를 사용해 스마트 뷰를 만듭니다. |
| [Workspace Cleanup](https://plugins.jenkins.io/ws-cleanup) | 프로젝트의 작업 공간을 정리합니다. |
| [Xcode integration](https://plugins.jenkins.io/xcode-plugin) | Xcode 프로젝트를 빌드하고 .ipa 파일을 패키징합니다. |

</div>
</details>