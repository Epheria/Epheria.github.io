---
name: excalidraw-diagram
description: Excalidraw MCP를 사용하여 손글씨 스타일 다이어그램을 생성하고 블로그 포스트 이미지 디렉토리에 자동 저장한다. 다이어그램, 아키텍처 도식, 플로우차트, 시퀀스 다이어그램, 비교표 등 시각 자료가 필요할 때 사용한다. 기존 다이어그램을 편집하거나 수정할 때도 이 스킬을 사용한다. "그림 그려줘", "도식으로 설명해줘", "diagram", "flowchart", "architecture diagram", "다이어그램 수정", "이미지 편집", "그림 수정해줘", "edit diagram", "번역해줘" 같은 요청에도 이 스킬을 사용할 것.
argument-hint: <diagram-description> [--post <post-slug>] [--lang ko|en|ja] [--no-save] [--edit <filename>]
allowed-tools: Bash, Read, Edit, Glob, Grep, mcp__excalidraw__*
---

# Excalidraw Diagram Generator & Editor

Excalidraw MCP로 손글씨 스타일 다이어그램을 생성/편집하고, 블로그 포스트 이미지 디렉토리에 자동 저장한다.

## 모드 선택

이 스킬은 두 가지 모드를 지원한다:

| 모드 | 사용 시점 | 트리거 |
|------|----------|--------|
| **Create Mode** | 새 다이어그램을 처음부터 생성 | 기본 동작 |
| **Edit Mode** | 기존 다이어그램을 수정/번역 | `--edit` 옵션 또는 "수정", "편집", "edit" 키워드 |

사용자 요청에 "수정", "편집", "고쳐", "edit", "modify", "update" 등의 키워드가 있거나 기존 이미지 파일명을 언급하면 **Edit Mode**로 진입한다.

---

# Create Mode (새 다이어그램 생성)

## 워크플로우 요약

| Phase | 내용 | 참조 |
|-------|------|------|
| 1 | Canvas Server 연결 | 아래 |
| 2 | 저장 경로 결정 | 아래 |
| 3 | 다이어그램 설계 | `references/design-guide.md` |
| 4 | 다이어그램 생성 | `references/design-guide.md` |
| 5-6 | 품질 검사 (린트 + 겹침) | `references/quality-checks.md` |
| 7 | 확인 및 조정 | 아래 |
| 8 | 이미지 + 씬 파일 저장 | 아래 |
| 9 | 다국어 & 삽입 안내 | 아래 |

---

## Phase 1: Canvas Server 연결

로컬 Canvas Server가 실행 중이어야 브라우저(`localhost:3000`)에서 실시간으로 다이어그램이 그려지는 모습을 볼 수 있다.

```bash
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/ 2>/dev/null)

if [ "$STATUS" != "200" ]; then
  PID=$(lsof -t -i:3000 2>/dev/null)
  [ -n "$PID" ] && kill $PID 2>/dev/null && sleep 1
  cd /Users/son_sehyup/mcp_excalidraw && PORT=3000 node dist/server.js &
  sleep 2
fi

# 프론트엔드 빌드 안 된 경우
BODY=$(curl -s http://localhost:3000/ 2>/dev/null)
if echo "$BODY" | grep -q "Frontend not found"; then
  cd /Users/son_sehyup/mcp_excalidraw && npm run build
  kill $(lsof -t -i:3000) 2>/dev/null && sleep 1
  PORT=3000 node dist/server.js &
  sleep 2
fi
```

사용자에게 `http://localhost:3000`을 브라우저에서 열도록 안내한다.

## Phase 2: 저장 경로 결정

포스트의 카테고리를 기반으로 이미지 저장 경로를 자동 결정한다.

**자동 감지 순서:**
1. `--post` 옵션이 있으면 해당 slug 사용
2. 없으면 현재 대화에서 작업 중인 포스트의 categories 감지
3. 카테고리에서 이미지 디렉토리 결정: `assets/img/post/${CATEGORY_LOWER}/`

