export default async function handler(req: any, res: any) {
  if (req.method !== "GET") {
    res.status(405).json({ detail: "Method not allowed" });
    return;
  }
  try {
    const upstream = await fetch("https://api.music.yandex.net/landing3/chart/russia", {
      headers: {
        Accept: "application/json",
        "User-Agent": "Mozilla/5.0 SONA-Music-Intelligence/1.0",
        "Referer": "https://music.yandex.ru/",
        "Origin": "https://music.yandex.ru",
        "X-Yandex-Music-Device": "os=web; os_version=1; manufacturer=SONA; model=Web; device_id=sona-web; uuid=sona-web",
      },
      cache: "no-store",
    });
    if (!upstream.ok) throw new Error(`Yandex HTTP ${upstream.status}`);
    const data = await upstream.json();
    res.setHeader("Cache-Control", "public, s-maxage=300, stale-while-revalidate=900");
    res.status(200).json(data);
  } catch (error) {
    res.status(502).json({ detail: "Yandex Music chart is temporarily unavailable", upstream_error: String(error) });
  }
}
