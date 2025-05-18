# -*- coding: utf-8 -*-
# Author : Dr. Songhee Kang
# Description : KOSTEC stat visualizer using Excel-based trend summary

import streamlit as st
import pandas as pd
import altair as alt
from streamlit_agraph import agraph, Node, Edge, Config
from collections import defaultdict
import os, io, zipfile
import datetime

# --- 1. 설정
st.set_page_config(page_title="한중과기협력센터 키워드 대시보드", layout="wide")

# --- 2. CSS 적용
def local_css(file_name):
    with open(file_name, "r", encoding="utf-8") as f:
        css_content = f.read()
    st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)

local_css("assets/css/main.css")

# --- 3. 사이드바 


input_date = st.sidebar.date_input("📆 수집 시작 날짜", value=datetime.today())
api_token = st.sidebar.text_input("🔐 API 토큰 입력", type="password")
if st.sidebar.button("🛰 주간 동향 수집 시작"):
    st.sidebar.success(f"✅ {input_date.strftime('%Y-%m-%d')}부터 수집 시작! (토큰 입력 완료: {'예' if api_token else '아니오'})")

st.sidebar.markdown("---")
snapshot_dates = ['20250418', '20250425', '20250502', '20250509', '20250516']
selected_snapshot = st.sidebar.selectbox("스냅샷 날짜 선택", snapshot_dates)
excel_path = f"assets/data/{selected_snapshot}_trend_summary.xlsx"

@st.cache_data
def load_excel_data(path):
    xls = pd.ExcelFile(path)
    df_summary = pd.read_excel(xls, sheet_name="Summary Table")
    df_sources = pd.read_excel(xls, sheet_name="Sources")
    df_exec = pd.read_excel(xls, sheet_name="Executive Summary")
    df_cooccur = pd.read_excel(xls, sheet_name="Cooccurrence")
    df_assoc = pd.read_excel(xls, sheet_name="Associations")
    return df_summary, df_sources, df_exec, df_cooccur, df_assoc

try:
    df_summary, df_sources, df_exec, df_cooccur, df_assoc = load_excel_data(excel_path)
except Exception as e:
    st.error(f"분석데이터 로드 실패: {e}")
    st.stop()

df_summary.columns = [col.strip() for col in df_summary.columns]
df_cooccur.columns = [col.strip() for col in df_cooccur.columns]

if "count" not in df_cooccur.columns:
    st.error("❌ 'count' 컬럼이 존재하지 않습니다.")
    st.write("📌 현재 컬럼:", df_cooccur.columns.tolist())
    st.stop()

# 존재하는 컬럼인지 확인
if "Keyword Count" not in df_summary.columns:
    st.error("❌ 'Keyword Count' 컬럼을 찾을 수 없습니다.")
    st.write("🔎 현재 컬럼 목록:", df_summary.columns.tolist())
    st.stop()
# 1. 엑셀에서 시트 불러오기
xls = pd.ExcelFile(excel_path)
df_summary = pd.read_excel(xls, sheet_name="Summary Table")
df_sources = pd.read_excel(xls, sheet_name="Sources")

# 2. 컬럼명 정리
df_summary.columns = [c.strip() for c in df_summary.columns]
df_sources.columns = [c.strip() for c in df_sources.columns]

# 3. URL 기준으로 날짜 매핑
df_merged = df_summary.merge(
    df_sources[["URL", "Publication Date"]],
    how="left",
    left_on="Source URL",
    right_on="URL"
)
# 4. 날짜 정리
df_merged["Publication Date"] = pd.to_datetime(df_merged["Publication Date"])
df_merged["Keyword"] = df_merged["Keyword"].astype(str)

# 5. 일자별 키워드 등장 횟수 집계
df_daily = df_merged.groupby(["Publication Date", "Keyword"]).size().reset_index(name="count")

# 6. 피벗 테이블로 일자 x 키워드 형태
df_pivot = df_daily.pivot_table(index="Publication Date", columns="Keyword", values="count", fill_value=0).sort_index()

# 7. 7일 이동 평균
df_rolling = df_pivot.rolling(window=7, min_periods=1).mean()

# --- 4. 탭 구성
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 빈도수", 
    "🕸 네트워크", 
    "🔍 연관어", 
    "🏆 보고서"
])
# --- TAB 1: 빈도수 통계
with tab1:
    st.subheader("키워드 Top 20")
    st.dataframe(df_summary.sort_values("Keyword Count", ascending=False).head(20), use_container_width=True)
    st.subheader("📈 7일 이동 평균 기반 키워드 트렌드")
    
    selected_keywords = st.multiselect("📌 키워드 선택", df_rolling.columns.tolist(), default=df_rolling.columns[:5])
    
    if selected_keywords:
        df_long = df_rolling[selected_keywords].reset_index().melt(id_vars="Publication Date", var_name="Keyword", value_name="7d_avg")
    
        chart = alt.Chart(df_long).mark_line().encode(
            x="Publication Date:T",
            y="7d_avg:Q",
            color="Keyword:N"
        ).properties(width=800, height=400)
    
        st.altair_chart(chart, use_container_width=True)

# --- TAB 2: 동시출현 네트워크
with tab2:
    st.subheader("🕸 동시출현 네트워크")

    layout_options = {
        "Force-Directed": {"physics": True, "hierarchical": False},
        "Hierarchical - LR": {
            "physics": False,
            "hierarchical": True,
            "layout": {"hierarchical": {"enabled": True, "direction": "LR"}}
        },
        "Hierarchical - TB": {
            "physics": False,
            "hierarchical": True,
            "layout": {"hierarchical": {"enabled": True, "direction": "TB"}}
        },
        "Circular (Random Seed)": {
            "physics": False,
            "hierarchical": False,
            "layout": {"randomSeed": 7}
        }
    }
    # 사용자 선택 드롭다운
    selected_layout = st.selectbox("📐 네트워크 레이아웃 선택", list(layout_options.keys()))
    layout_config = layout_options[selected_layout]
    
    # 노드/엣지 구성
    nodes = []
    for _, row in df_cooccur.iterrows():
        nodes.append(Node(id=row["source"], label=row["source"], font={"color": "white"}))
        nodes.append(Node(id=row["target"], label=row["target"], font={"color": "white"}))
    nodes = {n.id: n for n in nodes}.values()  # 중복 제거

    edges = [Edge(source=row.source, target=row.target, label=str(row.count)) for row in df_cooccur.itertuples()]

    # 네트워크 config 설정
    config = Config(
        width=900,
        height=700,
        nodeHighlightBehavior=True,
        highlightColor="#FFCC00",
        collapsible=True,
        node={"color": "#00BFFF"},
        edge={"color": "#AAAAAA"},
        **layout_config
    )

    try:
        agraph(nodes=nodes, edges=edges, config=config)
    except Exception as e:
        st.error(f"❌ 네트워크 그래프 렌더링 실패: {e}")


# --- TAB 3: 연관어
with tab3:
    st.subheader("연관어 Top 20")
    df_top_assoc = df_assoc.sort_values("count", ascending=False).head(20)
    col1, col2 = st.columns(2)
    for i, row in df_top_assoc.iterrows():
        target_col = col1 if i % 2 == 0 else col2
        target_col.write(f"🔹 {row['term']} ({row['count']}회)")

# --- TAB 4: 보고서
with tab4:
    st.subheader("Executive Summary")
    st.markdown(df_exec.iloc[0, 0])
