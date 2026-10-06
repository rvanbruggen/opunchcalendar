#!/usr/bin/env python3
"""
opunch_to_ics.py - turn the O'Punch (opunch.org) event list into an iCalendar file.

How it works
------------
The public events page (https://www.opunch.org/events/) is filled by an
undocumented JSON endpoint:

    GET https://www.opunch.org/event/list/

(Until September 2026 these lived under /in/event/ and the endpoint required an
anonymous session cookie plus X-Requested-With: XMLHttpRequest. The new endpoint
answers without either, but we still visit the events page first and send the
header, as the page's own JavaScript does, in case that requirement returns.)

It returns ~250 upcoming events. Events with status 0 (cancelled) are skipped,
so cancelled events disappear from the calendar on the next refresh.

Fields used per event:
    event_id, event_name, start_dt, end_dt (YYYY-MM-DD),
    start_from_time, start_to_time (HH:MM or null),
    level (1 = local/club, 2 = regional, 3 = national),
    organization_name, address {common_name, address, housenumber, city,
    latitude, longitude}, reg_open_dt, reg_close_dt.

Usage
-----
    python3 opunch_to_ics.py                       # writes docs/opunch.ics
    python3 opunch_to_ics.py -o out.ics            # custom output path
    python3 opunch_to_ics.py --levels 2 3          # regional + national only
    python3 opunch_to_ics.py --from-json data.json # offline / testing

Only the Python standard library is used.
"""
import argparse
import datetime as dt
import http.cookiejar
import json
import math
import re
import sys
import time
import urllib.parse
import urllib.request

BASE = "https://www.opunch.org"
PAGE_URL = BASE + "/events/"
LIST_URL = BASE + "/event/list/"
EVENT_URL = BASE + "/event/{id}"
UA = "Mozilla/5.0 (compatible; opunch-ics/1.0; +https://github.com/)"

LEVEL_NAMES = {1: "Local", 2: "Regional", 3: "National"}
LEVEL_TAGS = {1: "LOC", 2: "REG", 3: "NAT"}

# Europe/Brussels VTIMEZONE so timed events are unambiguous in every client.
VTIMEZONE = """BEGIN:VTIMEZONE
TZID:Europe/Brussels
X-LIC-LOCATION:Europe/Brussels
BEGIN:DAYLIGHT
TZOFFSETFROM:+0100
TZOFFSETTO:+0200
TZNAME:CEST
DTSTART:19700329T020000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU
END:DAYLIGHT
BEGIN:STANDARD
TZOFFSETFROM:+0200
TZOFFSETTO:+0100
TZNAME:CET
DTSTART:19701025T030000
RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU
END:STANDARD
END:VTIMEZONE"""


# --------------------------------------------------------------------------- fetch
def fetch_events(timeout=60):
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    opener.addheaders = [("User-Agent", UA), ("Accept-Language", "en")]

    # 1. get a session cookie
    with opener.open(PAGE_URL, timeout=timeout) as r:
        r.read()

    # 2. call the JSON endpoint as the page's JavaScript does
    req = urllib.request.Request(
        LIST_URL,
        headers={
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": PAGE_URL,
        },
    )
    with opener.open(req, timeout=timeout) as r:
        body = r.read().decode("utf-8")
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        sys.exit("ERROR: opunch.org did not return JSON (got HTML?). "
                 "The endpoint or the session handling may have changed.")
    events = data.get("events")
    if not isinstance(events, list):
        sys.exit("ERROR: unexpected JSON shape, no 'events' list.")
    return events


