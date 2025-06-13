# -*- coding: utf-8 -*-
# Author : Prof. Dr. Songhee Kang
# Description : KOSTEC stat visualizer using Excel-based trend summary
# Date : 2025-04-14
# Last Update : 2025-06-14
# **** 중간보고(2025-05-30) 후 수정사항: 도넛그래프 추가, 연관검색어 센터링, 막대그래프 두께 조정, KOSTEC 로고 삽입
# **** 최종보고(2025-06-12) 후 수정사항: 스냅샷 시작과 끝을 지정해 기간별 보고서 리포트
# **** 최종보고(2025-06-12) 후 수정사항: 컬러팔레트 제공
# License : MIT

# --- 0. 라이브러리 임포트
import streamlit as st
import pandas as pd
import altair as alt
from streamlit_agraph import agraph, Node, Edge, Config
from collections import defaultdict
import os, io, zipfile
from datetime import date, datetime
import glob, time
from matplotlib_venn import venn2
import matplotlib.pyplot as plt
import numpy as np
from datetime import timedelta
import html
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.text_rank import TextRankSummarizer
import itertools

# --- 1. 설정
st.set_page_config(page_title="한중과기협력센터 키워드 대시보드", layout="wide")
col1, col2 = st.columns([2, 8])  # 로고:제목 비율 조정
st.markdown("""
    <style>
    .custom-subheader {
        font-size: 25px !important;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    </style>
""", unsafe_allow_html=True)
st.markdown("""
    <style>
    [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] {
        justify-content: center;
    }
    </style>
""", unsafe_allow_html=True)
st.markdown("""
<style>
/* 🎨 탭 공통 스타일 (글씨 보이게) */
[data-testid="stTabs"] button {
    font-size: 18px !important;
    font-family: "Noto Sans KR", sans-serif !important;
    padding: 10px 16px !important;
    margin-right: 6px;
    border-radius: 6px;
    color: black !important;   /* ✅ 글씨 색: 검정으로 변경 */
    font-weight: 500;
}

/* 🌗 각 탭에 그레이스케일 배경색 적용 */
[data-testid="stTabs"] button:nth-child(1) {
    background-color: #f0f0f0 !important;  /* 연회색 */
}
[data-testid="stTabs"] button:nth-child(2) {
    background-color: #d9d9d9 !important;
}
[data-testid="stTabs"] button:nth-child(3) {
    background-color: #bfbfbf !important;
}
[data-testid="stTabs"] button:nth-child(4) {
    background-color: #a6a6a6 !important;
}
[data-testid="stTabs"] button:nth-child(5) {
    background-color: #8c8c8c !important;
}

/* ✅ 선택된 탭 강조 스타일 */
[data-testid="stTabs"] button[aria-selected="true"] {
    border: 2px solid #444 !important;
    font-weight: bold !important;
    margin-bottom: 10px !important;
    box-shadow: 0px 2px 6px rgba(0,0,0,0.15);
}

/* 🧾 탭 내부 글자 크기 및 패딩 확대 */
.block-container {
    font-size: 17px !important;
    font-family: "Noto Sans KR", sans-serif !important;
    padding: 1.5rem 2rem !important;
}
</style>
""", unsafe_allow_html=True)

with col1:
    st.image("assets/images/logo.svg")  # 로고 파일 경로와 크기 설정

with col2:
    st.markdown("""
        <h1 style='font-size:35px; color:#044B9A; padding-top: 6px;'>
        한중과기협력센터 키워드 동향 대시보드
        </h1>
    """, unsafe_allow_html=True)

# --- 2. CSS 적용
def local_css(file_name):
    with open(file_name, "r", encoding="utf-8") as f:
        css_content = f.read()
    st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)

local_css("assets/css/main.css")

# --- 3. 사이드바 
color_palettes = [
    "viridis", "plasma", "magma", "inferno", "turbo",
    "category10", "category20", "accent", "dark2", "set1", "set2", "set3"
]

