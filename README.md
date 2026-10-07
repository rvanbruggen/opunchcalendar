# Belgian orienteering events in your calendar

> **This project has ended.** O'Punch now publishes its own calendar feed:
> `https://www.opunch.org/calendar/all` - subscribe to that instead.
> The feeds below stopped being updated on 6 October 2026 and are frozen in time.
> The official feed covers all events; there is no official regional-only or
> national-only variant.

This project publishes the upcoming orienteering events listed on [O'Punch](https://www.opunch.org/events/) as calendar feeds (`.ics`) that you can subscribe to in Google Calendar, Apple Calendar, Outlook or any other calendar app. It ran from September 2026 until 6 October 2026, when O'Punch started publishing its own feed.

## The feeds (no longer updated)

| Feed | Contains | URL |
|---|---|---|
| All events | local, regional and national events | `https://rvanbruggen.github.io/opunchcalendar/opunch.ics` |
| Regional + national | no club-level trainings | `https://rvanbruggen.github.io/opunchcalendar/opunch-regional-national.ics` |
| National only | championships and national events | `https://rvanbruggen.github.io/opunchcalendar/opunch-national.ics` |

The same links, with instructions, are on https://rvanbruggen.github.io/opunchcalendar/.

## Map of events

The web page also has a map: pick a date range (and optionally the levels) and every event in that range with a known location is shown as a marker. A marker's popup links to the event page on O'Punch and to Google Maps directions to the venue. The map reads `opunch.ics` when the page loads, so it is always as fresh as the feeds. Many events have no venue on O'Punch at all. For some of those the location is guessed from the event name and drawn as a hollow, dashed marker - treat those as a hint, not an address, and check the event page. The rest are counted under the map as missing.

## How to subscribe

Subscribe rather than import: a subscription keeps itself up to date, an import is a one-off copy.

**Google Calendar** (on the web, not in the mobile app): in the left panel next to *Other calendars* click **+**, choose **From URL**, paste the feed URL and click **Add calendar**. It then also appears in the Google Calendar app on your phone.

**Apple Calendar** (Mac): *File → New Calendar Subscription…*, paste the URL. On iPhone/iPad: *Settings → Apps → Calendar → Accounts → Add Account → Other → Add Subscribed Calendar*.

**Outlook**: *Add calendar → Subscribe from web*, paste the URL.

## What you get

Each event appears as `[LOC|REG|NAT] event name (organising club)`, with the venue and GPS location, the organiser, the level, the start-time window, the registration deadline, a Google Maps link and a link to the event page on O'Punch where you can register. Events with a start-time window are shown at that time (Belgian time); events without times, and multi-day events, are shown as all-day events.

## Good to know

- The nightly rebuild has been switched off; the feeds no longer change.
- Until 6 October 2026 the feeds were rebuilt every night from opunch.org. Calendar apps poll subscriptions on their own schedule - Google Calendar typically every 12 to 24 hours - so a change on O'Punch can take a day or two to show up.
- Cancelled events used to disappear from the feed on the next refresh; the frozen feeds still list events that have since been cancelled.
- Every refresh it ever did is recorded in the [refresh log](https://rvanbruggen.github.io/opunchcalendar/update-log.txt).
- This is an unofficial community project, not affiliated with O'Punch, FRSO, OV or LuxOC. Always check the event page on O'Punch before travelling.

Want to run or adapt this yourself? See [HOW-TO-RUN.md](HOW-TO-RUN.md).
