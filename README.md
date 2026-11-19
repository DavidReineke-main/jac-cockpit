# JAC Admin Cockpit

One place for the admin of Joint Aviation Command (4th Infantry Brigade, Arma 3): who is in which flight, who needs which course, what is still open after each op night, and what the next night needs.

- **GitHub Pages** shows the public ORBAT: https://davidreineke-main.github.io/jac-cockpit/
- **The cockpit server** adds sign-in and everything else. Members see and change what their post in the JAC ORBAT allows.

The Google Sheets stay the source of truth. The server reads them, members never edit data twice.

## Views

| View | What it shows |
|---|---|
| ORBAT (public) | Squadrons and flights, course progress towards the next rank, open posts, who can be promoted |
| Admin | Deployment cycle, op-night board, tasks for your post, fill-ins, unit roster changes |
| Night prep | The Flight IC's jobs as sub-tabs: **Staffing** (crews, autosave, mission summary for Discord), **Logistics** (orders for the night, receipt creator, order limit check), **Reports** (patrol or training report, reinsert reports), **Checklists** |
| LOA check | Waits for the forum reading account |
| Setup | Deployment cycle, flight settings, data sources, access by rank |

## What it takes off the ICs

- **Mission summary** written from the staffing, with comms plan, crew, fill-ins and the logistics orders due that night.
- **Staffing** saves as you type, suggests JAC members but takes any name, extra positions such as Shadow or WSOp, and can start from last week's crew.
- **Fill-ins** are spotted from the staffing and listed with a reminder to log them.
- **Receipts** are filled from the order in Requested Logistics (shipper, consignee, grid, pieces, type, weight, size, ETA), saved as an image for Lightshot, with the forum reply ready to paste.
- **Order limit check**: paste the company request, get the decision text with every category over its limit.
- **Patrol and training reports** are drafted from the staffing and the reinsert numbers.
- **Checks** the 2ICs and JAC HQ used to do by hand: Unit Attendance filled in for every night, entries made before a night, reinsert reports per callsign, ORBAT 2.0 out of line with the course tracker, logistics orders still open after their ETA.

## Rules the cockpit encodes

- **Courses per rank**: SOP Section 09, 9-7 Joint Aviation Command Ranks.
- **Direct promotion** only below NCO and without a post: SuT to A/SAcr to SAcr, Off Cdt to Plt Off, SuT to AS2 to AS1. Posts (Fg Off as Flight IC, FSAcr as Flight 2IC, MAcr as Squadron 2IC, the 662 and ALIC IC and 2IC ranks) only through an advertised vacancy and a promotion board.
- **Unit Attendance** within 48 hours of every night, in addition to the forum tracker.
- **Reinsert reports** on operation nights, one per crewed callsign. Each Flight IC decides whether they or their 2IC makes sure.
- **Deployment cycle**: operation, admin week(s), usually four weeks of PDT, admin, next operation, kept as a list of blocks so admin weeks can move.

## Sign-in

Google sign-in, then once a forum link: pick yourself from the ORBAT, put a one-time code into your forum signature, the server finds it on your public profile. No forum password is entered anywhere. Details in [docs/DEPLOY.md](docs/DEPLOY.md).

## Run

```bash
python3 -m venv .venv && .venv/bin/pip install -r server/requirements.txt
SESSION_SECRET=dev COOKIE_SECURE=0 DEV_LOGIN=1 .venv/bin/uvicorn server.app:app --port 8080
```

Open http://localhost:8080/auth/dev?uid=4792 to act as a forum user, then http://localhost:8080/. Deployment on a VPS: [docs/DEPLOY.md](docs/DEPLOY.md). Plans: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Not built yet

- Forum reading account for the attendance tracker, LOAs and patrol reports.
- Google service account, so the sheets can stop being shared by link.
- Training objectives for PDT, with the next PDT.

The interface was cleaned up with the [unslop](https://github.com/heydamir/unslop) method by Damir Sokolovsky (CC BY 4.0).
