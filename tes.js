fetch("https://otakudesu.blog/anime-list/")
  .then((r) => r.text())
  .then((res) => {
    const matches = res.matchAll(
      /<a[^>]*class=["']hodebgst["'][^>]*href=["']([^"']+)["'][^>]*>(.*?)<\/a>/gis,
    );

    for (const m of matches) {
      const href = m[1];
      const title = m[2].replace(/<[^>]+>/g, "").trim();

      console.log({ title, href });
    }
  });