**파일 네이밍:**
- 패턴: `excalidraw-{번호}-{짧은설명}.png`
- 번호: 2자리 zero-padded (01, 02, ...) — 기존 파일 중 최대 번호 + 1
- 설명: 영문 소문자 + 하이픈, 3단어 이내
- 예시: `excalidraw-01-load-factor.png`, `excalidraw-02-bfs-vs-dfs.png`

## Phase 3: 다이어그램 설계

사용자의 설명을 분석하여 다이어그램 구조를 설계한다.

1. `read_diagram_guide`를 먼저 호출하여 최신 디자인 가이드를 확인
2. Mermaid 변환(`create_from_mermaid`)은 사용하지 않는다 — 한글 텍스트 깨짐, `<br/>` 리터럴 출력 등 렌더링 문제가 있기 때문
3. `batch_create_elements`로 네이티브 요소를 직접 생성한다

> 색상 팔레트, 사이징 규칙, 레이아웃 패턴은 `references/design-guide.md`를 참조한다.

## Phase 4: 다이어그램 생성

핵심 스타일 규칙 — Excalidraw다운 느낌을 살리는 3가지:

- **fontFamily: 5** (Excalifont) — CJK(한중일) 포함 필기체. Virgil(1)은 구형으로 한글이 시스템 폰트로 폴백됨
- **roughness: 1~2** — 손그림 테두리가 Excalidraw의 핵심 매력. 점선/대시 라인에만 0 사용 (선이 흐트러지면 대시가 안 보이므로)
- **화살표 바인딩** — `startElementId`/`endElementId`로 연결. 수동 좌표로 하면 도형 이동 시 화살표가 끊김

생성 순서: `clear_canvas` → Zone 배경 → 주요 노드 → 화살표 → 주석

> 색상 팔레트, 사이징 상세, 레이아웃 규칙은 `references/design-guide.md`를 참조한다.

## Phase 5-6: 품질 검사

다이어그램 생성 후 fontFamily 린트와 겹침 검사를 수행한다.

- fontFamily: 5로 생성했다면 린트는 불필요 (프론트엔드 기본값이 5이므로 그대로 유지됨)
- 겹침 검사는 바운딩 박스를 비교하여 최소 간격(40px)을 확보

> 상세 절차는 `references/quality-checks.md`를 참조한다.

## Phase 7: 확인 및 조정

1. `get_canvas_screenshot`으로 결과 확인
2. 텍스트 겹침, 간격 부족, 화살표 끊김 등 검토
3. 문제 있으면 `update_element` 또는 `delete_element`로 수정
4. `align_elements`, `distribute_elements`로 정렬

## Phase 8: 이미지 + 씬 파일 저장

`--no-save`가 없으면 PNG와 `.excalidraw` 씬 파일을 함께 저장한다. 씬 파일은 나중에 Edit Mode로 다시 편집할 수 있게 해준다.

```
# 1. PNG 저장
mcp__excalidraw__export_to_image(format="png", filePath=OUTPUT_PATH)

# 2. .excalidraw 씬 파일 저장 (편집용)
SCENE_PATH = OUTPUT_PATH.replace(".png", ".excalidraw")
mcp__excalidraw__export_scene(filePath=SCENE_PATH)
```

저장 후 사용자에게 보고:
```
✅ 다이어그램 저장 완료
📁 이미지: assets/img/post/cs/excalidraw-01-load-factor.png
📁 씬 파일: assets/img/post/cs/excalidraw-01-load-factor.excalidraw (편집용)
📐 크기: 83KB
🔗 포스트에서 사용: ![설명](/assets/img/post/cs/excalidraw-01-load-factor.png)
```

## Phase 9: 다국어 & 삽입 안내

**다국어 (`--lang` 옵션):**
- 같은 레이아웃/색상을 유지하고 텍스트만 번역
- `clear_canvas` 후 번역 텍스트로 동일 구조 재생성
- 파일명 접미사: `-en.png`, `-ja.png`
- 씬 파일도 함께 저장: `-en.excalidraw`, `-ja.excalidraw`

