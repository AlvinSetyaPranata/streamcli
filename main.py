import requests as req
from bs4 import BeautifulSoup as bs
import shutil, textwrap, os

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
WHITE = "\033[37m"
RED = "\033[31m"

ANIME_BASE_URL = "https://otakudesu.blog"
ANIME_LIST = ANIME_BASE_URL + "/anime-list"

def truncate(text, max_length):
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."

def extractAnimeList():
    getList = req.get(ANIME_LIST)
    soup = bs(getList.text, "html.parser")
    elClass = soup.find_all(class_="hodebgst")
    animes = []
    for element in elClass:
        anime = {
            "title": element.text.strip(),
            "path": element.get("href")
        }
        animes.append(anime)
    return animes

def parseAnimeDetail(html):
    soup = bs(html, "html.parser")

    anime = {}

    title = soup.select_one(".jdlrx h1")
    anime["title"] = title.text.strip() if title else None

    sub_title = soup.select_one(".subheading h2")
    anime["sub_title"] = (
        sub_title.text.strip()
        if sub_title else None
    )

    poster = soup.select_one(".fotoanime img")
    anime["poster"] = poster.get("src") if poster else None

    info = {}

    for p in soup.select(".infozingle p"):
        text = p.text.strip()

        if ":" in text:
            key, value = text.split(":", 1)
            info[key.strip()] = value.strip()

    anime["info"] = info

    synopsis = soup.select_one(".sinopc")
    anime["synopsis"] = (
        synopsis.text.strip()
        if synopsis else None
    )

    anime["genres"] = [
        a.text.strip()
        for a in soup.select(".infozingle a[rel='tag']")
    ]

    anime["episodes"] = []

    for li in soup.select(".episodelist ul li"):
        a = li.select_one("a")

        if a:
            anime["episodes"].append({
                "title": a.text.strip(),
                "path": a.get("href")
            })

    return anime

def getAnimeDetail(url):
    response = req.get(url)
    return parseAnimeDetail(response.text)

def getAnimeStream(url):
    r = req.get(url)
    soup = bs(r.text, "html.parser")
    embedStream = soup.find(class_="responsive-embed-stream")
    srcStream = embedStream.find("iframe").get("src")
    print(srcStream)

def displayAnimeList(anime_list):
    width = shutil.get_terminal_size().columns
    column_width = width // 2

    print("\033[1;34mAnime List:\033[0m\n")

    for i in range(0, len(anime_list), 2):
        left = anime_list[i]
        right = anime_list[i + 1] if i + 1 < len(anime_list) else None

        left_title = truncate(
            left["title"],
            column_width - 8
        )

        left_text = f"{i + 1:>3}. {left_title}"

        if right:
            right_title = truncate(
                right["title"],
                column_width - 8
            )
            right_text = f"{i + 2:>3}. {right_title}"
        else:
            right_text = ""

        print(f"{left_text:<{column_width}}{right_text}")

    print(f"\n\033[2m{len(anime_list)} results\033[0m")

def searchAnime(keyword, animeList):
    results = []
    for anime in animeList:
        if keyword in anime["title"]:
            results.append(anime)
    displayAnimeList(results)

def displayAnimeDetail(anime):
    width = shutil.get_terminal_size().columns
    width = min(width, 100)

    print()

    # Header
    print(f"{BOLD}{CYAN}┌{'─' * (width - 2)}┐{RESET}")
    title = truncate(anime.get("title"), width - 6)

    print(
        f"{BOLD}{CYAN}│{RESET} "
        f"{BOLD}{WHITE}{title}{RESET}"
        f"{' ' * max(0, width - len(title) - 3)}"
        f"{BOLD}{CYAN}│{RESET}"
    )

    print(f"{BOLD}{CYAN}└{'─' * (width - 2)}┘{RESET}")

    # Basic info
    print(f"\n{BOLD}{BLUE}:: Information{RESET}")
    info = anime.get("info", {})
    fields = [
        ("Judul", info.get("Judul")),
        ("Japanese", info.get("Japanese")),
        ("Skor", info.get("Skor")),
        ("Tipe", info.get("Tipe")),
        ("Status", info.get("Status")),
        ("Total Episode", info.get("Total Episode")),
        ("Durasi", info.get("Durasi")),
        ("Tanggal Rilis", info.get("Tanggal Rilis")),
        ("Studio", info.get("Studio")),
        ("Produser", info.get("Produser")),
    ]

    for label, value in fields:
        if not value:
            continue

        value = truncate(value, width - 23)

        print(
            f"  {DIM}{label:<14}{RESET} "
            f"{WHITE}{value}{RESET}"
        )

    # Genre
    genres = anime.get("genres", [])

    if genres:
        print(
            f"  {DIM}{'Genre':<14}{RESET} "
            f"{GREEN}{', '.join(genres)}{RESET}"
        )

    # Synopsis
    print(f"\n{BOLD}{BLUE}:: Synopsis{RESET}")

    synopsis = anime.get("synopsis") or "-"
    for line in textwrap.wrap(synopsis, width=width - 4):
        print(f"  {WHITE}{line}{RESET}")

    # Episodes
    episodes = anime.get("episodes", [])

    print(
        f"\n{BOLD}{BLUE}:: Episodes "
        f"{DIM}({len(episodes)}){RESET}"
    )

    column_width = width // 2

    for i in range(0, len(episodes), 2):
        left = episodes[i]
        right = episodes[i + 1] if i + 1 < len(episodes) else None

        left_title = truncate(
            left.get("title"),
            column_width - 8
        )

        left_text = (
            f"{YELLOW}{i + 1:>3}{RESET} "
            f"{left_title}"
        )

        if right:
            right_title = truncate(
                right.get("title"),
                column_width - 8
            )

            right_text = (
                f"{YELLOW}{i + 2:>3}{RESET} "
                f"{right_title}"
            )
        else:
            right_text = ""

        plain_left = f"{i + 1:>3} {left_title}"
        padding = max(
            1,
            column_width - len(plain_left)
        )

        print(
            f"  {left_text}"
            f"{' ' * padding}"
            f"{right_text}"
        )

    print(
        f"{GREEN}✓{RESET} "
        f"{len(episodes)} episodes"
    )

    print()