# 👉 사이드바에서 팔레트 선택
selected_palette = st.sidebar.selectbox("🎨 색상 팔레트 선택", color_palettes, index=0)
start_date = st.sidebar.date_input("🗓 시작일", value=date.today() - timedelta(days=7), key="start_date")
end_date = st.sidebar.date_input("⏳ 종료일", value=date.today(), key="end_date")

# 파일 목록 필터링 (중국 버전 기준)
snapshot_files = glob.glob("assets/data/*_trend_summary.xlsx")
snapshot_files_global = glob.glob("assets/data/*_trend_summary_en.xlsx")
snapshot_dates = [os.path.basename(f).split("_")[0] for f in snapshot_files]
snapshot_dates = [d for d in snapshot_dates if d.isdigit() and len(d) == 8]

# 날짜 필터링
selected_files = [
    f for f in snapshot_files
    if start_date.strftime("%Y%m%d") <= os.path.basename(f).split("_")[0] <= end_date.strftime("%Y%m%d")
]
selected_files_global = [
    f for f in snapshot_files_global
    if start_date.strftime("%Y%m%d") <= os.path.basename(f).split("_")[0] <= end_date.strftime("%Y%m%d")
]

st.sidebar.markdown("---")
st.sidebar.markdown("### 🛰 주간 동향 수집")

input_date = st.sidebar.date_input("📆 수집 시작 날짜", value=date.today(), key="expander_date")
current_date = input_date.strftime("%Y%m%d")
api_token = st.sidebar.text_input("🔐 Claude API 토큰", type="password", key="expander_api")
github_token = st.sidebar.text_input("🪪 GitHub Token", type="password", key="expander_git")

if st.sidebar.button("수집 시작(중국) 🚀 ", key="expander_run1"):
    with st.spinner(f"📡 {current_date} 기준 수집 중입니다... 최대 3~5분 소요."):
        try:
            import os
            import anthropic
            import re
            from io import StringIO
            from itertools import combinations
            from openpyxl import load_workbook

            client = anthropic.Anthropic(api_key=api_token)

            with open("assets/input/keywords.txt", "r", encoding="utf-8") as f:
                keywords = f.read().strip()
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
                        #st.write(prompt2)
                            # Claude API 호출
            message = client.messages.create(
        model="claude-3-7-sonnet-20250219",
        max_tokens=20000,
        temperature=1,
        messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt1
                            }
                        ]
                    }
                ]
      )

                        #st.write(prompt1)
            st.write("Step 1: RAG 수행 완료.")
                            # 결과 파싱
            text_data = message.content[0].text if isinstance(message.content, list) else message.content.text
            match = re.search(r"<excel_report>(.*?)</excel_report>", text_data, re.DOTALL)
            text_block = match.group(0) if match else None
            st.write("Step 2: 메시지 파싱 완료.")
            sheet1_start = text_block.find("<sheet1>")
            sheet1_end = text_block.find("</sheet1>")
            sheet2_start = text_block.find("<sheet2>")
            sheet2_end = text_block.find("</sheet2>")
            summary_start = text_block.find("<executive_summary>")
            summary_end = text_block.find("</executive_summary>")

            sheet1_text = text_block[sheet1_start:sheet1_end]
            sheet2_text = text_block[sheet2_start:sheet2_end]
            executive_summary_text = text_block[summary_start + len("<executive_summary>"):summary_end].strip()

            st.write("Step 3: 엑셀 시트 파싱 완료")

            sheet1_table_match = re.search(r"(\|.+?\|\n\|[-|]+\|\n(.+?))$", sheet1_text, re.DOTALL)
            sheet2_table_match = re.search(r"(\|.+?\|\n\|[-|]+\|\n(.+?))$", sheet2_text, re.DOTALL)

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
            st.write("Step 4: 동시출현 및 연관어 분석 완료")

            with pd.ExcelWriter(excel_path, engine="openpyxl", mode="w") as writer:
                df_summary.to_excel(writer, index=False, sheet_name="Summary Table")
                df_sheet2.to_excel(writer, index=False, sheet_name="Sources")
                pd.DataFrame({"Executive Summary": [executive_summary_text]}).to_excel(writer, index=False, sheet_name="Executive Summary")
                df_cooccur.to_excel(writer, index=False, sheet_name="Cooccurrence")
                df_association.to_excel(writer, index=False, sheet_name="Associations")

            st.sidebar.success(f"{current_date} 기준 주간 중국 동향 수집 및 저장 완료!")

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

