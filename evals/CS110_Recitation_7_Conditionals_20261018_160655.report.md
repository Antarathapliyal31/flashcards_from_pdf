# Evaluation: CS110_Recitation_7_Conditionals_20261018_160655.json

**Summary:** 22 passed, 1 flagged out of 23
**Uncovered pages** (pages with no cards): 1, 2, 3, 5, 7, 13, 17, 18

## Card 0 — ok
- Q: What are the four components of IPO-S planning?
- A: Input (what the program needs from the user), Process (how input turns into output), Output (what the program gives back), Storage (variables needed).
- Page: 4
## Card 1 — ok
- Q: What does the relational operator == mean in Python?
- A: Equal to. It uses two equal signs to distinguish it from the assignment operator =.
- Page: 8
## Card 2 — ok
- Q: What does the relational operator != mean?
- A: Not equal to.
- Page: 8
## Card 3 — ok
- Q: When using 'and' in a condition, what must be true for the overall condition to be true?
- A: Both sides must be true.
- Page: 8
## Card 4 — ok
- Q: When using 'or' in a condition, what must be true for the overall condition to be true?
- A: Either side (or both) must be true.
- Page: 8
## Card 5 — ok
- Q: What is a common mistake when chaining comparisons with 'and'?
- A: Each side of 'and' must be a complete comparison. '80 <= grade and < 90' does not work; use '80 <= grade and grade < 90'.
- Page: 8
## Card 6 — ok
- Q: In Program 1 (three separate ifs), why is the middle condition '80 <= grade and grade < 90' necessary?
- A: Without the second part, a grade of 95 would be incorrectly relabeled as B because it satisfies grade >= 80.
- Page: 9
## Card 7 — ok
- Q: How many comparisons does Program 1 (three separate ifs) make for every single run?
- A: Four comparisons, regardless of the grade entered.
- Page: 11
## Card 8 — ok
- Q: In nested if-else (Program 2), why can you drop the 'and' from the middle condition?
- A: Reaching the else already tells you grade < 90, so 'grade >= 80' alone is sufficient to mean 80–89.
- Page: 10
## Card 9 — ok
- Q: How many comparisons does Program 2 (nested if-else) make for a grade of 95?
- A: One comparison.
- Page: 11
## Card 10 — ok
- Q: How many comparisons does Program 2 (nested if-else) make for a grade of 85 or 72?
- A: Two comparisons.
- Page: 11
## Card 11 — ok
- Q: What error occurs if you use 'grade > 90' instead of 'grade >= 90' and enter 90?
- A: NameError: name 'letterGrade' is not defined, because 90 falls through all conditions.
- Page: 12
## Card 12 — ok
- Q: What four boundary values should you test to catch gaps in grade conditions?
- A: 90, 89, 80, and 79. These values catch almost every mistake at condition boundaries.
- Page: 12
## Card 13 — ok
- Q: What operator in Python means 'to the power of'?
- A: ** (double asterisk). For example, a**2 means a squared.
- Page: 14
## Card 14 — ok
- Q: What must you type before using math.sqrt, math.ceil, or math.floor?
- A: import math at the top of your program.
- Page: 14
## Card 15 — ok
- Q: What does math.ceil do?
- A: Always rounds up to the nearest integer, whatever the decimal value is.
- Page: 15
## Card 16 — ok
- Q: What does math.floor do?
- A: Always rounds down to the nearest integer, whatever the decimal value is.
- Page: 15
## Card 17 — ok
- Q: How does Python's round function handle ties like 4.5?
- A: It rounds to the even number, so round(4.5) is 4, not 5.
- Page: 15
## Card 18 — ok
- Q: What is the purpose of a guard check on input?
- A: To check that input makes sense (e.g., positive values, non-zero divisors) before using it in calculations.
- Page: 16
## Card 19 — FLAGGED
- Q: If you use 'quit()' to stop a program early, how should you indent the lines under it?
- A: Both quit() and any other lines must be indented under the if, or the program quits every time, even on good input.
- Page: 16
- LLM flags: hallucination, citation — The source says 'Both lines must be indented' but does not explicitly require quit() itself to be indented under if; it warns against improper indentation of the lines after quit().
## Card 20 — ok
- Q: What shape in a flowchart represents a decision?
- A: A diamond with two ways out (Yes and No paths).
- Page: 6
## Card 21 — ok
- Q: What shape in a flowchart represents input or output?
- A: A parallelogram.
- Page: 6
## Card 22 — ok
- Q: What shape in a flowchart represents the start or end of a program?
- A: An oval or rounded rectangle.
- Page: 6
