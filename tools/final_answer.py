from smolagents import tool


@tool
def final_answer(answer: str) -> str:
    """
    Final response to Mr. Mariusz.

    This tool must be called exactly once at the end of a run, with the entire
    message that should be shown to him.
    It should include all the asnwer details in a nicely structured way.

    Args:
        answer: The full, formatted reply that will be returned to Mr. Mariusz.

    Returns:
        The same text passed in `answer`.
    """
    return answer
