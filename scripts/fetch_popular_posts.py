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

import json
import os
import re
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


def fetch_popular_pages(client, property_id, days=30, limit=15):
    """지난 N일간 페이지뷰 기준 상위 페이지 조회"""
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


def is_post_path(path):
    """Jekyll 포스트 경로인지 판별 (카테고리/slug/ 패턴)"""
    # 포스트 URL 패턴: /카테고리/슬러그/ 혹은 /posts/슬러그/
    # 홈, /archives/, /categories/ 등 탭 페이지는 제외
    excluded = ["/", "/archives/", "/categories/", "/tags/", "/about/",
                "/stats/", "/books/", "/sideproject/", "/404"]
    if path in excluded:
        return False
    # 포스트는 보통 2단계 이상 경로
    parts = [p for p in path.split("/") if p]
    return len(parts) >= 2


def build_popular_posts(response):
    """GA 응답에서 포스트 데이터 추출"""
    posts = []
    for row in response.rows:
        path = row.dimension_values[0].value
        title = row.dimension_values[1].value
        views = int(row.metric_values[0].value)

        if not is_post_path(path):
            continue

        # 경로 정규화 (trailing slash 보장)
        if not path.endswith("/"):
            path += "/"

        posts.append({
            "url": path,
            "title": title,
            "views": views,
        })

        if len(posts) >= 10:
            break

    return posts


def write_yaml(posts, output_path="_data/popular-posts.yml"):
    """YAML 파일로 저장"""
    data = {
        "# 이 파일은 GitHub Actions(update-popular-posts.yml)에 의해 자동 생성됩니다.": None,
        "# 수동 수정 시 다음 자동 실행 시 덮어씌워집니다.": None,
        "posts": posts,
    }

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

    # 주석을 포함한 YAML 수동 작성
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# 이 파일은 GitHub Actions(update-popular-posts.yml)에 의해 자동 생성됩니다.\n")
        f.write("# 수동 수정 시 다음 자동 실행 시 덮어씌워집니다.\n\n")
        f.write("posts:\n")
        for post in posts:
            f.write(f"  - url: \"{post['url']}\"\n")
            # 제목의 특수문자 이스케이프
            safe_title = post["title"].replace('"', '\\"')
            f.write(f"    title: \"{safe_title}\"\n")
            f.write(f"    views: {post['views']}\n")

    print(f"✅ {len(posts)}개 인기 포스트를 {output_path}에 저장했습니다.")


def main():
    property_id = os.environ.get("GA_PROPERTY_ID")
    if not property_id:
        raise ValueError("GA_PROPERTY_ID 환경변수가 없습니다.")

    print(f"GA4 Property ID: {property_id}")
    print("GA4 클라이언트 초기화 중...")

    client = get_ga_client()

    print("지난 30일간 인기 페이지 조회 중...")
    response = fetch_popular_pages(client, property_id)

    posts = build_popular_posts(response)
    print(f"포스트 {len(posts)}개 추출 완료")

    write_yaml(posts)


if __name__ == "__main__":
    main()
