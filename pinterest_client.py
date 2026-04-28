"""
Pinterest API v5 Client
Handles all communication with the Pinterest API.
"""

import time
import requests


PINTEREST_API_BASE = "https://api.pinterest.com/v5"


def create_pin(board_id: str, title: str, description: str, image_url: str, token: str, max_retries: int = 3) -> dict:
    """
    Post a new Pin to Pinterest with exponential backoff retry logic.

    Args:
        board_id:    Target Pinterest board ID
        title:       Pin title (max 100 chars)
        description: Pin description (max 500 chars)
        image_url:   Publicly accessible image URL
        token:       Pinterest OAuth2 Bearer token
        max_retries: Number of retry attempts on rate-limit (429)

    Returns:
        dict: Pinterest API response with created Pin data

    Raises:
        ValueError: On bad input
        Exception:  On unrecoverable API error
    """
    # --- Input validation ---
    if not board_id or not board_id.strip():
        raise ValueError("board_id is required")
    if not token or not token.strip():
        raise ValueError("Pinterest access token is required")
    if not image_url or not image_url.startswith("http"):
        raise ValueError("image_url must be a valid public URL")
    if len(title) > 100:
        raise ValueError("title must be 100 characters or fewer")
    if len(description) > 500:
        raise ValueError("description must be 500 characters or fewer")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    payload = {
        "board_id": board_id,
        "title": title,
        "description": description,
        "media_source": {
            "source_type": "image_url",
            "url": image_url,
        },
    }

    last_error = None

    for attempt in range(max_retries):
        try:
            response = requests.post(
                f"{PINTEREST_API_BASE}/pins",
                headers=headers,
                json=payload,
                timeout=30,
            )

            if response.status_code == 201:
                return response.json()

            if response.status_code == 429:
                wait = 2 ** attempt  # 1s, 2s, 4s
                print(f"[Rate limited] Attempt {attempt + 1}/{max_retries}. Waiting {wait}s...")
                time.sleep(wait)
                last_error = f"Rate limited after {max_retries} attempts"
                continue

            if response.status_code == 401:
                raise Exception("Unauthorized: check your Pinterest access token")

            if response.status_code == 404:
                raise Exception(f"Board not found: {board_id}")

            # Any other error — raise immediately
            raise Exception(f"Pinterest API error {response.status_code}: {response.text}")

        except requests.exceptions.Timeout:
            last_error = f"Request timed out on attempt {attempt + 1}"
            print(f"[Timeout] {last_error}")
            time.sleep(2 ** attempt)
            continue

        except requests.exceptions.ConnectionError as e:
            last_error = f"Connection error: {e}"
            print(f"[Connection error] {last_error}")
            time.sleep(2 ** attempt)
            continue

    raise Exception(last_error or "Failed to create pin after all retries")


def get_board(board_id: str, token: str) -> dict:
    """
    Fetch a Pinterest board by ID (useful for validation).
    """
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{PINTEREST_API_BASE}/boards/{board_id}",
        headers=headers,
        timeout=15,
    )
    if response.status_code == 200:
        return response.json()
    raise Exception(f"Could not fetch board {board_id}: {response.status_code} {response.text}")
