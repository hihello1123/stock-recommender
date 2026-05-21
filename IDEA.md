# 텔레그램 기반 미국 주식 평가 봇 기획서

## 1. 프로젝트 개요

### 프로젝트 목적

미국 상장주식을 대상으로 기업 데이터를 수집하고, 여러 투자 대가의 관점으로 정량 평가한 뒤, 텔레그램 봇을 통해 요약 리포트를 제공하는 개인용 주식 평가 프로그램을 만든다.

이 프로젝트는 당장 실제 주식을 매수하기 위한 도구가 아니라, 나중에 현금흐름이 안정되었을 때 감정이 아닌 기준으로 투자 판단을 하기 위한 사전 준비 도구다.

### 핵심 방향

```text
투자 자동화 X
자동회사평가 O
자동매수 X
분석/모의투자/관심종목 관리 O
최종 판단은 사용자 본인이 수행
```

### 사용 방식

프론트 페이지 없이 텔레그램 봇으로 사용한다.

```text
사용자 → 텔레그램 명령어 입력
텔레그램 봇 → 서버 호출
서버 → 데이터 조회 / 평가 실행
봇 → 요약 리포트 반환
```

---

## 2. 현재 재정계획상 투자 투입 기준

현재 실제 자금 투입은 하지 않는다.

### 현재 허용되는 것

```text
- 주식 평가 봇 개발
- 관심종목 등록
- 평가 기준 정리
- 모의투자
- 투자일지 기록
- 매수 후보 감시
```

### 현재 금지되는 것

```text
- 실제 주식 매수
- 자동매수 기능
- API 주문 기능
- 레버리지 투자
- 단타 신호 기반 매매
```

### 실제 투자 시작 조건

실제 자금 투입은 아래 조건이 충족된 이후에 검토한다.

```text
1. 생활비대출 잔액 0원
2. 카드 신규사용 중단 유지
3. 카드 청구액 납부 가능 상태
4. 현금 비상금 100만 원 확보
5. 월말 기준 생활비대출 재사용 없음
```

즉, 투자 시작 기준은 다음과 같다.

```text
생카 정리
↓
현금 비상금 100만 원 확보
↓
월 1만~5만 원 수준의 소액 테스트 투자 가능
```

---

## 3. 전체 시스템 구조

```text
Telegram Bot
    ↓
Django / Python Backend
    ↓
Stock Data Collector
    ↓
Financial Data Normalizer
    ↓
Quantitative Scoring Engine
    ↓
Investor Lens Evaluators
    ↓
LLM Explanation Generator
    ↓
Telegram Report
```

### 핵심 설계 원칙

```text
정량 평가 = 코드
정성 설명 = LLM
최종 판단 = 사용자
```

LLM에게 점수 계산까지 맡기지 않는다.  
점수는 코드가 고정된 기준으로 계산하고, LLM은 그 점수의 이유를 사람이 읽기 좋게 설명하는 역할만 맡는다.

---

## 4. 대상 시장

### 대상

```text
미국 상장주식
S&P 500 중심
대형 우량주 중심
일반 기업 중심
```

### 초기 제외 또는 낮은 신뢰도로 처리할 대상

```text
은행
보험
증권
REIT
바이오 적자기업
원자재/광산
항공
조선/건설/플랜트
SPAC
폐쇄형 펀드
레버리지 ETF
```

단, REIT는 리얼티 인컴 같은 관심 종목이 있을 경우 1.5단계에서 전용 보정 렌즈를 추가할 수 있다.

---

## 5. 주요 명령어 설계

### 기본 명령어

```text
/start
/help
/ping
```

### 회사 평가

```text
/company AAPL
/company MSFT
/company O
```

### 렌즈별 상세 평가

```text
/lens AAPL buffett
/lens AAPL graham
/lens AAPL lynch
/lens AAPL munger
/lens AAPL all
```

### 랭킹

```text
/rank buffett
/rank graham
/rank lynch
/rank munger
```

### 관심종목

```text
/watch AAPL
/unwatch AAPL
/watchlist
```

### 모의투자