**포스트 삽입 안내:**
```markdown
<!-- 단일 이미지 -->
![로드 팩터별 성능 변화](/assets/img/post/cs/excalidraw-01-load-factor.png)

<!-- 다국어 (polyglot 대응) -->
![Description](/assets/img/post/cs/excalidraw-01-load-factor-en.png)
```

---

# Edit Mode (기존 다이어그램 편집)

기존 Excalidraw 다이어그램을 캔버스에 로드하여 유저가 브라우저에서 직접 수정한 뒤, 수정본을 저장하고 번역본도 자동 생성하는 워크플로우.

## Edit 워크플로우 요약

| Phase | 내용 |
|-------|------|
| E1 | Canvas Server 연결 (Create Mode Phase 1과 동일) |
| E2 | 대상 이미지 선택 |
| E3 | 씬 파일을 캔버스에 로드 |
| E4 | 유저 수동 편집 대기 |
| E5 | 수정본 저장 (PNG + 씬 파일) |
| E6 | 자동 번역 및 번역본 저장 (EN/JA) |

## Phase E1: Canvas Server 연결

Create Mode의 Phase 1과 동일하다. `localhost:3000` 실행을 확인한다.

## Phase E2: 대상 이미지 선택

사용자가 편집할 이미지를 특정한다.

**방법 1: `--edit` 옵션으로 직접 지정**
```
/excalidraw-diagram --edit excalidraw-01-load-factor
```

**방법 2: 대화에서 파일명 또는 설명 언급**
```
"로드 팩터 다이어그램 수정해줘"
"excalidraw-02-bfs-vs-dfs 편집하고 싶어"
```

**방법 3: 목록에서 선택**
사용자가 구체적인 파일을 언급하지 않으면, 해당 카테고리의 excalidraw 이미지 목록을 보여준다:

```bash
# 카테고리 디렉토리에서 excalidraw 이미지 검색
ls assets/img/post/${CATEGORY_LOWER}/excalidraw-*.png
```

목록을 보여주고 사용자에게 선택을 요청한다.

## Phase E3: 씬 파일을 캔버스에 로드

선택한 이미지의 `.excalidraw` 씬 파일을 캔버스에 로드한다.

```
# 씬 파일 경로 결정
SCENE_PATH = IMAGE_PATH.replace(".png", ".excalidraw")

# 씬 파일 존재 여부 확인
if 씬 파일이 존재:
    mcp__excalidraw__import_scene(filePath=SCENE_PATH, mode="replace")
else:
    # 씬 파일이 없는 기존 이미지 → PNG를 보고 캔버스에 재현
    # 1. Read 도구로 PNG 이미지를 시각적으로 확인
    # 2. 이미지의 레이아웃/색상/텍스트를 분석
    # 3. batch_create_elements로 동일한 다이어그램을 캔버스에 재현
    # 4. get_canvas_screenshot으로 원본과 비교 확인
    # 5. 재현 후 .excalidraw 씬 파일도 함께 생성하여 다음 편집에 활용
```

로드 성공 시 사용자에게 안내:
```
✅ 캔버스에 로드 완료!
🌐 http://localhost:3000 에서 브라우저로 확인하세요.
✏️ 자유롭게 수정하신 후, 완료되면 "저장해줘" 또는 "수정 완료"라고 알려주세요.
```

## Phase E4: 유저 수동 편집 대기

사용자가 브라우저(`localhost:3000`)에서 다이어그램을 직접 수정한다.
Claude는 사용자가 다음 키워드로 완료 신호를 보낼 때까지 대기한다:

- "저장해줘", "수정 완료", "완료", "다 됐어", "save", "done"

완료 신호를 받으면 Phase E5로 진행한다.

## Phase E5: 수정본 저장

사용자가 편집을 완료하면, 현재 캔버스 상태를 저장한다.

```
# 1. 편집된 캔버스의 스크린샷으로 결과 확인
mcp__excalidraw__get_canvas_screenshot()

# 2. 사용자에게 확인
"수정된 다이어그램입니다. 이대로 저장할까요?"

# 3. 확인 받으면 저장
mcp__excalidraw__export_to_image(format="png", filePath=ORIGINAL_IMAGE_PATH)
mcp__excalidraw__export_scene(filePath=ORIGINAL_SCENE_PATH)
```

