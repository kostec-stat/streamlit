#-*- coding: utf-8 -*-
#   Author : Dr. Songhee Kang.
#   Email : dellabee@tukorea.ac.kr
#   Description : KOSTEC stat visualizer
#   Version : 1.0.0
#   History : 1.0.0 - 2025. 04. 29. 최초 작성

# streamlit_dashboard.py

import streamlit as st
import pandas as pd
import json
import altair as alt
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
from streamlit_agraph import agraph, Node, Edge, Config
import os

# 키워드, 스냅샷 날짜 리스트
keywords = []
# 1. 키워드 로딩
def load_keywords(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        keywords = [line.strip() for line in f if line.strip()]
    return keywords

keywords = load_keywords("assets/input/keywords.txt")  # 키워드 파일 경로 수정
snapshot_dates = ['20250429']

# Streamlit App 시작
st.set_page_config(page_title="📈 키워드 대시보드", layout="wide")
col_main, col_side = st.columns([3, 1])
with col_main:
    st.title("📈 주간 키워드 대시보드")
    
    # 사이드바에서 키워드와 날짜 선택
    selected_keyword = st.sidebar.selectbox("관심 키워드 선택", keywords)
    selected_snapshot = st.sidebar.selectbox("스냅샷 날짜 선택", snapshot_dates)
    
    # 선택에 따라 JSON 파일 경로 결정
    report_path = f"assets/reports/{selected_keyword}_{selected_snapshot}.json"
    trend_path = f"assets/data/{selected_snapshot}_trend_summary.json"
    
    # 데이터 로딩
    @st.cache_data
    def load_report(path):
        with open(path, encoding='utf-8-sig') as f:
            return json.load(f)
    
    try:
        report = load_report(report_path)
    except FileNotFoundError:
        st.error("보고서 파일이 없습니다.")
        st.stop()
    
    # 탭 생성
    tab1, tab2, tab3, tab4 = st.tabs(["📊 키워드 빈도수", "🕸 키워드 네트워크", "🔍 연관어 통계", "🏆 Top 20 키워드"])
    
    # 1. 키워드 빈도수 통계
    with tab1:
        st.subheader("📊 키워드별 빈도수 통계")
        
        freq_df = pd.DataFrame(report["frequency_stats"])
        st.dataframe(freq_df)
        
        st.subheader("📈 키워드 트렌드 차트")
        try:
            with open(trend_path, encoding='utf-8-sig') as f:
                trend_json = json.load(f)
        
            trend_data = pd.DataFrame(trend_json["trend_data"])
        
            # long format으로 변환 (date, keyword, count 형태)
            trend_data_long = trend_data.melt(id_vars=["date"], var_name="keyword", value_name="count")
        
            chart = alt.Chart(trend_data_long).mark_line(point=True).encode(
                x='date:T',
                y=alt.Y('count:Q', title='빈도수'),
                color='keyword:N'
            )
            st.altair_chart(chart, use_container_width=True)
        except Exception as e:
            st.error(f"트렌드 차트 로딩 실패: {e}")
    
    
    # 2. 키워드 네트워크
    with tab2:
        st.subheader("🕸 키워드 동시출현 네트워크 (Graph)")
        try:
            node_ids = set()
            nodes = []
            edges = []
            background_color = "black"
            font_color = "white"
            # 노드를 중복 없이 만들기
            for link in report["cooccurrence"]:
                source = link['source']
                target = link['target']
                count = link['count']
    
                if source not in node_ids:
                    nodes.append(Node(id=source, label=source))
                    node_ids.add(source)
    
                if target not in node_ids:
                    nodes.append(Node(id=target, label=target))
                    node_ids.add(target)
    
                edges.append(Edge(source=source, target=target, label=str(count)))
    
            config = Config(
                width=800,
                height=600,
                directed=False,
                physics=True,
                hierarchical=False
            )
    
            agraph(nodes=nodes, edges=edges, config=config)
    
        except Exception as e:
            st.error(f"네트워크 그래프 로딩 실패: {e}")
    # 3. 연관어 통계
    with tab3:
        st.subheader("🔍 키워드 연관어 통계")
        for assoc in report["associations"]:
            st.write(f"🔹 {assoc['term']} ({assoc['count']}회)")
            
# Top 20 키워드 (오른쪽 패널)
with col_side:
    st.header("🏆 Top 20 키워드")



# CSV 파일 읽기
    df = pd.read_csv(f"assets/data/{selected_snapshot}_search_results.csv", encoding="utf-8-sig")
    
    # title + snippet 합치기 (full_text 컬럼 만들기)
    df["full_text"] = df["title"].fillna('') + " " + df["snippet"].fillna('')
    # 1. 키워드 빈도수 집계
    keyword_counter = {}
    for kw in keywords:
        keyword_counter[kw] = df["full_text"].str.contains(kw, na=False, regex=False).sum()

    # 2. 빈도수 기준 상위 20개 키워드 추출
    top_keywords = sorted(keyword_counter.items(), key=lambda x: x[1], reverse=True)[:20]

    for idx, (kw, count) in enumerate(top_keywords, 1):
        st.markdown(f"**{idx}. {kw}** ({count}회 등장)")

        # 3. 관련 사이트(title, link, snippet) 리스트
        matched_rows = df[df["full_text"].str.contains(kw, na=False)]
        for _, row in matched_rows.iterrows():
            st.markdown(f"- [{row['title']}]({row['link']})")
            st.caption(f"{row['snippet'][:80]}...")  # snippet을 짧게 요약
        st.divider()
