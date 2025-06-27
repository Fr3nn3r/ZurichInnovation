"""
This script evaluates a given document by splitting it into clauses
and scoring each clause against a predefined set of rules using a dispatch table.

Usage:
    python src/evaluate_file.py <path_to_file>
"""

import json
import sys
import re
from rapidfuzz import process, fuzz
from clause_splitter import split_clauses
import os
from unidecode import unidecode
import language_tool_python
import argparse


# --- Text Normalization ---
def normalize_text(s):
    """Lowercase and remove diacritics."""
    return unidecode(s.lower())


# --- Rule-specific helper functions ---


def check_fuzzy(clause_text, rule):
    """Handles fuzzy string matching rules."""
    all_patterns = (
        rule["patterns"].get("green", [])
        + rule["patterns"].get("yellow", [])
        + rule["patterns"].get("red", [])
    )
    if not all_patterns:
        return "N/A", "No patterns defined for fuzzy rule."

    match, score, _ = process.extractOne(
        clause_text, all_patterns, scorer=fuzz.partial_ratio, processor=normalize_text
    )

    green_threshold = rule["thresholds"].get("green", 90)
    yellow_threshold = rule["thresholds"].get("yellow", 75)

    color = "RED"
    if score >= green_threshold:
        color = "GREEN"
    elif score >= yellow_threshold:
        color = "YELLOW"

    return color, f"Best match: '{match}' with score {score:.2f}"


def check_numeric(clause_text, rule):
    """Handles various numeric checks based on rule type."""
    rule_type = rule.get("type")
    # Find all integer numbers in the clause
    nums = [int(n) for n in re.findall(r"\d+", clause_text)]

    if rule_type == "numeric_amount":
        if rule["thresholds"].get("amount_presence"):
            return (
                ("GREEN", f"Found potential amount(s): {nums}")
                if nums
                else ("RED", "No amount found.")
            )

    if rule_type == "numeric_years":
        if not nums:
            return "N/A", "No year value found."
        # Use the non-energy threshold by default
        max_years = rule["thresholds"].get("green_max_years", 6)
        if any(n <= max_years for n in nums):
            return "GREEN", f"Found term <= {max_years} years."
        else:
            return "RED", f"Found term > {max_years} years: {nums[0]}"

    if rule_type == "numeric_days":
        min_days = rule["thresholds"].get("green_min_days")
        if nums and any(n >= min_days for n in nums):
            return "GREEN", f"Payment period of >= {min_days} days found."
        # Check for vague terms if numeric check fails
        if "yellow" in rule["patterns"]:
            match, score, _ = process.extractOne(
                clause_text,
                rule["patterns"]["yellow"],
                scorer=fuzz.partial_ratio,
            )
            if score > 80:
                return "YELLOW", f"Vague term found: '{match}'"
        return "RED", f"No payment period of at least {min_days} days found."

    if rule_type == "numeric_percentage":
        # Specifically look for numbers with a '%'
        perc_nums = [int(n) for n in re.findall(r"(\d+)\s*%", clause_text)]
        if not perc_nums:
            return "N/A", "No percentage value found."
        max_perc = rule["thresholds"].get("green_max_percent")
        if any(p <= max_perc for p in perc_nums):
            return "GREEN", f"Found percentage <= {max_perc}%."
        else:
            return "RED", f"Found percentage > {max_perc}%: {perc_nums[0]}%"

    return "N/A", f"Numeric rule type '{rule_type}' logic not fully implemented."


def check_presence_inverse(clause_text, rule):
    """Checks for the presence of undesirable terms."""
    patterns = rule["patterns"].get("red", [])
    if not patterns:
        return "N/A", "No red patterns defined for inverse presence rule."

    match, score, _ = process.extractOne(
        clause_text, patterns, scorer=fuzz.partial_ratio
    )

    if score > 90:  # High threshold to be sure
        return "RED", f"Found forbidden term: '{match}'"
    return "GREEN", "No forbidden terms found."


