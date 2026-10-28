import json
import os
import re
import time
from http.client import IncompleteRead
from html import unescape
from urllib.request import Request, urlopen
from urllib.parse import urljoin, urlparse, parse_qs
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from html.parser import HTMLParser

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8080"))

ANIME_BASE_URL = os.environ.get(
    "ANIME_BASE_URL",
    "https://otakudesu.blog"
).rstrip("/")
ANIME_LIST = ANIME_BASE_URL + "/anime-list"

ALLOWED_HOSTS = {
    host.strip().lower()
    for host in os.environ.get(
        "ALLOWED_HOSTS",
        urlparse(ANIME_BASE_URL).netloc
    ).split(",")
    if host.strip()
}


# =========================
# URL VALIDATION
# =========================

def is_allowed_url(url):
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        return False

    return parsed.netloc.lower() in ALLOWED_HOSTS


# =========================
# HTTP CLIENT
# =========================

def http_get(url, retries=3):
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/html,application/xhtml+xml",
        }
    )

    last_error = None

    for attempt in range(retries):
        try:
            with urlopen(req, timeout=20) as response:
                return response.read().decode("utf-8", errors="ignore")

        except (IncompleteRead, OSError) as e:
            last_error = e

            if attempt < retries - 1:
                time.sleep(1 + attempt)

    raise last_error


# =========================
# HTML PARSER
# =========================

class AnimeListParser(HTMLParser):

    def __init__(self):
        super().__init__()

        self.animes = []
        self.in_hodebgst = False
        self.current = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)

        if tag == "a":
            classes = attrs.get("class", "").split()

            if "hodebgst" in classes:
                self.in_hodebgst = True

                self.current = {
                    "title": "",
                    "path": attrs.get("href")
                }

    def handle_data(self, data):
        if self.in_hodebgst and self.current:
            self.current["title"] += data

    def handle_endtag(self, tag):
        if tag == "a" and self.in_hodebgst:
            self.current["title"] = self.current["title"].strip()

            self.animes.append(self.current)

            self.current = None
            self.in_hodebgst = False


class AnimeDetailParser(HTMLParser):

    def __init__(self):
        super().__init__()

        self.anime = {
            "title": None,
            "sub_title": None,
            "poster": None,
            "info": {},
            "synopsis": None,
            "genres": [],
            "episodes": []
        }

        self.stack = []

        self.current_text = ""
        self.current_href = None

        self.in_info = False
        self.in_genre = False
        self.in_episode = False
        self.in_poster = False
        self.in_synopsis = False

    def has_class(self, attrs, class_name):
        classes = dict(attrs).get("class", "").split()
        return class_name in classes

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)

        self.stack.append((tag, attrs_dict))

        if tag == "img" and self.has_class(attrs, "img-responsive"):
            self.in_poster = True

        if tag == "a":
            self.current_href = attrs_dict.get("href")

        # Poster
        if tag == "img":
            src = attrs_dict.get("src")

            if src and self.in_poster:
                self.anime["poster"] = src

        # Genre
        if tag == "a":
            rel = attrs_dict.get("rel", "")

            if isinstance(rel, str) and "tag" in rel:
                self.in_genre = True
                self.current_text = ""

        # Episode
        if tag == "li":
            self.in_episode = False

        if tag == "a" and self.in_episode is False:
            classes = attrs_dict.get("class", "").split()

            if "btn-eps" in classes:
                self.in_episode = True
                self.current_text = ""

    def handle_data(self, data):
        text = data.strip()

        if not text:
            return

        self.current_text += text + " "

    def handle_endtag(self, tag):

        text = self.current_text.strip()

        # Genre
        if tag == "a" and self.in_genre:
            if text:
                self.anime["genres"].append(text)

            self.in_genre = False
            self.current_text = ""

        # Episode
        elif tag == "a" and self.in_episode:
            if text and self.current_href:
                self.anime["episodes"].append({
                    "title": text,
                    "path": self.current_href
                })

            self.in_episode = False
            self.current_href = None
            self.current_text = ""

        # Reset poster state
        if tag == "img":
            self.in_poster = False

        if self.stack:
            self.stack.pop()


