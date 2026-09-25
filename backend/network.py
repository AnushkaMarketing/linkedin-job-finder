"""No browser credentials. DNS is validated then pinned for each connection.

Only public HTTP(S), port 80/443. Redirects are revalidated. Fetches are bounded,
cached and per-host serialized; robots rules are checked for HTML collection.
"""
import asyncio
import hashlib
import http.client
import ipaddress
import json
import socket
import ssl
import time
from urllib.parse import urlsplit, urljoin
from urllib.robotparser import RobotFileParser
from .models import web_url

USER_AGENT = 'LocalJobIntelligence/1.0'


class SourceError(Exception):
    def __init__(self, state: str, message: str):
        self.state, self.message = state, message
        super().__init__(message)


def resolve_public(url: str) -> tuple[str, str, int]:
    web_url(url)
    p = urlsplit(url)
    port = p.port or (443 if p.scheme == 'https' else 80)
    if port not in (80, 443): raise SourceError('Source unavailable', 'Only public web ports are permitted')
    host = p.hostname.encode('idna').decode()
    try:
        addresses = {entry[4][0] for entry in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)}
    except OSError:
        raise SourceError('Temporary failure', 'DNS lookup failed') from None
    if not addresses or any(not ipaddress.ip_address(ip).is_global for ip in addresses):
        raise SourceError('Source unavailable', 'Private, loopback, reserved and link-local destinations are blocked')
    return host, sorted(addresses)[0], port


def fetch_pinned(url: str, max_bytes: int = 4_000_000) -> dict:
    host, ip, port = resolve_public(url)
    parsed = urlsplit(url)
    connection = http.client.HTTPConnection(host, port=port, timeout=12)
    def connect():
        sock = socket.create_connection((ip, port), timeout=12)
        if parsed.scheme == 'https':
            sock = ssl.create_default_context().wrap_socket(sock, server_hostname=host)
        connection.sock = sock
    connection.connect = connect
    try:
        route = parsed.path or '/'
        if parsed.query: route += '?' + parsed.query
        connection.request('GET', route, headers={'Host': host, 'User-Agent': USER_AGENT, 'Accept': 'application/json,text/html,text/plain', 'Accept-Encoding': 'identity'})
        response = connection.getresponse()
        raw = response.read(max_bytes + 1)
        if len(raw) > max_bytes: raise SourceError('Source unavailable', 'Response exceeds collection limit')
        return {'status': response.status, 'headers': dict(response.getheaders()), 'body': raw.decode('utf-8', errors='replace'), 'url': url}
    finally:
        connection.close()


class Network:
    def __init__(self, store):
        self.store = store
        self.locks: dict[str, asyncio.Lock] = {}
        self.last: dict[str, float] = {}
        self.failures: dict[str, int] = {}
        self.open_until: dict[str, float] = {}
        self.calls = 0
        self.hits = 0

    async def get(self, url: str, ttl: float = 900, robots: bool = False, redirects: int = 0) -> dict:
        web_url(url)
        if redirects > 4: raise SourceError('Temporary failure', 'Too many redirects')
        parsed = urlsplit(url)
        # Resolve even cached URLs to prevent private endpoints from entering the cache path.
        await asyncio.to_thread(resolve_public, url)
        key = hashlib.sha256(url.encode()).hexdigest()
        if cached := self.store.get('cache', key):
            self.hits += 1; return cached
        host = parsed.hostname
        if self.open_until.get(host, 0) > time.monotonic():
            raise SourceError('Rate limited', 'Source cooldown active; try later')
        if robots:
            robot_url = f'{parsed.scheme}://{parsed.netloc}/robots.txt'
            try:
                rules = await self.get(robot_url, ttl=86400)
            except SourceError as exc:
                raise SourceError(exc.state, 'Unable to check robots policy; skipped page') from None
            if rules['status'] == 200:
                robot = RobotFileParser(); robot.parse(rules['body'].splitlines())
                if not robot.can_fetch(USER_AGENT, url): raise SourceError('Source unavailable', 'robots.txt disallows automated access')
            elif rules['status'] not in (404, 410):
                raise SourceError('Source unavailable', 'Robots policy unavailable')
        async with self.locks.setdefault(host, asyncio.Lock()):
            if cached := self.store.get('cache', key):
                self.hits += 1; return cached
            for attempt in range(2):
                await asyncio.sleep(max(0, 1.1 - (time.monotonic() - self.last.get(host, 0))))
                self.last[host] = time.monotonic(); self.calls += 1
                try:
                    result = await asyncio.to_thread(fetch_pinned, url)
                except (OSError, http.client.HTTPException, ssl.SSLError):
                    result = {'status': 503, 'headers': {}, 'body': '', 'url': url}
                code = result['status']
                if code in (401, 403): raise SourceError('Authentication required', 'Access denied; sign in normally or import a listing')
                if code == 429:
                    self.open_until[host] = time.monotonic() + 300
                    raise SourceError('Rate limited', 'Source returned HTTP 429; no further requests for five minutes')
                if code >= 500:
                    self.failures[host] = self.failures.get(host, 0) + 1
                    if self.failures[host] >= 3: self.open_until[host] = time.monotonic() + 120
                    if attempt == 0: await asyncio.sleep(2); continue
                    raise SourceError('Temporary failure', 'Source returned a server error')
                break
        headers = {k.lower(): v for k, v in result['headers'].items()}
        if code in (301, 302, 303, 307, 308):
            target = headers.get('location')
            if not target: raise SourceError('Temporary failure', 'Redirect has no target')
            return await self.get(urljoin(url, target), ttl, robots, redirects + 1)
        self.failures[host] = 0
        self.store.put('cache', key, result, ttl)
        return result

    async def json(self, url: str, ttl: float = 900):
        result = await self.get(url, ttl)
        if result['status'] != 200: raise SourceError('Source unavailable', f"Source returned HTTP {result['status']}")
        try: return json.loads(result['body'])
        except ValueError: raise SourceError('Temporary failure', 'Source did not return valid JSON') from None
