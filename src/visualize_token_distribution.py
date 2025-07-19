import pandas as pd
import matplotlib.pyplot as plt
import argparse
import os
from pathlib import Path


def plot_token_distribution(excel_path, output_path):
    """
    Reads an Excel file and plots the distribution of 'estimated_tokens'.
    """
    try:
        df = pd.read_excel(excel_path)
    except FileNotFoundError:
        print(f"Error: The file '{excel_path}' was not found.")
        return

    if "estimated_tokens" not in df.columns:
        print(f"Error: 'estimated_tokens' column not found in {excel_path}.")
        return

    # Cap values at 50k for the last bucket
    tokens = df["estimated_tokens"].copy()
    tokens[tokens >= 50000] = 50000

    plt.style.use("ggplot")
    plt.figure(figsize=(12, 7))

    # Define custom bins
    max_val = 50000
    bins = list(range(0, max_val + 5000, 5000))

    n, bins, patches = plt.hist(tokens, bins=bins, color="skyblue", edgecolor="black")

    plt.title("Distribution of Estimated Tokens (50k+ grouped)")
    plt.xlabel("Estimated Tokens")
    plt.ylabel("Frequency")

    # Customize x-axis labels
    tick_labels = [f"{int(b/1000)}k" for b in bins[:-1]] + ["50k+"]
    plt.xticks(ticks=bins, labels=tick_labels, rotation=45)

    plt.grid(True, axis="y")
    plt.tight_layout()

    # Ensure output directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    plt.savefig(output_path, bbox_inches="tight", dpi=300)
    print(f"Distribution plot saved to: {output_path}")
    plt.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Plot the distribution of estimated tokens from an Excel file."
    )
    parser.add_argument(
        "--excel_path",
        type=str,
        default="output/context_report.xlsx",
        help="Path to the input Excel file.",
    )
    parser.add_argument(
        "--output_path",
        type=str,
        default="output/token_distribution.png",
        help="Path to save the output plot image.",
    )
    args = parser.parse_args()

    plot_token_distribution(args.excel_path, args.output_path)
