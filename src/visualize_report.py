# This script is a data visualization tool that generates a visual "heatmap" style
# report from a JSON evaluation file. It is designed to provide a quick, at-a-glance
# overview of the evaluation results for a set of clauses against multiple rules.
#
# The script's main functionalities are:
# 1.  **JSON Data Parsing**: It reads a specified JSON file that is expected to
#     contain clause-level evaluation data. It extracts the names of all the rules
#     and the evaluation results for each clause.
#
# 2.  **Data Structuring for Visualization**: The script processes the raw data into
#     a tabular format suitable for plotting. It creates a matrix where rows
#     represent individual clauses and columns represent the evaluation rules. The
#     cells of this matrix contain the evaluation scores.
#
# 3.  **Color-Coded Heatmap Generation**: Using `matplotlib`, it generates a table
#     (or heatmap) where each cell is colored based on its score value. It uses a
#     predefined color map:
#     - GREEN (#d4edda) for high scores/passing rules.
#     - YELLOW (#fff3cd) for medium scores/warnings.
#     - RED (#f8d7da) for low scores/failing rules.
#     - GRAY (#f0f0f0) for 'N/A' values.
#     This color coding provides an immediate visual summary of the performance of
#     each clause against the rules.
#
# 4.  **Plot Customization**: The generated plot is customized for clarity. The axes
#     are turned off to focus on the table, font sizes are set for readability,
#     and a title is added that includes the name of the source JSON file.
#
# 5.  **Image Export**: Instead of just displaying the plot, the script saves the
#     generated visual report as a PNG image file. The output image is saved in
#     the same directory as the input JSON file and shares the same base name.
#
# 6.  **Command-Line Interface**: The script is intended to be run from the command
#     line, taking a single argument: the path to the JSON evaluation file.
#
# Usage:
#   python src/visualize_report.py /path/to/evaluation_file.json

import json
import matplotlib.pyplot as plt
import numpy as np
import os
import argparse


def create_visual_report(json_path):
    """
    Reads a JSON evaluation file and creates a color-coded visual 'heatmap' report.
    """
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: The file '{json_path}' was not found.")
        return

    # Prepare data for the table
    clause_evals = data.get("clause_level_evaluation", [])
    if not clause_evals:
        print("No clause-level evaluation data found in the JSON file.")
        return

    # Get all unique rule names from the first clause's evaluations
    rules = [evaluation["rule_name"] for evaluation in clause_evals[0]["evaluations"]]
    clauses = [f"Clause {item['clause_number']}" for item in clause_evals]

    cell_text = []
    cell_colors = []
    color_map = {
        "GREEN": "#d4edda",
        "YELLOW": "#fff3cd",
        "RED": "#f8d7da",
        "N/A": "#f0f0f0",
    }

    for clause in clause_evals:
        row_text = []
        row_colors = []
        for rule_name in rules:
            # Find the evaluation for the current rule
            evaluation = next(
                (e for e in clause["evaluations"] if e["rule_name"] == rule_name), None
            )
            score = evaluation["score"] if evaluation else "N/A"
            row_text.append(score)
            row_colors.append(color_map.get(score, "#ffffff"))
        cell_text.append(row_text)
        cell_colors.append(row_colors)

    fig, ax = plt.subplots(figsize=(12, len(clauses) * 0.5 + 1))
    ax.axis("tight")
    ax.axis("off")

    table = ax.table(
        cellText=cell_text,
        cellColours=cell_colors,
        rowLabels=clauses,
        colLabels=rules,
        loc="center",
        cellLoc="center",
    )

    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1.2, 1.2)

    plt.title(f"Visual Report for {os.path.basename(json_path)}", y=0.95)

    # Save the plot
    output_filename = os.path.splitext(json_path)[0] + ".png"
    plt.savefig(output_filename, bbox_inches="tight", dpi=300)
    print(f"Visual report saved to: {output_filename}")
    plt.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate a visual report from an evaluation JSON file."
    )
    parser.add_argument("json_path", help="Path to the evaluation JSON file.")
    args = parser.parse_args()
    create_visual_report(args.json_path)
