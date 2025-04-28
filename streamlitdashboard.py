#-*- coding: utf-8 -*-
#   Author : Dr. Songhee Kang.
#   Email : dellabee@tukorea.ac.kr
#   Description : KOSTEC stat visualizer
#   Version : 1.0.0
#   History : 1.0.0 - 2025. 04. 29. 최초 작성

import streamlit as st
import pandas as pd
import json
import altair as alt
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
import os

st.set_page_config(page_title="📈 키워드 대시보드", layout="wide")
st.title("📈 주간 키워드 대시보드")

# 사이드바: 키워드, 스냅샷 선택
keywords = ['AI', '과학기술정책']
snapshot_dates = ['2025-04-07', '2025-04-14', '2025-04-21', '2025-04-28']

selected_keyword = st.sidebar.selectbox("관심 키워드", keywords)
selected_snapshot = st.sidebar.selectbox("스냅샷 날짜", snapshot_dates)

# 데이터 경로 설정
keyword_prefix = 'AI' if selected_keyword == 'AI' else 'STP'
report_path = f"assets/reports/{keyword_prefix}_{selected_snapshot}.json"
trend_path = f"assets/data/{keyword_prefix}_{selected_snapshot}_KT.json"

# 데이터 불러오기
@st.cache_data
def load_report(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)

try:
    report = load_report(report_path)
except FileNotFoundError:
    st.error("보고서 파일을 찾을 수 없습니다.")
    st.stop()

# 카드 스타일 적용
with st.container():
    st.markdown("### 📊 대시보드 영역")

    tabs = st.tabs(["📈 키워드 빈도수", "🕸 키워드 네트워크", "🔍 연관어 통계", "🏆 Top 20 키워드"])

    # 1. 빈도수
    with tabs[0]:
        st.subheader("📈 키워드별 빈도수 통계")
        st.divider()
        freq_df = pd.DataFrame(report["frequency_stats"])
        st.dataframe(freq_df, use_container_width=True)

        st.subheader("📈 트렌드 차트")
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

    # 2. 네트워크
    with tabs[1]:
        st.subheader("🕸 키워드 동시출현 네트워크")
        st.divider()
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
    with tabs[2]:
        st.subheader("🔍 키워드 연관어 통계")
        st.divider()
        for assoc in report["associations"]:
            st.markdown(f"🔹 **{assoc['term']}** ({assoc['count']}회)")

    # 4. Top 20 키워드
    with tabs[3]:
        st.subheader("🏆 Top 20 키워드")
        st.divider()
        for item in report["top_keywords"]:
            with st.expander(f"**{item['rank']}. {item['keyword']}** (사이트 {item['site_coverage']}개, {item['site_count']}회)"):
                for url in item.get('sites', []):
                    st.markdown(f"- [🔗 {url}]({url})")