```text
/paper_buy AAPL 1
/paper_sell AAPL 1
/paper_portfolio
```

### 리포트

```text
/report
/report weekly
```

---

## 6. 투자 대가 렌즈

처음에는 4명의 투자 대가 기준만 구현한다.

```text
1. Warren Buffett Lens
2. Benjamin Graham Lens
3. Peter Lynch Lens
4. Charlie Munger Lens
```

각 렌즈는 서로 독립적으로 평가한다.

```text
같은 회사 데이터
→ Buffett Lens 단독 평가
→ Graham Lens 단독 평가
→ Lynch Lens 단독 평가
→ Munger Lens 단독 평가
→ 마지막에 결과만 취합
```

렌즈별 평가 과정에서는 다른 렌즈의 결과를 입력으로 넣지 않는다.  
이렇게 해야 평가 관점 간 오염을 줄일 수 있다.

---

## 7. Buffett Lens

### 핵심 관점

```text
좋은 회사를 합리적인 가격에 오래 보유한다.
```

버핏 렌즈는 단순히 싼 주식보다 사업의 질을 우선한다.

### 주요 평가 항목

| 항목 | 설명 |
|---|---|
| ROE | 자기자본으로 이익을 잘 내는가 |
| ROIC | 투입자본 대비 수익성이 좋은가 |
| 영업이익률 | 사업 자체의 수익성이 좋은가 |
| 순이익 안정성 | 장기간 돈을 벌었는가 |
| FCF | 실제 현금이 남는가 |
| 부채 부담 | 위기 때 버틸 수 있는가 |
| 경제적 해자 | 경쟁자가 쉽게 따라올 수 없는가 |
| 가격 합리성 | 너무 비싸게 사는 것은 아닌가 |

### 점수 구조 예시

```text
Buffett Lens / 100점

1. 장기 수익성          20점
2. 현금흐름 안정성       20점
3. 부채 안정성          15점
4. 경제적 해자          20점
5. 사업 이해 가능성      10점
6. 가격 합리성          15점
```

### 좋은 회사로 보는 조건

```text
- 최근 5~10년 흑자 유지
- ROE 또는 ROIC가 꾸준히 높음
- FCF가 장기간 플러스
- 부채가 과하지 않음
- 사업 모델이 단순하고 이해 가능함
- 브랜드, 네트워크 효과, 전환비용, 규모의 경제 중 하나 이상 존재
```

### 감점 조건

```text
- 이익 변동성이 너무 큼
- 부채가 과도함
- FCF가 자주 마이너스
- 사업 구조가 지나치게 복잡함
- 경쟁우위가 불명확함
- 현재 가격이 지나치게 비쌈
```

### 봇 응답 예시

```text
[Buffett Lens]

등급: B+
점수: 82 / 100

좋은 점:
- ROIC가 장기간 높게 유지됨
- FCF가 꾸준히 플러스
- 부채 부담이 낮음
- 브랜드/플랫폼 해자가 있음

아쉬운 점:
- 현재 밸류에이션은 낮지 않음
- 최근 성장률 둔화 확인 필요

판단:
좋은 회사로 볼 수 있으나, 가격 안전마진은 별도 확인 필요.
```

---

## 8. Graham Lens

### 핵심 관점

```text
충분히 싼 가격에 안전마진을 확보한다.
```

그레이엄 렌즈는 사업의 화려함보다 가격과 재무 안정성을 본다.

### 주요 평가 항목

| 항목 | 설명 |
|---|---|
| PER | 이익 대비 싼가 |
| PBR | 자산 대비 싼가 |
| 유동비율 | 단기 지급능력이 있는가 |
| 부채비율 | 재무위험이 낮은가 |
| NCAV | 순유동자산 대비 싸게 거래되는가 |
| 배당 이력 | 안정적 기업인지 참고 |
| 이익 안정성 | 적자 반복 기업인지 확인 |
| 안전마진 | 내재가치보다 충분히 싼가 |

### 점수 구조 예시

