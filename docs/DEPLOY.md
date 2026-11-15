# Deploying VirtuTrade for free

VirtuTrade needs two things to feel like a real paper-trading site:

1. **One always-on process** that receives prices (the DNSE stream, or the practice
   simulator) and records one-minute candles.
2. **A disk that keeps the SQLite database**, because accounts, holdings and trades
   live in it.

The three free options differ exactly on those two points.

| | Google Cloud e2-micro VM | Render free web service | GitHub Codespaces |
|---|---|---|---|
| Use it for | The public site, with real DNSE data | A quick public demo | Coding and classroom demos |
| Keeps running | Always on | Sleeps after 15 idle minutes; about one minute to wake | Stops after 30 idle minutes (default) |
| Keeps the database | Yes (persistent disk) | **No**: lost on every restart, redeploy or sleep | While the codespace exists |
| Market feed | Separate `virtutrade-feed` service | Thread inside the web process | Thread inside the web process |
| Cost | Free inside the Always Free limits; needs a billing account | Free, 750 instance-hours a month | Free, 120 core-hours a month (personal account) |

Render and Codespaces facts were read on 7 November 2026 from
<https://render.com/docs/free> and
<https://docs.github.com/en/billing/concepts/product-billing/github-codespaces>.
The Google Cloud figures below are from the team's previous setup and **were not
re-verified**: check <https://cloud.google.com/free/docs/free-cloud-features> before
creating the VM.

**Recommendation:** Google Cloud for the real site, Codespaces for development.
Render's free plan suits a throwaway demo only, because every account and trade
disappears whenever the service sleeps.

## Option 1: Google Cloud e2-micro (recommended)

### What stays free (verify first)

- One `e2-micro` VM in `us-west1`, `us-central1` or `us-east1`.
- Up to 30 GB of **standard** persistent disk (choose "Standard persistent disk",
  not "Balanced").
- Limited outbound traffic per month; VirtuTrade's own traffic is small.
- Check whether the VM's **external IPv4 address** is charged in your billing
  account. Google started charging for in-use external IPv4 addresses in 2024;
  confirm the current rule on the pricing page or in Billing → Reports after the
  first day.

Before anything else, open **Billing → Budgets & alerts** and create a budget of
1 USD with e-mail alerts at 50% and 100%. That turns any surprise charge into an
e-mail instead of a bill.

### Create the VM

In Cloud Shell (or with the `gcloud` CLI):

```bash
gcloud compute instances create virtutrade \
  --zone=us-central1-a --machine-type=e2-micro \
  --image-family=debian-12 --image-project=debian-cloud \
  --boot-disk-size=30GB --boot-disk-type=pd-standard \
  --tags=http-server,https-server
gcloud compute firewall-rules create virtutrade-web \
  --allow=tcp:80,tcp:443 --target-tags=http-server,https-server
```

In the console, the equivalent is: Compute Engine → Create instance, region
`us-central1`, machine `e2-micro`, boot disk Debian 12 / Standard persistent disk /
30 GB, and tick **Allow HTTP traffic** and **Allow HTTPS traffic**.

### Install

