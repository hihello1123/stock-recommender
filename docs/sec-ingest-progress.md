# SEC 재무제표 수집 진행상황

작성일: 2026-05-27
저장소: stock-recommander

## 목표

SEC EDGAR를 1차 원천으로 사용해 회사별 핵심 재무항목을 백그라운드에서 수집한다. 봇은 SEC 데이터가 없거나 오래된 경우 사용자에게 수집 중이라고 안내하고, 수집 완료 시 해당 사용자에게 완료 메시지를 보낸다.

## 합의된 설계

- 원천 데이터는 처음부터 SEC EDGAR를 사용한다.
- 원문 HTML/XBRL 전체는 저장하지 않고, 핵심 재무항목과 출처 메타데이터만 저장한다.
- 저장 범위는 최근 5년 연간 보고서와 최근 8개 분기 보고서다.
- SEC 요청은 기본 1 req/sec로 제한한다.
- 수집 작업은 기존 분석 워커와 분리된 별도 SEC ingest worker로 처리한다.
- 같은 티커의 활성 수집 job은 하나만 만들고, 여러 사용자는 subscriber로 묶는다.
- 수집 완료 후 분석은 자동 재개하지 않고, 완료 알림과 `/company TICKER` 재실행 안내만 보낸다.
- 지표 계산, 뉴스 수집, LLM 프롬프트 개선은 이번 단계 범위 밖이다.

## 완료된 작업

커밋: `b30a761 🗃️ SEC 재무제표 수집 모델 추가`

- `FinancialStatementPeriod` 모델 추가
  - SEC 10-K/10-Q 기간 재무제표 저장용
  - accession number, filed date, fiscal period, 핵심 재무항목, missing fields 저장
- `SecIngestJob` 모델 추가
  - 티커별 SEC 수집 상태 관리
  - pending/running/succeeded/failed
  - 티커별 활성 job 중복 방지
- `SecIngestSubscriber` 모델 추가
  - 수집 완료 알림 대상 사용자 관리
  - 같은 job/chat 중복 방지
- Django migrations 생성
- 모델 제약 테스트 추가
- 검증: `uv run python manage.py test` → 82 tests OK

## 다음 작업

1. SEC client/extractor/ingest service 추가
   - SEC `company_tickers_exchange.json`에서 ticker → CIK 조회
   - `submissions`와 `companyfacts` JSON 호출
   - companyfacts에서 핵심 재무항목 추출
   - 최근 5년 연간 + 최근 8개 분기 저장
   - fixture/mock 기반 테스트 추가

2. SEC ingest worker 추가
   - `run_sec_ingest_worker`
   - job 상태 전이
   - 성공/실패 알림 전송
   - worker 테스트

3. 봇 분석 흐름과 SEC 수집 큐 연결
   - SEC 데이터 fresh면 기존 분석 흐름 유지
   - 데이터 없거나 24시간 초과면 수집 job 생성 및 사용자 안내
   - callback 분석 요청과 자연어 분석 요청 모두 적용

4. 운영 스크립트/문서/env 정리
   - `SEC_USER_AGENT` 설정 추가
   - `scripts/run_sec_ingest_worker.sh`
   - launch agent install/restart/uninstall에 SEC worker 반영
   - README 업데이트

## 커밋 운영 규칙

남은 작업은 단계별로 나누어 진행한다. 각 단계마다 커밋 직전에 메시지와 변경 요약, 검증 결과를 사용자에게 보여주고 명시 승인을 받은 뒤 커밋한다.
