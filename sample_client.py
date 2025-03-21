import asyncio
import requests

from openai import AsyncOpenAI

story = requests.get("https://poneb.in/raw/y3xpbMgb").text


async def main():
    oai_client = AsyncOpenAI(
        base_url="http://0.0.0.0:8001/api/v1",
        api_key="none",  # API key not needed for local server
    )

    response = await oai_client.chat.completions.create(
        model="Applejack",  # Use a pony name with a known profile
        messages=[{"role": "user", "content": story}],
    )

    print(response.choices[0].message.content)


asyncio.run(main())