# ============================================================
# CLI WORKFLOW
# ============================================================

def clearScreen():
    os.system("cls")
    print("\033[2J\033[H", end="")

def pause(message="Press Enter to continue..."):
    try:
        input(f"\n{DIM}{message}{RESET}")
    except (KeyboardInterrupt, EOFError):
        pass

def getInput(prompt):
    try:
        return input(prompt).strip()
    except (KeyboardInterrupt, EOFError):
        print()
        return "q"


def normalizeUrl(url):
    if not url:
        return None

    if url.startswith("http://") or url.startswith("https://"):
        return url

    if url.startswith("/"):
        return ANIME_BASE_URL + url

    return ANIME_BASE_URL + "/" + url


def loading(message):
    print(f"{DIM}{message}{RESET}")

def displayHeader(title):
    width = shutil.get_terminal_size().columns
    width = max(40, min(width, 100))

    title = truncate(title, width - 6)

    print(
        f"{BOLD}{CYAN}"
        f"┌{'─' * (width - 2)}┐"
        f"{RESET}"
    )

    padding = width - len(title) - 4

    print(
        f"{BOLD}{CYAN}│{RESET} "
        f"{BOLD}{WHITE}{title}{RESET}"
        f"{' ' * max(0, padding)}"
        f" {BOLD}{CYAN}│{RESET}"
    )

    print(
        f"{BOLD}{CYAN}"
        f"└{'─' * (width - 2)}┘"
        f"{RESET}"
    )

    return width

def selectAnime(anime_list):
    if not anime_list:
        print(f"\n{RED}No anime found.{RESET}")
        pause()
        return None

    while True:
        choice = getInput(
            f"\n{CYAN}Select anime "
            f"{DIM}[1-{len(anime_list)}, b=back, q=quit]"
            f"{RESET}: "
        )

        if choice.lower() == "b":
            return None

        if choice.lower() == "q":
            return "QUIT"

        if not choice.isdigit():
            print(
                f"{RED}Invalid selection.{RESET}"
            )
            continue

        index = int(choice) - 1

        if 0 <= index < len(anime_list):
            return anime_list[index]

        print(
            f"{RED}Selection out of range.{RESET}"
        )

def selectEpisode(episodes):
    if not episodes:
        print(
            f"\n{RED}No episodes available.{RESET}"
        )
        pause()
        return None

    while True:
        choice = getInput(
            f"\n{CYAN}Select episode "
            f"{DIM}[1-{len(episodes)}, b=back, q=quit]"
            f"{RESET}: "
        )

        if choice.lower() == "b":
            return None

        if choice.lower() == "q":
            return "QUIT"

        if not choice.isdigit():
            print(
                f"{RED}Invalid selection.{RESET}"
            )
            continue

        index = int(choice) - 1

        if 0 <= index < len(episodes):
            return episodes[index]

        print(
            f"{RED}Episode out of range.{RESET}"
        )


# ============================================================
# ANIME LIST MENU
# ============================================================

def animeListMenu(anime_list):
    while True:
        clearScreen()

        displayHeader(
            f"Anime List ({len(anime_list)})"
        )

        print()

        displayAnimeList(anime_list)

        anime = selectAnime(anime_list)

        if anime == "QUIT":
            return "QUIT"

        if anime is None:
            return

        result = animeDetailMenu(anime)

        if result == "QUIT":
            return "QUIT"


# ============================================================
# SEARCH MENU
# ============================================================

