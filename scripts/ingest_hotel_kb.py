from __future__ import annotations

import argparse
import json

from realtime_phone_agents.config import settings
from realtime_phone_agents.infrastructure.superlinked.service import (
    get_knowledge_search_service,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest a hotel KB bundle into Superlinked/Qdrant.")
    parser.add_argument(
        "--bundle-path",
        default=settings.knowledge_base.default_bundle_path,
        help="Path to the versioned hotel KB bundle directory.",
    )
    parser.add_argument(
        "--in-memory",
        action="store_true",
        help="Use the in-memory Superlinked executor instead of Qdrant.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    service = get_knowledge_search_service(force_in_memory=args.in_memory)
    result = service.ingest_knowledge_bundle(args.bundle_path)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
