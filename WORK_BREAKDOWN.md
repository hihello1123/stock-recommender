# 작업 단위 계획

작성일: 2026-05-21

기준 문서:

- `IDEA.md`
- `IMPLEMENTATION_PLAN.md`

목표는 `Global Equity Lens Bot`의 v1을 작게, 검증 가능하게 구현하는 것이다.

## Scope Challenge

v1 전체를 한 번에 만들면 Django 프로젝트, Telegram bot, 인증, 데이터 수집, 정규화, DB 모델, 업종 분류, 점수 계산, 리포트 렌더링, 테스트가 동시에 생긴다. 이는 8개 이상 파일과 2개 이상 서비스를 건드리는 작업이라 한 PR/커밋 단위로는 크다.

따라서 v1을 아래 7개 작업 단위로 나눈다.

## 작업 단위 요약

| 순서 | 작업 | 목표 | 검증 |
|---:|---|---|---|
| 1 | 프로젝트 골격 | Django 실행 가능 상태 | `python manage.py check` |
| 2 | Telegram 기본 봇 | `/start`, `/help`, `/ping` 응답 | handler 단위 테스트 |
| 3 | 접근 제어 | 허용 chat id만 사용 | 인증 테스트 |
| 4 | 회사/스냅샷 모델 | 재현 가능한 데이터 저장 구조 | migration/check/model 테스트 |
| 5 | 시장 데이터 조회/정규화 | yfinance 응답을 내부 객체로 변환 | fixture 테스트 |
| 6 | Quality Lens v1 | 기본 품질 점수 계산 | golden fixture 테스트 |
| 7 | `/company TICKER` | end-to-end 텔레그램 리포트 | 통합 테스트 |

## 1. 프로젝트 골격

### 포함

- Python 프로젝트 설정
- Django 프로젝트 생성
- 기본 settings 분리
- `.env.example`
- pytest 또는 Django test runner 설정
- README 실행 방법 초안

### 제외

- Telegram 연동
- yfinance
- DB 모델 상세 구현

### 파일 범위

```text
pyproject.toml
manage.py
stock_evaluator/config/
README.md
.env.example
```

### 완료 조건

```text
python manage.py check
python manage.py test
```

둘 다 통과한다.

## 2. Telegram 기본 봇

### 포함

- Telegram bot application factory
- `/start`
- `/help`
- `/ping`
- 로컬 polling 실행 command

### 제외

- webhook 배포
- 주식 조회
- 접근 제어 고도화

### 파일 범위

```text
stock_evaluator/telegram_bot/
stock_evaluator/config/settings.py
```

### 완료 조건

- `/ping` handler가 `"pong"` 계열 응답을 만든다.
- Telegram token이 없을 때 명확한 설정 오류를 낸다.
- 봇 토큰은 로그에 출력되지 않는다.

## 3. 접근 제어

### 포함

- `ALLOWED_TELEGRAM_CHAT_IDS`
- private chat만 허용
- 미허용 사용자는 모든 명령 차단
- 접근 거부 메시지

### 제외

- rate limit
- webhook secret token

### 파일 범위

```text
stock_evaluator/telegram_bot/auth.py
stock_evaluator/telegram_bot/handlers.py
stock_evaluator/config/settings.py
```

### 완료 조건

- 허용 chat id는 `/ping` 가능
- 미허용 chat id는 차단
- group chat은 차단
- 접근 거부 테스트가 있다.

## 4. 회사/스냅샷 모델

### 포함

- `Company`
- `FinancialSnapshot`
- `LensScore`
- `TelegramUser`
- unique constraint
- admin 등록은 선택

### 제외

- Watchlist
- PaperTrade
- AlertLog

### 파일 범위

```text
stock_evaluator/companies/models.py
stock_evaluator/users/models.py
stock_evaluator/companies/migrations/
stock_evaluator/users/migrations/
```

### 완료 조건

- migration 생성
- `python manage.py check` 통과
- 중복 snapshot 저장이 constraint로 막힌다.
- `LensScore.scoring_version`이 필수다.

