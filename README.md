# mcp-network-tools

MCP-сервер с сетевыми инструментами и агент, который пользуется ими
через модель NVIDIA на OpenRouter.

MCP (Model Context Protocol) — протокол, по которому нейросеть вызывает
внешние инструменты. Здесь сервер даёт модели четыре инструмента:

| Инструмент    | Что делает                                              |
|---------------|---------------------------------------------------------|
| `subnet_info` | параметры подсети: адрес сети, маска, broadcast, хосты  |
| `same_subnet` | находятся ли два адреса в одной подсети                 |
| `ping`        | ping до узла                                            |
| `dns_lookup`  | IP-адреса доменного имени                               |

## Установка

Нужен [uv](https://docs.astral.sh/uv/).

```sh
git clone https://github.com/dadashi44/mcp-network-tools.git
cd mcp-network-tools
uv sync
```

## Агент с моделью NVIDIA через OpenRouter

1. Создайте ключ на <https://openrouter.ai/keys>.
2. Скопируйте `.env.example` в `.env` и вставьте ключ в `OPENROUTER_API_KEY`.
3. Запустите:

```sh
uv run agent.py "В одной ли сети 10.0.0.5 и 10.0.1.7 при маске 255.255.254.0?"
```

Агент запускает `server.py`, передаёт модели список инструментов и выполняет
вызовы, которые она запрашивает. По умолчанию используется модель
`nvidia/nemotron-3.5-lightning:free`; другую можно задать в `OPENROUTER_MODEL`.

## Подключение сервера к Claude Code

```sh
claude mcp add network-tools -- uv run --directory /полный/путь/к/mcp-network-tools server.py
```

После этого инструменты доступны в чате, например:
«посчитай подсеть 192.168.1.10/26».
