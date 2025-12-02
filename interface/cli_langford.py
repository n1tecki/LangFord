# cli_langford.py

from core.langford_service import init_langford, run_langford


def show(text: str) -> str:
    """
    Normalize escaped newlines so multi-line answers look normal in the terminal.
    """
    s = str(text)
    s = s.replace("\\r\\n", "\n")
    s = s.replace("\\n", "\n")
    s = s.replace("\\r", "\n")
    s = s.replace("\\\\n", "\n")
    return s


def repl() -> None:
    """
    Minimal interactive loop for talking to Langford on the command line.
    """
    init_langford()

    print("Langford CLI ready.")
    print("Type 'brief' for your executive brief, 'exit' to quit.\n")

    while True:
        try:
            user_msg = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nBye.")
            break

        if not user_msg:
            continue

        if user_msg.lower() in {"exit", "quit", "q"}:
            print("Bye.")
            break

        # Everything else is passed straight to Langford
        try:
            result = run_langford(user_msg)
        except Exception as exc:  # noqa: BLE001
            print(f"Assistant: [error in backend: {exc}]")
            continue

        print(f"Assistant: {show(result)}\n")


if __name__ == "__main__":
    repl()
