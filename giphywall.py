#!/usr/bin/env python3
"""Flask-powered Giphy wall with SQLite storage and lightweight frontend."""

from __future__ import annotations

import random
import re
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify, render_template_string, request, send_from_directory

BASE_DIR = Path(__file__).resolve().parent
DB_URL = "postgresql://giphywall_user:VHot1umtmoRUIR35j2X5cDnILR9Luuk2@dpg-d4ghl94hg0os73fq5jlg-a/giphywall"
STATIC_DIR = BASE_DIR / "static"
MUSIC_DIR = BASE_DIR / "music"


def get_conn():
    return psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)


def ensure_db() -> None:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS giphies (
                id SERIAL PRIMARY KEY,
                giphy_id TEXT NOT NULL,
                giphy_url TEXT NOT NULL,
                commentary TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()


def extract_giphy_id(raw_url: str) -> str | None:
    """Try to pull the Giphy ID from a user-provided URL or slug."""
    if not raw_url:
        return None

    parsed = re.sub(r"^https?://", "", raw_url)
    parsed_parts = raw_url.split("/")
    slug = ""

    if "giphy.com" in raw_url:
        parts = [p for p in parsed_parts if p]
        if parts:
            slug = parts[-1]

    if not slug:
        if re.fullmatch(r"[A-Za-z0-9]+", raw_url):
            return raw_url
        if parsed_parts:
            candidate = parsed_parts[-1].split("?")[0]
            if re.fullmatch(r"[A-Za-z0-9]+", candidate):
                slug = candidate

    if slug:
        candidate = slug.split("-")[-1]
        if re.fullmatch(r"[A-Za-z0-9]+", candidate):
            return candidate

    return None


def make_preview_url(giphy_id: str | None, fallback: str) -> str:
    if giphy_id:
        return f"https://i.giphy.com/media/{giphy_id}/200.gif"
    return fallback


KEYWORDS = {
    "cat": ["such whisker", "very purr", "much stealth"],
    "dog": ["many bork", "such zoom", "very good boi"],
    "wow": ["wow amaze", "so sparkle", "very wow"],
    "dance": ["much groove", "so boogie", "very rhythm"],
    "meme": ["such meme", "so viral", "very lol"],
    "fail": ["much oops", "so tumble", "very chaos"],
    "win": ["such victory", "very pro", "much clutch"],
    "happy": ["so joy", "very grin", "such sunshine"],
    "sad": ["so sniff", "much feels", "very hug"],
    "cry": ["so tear", "much soft", "very tissue"],
    "sparkle": ["much glitter", "so shiny", "very glam"],
    "neon": ["such glow", "very rave", "so cyber"],
    "space": ["so cosmic", "very star", "much orbit"],
    "food": ["such snack", "very yum", "much munch"],
}


def generate_commentary(url: str, giphy_id: str) -> str:
    text = url.lower()
    hits = []
    for key, phrases in KEYWORDS.items():
        if key in text:
            hits.append(random.choice(phrases))
    if not hits:
        hits.append(random.choice(["so loop", "much gif", "very pixels", "such motion"]))
    hits.append(random.choice(["wow", "much amaze", "such delight", "very enjoy"]))
    return " • ".join(hits[:3])


def fetch_giphies(limit: int, offset: int):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, giphy_id, giphy_url, commentary, created_at
            FROM giphies
            ORDER BY created_at DESC, id DESC
            LIMIT %s OFFSET %s
            """,
            (limit, offset),
        )
        rows = cur.fetchall()
        items = []
        for row in rows:
            items.append(
                {
                    "id": row["id"],
                    "giphy_id": row["giphy_id"],
                    "giphy_url": row["giphy_url"],
                    "commentary": row["commentary"] or "",
                    "preview_url": make_preview_url(row["giphy_id"], row["giphy_url"]),
                    "created_at": row["created_at"],
                }
            )
        return items


def insert_giphy(giphy_id: str, giphy_url: str) -> dict:
    commentary = generate_commentary(giphy_url, giphy_id)
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO giphies (giphy_id, giphy_url, commentary)
            VALUES (%s, %s, %s)
            RETURNING id, giphy_id, giphy_url, commentary, created_at
            """,
            (giphy_id, giphy_url, commentary),
        )
        row = cur.fetchone()
        conn.commit()
        return {
            "id": row["id"],
            "giphy_id": row["giphy_id"],
            "giphy_url": row["giphy_url"],
            "commentary": row["commentary"] or "",
            "preview_url": make_preview_url(row["giphy_id"], row["giphy_url"]),
            "created_at": row["created_at"],
        }


def delete_giphy(giphy_id: int) -> bool:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM giphies WHERE id = %s", (giphy_id,))
        conn.commit()
        return cur.rowcount > 0


INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Such Giphy Wall</title>
  <link rel="stylesheet" href="/static/style.css">
  <link rel="stylesheet" href="/static/seasonal.css">
</head>
<body>
  <div class="doge-cloud" aria-hidden="true">
    <img class="doge d1" src="/static/doge.jpg" alt="">
    <img class="doge d2" src="/static/doge.jpg" alt="">
    <img class="doge d3" src="/static/doge.jpg" alt="">
    <img class="doge d4" src="/static/doge.jpg" alt="">
    <img class="doge d5" src="/static/doge.jpg" alt="">
    <img class="doge d6" src="/static/doge.jpg" alt="">
  </div>
  <div id="snow" aria-hidden="true"></div>
  <div class="page">
    <header class="hero">
      <div>
        <p class="badge">wow live</p>
        <h1>Much Giphy Wall</h1>
        <p class="subtitle">so scroll. very gif. wow delight.</p>
        <div class="music-bar">
          <div class="music-buttons">
            <button type="button" class="music-btn" data-track="chasing">wow chill</button>
            <button type="button" class="music-btn" data-track="goofy">such goofy</button>
            <button type="button" class="music-btn" data-track="swing">very swing</button>
          </div>
          <div class="vinyl" aria-hidden="true">
            <img src="/static/vinyl.png" alt="" class="vinyl-img">
          </div>
        </div>
      </div>
      <form id="giphy-form" class="add-form">
        <label for="giphy-url" class="sr-only">Giphy URL</label>
        <input id="giphy-url" name="url" type="url" required placeholder="such giphy link, so wow" autocomplete="off">
        <button type="submit">Drop GIF</button>
      </form>
      <p class="hint">tip: paste any giphy link or id, newest shows first.</p>
      <div id="status" class="status"></div>
    </header>

    <main>
      <div id="feed" class="feed"></div>
      <div id="loader" class="loader hidden">loading wow...</div>
      <div id="end" class="end hidden">no more gifs, much empty</div>
    </main>
  </div>

  <script>
    const feed = document.getElementById('feed');
    const loader = document.getElementById('loader');
    const endMarker = document.getElementById('end');
    const statusBox = document.getElementById('status');
    const hero = document.querySelector('.hero');
    const form = document.getElementById('giphy-form');
    const input = document.getElementById('giphy-url');
    const snow = document.getElementById('snow');
    const musicButtons = document.querySelectorAll('.music-btn');
    const mobileCompactMq = window.matchMedia('(max-width: 700px)');

    let offset = 0;
    const limit = 18;
    let isLoading = false;
    let reachedEnd = false;

    const tracks = {
      chasing: {
        src: '/music/Ian%20Post%20-%20Chasing%20Fireflies.mp3',
        audio: null,
      },
      goofy: {
        src: '/music/MRMUSTACHE%20-%20GOOFY%20POTION%20-%20No%20FX.mp3',
        audio: null,
      },
      swing: {
        src: '/music/Raanana%20Big%20Band%20-%20Santa%20Swings.mp3',
        audio: null,
      },
    };
    let currentTrack = null;

    const stopAllMusic = () => {
      Object.values(tracks).forEach(t => {
        if (t.audio) {
          t.audio.pause();
          t.audio.currentTime = 0;
        }
      });
      musicButtons.forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.label) btn.textContent = btn.dataset.label;
      });
      currentTrack = null;
    };

    const toggleMusic = (key, button) => {
      const track = tracks[key];
      if (!track) return;
      const isActive = key === currentTrack;
      stopAllMusic();
      if (isActive) return;
      if (!track.audio) {
        track.audio = new Audio(track.src);
        track.audio.loop = true;
        track.audio.volume = 0.3;
      }
      track.audio.play().catch(() => {});
      button.classList.add('active');
      button.textContent = `${button.dataset.label} ♪`;
      currentTrack = key;
    };

    const setStatus = (message, kind = 'info') => {
      statusBox.textContent = message || '';
      statusBox.className = 'status ' + kind;
    };

    const makeSnow = () => {
      const flakeCount = 70;
      for (let i = 0; i < flakeCount; i++) {
        const flake = document.createElement('span');
        flake.className = 'flake';
        const size = Math.random() * 4 + 2;
        flake.style.left = `${Math.random() * 100}%`;
        flake.style.animationDuration = `${6 + Math.random() * 8}s`;
        flake.style.animationDelay = `${Math.random() * 6}s`;
        flake.style.opacity = `${0.4 + Math.random() * 0.6}`;
        flake.style.width = `${size}px`;
        flake.style.height = `${size}px`;
        snow.appendChild(flake);
      }
    };

    const makeSeasonalBarks = () => {
      return;
    };

    const makeCard = (item) => {
      const card = document.createElement('article');
      card.className = 'card';
      card.innerHTML = `
        <div class="image-wrap">
          <img src="${item.preview_url}" alt="giphy ${item.giphy_id}" loading="lazy">
        </div>
        <div class="meta">
          <p class="meta-line">id: ${item.giphy_id}</p>
          <div class="meta-actions">
            <a class="meta-link" href="${item.giphy_url}" target="_blank" rel="noopener">open original</a>
            <button class="ghost delete" data-id="${item.id}">delete</button>
          </div>
        </div>
      `;
      return card;
    };

    const fetchGiphies = async () => {
      if (isLoading || reachedEnd) return;
      isLoading = true;
      loader.classList.remove('hidden');
      try {
        const response = await fetch(`/api/giphies?offset=${offset}&limit=${limit}`);
        const data = await response.json();
        const items = data.items || [];
        if (items.length === 0) {
          reachedEnd = true;
          endMarker.classList.remove('hidden');
        } else {
          items.forEach(item => feed.appendChild(makeCard(item)));
          offset += items.length;
        }
      } catch (err) {
        setStatus('such error fetching gifs', 'error');
      } finally {
        isLoading = false;
        loader.classList.add('hidden');
      }
    };

    const resetFeed = () => {
      offset = 0;
      reachedEnd = false;
      feed.innerHTML = '';
      endMarker.classList.add('hidden');
      fetchGiphies();
    };

    const updateHeroCompact = () => {
      if (!hero) return;
      const shouldCompact = mobileCompactMq.matches && window.scrollY > 32;
      hero.classList.toggle('compact', shouldCompact);
    };

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const url = input.value.trim();
      if (!url) {
        setStatus('much empty link', 'error');
        return;
      }
      setStatus('sending wow...', 'info');
      try {
        const response = await fetch('/api/giphies', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url })
        });
        if (!response.ok) {
          const err = await response.json().catch(() => ({}));
          throw new Error(err.message || 'bad vibes');
        }
        await response.json();
        input.value = '';
        setStatus('much success, gif now live', 'success');
        resetFeed();
      } catch (err) {
        setStatus(err.message || 'such error', 'error');
      }
    });

    const onScroll = () => {
      updateHeroCompact();
      if (reachedEnd || isLoading) return;
      const scrollSpot = window.innerHeight + window.scrollY;
      if (scrollSpot >= document.body.offsetHeight - 300) {
        fetchGiphies();
      }
    };

    feed.addEventListener('click', async (e) => {
      const btn = e.target.closest('button.delete');
      if (!btn) return;
      const id = btn.dataset.id;
      btn.disabled = true;
      btn.textContent = 'deleting...';
      try {
        const resp = await fetch(`/api/giphies/${id}`, { method: 'DELETE' });
        if (!resp.ok) throw new Error('such fail');
        btn.closest('.card')?.remove();
      } catch (err) {
        setStatus('could not delete wow', 'error');
        btn.disabled = false;
        btn.textContent = 'delete';
      }
    });

    musicButtons.forEach(btn => {
      btn.dataset.label = btn.textContent.trim();
      btn.addEventListener('click', () => toggleMusic(btn.dataset.track, btn));
    });

    if (mobileCompactMq.addEventListener) {
      mobileCompactMq.addEventListener('change', updateHeroCompact);
    } else if (mobileCompactMq.addListener) {
      mobileCompactMq.addListener(updateHeroCompact);
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    updateHeroCompact();
    makeSnow();
    makeSeasonalBarks();
    fetchGiphies();
  </script>
</body>
</html>
"""


def create_app() -> Flask:
    app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="/static")
    ensure_db()

    @app.route("/")
    def index():
        return render_template_string(INDEX_HTML)

    @app.route("/api/giphies", methods=["GET", "POST"])
    def giphies():
        if request.method == "GET":
            try:
                limit = int(request.args.get("limit", 18))
                offset = int(request.args.get("offset", 0))
            except ValueError:
                return jsonify({"message": "bad paging"}), 400
            limit = max(1, min(limit, 50))
            offset = max(0, offset)
            items = fetch_giphies(limit, offset)
            return jsonify({"items": items})

        data = request.get_json(force=True, silent=True) or {}
        url = str(data.get("url", "")).strip()
        if not url:
            return jsonify({"message": "such need url"}), 400
        giphy_id = extract_giphy_id(url)
        if not giphy_id:
            return jsonify({"message": "no giphy id found"}), 400
        item = insert_giphy(giphy_id, url)
        return jsonify(item), 201

    @app.route("/api/giphies/<int:item_id>", methods=["DELETE"])
    def remove_giphy(item_id: int):
        if delete_giphy(item_id):
            return "", 204
        return jsonify({"message": "no gif wow"}), 404

    @app.route("/music/<path:filename>")
    def music(filename: str):
        return send_from_directory(MUSIC_DIR, filename)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
