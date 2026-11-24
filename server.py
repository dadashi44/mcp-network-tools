"""MCP-сервер с сетевыми инструментами.

Сервер отдаёт нейросети четыре инструмента для работы с IP-сетями:
расчёт подсети, проверку, что два адреса лежат в одной сети,
ping и DNS-запрос.

Запуск (транспорт stdio):  uv run server.py
"""

import ipaddress
import socket
import subprocess

from mcp.server.mcpserver import MCPServer

mcp = MCPServer("network-tools")


@mcp.tool()
def subnet_info(cidr: str) -> dict:
    """Рассчитать параметры IPv4-подсети.

    cidr — адрес с префиксом или маской, например "192.168.1.10/24"
    или "192.168.1.10/255.255.255.0".
    """
    net = ipaddress.ip_network(cidr, strict=False)
    hosts = max(net.num_addresses - 2, 0) if net.prefixlen < 31 else net.num_addresses
    return {
        "network": str(net.network_address),
        "prefix": net.prefixlen,
        "netmask": str(net.netmask),
        "broadcast": str(net.broadcast_address),
        "first_host": str(net.network_address + 1) if net.prefixlen < 31 else str(net.network_address),
        "last_host": str(net.broadcast_address - 1) if net.prefixlen < 31 else str(net.broadcast_address),
        "usable_hosts": hosts,
    }


@mcp.tool()
def same_subnet(ip_a: str, ip_b: str, netmask: str) -> dict:
    """Проверить, находятся ли два IPv4-адреса в одной подсети.

    Если да, устройства могут общаться напрямую, без маршрутизатора.
    """
    net_a = ipaddress.ip_network(f"{ip_a}/{netmask}", strict=False)
    net_b = ipaddress.ip_network(f"{ip_b}/{netmask}", strict=False)
    return {
        "ip_a_network": str(net_a),
        "ip_b_network": str(net_b),
        "same_subnet": net_a == net_b,
    }


@mcp.tool()
def ping(host: str, count: int = 4) -> str:
    """Выполнить ping до узла и вернуть вывод команды.

    host — IP-адрес или доменное имя, count — число пакетов (от 1 до 10).
    """
    if not host or host.startswith("-"):
        raise ValueError("некорректное имя узла")
    count = min(max(count, 1), 10)
    try:
        result = subprocess.run(
            ["ping", "-c", str(count), host],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        return f"ping до {host} не завершился за 30 секунд"
    return (result.stdout + result.stderr).strip()


@mcp.tool()
def dns_lookup(hostname: str) -> list[str]:
    """Получить IP-адреса доменного имени."""
    infos = socket.getaddrinfo(hostname, None)
    return sorted({info[4][0] for info in infos})


if __name__ == "__main__":
    mcp.run()
