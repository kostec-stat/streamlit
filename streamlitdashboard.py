# streamlit_dashboard.py

import streamlit as st
import pandas as pd
import json
import altair as alt
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
import os

# 키워드, 스냅샷 날짜 리스트
keywords = ['AI', '과학기술정책']
snapshot_dates = ['2025-04-07', '2025-04-14', '2025-04-21', '2025-04-28']

# Streamlit App 시작
st.set_page_config(page_title="📈 키워드 대시보드", layout="wide")
st.title("📈 주간 키워드 대시보드")

# 사이드바에서 키워드와 날짜 선택
selected_keyword = st.sidebar.selectbox("관심 키워드 선택", keywords)
selected_snapshot = st.sidebar.selectbox("스냅샷 날짜 선택", snapshot_dates)

# 선택에 따라 JSON 파일 경로 결정
keyword_prefix = 'AI' if selected_keyword == 'AI' else 'STP'
report_path = f"assets/reports/{keyword_prefix}_{selected_snapshot}.json"
trend_path = f"assets/data/{keyword_prefix}_{selected_snapshot}_KT.json"

# 데이터 로딩
@st.cache_data
def load_report(path):
    with open(path, encoding='utf-8') as f:
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
        trend_data = pd.read_json(trend_path)
        chart = alt.Chart(trend_data).mark_line(point=True).encode(
            x='date:T',
            y=alt.Y('count:Q', title='빈도수'),
            color='keyword:N'
        )
        st.altair_chart(chart, use_container_width=True)
    except Exception as e:
        st.error(f"트렌드 차트 로딩 실패: {e}")

# 2. 키워드 네트워크
with tab2:
    st.subheader("🕸 키워드 동시출현 네트워크")
    try:
        G = nx.Graph()
        for link in report["co_occurrence_network"]:
            G.add_edge(link['source'], link['target'], weight=link['weight'])
        
        net = Network(height="500px", width="100%", bgcolor="#ffffff", font_color="black")
        net.from_nx(G)
        net.save_graph("network.html")
        components.iframe("network.html", height=550)
    except Exception as e:
        st.error(f"네트워크 그래프 로딩 실패: {e}")

# 3. 연관어 통계
with tab3:
    st.subheader("🔍 키워드 연관어 통계")
    for assoc in report["associations"]:
        st.write(f"🔹 {assoc['term']} ({assoc['count']}회)")

# 4. Top 20 키워드
with tab4:
    st.subheader("🏆 Top 20 키워드 및 사이트 목록")
    for item in report["top_keywords"]:
        with st.expander(f"{item['rank']}. {item['keyword']} (사이트 {item['site_coverage']}개, {item['site_count']}회)"):
            for url in item.get('sites', []):
                st.markdown(f"- [🔗 {url}]({url})")
