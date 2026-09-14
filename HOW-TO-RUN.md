# How to run this yourself

This page is for people who want to generate the calendar on their own machine, change what goes into it, or host their own copy of the feeds.

## What is in the repository

```
opunch_to_ics.py                       the converter (Python 3, standard library only)
.github/workflows/update-calendar.yml  GitHub Actions job that rebuilds the feeds daily
docs/                                  published by GitHub Pages: index.html + the .ics files
```

## How the data is obtained

The events page on opunch.org is filled by an undocumented JSON endpoint that the page's own JavaScript calls:

```
GET https://www.opunch.org/event/list/
```

It currently answers with JSON without any cookie or special header. Until September 2026 the site lived under `/in/event/` and the endpoint then required an anonymous session cookie plus `X-Requested-With: XMLHttpRequest`, so the script still visits `https://www.opunch.org/events/` first and sends that header, in case the requirement comes back. The endpoint returns every upcoming event (about 250, up to two years ahead). Events with `status` 0 (cancelled) are skipped.

Per event the script uses `event_id`, `status`, `event_name`, `start_dt`, `end_dt`, `start_from_time`, `start_to_time`, `level` (1 local, 2 regional, 3 national), `organization_name`, `address` (venue, street, city, latitude, longitude), `reg_close_dt` and `description`.

## Running locally

Requirements: Python 3.9 or newer. No packages to install.

```bash
git clone https://github.com/rvanbruggen/opunchcalendar.git
cd opunchcalendar

python3 opunch_to_ics.py                         # writes docs/opunch.ics
python3 opunch_to_ics.py -o my.ics --levels 2 3  # regional + national only
python3 opunch_to_ics.py --levels 3 --name "BE national orienteering"
```

Open the resulting `.ics` in your calendar app, or import it once into Google Calendar via *Settings → Import & export*.

### Working offline

Save the raw JSON once, then iterate on the converter without hitting opunch.org:

```bash
python3 opunch_to_ics.py --dump-json raw.json
python3 opunch_to_ics.py --from-json raw.json -o test.ics
```

### Checking the output

`opunch_to_ics.py` writes plain RFC 5545 iCalendar. To validate it, install the `icalendar` package and parse the file:

```bash
pip install icalendar
python3 -c "from icalendar import Calendar; c=Calendar.from_ical(open('docs/opunch.ics','rb').read()); print(len(c.walk('VEVENT')),'events OK')"
```

## Customising

Everything lives in `opunch_to_ics.py`:

- `build_vevent()` decides what goes into the title, location and description of each event. Change the `[LOC]/[REG]/[NAT]` prefix in `LEVEL_TAGS`, or drop the organiser from the title, here.
- Timed events default to a 2-hour duration when O'Punch gives a start time but no end time.
- Filtering by organiser, region or federation is not built in but trivial to add where `--levels` is applied in `main()`.

## Hosting your own feeds

1. Fork this repository (it must be public for free GitHub Pages).
2. *Settings → Pages*: Source = *Deploy from a branch*, Branch = `main`, Folder = `/docs`.
3. *Settings → Actions → General → Workflow permissions*: *Read and write permissions* (the job commits the generated files).
4. *Actions* tab → *Update O'Punch calendar* → *Run workflow* to build the feeds the first time. From then on it runs every day at 04:17 UTC and only commits when the event content actually changed.
5. Replace `rvanbruggen` with your own username in `README.md` and `docs/index.html`.

Your feeds will be served from `https://<username>.github.io/opunchcalendar/opunch.ics` and friends.

## When it breaks

The endpoint is undocumented. If O'Punch changes it, the script exits with an error instead of publishing an empty calendar, and the Actions run turns red. Start debugging by opening https://www.opunch.org/events/ in a browser with the developer tools' Network tab open and looking at the request the *List* / *Calendar* tabs make.
