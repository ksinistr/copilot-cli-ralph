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
    Executes the Copilot CLI with specified model, streaming output to console.
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
        # Use Popen to stream output line-by-line
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Merge stderr into stdout
            text=True,
            bufsize=1,  # Line buffered
        )

        output_lines = []
        for line in process.stdout:
            # Print to console in real-time
            print(line, end="", flush=True)
            output_lines.append(line)

        process.wait()
        output = "".join(output_lines)
        return output, process.returncode

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
        Read {PLAN_FILE}. Find the FIRST Task section (e.g., '### Task 1:') that has uncompleted checkboxes ('- [ ]').
        
        CRITICAL CONSTRAINT: Complete ONE entire Task section per iteration.
        
        1. Implement ALL items in that Task section.
        2. Once fully implemented and tested, modify {PLAN_FILE} to change ALL the '- [ ]' checkboxes in that section to '- [x]'.
        3. Stage all your changes (`git add .`) and commit them with a descriptive message (e.g., `git commit -m "feat: implement [task name]"`).
        
        Do NOT continue to the next task section. Stop after completing and committing this one.
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
            Review the code changes made to fulfill the most recently completed task in {PLAN_FILE}.
            
            To see the full scope of what you are reviewing, you must look at BOTH:
            1. The initial implementation in the most recent commit (use `git show`).
            2. Any UNCOMMITTED fixes currently in the workspace from previous review rounds (use `git diff`).
            
            Analyze the combined state of these changes for:
            - Bugs or logic errors
            - Edge cases not handled
            - Missing test coverage
            
            If you find actionable issues, report them clearly with file and line numbers.
            If the implementation is solid and no issues are found, output EXACTLY: "NO ISSUES FOUND".
            Do NOT modify the code yourself. Do NOT create commits.
            """

            log("Starting code review with GPT-5.1-Codex-Mini...")
            review_out, review_code = run_copilot(
                review_prompt, model="gpt-5.1-codex-mini"
            )
            if review_code != 0:
                log(f"Code review failed: {(review_out or 'unknown error').strip()}")
                return

            if "NO ISSUES FOUND" in review_out:
                log("Review approved the changes. No issues found.")

                # Automatically commit any accumulated fixes from the review loop
                status = subprocess.run(
                    ["git", "status", "--porcelain"], capture_output=True, text=True
                )
                if status.stdout.strip():  # If there are uncommitted changes
                    subprocess.run(["git", "add", "."])
                    subprocess.run(
                        [
                            "git",
                            "commit",
                            "-m",
                            f"fix: address review findings for task {task_iteration}",
                        ]
                    )
                    log("Committed accumulated review fixes.")

                break  # Exit the review loop and move to the next task

            print_section(
                f"copilot evaluate review findings (retry {review_iteration})"
            )

            eval_prompt = f"""
            A code reviewer found the following issues with the recent implementation:
            
            {review_out}
            
            Please evaluate these findings, fix the code accordingly, and verify the fixes.
            Do NOT commit your changes. Update the code in place and leave
            the changes UNCOMMITTED in the workspace so the reviewer can check them.
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
