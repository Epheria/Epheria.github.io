---
name: excalidraw-diagram
description: Excalidraw MCP를 사용하여 다이어그램을 생성한다. Canvas Server 자동 실행, 손글씨 스타일 다이어그램 생성, 스크린샷 확인, 작업 중인 포스트의 이미지 디렉토리에 자동 번호 매겨 PNG 저장까지 전 과정을 자동화한다. 블로그 포스트용 다이어그램이나 아키텍처 도식이 필요할 때 사용한다.
argument-hint: <diagram-description> [--post <post-slug>] [--lang ko|en|ja] [--no-save]
allowed-tools: Bash, Read, Edit, Glob, Grep, mcp__excalidraw__*
---

# Excalidraw Diagram Generator

Excalidraw MCP를 사용하여 손글씨 스타일의 다이어그램을 생성하고, 작업 중인 포스트의 이미지 디렉토리에 자동 저장하는 스킬이다.

## 워크플로우

### Phase 1: Canvas Server 연결

다이어그램 작업 전 반드시 Canvas Server 상태를 확인한다.

```bash
# 1. 헬스체크
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/ 2>/dev/null)

# 2. 서버 미실행 시 시작
if [ "$STATUS" != "200" ]; then
  # 포트 사용 중이면 기존 프로세스 확인
  PID=$(lsof -t -i:3000 2>/dev/null)
  [ -n "$PID" ] && kill $PID 2>/dev/null && sleep 1
  cd /Users/son_sehyup/mcp_excalidraw && PORT=3000 node dist/server.js &
  sleep 2
fi

# 3. 프론트엔드 404면 빌드 후 재시작
BODY=$(curl -s http://localhost:3000/ 2>/dev/null)
if echo "$BODY" | grep -q "Frontend not found"; then
  cd /Users/son_sehyup/mcp_excalidraw && npm run build
  kill $(lsof -t -i:3000) 2>/dev/null && sleep 1
  PORT=3000 node dist/server.js &
  sleep 2
fi
```

사용자에게 `http://localhost:3000`을 브라우저에서 열도록 안내한다.

### Phase 2: 저장 경로 결정

**자동 감지 로직:**

1. `--post` 옵션이 있으면 해당 slug 사용
2. 없으면 현재 대화 컨텍스트에서 작업 중인 포스트 감지:
   - IDE에서 열린 파일의 categories 확인
   - 최근 편집한 `_posts/` 파일의 categories 확인
3. 카테고리에서 이미지 디렉토리 결정

```bash
# 카테고리 → 이미지 디렉토리 매핑
# categories: [AI, CS] → assets/img/post/cs/
# categories: [Unity, build] → assets/img/post/unity/
IMG_DIR="assets/img/post/${CATEGORY_LOWER}/"

# 자동 번호 매기기: 기존 excalidraw-*.png 파일 중 최대 번호 + 1
EXISTING=$(ls ${IMG_DIR}excalidraw-*.png 2>/dev/null | sort -V | tail -1)
if [ -z "$EXISTING" ]; then
  NEXT_NUM="01"
else
  LAST_NUM=$(echo "$EXISTING" | grep -o '[0-9]*' | tail -1)
  NEXT_NUM=$(printf "%02d" $((LAST_NUM + 1)))
fi

# 최종 파일명: excalidraw-{번호}-{설명}.png
# 예: excalidraw-01-load-factor.png
FILENAME="excalidraw-${NEXT_NUM}-${SLUG}.png"
OUTPUT_PATH="${IMG_DIR}${FILENAME}"
```

**파일 네이밍 규칙:**
- 패턴: `excalidraw-{번호}-{짧은설명}.png`
- 번호: 2자리 zero-padded (01, 02, 03...)
- 설명: 영문 소문자 + 하이픈, 3단어 이내
- 예시: `excalidraw-01-load-factor.png`, `excalidraw-02-bfs-vs-dfs.png`

### Phase 3: 다이어그램 설계

사용자의 설명(`$ARGUMENTS`)을 분석하여 다이어그램 구조를 설계한다.

**설계 원칙:**
1. `read_diagram_guide`를 먼저 호출하여 최신 디자인 가이드 확인
2. Mermaid 변환(`create_from_mermaid`) 사용 금지 — 한글 텍스트 깨짐 발생
3. 반드시 `batch_create_elements`로 네이티브 요소 직접 생성

### Phase 4: 다이어그램 생성

**필수 스타일 규칙:**

| 속성 | 값 | 이유 |
|------|-----|------|
| `fontFamily` | `1` (Virgil) | 영문/숫자 필기체 (CJK는 폴백) |
| `roughness` | `1~2` | 손그림 테두리 |
| `roughness` | `0` | 점선/대시 라인에만 |
| `strokeWidth` | `2` | 기본, 강조는 `3` |
| `opacity` | `35~50` | Zone 배경에만 |

**색상 팔레트 (Excalidraw 공식):**

| 용도 | Stroke | Fill (파스텔) |
|------|--------|--------------|
| 성공/안전 | #2f9e44 | #b2f2bb |
| 주요 액션 | #1971c2 | #a5d8ff |
| 비동기/이벤트 | #e8590c | #ffd8a8 |
| 에러/위험 | #e03131 | #ffc9c9 |
| 보조/주석 | #868e96 | #e9ecef |
| 기본 텍스트 | #1e1e1e | — |

**사이징 규칙:**
- 최소 도형: width >= 120px, height >= 60px
- 폰트: 제목 >= 20, 본문 >= 16, 라벨 >= 14
- 도형 간격: 40~80px
- 화살표 최소 길이: 80px

