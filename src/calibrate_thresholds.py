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
