# Global Equity Lens Bot

텔레그램에서 미국 상장기업을 조회하고, 재무 데이터와 품질 점수, 로컬 LLM 기반 대가별 해석을 보여주는 개인용 봇입니다.

이 저장소의 현재 범위는 회사 평가와 정보 조회까지입니다.

- 실제 주식 매수 없음
- 자동 주문 없음
- 계좌 조회 없음
- 랭킹 없음
- 실제 투자 조언 없음

## 지금 할 수 있는 것

- `/start`
- `/help`
- `/ping`
- `/company AAPL`
- `/watch AAPL`
- `/unwatch AAPL`
- `/watchlist`

`/company`는 회사를 먼저 확인한 뒤, 선택한 투자자 관점의 분석을 대기열에 넣습니다.
분석이 끝나면 텔레그램 새 메시지로 다음 내용을 보내줍니다.

- 회사 기본 정보
- 데이터 출처
- 기준일
- 누락 필드
- `Quality Lens v1` 점수
- 평가 신뢰도
- 선택한 투자자 관점의 로컬 LLM 해석
- 추가 확인사항

관심종목 명령어는 나중에 일일 뉴스 리포트와 주간 리포트의 대상 목록으로 사용합니다.

## 준비물

- Python 3.11 이상
- `uv`
- Telegram Bot Token

## 설치

```bash
uv sync
uv run python manage.py migrate
```

## 환경변수 설정

코드는 저장소 루트의 `.env`를 자동으로 읽습니다. 셸에 직접 `export`할 필요는 없습니다.
셸 환경변수가 이미 설정돼 있으면 그 값이 `.env`보다 우선합니다.

`.env.example`을 참고해서 `.env`를 만들고 값을 채우세요.

```bash
DJANGO_SECRET_KEY=replace-me
DJANGO_DEBUG=true
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
TELEGRAM_BOT_TOKEN=replace-me
LOCAL_LLM_MODEL=
LOCAL_LLM_BASE_URL=http://127.0.0.1:11434
LOCAL_LLM_TIMEOUT_SECONDS=60
```

봇 토큰은 서버에서만 사용합니다. 텔레그램 사용자에게 공유하지 않습니다.
`LOCAL_LLM_MODEL`을 비워두면 대가별 LLM 해석은 생략됩니다. Ollama를 쓴다면 예를 들어 `LOCAL_LLM_MODEL=qwen3.6:27b`처럼 로컬에 설치된 모델명을 넣습니다.

## 실행

기본 검증:

```bash
uv run python manage.py check
uv run python manage.py test
```

텔레그램 봇 실행:

```bash
uv run python manage.py run_telegram_bot
```

분석 워커 실행:

```bash
uv run python manage.py run_analysis_worker
```

`run_telegram_bot`은 텔레그램 명령과 버튼을 받는 프로세스입니다.
`run_analysis_worker`는 오래 걸리는 로컬 LLM 분석 작업을 하나씩 처리하는 프로세스입니다.
로컬에서 직접 실행할 때는 두 명령을 각각 다른 터미널에서 실행하세요.

## macOS 백그라운드 실행

`launchd`를 쓰면 로그인 후 자동으로 봇을 올리고, 재시작도 관리할 수 있습니다.
저장소에는 `launchd` 등록 스크립트가 포함되어 있습니다.

### 1. 설치 및 시작

먼저 `.env`와 DB migration이 준비되어 있어야 합니다.

```bash
uv sync
uv run python manage.py migrate
./scripts/install_launch_agent.sh
```

이 스크립트는 현재 저장소 경로를 기준으로 두 개의 서비스를 생성하고 시작합니다.

- `~/Library/LaunchAgents/com.george.stockrecommender.bot.plist`
- `~/Library/LaunchAgents/com.george.stockrecommender.worker.plist`

### 2. 상태 확인

```bash
launchctl print gui/$(id -u)/com.george.stockrecommender.bot
launchctl print gui/$(id -u)/com.george.stockrecommender.worker
tail -f logs/bot.out.log logs/bot.err.log logs/worker.out.log logs/worker.err.log
```

### 3. 코드 변경 후 재시작

로컬에서 코드만 바꿔 쓰는 경우에는 원격에서 받을 내용이 없으므로 `git pull`은 필요 없습니다.