```text
Graham Lens / 100점

1. 가격 저평가          30점
2. 재무 안정성          25점
3. 이익 안정성          15점
4. 배당/주주환원         10점
5. 안전마진             20점
```

### 좋은 회사로 보는 조건

```text
- PER이 낮음
- PBR이 낮음
- 유동비율이 높음
- 부채가 낮음
- 장기간 적자가 아님
- 내재가치 대비 충분히 할인되어 있음
```

### 감점 조건

```text
- PER/PBR이 높음
- 적자 지속
- 부채 과다
- 유동성 부족
- 순자산 대비 전혀 싸지 않음
- 안전마진이 부족함
```

### 봇 응답 예시

```text
[Graham Lens]

등급: C+
점수: 61 / 100

좋은 점:
- 부채 부담은 낮은 편
- 장기 적자 기업은 아님

아쉬운 점:
- PER 기준 저평가로 보기 어려움
- PBR 기준 자산가치 할인도 크지 않음
- NCAV 방식에는 부합하지 않음

판단:
좋은 회사일 수는 있으나, 그레이엄식 '싼 주식'은 아님.
```

---

## 9. Peter Lynch Lens

### 핵심 관점

```text
성장하는 회사를 합리적인 가격에 산다.
```

린치 렌즈는 내가 이해할 수 있는 성장과 성장 대비 가격을 본다.

### 주요 평가 항목

| 항목 | 설명 |
|---|---|
| 매출 성장률 | 실제 사업이 커지는가 |
| EPS 성장률 | 주주 몫의 이익이 증가하는가 |
| PEG | 성장률 대비 가격이 적절한가 |
| 부채비율 | 성장 중 재무위험이 과하지 않은가 |
| 이익 지속성 | 성장 품질이 좋은가 |
| 사업 이해도 | 개인 투자자가 이해 가능한가 |
| 시장 확장성 | 더 커질 여지가 있는가 |
| 내부자/자사주 | 경영진 신뢰도 참고 |

### 점수 구조 예시

```text
Peter Lynch Lens / 100점

1. 성장성               30점
2. 성장 대비 가격        25점
3. 재무 안정성           15점
4. 사업 이해 가능성       15점
5. 장기 확장성           15점
```

### 좋은 회사로 보는 조건

```text
- 매출과 EPS가 꾸준히 증가
- PEG가 과도하지 않음
- 부채가 감당 가능함
- 사업 모델을 쉽게 설명할 수 있음
- 아직 성장 여지가 있음
```

### 감점 조건

```text
- 성장률 둔화
- EPS가 들쭉날쭉함
- PEG가 지나치게 높음
- 부채로 성장하는 구조
- 사업이 너무 복잡하거나 유행성 테마에 가까움
```

### 봇 응답 예시

```text
[Peter Lynch Lens]

등급: B
점수: 76 / 100

좋은 점:
- 매출 성장률이 안정적
- EPS 증가 추세가 있음
- 사업 구조를 이해하기 쉬움

아쉬운 점:
- 현재 가격은 성장률 대비 싸지 않음
- 향후 성장률 둔화 가능성 확인 필요

판단:
성장성과 이해 가능성은 양호하나, PEG 기준 가격 부담 확인 필요.
```

---

## 10. Munger Lens

### 핵심 관점

```text
훌륭한 사업을 오래 보유한다.
나쁜 사업은 아무리 싸도 피한다.
```

멍거 렌즈는 숫자도 보지만 사업의 질과 장기 생존성을 강하게 본다.

### 주요 평가 항목

| 항목 | 설명 |
|---|---|
| 사업 품질 | 장기적으로 좋은 사업인가 |
| ROIC | 자본을 효율적으로 쓰는가 |
| 경제적 해자 | 경쟁우위가 지속 가능한가 |
| 가격 결정력 | 원가 상승을 가격에 전가 가능한가 |
| 반복 수익 | 매출이 예측 가능한가 |
| 경영진 자본배분 | 돈을 현명하게 쓰는가 |
| 복잡성 | 내가 이해할 수 있는가 |
| 장기 리스크 | 규제, 기술 변화, 산업 쇠퇴 가능성 |

