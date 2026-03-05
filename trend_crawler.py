#!/usr/bin/env python3
"""Google Trends & Naver 검색 트렌드를 1시간마다 수집하여 JSON으로 저장하는 스크립트"""

import json
import logging
import os
import re
import time
from datetime import datetime

import feedparser
import requests
from bs4 import BeautifulSoup

# 설정
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
INTERVAL_SECONDS = 3600  # 1시간

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def fetch_google_trends() -> list[dict]:
    """Google Trends 일간 인기 검색어 (한국) RSS 피드에서 수집"""
    url = "https://trends.google.co.kr/trending/rss?geo=KR"
    try:
        feed = feedparser.parse(url)
        results = []
        for i, entry in enumerate(feed.entries, start=1):
            results.append({
                "rank": i,
                "title": entry.get("title", ""),
                "traffic": entry.get("ht_approx_traffic", ""),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
            })
        logger.info("Google Trends: %d개 키워드 수집 완료", len(results))
        return results
    except Exception as e:
        logger.error("Google Trends 수집 실패: %s", e)
        return []


def fetch_naver_datalab_shopping() -> dict:
    """Naver DataLab 쇼핑인사이트 - 분야별 인기 검색어 & 인기분야 수집"""
    base_headers = {**HEADERS, "Referer": "https://datalab.naver.com/"}

    result = {"popular_categories": [], "category_keywords": {}}

    # 1) 인기분야 랭킹
    try:
        resp = requests.get(
            "https://datalab.naver.com/shoppingInsight/getCategoryRank.naver",
            headers=base_headers,
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            # 여러 날짜의 데이터 중 가장 최신 것 선택
            if isinstance(data, list):
                latest = data[-1] if data else {}
            else:
                latest = data
            ranks = latest.get("ranks", [])
            result["popular_categories"] = [
                {"rank": r["rank"], "keyword": r["keyword"]}
                for r in ranks
            ]
    except Exception as e:
        logger.warning("Naver 인기분야 수집 실패: %s", e)

    # 2) 카테고리별 인기 검색어 (주요 카테고리)
    categories = {
        "50000000": "패션의류",
        "50000001": "패션잡화",
        "50000002": "화장품/미용",
        "50000003": "디지털/가전",
        "50000004": "가구/인테리어",
        "50000005": "출산/육아",
        "50000006": "식품",
        "50000007": "스포츠/레저",
        "50000008": "생활/건강",
    }
    for cid, cname in categories.items():
        try:
            resp = requests.get(
                "https://datalab.naver.com/shoppingInsight/getCategoryKeywordRank.naver",
                headers=base_headers,
                params={"cid": cid},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                ranks = data.get("ranks", [])
                if ranks:
                    result["category_keywords"][cname] = [
                        {"rank": r["rank"], "keyword": r["keyword"]}
                        for r in ranks
                    ]
        except Exception as e:
            logger.warning("Naver 카테고리(%s) 수집 실패: %s", cname, e)

    return result


def fetch_naver_datalab_page() -> list[dict]:
    """Naver DataLab 메인 페이지 파싱 (API 실패 시 fallback)"""
    try:
        resp = requests.get(
            "https://datalab.naver.com/",
            headers=HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # keyword_rank 블록 중 데이터가 있는 가장 최신 것 사용
        blocks = soup.select(".keyword_rank")
        results = []
        for block in reversed(blocks):
            items = block.select(".rank_list li")
            if not items:
                continue
            date_el = block.select_one(".rank_title")
            date_str = date_el.get_text(strip=True) if date_el else ""
            for item in items:
                num_el = item.select_one(".num")
                title_el = item.select_one(".title")
                if num_el and title_el:
                    results.append({
                        "rank": int(num_el.get_text(strip=True)),
                        "title": title_el.get_text(strip=True),
                        "date": date_str,
                    })
            if results:
                break

        return results
    except Exception as e:
        logger.warning("Naver DataLab 페이지 파싱 실패: %s", e)
        return []


def fetch_naver_trends() -> dict:
    """Naver 트렌드 수집 (DataLab 쇼핑인사이트 API + 페이지 파싱)"""
    try:
        # DataLab 쇼핑인사이트 API
        shopping = fetch_naver_datalab_shopping()
        # DataLab 메인 페이지 인기 검색어 (fallback / 보충)
        page_keywords = fetch_naver_datalab_page()

        result = {
            "shopping_insight": shopping,
            "page_keywords": page_keywords,
        }

        total = (
            len(shopping.get("popular_categories", []))
            + sum(len(v) for v in shopping.get("category_keywords", {}).values())
            + len(page_keywords)
        )
        logger.info("Naver Trends: 총 %d개 항목 수집 완료", total)
        return result
    except Exception as e:
        logger.error("Naver Trends 수집 실패: %s", e)
        return {}


def save_to_json(google_data: list[dict], naver_data: dict) -> str:
    """수집 결과를 JSON 파일로 저장"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    now = datetime.now()
    filename = now.strftime("trends_%Y%m%d_%H%M%S.json")
    filepath = os.path.join(OUTPUT_DIR, filename)

    result = {
        "collected_at": now.isoformat(),
        "google_trends": google_data,
        "naver_trends": naver_data,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    logger.info("저장 완료: %s", filepath)
    return filepath


def collect_once():
    """한 번 수집 실행"""
    logger.info("=== 트렌드 수집 시작 ===")
    google_data = fetch_google_trends()
    naver_data = fetch_naver_trends()
    filepath = save_to_json(google_data, naver_data)
    logger.info("=== 트렌드 수집 완료: %s ===", filepath)
    return filepath


def main():
    logger.info("트렌드 크롤러 시작 (수집 간격: %d초)", INTERVAL_SECONDS)

    # 시작 시 즉시 1회 수집
    collect_once()

    # 이후 1시간 간격으로 반복
    while True:
        time.sleep(INTERVAL_SECONDS)
        collect_once()


if __name__ == "__main__":
    main()
