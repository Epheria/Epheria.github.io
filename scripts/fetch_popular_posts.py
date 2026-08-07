#!/usr/bin/env python3
"""
GA4 Data API를 사용해서 인기 포스트 Top 10을 가져와
_data/popular-posts.yml 파일을 생성합니다.

사전 준비:
1. Google Cloud Console에서 Service Account 생성
2. GA4 Property에 Service Account 뷰어 권한 부여
3. GitHub Secrets에 다음 두 값 설정:
   - GA_PROPERTY_ID: GA4 Numeric Property ID (예: 123456789)
   - GA_SERVICE_ACCOUNT_KEY: 서비스 계정 JSON 키 (전체 내용)
"""

import glob
import json
import os
import re
from datetime import datetime, timedelta

import yaml

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
)
from google.oauth2 import service_account


def get_ga_client():
    """서비스 계정 키로 GA4 클라이언트 생성"""
    key_json = os.environ.get("GA_SERVICE_ACCOUNT_KEY")
    if not key_json:
        raise ValueError("GA_SERVICE_ACCOUNT_KEY 환경변수가 없습니다.")

    key_data = json.loads(key_json)
    credentials = service_account.Credentials.from_service_account_info(
        key_data,
        scopes=["https://www.googleapis.com/auth/analytics.readonly"],
    )
    return BetaAnalyticsDataClient(credentials=credentials)


def get_recent_post_slugs(posts_dir="_posts", months=6):
    """_posts/ 디렉토리에서 최근 N개월 이내 작성된 포스트의 slug 목록 반환"""
    cutoff = datetime.now() - timedelta(days=months * 30)
    slugs = set()

    for filepath in glob.glob(os.path.join(posts_dir, "**/*.md"), recursive=True):
        filename = os.path.basename(filepath)
        # 번역 파일(.en.md, .ja.md) 제외
        if re.search(r'\.(en|ja)\.md$', filename):
            continue
        # 파일명 패턴: YYYY-M-D-slug.md
        # 월/일 zero-padding은 선택이다. 2026-2-13-llm-guide.md 처럼
        # 한 자리로 쓴 파일이 실제로 존재하므로 \d{2} 로 고정하면 안 된다.
        match = re.match(r'(\d{4})-(\d{1,2})-(\d{1,2})-(.+)\.md$', filename)
        if not match:
            continue
        try:
            post_date = datetime(
                int(match.group(1)), int(match.group(2)), int(match.group(3))
            )
        except ValueError:
            continue
        if post_date >= cutoff:
            slug = match.group(4)
            slugs.add(slug)

    return slugs


def fetch_popular_pages(client, property_id, days=30, limit=1000):
    """지난 N일간 페이지뷰 기준 상위 페이지 조회

    limit은 필터링 이전에 GA 쪽에서 잘리는 값이다. 응답 행에는 en/ja 미러,
    오래된 포스트, 탭·아카이브 페이지가 전부 섞여 있어서 이 값이 작으면
    조건을 통과하는 최근 ko 포스트가 몇 개 남지 않는다. GA4 기본값은 10000.
    """
    request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[
            Dimension(name="pagePath"),
            Dimension(name="pageTitle"),
        ],
        metrics=[
            Metric(name="screenPageViews"),
        ],
        date_ranges=[DateRange(start_date=f"{days}daysAgo", end_date="today")],
        limit=limit,
        order_bys=[
            {
                "metric": {"metric_name": "screenPageViews"},
                "desc": True,
            }
        ],
    )
    return client.run_report(request)


# ko 포스트 URL만 매칭한다. permalink가 /posts/:title/ 이라 정확히 두 세그먼트이고,
# polyglot이 붙이는 /en/posts/..., /ja/posts/... 는 세그먼트가 하나 더 많아 자동 제외된다.
# 탭(/:title/), 아카이브(/categories/:name/), 홈(/)도 여기서 함께 걸러진다.
POST_PATH_RE = re.compile(r"^/posts/([^/]+)/?$")