### 점수 구조 예시

```text
Munger Lens / 100점

1. 사업 품질             25점
2. 경제적 해자           25점
3. 자본효율성            20점
4. 경영/자본배분          15점
5. 단순성/예측 가능성      15점
```

### 좋은 회사로 보는 조건

```text
- ROIC가 높고 오래 유지됨
- 경쟁우위가 명확함
- 가격 결정력이 있음
- 반복 매출 또는 높은 고객 충성도가 있음
- 경영진의 자본배분이 합리적임
- 장기적으로 산업이 사라질 가능성이 낮음
```

### 감점 조건

```text
- 싸지만 사업의 질이 낮음
- 자본을 많이 넣어야 겨우 성장함
- 해자가 약함
- 기술 변화에 쉽게 무너질 수 있음
- 경영진이 주주가치를 훼손함
- 사업 구조가 지나치게 복잡함
```

### 봇 응답 예시

```text
[Munger Lens]

등급: A-
점수: 86 / 100

좋은 점:
- 높은 ROIC
- 강한 브랜드/네트워크 효과
- 반복 매출 구조
- 장기 경쟁우위가 명확함

아쉬운 점:
- 현재 가격은 싸지 않음
- 장기 규제 리스크 확인 필요

판단:
사업 품질은 높음. 다만 좋은 회사를 나쁜 가격에 사지 않도록 주의 필요.
```

---

## 11. 평가 신뢰도

점수와 별개로 평가 신뢰도를 표시한다.

```text
평가 점수: 82점
평가 신뢰도: 높음 / 중간 / 낮음
```

### 평가 신뢰도 기준 예시

| 기업 유형 | 평가 신뢰도 |
|---|---|
| 소비재 우량주 | 높음 |
| 소프트웨어 대형주 | 중간~높음 |
| 안정적 배당주 | 중간~높음 |
| REIT | REIT 렌즈 없으면 중간 이하 |
| 은행/보험 | 낮음 |
| 바이오 적자기업 | 낮음 |
| 원자재/에너지 | 낮음 |
| 조선/건설/플랜트 | 낮음 |

### 낮은 신뢰도 응답 예시

```text
평가 신뢰도: 낮음

주의:
이 회사는 일반 재무지표만으로 판단하기 어려운 업종입니다.
현재 점수는 참고용이며 업종 전용 지표 확인이 필요합니다.
```

---

## 12. 업종별 특수성 처리 방식

처음부터 모든 업종별 전용 렌즈를 만들지 않는다.

### 초기 전략

```text
1. 공통 평가 엔진을 만든다.
2. 4명 투자자 렌즈를 만든다.
3. 업종별로 평가 신뢰도와 추가 확인사항만 표시한다.
4. 자주 보는 업종부터 전용 렌즈를 하나씩 추가한다.
```

### 예시: REIT

```text
주의:
이 회사는 REIT입니다.
일반 PER보다 P/AFFO, AFFO payout ratio, occupancy, debt maturity를 확인해야 합니다.
```

### 예시: 조선/장기계약 산업

```text
주의:
이 회사는 장기계약 산업에 속합니다.
일반 PER, ROE만으로 저평가 여부를 판단하기 어렵습니다.

추가 확인 필요:
- 수주잔고
- 신규 수주 단가
- 인도 일정
- 원가 상승 리스크
- 공정률 기준 매출 인식
- 손실충당금 발생 여부
```

---

## 13. 데이터 수집

### 1차 데이터 소스

초기에는 개발 속도와 편의성을 우선한다.

```text
1차: yfinance
2차: Financial Modeling Prep 또는 Alpha Vantage
3차: SEC EDGAR 직접 파싱
```

### 필요한 데이터

```text
- 티커
- 회사명
- 섹터
- 산업군
- 현재가
- 시가총액
- PER
- PBR
- PSR
- EV/EBITDA
- ROE
- ROIC
- 매출
- 영업이익
- 순이익
- EPS
- FCF
- 부채
- 현금
- 배당금
- 배당수익률
- 자사주 매입 여부
```

---

## 14. DB 모델 초안

