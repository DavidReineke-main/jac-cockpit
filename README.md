# JAC Admin Cockpit

One page for the admin of Joint Aviation Command (4th Infantry Brigade, Arma 3): who is in which flight, who needs which course, what is still open after each op night, and what the next night needs.

The Google Sheets are the backend. The page is a single static `index.html` that reads them live in the background, so no member data lives in this repository.

## Views

| View | What it shows | Source |
|---|---|---|
| ORBAT | Squadrons and flights, course progress towards the next rank, open posts, who can be promoted | ORBAT and Course Tracker (Input tab), SOP 9-7 |
| Admin | Deployment cycle, op-night board, the task list, fill-ins, unit roster changes | Unit Attendance, reinsert reports, ORBAT 2.0, staffing |
| Night prep | Staffing per night, mission summary to paste into Discord, patrol or training report, checklists, logistics due that night | Staffing entries, Requested Logistics, reinsert reports |
| LOA check | What the forum check will flag | Needs the hosted backend |
| Setup | Deployment cycle, flight settings, data sources, access by rank | Entries |

## Rules the cockpit encodes

- **Courses per rank** come from SOP Section 09, 9-7 Joint Aviation Command Ranks.
- **Direct promotion** is shown only below NCO and without a post: SuT to A/SAcr to SAcr, Off Cdt to Plt Off, SuT to AS2 to AS1.
- **Posts** (Fg Off as Flight IC, FSAcr as Flight 2IC, MAcr as Squadron 2IC, the 662 and ALIC IC and 2IC ranks) are filled only through an advertised vacancy and a promotion board. The cockpit shows whether the post is open and who would have the courses to apply.
- **Unit Attendance**: the 2ICs enter every night there as well as in the forum tracker, within 48 hours. The cockpit flags missing or partial nights and entries made before the night.
- **Unit roster**: Unit Attendance takes its names and ranks from ORBAT 2.0. JAC HQ keeps the JAC part in line with the course tracker; the cockpit lists every difference.
- **Reinsert reports**: on operation nights the loadmasters file one report per crewed callsign in the casualty and reinsert form. Each Flight IC sets in Setup whether they or their 2IC makes sure it happens.
- **Fill-ins**: anyone staffed outside their own flight is listed and reminded to log the fill-in.
- **Deployment cycle**: operation, admin week(s), usually four weeks of PDT, admin, next operation. Admin weeks move, so the cycle is a list of blocks with a number of weeks; week labels and op nights are derived from it.

## Data

Read with the sheets' CSV export (`/export?format=csv&gid=…`), which Google serves with CORS. The `gviz` endpoint is not used because it drops values in mixed-type columns.

Staffing, checklists, settings and the cycle are "entries". Until the entries form is connected they stay in the viewer's browser. Setting it up takes five minutes, see [docs/ENTRIES-FORM.md](docs/ENTRIES-FORM.md).

On load the page shows the last data it saw (browser cache), then refreshes every source in the background and again every 10 minutes.

## Run locally

```bash
python3 -m http.server 8000
```

Then open http://localhost:8000.

## Status

Prototype. The forum (attendance tracker, LOAs, patrol reports) needs a small backend with a read-only forum account. The plan is in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Training objectives for PDT come with the next PDT.

The interface was cleaned up with the [unslop](https://github.com/heydamir/unslop) method by Damir Sokolovsky (CC BY 4.0).
