# Hosted version: architecture

How the prototype becomes a dashboard JAC can use every week. Written for JAC HQ, BG HQ and J6.

## Goal

The 2ICs and squadron HQs see in one place what they still have to do. JAC HQ sees whether it gets done across No. 18, No. 662 and ALIC. The forum and the sheets stay where the work is recorded; the dashboard reads them and points to the right place.

## Constraints

- **Forum** runs MyBB with custom pages (attendance tracker, ORBAT, events). MyBB has no REST API and no OAuth. Access through the webmaster is unlikely for now.
- **Discord** is out of scope. A bot in the unit server would not be approved.
- **Google**: members use private Gmail accounts. The relevant sheets are shared by link, so their CSV export is readable without a login.
- **Hosting**: a small VPS run by a JAC member.

## Data sources

| Source | How it is read | How often |
|---|---|---|
| ORBAT and Course Tracker, Input tab | CSV export | Every 15 minutes |
| Unit Attendance, JAC tab | CSV export | Every 15 minutes |
| Unit roster, ORBAT 2.0 | CSV export | Hourly |
| Requested Logistics | CSV export | Every 15 minutes |
| Forum attendance tracker | `attendance.php?action=export` with a read-only forum account | After each op night |
| Forum LOA and patrol report threads | Thread lists of the flight forums with the same account | Every 15 minutes |
| SOP 9-7 course requirements | Kept as configuration, updated when the SOP changes | By hand |
| Deployment cycle, permissions, recurring tasks | Dashboard database, edited in Setup | By hand |

The read-only forum account is the only new thing the unit has to agree to. If that is refused, the forum parts stay as links.

## Sign-in

Google sign-in, since everyone already has a Google account for the Drive. JAC HQ links each Google account to a forum profile once (the forum user id is already in the course tracker). Rank, squadron and flight then come from the course tracker, so access always follows the ORBAT and nobody maintains a second list.

## Permissions

Per squadron HQ, per rank, as in Setup: who can see the LOA check, edit night prep, manage course nominations, and which recurring tasks each rank owns. JAC HQ sees all squadrons. Nobody can promote into a post from the dashboard.

## Components

```
                   ┌─────────────────────────┐
 Google Sheets ───▶│  fetcher (cron, Python) │───┐
 Forum (read-only)▶│                         │   │
                   └─────────────────────────┘   ▼
                                           ┌───────────┐     ┌────────────────┐
                                           │  SQLite   │◀───▶│  web app       │◀── Google sign-in
                                           └───────────┘     │  (the cockpit) │
                                                             └────────────────┘
```

- **Fetcher**: `scripts/fetch_sheets.py` grows into a scheduled job that also reads the forum and stores snapshots with a timestamp.
- **Database**: SQLite is enough for one unit. Holds snapshots, the cycle, permissions, task state (done, reminded).
- **Web app**: the current page, served by a small Python app (FastAPI or Flask) that reads from the database instead of inlined JSON.

## Writing back

Not in the first version. Later, in this order:

1. Course results into the Input tab of the course tracker, through a Google service account that is given edit access to that one sheet.
2. Unit Attendance entries, so a 2IC fills in one form and both places are updated.
3. Forum posts (patrol report sign-off, PMs) only if the webmaster agrees.

## Build order

1. Host the prototype as it is, refreshed by the fetcher. Read-only, Google sign-in, JAC HQ only.
2. Read the forum attendance tracker and LOA threads with the read-only account. Replaces the sample data.
3. Open it to squadron HQs and 2ICs with the permissions from Setup.
4. Task state that persists (done, reminders) and a weekly summary for JAC HQ.
5. Writing back, as above.