def searchMenu(anime_list):
    while True:
        clearScreen()

        displayHeader("Search Anime")

        print()

        keyword = getInput(
            f"{CYAN}Search:{RESET} "
        )

        if keyword.lower() == "q":
            return "QUIT"

        if keyword.lower() == "b":
            return

        if not keyword:
            continue

        keyword = keyword.lower()

        results = [
            anime
            for anime in anime_list
            if keyword in anime["title"].lower()
        ]

        clearScreen()

        displayHeader(
            f"Search: {keyword}"
        )

        print()

        if not results:
            print(
                f"{RED}No anime found.{RESET}"
            )

            pause()
            continue

        displayAnimeList(results)

        anime = selectAnime(results)

        if anime == "QUIT":
            return "QUIT"

        if anime is None:
            continue

        result = animeDetailMenu(anime)

        if result == "QUIT":
            return "QUIT"


# ============================================================
# EPISODE MENU
# ============================================================

def episodeMenu(episode):
    while True:
        clearScreen()

        displayHeader("Episode")

        print()

        title = episode.get("title", "-")

        for line in textwrap.wrap(
            title,
            width=shutil.get_terminal_size().columns - 6
        ):
            print(
                f"  {WHITE}{line}{RESET}"
            )

        print()

        print(
            f"  {YELLOW}[1]{RESET} Stream"
        )

        print(
            f"  {YELLOW}[b]{RESET} Back"
        )

        print(
            f"  {YELLOW}[q]{RESET} Quit"
        )

        choice = getInput(
            f"\n{GREEN}> {RESET}"
        )

        if choice.lower() == "b":
            return

        if choice.lower() == "q":
            return "QUIT"

        if choice == "1":
            clearScreen()

            displayHeader("Stream")

            print()

            try:
                url = normalizeUrl(
                    episode["path"]
                )

                loading("Fetching stream...")

                getAnimeStream(url)

            except req.RequestException as e:
                print(
                    f"\n{RED}Network error:{RESET} {e}"
                )

            except Exception as e:
                print(
                    f"\n{RED}Failed to get stream:"
                    f"{RESET} {e}"
                )

            pause()

        else:
            print(
                f"{RED}Unknown option.{RESET}"
            )


# ============================================================
# ANIME DETAIL
# ============================================================

def animeDetailMenu(anime):
    while True:
        clearScreen()

        print(
            f"{DIM}Loading anime detail..."
            f"{RESET}"
        )

        try:
            url = normalizeUrl(
                anime["path"]
            )

            detail = getAnimeDetail(url)

        except req.RequestException as e:
            clearScreen()

            print(
                f"{RED}Network error:{RESET} {e}"
            )

            pause()

            return

        except Exception as e:
            clearScreen()

            print(
                f"{RED}Failed to load anime:"
                f"{RESET} {e}"
            )

            pause()

            return

        clearScreen()

        displayAnimeDetail(detail)

        episode = selectEpisode(
            detail.get("episodes", [])
        )

        if episode == "QUIT":
            return "QUIT"

        if episode is None:
            return

        result = episodeMenu(episode)

        if result == "QUIT":
            return "QUIT"


# ============================================================
# MAIN MENU
# ============================================================

def mainMenu(anime_list):
    while True:
        clearScreen()

        displayHeader("Anime CLI")

        print()

        print(
            f"  {YELLOW}[1]{RESET} "
            f"Anime List"
        )

        print(
            f"  {YELLOW}[2]{RESET} "
            f"Search Anime"
        )

        print(
            f"  {YELLOW}[q]{RESET} "
            f"Exit"
        )

        print()

        print(
            f"{DIM}{len(anime_list)} anime available"
            f"{RESET}"
        )

        choice = getInput(
            f"\n{GREEN}> {RESET}"
        )

        if choice == "1":
            result = animeListMenu(
                anime_list
            )

            if result == "QUIT":
                break

        elif choice == "2":
            result = searchMenu(
                anime_list
            )

            if result == "QUIT":
                break

        elif choice.lower() == "q":
            break

        else:
            print(
                f"{RED}Unknown command.{RESET}"
            )

            pause()

    clearScreen()

    print(
        f"\n{GREEN}✓{RESET} "
        f"{WHITE}Goodbye!{RESET}\n"
    )


# ============================================================
# ENTRY POINT
# ============================================================

def main():
    clearScreen()

    displayHeader("Anime CLI")

    print()
    loading("Loading anime list...")

    try:
        anime_list = extractAnimeList()

    except req.RequestException as e:
        print(
            f"\n{RED}Network error:{RESET} {e}"
        )
        return

    except Exception as e:
        print(
            f"\n{RED}Failed to load anime list:"
            f"{RESET} {e}"
        )
        return

    if not anime_list:
        print(
            f"\n{RED}Anime list is empty.{RESET}"
        )
        return

    print(
        f"{GREEN}✓{RESET} "
        f"{len(anime_list)} anime loaded."
    )

    pause()

    mainMenu(anime_list)


if __name__ == "__main__":
    main()
