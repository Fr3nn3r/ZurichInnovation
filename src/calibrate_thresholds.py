# This script is a data visualization tool designed to help in the calibration
# of scoring thresholds for a rules-based system. Its primary function is to plot
# the distribution of scores for a specific rule, allowing for a visual analysis
# of how the scores are grouped.
#
# The script's main functionalities are:
# 1.  **Data Loading**: It can load scoring data from one or more JSON files.
#     These files are expected to contain a list of tuples or lists, where each
#     entry includes a rule ID, a score, and a label.
#
# 2.  **Rule-Specific Filtering**: It filters the loaded data to isolate the scores
#     that correspond to a single, specific rule ID provided by the user. It also
#     ensures that only numerical scores are processed, ignoring any non-numerical
#     values (like 'N/A').
#
# 3.  **Histogram Plotting**: The core of the script is its ability to generate
#     and display a histogram. This histogram visually represents the frequency
#     distribution of the scores for the selected rule.
#
# 4.  **Multi-File Comparison**: The script is capable of overlaying histograms
#     from multiple input files onto a single plot. This is particularly useful
#     for comparing score distributions across different datasets or different
#     versions of the scoring algorithm. Each histogram is given a distinct label
#     in the plot's legend, derived from its filename.
#
# 5.  **Command-Line Interface**: It is designed to be run from the command line,
#     requiring the user to provide the `rule_id` they wish to analyze and the
#     paths to one or more score files.
#
# By visualizing how scores are distributed, a user can make more informed
# decisions about where to set thresholds to distinguish between different
# outcomes (e.g., pass/fail, true/false).
#
# Usage:
#   python src/calibrate_thresholds.py <rule_id> <path_to_scores1.json> [<path_to_scores2.json> ...]
#
# Example:
#   python src/calibrate_thresholds.py 17 output/scores.json output/scores_new.json

import json
import numpy as np
import matplotlib.pyplot as plt
import argparse
import os


def plot_score_distributions(rule_id, score_paths):
    """
    Plots the distribution of scores for a specific rule from one or more score files.
    """
    plt.figure(figsize=(10, 6))

    for scores_path in score_paths:
        try:
            with open(scores_path, "r") as f:
                scores_data = json.load(f)
        except FileNotFoundError:
            print(f"Error: Scores file not found at {scores_path}")
            continue

        # Filter scores for the specified rule and exclude 'N/A'
        rule_scores = [
            score
            for r_id, score, label in scores_data
            if r_id == rule_id and isinstance(score, (int, float))
        ]

        if not rule_scores:
            print(f"No numerical scores found for Rule {rule_id} in {scores_path}")
            continue

        # Plot histogram
        label = (
            os.path.basename(scores_path).replace(".json", "").replace("_", " ").title()
        )
        plt.hist(rule_scores, bins=20, alpha=0.7, label=label, density=True)

    plt.title(f"Score Distribution for Rule {rule_id}")
    plt.xlabel("Fuzzy Match Score")
    plt.ylabel("Frequency Density")
    plt.legend()
    plt.grid(True)
    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Plot score distributions for a given rule from multiple files."
    )
    parser.add_argument("rule_id", type=int, help="The rule ID to plot.")
    parser.add_argument(
        "score_paths", nargs="+", help="Path(s) to the scores JSON file(s)."
    )
    args = parser.parse_args()

    plot_score_distributions(args.rule_id, args.score_paths)
