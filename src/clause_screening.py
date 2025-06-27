import re, json, pdfplumber, pytesseract, numpy as np
from rapidfuzz import process, fuzz
from langdetect import detect
import pandas as pd

# --- load rules ---
rules = json.load(open("rules.json"))


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


# --- pipeline entry ---
def screen_pdf(path):
    results = []
    with pdfplumber.open(path) as pdf:
        raw_text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    lang = detect(raw_text)
    clauses = re.split(r"\n\s*(?:§?\d+\S*\.?|[A-Z ]{4,})\s*\n", raw_text)[
        1:
    ]  # naive split

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
    json.dump(results, open(f"{path}.json", "w"), indent=2, ensure_ascii=False)


if __name__ == "__main__":
    import sys

    screen_pdf(sys.argv[1])
