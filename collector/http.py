"""Bounded HTTP requests, robots rules, retries and per-host pacing."""
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from urllib.parse import urlsplit
import re
import time

AGENT = "VivienneMetals/0.7 (public Paris price monitor)"


def robots_allowed(text, path, agent="viviennemetals"):
    # Support standard wildcard and terminal-$ matching (urllib.robotparser doesn't).
    groups, agents, rules = [], [], []
    for line in text.splitlines() + ["User-agent: __end__"]:
        line = line.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        key, val = (s.strip() for s in line.split(":", 1))
        key = key.lower()
        if key == "user-agent":
            if rules:
                groups.append((agents, rules)); agents, rules = [], []
            agents.append(val.lower())
        elif key in ("allow", "disallow") and val:
            rules.append((key, val))
    matches = []
    specific = any(any(a != "*" and a in agent for a in aa) for aa, _ in groups)
    for aa, rr in groups:
        if not any((a != "*" and a in agent) if specific else a == "*" for a in aa):
            continue
        for key, pattern in rr:
            regex = re.escape(pattern).replace(r"\*", ".*")
            if regex.endswith(r"\$"):
                regex = regex[:-2] + "$"
            if re.match(regex, path):
                matches.append((len(pattern.replace("*", "")), key == "allow"))
    return max(matches, default=(0, True))[1]


class Client:
    def __init__(self, opener=urlopen, sleeper=time.sleep):
        self.opener, self.sleep = opener, sleeper
        self.robots, self.last = {}, {}

    def raw(self, url):
        for attempt in range(3):
            try:
                accept = "application/javascript,application/json,*/*" if urlsplit(url).path.endswith(".js") else "text/html,text/plain"
                req = Request(url, headers={"User-Agent": AGENT, "Accept": accept, "Cache-Control": "no-cache"})
                with self.opener(req, timeout=25) as r:
                    if urlsplit(r.url).hostname != urlsplit(url).hostname:
                        raise ValueError("Cross-host redirect rejected")
                    body = r.read(3_000_001)
                    if len(body) > 3_000_000:
                        raise ValueError("Response exceeds size limit")
                    return body.decode("utf-8", errors="strict")
            except HTTPError as e:
                # Do not loop over authentication/anti-bot blocks or rate limits.
                if e.code not in (500, 502, 503, 504) or attempt == 2:
                    raise
            except (TimeoutError, OSError):
                if attempt == 2:
                    raise
            self.sleep(2 ** attempt)

    def get(self, url):
        u = urlsplit(url)
        if u.scheme != "https" or u.username or u.password:
            raise ValueError("HTTPS public URL required")
        origin = f"{u.scheme}://{u.netloc}"
        if origin not in self.robots:
            try:
                self.robots[origin] = self.raw(origin + "/robots.txt")
            except HTTPError as e:
                if e.code == 404:
                    self.robots[origin] = ""
                else:
                    raise
        if not robots_allowed(self.robots[origin], u.path + ("?" + u.query if u.query else "")):
            raise PermissionError("robots.txt disallows this path")
        wait = 1.5 - (time.monotonic() - self.last.get(origin, 0))
        if wait > 0:
            self.sleep(wait)
        try:
            return self.raw(url)
        finally:
            self.last[origin] = time.monotonic()
