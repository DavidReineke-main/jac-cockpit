# Deploy the cockpit server

A small Python service behind Caddy on a Linux VPS (Debian or Ubuntu). GitHub Pages keeps showing the public ORBAT and links to the server for sign-in.

## 1. Domain

Point a (sub)domain at the VPS, e.g. `cockpit.example.org` with an A record to the server's IP.

## 2. Google sign-in

1. https://console.cloud.google.com → create a project, e.g. "JAC Cockpit".
2. APIs & Services → OAuth consent screen: External, app name "JAC Cockpit", your email as support contact. Scopes: none beyond the defaults. Publish the app (no verification is needed for basic sign-in).
3. Credentials → Create credentials → OAuth client ID → Web application.
   - Authorized JavaScript origins: `https://cockpit.example.org`
4. Copy the client ID into `/etc/jac-cockpit.env` as `GOOGLE_CLIENT_ID`.

## 3. Server

```bash
sudo apt update && sudo apt install -y python3-venv git caddy
sudo useradd --system --home /opt/jac-cockpit jac
sudo git clone https://github.com/DavidReineke-main/jac-cockpit.git /opt/jac-cockpit
sudo python3 -m venv /opt/jac-cockpit/.venv
sudo /opt/jac-cockpit/.venv/bin/pip install -r /opt/jac-cockpit/server/requirements.txt
sudo mkdir -p /var/lib/jac-cockpit && sudo chown jac /var/lib/jac-cockpit
sudo cp /opt/jac-cockpit/deploy/jac-cockpit.env.example /etc/jac-cockpit.env && sudo chmod 600 /etc/jac-cockpit.env
sudo nano /etc/jac-cockpit.env        # GOOGLE_CLIENT_ID and SESSION_SECRET
sudo cp /opt/jac-cockpit/deploy/jac-cockpit.service /etc/systemd/system/
sudo systemctl enable --now jac-cockpit
sudo cp /opt/jac-cockpit/deploy/Caddyfile /etc/caddy/Caddyfile && sudo nano /etc/caddy/Caddyfile   # set the domain
sudo systemctl reload caddy
```

Open `https://cockpit.example.org`. The ORBAT shows straight away; Admin asks for sign-in.

## 4. Link GitHub Pages to the server

Set `SERVER_URL` near the top of `index.html` to `https://cockpit.example.org` and push. The Pages site then shows a "Sign in" link to the server.

## 5. Updates

```bash
cd /opt/jac-cockpit && sudo git pull && sudo /opt/jac-cockpit/.venv/bin/pip install -r server/requirements.txt && sudo systemctl restart jac-cockpit
```

## How sign-in works

1. Google sign-in identifies the person. The session cookie lasts 30 days.
2. Once, the person links their forum profile: they pick themselves from the JAC ORBAT, get a one-time code (`JAC-XXXXX`), put it into their forum signature on the forum, and press Check. The server reads their public profile and finds the code. No forum password is entered anywhere.
3. The forum user id leads to their row(s) in the course tracker: squadron, flight, rank, post. That decides what they can change:
   - JAC HQ: everything, including the deployment cycle.
   - No. 18 Squadron OC or 2IC: staffing and settings of all No. 18 flights, access by rank for No. 18.
   - Flight IC or Flight 2IC: staffing, checklists and the reinsert setting of their flight.
   - 662 and ALIC IC or 2IC: checklists and access by rank of their squadron.
   - Everyone else: reads what concerns them, e.g. their own fill-ins.

## After it runs

- **Make the sheets private.** Once the server works, the link sharing of the sheets can be switched off. Share them with the server instead: that needs a Google service account, which is the next step and is not built yet.
- **Forum reading account.** For the attendance tracker, LOAs and patrol reports the server needs its own forum account with read access to those forums, set up by a forum admin. Put it into `FORUM_USER` and `FORUM_PASSWORD`.

## Test locally

```bash
python3 -m venv .venv && .venv/bin/pip install -r server/requirements.txt
SESSION_SECRET=dev COOKIE_SECURE=0 DEV_LOGIN=1 .venv/bin/uvicorn server.app:app --port 8080
```

Then open http://localhost:8080/auth/dev?uid=4792 to act as that forum user, and http://localhost:8080/. `DEV_LOGIN` must never be set on the server.
