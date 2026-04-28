# Pinterest Pin Automation

Post Pins to Pinterest automatically via **GitHub Actions** using the official Pinterest API v5.

---

## Quick Start

### 1. Add GitHub Secrets

Go to **Settings → Secrets → Actions** in your repo and add:

| Secret | Description |
|---|---|
| `PINTEREST_ACCESS_TOKEN` | Your Pinterest OAuth2 bearer token |
| `PINTEREST_BOARD_ID` | Target board ID (found in the board URL) |

### 2. Trigger manually

Go to **Actions → Post Pinterest Pin → Run workflow** and fill in:
- **Title** — up to 100 characters
- **Description** — up to 500 characters  
- **Image URL** — must be a publicly accessible URL
- **Board ID** — optional override of the secret

### 3. Scheduled posts

The workflow runs daily at **09:00 UTC**. Edit the `schedule` cron and the
`Post Pin (scheduled)` step in `.github/workflows/post_pin.yml` to customise
the image URL and copy.

---

## Local Development

```bash
# 1. Clone and install
pip install -r requirements.txt

# 2. Create your .env
cp .env.example .env
# Fill in PINTEREST_ACCESS_TOKEN and PINTEREST_BOARD_ID

# 3. Validate your credentials
python app.py validate

# 4. Post a pin
python app.py post \
  --title "My first pin" \
  --description "Hello from the CLI!" \
  --image-url "https://picsum.photos/800/1200"
```

---

## File Structure

```
pinterest-automation/
├── app.py                  # Flask app + CLI entry point
├── pinterest_client.py     # Pinterest API v5 wrapper
├── requirements.txt
├── .env.example
└── .github/
    └── workflows/
        └── post_pin.yml    # GitHub Actions workflow
```

---

## How it works

GitHub Actions **does not run a persistent Flask server**. Instead:

1. The workflow checks out your code and installs deps.
2. It calls `python app.py post ...` directly — Flask is used as a library,
   not a server. This means zero port conflicts and instant startup.
3. The `pinterest_client.py` module handles the API call with retry logic
   (exponential backoff on 429 rate-limit responses).

If you ever need a real HTTP webhook (e.g. from Zapier), use
`python app.py webhook ...` which exercises the `/webhook` route via
Flask's built-in test client — still no open port needed.
