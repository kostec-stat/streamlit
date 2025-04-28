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

# --- 1. 설정 (가장 먼저)
st.set_page_config(page_title="📈 키워드 대시보드", layout="wide")
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
snapshot_dates = ['20250429']

# --- 4. 사이드바
selected_keyword = st.sidebar.selectbox("관심 키워드 선택", keywords)
selected_snapshot = st.sidebar.selectbox("스냅샷 날짜 선택", snapshot_dates)

# --- 5. 메인 대시보드
st.title("📈 주간 키워드 대시보드")
    
# --- 6. 데이터 경로 설정
report_path = f"assets/reports/{selected_keyword}_{selected_snapshot}.json"
trend_path = f"assets/data/{selected_snapshot}_trend_summary.json"
    
try:
    report = load_json(report_path)
except FileNotFoundError:
    st.error("보고서 파일을 찾을 수 없습니다.")
    st.stop()
    
# 탭
tab1, tab2, tab3 = st.tabs(["📊 빈도수", "🕸 네트워크", "🔍 연관어"])

# --- 7.1 빈도수 통계
with tab1:
    st.subheader(f"📊 {selected_keyword} 빈도수 통계")
    freq_df = pd.DataFrame(report["frequency_stats"])
    selected_freq_df = freq_df[freq_df["keyword"] == selected_keyword]
    st.dataframe(selected_freq_df)

    st.subheader(f"📈 {selected_keyword} 트렌드 차트")
    trend_data_long = trend_data.melt(id_vars=["date"], var_name="keyword", value_name="count")
    trend_data_filtered = trend_data_long[trend_data_long["keyword"] == selected_keyword]

    chart = alt.Chart(trend_data_filtered).mark_line(point=True).encode(
        x='date:T',
        y=alt.Y('count:Q', title='빈도수'),
        color=alt.value('teal')
    )
    st.altair_chart(chart, use_container_width=True)

    # --- 7.2 네트워크 그래프
with tab2:
    st.subheader(f"🕸 {selected_keyword} 관련 네트워크")
    try:
        node_ids = set()
        nodes = []
        edges = []

        for link in report["cooccurrence"]:
            if selected_keyword in (link['source'], link['target']):
                source, target, count = link['source'], link['target'], link['count']

                if source not in node_ids:
                    nodes.append(Node(id=source, label=source, font={"color": "white"}))
                    node_ids.add(source)
                if target not in node_ids:
                    nodes.append(Node(id=target, label=target, font={"color": "white"}))
                    node_ids.add(target)

                edges.append(Edge(source=source, target=target, label=str(count)))

        config = Config(width=800, height=600, directed=False, physics=True, hierarchical=False)
        agraph(nodes=nodes, edges=edges, config=config)
    except Exception as e:
        st.error(f"네트워크 그래프 로딩 실패: {e}")

    # --- 7.3 연관어 통계
with tab3:
    st.subheader(f"🔍 {selected_keyword} 연관어 통계")
    for assoc in report["associations"]:
        st.write(f"🔹 {assoc['term']} ({assoc['count']}회)")

# --- 5. 하단(푸터) Top 20 키워드 + 관련 사이트
st.divider()
st.subheader("🏆 Top 20 키워드 및 관련 사이트")

# 데이터 읽기 (full_text 생성 포함)
search_results_path = f"assets/data/{selected_snapshot}_search_results.csv"
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