def check_not_applicable(clause_text, rule):
    """Placeholder for rules that don't apply at the clause level."""
    rule_type = rule.get("type")
    return "N/A", f"Rule type '{rule_type}' is not applicable to a single clause."


def check_placeholder(clause_text, rule):
    """Placeholder for rule types not yet implemented."""
    rule_type = rule.get("type", "unknown")
    return "N/A", f"Rule type '{rule_type}' not implemented."


def check_grammar_count(clause_text, rule):
    """Checks the number of grammar errors in the clause."""
    try:
        # It's more efficient to initialize the tool once, but for simplicity
        # in this dispatch model, we initialize it here.
        # It will cache the server process.
        tool = language_tool_python.LanguageTool(
            "en-US"
        )  # Default, but it can detect others
        matches = tool.check(clause_text)
        error_count = len(matches)

        # Using the thresholds you provided
        if error_count == 0:
            color = "GREEN"
        elif error_count <= 5:
            color = "YELLOW"
        else:
            color = "RED"

        return color, f"Found {error_count} grammar errors."
    except Exception as e:
        return "N/A", f"Grammar check failed: {e}"


def check_not_implemented(clause_text, rule):
    """Placeholder for rule types not yet implemented."""
    rule_type = rule.get("type", "unknown")
    return "N/A", f"Rule type '{rule_type}' not implemented."


def check_cross_clause_data(clause_text):
    """
    Extracts data (amounts, currencies, contract numbers) from a clause
    to be used in the final cross-clause consistency check.
    """
    data = {"amounts": [], "currencies": [], "contract_nos": []}

    # Simple regex for amounts (can be improved)
    # This regex looks for numbers with optional commas/dots
    data["amounts"] = re.findall(r"\b\d{1,3}(?:[,.]\d{3})*(?:\.\d+)?\b", clause_text)

    # Regex for common currency symbols or codes
    data["currencies"] = re.findall(r"(\b[A-Z]{3}\b|[\$€£¥])", clause_text)

    # Example regex for a contract number (e.g., "PR+123456789")
    data["contract_nos"] = re.findall(r"\b(PR\+\d{9})\b", clause_text)

    return data


def perform_final_cross_clause_check(all_clause_data):
    """
    Analyzes the collected data from all clauses for inconsistencies.
    """
    results = []

    # Aggregate all found items
    all_amounts = [item for clause in all_clause_data for item in clause["amounts"]]
    all_currencies = [
        item for clause in all_clause_data for item in clause["currencies"]
    ]
    all_contract_nos = [
        item for clause in all_clause_data for item in clause["contract_nos"]
    ]

    # Check for contradictions
    unique_amounts = set(all_amounts)
    unique_currencies = set(all_currencies)
    unique_contract_nos = set(all_contract_nos)

    color = "GREEN"
    evidence = "All values are consistent across clauses."

    if len(unique_amounts) > 1:
        color = "RED"
        evidence = f"Inconsistent amounts found: {list(unique_amounts)}"

    if len(unique_currencies) > 1:
        color = "RED"
        evidence += f" Inconsistent currencies found: {list(unique_currencies)}"

    if len(unique_contract_nos) > 1:
        color = "RED"
        evidence += f" Inconsistent contract numbers found: {list(unique_contract_nos)}"

    results.append(
        {"rule_name": "Cross-Clause Consistency", "color": color, "evidence": evidence}
    )

    return results


# --- Dispatch Table ---

DISPATCH = {
    "fuzzy": check_fuzzy,
    "numeric_years": check_numeric,
    "numeric_days": check_numeric,
    "numeric_amount": check_numeric,
    "numeric_percentage": check_numeric,
    "presence_inverse": check_presence_inverse,
    "format": check_not_implemented,
    "ocr_confidence": check_not_implemented,
    "grammar_count": check_grammar_count,
}


