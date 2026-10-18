# Evaluation: CS110_Recitation_7_Conditionals_20261016_203022.json

**Summary:** 32 passed, 0 flagged out of 32
**Uncovered pages** (pages with no cards): 1, 2, 3, 7, 13, 18

## Card 0 — ok
- Q: What does IPO-S stand for in the planning method taught before coding?
- A: Input, Process, Output, Storage.
- Page: 4
## Card 1 — ok
- Q: In IPO-S, which of the four questions is usually the hardest to answer?
- A: Process — the other three (Input, Output, Storage) are usually obvious once you read the problem.
- Page: 4
## Card 2 — ok
- Q: In the recitation's grade-to-letter problem, what letter does a numerical grade of 85 map to?
- A: B. The mapping is A: 90–100, B: 80–89, C: 79 and below.
- Page: 5
## Card 3 — ok
- Q: Is the IPO-S process block written in Python?
- A: No. IPO-S is the plan, written so a human can read it — not Python code yet.
- Page: 5
## Card 4 — ok
- Q: In a flowchart, what shape represents a decision, and how many ways out does it have?
- A: A diamond represents a decision, and it has two ways out (e.g. Yes / No).
- Page: 6
## Card 5 — ok
- Q: How many entry points and exit points should a complete flowchart have overall?
- A: One way in and one way out of the whole chart — every path reaches End.
- Page: 6
## Card 6 — ok
- Q: In Python, which relational operator tests equality, and what is the common mistake?
- A: `==` (two equals signs). Using a single `=` is assignment, not comparison.
- Page: 8
## Card 7 — ok
- Q: When is the boolean operator `and` True?
- A: Only when BOTH sides are true.
- Page: 8
## Card 8 — ok
- Q: When is the boolean operator `or` True?
- A: When EITHER side is true.
- Page: 8
## Card 9 — ok
- Q: Why is `80 <= grade and < 90` invalid in Python?
- A: Each side of `and` must be a complete comparison. The correct form is `80 <= grade and grade < 90`.
- Page: 8
## Card 10 — ok
- Q: In Program 1 (three separate ifs), why does the middle condition need `and`?
- A: B is a range with a floor and a ceiling. Without `grade < 90`, a grade of 95 would also be relabeled B.
- Page: 9
## Card 11 — ok
- Q: How many conditions does Program 1 (three separate ifs) check on each run?
- A: All three — every run checks all conditions, even after the answer is already known.
- Page: 9
## Card 12 — ok
- Q: In Program 2's nested if-else, why does the inner condition drop the `and grade < 90`?
- A: Reaching `else` already tells you `grade < 90`, so `grade >= 80` alone is enough to mean 80–89.
- Page: 10
## Card 13 — ok
- Q: In Program 2, what makes the inner if-else part of the outer `else` block?
- A: Indentation — the inner if-else is indented so it lives inside the outer `else`.
- Page: 10
## Card 14 — ok
- Q: How many comparisons does Program 1 (three separate ifs) make for a grade of 95, vs. Program 2 (nested if-else)?
- A: Program 1 makes 4 comparisons; Program 2 makes 1.
- Page: 11
## Card 15 — ok
- Q: How many comparisons does Program 2 (nested if-else) make for grades 85 and 72?
- A: 2 comparisons for each.
- Page: 11
## Card 16 — ok
- Q: Does the number of comparisons Program 1 makes depend on the input grade?
- A: No — Program 1 always makes 4 comparisons on every run, regardless of the grade.
- Page: 11
## Card 17 — ok
- Q: If `if grade >= 90` is mistyped as `if grade > 90` and the user enters 90, what error does Python raise?
- A: NameError: name 'letterGrade' is not defined. No branch runs, so `letterGrade` is never created.
- Page: 12
## Card 18 — ok
- Q: Which four boundary values are recommended for testing the grade-to-letter conditionals?
- A: 90, 89, 80, and 79 — these catch almost every mistake of that kind.
- Page: 12
## Card 19 — ok
- Q: Why can Program 2 (nested if-else) not suffer from the 'gap' bug that Program 1 can?
- A: An `else` always catches whatever the `if` did not, so no value can fall through unmatched.
- Page: 12
## Card 20 — ok
- Q: In Python, what does `**` mean, and what does `a**2` compute?
- A: `**` means 'to the power of', so `a**2` is a squared.
- Page: 14
## Card 21 — ok
- Q: Why use `float()` rather than `int()` when reading lengths for a Pythagoras calculation?
- A: Lengths can have decimals, so they must be stored as floats, not integers.
- Page: 14
## Card 22 — ok
- Q: What error does Python raise if you call `math.sqrt(...)` without first importing math?
- A: NameError: name 'math' is not defined.
- Page: 14
## Card 23 — ok
- Q: What does `math.ceil(4.2)` return?
- A: 5.
- Page: 15
## Card 24 — ok
- Q: What does `math.floor(4.9)` return?
- A: 4.
- Page: 15
## Card 25 — ok
- Q: What is Python's interactive mode (the `>>>` prompt) and when is it useful?
- A: It runs one line at a time and prints the result immediately — no file, no Run button. Use it to quickly check what a function does.
- Page: 15
## Card 26 — ok
- Q: How does `round` handle ties like 4.5, and what does `round(4.5)` return?
- A: Ties round to the nearest even number, so `round(4.5)` returns 4, not 5.
- Page: 15
## Card 27 — ok
- Q: Which Python built-in ends a program early when input is invalid?
- A: `quit()`.
- Page: 16
## Card 28 — ok
- Q: In the input-guard pattern, why must both the error print and `quit()` be indented under the `if`?
- A: If they are not indented under the `if`, the program quits every time — even on good input.
- Page: 16
## Card 29 — ok
- Q: Before writing any Python, what should you draft first for an assignment?
- A: Write the IPO-S on paper — Input, Process, Output, Storage — before any typing.
- Page: 17
## Card 30 — ok
- Q: Why must `input()` results be cast with `int()` or `float()` before use?
- A: `input()` always returns text, so it must be cast before any arithmetic can be done on it.
- Page: 17
## Card 31 — ok
- Q: Why does the recitation recommend if-else over stacked `if` statements?
- A: Fewer comparisons on each run, and no gap for a value to fall through unmatched.
- Page: 17
