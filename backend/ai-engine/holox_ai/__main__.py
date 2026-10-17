"""Try the search from the command line:  python -m holox_ai "What is Ohm's law?" --subject Physics"""

import argparse
import sys

from .retriever import get_retriever


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m holox_ai",
        description="Search the course notes the same way the tutor does.",
    )
    parser.add_argument("query", help="the student's question")
    parser.add_argument("--subject", help="limit to one subject folder, e.g. Physics")
    parser.add_argument("-k", type=int, default=4, help="how many results (default 4)")
    parser.add_argument("--notes", help="notes folder (default: ai-engine/notes)")
    args = parser.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # so Malayalam prints on Windows

    hits = get_retriever(args.notes).search(args.query, args.subject, args.k)
    if not hits:
        print("No matching notes found.")
        return 1
    for number, hit in enumerate(hits, 1):
        heading = f" | {hit.chunk.heading}" if hit.chunk.heading else ""
        print(f"{number}. {hit.chunk.source}{heading}  (score {hit.score:.2f})")
        print(hit.chunk.text)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
