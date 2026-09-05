import os
import sys

from v2s import i18n


def ensure_standard_streams() -> None:
    """Give windowed builds a writeable sink for stdout and stderr."""
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")


def main() -> None:
    ensure_standard_streams()
    args = sys.argv[1:]
    if "--lang" in args:
        index = args.index("--lang")
        if index + 1 < len(args):
            i18n.set_language(args[index + 1])

    from v2s.gui import main as gui_main

    gui_main()


if __name__ == "__main__":
    main()
