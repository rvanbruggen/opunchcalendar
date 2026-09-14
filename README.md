# Belgian orienteering events in your calendar

This project publishes the upcoming orienteering events listed on [O'Punch](https://www.opunch.org/events/) as calendar feeds (`.ics`) that you can subscribe to in Google Calendar, Apple Calendar, Outlook or any other calendar app. The feeds are refreshed automatically every day.

## The feeds

| Feed | Contains | URL |
|---|---|---|
| All events | local, regional and national events | `https://rvanbruggen.github.io/opunchcalendar/opunch.ics` |
| Regional + national | no club-level trainings | `https://rvanbruggen.github.io/opunchcalendar/opunch-regional-national.ics` |
| National only | championships and national events | `https://rvanbruggen.github.io/opunchcalendar/opunch-national.ics` |

The same links, with instructions, are on https://rvanbruggen.github.io/opunchcalendar/.

## How to subscribe

Subscribe rather than import: a subscription keeps itself up to date, an import is a one-off copy.

**Google Calendar** (on the web, not in the mobile app): in the left panel next to *Other calendars* click **+**, choose **From URL**, paste the feed URL and click **Add calendar**. It then also appears in the Google Calendar app on your phone.

**Apple Calendar** (Mac): *File → New Calendar Subscription…*, paste the URL. On iPhone/iPad: *Settings → Apps → Calendar → Accounts → Add Account → Other → Add Subscribed Calendar*.

**Outlook**: *Add calendar → Subscribe from web*, paste the URL.

## What you get

Each event appears as `[LOC|REG|NAT] event name (organising club)`, with the venue and GPS location, the organiser, the level, the start-time window, the registration deadline, a Google Maps link and a link to the event page on O'Punch where you can register. Events with a start-time window are shown at that time (Belgian time); events without times, and multi-day events, are shown as all-day events.

## Good to know

- The feeds are rebuilt every night from opunch.org. Calendar apps poll subscriptions on their own schedule - Google Calendar typically every 12 to 24 hours - so a change on O'Punch can take a day or two to show up.
- Events that are cancelled on O'Punch disappear from the feed on the next refresh.
- This is an unofficial community project, not affiliated with O'Punch, FRSO, OV or LuxOC. Always check the event page on O'Punch before travelling.

Want to run or adapt this yourself? See [HOW-TO-RUN.md](HOW-TO-RUN.md).
