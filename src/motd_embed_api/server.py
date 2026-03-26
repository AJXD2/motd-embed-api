"""Minecraft server status fetching logic"""

import socket
import ipaddress
import time
from typing import Optional, Tuple

from mcstatus import JavaServer
from mcstatus.responses import JavaStatusResponse

from .metrics import SERVER_QUERIES_TOTAL, SERVER_QUERY_DURATION


def is_private_ip(hostname: str) -> bool:
    """
    Check if a hostname resolves to a private/internal IP address.

    Returns:
        True if the address is private/internal, False otherwise

    Raises:
        ValueError: If the hostname cannot be resolved
    """
    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        try:
            resolved_ip = socket.gethostbyname(hostname)
            ip = ipaddress.ip_address(resolved_ip)
        except (socket.gaierror, socket.herror):
            raise ValueError(f"Cannot resolve hostname: {hostname}")

    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
    )


def validate_server_address(hostname: str, port: int) -> None:
    """
    Validate server address for SSRF protection.

    Raises:
        ValueError: If the address is invalid or blocked
    """
    if not (1 <= port <= 65535):
        raise ValueError(f"Port must be between 1 and 65535, got {port}")

    blocked_ports = {
        20,
        21,  # FTP
        22,  # SSH
        23,  # Telnet
        25,  # SMTP
        80,
        443,  # HTTP/HTTPS
        110,  # POP3
        143,  # IMAP
        3306,  # MySQL
        5432,  # PostgreSQL
        6379,  # Redis
        27017,  # MongoDB
    }

    if port in blocked_ports:
        raise ValueError(f"Port {port} is not allowed for security reasons")

    if is_private_ip(hostname):
        raise ValueError("Access to private/internal IP addresses is not allowed")


def parse_server_address(ip: str, max_address_length: int = 253) -> Tuple[str, int]:
    """
    Parse server address, handling ip:port format.

    Returns:
        Tuple of (host, port)

    Raises:
        ValueError: If address is invalid, too long, or blocked
    """
    if ":" in ip:
        host, port_str = ip.rsplit(":", 1)
        try:
            port = int(port_str)
        except ValueError:
            raise ValueError(f"Invalid port: {port_str}")
    else:
        host = ip
        port = 25565

    if len(host) > max_address_length:
        raise ValueError("Server address is too long")

    validate_server_address(host, port)
    return host, port


def fetch_server_status(
    ip: str,
    timeout: float = 5.0,
    max_address_length: int = 253,
) -> Optional[JavaStatusResponse]:
    """
    Fetch Minecraft server status.

    Returns:
        JavaStatusResponse if server is online, None if connection failed

    Raises:
        ValueError: If the address is invalid (propagates for 400 response)
    """
    # Raises ValueError for invalid/private addresses — let it propagate
    host, port = parse_server_address(ip, max_address_length=max_address_length)

    start = time.perf_counter()
    try:
        server = JavaServer(host, port, timeout=timeout)
        status = server.status()
        SERVER_QUERIES_TOTAL.labels(result="online").inc()
        SERVER_QUERY_DURATION.observe(time.perf_counter() - start)
        return status
    except (socket.timeout, ConnectionRefusedError, OSError):
        SERVER_QUERIES_TOTAL.labels(result="offline").inc()
        SERVER_QUERY_DURATION.observe(time.perf_counter() - start)
        return None
    except Exception:
        SERVER_QUERIES_TOTAL.labels(result="error").inc()
        SERVER_QUERY_DURATION.observe(time.perf_counter() - start)
        return None


def get_server_info(ip: str, timeout: float = 5.0) -> dict:
    """
    Get server information including MOTD, players, version, and icon.

    Returns:
        Dictionary with keys: online, motd, server_name, players_online,
        players_max, version, favicon
    """
    status = fetch_server_status(ip, timeout=timeout)
    if status is None:
        return {
            "online": False,
            "motd": "Server Offline",
            "server_name": ip,
            "players_online": 0,
            "players_max": 0,
            "version": "Unknown",
            "favicon": None,
        }

    # Extract MOTD text — handle string, dict, and object formats
    motd_text = ""
    description = status.description

    if isinstance(description, str):
        motd_text = description
    elif hasattr(description, "text"):
        motd_text = str(description.text) if description.text else ""
        if hasattr(description, "extra") and description.extra:
            extra_text = "".join(
                str(item.get("text", "")) if isinstance(item, dict) else str(item)
                for item in description.extra
            )
            motd_text = motd_text + extra_text
    elif isinstance(description, dict):
        if "text" in description:
            motd_text = str(description["text"])
        if "extra" in description:
            extra_text = "".join(
                str(item.get("text", "")) if isinstance(item, dict) else str(item)
                for item in description.get("extra", [])
            )
            motd_text = motd_text + extra_text

    if not motd_text:
        motd_text = str(description) if description else "No MOTD"

    server_name = status.version.name if status.version else ip

    return {
        "online": True,
        "motd": motd_text or "No MOTD",
        "server_name": server_name,
        "players_online": status.players.online if status.players else 0,
        "players_max": status.players.max if status.players else 0,
        "version": status.version.name if status.version else "Unknown",
        "favicon": status.icon,
    }