**레이아웃:**
- **가로(LR) 레이아웃 우선** — 세로보다 가독성 좋음
- Zone 배경: 큰 rectangle + 낮은 opacity + roughness: 2
- Zone 라벨: 좌상단 작은 폰트(16px)
- 화살표: 반드시 `startElementId`/`endElementId` 바인딩

**생성 순서:**
1. `clear_canvas` — 캔버스 초기화
2. 배경 Zone (큰 사각형, 연한 fill, 낮은 opacity)
3. 주요 노드 (도형 + 텍스트, id 부여)
4. 화살표 (바인딩 ID로 연결)
5. 주석 (독립 텍스트 — 제목, 설명, 각주)

### Phase 5: 스타일 린트 (자동)

다이어그램 생성 후, 모든 텍스트 요소의 fontFamily를 일괄 검사/수정한다.
**필수 실행 이유**: `batch_create_elements`로 fontFamily: 1 지정해도, 프론트엔드 sync 시 한글 텍스트를 fontFamily: 5로 자동 교체함. `update_element`로 강제 복원하면 Virgil이 유지됨.

```
# 1. 모든 텍스트 요소 조회
texts = query_elements(type="text")

# 2. fontFamily != 1 인 요소만 필터
non_virgil = [t for t in texts if t.fontFamily != 1]

# 3. 일괄 업데이트 (병렬 호출)
for t in non_virgil:
    update_element(id=t.id, fontFamily=1)

# 4. 린트 결과 보고
# "✅ 린트 완료: {N}개 텍스트 → fontFamily: 1 (Virgil) 변환"
```

**린트 대상:** `fontFamily` 값 매핑
| 값 | 이름 | 판정 |
|----|------|------|
| 1 | Virgil (필기체) | OK — 영문/숫자에 필기체 적용 |
| 2 | Helvetica | 변환 |
| 3 | Cascadia (코드) | 유지 (코드 블록일 때만) |
| 5 | Excalifont | 변환 |
| 기타 | — | 변환 |

> **CJK 린트 필수**: 프론트엔드가 한글 텍스트의 fontFamily를 1→5로 자동 교체하므로,
> `batch_create_elements` 후 반드시 `query_elements` + `update_element`로 fontFamily: 1 강제 복원해야 함.
> 복원 후에는 Virgil이 유지되며, 브라우저에서 수동 변경한 것과 동일한 결과.

### Phase 6: 확인 및 조정

1. `get_canvas_screenshot`으로 결과 확인
2. 텍스트 겹침, 간격 부족, 화살표 끊김 등 확인
3. 문제 있으면 `update_element` 또는 `delete_element`로 수정
4. `align_elements`, `distribute_elements`로 정렬

### Phase 7: 이미지 저장 (기본 동작)

`--no-save` 가 없으면 자동으로 이미지를 저장한다.

```bash
# PNG로 포스트 이미지 디렉토리에 저장
mcp__excalidraw__export_to_image(format="png", filePath=OUTPUT_PATH)

# 저장 결과 확인
ls -lh $OUTPUT_PATH
```

**저장 후 사용자에게 보고:**
```
✅ 다이어그램 저장 완료
📁 경로: assets/img/post/cs/excalidraw-01-load-factor.png
📐 크기: 83KB
🔗 포스트에서 사용: ![설명](/assets/img/post/cs/excalidraw-01-load-factor.png)
```

### Phase 8: 다국어 (선택)

`--lang` 옵션으로 다국어 버전 생성 시:
- 같은 레이아웃과 색상을 유지하고 텍스트만 번역
- `clear_canvas` 후 번역된 텍스트로 동일 구조 재생성
- 각 언어별 파일명에 접미사 추가: `excalidraw-01-load-factor-en.png`, `-ja.png`
- 각 언어별로 스크린샷 확인 후 저장

```bash
# 다국어 파일 네이밍
# ko (기본): excalidraw-01-load-factor.png
# en:         excalidraw-01-load-factor-en.png
# ja:         excalidraw-01-load-factor-ja.png
```

### Phase 9: 포스트에 이미지 삽입 안내

저장 완료 후, 포스트 마크다운에서 사용할 수 있는 코드를 제안한다:

```markdown
<!-- 단일 이미지 -->
![로드 팩터별 Linear Probing 성능 변화](/assets/img/post/cs/excalidraw-01-load-factor.png)

<!-- 다국어 이미지 (polyglot 대응) -->
<!-- ko 포스트 → 기본 파일 사용 -->
![설명](/assets/img/post/cs/excalidraw-01-load-factor.png)
<!-- en 포스트 → -en 파일 사용 -->
![Description](/assets/img/post/cs/excalidraw-01-load-factor-en.png)
```

## 안티패턴 (반드시 피할 것)

1. `create_from_mermaid` 한글 사용 — 텍스트 깨짐
2. `fontFamily: 2` (Helvetica) — Excalidraw 느낌 없음
3. `roughness: 0` 전체 적용 — 딱딱한 느낌
4. 색상 4개 초과 — 산만해짐
5. 화살표 수동 좌표 — 바인딩 안 하면 도형 이동 시 끊김
6. 텍스트 `label` 속성 — export 시 렌더링 안 됨
7. 이미지 저장 없이 캔버스만 생성 — 서버 재시작 시 소실

## 사용 예시

```
# 기본: 현재 작업 중인 포스트 디렉토리에 자동 저장
/excalidraw-diagram "해시 테이블 로드 팩터별 성능 변화"

# 포스트 지정 + 다국어
/excalidraw-diagram "BFS vs DFS 비교" --post HashTable --lang ko,en,ja

# 저장 없이 캔버스에만 표시
/excalidraw-diagram "게임 아키텍처" --no-save

# 특정 포스트 이미지 디렉토리에 저장
/excalidraw-diagram "메모리 레이아웃" --post ArrayAndLinkedList
```