def extract_post_slug(path):
    """ko 포스트 경로면 slug를, 아니면 None을 반환"""
    match = POST_PATH_RE.match(path)
    return match.group(1) if match else None


def build_popular_posts(response, recent_slugs=None, top_n=10):
    """GA 응답에서 포스트 데이터 추출 (경로·최근성 필터 후 URL 기준 합산)"""
    aggregated = {}
    path_matched = 0

    for row in response.rows:
        path = row.dimension_values[0].value
        title = row.dimension_values[1].value
        views = int(row.metric_values[0].value)

        slug = extract_post_slug(path)
        if slug is None:
            continue
        path_matched += 1

        if recent_slugs is not None and slug not in recent_slugs:
            continue

        # 경로 정규화 (trailing slash 보장)
        url = f"/posts/{slug}/"
        entry = aggregated.get(url)
        if entry is None:
            aggregated[url] = {
                "url": url,
                "title": title,
                "views": views,
                "_top_row_views": views,
            }
        else:
            # GA는 (pagePath, pageTitle) 조합으로 그룹화하므로 제목을 고친 포스트는
            # 옛 제목·새 제목 두 행으로 쪼개진다. 조회수는 합치고 제목은 조회수가
            # 가장 많은 행의 것을 쓴다.
            entry["views"] += views
            if views > entry["_top_row_views"]:
                entry["_top_row_views"] = views
                entry["title"] = title

    # 합산으로 GA의 정렬이 깨지므로 다시 내림차순 정렬한다.
    posts = sorted(aggregated.values(), key=lambda p: p["views"], reverse=True)
    for post in posts:
        post.pop("_top_row_views", None)

    print(f"  GA 전체 행 {response.row_count}개 중 {len(response.rows)}개 수신")
    print(f"  ko 포스트 경로 {path_matched}개 → 최근성 통과 {len(posts)}개")

    posts = posts[:top_n]
    if posts:
        print(f"  상위 {len(posts)}개 선정 (최저 조회수 {posts[-1]['views']})")

    return posts


def write_yaml(posts, output_path="_data/popular-posts.yml"):
    """YAML 파일로 저장"""
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

    # 주석을 포함한 YAML 수동 작성
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# 이 파일은 GitHub Actions(update-popular-posts.yml)에 의해 자동 생성됩니다.\n")
        f.write("# 수동 수정 시 다음 자동 실행 시 덮어씌워집니다.\n\n")
        f.write("posts:\n")
        for post in posts:
            # JSON 문자열 리터럴은 YAML의 double-quoted scalar와 문법이 호환된다.
            # 직접 큰따옴표만 치환하면 제목에 백슬래시가 섞였을 때 YAML이 깨지고
            # 사이트 빌드 전체가 실패한다.
            f.write(f"  - url: {json.dumps(post['url'], ensure_ascii=False)}\n")
            f.write(f"    title: {json.dumps(post['title'], ensure_ascii=False)}\n")
            f.write(f"    views: {post['views']}\n")

    print(f"✅ {len(posts)}개 인기 포스트를 {output_path}에 저장했습니다.")


def main():
    property_id = os.environ.get("GA_PROPERTY_ID")
    if not property_id:
        raise ValueError("GA_PROPERTY_ID 환경변수가 없습니다.")

    print(f"GA4 Property ID: {property_id}")
    print("GA4 클라이언트 초기화 중...")

    client = get_ga_client()

    # 최근 6개월 이내 작성된 포스트 slug 목록
    recent_slugs = get_recent_post_slugs()
    print(f"최근 6개월 이내 포스트: {len(recent_slugs)}개")

    print("지난 30일간 인기 페이지 조회 중...")
    response = fetch_popular_pages(client, property_id)

    posts = build_popular_posts(response, recent_slugs)
    print(f"포스트 {len(posts)}개 추출 완료")

    write_yaml(posts)


if __name__ == "__main__":
    main()
