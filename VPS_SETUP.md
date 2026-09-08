# Google Cloud VPS — step by step

Everything needed to stand up a server for the Agent Desk and hand back
the values that go into `.env`.

> **Check first:** `desk.sagaxventures.com` is already live and serving
> `server.py`. If SSH access to that machine still exists, skip this
> entire document and deploy there instead — it costs nothing extra and
> the DNS, TLS and nginx are already working.

---

## 0. What you will end up with

Six values for `.env`:

```
GCP_PROJECT_ID=       GCP_ZONE=        GCP_INSTANCE_NAME=
VPS_HOST=             VPS_SSH_USER=    VPS_SSH_KEY_PATH=
```

`VPS_SSH_KEY_PATH` is a **path to a file on your laptop**, never the key
text itself. A private key pasted into an environment variable ends up
in logs, shell history, and eventually somewhere you did not intend.

---

## 1. Project and billing

1. Go to <https://console.cloud.google.com>
2. Top bar → project dropdown → **New Project**
3. Name it `saga-x-desk`. Note the **Project ID** it generates — usually
   `saga-x-desk-123456`, and it is *not* the same as the display name.
   That ID is `GCP_PROJECT_ID`.
4. Billing must be enabled or you cannot create a VM. Left menu →
   **Billing** → link an account.

---

## 2. Create the VM

Left menu → **Compute Engine → VM instances → Create instance**.
(The first visit takes a minute while the API enables itself.)

| Field | Value | Why |
|---|---|---|
| Name | `saga-x-desk` | becomes `GCP_INSTANCE_NAME` |
| Region | `asia-southeast1` (Singapore) | closest to Malaysia; every request from your phone crosses this |
| Zone | `asia-southeast1-b` | becomes `GCP_ZONE` |
| Series | E2 | cheapest general purpose |
| Machine type | `e2-small` (2 vCPU, 2 GB) | `e2-micro` works, but 1 GB gets tight with Python plus nginx |
| Boot disk | Ubuntu 24.04 LTS, 20 GB standard | matches `DEPLOY.md` |
| Firewall | tick **Allow HTTP** and **Allow HTTPS** | nginx needs both |

**Watch the monthly estimate** shown on the right as you configure. It
updates live. Google's free tier covers `e2-micro` only in three US
regions — a Singapore instance is not free, and the estimate is the real
number, not the ~$0 the free-tier banner suggests.

Click **Create**, wait for the green tick, then copy the **External IP**
from the instance list. That is `VPS_HOST`.

> Reserve it: **VPC network → IP addresses**, find the ephemeral address,
> **Reserve**. Otherwise the IP changes on restart and your DNS silently
> points at nothing. This is worth doing before you touch DNS.

---

## 3. SSH key

Generate on your laptop, in Git Bash:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/sagax_vps -C "sagax-desk"
```

Press Enter twice to skip the passphrase — a passphrase would mean
someone typing it on every automated deploy, which defeats the point.

This writes two files:

- `~/.ssh/sagax_vps` — **private**. Never leaves your machine, never
  gets pasted anywhere. This path is `VPS_SSH_KEY_PATH`.
- `~/.ssh/sagax_vps.pub` — public. Safe to hand out.

Print the public one:

```bash
cat ~/.ssh/sagax_vps.pub
```

It is one line, starting `ssh-ed25519 AAAA…` and ending with
`sagax-desk`. **The last word is the username the key logs in as** —
Google reads it that way. So `VPS_SSH_USER` is `sagax-desk`.

Add it: **Compute Engine → VM instances →** click `saga-x-desk` →
**Edit** → scroll to **SSH Keys** → **Add item** → paste the whole line
→ **Save**.

Test it:

```bash
ssh -i ~/.ssh/sagax_vps sagax-desk@<VPS_HOST>
```

First connection asks about the host fingerprint; answer `yes`. If you
land at a shell prompt, the key works. Type `exit`.

If it refuses, the usual cause is the username: it must match the
comment at the end of the public key exactly.

---

## 4. Prepare the machine

On the VM:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv nginx git certbot python3-certbot-nginx
sudo mkdir -p /opt/saga-x-desk
sudo chown -R $USER:$USER /opt/saga-x-desk
```

Confirm Python is 3.10 or newer:

```bash
python3 --version
```

---

## 5. DNS

Only after the IP is reserved. In Cloudflare, on `sagaxventures.com`:

- Type `A`, name `desk`, content `<VPS_HOST>`, proxy **on** (orange cloud)

Leave the proxy on — it is what gives you HTTPS at the edge and hides
the origin IP.

> If `desk.sagaxventures.com` currently points at the existing server,
> changing this record **moves the live desk**. Do it when you are ready
> to cut over, not while testing.

---

## 6. Fill `.env`

```
GCP_PROJECT_ID=saga-x-desk-123456
GCP_ZONE=asia-southeast1-b
GCP_INSTANCE_NAME=saga-x-desk
VPS_HOST=<external IP>
VPS_SSH_USER=sagax-desk
VPS_SSH_KEY_PATH=C:/Users/User/.ssh/sagax_vps
VPS_APP_DIR=/opt/saga-x-desk
```

Forward slashes in the key path, even on Windows — backslashes get eaten
as escape characters.

---

## 7. Hand back

Say the word once `.env` is filled and the SSH test passed. Then:

1. Copy the app across and `pip install -r requirements.txt`
2. `DATABASE_URL`, `OPENAI_API_KEY` and the rest into the systemd unit —
   not into a file in the app directory
3. Run `import_legacy()` **on the VM**, where the real `state.json` and
   `history.jsonl` live
4. nginx + certbot per `DEPLOY.md`
5. Three cron entries: scheduler every 15 min, monitors every 6 h,
   notifications every 5 min
6. `python -m agents.preflight` on the VM — the same checks that pass
   locally must pass there before we call it done

---

## Gotchas hit during the real build

Three things cost time. All are fixed in `deploy.sh`, recorded here so
they do not cost it twice.

**Supabase's direct connection is IPv6-only.** `db.<ref>.supabase.co`
resolves to an IPv6 address. A GCP VM has no IPv6 by default, so it
fails with `Network is unreachable` — while working perfectly from a
home network that has IPv6. Use the **pooler** instead:

```
postgresql://postgres.<ref>:<pw>@aws-0-<region>.pooler.supabase.com:5432/postgres
```

The pooler region is the *Supabase project's* region, which need not be
the VM's. This project turned out to be `ap-southeast-2` while the VM is
in `ap-southeast-1`.

**Git Bash on Windows has no rsync.** `deploy.sh` falls back to tar over
ssh, which needs nothing installed. The fallback cannot delete files
removed locally, so a file dropped from the repo lingers on the VM.

**The env file must be owned by the app user, not root.** systemd reads
it as root either way, but the cron jobs run as `sagax-desk` and a
root-owned 0600 file is unreadable to them. Mode stays 0600.

## Costs

Two things now bill monthly, and they are separate:

| | |
|---|---|
| GCP VM (`e2-small`, Singapore) | see the console estimate |
| OpenAI (`gpt-5.6-sol`) | ~$13.50 measured, capped at $30 |

Supabase and Cloudflare stay on free tiers at this volume.

If the VM estimate is uncomfortable, `e2-micro` halves it and will run
this workload — the desk is a small Python process and a few cron jobs,
not a busy application.