# =========================
# LIST
# =========================

def extractAnimeList():
    html = http_get(ANIME_LIST)

    parser = AnimeListParser()
    parser.feed(html)

    return parser.animes


# =========================
# DETAIL
# =========================

def parseAnimeDetail(html):
    anime = {
        "title": None,
        "sub_title": None,
        "poster": None,
        "info": {},
        "synopsis": None,
        "genres": [],
        "episodes": []
    }

    # title
    match = re.search(
        r'<div[^>]*class=["\'][^"\']*jdlrx[^"\']*["\'][^>]*>'
        r'.*?<h1[^>]*>(.*?)</h1>',
        html,
        re.I | re.S
    )

    if match:
        anime["title"] = clean_html(match.group(1))

    # subtitle
    match = re.search(
        r'<div[^>]*class=["\'][^"\']*subheading[^"\']*["\'][^>]*>'
        r'.*?<h2[^>]*>(.*?)</h2>',
        html,
        re.I | re.S
    )

    if match:
        anime["sub_title"] = clean_html(match.group(1))

    # poster
    match = re.search(
        r'<div[^>]*class=["\'][^"\']*fotoanime[^"\']*["\'][^>]*>'
        r'.*?<img[^>]+src=["\']([^"\']+)',
        html,
        re.I | re.S
    )

    if match:
        anime["poster"] = urljoin(
            ANIME_BASE_URL,
            match.group(1)
        )

    # info
    info_matches = re.findall(
        r'<p[^>]*>(.*?)</p>',
        html,
        re.I | re.S
    )

    for raw in info_matches:
        text = clean_html(raw)

        if ":" in text:
            key, value = text.split(":", 1)

            key = key.strip()
            value = value.strip()

            if key and value:
                anime["info"][key] = value

    # synopsis
    match = re.search(
        r'<div[^>]*class=["\'][^"\']*sinopc[^"\']*["\'][^>]*>'
        r'(.*?)</div>',
        html,
        re.I | re.S
    )

    if match:
        anime["synopsis"] = clean_html(match.group(1))

    # genres     
    genre_matches = re.findall(
        r'<a[^>]+rel=["\']tag["\'][^>]*>(.*?)</a>',
        html,
        re.I | re.S
    )

    anime["genres"] = [
        clean_html(x)
        for x in genre_matches
        if clean_html(x)
    ]

    # episodes
    episode_matches = re.findall(
        r'<li[^>]*>.*?'
        r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>'
        r'(.*?)</a>.*?</li>',
        html,
        re.I | re.S
    )

    for path, title in episode_matches:

        anime["episodes"].append({
            "title": clean_html(title),
            "path": urljoin(ANIME_BASE_URL, path)
        })

    return anime


def getAnimeDetail(url):
    if not is_allowed_url(url):
        raise ValueError("URL tidak diizinkan")

    return parseAnimeDetail(
        http_get(url)
    )


# =========================
# STREAM
# =========================

def getAnimeStream(url):

    if not is_allowed_url(url):
        raise ValueError("URL tidak diizinkan")

    html = http_get(url)

    match = re.search(
        r'<div[^>]*class=["\'][^"\']*responsive-embed-stream[^"\']*["\'][^>]*>'
        r'.*?<iframe[^>]+src=["\']([^"\']+)',
        html,
        re.I | re.S
    )

    if not match:
        return None

    return urljoin(
        ANIME_BASE_URL,
        match.group(1)
    )


# =========================
# HTML CLEANER
# =========================