```text
Company
- id
- ticker
- name
- exchange
- sector
- industry
- country
- is_active
- created_at
- updated_at

FinancialStatement
- id
- company_id
- fiscal_year
- fiscal_quarter
- revenue
- operating_income
- net_income
- eps
- total_assets
- total_liabilities
- total_equity
- operating_cash_flow
- free_cash_flow
- capex
- created_at

ValuationSnapshot
- id
- company_id
- date
- price
- market_cap
- per
- pbr
- psr
- ev_ebitda
- dividend_yield
- created_at

LensScore
- id
- company_id
- lens_name
- date
- score
- grade
- confidence
- passed_rules
- failed_rules
- warnings
- created_at

TelegramUser
- id
- chat_id
- username
- is_allowed
- created_at

Watchlist
- id
- user_id
- company_id
- memo
- target_price
- created_at

PaperTrade
- id
- user_id
- company_id
- trade_type
- quantity
- price
- reason
- traded_at

AlertLog
- id
- user_id
- company_id
- alert_type
- message
- sent_at
```

---

## 15. 코드 구조 초안

```text
stock_evaluator/
  config/
    settings.py
    urls.py

  companies/
    models.py
    services/
      market_data_client.py
      financial_data_client.py
      data_normalizer.py
      report_service.py
    management/
      commands/
        sync_companies.py
        sync_financials.py
        calculate_scores.py
        send_daily_report.py

  lenses/
    base.py
    buffett.py
    graham.py
    lynch.py
    munger.py
    aggregator.py

  telegram_bot/
    bot.py
    handlers.py
    messages.py
    keyboards.py

  users/
    models.py

  paper_trading/
    models.py
    services.py
```

---

## 16. 평가 결과 객체

```python
from dataclasses import dataclass

@dataclass
class LensScoreResult:
    lens_name: str
    score: int
    grade: str
    confidence: str
    passed_rules: list[str]
    failed_rules: list[str]
    warnings: list[str]
    required_extra_checks: list[str]
```

### 렌즈 클래스 구조

```python
class InvestorLens:
    name: str

    def evaluate(self, company_data) -> LensScoreResult:
        raise NotImplementedError
```

---

## 17. LLM 사용 원칙

LLM은 점수를 새로 만들지 않는다.  
코드가 계산한 결과를 자연어로 설명한다.

### LLM 입력 예시

```text
아래 코드 평가 결과를 바탕으로 설명만 작성해라.
새 점수를 만들지 마라.
입력에 없는 사실을 추측하지 마라.
투자 추천처럼 말하지 마라.

회사:
- Ticker: MSFT
- Name: Microsoft

렌즈:
- Buffett Lens

코드 평가 결과:
- Score: 84
- Grade: A-
- Confidence: 중간~높음

통과 기준:
- 높은 ROIC
- 안정적인 FCF
- 낮은 부채 부담
- 강한 해자

감점 기준:
- 밸류에이션 부담

출력:
- 좋은 점
- 아쉬운 점
- 추가 확인사항
- 최종 해석
```

### LLM 출력 예시

```text
Microsoft는 버핏식 관점에서 높은 사업 품질과 장기 현금창출력을 가진 회사로 평가됩니다.
높은 ROIC와 안정적인 FCF는 긍정적입니다.
다만 이미 시장에서 높은 평가를 받고 있어 매수 판단에는 가격 안전마진 확인이 필요합니다.
```

---

## 18. 텔레그램 최종 응답 예시

```text
[MSFT / Microsoft]

종합 요약:
좋은 회사에 가깝지만, 가격 매력은 별도 확인 필요.

렌즈별 평가:
- Buffett: A- / 84점
- Graham: C / 58점
- Lynch: B+ / 78점
- Munger: A / 88점

공통 장점:
- 높은 현금흐름
- 강한 사업 경쟁력
- 안정적인 수익성
- 장기 성장성 존재

공통 위험 신호:
- 밸류에이션 부담 있음
- 성장률 둔화 여부 확인 필요
- 규제 리스크 확인 필요

평가 신뢰도:
중간~높음

최종 판단:
자동 매수 아님.
관심종목 등록 후 가격과 실적 추적 권장.

/lens MSFT buffett
/lens MSFT graham
/lens MSFT lynch
/lens MSFT munger
/watch MSFT
```