```bash
./scripts/restart_bot.sh
```

이 스크립트는 `uv sync`, `migrate`, 봇 재시작, 분석 워커 재시작을 순서대로 실행합니다.
DB가 아직 없어도 `migrate` 단계에서 `db.sqlite3`를 만들고 필요한 테이블을 생성합니다.

### 4. 중지 및 제거

```bash
./scripts/uninstall_launch_agent.sh
```

## Telegram 명령어

### `/start`

봇 소개를 보여줍니다.

### `/help`

사용 가능한 명령어를 보여줍니다.

### `/ping`

연결 상태를 확인합니다.

### `/company TICKER`

회사 기본 정보를 먼저 보여주고, `Buffett`, `Graham`, `Lynch`, `Munger` 버튼 중 하나를 선택합니다.
버튼을 누르면 분석 작업이 대기열에 들어가고, 봇은 먼저 대기 순서를 알려줍니다.
분석 워커가 작업을 완료하면 선택한 투자자 관점의 품질 점수 리포트와 로컬 LLM 해석을 새 메시지로 보냅니다.

예:

```text
/company AAPL
/company MSFT
/company O
```

### `/watch TICKER`

회사 기본 정보를 먼저 보여주고, 맞는 회사인지 확인합니다. 확인 버튼을 누르면 관심종목에 추가하고 DB에 저장합니다.

```text
/watch AAPL
```

### `/unwatch TICKER`

관심종목에서 회사를 제거합니다.

```text
/unwatch AAPL
```

### `/watchlist`

현재 관심종목 목록을 보여줍니다.

개인 채팅에서는 누구나 사용할 수 있습니다. 그룹 채팅은 차단됩니다.

## 응답 예시

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
- FCF가 양수입니다.
- 현금이 총부채 이상입니다.

주의
- ROIC 데이터가 없습니다.

선택한 대가 해석
[Buffett]
- 좋은 점: ...
- 아쉬운 점: ...
- 확인할 것: ...

주의
이 결과는 자동 매수 신호가 아닙니다.
가격, 최근 실적, 업종 리스크를 직접 확인해야 합니다.
```

## 현재 구현된 구조

- Django 프로젝트 골격
- Telegram 기본 봇
- 접근 제어
- 회사/스냅샷 DB 모델
- yfinance 기반 데이터 조회
- 데이터 정규화
- 업종/상품 유형 분류
- `Quality Lens v1`
- 로컬 LLM 기반 대가별 해석
- DB 기반 분석 작업 대기열
- 단일 분석 워커
- `/company` 결과 렌더링

## 데이터 소스

현재는 `yfinance`를 첫 번째 데이터 소스로 사용합니다.

이 때문에 다음 상황이 생길 수 있습니다.

- 일부 필드가 비어 있을 수 있음
- 지연되거나 오래된 데이터가 들어올 수 있음
- 종목별로 신뢰도가 크게 다를 수 있음

그래서 이 봇은 점수만 보여주지 않고 데이터 완성도와 신뢰도도 같이 보여줍니다.

## 개발 메모

- 점수는 코드가 계산합니다.
- 설명은 로컬 LLM이 생성하되, 점수 계산은 코드 결과만 사용합니다.
- 로컬 LLM 호출은 워커가 하나씩 처리합니다. 여러 사용자가 동시에 눌러도 봇 응답은 먼저 돌아가고, 분석 결과는 완료 후 새 메시지로 전송됩니다.
- 일반 품질 점수를 쓰기 어려운 업종은 낮은 신뢰도로 처리합니다.
- 실제 주문 기능은 아직 넣지 않습니다.

## 테스트

```bash
uv run python manage.py test
```

현재 테스트는 다음을 확인합니다.

- 텔레그램 명령어 응답
- 접근 제어
- DB 모델 제약
- 시장 데이터 정규화
- `Quality Lens v1`
- 분석 작업 큐와 워커
- `/company` 통합 경로

## 다음 단계

현재 v1 이후에 붙일 후보는 다음 순서입니다.

1. `/watch`, `/unwatch`, `/watchlist`
2. 렌즈 확장
3. 주간 리포트
4. 모의투자

실제 주문과 계좌 조회는 별도 판단이 필요합니다.
