from apps.nvda_remote.main import main as nvda_remote_main


def main() -> int:
    return nvda_remote_main()


if __name__ == "__main__":
    raise SystemExit(main())
