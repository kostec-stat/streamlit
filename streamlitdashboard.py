# -*- coding: utf-8 -*-
# Author : Dr. Songhee Kang
# Description : KOSTEC stat visualizer using Excel-based trend summary

import streamlit as st
import pandas as pd
import altair as alt
from streamlit_agraph import agraph, Node, Edge, Config
from collections import defaultdict
import os, io, zipfile

# --- 1. 설정
st.set_page_config(page_title="\ud83d\udcc8 \ud55c\uc911\uacfc\uae30\ud611\ub825\uc13c\ud130 \ud0a4\uc6cc\ub4dc \ub370\uc2dc\ubcf4\ub4dc", layout="wide")

# --- 2. CSS 적용
def local_css(file_name):
    with open(file_name, "r", encoding="utf-8") as f:
        css_content = f.read()
    st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)

local_css("assets/css/main.css")

# --- 3. 파일 선택 및 로딩
snapshot_dates = ['20250418', '20250425', '20250502', '20250509', '20250518']
selected_snapshot = st.sidebar.selectbox("\uc2a4\ub0e5\uc0f7 \ub0a0\uc9dc \uc120\ud0dd", snapshot_dates)
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
    st.error(f"\uc5d0\ud1a0\uacac \ud30c\uc77c \ub85c\ub4dc \uc2e4\ud328: {e}")
    st.stop()

# --- 4. 탭 구성
tab1, tab2, tab3, tab4 = st.tabs(["\ud83d\udcca \ube44\ub3c4\uc218", "\ud83d\udd78 \ub124\ud2b8\uc6cc\ud06c", "\ud83d\udd0d \uc5f0\uad00\uc5b4", "\ud83c\udfc6 \ubcf4\uace0\uc11c"])

# --- TAB 1: 빈도수 통계
with tab1:
    st.subheader("\ud0a4\uc6cc\ub4dc \ube44\ub3c4\uc218 Top 20")
    st.dataframe(df_summary.sort_values("Keyword Count", ascending=False).head(20), use_container_width=True)

# --- TAB 2: 동시출현 네트워크
with tab2:
    st.subheader("\ub3d9\uc2dc\ucd9c\ud604 \uadf8\ub798\ud504")

    config = Config(width=900, height=700, directed=False, physics=True,
                    hierarchical=False, nodeHighlightBehavior=True, highlightColor="#FFCC00",
                    collapsible=True, node={"color": "#00BFFF"}, edge={"color": "#AAAAAA"})

    top_links = df_cooccur.sort_values("count", ascending=False).head(100)
    top_nodes = pd.unique(top_links[['source', 'target']].values.ravel())

    nodes = [Node(id=kw, label=kw, font={"color": "white"}) for kw in top_nodes]
    edges = [Edge(source=row['source'], target=row['target'], label=str(row['count'])) for _, row in top_links.iterrows()]

    agraph(nodes=nodes, edges=edges, config=config)

# --- TAB 3: 연관어
with tab3:
    st.subheader("\ud0a4\uc6cc\ub4dc \uc5f0\uad00\uc5b4 Top 20")
    df_top_assoc = df_assoc.sort_values("count", ascending=False).head(20)
    col1, col2 = st.columns(2)
    for i, row in df_top_assoc.iterrows():
        target_col = col1 if i % 2 == 0 else col2
        target_col.write(f"🔹 {row['term']} ({row['count']}회)")

# --- TAB 4: 보고서
with tab4:
    st.subheader("\ubcf4\uace0\uc11c Executive Summary")
    st.markdown(df_exec.iloc[0, 0])
