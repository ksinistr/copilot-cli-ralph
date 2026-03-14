package main

import (
	"bufio"
	"context"
	"fmt"
	"os"
	"os/exec"
	"strings"
	"time"
)

const (
	planFile         = "plan.md"
	maxReviewRetries = 3
	maxTotalTasks    = 20
	copilotTimeout   = 15 * time.Minute
	codingModel      = "claude-haiku-4.5"
	reviewModel      = "claude-haiku-4.5"
)

func logMsg(msg string) {
	fmt.Printf("[%s] %s\n", time.Now().Format("06-01-02 15:04:05"), msg)
}

func printSection(name string) {
	fmt.Printf("\n--- %s ---\n\n", name)
}

func hasUncompletedTasks() bool {
	data, err := os.ReadFile(planFile)
	if err != nil {
		return false
	}
	return strings.Contains(string(data), "- [ ]")
}

func runCopilot(ctx context.Context, prompt, model string) (string, error) {
	cmd := exec.CommandContext(
		ctx,
		"copilot",
		"--model",
		model,
		"--allow-all-tools",
		"-p",
		prompt,
	)
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		return "", fmt.Errorf("creating stdout pipe: %w", err)
	}
	cmd.Stderr = cmd.Stdout

	if err := cmd.Start(); err != nil {
		return "", fmt.Errorf("starting copilot: %w", err)
	}

	var sb strings.Builder
	scanner := bufio.NewScanner(stdout)

	for scanner.Scan() {
		line := scanner.Text()
		fmt.Println(line)
		sb.WriteString(line)
		sb.WriteByte('\n')
	}

	if err := cmd.Wait(); err != nil {
		if ctx.Err() == context.DeadlineExceeded {
			return sb.String(), fmt.Errorf(
				"copilot timed out after %v", copilotTimeout,
			)
		}
		return sb.String(), fmt.Errorf("copilot exited with error: %w", err)
	}
	return sb.String(), nil
}

func main() {
	if !hasUncompletedTasks() {
		logMsg(fmt.Sprintf("No uncompleted tasks found in %s.", planFile))
		return
	}

	for taskIter := 1; hasUncompletedTasks(); taskIter++ {
		if taskIter > maxTotalTasks {
			logMsg(
				fmt.Sprintf(
					`Max total tasks limit (%d) reached. 
					Exiting to prevent infinite loop.`,
					maxTotalTasks,
				),
			)
			break
		}

		printSection(fmt.Sprintf("copilot task iteration %d", taskIter))

		taskPrompt := fmt.Sprintf(
			`Read %s. Find the FIRST Task section (e.g., '### Task 1:')
			that has uncompleted checkboxes ('- [ ]').

			CRITICAL CONSTRAINT: Complete ONE entire Task section per iteration.

			1. Implement ALL items in that Task section.
			2. Once fully implemented and tested, modify %s to change ALL 
			   the '- [ ]' checkboxes in that section to '- [x]'.
			3. Stage ONLY the specific files you modified and commit them 
			   with a descriptive message.

			Do NOT continue to the next task section. Stop after completing 
			and committing this one.`, planFile, planFile)

		logMsg(fmt.Sprintf("Starting implementation with %s...", codingModel))

		ctx, cancel := context.WithTimeout(context.Background(), copilotTimeout)
		_, err := runCopilot(ctx, taskPrompt, codingModel)
		cancel()

		if err != nil {
			logMsg(fmt.Sprintf("Implementation failed: %s", err))
			return
		}
		logMsg("Implementation finished.")

		for reviewIter := 1; ; reviewIter++ {
			printSection(fmt.Sprintf("copilot review iteration %d", reviewIter))

			reviewPrompt := fmt.Sprintf(
				`Review the code changes made to fulfill the most recently
				completed task in %s.

				To see the full scope of what you are reviewing, 
				you must look at BOTH:
				1. The initial implementation in the most 
				   recent commit (use git show).
				2. Any UNCOMMITTED fixes currently in the workspace 
				   from previous review rounds (use git diff).

				Analyze the combined state of these changes for:
				- Bugs or logic errors
				- Edge cases not handled
				- Missing test coverage

				If you find actionable issues, report them clearly 
				with file and line numbers.
				If the implementation is solid and no issues are found,
				output EXACTLY: "NO ISSUES FOUND".
				Do NOT modify the code yourself. Do NOT create commits.`,
				planFile,
			)

			logMsg(fmt.Sprintf("Starting code review with %s...", reviewModel))
			ctxReview, cancelReview := context.WithTimeout(
				context.Background(),
				copilotTimeout,
			)
			reviewOut, err := runCopilot(ctxReview, reviewPrompt, reviewModel)
			cancelReview()

			if err != nil {
				logMsg(fmt.Sprintf("Code review failed: %s", err))
				return
			}

			if strings.Contains(reviewOut, "NO ISSUES FOUND") {
				logMsg("Review approved the changes. No issues found.")
				break
			}

			printSection(
				fmt.Sprintf(
					"copilot evaluate review findings (retry %d)", reviewIter,
				),
			)

			evalPrompt := fmt.Sprintf(
				`A code reviewer found the following issues with the recent
				implementation:

				%s

				Please evaluate these findings, fix the code accordingly,
				and verify the fixes.
				Once verified, stage ONLY the specific files you modified and
				commit them with a descriptive message indicating you
				addressed review findings.`, reviewOut)

			logMsg("Starting evaluation and fixing with gpt-5-mini...")
			ctxEval, cancelEval := context.WithTimeout(
				context.Background(),
				copilotTimeout,
			)
			_, err = runCopilot(ctxEval, evalPrompt, "gpt-5-mini")
			cancelEval()

			if err != nil {
				logMsg(fmt.Sprintf("Evaluation failed: %s", err))
				return
			}

			if reviewIter >= maxReviewRetries {
				logMsg(
					fmt.Sprintf(
						`Max review retries (%d) reached. 
						Moving on to prevent infinite loop.`,
						maxReviewRetries,
					),
				)
				break
			}
		}
	}

	logMsg("All tasks completed successfully!")
}
