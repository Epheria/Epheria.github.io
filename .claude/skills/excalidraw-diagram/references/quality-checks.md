# Quality Checks (린트 & 겹침 검사)

다이어그램 생성 후 자동으로 수행하는 품질 검사 절차다.
SKILL.md의 Phase 5~6에서 이 문서를 참조한다.

## 1. fontFamily 린트

`batch_create_elements`로 `fontFamily: 5`를 지정하면 프론트엔드에서도 5로 유지된다.
따라서 **생성 시 fontFamily: 5로 지정했다면 린트는 불필요**하다.

만약 외부에서 가져온 요소나 수동 편집으로 fontFamily가 바뀐 경우에만 검사한다:

```
# 모든 텍스트 요소 조회
texts = query_elements(type="text")

# fontFamily != 5 인 요소만 필터
wrong_font = [t for t in texts if t.fontFamily != 5]

# 일괄 업데이트
for t in wrong_font:
    update_element(id=t.id, fontFamily=5)
```

| fontFamily 값 | 이름 | 판정 |
|--------------|------|------|
| 5 | Excalifont (CJK 필기체) | OK — 기본값 |
| 1 | Virgil (영문 필기체) | 변환 (CJK 미지원) |
| 2 | Helvetica | 변환 |
| 3 | Cascadia (코드) | 유지 (코드 블록일 때만) |

## 2. 겹침 검사 및 간격 조정

모든 요소의 바운딩 박스를 비교하여 겹침을 탐지하고 자동 보정한다.
한 요소를 밀면 다른 겹침이 생길 수 있으므로 최대 2회 재검사한다.

### 검사 절차

1. `query_elements()`로 모든 요소 조회
2. 바운딩 박스 추출 (x, y, width, height)
3. AABB 겹침 판정: `(A.x < B.x+B.w) && (A.x+A.w > B.x) && (A.y < B.y+B.h) && (A.y+A.h > B.y)`
4. 겹치는 쌍의 중심 간 방향 벡터 계산 → 최소 간격 확보하도록 이동
5. `update_element(id, x, y)`로 위치 보정
6. 재검사 (최대 2회)

### 검사 제외 대상

의도적으로 겹치는 관계는 검사하지 않는다:

| 요소 조합 | 이유 |
|-----------|------|
| Zone 배경 ↔ 내부 노드 | 의도적 포함 관계 |
| 도형 ↔ 바인딩된 텍스트 | 도형 내부 라벨 |
| 화살표 ↔ 모든 요소 | 바인딩으로 자동 위치 |
| 그룹 내부 요소끼리 | 하나의 단위 |

### 간격 기준

- 같은 행/열 노드: 최소 40px
- 서로 다른 Zone 노드: 최소 60px
- 텍스트 주석 ↔ 도형: 최소 20px

### 결과 보고 형식

```
# 겹침 없음:
"✅ 겹침 검사 완료: 겹치는 요소 없음 (총 {N}개 요소 검사)"

# 겹침 해소:
"⚠️ 겹침 {M}건 발견 → 간격 조정 완료"
"  - rect_01 ↔ rect_03: 12px 겹침 → 40px 간격으로 이동"
```
