# This script implements a document screening process designed to evaluate clauses
# from a PDF document against a predefined set of rules. It extracts text from a
# PDF, splits it into individual clauses, and then evaluates each clause to assign
# it a color-coded status (GREEN, YELLOW, or RED).
#
# The script's main functionalities are:
# 1.  **Rule Loading**: It loads a set of evaluation rules from an external JSON
#     file (`rules_detailed.json`). These rules define the patterns, thresholds,
#     and logic for evaluating the text.
#
# 2.  **PDF Text Extraction**: It uses the `pdfplumber` library to open a PDF file
#     and extract the raw text content from all of its pages.
#
# 3.  **Clause Splitting**: It employs a naive but effective regular expression to
#     split the full text of the document into individual clauses. The splitting
#     is based on patterns that typically denote the start of a new clause, such
#     as section symbols (§), numbers, or capitalized headings.
#
# 4.  **Multi-Type Rule Evaluation**: It evaluates each clause against the loaded
#     rules in a priority order. The script supports different types of rules:
#     - **Fuzzy Matching**: Uses the `rapidfuzz` library to perform partial ratio
#       string matching against a list of "green," "yellow," and "red" patterns.
#       The clause is assigned a color based on which threshold the match score
#       exceeds.
#     - **Numeric Rules**: Extracts numerical values from the clause and checks
#       if they fall within a specified maximum value.
#     The evaluation for a clause stops at the first rule that does not result
#     in a "GREEN" status.
#
# 5.  **OCR Confidence (Helper)**: Although not used in the main pipeline, a helper
#     function `ocr_confidence` is included, which can calculate the average
#     confidence score of text extracted via Tesseract's OCR data output.
#
# 6.  **Results Aggregation**: It compiles the evaluation results for each clause
#     into a structured list of dictionaries. Each dictionary contains the clause
#     ID, a truncated version of the text, the ID of the rule that was triggered,
#     the final color status, and the evidence for that status.
#
# 7.  **Command-Line Execution**: The script is designed to be run from the command
#     line, taking the path to a single PDF file as an argument.
#
# Usage:
#   python src/clause_screening.py /path/to/document.pdf

import re, json, pdfplumber, pytesseract, numpy as np
from rapidfuzz import process, fuzz
from langdetect import detect
import pandas as pd

# --- load rules ---
rules = json.load(open("rules_detailed.json"))


def get_rules():
    return rules


# --- helper funcs ---
def ocr_confidence(image):
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    conf = [int(c) for c in data["conf"] if c.isdigit()]
    return sum(conf) / len(conf) if conf else 0


def fuzzy_colour(text, rule):
    match, score, _ = process.extractOne(
        text,
        rule["patterns"]["green"]
        + rule["patterns"]["yellow"]
        + rule["patterns"]["red"],
        scorer=fuzz.partial_ratio,
    )
    if score >= rule["thresholds"]["green"]:
        return "GREEN", f"matched '{match}' ({score})"
    if score >= rule["thresholds"]["yellow"]:
        return "YELLOW", f"matched '{match}' ({score})"
    return "RED", f"best score {score}"


def evaluate_clause(clause_text):
    for rule in rules:  # priority order inside JSON
        if rule["type"] == "fuzzy":
            colour, ev = fuzzy_colour(clause_text.lower(), rule)
        elif rule["type"] == "numeric":
            nums = [int(x) for x in re.findall(r"\d+", clause_text)]
            colour = (
                "RED" if not nums else ("GREEN" if nums[0] <= rule["max"] else "YELLOW")
            )
            ev = f"found {nums}"
        # …add handlers for other types…
        if colour != "GREEN":  # stop at first non-green
            return colour, rule["id"], ev
    return "GREEN", None, "all checks passed"


def split_into_clauses(text):
    return re.split(r"\n\s*(?:§?\d+\S*\.?|[A-Z ]{4,})\s*\n", text)[1:]  # naive split


def screen_clauses(clauses, rules):
    results = []
    for idx, text in enumerate(clauses, 1):
        colour, rule_id, ev = evaluate_clause(text)
        results.append(
            {
                "clause_id": idx,
                "text": text[:120],  # truncate
                "rule_id": rule_id,
                "colour": colour,
                "evidence": ev,
            }
        )
    return results


# --- pipeline entry ---
def screen_pdf(path):
    with pdfplumber.open(path) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text()

    clauses = split_into_clauses(text)

    # screen all clauses
    results = screen_clauses(clauses, rules)
    print(results)


if __name__ == "__main__":
    import sys

    screen_pdf(sys.argv[1])
