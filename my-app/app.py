"""
Pinterest Pin Automation — Flask App
=====================================
Runs in two modes:

  1. CLI mode (GitHub Actions):
       python app.py --mode post \
         --board-id 123456789 \
         --title "My Pin" \
         --description "Check this out!" \
         --image-url "https://example.com/image.jpg"

  2. Webhook mode (manual HTTP trigger via test client):
       python app.py --mode webhook
       # Then POST JSON to /webhook in another process or test

Environment variables (set as GitHub Secrets):
  PINTEREST_ACCESS_TOKEN  — OAuth2 bearer token
  PINTEREST_BOARD_ID      — Default board ID (can be overridden per call)
"""

import argparse
import json
import os
import sys

from dotenv import load_dotenv
from flask import Flask, jsonify, request

from pinterest_client import create_pin, get_board

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

load_dotenv()  # Loads .env in local dev; GitHub Secrets are already env vars

app = Flask(__name__)


def _get_token() -> str:
    token = os.environ.get("PINTEREST_ACCESS_TOKEN", "")
    if not token:
        raise EnvironmentError(
            "PINTEREST_ACCESS_TOKEN is not set. "
            "Add it as a GitHub Secret or in your .env file."
        )
    return token


# ---------------------------------------------------------------------------
# Flask routes  (used when you need a real HTTP interface or test client)
# ---------------------------------------------------------------------------

@app.route("/health", methods=["GET"])
def health():
    """Quick liveness check."""
    return jsonify({"status": "ok"}), 200


@app.route("/webhook", methods=["POST"])
def webhook():
    """
    Accept a JSON body and post a Pin to Pinterest.

    Expected JSON:
    {
        "board_id":    "123456789",        // optional, falls back to env var
        "title":       "Pin title",
        "description": "Pin description",
        "image_url":   "https://..."
    }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    # Required fields
    image_url = data.get("image_url", "").strip()
    title = data.get("title", "").strip()
    description = data.get("description", "").strip()
    board_id = data.get("board_id", "").strip() or os.environ.get("PINTEREST_BOARD_ID", "")

    missing = [f for f, v in [("image_url", image_url), ("title", title), ("board_id", board_id)] if not v]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    try:
        token = _get_token()
        result = create_pin(
            board_id=board_id,
            title=title,
            description=description,
            image_url=image_url,
            token=token,
        )
        return jsonify({"success": True, "pin": result}), 201

    except EnvironmentError as e:
        return jsonify({"error": str(e)}), 500
    except ValueError as e:
        return jsonify({"error": str(e)}), 422
    except Exception as e:
        return jsonify({"error": str(e)}), 502


# ---------------------------------------------------------------------------
# CLI entry point — used directly by GitHub Actions
# ---------------------------------------------------------------------------

def cli_post(args):
    """Post a pin straight from CLI args (no HTTP server needed)."""
    token = _get_token()
    board_id = args.board_id or os.environ.get("PINTEREST_BOARD_ID", "")

    if not board_id:
        print("ERROR: --board-id is required (or set PINTEREST_BOARD_ID env var)", file=sys.stderr)
        sys.exit(1)

    print(f"Posting pin to board {board_id}...")
    result = create_pin(
        board_id=board_id,
        title=args.title,
        description=args.description,
        image_url=args.image_url,
        token=token,
    )
    print("Pin created successfully!")
    print(json.dumps(result, indent=2))


def cli_webhook(args):
    """Trigger the /webhook route via Flask test client (no live server)."""
    payload = {
        "board_id":    args.board_id or os.environ.get("PINTEREST_BOARD_ID", ""),
        "title":       args.title,
        "description": args.description,
        "image_url":   args.image_url,
    }

    with app.test_client() as client:
        response = client.post(
            "/webhook",
            data=json.dumps(payload),
            content_type="application/json",
        )
        body = response.get_json()
        if response.status_code == 201:
            print("Webhook succeeded!")
            print(json.dumps(body, indent=2))
        else:
            print(f"Webhook failed ({response.status_code}):", file=sys.stderr)
            print(json.dumps(body, indent=2), file=sys.stderr)
            sys.exit(1)


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pinterest Pin Automation")
    sub = parser.add_subparsers(dest="mode", required=True)

    # Shared pin arguments
    pin_args = argparse.ArgumentParser(add_help=False)
    pin_args.add_argument("--board-id",    default="", help="Pinterest board ID")
    pin_args.add_argument("--title",       required=True, help="Pin title (max 100 chars)")
    pin_args.add_argument("--description", default="", help="Pin description (max 500 chars)")
    pin_args.add_argument("--image-url",   required=True, help="Public image URL")

    sub.add_parser("post",    parents=[pin_args], help="Post pin directly via API")
    sub.add_parser("webhook", parents=[pin_args], help="Post pin via Flask test client")

    validate = sub.add_parser("validate", help="Validate token + board ID")
    validate.add_argument("--board-id", default="", help="Board ID to validate")

    return parser


if __name__ == "__main__":
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.mode == "post":
            cli_post(args)
        elif args.mode == "webhook":
            cli_webhook(args)
        elif args.mode == "validate":
            token = _get_token()
            board_id = args.board_id or os.environ.get("PINTEREST_BOARD_ID", "")
            if board_id:
                board = get_board(board_id, token)
                print(f"Board found: {board.get('name')} ({board_id})")
            else:
                print("Token loaded successfully (no board ID provided to validate)")
    except EnvironmentError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
