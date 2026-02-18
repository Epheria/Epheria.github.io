#!/usr/bin/env python3
"""
모든 포스트에 difficulty: intermediate 기본값을 추가합니다.
이미 difficulty가 있는 포스트는 건드리지 않습니다.

사용법:
  # 미리보기 (파일 수정 없음)
  python scripts/add_difficulty.py --dry-run

  # 실제 적용
  python scripts/add_difficulty.py
"""

import argparse
import os
import re
import sys


POSTS_DIR = "_posts"
DEFAULT_DIFFICULTY = "intermediate"


def find_markdown_files(root):
    """모든 .md 파일 경로 수집"""
    files = []
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            if name.endswith(".md"):
                files.append(os.path.join(dirpath, name))
    return sorted(files)


def parse_front_matter(content):
    """front matter 파싱. (start_end_indices, dict) 반환"""
    if not content.startswith("---"):
        return None, None

    end = content.find("\n---", 3)
    if end == -1:
        return None, None

    return (0, end + 4), content[3:end].strip()


def has_field(front_matter_str, field):
    """front matter 문자열에서 특정 필드 존재 여부 확인"""
    return bool(re.search(rf"^{re.escape(field)}\s*:", front_matter_str, re.MULTILINE))


def insert_difficulty(front_matter_str, difficulty):
    """toc 줄 앞에 difficulty 삽입 (없으면 맨 마지막에 추가)"""
    lines = front_matter_str.split("\n")
    insert_idx = len(lines)  # 기본: 맨 끝

    for i, line in enumerate(lines):
        if re.match(r"^toc\s*:", line):
            insert_idx = i
            break

    lines.insert(insert_idx, f"difficulty: {difficulty}")
    return "\n".join(lines)


def process_file(filepath, difficulty, dry_run):
    """파일 처리: difficulty 없는 경우 추가"""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    indices, fm_str = parse_front_matter(content)
    if fm_str is None:
        return "skip_no_fm"

    if has_field(fm_str, "difficulty"):
        return "skip_has_difficulty"

    new_fm = insert_difficulty(fm_str, difficulty)

    # front matter 영역 교체
    start, end = indices
    new_content = "---\n" + new_fm + "\n---" + content[end:]

    if not dry_run:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)

    return "updated"


def main():
    parser = argparse.ArgumentParser(description="Add difficulty front matter to all posts")
    parser.add_argument("--dry-run", action="store_true", help="미리보기만 (파일 수정 없음)")
    parser.add_argument("--difficulty", default=DEFAULT_DIFFICULTY,
                        choices=["beginner", "intermediate", "advanced"],
                        help=f"기본 난이도 (기본값: {DEFAULT_DIFFICULTY})")
    args = parser.parse_args()

    # 프로젝트 루트에서 실행되어야 함
    if not os.path.isdir(POSTS_DIR):
        print(f"오류: '{POSTS_DIR}' 디렉토리를 찾을 수 없습니다.")
        print("프로젝트 루트 디렉토리에서 실행하세요.")
        sys.exit(1)

    files = find_markdown_files(POSTS_DIR)
    print(f"총 {len(files)}개 포스트 파일 발견\n")

    if args.dry_run:
        print("🔍 미리보기 모드 (실제 파일 수정 없음)\n")

    stats = {"updated": 0, "skip_has_difficulty": 0, "skip_no_fm": 0}

    for filepath in files:
        result = process_file(filepath, args.difficulty, args.dry_run)
        stats[result] += 1
        if result == "updated":
            action = "미리보기" if args.dry_run else "추가됨"
            rel_path = os.path.relpath(filepath, POSTS_DIR)
            print(f"  ✅ {action}: {rel_path}")

    print(f"\n{'─' * 50}")
    print(f"📊 결과 요약")
    print(f"  difficulty 추가{'(예정)' if args.dry_run else '됨'}: {stats['updated']}개")
    print(f"  이미 있음 (건드리지 않음): {stats['skip_has_difficulty']}개")
    print(f"  front matter 없음 (건드리지 않음): {stats['skip_no_fm']}개")

    if args.dry_run and stats["updated"] > 0:
        print(f"\n💡 실제 적용하려면:")
        print(f"  python scripts/add_difficulty.py --difficulty {args.difficulty}")


if __name__ == "__main__":
    main()
