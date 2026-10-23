#!/usr/bin/env python3
"""Rebuilds playlist.js from the songs in assets/music/.

Drop songs into assets/music/ and run this script (or double-click update-playlist.bat).

Naming: "Song Title - Artist.mp3" shows as "Song Title" with the artist next to it.
Order: alphabetical. Start a name with a number to control the order ("01 - Song - Artist.mp3");
the number is hidden on the site. Files without " - " use their title and artist tags if the
optional "mutagen" package is installed (pip install mutagen), otherwise the file name.

Covers: artwork embedded in an MP3's ID3 tag wins. Tracks without it are looked up by
"Title - Artist" on Deezer, then Last.fm (using the key already in config.js), matched strictly
on artist and title, saved to assets/art/ and linked from playlist.js. Found covers are cached:
a later run reuses the file instead of asking again, and only a missing one triggers a lookup.
Run with --no-art-lookup to skip the network entirely. Anything still without a cover gets a
gradient drawn from the title on the site.
"""
import hashlib
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent
MUSIC = ROOT / "assets" / "music"
ART = ROOT / "assets" / "art"
OUT = ROOT / "playlist.js"
INDEX = ROOT / "index.html"
EXTS = {".mp3", ".m4a", ".wav", ".ogg"}
COVER_MAX = 320  # px; the player shows a 46 px cover, so this is already sharp on a 3x screen
UA = "ashy.lol playlist maker"
LASTFM_PLACEHOLDER = "2a96cbd8b46e442fc41c2b86b821562f"  # Last.fm's grey "no image" star


def natural(s):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]


def from_tags(path):
    try:
        from mutagen import File
        f = File(path, easy=True)
        if f:
            title = (f.get("title") or [""])[0].strip()
            artist = (f.get("artist") or [""])[0].strip()
            if title and artist:
                return f"{title} – {artist}"
            return title or None
    except Exception:
        pass
    return None


def title_for(path):
    name = re.sub(r"^\d{1,3}\s*[-._]\s+", "", path.stem)  # "01 - " or "01. " ordering prefixes
    if " " not in name:
        name = name.replace("_", " ")
    if re.search(r"\s[-–—]\s", name):
        return re.sub(r"\s[-–—]\s", " – ", name)
    return from_tags(path) or name


def split_artist(full):
    """"two cups- Voda Fuji" and "TORN – Ramzoid" both become (title, artist)."""
    parts = re.split(r"\s*[–—]\s*|\s+-\s+|- ", full, maxsplit=1)
    if len(parts) == 2 and parts[1].strip():
        return parts[0].strip(), parts[1].strip()
    return full.strip(), ""


def syncsafe(b):
    return (b[0] << 21) | (b[1] << 14) | (b[2] << 7) | b[3]


def embedded_cover(path):
    """Front cover out of an MP3's ID3v2 tag, as (image bytes, extension), or None.

    Read by hand so the script keeps working with nothing installed. The image is found by
    its own signature rather than by counting past the description field, which is the part
    of the APIC frame that depends on the tag's text encoding.
    """
    try:
        with path.open("rb") as f:
            head = f.read(10)
            if len(head) < 10 or head[:3] != b"ID3":
                return None
            major, flags = head[3], head[5]
            body = f.read(syncsafe(head[6:10]))
    except OSError:
        return None

    off = 0
    if flags & 0x40:  # extended header
        off = syncsafe(body[:4]) if major == 4 else int.from_bytes(body[:4], "big") + 4
    while off + 10 <= len(body):
        fid = body[off:off + 4]
        if not fid.strip(b"\x00"):
            break
        size = syncsafe(body[off + 4:off + 8]) if major == 4 else int.from_bytes(body[off + 4:off + 8], "big")
        if size <= 0 or off + 10 + size > len(body):
            break
        if fid == b"APIC":
            frame = body[off + 10:off + 10 + size]
            mime_end = frame.find(b"\x00", 1)
            if mime_end < 0:
                return None
            rest = frame[mime_end + 2:]  # past the mime, the picture-type byte and description
            for magic, ext in ((b"\xff\xd8\xff", ".jpg"), (b"\x89PNG", ".png"),
                               (b"RIFF", ".webp"), (b"GIF8", ".gif")):
                at = rest.find(magic)
                if at >= 0:
                    return rest[at:], ext
            return None
        off += 10 + size
    return None