if st.sidebar.button("수집 시작(글로벌) 🚀 ", key="expander_run2"):
    with st.spinner("⏳ 수집 중입니다. 최대 3~5분 소요..."):
        try:
            import os
            import anthropic
            import re
            from io import StringIO
            from itertools import combinations
            from openpyxl import load_workbook
                            # API 연결
            client = anthropic.Anthropic(api_key=api_token)
            with open("assets/input/en_keywords.txt", "r", encoding="utf-8") as f:
                en_keywords = f.read().strip()
            with open("assets/input/prompt.txt", "r", encoding="utf-8") as f:
                prompt_template = f.read()
                            # 변수 정의
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
        messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt2
                            }
                        ]
                    }
                ]
      )

                        #st.write(prompt1)
            st.write("Step 1: RAG 수행 완료.")

                            # 결과 파싱
            text_data = message.content[0].text if isinstance(message.content, list) else message.content.text
            match = re.search(r"<excel_report>(.*?)</excel_report>", text_data, re.DOTALL)
            text_block = match.group(0) if match else None
            st.write("Step 2: 메시지 파싱 완료.")
            sheet1_start = text_block.find("<sheet1>")
            sheet1_end = text_block.find("</sheet1>")
            sheet2_start = text_block.find("<sheet2>")
            sheet2_end = text_block.find("</sheet2>")
            summary_start = text_block.find("<executive_summary>")
            summary_end = text_block.find("</executive_summary>")

            sheet1_text = text_block[sheet1_start:sheet1_end]
            sheet2_text = text_block[sheet2_start:sheet2_end]
            executive_summary_text = text_block[summary_start + len("<executive_summary>"):summary_end].strip()
            sheet1_table_match = re.search(r"(\|.+?\|\n\|[-|]+\|\n(.+?))$", sheet1_text, re.DOTALL)
            sheet2_table_match = re.search(r"(\|.+?\|\n\|[-|]+\|\n(.+?))$", sheet2_text, re.DOTALL)

            sheet1_table_md = sheet1_table_match.group(1).strip() if sheet1_table_match else ""
            sheet2_table_md = sheet2_table_match.group(1).strip() if sheet2_table_match else ""

            df_sheet1 = pd.read_csv(StringIO(sheet1_table_md), sep="|", engine="python").dropna(axis=1, how="all")
            df_sheet2 = pd.read_csv(StringIO(sheet2_table_md), sep="|", engine="python").dropna(axis=1, how="all")
            st.write("Step 3: 엑셀 시트 파싱 완료")
                            # 저장
            excel_path = f"assets/data/{current_date}_trend_summary_en.xlsx"
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
            st.write("Step 4: 동시출현 및 연관어 분석 완료")
            with pd.ExcelWriter(excel_path, engine="openpyxl", mode="w") as writer:
                df_summary.to_excel(writer, index=False, sheet_name="Summary Table")
                df_sheet2.to_excel(writer, index=False, sheet_name="Sources")
                pd.DataFrame({"Executive Summary": [executive_summary_text]}).to_excel(writer, index=False, sheet_name="Executive Summary")
                df_cooccur.to_excel(writer, index=False, sheet_name="Cooccurrence")
                df_association.to_excel(writer, index=False, sheet_name="Associations")

            st.sidebar.success(f"{current_date} 기준 주간 글로벌 동향 수집 및 저장 완료!")

        except Exception as e:
            st.sidebar.error(f"❌ 수집 중 오류 발생: {e}")

        from github import Github
        repo_name = "kostec-stat/streamlit"
        file_path = f"assets/data/{current_date}_trend_summary_en.xlsx"

        try:
            g = Github(github_token)
            repo = g.get_repo(repo_name)

            with open(file_path, "rb") as f:
                content = f.read()
                path_in_repo = f"assets/data/{current_date}_trend_summary_en.xlsx"

            try:
                existing_file = repo.get_contents(path_in_repo)
                repo.update_file(existing_file.path, f"update {path_in_repo}", content, existing_file.sha)
            except Exception:
                repo.create_file(path_in_repo, f"add {path_in_repo}", content)

            st.success(f" {current_date} 기준 주간 동향 수집, 저장 및 GitHub 업로드 완료!")
        except Exception as upload_err:
            st.warning(f"⚠️ 수집은 완료되었으나 GitHub 업로드 실패: {upload_err}")