## 5. 시장 데이터 조회/정규화

### 포함

- yfinance client
- 티커 정규화
- 외부 응답을 `FinancialSnapshot` 입력값으로 변환
- 누락 필드 계산
- source/as_of_date/currency 기록

### 제외

- FMP/Alpha Vantage
- SEC EDGAR
- batch sync

### 파일 범위

```text
stock_evaluator/companies/services/market_data_client.py
stock_evaluator/companies/services/data_normalizer.py
stock_evaluator/companies/services/company_lookup.py
tests/fixtures/
```

### 완료 조건

- AAPL fixture가 내부 dict/dataclass로 변환된다.
- 누락 필드가 `missing_fields`에 들어간다.
- 네트워크 오류는 사용자에게 보여줄 수 있는 도메인 오류로 변환된다.
- 외부 API 호출 없이 fixture 테스트가 가능하다.

## 6. Quality Lens v1

### 포함

- `InvestorLens` base
- `QualityLensV1`
- 점수 계산
- grade 변환
- data completeness 반영
- 저신뢰 instrument 처리

### 제외

- Buffett/Graham/Lynch/Munger 개별 렌즈
- LLM 설명

### 파일 범위

```text
stock_evaluator/lenses/base.py
stock_evaluator/lenses/quality_v1.py
stock_evaluator/instruments/classifier.py
```

### 완료 조건

- 일반 대형주는 점수와 등급이 나온다.
- REIT/은행/ETF는 일반 점수를 숨기거나 낮은 신뢰도로 강제된다.
- 누락 데이터는 0점이 아니라 `unknown`과 낮은 data completeness로 처리된다.
- golden fixture 5개 테스트가 있다.

## 7. `/company TICKER`

### 포함

- `/company` command parser
- 조회 orchestration
- snapshot 저장
- lens score 저장
- Telegram 메시지 렌더링
- 사용자 친화적 오류 메시지

### 제외

- `/watch`
- `/rank`
- `/lens`
- 주간 리포트

### 파일 범위

```text
stock_evaluator/telegram_bot/handlers.py
stock_evaluator/reports/telegram_renderer.py
stock_evaluator/companies/services/company_lookup.py
```

### 완료 조건

- `/company AAPL` 성공 응답
- 없는 티커 오류 응답
- 외부 데이터 소스 장애 응답
- 낮은 신뢰도 업종 응답
- 메시지에 "매수 추천", "사라", "팔아라" 계열 표현이 없다.

## ASCII 데이터 흐름

```text
/company AAPL
  |
  v
CommandHandler
  |
  v
auth.require_allowed_chat
  |
  v
normalize_ticker("AAPL")
  |
  v
market_data_client.fetch("AAPL")
  |
  +--> timeout/error -> user-safe error message
  |
  v
data_normalizer.to_snapshot_input()
  |
  +--> missing fields -> missing_fields + lower completeness
  |
  v
instrument_classifier.classify()
  |
  +--> low-confidence type -> suppress/limit score
  |
  v
QualityLensV1.evaluate()
  |
  v
telegram_renderer.render_company_report()
  |
  v
Telegram response
```

## 테스트 다이어그램

```text
CODE PATHS                                      TEST TYPE
[+] telegram_bot.auth
  ├── allowed private chat                       unit
  ├── denied chat id                             unit
  └── group chat blocked                         unit

[+] telegram_bot.handlers
  ├── /ping happy path                           unit
  ├── /company missing ticker                    unit
  ├── /company invalid ticker                    unit
  ├── /company data source timeout               integration with fake client
  └── /company success                           integration with fake client

[+] companies.services.market_data_client
  ├── yfinance success                           mocked unit
  ├── empty result                               mocked unit
  └── network/library exception                  mocked unit

[+] companies.services.data_normalizer
  ├── full fixture                               unit
  ├── missing ROIC                               unit
  ├── missing currency/date                      unit
  └── invalid numeric field                      unit

[+] instruments.classifier
  ├── common stock                               unit
  ├── REIT                                      unit
  ├── ETF/fund                                  unit
  └── unknown                                   unit

[+] lenses.quality_v1
  ├── high-quality complete data                 unit/golden
  ├── weak company complete data                 unit/golden
  ├── missing fields                             unit/golden
  ├── low-confidence instrument                  unit/golden
  └── grade boundaries                           unit

[+] reports.telegram_renderer
  ├── normal report                              snapshot test
  ├── low-confidence report                      snapshot test
  ├── data error report                          snapshot test
  └── banned advice wording                      unit
```