def norm(s):
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def fetch_bytes(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def fetch_json(url, timeout=8):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def lastfm_key():
    try:
        return re.search(r'apiKey:\s*"([^"]+)"', (ROOT / "config.js").read_text(encoding="utf-8")).group(1)
    except Exception:
        return None


def deezer_cover(artist, track):
    url = "https://api.deezer.com/search?" + urllib.parse.urlencode({"q": f"{track} {artist}", "limit": 5})
    for hit in fetch_json(url).get("data", []):
        if norm(hit.get("artist", {}).get("name", "")) == norm(artist) and norm(hit.get("title", "")) == norm(track):
            return hit.get("album", {}).get("cover_xl")
    return None


def lastfm_cover(key, artist, track):
    if not key:
        return None
    url = "https://ws.audioscrobbler.com/2.0/?" + urllib.parse.urlencode({
        "method": "track.getInfo", "artist": artist, "track": track,
        "api_key": key, "format": "json", "autocorrect": 1})
    found = fetch_json(url).get("track") or {}
    if norm((found.get("artist") or {}).get("name", "")) != norm(artist):
        return None
    if norm(track) not in norm(found.get("name", "")):
        return None
    urls = [i.get("#text") for i in (found.get("album") or {}).get("image") or [] if i.get("#text")]
    if not urls or LASTFM_PLACEHOLDER in urls[-1]:
        return None
    return urls[-1]


def lookup_cover(key, artist, track):
    """Best available cover URL for one track, or None. Deezer first: its art is 1000 px."""
    for find in (deezer_cover, lambda a, t: lastfm_cover(key, a, t)):
        try:
            url = find(artist, track)
        except Exception:
            url = None
        if url:
            return url
    return None


def write_cover(raw, ext, base):
    """Save one cover as assets/art/<base>.jpg (or its own format without Pillow)."""
    try:
        import io
        from PIL import Image
        im = Image.open(io.BytesIO(raw)).convert("RGB")
        im.thumbnail((COVER_MAX, COVER_MAX))
        out = base.with_suffix(".jpg")
        im.save(out, "JPEG", quality=84, optimize=True, progressive=True)
        return out
    except Exception:
        out = base.with_suffix(ext)
        out.write_bytes(raw)
        return out


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "track"


def cached(base):
    """A cover kept from an earlier run, so a rerun does not ask the network again."""
    for path in base.parent.glob(base.name + ".*"):
        return path
    return None


def main():
    if not MUSIC.is_dir():
        MUSIC.mkdir(parents=True)
        print("Created assets/music. Put your songs in there and run this again.")
    files = sorted((p for p in MUSIC.iterdir() if p.is_file() and p.suffix.lower() in EXTS),
                   key=lambda p: natural(p.name))
    ART.mkdir(parents=True, exist_ok=True)

    key = lastfm_key()
    allow_network = "--no-art-lookup" not in sys.argv
    tracks, used, written = [], set(), set()
    embedded_n = lookup_n = 0
    failures = 0  # offline runs stop asking after a few, rather than timing out twelve times

    for p in files:
        track = {"title": title_for(p), "src": "assets/music/" + quote(p.name)}
        base = ART / slug(re.sub(r"^\d{1,3}\s*[-._]\s+", "", p.stem))
        name, n = base.name, 2
        while name in used:
            name, n = f"{base.name}-{n}", n + 1
        used.add(name)
        base = ART / name

        out, source = None, None
        tag_art = embedded_cover(p) if p.suffix.lower() == ".mp3" else None
        if tag_art:
            out, source = write_cover(tag_art[0], tag_art[1], base), "tag"
        else:
            out = cached(base)
            source = "kept" if out else None
            if not out and allow_network and failures < 3:
                title, artist = split_artist(track["title"])
                if artist:
                    url = None
                    try:
                        url = lookup_cover(key, artist, title)
                        if url:
                            out, source = write_cover(fetch_bytes(url), ".jpg", base), "lookup"
                        failures = 0
                    except Exception:
                        failures += 1
                        print(f"  ! cover lookup failed for {track['title']}")

        if out:
            written.add(out.name)
            track["art"] = "assets/art/" + quote(out.name)
            embedded_n += source == "tag"
            lookup_n += source == "lookup"
        tracks.append(track)

    # covers for songs that are gone would otherwise linger and bloat the site
    for f in ART.iterdir():
        if f.is_file() and f.name not in written:
            f.unlink()
            print("Removed stale cover", f.name)

    body = json.dumps(tracks, indent=2, ensure_ascii=False)
    text = ("// Generated by make-playlist.py from assets/music. Do not edit by hand.\n"
            f"window.PLAYLIST = {body};\n")
    OUT.write_text(text, encoding="utf-8")

    # browsers cache playlist.js for a while, so stamp its content hash into index.html;
    # without this a freshly added song (or its cover) can stay invisible after a reload
    if INDEX.is_file():
        html = INDEX.read_text(encoding="utf-8")
        stamp = hashlib.md5(text.encode("utf-8")).hexdigest()[:8]
        new = re.sub(r'src="playlist\.js(\?v=[^"]*)?"', f'src="playlist.js?v={stamp}"', html, count=1)
        if new != html:
            INDEX.write_text(new, encoding="utf-8")

    print(f"Wrote {len(tracks)} track(s) to {OUT.name}")
    print(f"  covers: {embedded_n} from ID3 tags, {lookup_n} looked up, {len(written) - embedded_n - lookup_n} kept from before")
    for t in tracks:
        print("  -", t["title"], "" if t.get("art") else "(no artwork, gradient on the site)")
    if not tracks:
        print("No songs found, so the site will use the playlist in config.js instead.")


if __name__ == "__main__":
    main()