@st.cache_data
def load_excel_data(path):
    xls = pd.ExcelFile(path)
    df_summary = pd.read_excel(xls, sheet_name="Summary Table")
    df_sources = pd.read_excel(xls, sheet_name="Sources")
    df_exec = pd.read_excel(xls, sheet_name="Executive Summary")
    df_cooccur = pd.read_excel(xls, sheet_name="Cooccurrence")
    df_assoc = pd.read_excel(xls, sheet_name="Associations")
    return df_summary, df_sources, df_exec, df_cooccur, df_assoc

# 모든 파일에서 시트 불러오기
df_summary_all, df_sources_all, df_exec_all, df_cooccur_all, df_assoc_all = [], [], [], [], []

for path in selected_files:
    try:
        df_s, df_src, df_exe, df_co, df_as = load_excel_data(path)
        df_summary_all.append(df_s)
        df_sources_all.append(df_src)
        df_exec_all.append(df_exe)
        df_cooccur_all.append(df_co)
        df_assoc_all.append(df_as)
    except Exception as e:
        st.warning(f"⚠️ 파일 로딩 실패: {path}, 오류: {e}")

# 하나의 DataFrame으로 통합
if df_summary_all:
    df_summary = pd.concat(df_summary_all, ignore_index=True)
    df_sources = pd.concat(df_sources_all, ignore_index=True)
    df_exec = pd.concat(df_exec_all, ignore_index=True)
    df_cooccur = pd.concat(df_cooccur_all, ignore_index=True)
    df_assoc = pd.concat(df_assoc_all, ignore_index=True)
else:
    st.error("❌ 선택한 기간에 해당하는 데이터를 찾을 수 없습니다.")
    st.stop()

df_summary.columns = [col.strip() for col in df_summary.columns]
df_cooccur.columns = [col.strip() for col in df_cooccur.columns]
df_sources.columns = [col.strip() for col in df_sources.columns]

# 2. 존재 여부 확인
required_cols = {"URL", "Publication Date"}
missing_cols = required_cols - set(df_sources.columns)

if missing_cols:
    st.error(f"❌ df_sources에 다음 컬럼이 없습니다: {missing_cols}")
    st.write("📌 현재 컬럼 목록:", df_sources.columns.tolist())
    st.stop()
else:
    df_merged = df_summary.merge(
        df_sources[["URL", "Publication Date"]],
        how="left",
        left_on="Source URL",
        right_on="URL"
    )
    
if "count" not in df_cooccur.columns:
    st.error("❌ 'count' 컬럼이 존재하지 않습니다.")
    st.write("📌 현재 컬럼:", df_cooccur.columns.tolist())
    st.stop()

# 존재하는 컬럼인지 확인
if "Keyword Count" not in df_summary.columns:
    st.error("❌ 'Keyword Count' 컬럼을 찾을 수 없습니다.")
    st.write("🔎 현재 컬럼 목록:", df_summary.columns.tolist())
    st.stop()

