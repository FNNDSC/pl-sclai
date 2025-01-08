import subprocess


def repl_start() -> None:
    """
    Start the REPL loop, presenting the user with a prompt, accepting input,
    and simulating responses from an LLM by using the `fortune` command.
    Handles <Ctrl+C> gracefully.
    """
    print("Welcome to the SCLAI REPL. Type 'exit' to quit.\n")
    try:
        while True:
            # Present the input prompt
            user_input: str = input("$> ").strip()

            # Exit the REPL on 'exit'
            if 'exit' in user_input.lower(): 
                print("Exiting REPL. Goodbye!")
                break

            # Simulate the LLM response using `fortune`
            response: str = fortune_get()
            print(f"LLM: {response}")
    except KeyboardInterrupt:
        print("\nREPL interrupted. Exiting gracefully. Goodbye!")


def fortune_get() -> str:
    """
    Simulate an LLM response using the `fortune` command.

    Returns:
        str: Output of the `fortune` command or a fallback message if unavailable.
    """
    try:
        result: str = subprocess.check_output(["fortune"], text=True).strip()
        return result
    except FileNotFoundError:
        return "Fortune command not found. Please install 'fortune' for simulated responses."