# --------------------------------------------------------------------------- ics helpers
# ----------------------------------------------------------------- geocoding
# About 60% of the events carry no address at all on O'Punch (the organiser
# never filled one in), so they cannot be shown on the map. As a fallback we
# guess a place name from the event title and look it up in Nominatim,
# restricted to Belgium. Measured against the events that DO have coordinates,
# this finds a little over half of them, all within a few km; when it is unsure
# it returns nothing rather than a wrong spot. Results are marked as
# approximate so the map and the calendar entry can say so.
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
GEO_UA = "opunch-ics/1.1 (+https://github.com/rvanbruggen/opunchcalendar)"
GEO_MIN_INTERVAL = 1.1       # Nominatim asks for at most 1 request per second
GEO_MISS_RETRY_DAYS = 30     # re-try a failed lookup once a month
GEO_DEFAULT_LIMIT = 80       # new lookups per run, to keep the daily job short

# Words that are part of event titles, never part of a place name.
GEO_STOPWORDS = set("""
entrainement entrainements entrainement entraînement entraînements ecole école co training trainingen
technische avond avondwedstrijd nacht regionale regionale régionale nationale nationales national lokale
stage stages formations formation moniteur sportif animateur initiateur externat internat jeunes club
criterium critérium regelmatigheidscriterium orientatieloop oriëntatieloop sprint middle long longue
longues distances distance relais aflossing individuele omlopen omloop kampioenschap championnat
memorial trophy trophee trophée cup series serie open helpers deel part jour dag manche wedstrijd
competitie bk vk nk test fysieke physique challenge ultra urbain urban jardin
de het een la le les du des aux and met voor van der ter
""".split())

# Nominatim result categories that can plausibly be an orienteering venue.
# Deliberately narrow: allowing amenities matched shops and cafes with the same
# name as the event ("Drykkerij Ultra" for a race called "Ultra Longues Distances").
GEO_OK_CATEGORIES = {"place", "natural", "boundary", "landuse"}

# How far from the organising club's usual area a guess may fall (km).
GEO_MAX_CLUB_KM = 40

_geo_last_call = 0.0


def geo_candidates(name):
    """Place-name guesses from an event title, best (longest) first.

    Splits on punctuation that separates title parts but keeps hyphenated
    names such as "Sart-Tilman" intact - splitting those was what once sent
    an event in Liege to Bavaria.
    """
    name = re.sub(r"\(.*?\)", " ", name or "")
    out = []
    for seg in re.split(r"[:,\u2013]|\s-\s|\s+-\s*|\||#", name):
        toks = [t for t in re.findall(r"[A-Za-z\u00c0-\u00ff][A-Za-z\u00c0-\u00ff'\-.]{2,}", seg)
                if t.lower() not in GEO_STOPWORDS]
        if toks:
            out.append(" ".join(toks))
    out.sort(key=len, reverse=True)
    return [q for q in out if len(q) >= 4][:3]


def load_geocache(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_geocache(path, cache):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=1, sort_keys=True)
    except OSError as err:
        print(f"warning: could not write {path}: {err}", file=sys.stderr)


def haversine_km(lat1, lon1, lat2, lon2):
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    return 2 * 6371.0 * math.asin(math.sqrt(a))


