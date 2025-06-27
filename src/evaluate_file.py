"""
This script evaluates a given document by splitting it into clauses
and scoring each clause against a predefined set of rules.

Usage:
    python evaluate_file.py <path_to_file>
"""

import json
import sys
import re
from rapidfuzz import process, fuzz
from clause_splitter import split_clauses


def load_rules(rules_path="rules_detailed.json"):
    """Loads the evaluation rules from a JSON file."""
    with open(rules_path, "r", encoding="utf-8") as f:
        return json.load(f)


def evaluate_clause(clause_text, rules):
    """
    Evaluates a single clause against all provided rules.
    This is an enhanced version of the function from clause_screening.py.
    """
    clause_results = []
    # Normalize clause text for better matching
    normalized_text = clause_text.lower()

    for rule in rules:
        rule_type = rule.get("type")
        result = {
            "rule_id": rule["id"],
            "rule_name": rule["name"],
            "score": "N/A",
            "details": f"Rule type '{rule_type}' not implemented.",
        }

        if rule_type == "fuzzy":
            # Combine all patterns for matching
            all_patterns = (
                rule["patterns"].get("green", [])
                + rule["patterns"].get("yellow", [])
                + rule["patterns"].get("red", [])
            )
            if not all_patterns:
                result["details"] = "No patterns defined for fuzzy rule."
                clause_results.append(result)
                continue

            # Find the best match
            match, score, _ = process.extractOne(
                normalized_text, all_patterns, scorer=fuzz.partial_ratio
            )

            # Determine color based on thresholds from rules_detailed.json
            green_threshold = rule["thresholds"].get("green", 90)
            yellow_threshold = rule["thresholds"].get("yellow", 75)

            color = "RED"
            if score >= green_threshold:
                color = "GREEN"
            elif score >= yellow_threshold:
                color = "YELLOW"

            result["score"] = color
            result["details"] = f"Best match: '{match}' with score {score:.2f}"

        clause_results.append(result)

    return clause_results


def main():
    """Main function to orchestrate the file evaluation."""
    if len(sys.argv) < 2:
        print("Usage: python evaluate_file.py <path_to_file>")
        sys.exit(1)

    file_path = sys.argv[1]

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)

    # 1. Split the document into clauses
    clauses = split_clauses(text)

    # 2. Load the evaluation rules
    rules = load_rules()

    # 3. Evaluate each clause and store results
    all_results = []
    for i, clause in enumerate(clauses, 1):
        clause_text = clause["clause"]
        evaluations = evaluate_clause(clause_text, rules)
        all_results.append(
            {"clause_number": i, "clause_text": clause_text, "evaluations": evaluations}
        )

    # 4. Print the results
    for result in all_results:
        print("-" * 80)
        print(f"Clause #{result['clause_number']}:\n'{result['clause_text']}'")
        print("\n--- Evaluation Results ---")
        for eval_result in result["evaluations"]:
            print(
                f"  - Rule: {eval_result['rule_name']} (Score: {eval_result['score']})"
            )
            print(f"    Details: {eval_result['details']}")
        print("-" * 80)


if __name__ == "__main__":
    main()
