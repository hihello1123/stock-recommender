# Global Equity Lens Bot 구현 계획

작성일: 2026-05-21

이 문서는 `docs/plans/IDEA.md`를 바탕으로 `/autoplan` 방식의 전략, 엔지니어링, DX 리뷰를 반영해 실제 구현 순서를 정리한 계획이다.

## 결론

첫 번째 버전은 "주식 추천 봇"이 아니라 "회사 데이터 신뢰도와 기본 품질 체크 봇"으로 만든다.

초기 목표는 다음 하나다.

```text
/company AAPL
→ 회사 기본 정보
→ 데이터 출처와 기준일
→ 평가 가능 여부
→ 1개 품질 렌즈 점수
→ 사람이 직접 확인해야 할 항목
```

4개 투자 대가 렌즈, 랭킹, 모의투자, LLM 설명은 바로 만들지 않는다. 이유는 점수 체계가 검증되기 전에 기능을 넓히면 그럴듯하지만 틀린 결론을 만들 위험이 커지기 때문이다.

## 제품 원칙

1. 실제 매수, 주문, 계좌 조회 기능은 이 저장소의 현재 범위에서 제외한다.
2. 점수는 코드가 계산하고, 설명은 템플릿 또는 제한된 LLM이 작성한다.
3. 점수보다 데이터 신뢰도를 먼저 보여준다.
4. 낮은 신뢰도 업종은 일반 점수를 숨기거나 강한 경고를 붙인다.
5. 모든 점수는 나중에 재현할 수 있어야 한다.

## v1 범위

### 포함

- Django 기반 백엔드
- Telegram Bot 명령어 처리
- 허용된 Telegram chat id만 접근
- `/start`, `/help`, `/ping`
- `/company TICKER`
- 티커 정규화와 회사 기본 정보 조회
- yfinance 기반 현재가와 기본 재무 데이터 조회
- 데이터 출처, 조회 시점, 누락 필드 표시
- `Quality Lens v1` 1개
- 평가 신뢰도와 경고 표시
- SQLite 개발 DB
- 핵심 로직 단위 테스트

### 제외

- `/rank`
- `/lens ... all`
- Graham, Lynch, Munger 렌즈
- LLM 설명 생성
- 관심종목
- 모의투자
- 주간 리포트
- 계좌 조회
- 실제 주문
- 브로커 API 의존성

## v1.5 범위

- `/watch`, `/unwatch`, `/watchlist`
- 점수 스냅샷 저장
- Buffett, Graham, Lynch, Munger 렌즈 중 1개씩 추가
- 템플릿 기반 상세 리포트
- 저신뢰 업종 전용 경고 강화

## v2 범위

- LLM 설명 생성
- 주간 리포트
- 모의투자
- 랭킹
- SEC EDGAR 또는 유료 데이터 소스 교차검증

실제 주문 기능은 v2에도 넣지 않는다. 별도 프로젝트로 다시 판단한다.

## 아키텍처

```text
Telegram
  -> telegram_bot.handlers
  -> companies.services.company_lookup
  -> companies.services.market_data_client
  -> companies.services.data_normalizer
  -> instruments.classifier
  -> lenses.quality_v1
  -> reports.telegram_renderer
  -> Telegram response
```

### Django 앱 구조

```text
stock_evaluator/
  config/
  companies/
    models.py
    services/
      company_lookup.py
      market_data_client.py
      data_normalizer.py
  instruments/
    classifier.py
  lenses/
    base.py
    quality_v1.py
  reports/
    telegram_renderer.py
  telegram_bot/
    handlers.py
    auth.py
    messages.py
  users/
    models.py
```

`paper_trading`, `llm`, `rankings` 앱은 v1에서 만들지 않는다.

## 데이터 모델

### Company

- `ticker`
- `name`
- `exchange`
- `sector`
- `industry`
- `country`
- `cik`
- `instrument_type`
- `is_active`
- `created_at`
- `updated_at`

제약:

- `(ticker, exchange)` unique

### FinancialSnapshot

- `company`
- `source`
- `source_url`
- `as_of_date`
- `period_end_date`
- `period_type`
- `currency`
- `price`
- `market_cap`
- `per`
- `pbr`
- `psr`
- `roe`
- `roic`
- `revenue`
- `operating_income`
- `net_income`
- `eps`
- `operating_cash_flow`
- `free_cash_flow`
- `total_debt`
- `cash`
- `missing_fields`
- `raw_payload`
- `created_at`

제약:

- `(company, source, as_of_date, period_end_date, period_type)` unique

### LensScore

- `company`
- `snapshot`
- `lens_name`
- `scoring_version`
- `score`
- `grade`
- `confidence`
- `data_completeness`
- `passed_rules`
- `failed_rules`
- `warnings`
- `required_extra_checks`
- `created_at`

제약:

- `(company, snapshot, lens_name, scoring_version)` unique

### TelegramUser

- `chat_id`
- `username`
- `is_allowed`
- `created_at`
- `last_seen_at`

## Quality Lens v1

유명 투자자 이름을 바로 붙이지 않는다. v1은 `Quality Lens v1`로 시작한다.

점수는 100점이다.

| 영역 | 배점 | 기준 |
|---|---:|---|
| 수익성 | 25 | ROE, ROIC, 영업이익률 |
| 현금흐름 | 25 | FCF 양수 여부, OCF 대비 FCF |
| 재무 안정성 | 20 | 부채 부담, 현금 보유 |
| 이익 안정성 | 15 | 최근 기간 적자 여부 |
| 가격 부담 | 15 | PER, PBR, PSR |

### 누락 데이터 처리

