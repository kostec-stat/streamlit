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
selected_keyword = st.sidebar.selectbox("관심 키워드 선택", keywords)
selected_snapshot = st.sidebar.selectbox("스냅샷 날짜 선택", snapshot_dates)
summary_type = st.sidebar.selectbox("주기별 요약 보고서 선택", ["주간", "연간", "전체"], index=0)

# --- 5. 메인 대시보드
st.title("📈 키워드 대시보드")
    
# --- 6-1. 데이터 경로 설정
report_path = f"assets/reports/{selected_keyword}_{selected_snapshot}.json"
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
    top_keywords = keyword_totals.head(10).index.tolist()

    trend_data_long = trend_data.melt(id_vars=["date"], var_name="keyword", value_name="count")
    trend_data_top10 = trend_data_long[trend_data_long["keyword"].isin(top_keywords)]

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
    st.subheader(f"📊 {selected_keyword} 빈도수 통계")
    freq_df = pd.DataFrame(report["frequency_stats"])
    selected_freq_df = freq_df[freq_df["keyword"] == selected_keyword]
    st.dataframe(selected_freq_df)

    st.subheader(f"📈 빈도수 상위 10 키워드 트렌드 차트")
    for keyword in top_keywords:
        st.subheader(f"🔹 {keyword}")
        df_kw = trend_data_top10[trend_data_top10["keyword"] == keyword]
        
        chart = alt.Chart(df_kw).mark_line(point=True).encode(
            x='date:T',
            y=alt.Y('count:Q', title='빈도수'),
            color=alt.value('crimson')  # 단일 색상
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