저장 후 보고:
```
✅ 수정본 저장 완료
📁 이미지: assets/img/post/cs/excalidraw-01-load-factor.png (덮어쓰기)
📁 씬 파일: assets/img/post/cs/excalidraw-01-load-factor.excalidraw (덮어쓰기)
```

## Phase E6: 자동 번역 및 번역본 저장

수정본 저장 후, EN/JA 번역본을 자동 생성한다.

### 번역 워크플로우

> **핵심**: `update_element(text=...)`는 `label` 속성으로 들어가서 캔버스에 반영되지 않는다.
> 텍스트 교체는 반드시 **delete_element → batch_create_elements** 방식을 사용할 것.

```
# 1. 현재 한국어 상태를 스냅샷으로 보존
mcp__excalidraw__snapshot_scene(name="edited-ko")

# 2. 캔버스의 모든 텍스트 요소 추출 (id, x, y, fontSize, strokeColor, text 기록)
texts = mcp__excalidraw__query_elements(type="text")

# 3. 텍스트가 없으면 번역 불필요
if len(texts) == 0:
    "텍스트 요소가 없어 번역이 불필요합니다."
    → 종료

# 4. 번역할 텍스트와 그대로 유지할 텍스트 분류
#    - 영어 전용 (Create, Eval, Done! 등): 번역하지 않음
#    - 한국어 포함 텍스트: 번역 대상

# === 영어 버전 ===

# 5. 한국어 텍스트 요소만 삭제 (delete_element)
for each korean_text in texts:
    mcp__excalidraw__delete_element(id=korean_text.id)

# 6. 영어 번역 텍스트로 재생성 (동일 위치/스타일, 새 id)
mcp__excalidraw__batch_create_elements(elements=[
    {id: "xxx-en", type: "text", x: 원본.x, y: 원본.y,
     text: "영어 번역", fontSize: 원본.fontSize,
     fontFamily: 5, strokeColor: 원본.strokeColor}
    ...
])

# 7. 번역 텍스트가 박스보다 긴지 확인 → 박스 width 조정
#    영어는 한국어보다 텍스트가 길어지는 경우가 많다.
#    get_canvas_screenshot으로 시각 확인 후, 넘치면:
#    - 박스(rectangle) width를 늘리거나
#    - fontSize를 줄이거나
#    - 텍스트를 더 짧게 의역

# 8. 영어 버전 저장
mcp__excalidraw__export_to_image(format="png", filePath=EN_IMAGE_PATH)
mcp__excalidraw__export_scene(filePath=EN_SCENE_PATH)

# === 일본어 버전 ===

# 9. 한국어 스냅샷 복원
mcp__excalidraw__restore_snapshot(name="edited-ko")

# 10. 동일하게 삭제 → 일본어 텍스트로 재생성 → 저장
#     (5~8 반복, 일본어 번역 적용)

# 11. 최종적으로 한국어 스냅샷 복원 (캔버스를 원래 상태로)
mcp__excalidraw__restore_snapshot(name="edited-ko")
```

### 번역 시 주의사항

- **텍스트 교체 = 삭제 후 재생성**: `update_element(text=...)`는 `label` 속성으로 들어가 캔버스에 반영되지 않는다. 반드시 `delete_element` → `batch_create_elements`로 교체할 것
- **박스 크기 조정 필수**: 영어 번역은 한국어보다 텍스트가 길어지는 경우가 많다. 번역 후 `get_canvas_screenshot`으로 확인하고, 텍스트가 박스 밖으로 넘치면 `update_element(id=box_id, width=새너비)`로 박스를 넓힌다
- **레이아웃 유지**: 텍스트 위치/색상/fontSize는 원본과 동일하게 유지한다
- **기술 용어 보존**: 코드명, 함수명, 약어 (Create, Eval, SKILL.md 등) 등 번역하지 말아야 할 텍스트는 그대로 유지한다
- **boundElements 텍스트**: 도형 안에 바인딩된 텍스트도 query_elements(type="text")에 포함된다. 빠짐없이 번역할 것

