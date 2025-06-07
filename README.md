# KOSTEC 주간 키워드 동향 대시보드

## 1. 소개 (Introduction)
한중과학기술협력센터(KOSTEC)의 **주간 키워드 동향 대시보드**는 한∙중 양국의 과학기술 분야 이슈를 추적하기 위해 개발된 **전문 분석 도구**입니다. 이 대시보드는 최신 **자연어 처리** 기술과 **데이터 시각화**를 접목하여, 매주 수집된 키워드들의 트렌드와 상관관계를 한눈에 보여줍니다. 사용자들은 본 도구를 통해 한중 과학기술 동향을 모니터링하고 **키워드 간 연관성**, **주간 변화 추세**, **국가별 이슈 비교** 등의 인사이트를 얻을 수 있습니다. 본 매뉴얼에서는 대시보드의 주요 기능, 구성 요소, 설정 방법에 대해 자세히 설명합니다.

## 2. 시스템 요구 사항 및 초기 설정 (System Requirements and Setup)

### 2.1 필수 API 키 설정 (Required API Keys)
- **Claude API Key** – Anthropic사의 Claude 3 모델(7B 버전)에 접근하기 위한 키입니다.
- **GitHub API Token** – 수집된 데이터의 자동 버전 관리에 사용됩니다.

Streamlit Secrets 또는 환경 변수에 아래와 같이 등록:
```toml
CLAUDE_API_KEY="your_claude_key"
GITHUB_TOKEN="your_github_token"
```

### 2.2 애플리케이션 설치 및 환경 구성 (Installation and Dependencies)
```bash
pip install -r requirements.txt 
# 예: streamlit==1.35.0, pandas==2.2.2, anthropic==0.25.0
```
- 플랫폼: Streamlit Community Cloud
- Python 버전: 3.10 이상
- 아키텍처: 모듈형 디자인 (데이터 수집 ↔ 시각화 분리)

## 3. 주요 기능 및 사용 방법 (Key Features and Usage)

### 3.1 데이터 수집 시스템 (Data Collection System)
- `🚀 수집 시작(중국)` → 중국 소스 대상 실시간 크롤링
- `🚀 수집 시작(글로벌)` → 글로벌 소스 대상 실시간 크롤링
- RAG 기반 자연어 처리 및 키워드 추출
- 주간 스냅샷 생성 및 GitHub 커밋으로 버전 관리

### 3.2 시각화 대시보드 (Visualization Dashboard)
#### 3.2.1 동시출현 네트워크 (Co-occurrence Network Graph)
- 키워드 간 연관 관계 시각화 (streamlit-agraph)
- 노드 및 에지의 인터랙션 지원 (드래그, 확대/축소 등)

#### 3.2.2 주간 트렌드 (Weekly Trend Chart)
- 7일 이동 평균 기반 키워드 빈도 시계열 차트 (Altair)
- 주요 키워드 추이 변화 시각화

#### 3.2.3 키워드 순위 비교 (Keyword Ranking Comparison)
- 중국 vs 글로벌 키워드 TOP 순위 비교 (pandas 기반)
- 교집합/차집합 키워드 분석 가능

### 3.3 분석 엔진 (Analysis Engine)
- LLM 기반 자연어 키워드 추출 (Claude 3 + 프롬프트)
- 키워드 동시출현 빈도 분석 (Python combinations)
- TF-IDF 가중치 기반 키워드 중요도 계산

## 4. 배포 및 실행 가이드 (Deployment and Execution)

### 4.1 Streamlit Cloud 배포
- Secrets 설정 필수
- GitHub push 권한 필요
- 저장소에 커밋 → 자동 재배포

### 4.2 로컬 실행
```bash
streamlit run main.py
```

### 4.3 프로젝트 디렉토리 구조
```
assets/
├── input/      # 키워드/사이트 목록
├── data/       # 엑셀 분석 결과물
└── css/        # 사용자 정의 스타일
main.py         # 메인 애플리케이션
```

## 5. 입력 데이터 커스터마이징 (Customizing Input Data)
- 키워드: `assets/input/keyword.txt`, `en_keyword.txt`
- 사이트: `assets/input/sites.txt`
- 프롬프트: 핵심 프롬프트 변경 시 개발자 협의 필요

## 6. 결론 및 참고 (Conclusion & Notes)
본 도구는 매주 생성되는 방대한 정보를 자동으로 수집, 분석, 시각화하여 연구자 및 정책결정자가 주요 과학기술 트렌드를 직관적으로 파악할 수 있도록 돕습니다.

**작성일자**: 2025년 6월 6일  
**작성자**: 한국공학대학교 강송희  
**라이선스**: MIT License
