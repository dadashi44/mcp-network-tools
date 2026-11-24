"""Агент: модель NVIDIA (через OpenRouter) + инструменты MCP-сервера.

Скрипт запускает server.py как MCP-сервер, передаёт модели список
его инструментов и выполняет вызовы, которые модель запрашивает,
пока она не даст окончательный ответ.

Запуск:  uv run agent.py "ваш вопрос"
Ключ:    переменная OPENROUTER_API_KEY (или файл .env рядом со скриптом)
"""

import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import AsyncOpenAI

HERE = Path(__file__).parent
DEFAULT_MODEL = "nvidia/nemotron-3.5-lightning:free"
DEFAULT_QUESTION = (
    "У меня два компьютера: 192.168.1.1 и 192.168.1.2, маска 255.255.255.0. "
    "Могут ли они общаться напрямую? Сколько всего хостов помещается в эту сеть?"
)
MAX_STEPS = 8


def to_openai_tool(tool) -> dict:
    """Перевести описание инструмента MCP в формат OpenAI/OpenRouter."""
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": tool.input_schema,
        },
    }


def result_text(result) -> str:
    """Собрать текстовый ответ инструмента MCP в одну строку."""
    parts = [block.text for block in result.content if getattr(block, "text", None)]
    text = "\n".join(parts) or "(пустой ответ)"
    return f"ОШИБКА: {text}" if result.is_error else text


async def main() -> int:
    load_dotenv(HERE / ".env")
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print(
            "Не задан OPENROUTER_API_KEY. Скопируйте .env.example в .env "
            "и вставьте туда ключ с https://openrouter.ai/keys",
            file=sys.stderr,
        )
        return 1

    model = os.environ.get("OPENROUTER_MODEL", DEFAULT_MODEL)
    question = " ".join(sys.argv[1:]) or DEFAULT_QUESTION
    client = AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
    server = StdioServerParameters(command=sys.executable, args=[str(HERE / "server.py")])

    async with stdio_client(server) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        tools = (await session.list_tools()).tools
        print(f"Модель: {model}")
        print(f"Инструменты MCP: {', '.join(t.name for t in tools)}")
        print(f"\nВопрос: {question}\n")

        messages = [
            {
                "role": "system",
                "content": "Ты сетевой помощник. Для расчётов и проверок используй "
                "инструменты, а не считай в уме. Отвечай кратко, по-русски.",
            },
            {"role": "user", "content": question},
        ]

        for _ in range(MAX_STEPS):
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                tools=[to_openai_tool(t) for t in tools],
            )
            message = response.choices[0].message
            if not message.tool_calls:
                print(f"Ответ: {message.content}")
                return 0

            messages.append(message.model_dump(exclude_none=True))
            for call in message.tool_calls:
                try:
                    args = json.loads(call.function.arguments or "{}")
                    output = result_text(await session.call_tool(call.function.name, args))
                except Exception as error:  # ошибку возвращаем модели, чтобы она исправилась
                    args, output = call.function.arguments, f"ОШИБКА: {error}"
                print(f"-> {call.function.name}({args})")
                print(f"<- {output}\n")
                messages.append({"role": "tool", "tool_call_id": call.id, "content": output})

        print(f"Модель не дала ответ за {MAX_STEPS} шагов.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
