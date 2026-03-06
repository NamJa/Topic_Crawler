#!/usr/bin/env python3
"""트렌드 JSON 파일을 보기 쉬운 Markdown 문서로 변환하는 스크립트"""

import glob
import json
import os
import sys
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def json_to_markdown(data: dict) -> str:
    """트렌드 JSON 데이터를 Markdown 문자열로 변환"""
    collected_at = data.get("collected_at", "")
    try:
        dt = datetime.fromisoformat(collected_at)
        time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        time_str = collected_at

    lines = [
        f"# 검색 트렌드 리포트",
        f"",
        f"> 수집 시각: {time_str}",
        f"",
    ]

    # --- Google Trends ---
    google = data.get("google_trends", [])
    if google:
        lines.append("## Google 인기 검색어 (한국)")
        lines.append("")
        lines.append("| 순위 | 키워드 | 검색량 |")
        lines.append("|---:|:---|:---|")
        for item in google:
            rank = item.get("rank", "")
            title = item.get("title", "")
            traffic = item.get("traffic", "")
            lines.append(f"| {rank} | {title} | {traffic} |")
        lines.append("")

    # --- Naver Trends ---
    naver = data.get("naver_trends", {})
    if not naver:
        return "\n".join(lines)

    lines.append("## Naver 트렌드")
    lines.append("")

    # 인기분야
    shopping = naver.get("shopping_insight", {})
    popular = shopping.get("popular_categories", [])
    if popular:
        lines.append("### 급상승 인기분야")
        lines.append("")
        lines.append("| 순위 | 분야 |")
        lines.append("|---:|:---|")
        for item in popular:
            lines.append(f"| {item['rank']} | {item['keyword']} |")
        lines.append("")

    # 인기 검색어 (전체)
    pop_keywords = shopping.get("popular_keywords", [])
    if pop_keywords:
        lines.append("### 인기 검색어")
        lines.append("")
        lines.append("| 순위 | 키워드 |")
        lines.append("|---:|:---|")
        for item in pop_keywords:
            lines.append(f"| {item['rank']} | {item['keyword']} |")
        lines.append("")

    # 카테고리별 인기 검색어
    cat_keywords = shopping.get("category_keywords", {})
    if cat_keywords:
        lines.append("### 카테고리별 인기 검색어")
        lines.append("")
        for category, keywords in cat_keywords.items():
            lines.append(f"#### {category}")
            lines.append("")
            lines.append("| 순위 | 키워드 |")
            lines.append("|---:|:---|")
            for item in keywords:
                lines.append(f"| {item['rank']} | {item['keyword']} |")
            lines.append("")

    # 페이지 인기 검색어
    page_kw = naver.get("page_keywords", [])
    if page_kw:
        date_str = page_kw[0].get("date", "") if page_kw else ""
        header = f"### 쇼핑 인기 검색어 ({date_str})" if date_str else "### 쇼핑 인기 검색어"
        lines.append(header)
        lines.append("")
        lines.append("| 순위 | 키워드 |")
        lines.append("|---:|:---|")
        for item in page_kw:
            lines.append(f"| {item['rank']} | {item['title']} |")
        lines.append("")

    return "\n".join(lines)


def convert_file(json_path: str) -> str:
    """JSON 파일 하나를 Markdown 파일로 변환, 저장 경로 반환"""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    md_content = json_to_markdown(data)
    md_path = json_path.rsplit(".", 1)[0] + ".md"

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    return md_path


def main():
    # 인자가 있으면 해당 파일만, 없으면 data/ 내 전체 JSON 변환
    if len(sys.argv) > 1:
        targets = sys.argv[1:]
    else:
        targets = sorted(glob.glob(os.path.join(DATA_DIR, "trends_*.json")))

    if not targets:
        print("변환할 JSON 파일이 없습니다.")
        return

    for path in targets:
        md_path = convert_file(path)
        print(f"{os.path.basename(path)} -> {os.path.basename(md_path)}")


if __name__ == "__main__":
    main()
