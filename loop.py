import os
import subprocess
from datetime import datetime

PLAN_FILE = "plan.md"
MAX_REVIEW_RETRIES = 3


def log(msg):
    """Outputs a timestamped log message."""
    ts = datetime.now().strftime("%y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def print_section(section_name):
    """Outputs a ralphex-style section header."""
    print(f"\n--- {section_name} ---\n", flush=True)


def has_uncompleted_tasks():
    """Checks the plan file for any remaining unchecked boxes."""
    if not os.path.exists(PLAN_FILE):
        return False
    with open(PLAN_FILE, "r") as f:
        return "- [ ]" in f.read()


def run_copilot(prompt, model):
    """
    Executes the Copilot CLI with specified model.
    """
    cmd = [
        "copilot",
        "--model",
        model,
        "--allow-all-tools",
        "-p",
        prompt,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stdout or result.stderr
        return output, result.returncode
    except FileNotFoundError:
        return "Error: copilot command not found", 1


def main():
    if not has_uncompleted_tasks():
        log(f"No uncompleted tasks found in {PLAN_FILE}.")
        return

    task_iteration = 1

    while has_uncompleted_tasks():
        print_section(f"copilot task iteration {task_iteration}")

        task_prompt = f"""
        Read {PLAN_FILE}. Find the FIRST uncompleted task (marked with '- [ ]').
        Implement the functionality required for this task in the codebase.
        Do NOT create any git commits, branches, or worktrees.
        Once you have fully implemented and tested the functionality,
        modify {PLAN_FILE} to change that specific '- [ ]' to '- [x]'.
        """

        log("Starting implementation with gpt-5-mini...")
        impl_out, impl_code = run_copilot(task_prompt, model="gpt-5-mini")
        if impl_code != 0:
            log(f"Implementation failed: {(impl_out or 'unknown error').strip()}")
            return
        log("Implementation finished.")

        review_iteration = 1
        while True:
            print_section(f"copilot review iteration {review_iteration}")

            review_prompt = f"""
            Review the recent code changes made to fulfill the currently active task in {PLAN_FILE}.
            Look for:
            - Bugs or logic errors
            - Edge cases not handled
            - Missing test coverage

            If you find actionable issues, report them clearly with file and line numbers.
            If the implementation is solid and no issues are found,
            output EXACTLY: "NO ISSUES FOUND".
            Do NOT modify the code yourself. Do NOT create commits.
            """

            log("Starting code review with GPT-5.1-Codex-Mini...")
            review_out, review_code = run_copilot(review_prompt, model="gpt-5.1-codex-mini")
            if review_code != 0:
                log(f"Code review failed: {(review_out or 'unknown error').strip()}")
                return

            if "NO ISSUES FOUND" in review_out:
                log("Review approved the changes. No issues found.")
                break

            print_section(
                f"copilot evaluate review findings (retry {review_iteration})"
            )

            eval_prompt = f"""
            A code reviewer found the following issues with the recent implementation:

            {review_out}

            Please evaluate these findings, fix the code accordingly, and verify the fixes.
            Do not commit. Update the code in place.
            """

            log("Starting evaluation and fixing with gpt-5-mini...")
            eval_out, eval_code = run_copilot(eval_prompt, model="gpt-5-mini")
            if eval_code != 0:
                log(f"Evaluation failed: {(eval_out or 'unknown error').strip()}")
                return

            review_iteration += 1
            if review_iteration > MAX_REVIEW_RETRIES:
                log(
                    f"""Max review retries ({MAX_REVIEW_RETRIES}) reached.
                    Moving on to prevent infinite loop."""
                )
                break

        task_iteration += 1

    log("All tasks completed successfully!")


if __name__ == "__main__":
    main()