### 번역 완료 보고

```
✅ 번역본 저장 완료

📁 한국어 (원본):
   이미지: assets/img/post/cs/excalidraw-01-load-factor.png
   씬 파일: assets/img/post/cs/excalidraw-01-load-factor.excalidraw

📁 영어:
   이미지: assets/img/post/cs/excalidraw-01-load-factor-en.png
   씬 파일: assets/img/post/cs/excalidraw-01-load-factor-en.excalidraw

📁 일본어:
   이미지: assets/img/post/cs/excalidraw-01-load-factor-ja.png
   씬 파일: assets/img/post/cs/excalidraw-01-load-factor-ja.excalidraw

🔗 포스트에서 사용:
   KO: ![로드 팩터](/assets/img/post/cs/excalidraw-01-load-factor.png)
   EN: ![Load Factor](/assets/img/post/cs/excalidraw-01-load-factor-en.png)
   JA: ![ロードファクター](/assets/img/post/cs/excalidraw-01-load-factor-ja.png)
```

---

# 안티패턴

실제 사용 중 발견된 문제들이다. 각각 이유가 있다:

1. **`create_from_mermaid`로 한글 다이어그램** — 텍스트 깨짐, `<br/>` 리터럴 출력
2. **`fontFamily: 2` (Helvetica)** — Excalidraw의 손글씨 느낌이 사라짐
3. **`roughness: 0` 전체 적용** — 딱딱한 CAD 느낌, Excalidraw답지 않음
4. **색상 4개 초과** — 산만해서 오히려 정보 전달력 감소
5. **화살표 수동 좌표** — 바인딩 없으면 도형 이동 시 화살표가 끊김
6. **`update_element(text=...)`로 텍스트 교체** — `label` 속성으로 들어가서 캔버스에 반영되지 않음. 텍스트 교체는 반드시 `delete_element` → `batch_create_elements`로 할 것
7. **이미지 저장 없이 캔버스만 생성** — 서버 재시작 시 작업물이 사라짐
8. **씬 파일 없이 PNG만 저장** — 나중에 편집이 불가능해짐. 항상 `.excalidraw`도 함께 저장할 것
9. **번역 시 snapshot 미사용** — 원본 한국어 상태를 잃어버림. 반드시 snapshot_scene으로 보존 후 번역
10. **번역 후 박스 크기 미조정** — 영어 텍스트는 한국어보다 길어지는 경우가 많아 박스 밖으로 넘침. 번역 후 `get_canvas_screenshot`으로 확인하고 박스 width를 조정할 것

# 사용 예시

```
# 기본: 현재 작업 중인 포스트 디렉토리에 자동 저장
/excalidraw-diagram "해시 테이블 로드 팩터별 성능 변화"

# 포스트 지정 + 다국어
/excalidraw-diagram "BFS vs DFS 비교" --post HashTable --lang ko,en,ja

# 저장 없이 캔버스에만 표시
/excalidraw-diagram "게임 아키텍처" --no-save

# 특정 포스트 이미지 디렉토리에 저장
/excalidraw-diagram "메모리 레이아웃" --post ArrayAndLinkedList

# [Edit Mode] 기존 다이어그램 편집
/excalidraw-diagram --edit excalidraw-01-load-factor

# [Edit Mode] 대화형으로 편집 요청
"로드 팩터 다이어그램 수정하고 싶어"
"excalidraw-02 그림 좀 고쳐줘"

# [Edit Mode] 편집 후 번역만 다시 생성
"excalidraw-01-load-factor 번역본 다시 만들어줘"
```

## 번들 리소스

| 파일 | 용도 | 언제 읽나 |
|------|------|----------|
| `references/design-guide.md` | 색상 팔레트, 사이징, 레이아웃, fontFamily 규칙 | Phase 3~4 (다이어그램 설계/생성 시) |
| `references/quality-checks.md` | fontFamily 린트, 겹침 검사 절차 | Phase 5~6 (품질 검사 시) |
