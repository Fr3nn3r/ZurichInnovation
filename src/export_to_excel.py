import pandas as pd
import json
import argparse
import os
from openpyxl import Workbook
from openpyxl.styles import PatternFill
from openpyxl.utils.dataframe import dataframe_to_rows


def style_cells(val):
    if isinstance(val, (int, float)):
        if val > 90:
            return "background-color: #C6EFCE"  # Green for > 90
        elif val > 70:
            return "background-color: #FFEB9C"  # Yellow for > 70
    return ""


def export_to_excel(json_paths, output_path="output/combined_report.xlsx"):
    """
    Reads a list of JSON evaluation files, combines them into a single DataFrame,
    adds a 'Filename' column, and exports to a styled Excel file.
    """
    all_data = []

    for json_path in json_paths:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Extract original filename from the json path
        base_filename = os.path.basename(json_path)
        original_filename = base_filename.replace("_evaluation.json", "")

        # Process clause evaluations
        for clause in data.get("clause_level_evaluation", []):
            row = {"Clause Text": clause["clause_text"], "Filename": original_filename}
            for score in clause["evaluations"]:
                row[score["rule_name"]] = score["score"]
            all_data.append(row)

    if not all_data:
        print("No data to export.")
        return

    df = pd.DataFrame(all_data)

    # Reorder columns to have Filename first
    rule_names = [col for col in df.columns if col not in ["Clause Text", "Filename"]]
    new_column_order = ["Filename", "Clause Text"] + sorted(rule_names)
    df = df[new_column_order]

    # Fill NaN values for cleaner output
    df.fillna("-", inplace=True)

    # Create workbook and sheet
    wb = Workbook()
    ws = wb.active
    ws.title = "Clause Evaluation Report"

    # Add headers
    for r_idx, row in enumerate(dataframe_to_rows(df, index=False, header=True), 1):
        ws.append(row)

    # Apply styling
    green_fill = PatternFill(
        start_color="C6EFCE", end_color="C6EFCE", fill_type="solid"
    )
    yellow_fill = PatternFill(
        start_color="FFEB9C", end_color="FFEB9C", fill_type="solid"
    )

    header_row = [cell.value for cell in ws[1]]
    rule_indices = {rule: i for i, rule in enumerate(header_row) if rule in rule_names}

    for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
        for rule, col_idx in rule_indices.items():
            cell = row[col_idx]
            if isinstance(cell.value, (int, float)):
                if cell.value > 90:
                    cell.fill = green_fill
                elif cell.value > 70:
                    cell.fill = yellow_fill

    # Auto-adjust column widths
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = max_length + 2
        ws.column_dimensions[column].width = adjusted_width

    # Save the workbook
    wb.save(output_path)
    print(f"Combined Excel report saved to: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Export evaluation JSON to a styled Excel file."
    )
    parser.add_argument(
        "json_paths", nargs="+", help="One or more paths to evaluation JSON files."
    )
    args = parser.parse_args()

    export_to_excel(args.json_paths)
