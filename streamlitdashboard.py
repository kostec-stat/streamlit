# -*- coding: utf-8 -*-
# Author : Dr. Songhee Kang
# Description : KOSTEC stat visualizer using Excel-based trend summary

import streamlit as st
import pandas as pd
import altair as alt
from streamlit_agraph import agraph, Node, Edge, Config
from collections import defaultdict
import os, io, zipfile
from datetime import date, datetime
import glob, time

# --- 1. 설정
st.set_page_config(page_title="한중과기협력센터 키워드 대시보드", layout="wide")

# --- 2. CSS 적용
def local_css(file_name):
    with open(file_name, "r", encoding="utf-8") as f:
        css_content = f.read()
    st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)

local_css("assets/css/main.css")

# --- 3. 사이드바 
input_date = st.sidebar.date_input("📆 수집 시작 날짜", value=date.today())
api_token = st.sidebar.text_input("🔐 수집 암호 입력", type="password")
github_token = st.sidebar.text_input("🪪 업로드 암호 입력", type="password")

current_date = input_date.strftime("%Y%m%d")

if st.sidebar.button("🛰 주간 동향 수집 시작"):
    with st.spinner("⏳ 주간 동향을 수집 중입니다. 최대 3~5분 정도 소요될 수 있습니다..."):
        try:
            import os
            import anthropic
            import re
            from io import StringIO
            from itertools import combinations
            from openpyxl import load_workbook
       
                # API 연결
            client = anthropic.Anthropic(api_key=api_token)
        
            with open("assets/input/keywords.txt", "r", encoding="utf-8") as f:
                keywords = f.read().strip()
            with open("assets/input/en_keywords.txt", "r", encoding="utf-8") as f:
                en_keywords = f.read().strip()
            with open("assets/input/sites.txt", "r", encoding="utf-8") as f:
                source_sites = f.read().strip()
            with open("assets/input/prompt.txt", "r", encoding="utf-8") as f:
                prompt_template = f.read()
               
                # 변수 정의
            prompt1 = prompt_template.format(
                keywords=keywords,        # 문자열 또는 리스트 join한 값
                current_date=current_date,        # '20250518' 같은 문자열
                source_sites=source_sites        # 문자열 또는 사이트 목록
            )
            #st.write(prompt1)
            prompt2 = prompt_template.format(
                keywords=en_keywords,        # 문자열 또는 리스트 join한 값
                current_date=current_date,        # '20250518' 같은 문자열
                source_sites="*"        # 문자열 또는 사이트 목록
            )
            #st.write(prompt2)
                # Claude API 호출
            message = client.messages.create(
                model="claude-3-7-sonnet-20250219",
                max_tokens=20000,
                temperature=1,
                messages=[{"role": "user", "content": [{"type": "text", "text": prompt1}]}]
            )
    
            #st.write(prompt1)
            
                # 결과 파싱
            text_data = message.content[0].text if isinstance(message.content, list) else message.content.text
            match = re.search(r"<excel_report>(.*?)</excel_report>", text_data, re.DOTALL)
            text_block = match.group(0) if match else None
        
            sheet1_start = text_block.find("<sheet1>")
            sheet1_end = text_block.find("</sheet1>")
            sheet2_start = text_block.find("<sheet2>")
            sheet2_end = text_block.find("</sheet2>")
            summary_start = text_block.find("<executive_summary>")
            summary_end = text_block.find("</executive_summary>")
        
            sheet1_text = text_block[sheet1_start:sheet1_end]
            sheet2_text = text_block[sheet2_start:sheet2_end]
            executive_summary_text = text_block[summary_start + len("<executive_summary>"):summary_end].strip()
        
            sheet1_table_match = re.search(r"(\|.+?\|\n\|[-|]+\|(?:\n\|.*?\|)+)", sheet1_text)
            sheet2_table_match = re.search(r"(\|.+?\|\n\|[-|]+\|(?:\n\|.*?\|)+)", sheet2_text)
        
            sheet1_table_md = sheet1_table_match.group(1).strip() if sheet1_table_match else ""
            sheet2_table_md = sheet2_table_match.group(1).strip() if sheet2_table_match else ""
        
            df_sheet1 = pd.read_csv(StringIO(sheet1_table_md), sep="|", engine="python").dropna(axis=1, how="all")
            df_sheet2 = pd.read_csv(StringIO(sheet2_table_md), sep="|", engine="python").dropna(axis=1, how="all")
        
                # 저장
            excel_path = f"assets/data/{current_date}_trend_summary.xlsx"
                # 동시출현 및 연관어 분석
            df_summary = df_sheet1.iloc[1:].reset_index(drop=True)
            df_summary.columns = [col.strip() for col in df_summary.columns]
            keywords_list = [kw.strip() for kw in df_summary["Keyword"].dropna().unique().tolist()]
        
            cooccur_counter = defaultdict(int)
            association_counter = defaultdict(int)
            for _, row in df_summary.iterrows():
                text = (str(row.get("Detailed Summary", "")) + " " + str(row.get("Short Summary", ""))).lower()
                present_keywords = [kw for kw in keywords_list if kw.lower() in text]
                for kw1, kw2 in combinations(sorted(set(present_keywords)), 2):
                    cooccur_counter[(kw1, kw2)] += 1
                for kw in present_keywords:
                    association_counter[kw] += 1
        
            df_cooccur = pd.DataFrame([{"source": k1, "target": k2, "count": v} for (k1, k2), v in cooccur_counter.items()])
            df_association = pd.DataFrame([{"term": k, "count": v} for k, v in association_counter.items()])
        
            with pd.ExcelWriter(excel_path, engine="openpyxl", mode="w") as writer:
                df_summary.to_excel(writer, index=False, sheet_name="Summary Table")
                df_sheeet2.to_excel(writer, index=False, sheet_name="Sources")
                pd.DataFrame({"Executive Summary": [executive_summary_text]}).to_excel(writer, index=False, sheet_name="Executive Summary")
                df_cooccur.to_excel(writer, index=False, sheet_name="Cooccurrence")
                df_association.to_excel(writer, index=False, sheet_name="Associations")
        
            st.sidebar.success(f"{current_date} 기준 주간 동향 수집 및 저장 완료!")
        
        except Exception as e:
        	st.sidebar.error(f"❌ 수집 중 오류 발생: {e}")
            
        from github import Github
        repo_name = "kostec-stat/streamlit"
        file_path = f"assets/data/{current_date}_trend_summary.xlsx"
            
        try:
            g = Github(github_token)
            repo = g.get_repo(repo_name)
            
            with open(file_path, "rb") as f:
                content = f.read()
            path_in_repo = f"assets/data/{current_date}_trend_summary.xlsx"
            
            try:
                existing_file = repo.get_contents(path_in_repo)
                repo.update_file(existing_file.path, f"update {path_in_repo}", content, existing_file.sha)
            except Exception:
                repo.create_file(path_in_repo, f"add {path_in_repo}", content)
            
            st.success(f" {current_date} 기준 주간 동향 수집, 저장 및 GitHub 업로드 완료!")
        except Exception as upload_err:
            st.warning(f"⚠️ 수집은 완료되었으나 GitHub 업로드 실패: {upload_err}")
                
