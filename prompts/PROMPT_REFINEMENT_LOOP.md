# Prompt Refinement Loop (Professional)

Use this loop to repeatedly improve execution quality.

## Step 1: Define Scorecard
- Instruction adherence rate
- Task success rate
- Tool-call correctness rate
- Regression rate
- Time-to-completion / token cost

## Step 2: Run Baseline
- Execute a fixed set of representative backend tasks (10-30).
- Collect failures by category.

## Step 3: Diagnose Failure Modes
- Ambiguous instruction
- Missing context
- Tool misuse
- Weak validation/testing
- Output contract drift

## Step 4: Apply One Prompt Change Batch
- Change one coherent section at a time (e.g., tool-use rules).
- Re-run same task set for apples-to-apples comparison.

## Step 5: Promote or Roll Back
- Promote only if metrics improve and regressions stay below threshold.
- Otherwise roll back and try a different refinement.

## Suggested Promotion Thresholds
- Adherence >= 95%
- Task success >= 90%
- Tool-call correctness >= 98%
- Regression <= 3%
