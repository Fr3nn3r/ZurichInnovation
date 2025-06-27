import json
import matplotlib.pyplot as plt
import numpy as np
import os
import argparse


def calibrate_thresholds():
    """
    Loads training scores from a specified file and generates a plot for a
    specific rule ID to help visualize and determine optimal thresholds.
    """
    parser = argparse.ArgumentParser(
        description="Generate score distribution plot for a specific rule."
    )
    parser.add_argument("scores_path", help="Path to the training scores JSON file.")
    parser.add_argument(
        "rule_id", type=int, help="The rule ID to generate the plot for."
    )
    args = parser.parse_args()

    try:
        with open(args.scores_path, "r") as f:
            scores = json.load(f)
    except FileNotFoundError:
        print(f"Error: Could not find '{args.scores_path}'.")
        print("Please ensure the training data has been generated.")
        return

    # Process only the specified rule
    rule_id = args.rule_id
    pos = [score for r, score, label in scores if r == rule_id and label]
    neg = [score for r, score, label in scores if r == rule_id and not label]

    if not pos and not neg:
        print(f"No data found for Rule {rule_id}. Exiting.")
        return

    plt.figure()
    plt.hist([pos, neg], bins=20, label=["good", "bad"], stacked=True, density=True)

    if pos:
        green_threshold = np.percentile(pos, 10)
        yellow_threshold = np.percentile(pos, 50)
        plt.axvline(
            green_threshold,
            color="g",
            linestyle="--",
            label=f"Green (10th %): {green_threshold:.2f}",
        )
        plt.axvline(
            yellow_threshold,
            color="y",
            linestyle=":",
            label=f"Yellow (50th %): {yellow_threshold:.2f}",
        )

    plt.title(f"Score Distribution for Rule {rule_id}")
    plt.xlabel("Fuzzy Match Score")
    plt.ylabel("Density")
    plt.legend()

    print(f"Displaying plot for Rule {rule_id}. Close the plot window to continue.")
    plt.show()


if __name__ == "__main__":
    calibrate_thresholds()
