"""Small network helpers used by SSDP and the NVA server."""

import email.utils
import ipaddress
import random
import socket
import string

def _usable_ip(ip):
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return not (addr.is_loopback or addr.is_unspecified or addr.is_link_local
                or addr.is_multicast)


def _is_private(ip):
    try:
        return ipaddress.ip_address(ip).is_private
    except ValueError:
        return False


def get_local_ips():
    """Best-effort list of IPv4 addresses on this machine."""
    found = []

    # The hostname path works on many desktop Linux/macOS systems.
    try:
        for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
            if _usable_ip(ip):
                found.append(ip)
    except OSError:
        pass

    # The connect trick works on Android, where gethostname() often returns
    # localhost. UDP connect does not send a packet.
    for target in (("8.8.8.8", 80), ("1.1.1.1", 80), ("192.168.1.1", 80)):
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(0.4)
            sock.connect(target)
            ip = sock.getsockname()[0]
            if _usable_ip(ip):
                found.append(ip)
        except OSError:
            pass
        finally:
            if sock is not None:
                sock.close()

    # Stable order, de-duplicated.
    result = []
    for ip in found:
        if ip not in result:
            result.append(ip)

    # Prefer RFC1918 addresses if both a public and a private address exist.
    private = [ip for ip in result if _is_private(ip)]
    if private:
        return private + [ip for ip in result if ip not in private]
    return result


def get_primary_ip():
    ips = get_local_ips()
    return ips[0] if ips else "127.0.0.1"


def choose_local_ip(peer_ip, local_ips=None):
    """Pick the local address most likely to be reachable from peer_ip."""
    ips = local_ips or get_local_ips()
    if not ips:
        return "127.0.0.1"
    try:
        peer = ipaddress.ip_address(peer_ip)
    except ValueError:
        return ips[0]

    peer_prefix = ".".join(str(peer).split(".")[:3])
    for ip in ips:
        if ".".join(ip.split(".")[:3]) == peer_prefix:
            return ip
    return ips[0]


def http_date():
    return email.utils.formatdate(usegmt=True)


def random_suffix(length=35):
    alphabet = string.ascii_uppercase + string.digits
    return "".join(random.choice(alphabet) for _ in range(length))


def make_tv_uuid():
    """Bilibili TV UUIDs look like XY + 35 uppercase alphanumeric chars."""
    return "XY" + random_suffix(35)


def make_session_id():
    import uuid

    return str(uuid.uuid4())
