"""Minecraft server status fetching logic"""
from typing import Optional, Tuple
from mcstatus import JavaServer
from mcstatus.status_response import JavaStatusResponse
import socket
import ipaddress


def is_private_ip(hostname: str) -> bool:
    """
    Check if a hostname resolves to a private/internal IP address.

    Args:
        hostname: Hostname or IP address to check

    Returns:
        True if the address is private/internal, False otherwise
    """
    try:
        # Try to parse as IP address directly
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        # Not a valid IP, try to resolve hostname
        try:
            resolved_ip = socket.gethostbyname(hostname)
            ip = ipaddress.ip_address(resolved_ip)
        except (socket.gaierror, socket.herror):
            # Cannot resolve hostname
            raise ValueError(f"Cannot resolve hostname: {hostname}")

    # Check if IP is private, loopback, link-local, or reserved
    return (
        ip.is_private or
        ip.is_loopback or
        ip.is_link_local or
        ip.is_reserved or
        ip.is_multicast
    )


def validate_server_address(hostname: str, port: int) -> None:
    """
    Validate server address for SSRF protection.

    Args:
        hostname: Server hostname or IP
        port: Server port

    Raises:
        ValueError: If the address is invalid or blocked for security reasons
    """
    # Validate port range
    if not (1 <= port <= 65535):
        raise ValueError(f"Port must be between 1 and 65535, got {port}")

    # Minecraft servers typically use ports 25500-25600 or custom high ports
    # Block well-known service ports to prevent port scanning
    blocked_ports = {
        20, 21,    # FTP
        22,        # SSH
        23,        # Telnet
        25,        # SMTP
        80, 443,   # HTTP/HTTPS
        110,       # POP3
        143,       # IMAP
        3306,      # MySQL
        5432,      # PostgreSQL
        6379,      # Redis
        27017,     # MongoDB
    }

    if port in blocked_ports:
        raise ValueError(f"Port {port} is not allowed for security reasons")

    # Check for private/internal IPs (SSRF protection)
    if is_private_ip(hostname):
        raise ValueError(f"Access to private/internal IP addresses is not allowed")


def parse_server_address(ip: str) -> Tuple[str, int]:
    """
    Parse server address, handling ip:port format.

    Args:
        ip: Server address, can be "host" or "host:port"

    Returns:
        Tuple of (host, port)

    Raises:
        ValueError: If address is invalid or blocked
    """
    if ':' in ip:
        host, port_str = ip.rsplit(':', 1)
        try:
            port = int(port_str)
        except ValueError:
            raise ValueError(f"Invalid port: {port_str}")
    else:
        host = ip
        port = 25565

    # Validate for SSRF protection
    validate_server_address(host, port)

    return host, port


def fetch_server_status(ip: str, timeout: float = 5.0) -> Optional[JavaStatusResponse]:
    """
    Fetch Minecraft server status.
    
    Args:
        ip: Server address (host or host:port)
        timeout: Connection timeout in seconds
        
    Returns:
        JavaStatusResponse if server is online, None if offline
    """
    try:
        host, port = parse_server_address(ip)
        server = JavaServer(host, port)
        status = server.status()
        return status
    except (socket.timeout, ConnectionRefusedError, OSError, ValueError):
        return None


def get_server_info(ip: str) -> dict:
    """
    Get server information including MOTD, players, version, and icon.
    
    Args:
        ip: Server address (host or host:port)
        
    Returns:
        Dictionary with server information:
        - online: bool
        - motd: str (raw MOTD text)
        - players_online: int
        - players_max: int
        - version: str
        - favicon: Optional[str] (base64 encoded icon)
    """
    status = fetch_server_status(ip)
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
    
    # Extract MOTD text - handle both string and dict formats
    motd_text = ""
    description = status.description
    
    # Handle different description formats
    if isinstance(description, str):
        motd_text = description
    elif hasattr(description, 'text'):
        # Handle object with text attribute
        motd_text = str(description.text) if description.text else ""
        # Also check for extra attribute
        if hasattr(description, 'extra') and description.extra:
            extra_text = "".join(
                str(item.get('text', '')) if isinstance(item, dict) else str(item)
                for item in description.extra
            )
            motd_text = motd_text + extra_text
    elif isinstance(description, dict):
        # Handle JSON text component format
        if 'text' in description:
            motd_text = str(description['text'])
        if 'extra' in description:
            # Extract text from extra array
            extra_text = "".join(
                str(item.get('text', '')) if isinstance(item, dict) else str(item)
                for item in description.get('extra', [])
            )
            motd_text = motd_text + extra_text
    
    # If still empty, try to convert to string
    if not motd_text:
        motd_text = str(description) if description else "No MOTD"
    
    # Extract server name (version name or use IP as fallback)
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
