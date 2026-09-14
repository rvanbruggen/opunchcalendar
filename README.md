# opunch-calendar

Turns the Belgian orienteering event list on [opunch.org](https://www.opunch.org/in/event/) into iCalendar (`.ics`) feeds that anyone can subscribe to in Google Calendar, Apple Calendar or Outlook. A GitHub Actions job refreshes the feeds every day.

## How it works

- `opunch_to_ics.py` (Python 3, standard library only) calls the JSON endpoint that the O'Punch events page itself uses (`GET /in/event/list/` with an `X-Requested-With: XMLHttpRequest` header and an anonymous session cookie) and writes an `.ics` file.
- `.github/workflows/update-calendar.yml` runs the script daily and commits `docs/*.ics` when the content changed.
- GitHub Pages serves the `docs/` folder, so the feeds get a stable public URL.

## One-time setup

1. Create a new **public** GitHub repository (e.g. `opunch-calendar`) and push these files to the `main` branch.
2. **Settings → Pages → Build and deployment**: Source = *Deploy from a branch*, Branch = `main`, Folder = `/docs`. Save.
3. **Settings → Actions → General → Workflow permissions**: select *Read and write permissions*. Save.
4. **Actions** tab → *Update O'Punch calendar* → **Run workflow** to generate the first files (otherwise it runs at the next 04:17 UTC).

Your feeds are then at:

```
https://<your-github-username>.github.io/opunch-calendar/opunch.ics
https://<your-github-username>.github.io/opunch-calendar/opunch-regional-national.ics
https://<your-github-username>.github.io/opunch-calendar/opunch-national.ics
```

and `https://<your-github-username>.github.io/opunch-calendar/` shows a small page with subscribe instructions you can share.

## Subscribing

Google Calendar (web): *Other calendars* → **+** → **From URL** → paste the `.ics` link → *Add calendar*. Google polls subscribed feeds on its own schedule (typically every 12–24 h), so a change on O'Punch shows up within a day or two. Importing the file instead of subscribing gives a one-off copy that never updates.

## Running locally

```
python3 opunch_to_ics.py                    # -> docs/opunch.ics
python3 opunch_to_ics.py --levels 2 3       # regional + national only
python3 opunch_to_ics.py --dump-json raw.json
python3 opunch_to_ics.py --from-json raw.json -o test.ics   # offline
```

## What ends up in the calendar

- Title: `[LOC|REG|NAT] event name (organising club)`
- Events with a start-time window become timed events (Europe/Brussels); events without times, and multi-day events, are all-day.
- Location, GPS coordinates, organiser, level, registration deadline, a Google Maps link and the O'Punch event URL are filled in.
- Cancelled events are dropped by O'Punch's endpoint and therefore vanish from the feed on the next refresh.

## Caveats

The endpoint is undocumented; if O'Punch changes it, the workflow fails visibly in the Actions tab (the script exits non-zero when it does not get JSON). This project is not affiliated with O'Punch, FRSO or OV.