def clean_html(text):

    text = re.sub(
        r'<br\s*/?>',
        '\n',
        text,
        flags=re.I
    )

    text = re.sub(
        r'<[^>]+>',
        '',
        text
    )

    text = unescape(text)

    replacements = {
        "&nbsp;": " ",
        "&amp;": "&",
        "&quot;": '"',
        "&#39;": "'",
        "&lt;": "<",
        "&gt;": ">"
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return " ".join(text.split())


# =========================
# JSON RESPONSE
# =========================

def json_response(handler, data, status=200):
    body = json.dumps(
        data,
        ensure_ascii=False,
        indent=2
    ).encode("utf-8")

    handler.send_response(status)

    handler.send_header(
        "Content-Type",
        "application/json; charset=utf-8"
    )

    handler.send_header(
        "Content-Length",
        str(len(body))
    )

    handler.send_header(
        "Access-Control-Allow-Origin",
        "*"
    )

    handler.end_headers()
    handler.wfile.write(body)


# =========================
# API HANDLER
# =========================

class APIHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header(
            "Access-Control-Allow-Origin",
            "*"
        )

        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, OPTIONS"
        )

        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type"
        )

        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        try:

            # =====================
            # GET /  and  /health
            # =====================

            if path in ("/", "/health"):

                json_response(
                    self,
                    {
                        "status": True,
                        "service": "streamcli-api",
                        "message": "OK"
                    }
                )

            # =====================
            # GET /anime
            # =====================

            if path == "/anime":

                animes = extractAnimeList()

                search = query.get(
                    "search",
                    [None]
                )[0]

                if search:

                    search = search.lower()

                    animes = [
                        anime
                        for anime in animes
                        if search in anime["title"].lower()
                    ]

                json_response(
                    self,
                    {
                        "status": True,
                        "count": len(animes),
                        "data": animes
                    }
                )

            # =====================
            # GET /anime/detail
            # =====================

            elif path == "/anime/detail":

                url = query.get(
                    "url",
                    [None]
                )[0]

                if not url:
                    json_response(
                        self,
                        {
                            "status": False,
                            "message": "Parameter url diperlukan"
                        },
                        400
                    )
                    return

                anime = getAnimeDetail(url)

                json_response(
                    self,
                    {
                        "status": True,
                        "data": anime
                    }
                )

            # =====================
            # GET /anime/stream
            # =====================

            elif path == "/anime/stream":

                url = query.get(
                    "url",
                    [None]
                )[0]

                if not url:
                    json_response(
                        self,
                        {
                            "status": False,
                            "message": "Parameter url diperlukan"
                        },
                        400
                    )
                    return

                stream = getAnimeStream(url)

                if not stream:
                    json_response(
                        self,
                        {
                            "status": False,
                            "message": "Stream tidak ditemukan"
                        },
                        404
                    )
                    return

                json_response(
                    self,
                    {
                        "status": True,
                        "data": {
                            "stream": stream
                        }
                    }
                )

            # =====================
            # 404
            # =====================

            else:

                json_response(
                    self,
                    {
                        "status": False,
                        "message": "Endpoint tidak ditemukan",
                        "endpoints": [
                            "GET /anime",
                            "GET /anime?search=naruto",
                            "GET /anime/detail?url=...",
                            "GET /anime/stream?url=..."
                        ]
                    },
                    404
                )

        except ValueError as e:

            json_response(
                self,
                {
                    "status": False,
                    "message": str(e)
                },
                400
            )

        except Exception as e:

            json_response(
                self,
                {
                    "status": False,
                    "message": str(e)
                },
                500
            )

    def log_message(self, format, *args):
        print(
            "[HTTP]",
            self.address_string(),
            "-",
            format % args
        )


# =========================
# RUN SERVER
# =========================

def main():

    server = ThreadingHTTPServer(
        (HOST, PORT),
        APIHandler
    )

    print(f"API running at http://{HOST}:{PORT}")

    try:
        server.serve_forever()

    except KeyboardInterrupt:
        print("\nStopping server...")

    finally:
        server.server_close()


if __name__ == "__main__":
    main()
