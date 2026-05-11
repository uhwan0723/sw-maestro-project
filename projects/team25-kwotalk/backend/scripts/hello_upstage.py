"""환경 검증용 스크립트 — Upstage Solar API 연결 확인."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from openai import AsyncOpenAI


async def main() -> None:
    api_key = os.getenv("UPSTAGE_API_KEY")
    if not api_key:
        print("[오류] UPSTAGE_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")
        sys.exit(1)

    client = AsyncOpenAI(api_key=api_key, base_url="https://api.upstage.ai/v1")
    print("Upstage Solar API 연결 테스트 중...")

    response = await client.chat.completions.create(
        model="solar-mini",
        messages=[
            {"role": "user", "content": "한국어로 '안녕하세요, Solar입니다.'라고만 답하세요."},
        ],
    )
    print(f"응답: {response.choices[0].message.content.strip()}")
    print("✓ Upstage Solar API 연결 성공")


if __name__ == "__main__":
    asyncio.run(main())
