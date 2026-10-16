#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
經濟學實證資料自動分析與敘述統計生成工具 (Econ Data Profiler)
Generates Table 1 (Markdown & LaTeX), checks panel structure, and produces
descriptive binned means visualizations (ASCII + SVG).
"""

import os
import sys
import argparse
import difflib
import re
from html import escape as xml_escape
from typing import Any, Dict, List, Optional
import pandas as pd
import numpy as np


def validate_columns(df: pd.DataFrame, requested: Dict[str, Optional[str]]) -> None:
    """Fail fast when a user-supplied column name does not exist."""
    missing = []
    for role, column in requested.items():
        if column and column not in df.columns:
            suggestions = difflib.get_close_matches(column, df.columns.tolist(), n=3, cutoff=0.4)
            hint = f"; closest: {', '.join(suggestions)}" if suggestions else ""
            missing.append(f"{role}='{column}'{hint}")
    if missing:
        raise ValueError("Unknown column(s): " + "; ".join(missing))

def dataframe_to_markdown(df: pd.DataFrame) -> str:
    """
    Dependency-free Markdown table generator (replaces pandas.to_markdown to avoid tabulate dependency).
    """
    headers = [str(c) for c in df.columns]
    rows = [[str(val) for val in row] for row in df.values]
    col_widths = [max(len(h), max((len(r[i]) for r in rows), default=0)) for i, h in enumerate(headers)]
    
    header_line = "| " + " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers)) + " |"
    sep_line = "| " + " | ".join("-" * w for w in col_widths) + " |"
    data_lines = ["| " + " | ".join(r[i].ljust(col_widths[i]) for i in range(len(headers))) + " |" for r in rows]
    return "\n".join([header_line, sep_line] + data_lines)

def compute_summary_table(df: pd.DataFrame, vars_subset: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Computes standard economics Table 1 summary statistics:
    Variable, N, Mean, Std Dev, Min, P25, P50 (Median), P75, Max, Missing %
    """
    if vars_subset:
        cols = [c for c in vars_subset if c in df.columns]
    else:
        # Select numeric columns by default
        cols = df.select_dtypes(include=[np.number]).columns.tolist()

    records = []
    total_len = len(df)

    for col in cols:
        series = df[col].dropna()
        n_obs = len(series)
        missing_cnt = total_len - n_obs
        missing_pct = (missing_cnt / total_len * 100) if total_len > 0 else 0.0

        if n_obs == 0:
            records.append({
                "Variable": col,
                "Obs": 0,
                "Mean": np.nan,
                "Std. Dev.": np.nan,
                "Min": np.nan,
                "P25": np.nan,
                "Median": np.nan,
                "P75": np.nan,
                "Max": np.nan,
                "Missing %": f"{missing_pct:.1f}%"
            })
            continue

        records.append({
            "Variable": col,
            "Obs": n_obs,
            "Mean": round(float(series.mean()), 4),
            "Std. Dev.": round(float(series.std()), 4) if n_obs > 1 else 0.0,
            "Min": round(float(series.min()), 4),
            "P25": round(float(series.quantile(0.25)), 4),
            "Median": round(float(series.median()), 4),
            "P75": round(float(series.quantile(0.75)), 4),
            "Max": round(float(series.max()), 4),
            "Missing %": f"{missing_pct:.1f}%"
        })

    return pd.DataFrame(records)

def check_panel_structure(df: pd.DataFrame, id_col: Optional[str] = None, time_col: Optional[str] = None) -> Dict[str, Any]:
    """
    Audits panel balance and structure.
    """
    res = {
        "total_rows": len(df),
        "is_panel": False,
        "id_col": id_col,
        "time_col": time_col,
        "num_units": None,
        "num_periods": None,
        "is_balanced": False,
        "duplicate_key_rows": 0,
        "missing_key_rows": 0,
        "min_periods_per_unit": None,
        "max_periods_per_unit": None,
        "notes": ""
    }

    if not id_col or not time_col:
        # Heuristic detection
        def matches(column: str, keywords: set[str]) -> bool:
            tokens = set(re.split(r"[^a-z0-9]+", str(column).casefold()))
            return bool(tokens & keywords)

        candidates_id = [c for c in df.columns if matches(c, {"id", "fips", "county", "state", "firm", "unit"})]
        candidates_time = [c for c in df.columns if matches(c, {"year", "time", "date", "month", "quarter", "period"})]
        if (id_col or candidates_id) and (time_col or candidates_time):
            id_col = id_col or candidates_id[0]
            time_col = time_col or candidates_time[0]
            res["id_col"] = id_col
            res["time_col"] = time_col
            res["notes"] = f"Heuristically detected panel: ID={id_col}, Time={time_col}"

    if id_col and time_col and id_col in df.columns and time_col in df.columns:
        res["is_panel"] = True
        keys = df[[id_col, time_col]]
        missing_key_rows = int(keys.isna().any(axis=1).sum())
        valid = df.loc[~keys.isna().any(axis=1)]
        duplicate_key_rows = int(valid.duplicated([id_col, time_col], keep=False).sum())
        units = valid[id_col].nunique()
        periods = valid[time_col].nunique()
        res["num_units"] = units
        res["num_periods"] = periods
        res["duplicate_key_rows"] = duplicate_key_rows
        res["missing_key_rows"] = missing_key_rows
        
        counts = valid.groupby(id_col)[time_col].nunique()
        if len(counts):
            res["min_periods_per_unit"] = int(counts.min())
            res["max_periods_per_unit"] = int(counts.max())
        is_balanced = (
            missing_key_rows == 0
            and duplicate_key_rows == 0
            and len(counts) > 0
            and (counts == periods).all()
            and len(valid) == units * periods
        )
        res["is_balanced"] = bool(is_balanced)

    return res