## 실패 모드와 처리

| 코드 경로 | 실패 모드 | 사용자 경험 | 테스트 필요 |
|---|---|---|---|
| auth | group chat에서 호출 | 접근 차단 | yes |
| yfinance client | timeout | "데이터 조회 실패" | yes |
| normalizer | 필수 필드 누락 | 낮은 데이터 완성도 | yes |
| classifier | instrument unknown | 낮은 신뢰도 | yes |
| lens | 분모 0 또는 null | unknown 처리 | yes |
| renderer | 긴 메시지 | 잘린 메시지 방지 | yes |

## NOT in scope

- 실제 주문: 현재 재정 원칙과 충돌한다.
- 계좌 조회: 주문 기능과 같은 보안/재정 경계를 건드린다.
- 랭킹: 추천처럼 보이고 검증 전 false confidence를 만든다.
- LLM 설명: v1에서는 템플릿으로 충분하다.
- 모의투자: 현금 장부, 수수료, 환율, 배당, 분할 처리가 필요하다.
- 주간 리포트: watchlist와 score history가 먼저 필요하다.
- 다중 렌즈: Quality Lens v1 검증 후 추가한다.

## What already exists

- `IDEA.md`: 제품 방향, 금지 범위, 초기 명령어, 렌즈 아이디어가 있다.
- `IMPLEMENTATION_PLAN.md`: v1 범위, 데이터 모델, 보안 경계, 테스트 방향이 있다.
- 실제 애플리케이션 코드는 아직 없다.

## 병렬화 전략

초기 1-4번은 순차 구현이 낫다. 프로젝트 골격, bot 설정, 인증, 모델은 서로 의존한다.

5번 이후는 일부 병렬화 가능하다.

| Lane | 작업 | 의존성 |
|---|---|---|
| A | 시장 데이터 조회/정규화 | 1, 4 |
| B | Quality Lens v1 / classifier | 1, 4 |
| C | Telegram `/company` 통합 | A, B |
| D | 리포트 렌더러 | 1, 6 |

추천 실행:

```text
1 -> 2 -> 3 -> 4
then A + B parallel
then C + D
```

충돌 가능성:

- A와 C 모두 `companies/services`를 건드릴 수 있으므로 C는 A 이후가 안전하다.
- B와 D는 모듈이 달라 병렬화하기 좋다.

## 커밋 단위 추천

1. `✨ 초기 Django 프로젝트 골격 추가`
2. `✨ 텔레그램 기본 명령어 추가`
3. `🔒 텔레그램 접근 제어 추가`
4. `🗃️ 회사 평가 데이터 모델 추가`
5. `✨ 시장 데이터 정규화 계층 추가`
6. `✨ 품질 렌즈 v1 점수 계산 추가`
7. `✨ 회사 조회 명령어 연결`
8. `🧪 회사 평가 핵심 경로 테스트 보강`

## 완료 요약

- Step 0 Scope Challenge: v1 전체는 크므로 7개 작업 단위로 분해
- Architecture Review: 데이터 흐름과 모듈 경계 확정
- Code Quality Review: 서비스 계층은 작게 유지하고 v1 앱 수 제한
- Test Review: 코드 경로별 테스트 다이어그램 작성
- Performance Review: v1은 단건 조회, batch/ranking 제외
- NOT in scope: 작성
- What already exists: 작성
- Failure modes: critical silent failure 없도록 각 경로 테스트 요구
- Parallelization: 4단계 이후 2개 lane 병렬 가능