def club_homes(events):
    """Median coordinate per organising club, from the events that have one.

    Clubs run their events near home, so this is what tells "Bruyeres near
    Liege" from the "Bruyeres" at the other end of the country.
    """
    by_club = {}
    for e in events:
        addr = e.get("address") or {}
        club = e.get("organization_name")
        if club and addr.get("latitude") is not None and addr.get("longitude") is not None:
            by_club.setdefault(club, []).append((float(addr["latitude"]), float(addr["longitude"])))
    homes = {}
    for club, pts in by_club.items():
        if len(pts) >= 2:                      # one event is not a pattern
            lats = sorted(p[0] for p in pts)
            lons = sorted(p[1] for p in pts)
            homes[club] = (lats[len(lats) // 2], lons[len(lons) // 2])
    return homes


def nominatim_lookup(query, timeout=20):
    """Candidate places for a query, nearest-first filtering left to the caller.

    Raises on network trouble so the caller can stop hitting a sick service.
    """
    global _geo_last_call
    wait = GEO_MIN_INTERVAL - (time.monotonic() - _geo_last_call)
    if wait > 0:
        time.sleep(wait)
    _geo_last_call = time.monotonic()

    url = NOMINATIM_URL + "?" + urllib.parse.urlencode(
        {"q": query, "format": "jsonv2", "limit": 10, "countrycodes": "be", "addressdetails": 0})
    req = urllib.request.Request(url, headers={"User-Agent": GEO_UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        results = json.load(r)
    return [{"lat": float(h["lat"]), "lon": float(h["lon"]),
             "display": (h.get("display_name") or "").split(",")[0].strip()}
            for h in results if h.get("category") in GEO_OK_CATEGORIES]


def pick_hit(hits, home):
    """Choose among same-named places, or decline to choose."""
    if not hits:
        return None
    if home:
        nearest = min(hits, key=lambda h: haversine_km(home[0], home[1], h["lat"], h["lon"]))
        if haversine_km(home[0], home[1], nearest["lat"], nearest["lon"]) <= GEO_MAX_CLUB_KM:
            return nearest
        return None
    # club's area unknown: only trust a name that means exactly one place
    return hits[0] if len(hits) == 1 else None


def geocode_events(events, cache_path, limit=GEO_DEFAULT_LIMIT, timeout=20, home_events=None):
    """Fill in coordinates for events that have none, guessed from their title.

    Mutates events: sets e["address"] and e["geo_approx"]. Network failures are
    not fatal - we publish what we have rather than failing the whole run.

    home_events is the unfiltered event list to derive each club's home area
    from, so that --levels runs place an event exactly where the full feed does.
    """
    missing = [e for e in events if not (e.get("address") or {}).get("latitude")]
    if not missing:
        return 0
    homes = club_homes(home_events if home_events is not None else events)
    cache = load_geocache(cache_path)
    today = dt.date.today()
    found = new_lookups = 0
    dirty = stop = False

    for e in missing:
        home = homes.get(e.get("organization_name"))
        for query in geo_candidates(e.get("event_name")):
            entry = cache.get(query)
            if entry is not None and entry.get("miss"):
                try:
                    age = (today - dt.date.fromisoformat(entry["miss"])).days
                except ValueError:
                    age = GEO_MISS_RETRY_DAYS + 1
                if age < GEO_MISS_RETRY_DAYS:
                    continue                   # known miss, still fresh
                entry = None                   # stale miss, look it up again
            if entry is None:
                if stop or new_lookups >= limit:
                    continue                   # budget spent; try again next run
                try:
                    hits = nominatim_lookup(query, timeout)
                except Exception as err:
                    print(f"warning: geocoding stopped ({err})", file=sys.stderr)
                    stop = True
                    continue
                new_lookups += 1
                entry = {"hits": hits} if hits else {"miss": today.isoformat()}
                cache[query] = entry
                dirty = True
            if entry.get("miss"):
                continue
            hit = pick_hit(entry.get("hits") or [], home)
            if not hit:
                continue                       # ambiguous here, may suit another event
            addr = dict(e.get("address") or {})
            addr["latitude"], addr["longitude"] = hit["lat"], hit["lon"]
            e["address"] = addr
            e["geo_approx"] = hit.get("display") or query
            found += 1
            break

    if dirty:
        save_geocache(cache_path, cache)
    return found


def ics_escape(s):
    if s is None:
        return ""
    s = str(s)
    s = s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
    s = s.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\\n")
    return s


def fold(line):
    """RFC 5545 line folding at 75 octets."""
    out = []
    data = line.encode("utf-8")
    first = True
    while data:
        limit = 75 if first else 74
        chunk = data[:limit]
        # do not split inside a multi-byte UTF-8 sequence
        while chunk and (chunk[-1] & 0xC0) == 0x80 and len(chunk) < len(data):
            chunk = chunk[:-1]
        # also ensure we don't end on a lead byte
        try:
            chunk.decode("utf-8")
        except UnicodeDecodeError:
            chunk = chunk[:-1]
        out.append(("" if first else " ") + chunk.decode("utf-8"))
        data = data[len(chunk):]
        first = False
    return "\r\n".join(out)


def strip_html(s):
    if not s:
        return ""
    s = re.sub(r"<\s*br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"</\s*(p|div|li|h\d)\s*>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = (s.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<")
          .replace("&gt;", ">").replace("&quot;", '"').replace("&#39;", "'"))
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def parse_date(s):
    return dt.date.fromisoformat(s[:10])


def parse_time(s):
    if not s:
        return None
    m = re.match(r"^(\d{1,2}):(\d{2})", s)
    return dt.time(int(m.group(1)), int(m.group(2))) if m else None


# --------------------------------------------------------------------------- event -> VEVENT
def build_vevent(e, stamp):
    eid = e.get("event_id")
    name = (e.get("event_name") or "Orienteering event").strip()
    level = e.get("level")
    org = (e.get("organization_name") or "").strip()
    start_d = parse_date(e["start_dt"])
    end_d = parse_date(e.get("end_dt") or e["start_dt"])
    if end_d < start_d:
        end_d = start_d
    t_from = parse_time(e.get("start_from_time"))
    t_to = parse_time(e.get("start_to_time"))

    tag = LEVEL_TAGS.get(level)
    summary = f"[{tag}] {name}" if tag else name
    if org:
        summary += f" ({org})"

    lines = ["BEGIN:VEVENT",
             f"UID:opunch-{eid}@opunch.org",
             f"DTSTAMP:{stamp}"]

    if t_from and start_d == end_d:
        # timed event on a single day; "start window" from..to, default 2h
        if not t_to or t_to <= t_from:
            end_dt = dt.datetime.combine(start_d, t_from) + dt.timedelta(hours=2)
        else:
            end_dt = dt.datetime.combine(start_d, t_to)
        lines.append("DTSTART;TZID=Europe/Brussels:" +
                     dt.datetime.combine(start_d, t_from).strftime("%Y%m%dT%H%M%S"))
        lines.append("DTEND;TZID=Europe/Brussels:" + end_dt.strftime("%Y%m%dT%H%M%S"))
    else:
        # all-day (possibly multi-day); DTEND is exclusive
        lines.append("DTSTART;VALUE=DATE:" + start_d.strftime("%Y%m%d"))
        lines.append("DTEND;VALUE=DATE:" + (end_d + dt.timedelta(days=1)).strftime("%Y%m%d"))

    lines.append("SUMMARY:" + ics_escape(summary))

    # location
    addr = e.get("address") or {}
    loc_parts = []
    if addr.get("common_name"):
        loc_parts.append(addr["common_name"].strip())
    street = " ".join(p for p in [(addr.get("address") or "").strip(),
                                  (addr.get("housenumber") or "").strip()] if p)
    if street:
        loc_parts.append(street)
    if addr.get("city"):
        loc_parts.append(addr["city"].strip())
    approx = e.get("geo_approx")
    if not loc_parts and approx:
        loc_parts.append(f"near {approx} (approximate)")
    if loc_parts:
        lines.append("LOCATION:" + ics_escape(", ".join(loc_parts)))
    if addr.get("latitude") is not None and addr.get("longitude") is not None:
        lines.append(f"GEO:{addr['latitude']};{addr['longitude']}")
        if approx:
            # read by the map on the landing page, and harmless to calendar apps
            lines.append("X-OPUNCH-GEO:APPROXIMATE")

    url = EVENT_URL.format(id=eid)
    lines.append("URL:" + url)

    # description
    desc = []
    if org:
        desc.append(f"Organiser: {org}")
    if level in LEVEL_NAMES:
        desc.append(f"Level: {LEVEL_NAMES[level]}")
    if t_from:
        window = t_from.strftime("%H:%M") + (f" - {t_to.strftime('%H:%M')}" if t_to else "")
        desc.append(f"Start times: {window}")
    if e.get("reg_close_dt"):
        desc.append(f"Registration closes: {e['reg_close_dt'][:10]}")
    if addr.get("latitude") is not None and addr.get("longitude") is not None:
        desc.append(f"Map: https://www.google.com/maps?q={addr['latitude']},{addr['longitude']}")
        if approx:
            desc.append(f"NOTE: no venue given on O'Punch; the location above is guessed "
                        f"from the event name ({approx}) and may be off. Check the event page.")
    desc.append(f"Details & registration: {url}")
    body = strip_html(e.get("description"))
    if body:
        desc.append("")
        desc.append(body[:1500])
    lines.append("DESCRIPTION:" + ics_escape("\n".join(desc)))

    if level in LEVEL_NAMES:
        lines.append("CATEGORIES:Orienteering," + LEVEL_NAMES[level])
    else:
        lines.append("CATEGORIES:Orienteering")
    lines.append("END:VEVENT")
    return lines


def build_calendar(events, name="Orienteering Belgium (O'Punch)"):
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = ["BEGIN:VCALENDAR",
           "VERSION:2.0",
           "PRODID:-//opunch-ics//opunch_to_ics.py//EN",
           "CALSCALE:GREGORIAN",
           "METHOD:PUBLISH",
           "X-WR-CALNAME:" + ics_escape(name),
           "X-WR-TIMEZONE:Europe/Brussels",
           "X-WR-CALDESC:" + ics_escape("Upcoming orienteering events from opunch.org"),
           "REFRESH-INTERVAL;VALUE=DURATION:P1D",
           "X-PUBLISHED-TTL:P1D"]
    out += VTIMEZONE.split("\n")
    for e in events:
        try:
            out += build_vevent(e, stamp)
        except Exception as ex:  # one bad record must not kill the feed
            print(f"WARNING: skipping event {e.get('event_id')}: {ex}", file=sys.stderr)
    out.append("END:VCALENDAR")
    return "\r\n".join(fold(l) for l in out) + "\r\n"


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--output", default="docs/opunch.ics")
    ap.add_argument("--levels", type=int, nargs="*", help="keep only these levels (1 local, 2 regional, 3 national)")
    ap.add_argument("--from-json", help="read events from a saved JSON file instead of opunch.org")
    ap.add_argument("--dump-json", help="also save the raw JSON to this path")
    ap.add_argument("--name", default="Orienteering Belgium (O'Punch)", help="calendar display name")
    ap.add_argument("--no-geocode", action="store_true",
                    help="do not guess coordinates for events without an address")
    ap.add_argument("--geocache", default="geocache.json", help="where to keep geocoding results")
    ap.add_argument("--geocode-limit", type=int, default=GEO_DEFAULT_LIMIT,
                    help="maximum new Nominatim lookups per run")
    args = ap.parse_args()

    if args.from_json:
        with open(args.from_json, encoding="utf-8") as f:
            data = json.load(f)
        events = data["events"] if isinstance(data, dict) else data
    else:
        events = fetch_events()

    if args.dump_json:
        with open(args.dump_json, "w", encoding="utf-8") as f:
            json.dump({"events": events}, f, ensure_ascii=False, indent=1)

    # status 0 = cancelled (the site's map labels these as cancelled)
    events = [e for e in events if e.get("status") != 0]
    all_events = events

    if args.levels:
        events = [e for e in events if e.get("level") in set(args.levels)]

    if not args.no_geocode:
        n = geocode_events(events, args.geocache, args.geocode_limit, home_events=all_events)
        if n:
            print(f"Guessed a location for {n} event(s) without an address")

    events.sort(key=lambda e: (e.get("start_dt") or "", e.get("event_id") or 0))
    ics = build_calendar(events, args.name)

    import os
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8", newline="") as f:
        f.write(ics)
    print(f"Wrote {len(events)} events to {args.output}")


if __name__ == "__main__":
    main()