def generate_ascii_binscatter(x_bins: List[float], y_bins: List[float], x_label: str, y_label: str, height: int = 12, width: int = 50) -> str:
    """
    Renders a compact, dependency-free ASCII binned scatter plot.
    """
    if not x_bins or not y_bins or len(x_bins) != len(y_bins):
        return "Insufficient data for ASCII plot."

    min_x, max_x = min(x_bins), max(x_bins)
    min_y, max_y = min(y_bins), max(y_bins)

    if min_x == max_x: max_x += 1e-5
    if min_y == max_y: max_y += 1e-5

    grid = [[" " for _ in range(width)] for _ in range(height)]

    for x, y in zip(x_bins, y_bins):
        col = int((x - min_x) / (max_x - min_x) * (width - 1))
        row = int((y - min_y) / (max_y - min_y) * (height - 1))
        row = (height - 1) - row
        grid[row][col] = "●"

    lines = []
    lines.append(f"  ▲ {y_label} (Max: {max_y:.3g})")
    for r in range(height):
        y_val = max_y - r * (max_y - min_y) / (height - 1)
        prefix = f"{y_val:8.2f} │ " if (r == 0 or r == height - 1 or r == height // 2) else "         │ "
        lines.append(prefix + "".join(grid[r]))
    lines.append("         └" + "─" * width + f"▶ {x_label} (Max: {max_x:.3g})")
    lines.append(f"         {min_x:<8.2f}" + " " * (width - 16) + f"{max_x:>8.2f}")
    return "\n".join(lines)

def generate_svg_binscatter(x_bins: List[float], y_bins: List[float], x_label: str, y_label: str, filepath: str):
    """
    Generates a standalone SVG of descriptive binned means.
    """
    if not x_bins or not y_bins or len(x_bins) != len(y_bins):
        raise ValueError("At least one paired bin is required")

    x_label_xml = xml_escape(str(x_label))
    y_label_xml = xml_escape(str(y_label))
    width, height = 700, 450
    margin_l, margin_r, margin_t, margin_b = 80, 40, 50, 60
    plot_w = width - margin_l - margin_r
    plot_h = height - margin_t - margin_b

    min_x, max_x = min(x_bins), max(x_bins)
    min_y, max_y = min(y_bins), max(y_bins)
    dx = (max_x - min_x) * 0.05 or 1.0
    dy = (max_y - min_y) * 0.05 or 1.0
    min_x -= dx; max_x += dx
    min_y -= dy; max_y += dy

    def scale_x(v): return margin_l + (v - min_x) / (max_x - min_x) * plot_w
    def scale_y(v): return margin_t + plot_h - (v - min_y) / (max_y - min_y) * plot_h

    # Fit linear OLS trend line
    if len(x_bins) > 1:
        slope, intercept = np.polyfit(x_bins, y_bins, 1)
        x_line_start, x_line_end = min(x_bins), max(x_bins)
        y_line_start = slope * x_line_start + intercept
        y_line_end = slope * x_line_end + intercept
    else:
        slope, intercept = 0, y_bins[0]
        x_line_start, x_line_end = min_x, max_x
        y_line_start, y_line_end = intercept, intercept

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" style="background-color: #ffffff; font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif;">',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        f'<text x="{width//2}" y="30" font-size="16" font-weight="bold" text-anchor="middle" fill="#1e293b">Descriptive Binned Means ({y_label_xml} vs. {x_label_xml})</text>',
        
        # Grid lines
        f'<line x1="{margin_l}" y1="{margin_t}" x2="{margin_l}" y2="{margin_t+plot_h}" stroke="#cbd5e1" stroke-width="1.5"/>',
        f'<line x1="{margin_l}" y1="{margin_t+plot_h}" x2="{margin_l+plot_w}" y2="{margin_t+plot_h}" stroke="#cbd5e1" stroke-width="1.5"/>',
    ]

    # OLS Fit Line
    svg_parts.append(
        f'<line x1="{scale_x(x_line_start):.1f}" y1="{scale_y(y_line_start):.1f}" x2="{scale_x(x_line_end):.1f}" y2="{scale_y(y_line_end):.1f}" stroke="#dc2626" stroke-width="2.5" stroke-dasharray="4,3"/>'
    )

    # Points
    for x, y in zip(x_bins, y_bins):
        cx = scale_x(x)
        cy = scale_y(y)
        svg_parts.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="5.5" fill="#2563eb" stroke="#1d4ed8" stroke-width="1.5" opacity="0.85"/>'
        )

    # Axis Labels
    svg_parts.append(f'<text x="{margin_l + plot_w//2}" y="{height - 15}" font-size="13" font-weight="600" text-anchor="middle" fill="#334155">{x_label_xml}</text>')
    svg_parts.append(f'<text x="25" y="{margin_t + plot_h//2}" font-size="13" font-weight="600" text-anchor="middle" transform="rotate(-90 25 {margin_t + plot_h//2})" fill="#334155">{y_label_xml}</text>')
    
    # Legend
    svg_parts.append(
        f'<text x="{margin_l + plot_w - 180}" y="{margin_t + 25}" font-size="12" fill="#475569">OLS Slope: {slope:.4f}</text>'
    )

    svg_parts.append('</svg>')

    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(svg_parts))