# URL 기준으로 날짜 매핑
df_merged = df_summary.merge(
    df_sources[["URL", "Publication Date"]],
    how="left",
    left_on="Source URL",
    right_on="URL"
)
# 날짜 정리
df_merged["Publication Date"] = pd.to_datetime(df_merged["Publication Date"])
df_merged["Keyword"] = df_merged["Keyword"].astype(str)

# 일자별 키워드 등장 횟수 집계
df_daily = df_merged.groupby(["Publication Date", "Keyword"]).size().reset_index(name="count")

# 피벗 테이블로 일자 x 키워드 형태
df_pivot = df_daily.pivot_table(index="Publication Date", columns="Keyword", values="count", fill_value=0).sort_index()

# 7일 이동 평균
df_rolling = df_pivot.rolling(window=7, min_periods=1).mean()

# --- 4. 탭 구성
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 요약과 다운로드", 
    "🕸 동시출현과 연관어", 
    "🔍 빈도수 추적", 
    "🏆 Top20과 드릴다운",
    "🌐 글로벌 비교"
])
# --- TAB 1: 빈도수 통계
with tab1:
    st.markdown("<div class='custom-subheader'>📌 주요 요약 </div>", unsafe_allow_html=True)
    if not df_exec.empty and df_exec.shape[1] > 0:
        df_exec.columns = [c.strip() for c in df_exec.columns]
    # 모든 셀을 문자열로 합친 후, '1.' 이후 추출
        full_text = "\n".join(df_exec.iloc[:, 0].astype(str).tolist())
        start_index = full_text.find("1.")
        if start_index != -1:
            cleaned_summary = full_text[start_index:].strip()
            #try:
            #    parser = PlaintextParser.from_string(full_text, Tokenizer("chinese"))
            #    summarizer = TextRankSummarizer()
            #    summary_sentences = summarizer(parser.document, 5)  # 최대 5문장
                
            #    if summary_sentences:
            #        for i, sentence in enumerate(summary_sentences, 1):
            #            st.markdown(f"**{i}.** {sentence}")
            #   else:
            #        st.info("ℹ️ 요약할 내용이 충분하지 않습니다.")
            #except Exception as e:
            #    st.error(f"❌ 요약 처리 중 오류 발생: {e}")
            st.markdown(cleaned_summary)
        else:
            st.warning("⚠️ '1.'로 시작하는 본문 내용을 찾을 수 없습니다.")
    else:
        st.warning("⚠️ Executive Summary 시트가 비어 있거나 형식이 올바르지 않습니다.")

    st.markdown("<div class='custom-subheader'>📁 다운로드할 스냅샷 선택</div>", unsafe_allow_html=True)

    # 사용자가 선택할 수 있는 스냅샷 목록 구성 (기존 snapshot 파일 기준)
    all_snapshot_files = glob.glob("assets/data/*_trend_summary.xlsx")
    snapshot_options = sorted({os.path.basename(f).split("_trend_summary")[0] for f in all_snapshot_files}, reverse=True)
    
    selected_download_snapshot = st.selectbox("📅 다운로드할 날짜 선택", snapshot_options)
    
    col1, col2 = st.columns(2)
    with col1:
        china_file = f"assets/data/{selected_download_snapshot}_trend_summary.xlsx"
        try:
            with open(china_file, "rb") as f:
                st.download_button(
                    label=f"📥 {selected_download_snapshot} 중국 주간동향 엑셀 다운로드",
                    data=f.read(),
                    file_name=f"{selected_download_snapshot}_trend_summary.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        except Exception as e:
            st.warning(f"⚠️ 중국 스냅샷 파일을 열 수 없습니다: {e}")
    
    with col2:
        global_file = f"assets/data/{selected_download_snapshot}_trend_summary_en.xlsx"
        try:
            with open(global_file, "rb") as f:
                st.download_button(
                    label=f"📥 {selected_download_snapshot} 글로벌 주간동향 엑셀 다운로드",
                    data=f.read(),
                    file_name=f"{selected_download_snapshot}_trend_summary_en.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        except Exception as e:
            st.warning(f"⚠️ 글로벌 스냅샷 파일을 열 수 없습니다: {e}")
      
# --- TAB 2: 동시출현 네트워크
with tab2:
    if "graph_first_rendered" not in st.session_state:
        st.session_state.graph_first_rendered = False

    if not st.session_state.graph_first_rendered:
        # 강제로 레이아웃을 한 번 바꿨다가 원래대로 돌림
        st.session_state.graph_first_rendered = True
        st.rerun()
        
    st.markdown("<div class='custom-subheader'>🕸 동시출현 네트워크</div>", unsafe_allow_html=True)

    layout_options = {
        "Static (좌표고정)": {
            "improvedLayout": False,
            "physics": False,
            "hierarchical": False,
            "staticGraph": True
        },
        "Circular (Centered)": {
            "improvedLayout": True,
            "randomSeed": 42,
            "physics": False,
            "hierarchical": False,
            "layout": {"hierarchical": {"enabled": False}},
        },
        "Force-Directed (Spring)": {
            "improvedLayout": True,
            "physics": False,
            "hierarchical": False,
        },
        "Random": {
            "improvedLayout": False,
            "physics": False,
            "hierarchical": False,
            "layout": {"randomSeed": 42},
        },
        "Grid": {
            "improvedLayout": False,
            "physics": False,
            "hierarchical": False,
            "layout": {"grid": {"enabled": True}},
        },
        "Hierarchical - LR": {
            "improvedLayout": True,
            "randomSeed": 42,
            "physics": False,
            "hierarchical": True,
            "layout": {"hierarchical": {"enabled": True, "direction": "LR"}}
        },
        "Hierarchical - RL": {
            "improvedLayout": True,
            "randomSeed": 42,
            "physics": False,
            "hierarchical": True,
            "layout": {"hierarchical": {"enabled": True, "direction": "RL"}}
        },
        "Hierarchical - TB": {
            "improvedLayout": True,
            "randomSeed": 42,
            "physics": False,
            "hierarchical": True,
            "layout": {"hierarchical": {"enabled": True, "direction": "TB"}}
        },
        "Hierarchical - BT": {
            "improvedLayout": True,
            "randomSeed": 42,
            "physics": False,
            "hierarchical": True,
            "layout": {"hierarchical": {"enabled": True, "direction": "BT"}}
        }
    }

    # 📌 고정 회색 스케일 팔레트
    gray_palette = [
        "#111111", "#2c2c2c", "#444444", "#666666", "#888888",
        "#aaaaaa", "#cccccc", "#dddddd", "#eeeeee"
    ]
    color_cycle = itertools.cycle(gray_palette)
    
    # 1. 레이아웃 구성
    selected_layout = st.selectbox("📐 네트워크 레이아웃 선택", list(layout_options.keys()))
    layout_config = layout_options[selected_layout]
    
    # 2. 노드 구성
    unique_nodes = set(df_cooccur["source"]).union(set(df_cooccur["target"]))
    node_color_map = {node: next(color_cycle) for node in unique_nodes}
    
    nodes = [
        Node(id=node, label=node, color=node_color_map[node], font={"color": "darkgray"})
        for node in unique_nodes
    ]
    
    # 4. 엣지 구성
    edges = [
        Edge(source=row.source, target=row.target, label=str(row.count))
        for row in df_cooccur.itertuples()
    ]
    
    # 5. 그래프 구성 옵션
    config = Config(
        width=800,
        height=600,
        layout=layout_config,
        physics=True,
        staticGraph=False
    )
    
    # 6. 렌더링
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

# --- TAB 3: 빈도수 추적
with tab3:
    st.markdown("<div class='custom-subheader'>📈 7일 이동 평균 기반 키워드 트렌드</div>", unsafe_allow_html=True)

    chart_type = st.selectbox("🎨 그래프 유형 선택", ["막대그래프", "선그래프", "도넛형 그래프"])
    selected_keywords = st.multiselect("📌 키워드 선택", df_rolling.columns.tolist(), default=df_rolling.columns[:5])
    color_scheme = alt.Scale(scheme=selected_palette)
    
    if selected_keywords:
      df_long = df_rolling[selected_keywords].reset_index().melt(
        id_vars="Publication Date",
        var_name="Keyword",
        value_name="7d_avg"
      )

      if chart_type == "선그래프":
        chart = alt.Chart(df_long).mark_line(point=True).encode(
            x="Publication Date:T",
            y="7d_avg:Q",
            color=alt.Color("Keyword:N", scale=color_scheme)
        ).properties(width=800)
        st.altair_chart(chart, use_container_width=True)

      elif chart_type == "막대그래프":
        chart = alt.Chart(df_long).mark_bar(size=30).encode(
            x=alt.X("Publication Date:T", axis=alt.Axis(labelAngle=-45)),
            y="7d_avg:Q",
            color=alt.Color("Keyword:N", scale=color_scheme),
            tooltip=["Publication Date:T", "Keyword:N", "7d_avg:Q"]
        ).properties(width=800)
        st.altair_chart(chart, use_container_width=True)

      elif chart_type == "도넛형 그래프":
        st.markdown("### 🍩 선택 키워드 비중")
        # 최근 7일 기준 데이터 집계
        #latest_date = df_long["Publication Date"].max()
        #start_date = latest_date - timedelta(days=6)
        #recent_data = df_long[df_long["Publication Date"] >= start_date]

        # 키워드별 총합
        keyword_totals = df_long.groupby("Keyword")["7d_avg"].sum()
        keyword_totals = keyword_totals[keyword_totals > 0]

        if keyword_totals.empty:
            st.warning("📭 유효한 키워드 데이터가 없습니다.")
        else:
            # Altair용 DataFrame 생성
            labels = keyword_totals.index.tolist()
            values = keyword_totals.values.tolist()
            label_texts = [f"{kw} ({val:.2f})" for kw, val in zip(labels, values)]
            keyword_totals_df = pd.DataFrame({
                "Keyword": labels,
                "Value": values,
                "LabelText": label_texts
            })
        
            donut = alt.Chart(keyword_totals_df).mark_arc(innerRadius=50, outerRadius=100).encode(
                theta=alt.Theta(field="Value", type="quantitative"),
                color=alt.Color(field="Keyword", scale=color_scheme),
                tooltip=[alt.Tooltip("Keyword"), alt.Tooltip("Value")]
            )
            st.altair_chart(donut, use_container_width=True)
            
# --- TAB 4: 키워드 Top 20 상세 보기 포함
with tab4:
    st.markdown("<div class='custom-subheader'>📌 키워드 Top 20 (상세 보기)</div>", unsafe_allow_html=True)

    df_summary.columns = [col.strip() for col in df_summary.columns]

    # ✅ groupby로 Count 집계 + 대표 요약 + 링크 모음
    grouped = (
        df_summary
        .groupby("Keyword")
        .agg({
            "Keyword Count": "sum",
            "Short Summary": lambda x: x.dropna().iloc[0] if not x.dropna().empty else "",
            "Detailed Summary": lambda x: x.dropna().iloc[0] if not x.dropna().empty else "",
            "Source URL": lambda urls: list(set(filter(lambda u: isinstance(u, str), urls)))
        })
        .reset_index()
        .sort_values("Keyword Count", ascending=False)
        .head(20)
    )

    table_data = []
    for i, row in grouped.iterrows():
        index = i + 1
        keyword = row["Keyword"]
        count = row["Keyword Count"]

        summary_html = f'<span title="{html.escape(row["Detailed Summary"])}">{html.escape(row["Short Summary"])}' \
                       f'</span>'

        # 여러 링크 모아서 한 줄에 표시
        urls = row["Source URL"]

        # 문자열인 경우 (단일 URL), 리스트로 감쌈
        if isinstance(urls, str):
            urls = [urls]
        elif not isinstance(urls, list):
            urls = []
        
        # 링크 HTML 생성
        link_html = f'<a href="{urls[0]}" target="_blank">🔗 link</a>'
        table_data.append((index, keyword, count, summary_html, link_html))
        
    df_display = pd.DataFrame(table_data, columns=["#", "Keyword", "Count", "Summary", "Sources"])
    st.markdown(df_display.to_html(escape=False, index=False), unsafe_allow_html=True)
    
with tab5:
    st.markdown("<div class='custom-subheader'>🏅 중국 vs 글로벌 키워드 순위 비교</div>", unsafe_allow_html=True)

    # 1. 키워드 매핑 테이블 생성
    with open("assets/input/keywords.txt", "r", encoding="utf-8") as f:
        zh_keywords = [line.strip() for line in f if line.strip()]
    with open("assets/input/en_keywords.txt", "r", encoding="utf-8") as f:
        en_keywords = [line.strip() for line in f if line.strip()]

    df_map = pd.DataFrame({
        "zh_keyword": zh_keywords,
        "en_keyword": en_keywords
    })
    #st.write(df_map)
    # 2. 국내 Summary Table
    df_summary.columns = [col.strip() for col in df_summary.columns]
    zh_set = set(df_summary["Keyword"])

    # 3. 글로벌 Summary Table
    df_summary_global_all = []

    for path in selected_files_global:
        try:
            xls = pd.ExcelFile(path)
            df_s = pd.read_excel(xls, sheet_name="Summary Table")
            df_summary_global_all.append(df_s)
        except Exception as e:
            st.warning(f"⚠️ 파일 로딩 실패: {path}, 오류: {e}")
    
    # 하나의 DataFrame으로 통합
    if df_summary_global_all:
        df_global_summary = pd.concat(df_summary_global_all, ignore_index=True)
    else:
        st.error("❌ 선택한 기간에 해당하는 데이터를 찾을 수 없습니다.")
        st.stop()
    
    df_global_summary.columns = [col.strip() for col in df_global_summary.columns]

    # 4. 글로벌 키워드 매핑 (영문 → 중문)
    map_dict = {
        en.strip().lower(): zh.strip()
        for en, zh in zip(df_map["en_keyword"], df_map["zh_keyword"])
    }
    
    # df_global_summary의 Keyword도 정규화해서 매핑
    df_global_summary["zh_keyword"] = df_global_summary["Keyword"].str.strip().str.lower().map(map_dict)
    
    matched_zh = set(df_global_summary["zh_keyword"].dropna())
    # 1. 국내 순위표
    df_rank_china = (
        df_summary
        .groupby("Keyword", as_index=False)["Keyword Count"].sum()
        .assign(Rank_China=lambda df: df["Keyword Count"].rank(ascending=False, method="min").astype(int))
        .sort_values("Rank_China")
        [["Rank_China", "Keyword", "Keyword Count"]]
    )
    
    # 2. 글로벌 순위표 (zh_keyword 기준)
    df_rank_global = (
        df_global_summary
        .groupby("zh_keyword", as_index=False)["Keyword Count"].sum()
        .assign(Rank_Global=lambda df: df["Keyword Count"].rank(ascending=False, method="min").astype(int))
        .sort_values("Rank_Global")
        .rename(columns={"zh_keyword": "Keyword"})
        [["Rank_Global", "Keyword", "Keyword Count"]]
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🇨🇳 중국 키워드 순위 (Rank_China)")
        html_china = df_rank_china.reset_index(drop=True).to_html(index=False, escape=False)
        st.markdown(html_china, unsafe_allow_html=True)

    with col2:
        st.markdown("#### 🌍 글로벌 키워드 순위 (Rank_Global)")
        html_global = df_rank_global.reset_index(drop=True).to_html(index=False, escape=False)
        st.markdown(html_global, unsafe_allow_html=True)
