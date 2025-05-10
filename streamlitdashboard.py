# -*- coding: utf-8 -*-
# Author : Dr. Songhee Kang
# Description : KOSTEC stat visualizer

import streamlit as st
import pandas as pd
import json
import altair as alt
import networkx as nx
from streamlit_agraph import agraph, Node, Edge, Config
import os
from collections import defaultdict

# --- 1. 설정 (가장 먼저)
st.set_page_config(page_title="📈 한중과기협력센터 키워드 대시보드", layout="wide")
# --- 2. CSS 적용
def local_css(file_name):
    with open(file_name, "r", encoding="utf-8") as f:
        css_content = f.read()
    st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)

# assets/css 폴더의 main.css를 읽어오기
local_css("assets/css/main.css")
# --- 3. 데이터 불러오기
def load_keywords(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def load_json(path):
    with open(path, encoding='utf-8-sig') as f:
        return json.load(f)

# 키워드, 스냅샷 날짜
keywords = load_keywords("assets/input/keywords.txt")
snapshot_dates = ['20250429', '20250501', '20250511']

# --- 4. 사이드바
#selected_keyword = st.sidebar.selectbox("관심 키워드 선택", keywords)
#selected_snapshot = st.sidebar.selectbox("스냅샷 날짜 선택", snapshot_dates)
summary_type = st.sidebar.selectbox("주기별 요약 보고서 선택", ["전체",  "연간", "주간"], index=0)

# --- 5. 메인 대시보드
st.title("📈 키워드 대시보드")
    
# --- 6-1. 데이터 경로 설정
#report_path = f"assets/reports/{selected_keyword}_{selected_snapshot}.json"
trend_path = f"assets/data/{snapshot_dates[-1]}_trend_summary.json"
search_results_path = f"assets/data/{selected_snapshot}_search_results.csv"

# --- 6-2. 데이터 로딩
try:
    report = load_json(report_path)
except FileNotFoundError:
    st.error(f"보고서 파일을 찾을 수 없습니다: {report_path}")
    st.stop()

try:
    trend_json = load_json(trend_path)
    trend_data = pd.DataFrame(trend_json["trend_data"])
    trend_data["date"] = pd.to_datetime(trend_data["date"])  # 날짜 형식 변환
    # 4. 총 빈도수 합산 기준 상위 10개 키워드 추출
    keyword_cols = [col for col in trend_data.columns if col != "date"]
    keyword_totals = trend_data[keyword_cols].sum().sort_values(ascending=False)
    top_keywords = keyword_totals.head(20).index.tolist()

    trend_data_long = trend_data.melt(id_vars=["date"], var_name="keyword", value_name="count")
    trend_data_top20 = trend_data_long[trend_data_long["keyword"].isin(top_keywords)]

except Exception as e:
    st.error(f"트렌드 데이터 로딩 실패: {e}")
    st.stop()

try:
    df = pd.read_csv(search_results_path, encoding="utf-8-sig")
    df["full_text"] = df["title"].fillna('') + " " + df["snippet"].fillna('')
except FileNotFoundError:
    st.error(f"검색 결과 파일을 찾을 수 없습니다: {search_results_path}")
    st.stop()
    
try:
    report = load_json(report_path)
except FileNotFoundError:
    st.error("보고서 파일을 찾을 수 없습니다.")
    st.stop()
    
# 탭
tab1, tab2, tab3 = st.tabs(["📊 빈도수", "🕸 네트워크", "🔍 연관어"])

# --- 7.1 빈도수 통계
with tab1:
    st.subheader("📊 전체 키워드 빈도수 통계")

    # 전체 빈도수 통계 DataFrame
    freq_df = pd.DataFrame(report["frequency_stats"])

    # 빈도수가 0 초과인 키워드만 필터링
    filtered_df = freq_df[freq_df["count"] > 0]

    # count 기준 내림차순 정렬
    sorted_df = filtered_df.sort_values(by="count", ascending=False).reset_index(drop=True)

    # 데이터프레임 출력
    st.dataframe(sorted_df, use_container_width=True)
    
    st.subheader(f"📈 빈도수 상위 20 키워드 트렌드 차트")
    n_cols = 5
    rows = [top_keywords[i:i + n_cols] for i in range(0, len(top_keywords), n_cols)]
    
    for row_keywords in rows:
        cols = st.columns(n_cols)
        for idx, keyword in enumerate(row_keywords):
            with cols[idx]:
                st.markdown(f"**{keyword}**")
                df_kw = trend_data_top20[trend_data_top20["keyword"] == keyword]
    
                chart = alt.Chart(df_kw).mark_line(point=True).encode(
                    x=alt.X('date:T', axis=alt.Axis(labelFontSize=8, titleFontSize=10)),
                    y=alt.Y('count:Q', title='', axis=alt.Axis(labelFontSize=8)),
                    color=alt.value('crimson')
                ).properties(width=220, height=180)
    
                st.altair_chart(chart, use_container_width=False)
    
# --- 7.2 네트워크 그래프
with tab2:
    st.subheader("🕸 전체 키워드 네트워크 (Top 20 중심 연결망)")

    # 1. keyword별 연결 count 총합 계산
    keyword_link_count = defaultdict(int)
    for link in report["cooccurrence"]:
        keyword_link_count[link["source"]] += link["count"]
        keyword_link_count[link["target"]] += link["count"]

    # 2. 상위 20개 중심 키워드 선정
    top20_keywords = sorted(keyword_link_count.items(), key=lambda x: x[1], reverse=True)[:20]
    top20_keywords = {kw for kw, _ in top20_keywords}

    # 3. Top 20 키워드 관련 링크만 필터링
    filtered_links = [
        link for link in report["cooccurrence"]
        if link["source"] in top20_keywords or link["target"] in top20_keywords
    ]

    # 4. 전체 노드/엣지 구성
    node_ids = set()
    nodes = []
    edges = []

    for link in filtered_links:
        source, target, count = link['source'], link['target'], link['count']

        if source not in node_ids:
            nodes.append(Node(id=source, label=source, font={"color": "white"}))
            node_ids.add(source)
        if target not in node_ids:
            nodes.append(Node(id=target, label=target, font={"color": "white"}))
            node_ids.add(target)

        edges.append(Edge(source=source, target=target, label=str(count)))

    # 5. 네트워크 시각화
    try:
        config = Config(width=900, height=700, directed=False, physics=True, hierarchical=False)
        agraph(nodes=nodes, edges=edges, config=config)
    except Exception as e:
        st.error(f"전체 네트워크 그래프 로딩 실패: {e}")

# --- 7.3 연관어 통계
with tab3:
    st.subheader("🔍 전체 연관어 Top 20")

    # count 기준으로 정렬
    associations_sorted = sorted(report["associations"], key=lambda x: x["count"], reverse=True)[:20]

    # 2열 표시
    col1, col2 = st.columns(2)
    half = len(associations_sorted) // 2

    for i, assoc in enumerate(associations_sorted):
        text = f"🔹 {assoc['term']} ({assoc['count']}회)"
        if i < half:
            col1.write(text)
        else:
            col2.write(text)

# --- 5. 하단(푸터) Top 20 키워드 + 관련 사이트
st.divider()
if summary_type == "전체":
    st.subheader("🏆 요약 보고서: Top 20 키워드 및 관련 사이트")
    
    # 데이터 읽기 (full_text 생성 포함)
    search_results_path = f"assets/data/{snapshot_dates[-1]}_search_results.csv"
    try:
        df = pd.read_csv(search_results_path, encoding="utf-8-sig")
        df["full_text"] = df["title"].fillna('') + " " + df["snippet"].fillna('')
    except FileNotFoundError:
        st.error(f"검색 결과 파일이 없습니다: {search_results_path}")
        st.stop()
    
    # 키워드 빈도수 집계
    keyword_counter = {kw: df["full_text"].str.contains(kw, na=False, regex=False).sum() for kw in keywords}
    top_keywords = sorted(keyword_counter.items(), key=lambda x: x[1], reverse=True)[:20]
    
    # 하단 패널 표시
    for idx, (kw, count) in enumerate(top_keywords, 1):
        with st.expander(f"**{idx}. {kw}** ({count}회 등장)", expanded=False):
            matched_rows = df[df["full_text"].str.contains(kw, na=False, regex=False)]
            for _, row in matched_rows.iterrows():
                st.markdown(f"- [{row['title']}]({row['link']})")
                st.caption(f"{row['snippet'][:80]}...")