def generate_latex_table(summary_df: pd.DataFrame) -> str:
    """
    Exports summary stats to LaTeX tabular syntax.
    """
    lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        r"\caption{Descriptive Summary Statistics}",
        r"\label{tab:summary_stats}",
        r"\begin{tabular}{lrrrrrrr}",
        r"\hline\hline",
        r"Variable & Obs & Mean & Std. Dev. & Min & Median & Max & Missing \\",
        r"\hline"
    ]
    for _, row in summary_df.iterrows():
        replacements = {
            "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$",
            "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
            "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
        }
        var_name = "".join(replacements.get(char, char) for char in str(row["Variable"]))
        obs = f"{row['Obs']:,}"
        mean = f"{row['Mean']:.3f}" if not pd.isna(row['Mean']) else "-"
        sd = f"{row['Std. Dev.']:.3f}" if not pd.isna(row['Std. Dev.']) else "-"
        min_v = f"{row['Min']:.3f}" if not pd.isna(row['Min']) else "-"
        med = f"{row['Median']:.3f}" if not pd.isna(row['Median']) else "-"
        max_v = f"{row['Max']:.3f}" if not pd.isna(row['Max']) else "-"
        miss = str(row["Missing %"]).replace("%", r"\%")
        lines.append(f"{var_name} & {obs} & {mean} & {sd} & {min_v} & {med} & {max_v} & {miss} \\\\")
    lines.extend([
        r"\hline\hline",
        r"\multicolumn{8}{l}{\footnotesize Notes: Statistics computed via Econ Data Profiler.}",
        r"\end{tabular}",
        r"\end{table}"
    ])
    return "\n".join(lines)


