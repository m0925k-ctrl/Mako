// Executive Brief — サーバー側ニュース取得スクリプト
// feeds.json を読み、各RSSを取得して data/news.json に保存します。
// GitHub Actions から定期実行され、閲覧時はブラウザが同一オリジンの
// data/news.json を読むだけなので、CORSプロキシに依存せず安定します。

import Parser from "rss-parser";
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";

const UA = "Mozilla/5.0 (compatible; MakoDashboard/1.0; +https://github.com/m0925k-ctrl/Mako)";
const TIMEOUT = 20000;
const MAX_ITEMS = 8;

const { feeds } = JSON.parse(readFileSync("feeds.json", "utf8"));
const parser = new Parser({ timeout: TIMEOUT });

async function fetchOne(feed) {
  const res = await fetch(encodeURI(feed.url), {
    headers: {
      "user-agent": UA,
      "accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
    },
    signal: AbortSignal.timeout(TIMEOUT),
    redirect: "follow",
  });
  if (!res.ok) throw new Error("HTTP " + res.status);
  const xml = await res.text();
  const parsed = await parser.parseString(xml);
  return (parsed.items || [])
    .map((it) => ({
      title: (it.title || "").trim(),
      link: it.link || it.guid || "#",
      date: it.isoDate || it.pubDate || "",
    }))
    .filter((x) => x.title)
    .slice(0, MAX_ITEMS);
}

const out = { generatedAt: new Date().toISOString(), feeds: {} };
let ok = 0, fail = 0;

for (const feed of feeds) {
  try {
    out.feeds[feed.id] = await fetchOne(feed);
    ok++;
    console.log(`OK   ${feed.id} (${out.feeds[feed.id].length})`);
  } catch (e) {
    out.feeds[feed.id] = null; // null = この回は取得失敗（閲覧側はプロキシ経由で再取得を試みる）
    fail++;
    console.log(`FAIL ${feed.id}: ${e.message}`);
  }
}

mkdirSync("data", { recursive: true });
writeFileSync("data/news.json", JSON.stringify(out));
console.log(`done: ${ok} ok, ${fail} fail -> data/news.json`);

// 全滅した場合は異常終了（前回の news.json を温存するため commit させない）
if (ok === 0) process.exit(1);