SSH into the VM (the console's **SSH** button works) and run:

```bash
curl -fsSLO https://raw.githubusercontent.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation/main/deploy/gcp/setup.sh
bash setup.sh
```

The script installs Python, Git and Caddy, adds 1 GB of swap, clones the
repository into `/opt/virtutrade`, creates the database in
`/var/lib/virtutrade`, writes `/etc/virtutrade/virtutrade.env` with a random
`SECRET_KEY`, and starts three services: `virtutrade-web` (gunicorn),
`virtutrade-feed` and `caddy`. It prints the address, which is
`https://<external-ip-with-dashes>.sslip.io`. Caddy gets the HTTPS certificate
automatically on the first visit. To use your own domain, point it at the VM and
run `SITE_ADDRESS=your.domain bash setup.sh`.

It starts with **real DNSE prices** from the credential-free public feed (see the
caveat below). Outside trading hours those prices are older than 15 minutes, so
orders are refused until the next session, as the order rules require. Running the script again updates the code and keeps the database and
settings.

### Switch to real DNSE data

**Without a key (the default after setup):** `QUOTE_MODE=dnse` with
`FEED_COMMAND=public-feed`. This reads real candles from DNSE's public chart
endpoint, the one behind DNSE's own web price board. It is unofficial and undocumented:
DNSE may change or block it at any time, so it polls once a minute and identifies itself
as a student project. Prefer the signed feed below as soon as a key works.

**With a DNSE API key:**

```bash
sudo nano /etc/virtutrade/virtutrade.env
```

Set `FEED_COMMAND=stream`, `DNSE_API_KEY` and `DNSE_API_SECRET`, and keep
`QUOTE_MODE=dnse`. Both DNSE feeds store provider prices, so the same
`/var/lib/virtutrade/dnse.db` keeps its candles and accounts. Never point a DNSE
feed at a simulation database (or the simulator at a DNSE one): both refuse to
mix generated and provider prices. Then:

```bash
sudo -u virtutrade bash -c 'set -a; . /etc/virtutrade/virtutrade.env; set +a; cd /opt/virtutrade; .venv/bin/python -m virtutrade init-db'
sudo systemctl restart virtutrade-web virtutrade-feed
journalctl -u virtutrade-feed -f
```

The feed log should show the WebSocket subscription and a candle refresh. If it
shows `DNSE rejected authentication` or `DNSE refused OHLC access`, the key is
not valid for this machine. Check that the key has not been regenerated, and
whether the DNSE portal limits API keys to particular IP addresses. On
7 November 2026 the team's existing key returned HTTP 401 for both the
latest-trade and OHLC endpoints, so a new key is needed before going live.

DNSE states that placing an order also needs a second factor (Smart OTP or
Email OTP), and VirtuTrade calls no order endpoint. A leaked key still exposes
read access, so treat it like a password: never commit it, never paste it into
an issue or screenshot, and regenerate it in the DNSE portal if it is ever
exposed.

### Operate

| Task | Command |
|---|---|
| Logs | `journalctl -u virtutrade-web -u virtutrade-feed -f` |
| Restart after changing settings | `sudo systemctl restart virtutrade-web virtutrade-feed` |
| Update to the latest `main` | `bash setup.sh` |
| Back up the database | `sudo systemctl stop virtutrade-feed && sudo cp /var/lib/virtutrade/dnse.db ~/virtutrade-$(date +%F).db && sudo systemctl start virtutrade-feed` |

## Option 2: Render free (demo only)

The repository contains a Blueprint, `render.yaml`. In Render choose
**New → Blueprint**, select this repository and apply. It runs the practice
simulator inside the web process (`MARKET_FEED=simulation`) with a generated
`SECRET_KEY`.

For real prices instead of the simulator, change three variables in the Render dashboard:
`QUOTE_MODE=dnse`, `MARKET_FEED=dnse-public` and `DATABASE_PATH=instance/dnse.db`, and
replace `init-demo` with `init-db` in the start command. No secret is needed. Candle history
is downloaded again on each start, so only accounts and trades are lost when it sleeps.

Read Render's limits before sharing the link. The service sleeps after 15 idle
minutes and loses its files on every restart, so the next visitor finds a fresh
market with no accounts. Do not put DNSE credentials on it unless you accept
that the market data is only received while someone keeps the service awake.

## Option 3: GitHub Codespaces (development and class demos)

Open the repository on GitHub → **Code → Codespaces → Create codespace on main**.
The dev container installs the app, copies `.devcontainer/demo.env` to `.env`
(only if `.env` does not exist yet), creates a simulation database and starts
`python -m virtutrade run` with the simulator inside it. Port 5000 opens in the
browser. Stop the codespace when you finish, so the free hours last.

`TRUST_PROXY=1` lets the login origin check see the forwarded public host name.
This has not yet been tested inside a real codespace: if registration or login
reports a cross-site request error there, report it on the issue and run the
app locally until it is fixed.

## Settings reference

| Variable | Values | Purpose |
|---|---|---|
| `QUOTE_MODE` | `seed`, `simulation`, `dnse` | Which quotes the site shows and trades on |
| `MARKET_FEED` | `off`, `simulation`, `dnse`, `dnse-public` | Feed run **inside** the web process (single-service hosts) |
| `FEED_COMMAND` | `simulate`, `stream`, `public-feed` | Feed run by the separate `virtutrade-feed` service (Google Cloud) |
| `SIMULATION_TICK_SECONDS` | default `20` | Seconds between simulated price moves |
| `TRUST_PROXY` | `1` or empty | Set only behind exactly one HTTPS proxy (Caddy, Render, Codespaces) |
| `SECRET_KEY` | long random value | Signs sessions and CSRF tokens; keep it stable in production |

Never run `MARKET_FEED` and a separate feed service on the same database, and
keep gunicorn at one worker: each worker would start its own feed.

### Why the simulator moves every 20 seconds

Confirming an order checks that the quote has the same timestamp as the
preview. This is the accepted rule from #107 and the US05 evidence: a user only
confirms a price they have seen. If a quote moves between preview and confirm,
the order is refused and the user previews again. A 20-second step leaves time
to preview and confirm. With real DNSE ticks during trading hours, this refusal
will be more frequent; changing the rule is a product decision.