def compute_binned_means(df: pd.DataFrame, x: str, y: str, bins: int) -> pd.DataFrame:
    """Return quantile-binned means or an empty frame when X has no variation."""
    sub = df[[x, y]].dropna().copy()
    if len(sub) < 5 or sub[x].nunique() < 2 or bins < 2:
        return pd.DataFrame(columns=[x, y])
    nbins = min(bins, max(2, len(sub) // 2), sub[x].nunique())
    sub["bin"] = pd.qcut(sub[x], q=nbins, duplicates="drop")
    return sub.groupby("bin", observed=True).agg({x: "mean", y: "mean"}).reset_index(drop=True)

def main():
    parser = argparse.ArgumentParser(description="Econ Data Profiler: panel checks, summary statistics, and descriptive binned means")
    parser.add_argument("--data", "-d", required=True, help="Path to input data file (.csv, .dta, .parquet, .xlsx)")
    parser.add_argument("--vars", "-v", nargs="+", help="Specific variables to profile (default: all numeric)")
    parser.add_argument("--id", type=str, help="Panel individual/unit ID column name")
    parser.add_argument("--time", type=str, help="Panel time column name")
    parser.add_argument("--x", type=str, help="Explanatory variable for binned scatterplot")
    parser.add_argument("--y", type=str, help="Outcome variable for binned scatterplot")
    parser.add_argument("--bins", type=int, default=20, help="Number of quantile bins (default: 20)")
    parser.add_argument("--out-dir", "-o", default="output", help="Directory to save generated tables and plots")
    parser.add_argument("--latex", action="store_true", help="Output LaTeX table syntax")

    args = parser.parse_args()

    data_path = args.data
    if not os.path.exists(data_path):
        print(f"[Error] File not found: {data_path}")
        sys.exit(1)

    ext = os.path.splitext(data_path)[-1].lower()
    try:
        if ext == ".csv":
            df = pd.read_csv(data_path)
        elif ext in [".dta"]:
            df = pd.read_stata(data_path)
        elif ext in [".parquet"]:
            df = pd.read_parquet(data_path)
        elif ext in [".xlsx", ".xls"]:
            df = pd.read_excel(data_path)
        else:
            df = pd.read_csv(data_path)
    except Exception as e:
        print(f"[Error] Failed to load {data_path}: {e}")
        sys.exit(1)

    requested = {"id": args.id, "time": args.time, "x": args.x, "y": args.y}
    for index, column in enumerate(args.vars or []):
        requested[f"vars[{index}]"] = column
    try:
        validate_columns(df, requested)
    except ValueError as exc:
        print(f"[Error] {exc}")
        sys.exit(2)

    os.makedirs(args.out_dir, exist_ok=True)

    # 1. Check Panel Structure
    panel_info = check_panel_structure(df, args.id, args.time)
    print("\n" + "=" * 60)
    print("📊 DATASET ARCHITECTURE AUDIT")
    print("=" * 60)
    print(f"Total Observations (Rows): {panel_info['total_rows']:,}")
    print(f"Total Variables (Columns):    {len(df.columns)}")
    if panel_info["is_panel"]:
        balance_str = "Balanced Panel ✅" if panel_info["is_balanced"] else "Unbalanced Panel ⚠️"
        print(f"Panel Structure Detected:     ID='{panel_info['id_col']}', Time='{panel_info['time_col']}'")
        print(f"Unique Units (N):             {panel_info['num_units']:,}")
        print(f"Unique Time Periods (T):      {panel_info['num_periods']:,}")
        print(f"Theoretical Obs (N x T):      {panel_info['num_units'] * panel_info['num_periods']:,}")
        print(f"Panel Balance Status:         {balance_str}")
        print(f"Duplicate ID-Time Rows:       {panel_info['duplicate_key_rows']:,}")
        print(f"Rows Missing Panel Keys:      {panel_info['missing_key_rows']:,}")
        print(f"Periods per Unit (Min/Max):   {panel_info['min_periods_per_unit']} / {panel_info['max_periods_per_unit']}")
    else:
        print("Panel Structure:              Cross-sectional or unidentified time/unit keys.")

    # 2. Compute Summary Statistics Table
    summary_df = compute_summary_table(df, args.vars)
    md_table = dataframe_to_markdown(summary_df)
    print("\n" + "=" * 60)
    print("📋 TABLE 1: SUMMARY STATISTICS (MARKDOWN)")
    print("=" * 60)
    print(md_table)

    # Save Markdown Table
    md_path = os.path.join(args.out_dir, "table1_summary_stats.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Table 1: Summary Statistics\n\n" + md_table + "\n")

    # Save LaTeX Table if requested
    if args.latex:
        latex_code = generate_latex_table(summary_df)
        tex_path = os.path.join(args.out_dir, "table1_summary_stats.tex")
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(latex_code + "\n")
        print(f"\n[+] Saved LaTeX table to: {tex_path}")

    # 3. Descriptive binned means visualization
    if args.x and args.y:
        binned = compute_binned_means(df, args.x, args.y, args.bins)
        if binned.empty:
            print("[Warning] Binned means require at least five observations, two bins, and variation in X.")
        else:
            x_vals = binned[args.x].tolist()
            y_vals = binned[args.y].tolist()
            ascii_plot = generate_ascii_binscatter(x_vals, y_vals, args.x, args.y)
            print("\n" + "=" * 60)
            print(f"📈 DESCRIPTIVE BINNED MEANS ({args.y} vs. {args.x})")
            print("=" * 60)
            print(ascii_plot)

            svg_path = os.path.join(args.out_dir, f"descriptive_binned_means_{args.y}_vs_{args.x}.svg")
            generate_svg_binscatter(x_vals, y_vals, args.x, args.y, svg_path)
            print(f"\n[+] Descriptive SVG saved to: {svg_path}")

    print("\n" + "=" * 60)
    print(f"✅ Profiling complete. Artifacts saved in directory: '{args.out_dir}'")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
