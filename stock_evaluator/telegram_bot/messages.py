def start_message() -> str:
    return (
        "Global Equity Lens Bot입니다.\n"
        "현재는 기본 동작 확인 단계입니다.\n"
        "/help 명령어로 사용 가능한 명령어를 확인하세요."
    )


def help_message() -> str:
    return "\n".join(
        [
            "사용 가능한 명령어",
            "/start - 봇 소개",
            "/help - 도움말",
            "/ping - 연결 확인",
            "/company TICKER - 회사 기본 평가",
            "/watch TICKER - 관심종목 추가",
            "/unwatch TICKER - 관심종목 제거",
            "/watchlist - 관심종목 목록",
        ]
    )
