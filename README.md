# Global Equity Lens Bot

텔레그램 기반 미국 주식 평가 봇입니다. 현재 단계에서는 실제 매수, 주문, 계좌 조회 기능을 만들지 않습니다.

## 개발 환경

```bash
uv sync
uv run python manage.py check
uv run python manage.py test
```

## 설정

`.env.example`을 참고해 로컬 환경변수를 설정합니다.

```bash
DJANGO_SECRET_KEY=replace-me
DJANGO_DEBUG=true
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
TELEGRAM_BOT_TOKEN=replace-me
ALLOWED_TELEGRAM_CHAT_IDS=123456789
```

## 현재 범위

현재 구현된 범위는 Django 프로젝트 골격과 텔레그램 기본 명령어입니다.

```bash
uv run python manage.py run_telegram_bot
```

지원 명령어:

- `/start`
- `/help`
- `/ping`

`ALLOWED_TELEGRAM_CHAT_IDS`에 없는 사용자는 모든 명령어가 차단됩니다.
