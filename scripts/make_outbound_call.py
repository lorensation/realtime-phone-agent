from __future__ import annotations

import argparse
from urllib.parse import urljoin

from twilio.rest import Client

from realtime_phone_agents.config import settings


def _looks_like_placeholder_base_url(base_url: str) -> bool:
    normalized = (base_url or "").strip().upper()
    return any(
        marker in normalized
        for marker in ("YOUR-RUNPOD-URL", "<RUNPOD-URL>", "YOUR_PUBLIC_BASE_URL")
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create an outbound phone call using the local Twilio credentials."
    )
    parser.add_argument("--to-number", help="Destination phone number in E.164 format.")
    parser.add_argument(
        "--from-number",
        help="Twilio source phone number in E.164 format. Defaults to TWILIO__FROM_NUMBER.",
    )
    parser.add_argument(
        "--public-base-url",
        help="Public HTTPS base URL of the deployed app. Defaults to SERVER__PUBLIC_BASE_URL.",
    )
    parser.add_argument(
        "--status-callback-url",
        help="Optional Twilio status callback URL. Defaults to TWILIO__STATUS_CALLBACK_URL.",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Fail instead of prompting when required values are missing.",
    )
    return parser


def _prompt_if_missing(value: str | None, prompt: str, *, non_interactive: bool) -> str:
    cleaned = (value or "").strip()
    if cleaned:
        return cleaned
    if non_interactive:
        raise ValueError(prompt)
    return input(f"{prompt}: ").strip()


def _normalize_public_base_url(base_url: str) -> str:
    cleaned = base_url.strip().rstrip("/")
    if not cleaned.startswith(("http://", "https://")):
        raise ValueError("Public base URL must start with http:// or https://")
    if _looks_like_placeholder_base_url(cleaned):
        raise ValueError(
            "Public base URL must be a real deployed URL, not the example placeholder."
        )
    return cleaned


def build_twilio_call_url(public_base_url: str) -> str:
    base_url = _normalize_public_base_url(public_base_url)
    return urljoin(f"{base_url}/", "voice/telephone/incoming")


def main() -> int:
    args = build_parser().parse_args()

    account_sid = _prompt_if_missing(
        settings.twilio.account_sid,
        "TWILIO__ACCOUNT_SID is required",
        non_interactive=args.non_interactive,
    )
    auth_token = _prompt_if_missing(
        settings.twilio.auth_token,
        "TWILIO__AUTH_TOKEN is required",
        non_interactive=args.non_interactive,
    )
    from_number = _prompt_if_missing(
        args.from_number or settings.twilio.from_number,
        "From number (Twilio number) is required",
        non_interactive=args.non_interactive,
    )
    to_number = _prompt_if_missing(
        args.to_number,
        "Destination number is required",
        non_interactive=args.non_interactive,
    )
    public_base_url = _prompt_if_missing(
        args.public_base_url or settings.server.public_base_url,
        "Public deployed app base URL is required",
        non_interactive=args.non_interactive,
    )

    client = Client(account_sid, auth_token)
    call_kwargs = {
        "to": to_number,
        "from_": from_number,
        "url": build_twilio_call_url(public_base_url),
    }
    status_callback_url = (
        args.status_callback_url or settings.twilio.status_callback_url
    ).strip()
    if status_callback_url:
        call_kwargs["status_callback"] = status_callback_url

    call = client.calls.create(**call_kwargs)
    print(f"Outbound call created successfully. SID={call.sid}")
    print(f"Twilio webhook URL: {call_kwargs['url']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
