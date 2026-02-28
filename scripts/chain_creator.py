#!/usr/bin/env python3
"""
llmauto Chain Creator -- Thin Wrapper.

Die Logik liegt in llmauto.core.chain_creator.
Standalone-Aufruf: python scripts/chain_creator.py [--list]
Integriert:        python -m llmauto chain create
"""
import sys
from pathlib import Path

# Sicherstellen dass llmauto importierbar ist
_root = str(Path(__file__).resolve().parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

from llmauto.core.chain_creator import create_chain, list_templates


def main():
    import argparse
    parser = argparse.ArgumentParser(description="llmauto Chain Creator")
    parser.add_argument("--list", action="store_true", help="Vorlagen anzeigen")
    args = parser.parse_args()

    if args.list:
        list_templates()
    else:
        create_chain()

    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