- 누락 필드는 0점 처리하지 않는다.
- 해당 하위 항목은 `unknown`으로 두고 `data_completeness`를 낮춘다.
- `data_completeness < 70`이면 총점보다 "평가 신뢰도 낮음"을 더 크게 표시한다.

### 저신뢰 대상 처리

다음 대상은 일반 점수를 숨기거나 낮은 신뢰도로 강제한다.

- 은행
- 보험
- 증권
- REIT
- ETF, 펀드, 폐쇄형 펀드
- SPAC
- 바이오 적자기업
- 원자재/광산
- 항공
- 조선/건설/플랜트

응답은 이렇게 한다.

```text
일반 품질 점수: 제공하지 않음
이유: 이 업종은 일반 PER/ROE/FCF 기준만으로 평가하기 어렵습니다.
추가 확인: 업종 전용 지표가 필요합니다.
```

## Telegram 응답 v1

```text
[AAPL / Apple Inc.]

데이터
- 출처: yfinance
- 기준일: 2026-05-21
- 누락 필드: ROIC
- 데이터 완성도: 86 / 100

Quality Lens v1
- 등급: B+
- 점수: 78 / 100
- 평가 신뢰도: 중간

통과
- FCF 양수
- 부채 부담 낮음
- 수익성 양호

주의
- ROIC 데이터 누락
- 현재 가격 부담 있음

해석
이 결과는 자동 매수 신호가 아닙니다.
가격, 최근 실적, 업종 리스크를 직접 확인해야 합니다.
```

## 보안 경계

- `ALLOWED_TELEGRAM_CHAT_IDS`에 없는 사용자는 모든 명령어 차단
- group chat에서는 기본 차단
- webhook 사용 시 Telegram secret token 검증
- API 키와 봇 토큰은 `.env` 또는 서버 시크릿으로만 주입
- 로그에 봇 토큰, API 키, 원본 env 출력 금지
- 명령어별 rate limit 적용
- 브로커 API 패키지 설치 금지
- `/buy`, `/sell`, `/orders`, `/portfolio` 명령어 등록 금지

## 테스트 계획

### Phase 1: 봇 골격

- `/ping`이 허용된 chat id에서만 응답한다.
- 허용되지 않은 chat id는 차단된다.
- group chat 명령은 차단된다.

### Phase 2: 티커 조회

- `aapl`, ` AAPL `, `AAPL.US` 입력 정규화
- 존재하지 않는 티커 오류 메시지
- 데이터 소스 장애 메시지

### Phase 3: 데이터 정규화

- yfinance 응답 fixture를 정규화한다.
- 통화, 기준일, 누락 필드를 기록한다.
- 숫자 타입 변환 실패를 안전하게 처리한다.

### Phase 4: Quality Lens

- golden fixture 5개로 점수 검증
- 누락 데이터가 점수를 왜곡하지 않는지 검증
- 저신뢰 업종은 일반 점수를 숨기는지 검증

### Phase 5: Telegram 리포트

- 긴 응답이 Telegram 메시지 제한을 넘지 않는다.
- 금지 표현을 쓰지 않는다.
- "매수 추천", "팔아라", "저평가라 사도 된다" 같은 문구가 나오지 않는다.

## 실패 모드

| 실패 | 사용자 영향 | 처리 |
|---|---|---|
| yfinance 장애 | 회사 조회 실패 | 재시도 안내, 기존 스냅샷 있으면 기준일 표시 |
| 재무 필드 누락 | 점수 왜곡 | 점수 대신 낮은 데이터 완성도 표시 |
| 업종 오분류 | 부적절한 점수 | unknown이면 점수 보수적으로 제한 |
| LLM 환각 | 투자 조언처럼 보임 | v1에서는 LLM 미사용 |
| Telegram 토큰 유출 | 봇 탈취 | env 관리, 로그 마스킹 |
| 실제 주문 기능 유입 | 재정 원칙 훼손 | 명령어와 의존성 모두 금지 |

## 구현 순서

1. Django 프로젝트 생성
2. 환경변수 설정 구조 추가
3. Telegram auth와 `/ping` 구현
4. `Company`, `FinancialSnapshot`, `LensScore`, `TelegramUser` 모델 추가
5. yfinance client 추가
6. 데이터 정규화 layer 추가
7. instrument classifier 추가
8. `Quality Lens v1` 구현
9. `/company TICKER` 구현
10. 테스트와 fixture 추가
11. README에 실행 방법 작성

## 결정 기록

| # | 결정 | 이유 | 미룬 것 |
|---|---|---|---|
| 1 | v1은 1개 렌즈만 구현 | 점수 체계 검증 전 기능 확장 방지 | 4개 투자자 렌즈 |
| 2 | LLM은 v1 제외 | 투자 조언처럼 보이는 문장 위험 제거 | LLM 설명 |
| 3 | ranking 제외 | 검증 전 순위는 추천처럼 보임 | `/rank` |
| 4 | paper trading 제외 | 현금/수수료/환율/배당/분할 처리가 필요함 | 모의투자 |
| 5 | 주문 기능 금지 | 현재 재정 원칙과 충돌 | `/buy`, `/sell` |
| 6 | 데이터 완성도 우선 | 나쁜 데이터가 점수를 오염시키는 문제 방지 | 고신뢰 자동 평가 |

## 다음 작업

바로 구현을 시작한다면 첫 커밋 범위는 다음이 적절하다.

```text
목표: 텔레그램에서 /ping이 안전하게 응답하는 Django 골격

포함:
- Django 프로젝트 생성
- .env.example
- Telegram bot 설정
- ALLOWED_TELEGRAM_CHAT_IDS 기반 접근 제한
- /start, /help, /ping
- 기본 테스트

제외:
- yfinance
- 점수 계산
- DB 스키마 확장
```