st.sidebar.markdown("---")
snapshot_files = glob.glob("assets/data/*_trend_summary.xlsx")
snapshot_dates = sorted({os.path.basename(f).split("_")[0] for f in snapshot_files})
selected_snapshot = st.sidebar.selectbox("📅 스냅샷 날짜 선택", snapshot_dates)
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
    "📊 주간요약과 다운로드", 
    "🕸 동시출현과 연관어", 
    "🔍 빈도수 추적", 
    "🏆 Top20과 드릴다운"
])
# --- TAB 1: 빈도수 통계
with tab1:
    st.subheader("📌 5줄 요약")
    df_exec = df_exec.iloc[1:].reset_index(drop=True)
    st.markdown(df_exec.iloc[0, 0])

    download_path = f"assets/data/{selected_snapshot}_trend_summary.xlsx"
    try:
        with open(download_path, "rb") as f:
            st.download_button(
                label="📥 선택된 스냅샷 엑셀 다운로드",
                data=f.read(),
                file_name=f"{selected_snapshot}_trend_summary.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    except Exception as e:
        st.warning(f"⚠️ 다운로드 파일을 열 수 없습니다: {e}")

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

    st.subheader("연관어 Top 20")
    df_top_assoc = df_assoc.sort_values("count", ascending=False).head(20)
    col1, col2 = st.columns(2)
    for i, row in df_top_assoc.iterrows():
        target_col = col1 if i % 2 == 0 else col2
        target_col.write(f"🔹 {row['term']} ({row['count']}회)")

# --- TAB 3: 연관어
with tab3:
    st.subheader("📈 7일 이동 평균 기반 키워드 트렌드")

    # 드롭다운: 그래프 유형 선택
    chart_type = st.selectbox("🎨 그래프 유형 선택", ["막대그래프", "선그래프"])
    
    # 키워드 선택
    selected_keywords = st.multiselect("📌 키워드 선택", df_rolling.columns.tolist(), default=df_rolling.columns[:5])
    
    if selected_keywords:
        df_long = df_rolling[selected_keywords].reset_index().melt(
            id_vars="Publication Date",
            var_name="Keyword",
            value_name="7d_avg"
        )
    
        # 그래프 생성
        if chart_type == "선그래프":
            chart = alt.Chart(df_long).mark_line(point=True).encode(
                x="Publication Date:T",
                y="7d_avg:Q",
                color="Keyword:N"
            )
        else:  # 막대그래프
            chart = alt.Chart(df_long).mark_bar().encode(
                x="Publication Date:T",
                y="7d_avg:Q",
                color="Keyword:N",
                tooltip=["Publication Date:T", "Keyword:N", "7d_avg:Q"]
            )
    
        st.altair_chart(chart.properties(width=800, height=400), use_container_width=True)

# --- TAB 4: 보고서
with tab4:
    st.subheader("📌 키워드 Top 20 (상세 보기 포함)")

    top_df = df_summary.sort_values("Keyword Count", ascending=False).head(20).copy()
    top_df = top_df.reset_index(drop=True)
    
    # 컬럼명 정리
    top_df.columns = [c.strip() for c in top_df.columns]
    
    # 새 테이블 만들기
    table_data = []
    
    for i, row in top_df.iterrows():
        index = i + 1
        keyword = row["Keyword"]
        count = row["Keyword Count"]
        # 링크 열기 (새 탭)
        link_html = f'<a href="{row["Source URL"]}" target="_blank">🔗 링크</a>'
    
        # 툴팁 Summary
        short = row["Short Summary"]
        detailed = row["Detailed Summary"]
        summary_html = f'<span title="{detailed}">{short}</span>'
    
        table_data.append((index, keyword, count, summary_html, link_html))
    
    # 표를 DataFrame으로 재생성 (표시용)
    df_display = pd.DataFrame(table_data, columns=["#", "Keyword", "Count", "Summary", "Source"])
    
    # st.markdown의 unsafe_allow_html로 링크와 툴팁 허용
    st.markdown(df_display.to_html(escape=False, index=False), unsafe_allow_html=True)