---

## 19. 개발 단계

### 1단계: 텔레그램 봇 기본 골격

```text
/start
/help
/ping
```

목표:

```text
내 텔레그램에서 봇이 정상 응답한다.
```

### 2단계: 티커 조회

```text
/company AAPL
/company MSFT
```

목표:

```text
티커를 입력하면 회사 기본 정보가 나온다.
```

### 3단계: 더미 렌즈 평가

목표:

```text
실제 데이터 없이 더미 데이터로 렌즈별 응답 포맷을 확정한다.
```

### 4단계: yfinance 연동

목표:

```text
현재가, 시가총액, PER, PBR, 재무 데이터 일부를 가져온다.
```

### 5단계: 코드 기반 점수 계산

목표:

```text
Buffett / Graham / Lynch / Munger 렌즈별 점수를 코드로 계산한다.
```

### 6단계: LLM 설명 생성

목표:

```text
코드 계산 결과를 바탕으로 자연어 설명을 생성한다.
```

### 7단계: 관심종목 기능

```text
/watch AAPL
/unwatch AAPL
/watchlist
```

### 8단계: 모의투자 기능

```text
/paper_buy AAPL 1
/paper_sell AAPL 1
/paper_portfolio
```

### 9단계: 주간 리포트

```text
/report weekly
```

예시:

```text
이번 주 관심종목 변화:
- MSFT: Buffett 점수 +2
- AAPL: Graham 점수 -1
- O: REIT 특성상 평가 신뢰도 중간
```

---

## 20. 나중에 확장 가능한 기능

### 계좌 조회

```text
/cash
/portfolio
/orders
```

### 주문 기능

현금흐름이 안정되고 실제 투자를 시작할 수 있는 상태가 된 뒤에만 고려한다.

```text
/buy AAPL 1
/sell AAPL 1
```

단, 실제 주문 기능은 반드시 2단계 확인을 거친다.

```text
/buy AAPL 1
↓
주문 요약 출력
↓
확인 코드 입력
↓
주문 실행
```

### 주문 확인 예시

```text
[주문 확인]

종목: Apple / AAPL
구분: 매수
수량: 1주
현재가: $000.00
예상금액: $000.00 + 수수료

주문을 실행하려면 아래 코드를 입력하세요.

CONFIRM 4931
```

---

## 21. 보안 원칙

개인용 봇이므로 접근 제한을 반드시 둔다.

```text
ALLOWED_CHAT_ID = 내 텔레그램 chat_id
```

허용되지 않은 사용자는 모든 명령어를 차단한다.

```text
접근 권한이 없습니다.
```

API 키는 절대 코드에 직접 넣지 않는다.

```text
.env
환경변수
서버 시크릿 관리
```

---

## 22. 최종 프로젝트 정의

```text
프로젝트명:
Global Equity Lens Bot

목적:
미국 상장기업을 여러 투자 대가의 관점으로 자동 평가하는 텔레그램 기반 개인 투자 분석 봇

초기 기능:
- 티커 기반 기업 조회
- 재무 요약
- Buffett / Graham / Lynch / Munger 렌즈 평가
- 평가 신뢰도 표시
- 추가 확인사항 표시
- 관심종목 등록
- 모의투자

장기 기능:
- 주간 리포트
- 투자일지
- 계좌 조회
- 확인형 주문 기능
```

---

## 23. 최종 원칙

```text
봇은 종목을 고르는 것이 아니다.
봇은 내가 종목을 고를 때 필요한 관점을 정리한다.
```

```text
점수는 코드가 계산한다.
설명은 LLM이 작성한다.
최종 판단은 내가 한다.
```

```text
지금은 실제 투자금 투입 없이 개발과 모의투자까지만 한다.
실제 투자는 생카 정리와 현금 비상금 확보 이후에 검토한다.
```