이 대시보드 애플리케이션은 한중과기협력센터(KOSTEC)의 주간 키워드 동향을 시각화하는 전문 분석 도구입니다. 주요 기능과 구성 요소를 설명드리겠습니다.

## 필수 API 키 설정

- **Claude API Key**: Anthropic의 Claude 3 모델(7B 버전)을 사용하기 위한 인증키 
- **GitHub API Token**: `kostec-stat` 조직 내 저장소에 자동 커밋을 위해 필요
- 두 키 모두 Streamlit Secrets 관리 또는 환경 변수에 등록해야 하며, `kostec-stat` 조직 구성원만 접근 가능


## 주요 기능

### 1. 데이터 수집 시스템

```python
# 중국/글로벌 소스 분리 수집
if st.sidebar.button("🚀 수집 시작(중국)"):  # 중국 현지 사이트 대상
if st.sidebar.button("🚀 수집 시작(글로벌)"):  # 글로벌 사이트 대상
```

- 실시간 RAG(Retrieval-Augmented Generation) 기반 데이터 크롤링
- 7일 주기 자동 스냅샷 생성 및 버전 관리[^1]


### 2. 시각화 대시보드

| 기능 | 설명 | 기술 스택 |
| :-- | :-- | :-- |
| 동시출현 네트워크 | 키워드 간 연관 관계 그래프 | `streamlit-agraph` |
| 주간 트렌드 | 7일 이동평균 기반 시계열 차트 | `altair` |
| 키워드 순위 | 중국-글로벌 비교 분석 | `pandas` |

### 3. 분석 엔진

```python
# 키워드 동시출현 분석 로직
for kw1, kw2 in combinations(sorted(set(present_keywords)), 2):
    cooccur_counter[(kw1, kw2)] += 1
```

- 자연어 처리 기반 키워드 추출
- 동시출현(co-occurrence) 빈도 분석[^1]
- TF-IDF 가중치 적용 연관어 분석[^1]


## 배포 환경

```bash
# 의존성 설치
pip install -r requirements.txt  # streamlit==1.35.0 pandas==2.2.2 anthropic==0.25.0
```

- **플랫폼**: Streamlit Community Cloud
- **Python**: 3.10 이상
- **아키텍처**: 모듈러 디자인(데이터 수집 ↔ 시각화 분리)


## 프로젝트 구조

```
assets/
├── input/      # 키워드/사이트 목록
├── data/       # 엑셀 분석 결과물
└── css/        # 사용자 정의 스타일
main.py         # 메인 애플리케이션
```

GitHub 저장소 설정 시 `secrets.toml` 파일에 API 키를 등록하고, 조직 저장소 권한을 `kostec-stat/streamlit`으로 설정해야 합니다[^1]. 배포 전 반드시 `assets/data` 디렉토리에 쓰기 권한을 확인해야 합니다.

## 입력 변경

```
assets/
├── input/      # 키워드/사이트 목록
```

- **키워드**: keyword.txt, en_keyword.txt 파일을 변경 및 추가하시면 됩니다. 
- **사이트**: sites.txt 파일을 수정하여 수집대상 신뢰할수 있는 고품질 사이트 목록을 완성하세요.
- **프롬프트**: 핵심 프롬프트를 변경할 경우 개발자에게 연락후 수정 및 검증하세요. 

<div style="text-align: center">⁂ 2025년 6월 6일, 한국공학대 강송희 작성. MIT 라이선스를 따릅니다. ⁂</div>

