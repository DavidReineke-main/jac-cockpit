# JAC Admin Cockpit

One page for the admin of Joint Aviation Command (4th Infantry Brigade, Arma 3): who is in which flight, who needs which course, what is still open after each op night, and what the next night needs.

This repository holds the clickable prototype. It reads the JAC Google Sheets and combines them with sample forum data. Nothing is written back anywhere.

## Views

| View | What it shows | Source |
|---|---|---|
| ORBAT | Squadrons and flights, course progress towards the next rank, open posts, who can be promoted | ORBAT and Course Tracker (Input tab), SOP 9-7 |
| Admin | Deployment cycle, op-night board, the 2IC task list, unit roster changes | Forum attendance tracker, Unit Attendance, ORBAT 2.0 |
| LOA check | LOA threads against what was entered in the attendance tracker | Forum |
| Night prep | Checklist per unit and night, logistics due that night | Requested Logistics |
| Setup | Deployment cycle editor, data sources, permissions and recurring tasks per rank | Maintained by JAC HQ |

## Rules the cockpit encodes

- **Courses per rank** come from SOP Section 09, 9-7 Joint Aviation Command Ranks.
- **Direct promotion** is offered only below NCO and without a post: SuT to A/SAcr to SAcr, Off Cdt to Plt Off, SuT to AS2 to AS1.
- **Posts** (Fg Off as Flight IC, FSAcr as Flight 2IC, MAcr as Squadron 2IC, the 662 and ALIC IC and 2IC ranks) are only filled through an advertised vacancy and a promotion board. The cockpit shows whether the post is open and who would have the courses to apply. It never offers a button.
- **Attendance** has to be in both the forum tracker and the Unit Attendance sheet within 48 hours of the night. Excused needs an LOA posted at least 3 hours before the night.
- **Unit roster**: Unit Attendance takes its names and ranks from ORBAT 2.0. JAC HQ keeps the JAC part in line with the JAC ORBAT; the cockpit lists every difference.
- **Deployment cycle**: operation, admin week(s), usually four weeks of PDT, admin, next operation. Admin weeks move, so the cycle is a list of blocks with a number of weeks; every week label is derived from it.

## Build

Needs Python 3.9 or later, no packages.

```bash
python3 scripts/fetch_sheets.py   # reads the four sheets into data/
python3 scripts/build.py          # writes dist/jac-cockpit.html
```

Open `dist/jac-cockpit.html` in a browser. `data/` and `dist/` hold member names and are ignored by git.

## Status

Prototype. Forum data (attendance tracker, LOAs, patrol reports) is sample data until the forum can be read. Actions such as Nominate, Mark passed, Promote and Remind only show what would happen.

The plan for a hosted version is in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

The interface was cleaned up with the [unslop](https://github.com/heydamir/unslop) method by Damir Sokolovsky (CC BY 4.0).
