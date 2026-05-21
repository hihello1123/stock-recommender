# Global Equity Lens Bot

텔레그램에서 미국 상장기업을 조회하고, 재무 데이터와 간단한 품질 점수를 보여주는 개인용 봇입니다.

이 저장소의 현재 범위는 회사 평가와 정보 조회까지입니다.

- 실제 주식 매수 없음
- 자동 주문 없음
- 계좌 조회 없음
- 랭킹 없음
- 다중 렌즈 없음

## 지금 할 수 있는 것

- `/start`
- `/help`
- `/ping`
- `/company AAPL`

`/company`는 다음을 보여줍니다.

- 회사 기본 정보
- 데이터 출처
- 기준일
- 누락 필드
- `Quality Lens v1` 점수
- 평가 신뢰도
- 추가 확인사항

## 준비물

- Python 3.11 이상
- `uv`
- Telegram Bot Token
- 허용할 Telegram `chat_id` 목록

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
ALLOWED_TELEGRAM_CHAT_IDS=123456789
```

`ALLOWED_TELEGRAM_CHAT_IDS`는 쉼표로 여러 개를 넣을 수 있습니다.

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

## macOS 백그라운드 실행

`launchd`를 쓰면 로그인 후 자동으로 봇을 올리고, 재시작도 관리할 수 있습니다.

### 1. 실행 스크립트 만들기

`scripts/run_bot.sh`

```bash
#!/bin/zsh
cd /path/to/stock-recommander

exec "$(command -v uv)" run python manage.py run_telegram_bot
```

```bash
chmod +x /path/to/stock-recommander/scripts/run_bot.sh
```

### 2. LaunchAgent 등록

`~/Library/LaunchAgents/com.george.stockrecommender.bot.plist`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>com.george.stockrecommender.bot</string>
    <key>ProgramArguments</key>
    <array>
      <string>/path/to/stock-recommander/scripts/run_bot.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>WorkingDirectory</key>
    <string>/path/to/stock-recommander</string>
    <key>StandardOutPath</key>
    <string>/path/to/stock-recommander/bot.out.log</string>
    <key>StandardErrorPath</key>
    <string>/path/to/stock-recommander/bot.err.log</string>
  </dict>
</plist>
```

### 3. 시작

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.george.stockrecommender.bot.plist
launchctl enable gui/$(id -u)/com.george.stockrecommender.bot
launchctl kickstart -k gui/$(id -u)/com.george.stockrecommender.bot
```

### 4. 상태 확인

```bash
launchctl print gui/$(id -u)/com.george.stockrecommender.bot
tail -f /path/to/stock-recommander/bot.out.log
tail -f /path/to/stock-recommander/bot.err.log
```

### 5. 중지

```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.george.stockrecommender.bot.plist
```

## Telegram 명령어

### `/start`

봇 소개를 보여줍니다.

### `/help`

사용 가능한 명령어를 보여줍니다.

### `/ping`

연결 상태를 확인합니다.

### `/company TICKER`

회사 기본 정보와 품질 점수를 조회합니다.

예:

```text
/company AAPL
/company MSFT
/company O
```

`ALLOWED_TELEGRAM_CHAT_IDS`에 없는 사용자는 모든 명령이 차단됩니다. 그룹 채팅도 차단됩니다.

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

해석
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
- 설명은 템플릿 기준으로 제한합니다.
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
- `/company` 통합 경로

## 다음 단계

현재 v1 이후에 붙일 후보는 다음 순서입니다.

1. `/watch`, `/unwatch`, `/watchlist`
2. 렌즈 확장
3. 주간 리포트
4. LLM 설명
5. 모의투자

실제 주문과 계좌 조회는 별도 판단이 필요합니다.