def load_rules(rules_path="rules_detailed.json"):
    """Loads the evaluation rules from a JSON file."""
    with open(rules_path, "r", encoding="utf-8") as f:
        return json.load(f)


def evaluate_clause(clause_text, rules):
    """
    Evaluates a single clause against all applicable rules from the dispatch table.
    """
    clause_results = []
    for rule in rules:
        rule_type = rule.get("type")
        # The dispatch table now correctly handles all implemented or placeholder functions
        if rule_type in DISPATCH:
            handler = DISPATCH[rule_type]
            color, evidence = handler(clause_text, rule)
            clause_results.append(
                {
                    "rule_id": rule["id"],
                    "rule_name": rule["name"],
                    "score": color,
                    "details": evidence,
                }
            )
    return clause_results


def generate_training_data(file_path, rules, output_path):
    """
    Generates a list of [rule_id, score, label] for calibrating fuzzy thresholds.
    Appends to the output file if it already exists.
    """
    print(f"Processing {os.path.basename(file_path)} for training data...")

    # Load existing scores if the file exists
    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            all_scores = json.load(f)
    else:
        all_scores = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        sys.exit(1)

    clauses = split_clauses(text)

    for clause in clauses:
        clause_text = clause["clause"]
        for rule in rules:
            if rule.get("type") == "fuzzy":
                patterns = rule.get("patterns", {})

                # Green/Yellow patterns are considered "good" matches (label=True)
                for pattern in patterns.get("green", []) + patterns.get("yellow", []):
                    score = fuzz.partial_ratio(
                        clause_text, pattern, processor=normalize_text
                    )
                    all_scores.append([rule["id"], score, True])

                # Red patterns are "bad" matches (label=False)
                for pattern in patterns.get("red", []):
                    score = fuzz.partial_ratio(
                        clause_text, pattern, processor=normalize_text
                    )
                    all_scores.append([rule["id"], score, False])

    # Save the combined results
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_scores, f, indent=2)
    print(f"Training data updated in '{output_path}'")


def run_evaluation(file_path, rules, output_path):
    """
    Runs the standard evaluation and saves the report.
    """
    # This function will contain the original logic from main()
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        sys.exit(1)

    clauses = split_clauses(text)
    clause_level_results = []
    cross_clause_data = []

    for i, clause in enumerate(clauses, 1):
        clause_text = clause["clause"]
        evaluations = evaluate_clause(clause_text, rules)
        clause_level_results.append(
            {"clause_number": i, "clause_text": clause_text, "evaluations": evaluations}
        )
        cross_clause_data.append(check_cross_clause_data(clause_text))

    document_level_results = perform_final_cross_clause_check(cross_clause_data)

    final_output = {
        "clause_level_evaluation": clause_level_results,
        "document_level_evaluation": document_level_results,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=2, ensure_ascii=False)
    print(f"Evaluation complete. Results saved to '{output_path}'")


def main():
    """Main function to orchestrate file processing."""
    parser = argparse.ArgumentParser(
        description="Evaluate a document against a set of rules."
    )
    parser.add_argument("file_path", help="Path to the text file to evaluate.")
    parser.add_argument(
        "--generate-training-data",
        action="store_true",
        help="Generate training data for threshold calibration.",
    )
    parser.add_argument("--output-file", help="Optional path for the output file.")

    args = parser.parse_args()

    # Common setup
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    script_dir = os.path.dirname(__file__)
    rules_path = os.path.join(script_dir, "../rules_detailed.json")
    rules = load_rules(rules_path)

    if args.generate_training_data:
        output_path = (
            args.output_file
            if args.output_file
            else os.path.join(output_dir, "training_scores.json")
        )
        generate_training_data(args.file_path, rules, output_path)
    else:
        output_path = (
            args.output_file
            if args.output_file
            else os.path.join(
                output_dir,
                os.path.splitext(os.path.basename(args.file_path))[0]
                + "_evaluation.json",
            )
        )
        run_evaluation(args.file_path, rules, output_path)


if __name__ == "__main__":
    main()
