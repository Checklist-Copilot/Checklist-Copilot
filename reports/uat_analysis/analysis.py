#!/usr/bin/env python3
"""Analyze the Checkly UAT survey exported as CSV.

Install dependencies:
    pip install pandas numpy matplotlib openpyxl

Run:
    python checkly_uat_csv_analysis.py responses.csv

Optional acceptance criteria:
    python checkly_uat_csv_analysis.py responses.csv \
        --acceptance-mean 4.0 --acceptance-positive 70

Outputs are written to ./uat_results by default.
"""

from __future__ import annotations

import argparse
import re
import unicodedata
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import MaxNLocator


RATING_COLUMNS = {
    "First impression": ["first impression"],
    "Ease of use": ["ease of use"],
    "App stability and reliability": ["app stability and reliability", "stability"],
    "Speed and responsiveness": ["speed and responsiveness", "speed"],
    "Ease of checklist creation": ["ease of checklist creation", "checklist creation"],
    "Usefulness of AI features": ["usefulness of ai features", "ai usefulness"],
    "AI understanding of requests": ["understanding of requests", "ai understanding"],
    "Trust in AI suggested changes": ["trust in the ai assistant", "trust in ai", "ai trust"],
    "Overall satisfaction": ["overall satisfaction"],
}

OTHER_COLUMNS = {
    "first_name": ["first name"],
    "last_name": ["last name"],
    "occupation": ["occupation"],
    "device": ["device used during testing", "device"],
    "browser": ["browser used", "browser"],
    "prior_use": ["have you used checklist software before", "previous checklist use"],
    "future_use": ["is there any chance you see yourself using", "future use"],
    "liked": ["what did you like most", "liked most"],
    "friction": ["what was confusing slow or didn t work", "confusing slow unexpected"],
    "improvement": ["what could be improved", "suggested improvement"],
    "missing_feature": ["feature you expected to find", "missing feature"],
    "additional": ["additional comments"],
}

# Regex-based theme coding. Review the participant-level coding before reporting it.
POSITIVE_THEMES = {
    "AI capabilities": r"\bai\b|assistant|chatbot|agentic",
    "UI and visual design": r"\bui\b|design|visual",
    "Simplicity and ease": r"simple|simplicity|ease of use|easy",
    "Checklist organisation": r"my checklist|checklist organisation|organized|organised",
}

IMPROVEMENT_THEMES = {
    "PDF/download workflow": r"\bpdf\b|download|upload",
    "Layout and visual simplification": r"layout|too many colou?rs|graphic|font size|full view|fit.*screen|visual density",
    "Sign-up and onboarding flow": r"sign.?up|create an account|registration|start for free|onboarding",
    "Navigation and checklist controls": r"back button|check.?off|open.*checklist directly|direct.*checklist|navigation|scroll",
    "Trust, legal information and social proof": r"impressum|legal|customer feedback|customer quote|social proof",
    "Profile customisation": r"profil(?:e)? picture|avatar",
}


def normalize(text: object) -> str:
    """Convert a header to a lowercase, accent-free comparison string."""
    value = unicodedata.normalize("NFKD", str(text))
    value = value.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def find_column(df: pd.DataFrame, aliases: list[str], required: bool = False) -> str | None:
    normalized = {column: normalize(column) for column in df.columns}
    for alias in aliases:
        needle = normalize(alias)
        matches = [column for column, header in normalized.items() if needle in header]
        if matches:
            return min(matches, key=lambda column: len(normalized[column]))
    if required:
        raise KeyError(f"Could not find a column matching: {aliases}")
    return None


def get_text(df: pd.DataFrame, column: str | None) -> pd.Series:
    if column is None:
        return pd.Series("", index=df.index, dtype="string")
    return df[column].fillna("").astype(str).str.strip()


def frequency_table(series: pd.Series, dimension: str) -> pd.DataFrame:
    cleaned = series.fillna("").astype(str).str.strip().replace("", "Not specified")
    counts = cleaned.value_counts(dropna=False)
    return pd.DataFrame(
        {
            "Dimension": dimension,
            "Category": counts.index,
            "Count": counts.values,
            "Share (%)": counts.values / counts.sum() * 100,
        }
    )


def save_figure(fig: plt.Figure, output_dir: Path, name: str) -> None:
    fig.savefig(output_dir / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(output_dir / f"{name}.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def analyze(args: argparse.Namespace) -> None:
    input_path = Path(args.csv_file)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # sep=None automatically detects comma, semicolon, or tab delimiters.
    df = pd.read_csv(input_path, sep=None, engine="python", encoding="utf-8-sig")
    df.columns = [str(column).strip() for column in df.columns]

    rating_sources = {
        label: find_column(df, aliases, required=True)
        for label, aliases in RATING_COLUMNS.items()
    }
    other_sources = {
        key: find_column(df, aliases)
        for key, aliases in OTHER_COLUMNS.items()
    }

    # Create anonymous IDs and never export names.
    participant_ids = pd.Series(
        [f"P{number:02d}" for number in range(1, len(df) + 1)],
        index=df.index,
        name="Participant ID",
    )

    ratings = pd.DataFrame(index=df.index)
    for label, source in rating_sources.items():
        ratings[label] = pd.to_numeric(df[source], errors="coerce")

    invalid = ~ratings.isna() & ~ratings.isin([1, 2, 3, 4, 5])
    if invalid.any().any():
        locations = np.argwhere(invalid.to_numpy())
        print(f"Warning: {len(locations)} rating(s) outside 1–5 were treated as missing.")
        ratings = ratings.mask(invalid)

    # Quantitative summary.
    metric_summary = pd.DataFrame(
        {
            "N": ratings.count(),
            "Mean": ratings.mean(),
            "Median": ratings.median(),
            "SD": ratings.std(ddof=1),
            "Positive count": (ratings >= args.positive_threshold).sum(),
            "Positive (%)": (ratings >= args.positive_threshold).sum() / ratings.count() * 100,
        }
    )
    metric_summary.index.name = "Metric"

    if args.acceptance_mean is not None and args.acceptance_positive is not None:
        metric_summary["Meets supplied criteria"] = (
            (metric_summary["Mean"] >= args.acceptance_mean)
            & (metric_summary["Positive (%)"] >= args.acceptance_positive)
        )

    distribution = pd.DataFrame(
        {
            metric: ratings[metric].value_counts().reindex(range(1, 6), fill_value=0)
            for metric in ratings.columns
        }
    ).T
    distribution.columns = [f"Rating {score}" for score in range(1, 6)]
    distribution.index.name = "Metric"

    all_ratings = ratings.stack()
    aggregate_mean = all_ratings.mean()
    aggregate_positive = (all_ratings >= args.positive_threshold).mean() * 100

    # Participant profile.
    profile_tables: list[pd.DataFrame] = []
    for key, label in [
        ("occupation", "Occupation"),
        ("device", "Device"),
        ("browser", "Browser"),
        ("prior_use", "Previous checklist use"),
        ("future_use", "Future-use interest"),
    ]:
        column = other_sources[key]
        if column is not None:
            series = df[column].copy()
            if key == "device":
                series = series.astype(str).str.replace(r"\s*\(recommended\)\s*", "", regex=True)
            if key == "browser":
                series = series.astype(str).str.replace(r"(?i)^dickduckgo$", "DuckDuckGo", regex=True)
            profile_tables.append(frequency_table(series, label))
    profile = pd.concat(profile_tables, ignore_index=True) if profile_tables else pd.DataFrame()

    # Qualitative theme coding.
    liked_text = get_text(df, other_sources["liked"])
    improvement_text = (
        get_text(df, other_sources["friction"])
        + " "
        + get_text(df, other_sources["improvement"])
        + " "
        + get_text(df, other_sources["missing_feature"])
    ).str.strip()

    coding = pd.DataFrame({"Participant ID": participant_ids})
    for theme, pattern in POSITIVE_THEMES.items():
        coding[f"Positive: {theme}"] = liked_text.str.contains(pattern, case=False, regex=True, na=False).astype(int)
    for theme, pattern in IMPROVEMENT_THEMES.items():
        coding[f"Improvement: {theme}"] = improvement_text.str.contains(pattern, case=False, regex=True, na=False).astype(int)

    positive_theme_summary = pd.DataFrame(
        {
            "Theme": list(POSITIVE_THEMES),
            "Mentions": [coding[f"Positive: {theme}"].sum() for theme in POSITIVE_THEMES],
        }
    ).sort_values(["Mentions", "Theme"], ascending=[False, True])

    improvement_theme_summary = pd.DataFrame(
        {
            "Theme": list(IMPROVEMENT_THEMES),
            "Mentions": [coding[f"Improvement: {theme}"].sum() for theme in IMPROVEMENT_THEMES],
        }
    ).sort_values(["Mentions", "Theme"], ascending=[False, True])

    # Anonymized source data for auditing.
    columns_to_drop = [
        column for column in [other_sources["first_name"], other_sources["last_name"]]
        if column is not None
    ]
    anonymized = df.drop(columns=columns_to_drop).copy()
    existing_id = find_column(anonymized, ["participant id"])
    if existing_id is not None:
        anonymized = anonymized.drop(columns=[existing_id])
    anonymized.insert(0, "Participant ID", participant_ids)

    # CSV and Excel outputs.
    metric_summary.round(2).to_csv(output_dir / "metric_summary.csv")
    distribution.to_csv(output_dir / "likert_distribution.csv")
    profile.round(1).to_csv(output_dir / "participant_profile.csv", index=False)
    positive_theme_summary.to_csv(output_dir / "positive_themes.csv", index=False)
    improvement_theme_summary.to_csv(output_dir / "improvement_themes.csv", index=False)
    coding.to_csv(output_dir / "qualitative_coding_review.csv", index=False)

    with pd.ExcelWriter(output_dir / "uat_analysis.xlsx", engine="openpyxl") as writer:
        metric_summary.round(2).to_excel(writer, sheet_name="Metric Summary")
        distribution.to_excel(writer, sheet_name="Rating Distribution")
        profile.round(1).to_excel(writer, sheet_name="Participant Profile", index=False)
        positive_theme_summary.to_excel(writer, sheet_name="Positive Themes", index=False)
        improvement_theme_summary.to_excel(writer, sheet_name="Improvement Themes", index=False)
        coding.to_excel(writer, sheet_name="Coding Review", index=False)
        anonymized.to_excel(writer, sheet_name="Anonymized Responses", index=False)

    # Chart styling.
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 13,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )

    # 1. Mean ratings.
    ordered = metric_summary.sort_values("Mean")
    colors = ["#D97706" if value == ordered["Mean"].min() else "#2563EB" for value in ordered["Mean"]]
    fig, ax = plt.subplots(figsize=(8.5, 5.0))
    bars = ax.barh(ordered.index, ordered["Mean"], color=colors, height=0.65)
    ax.set_xlim(1, 5)
    ax.set_xticks(range(1, 6))
    ax.set_xlabel("Mean rating (1–5)")
    ax.set_title("Checkly UAT: mean rating by metric")
    ax.grid(axis="x", color="#D1D5DB", linewidth=0.8)
    ax.set_axisbelow(True)
    for bar, value in zip(bars, ordered["Mean"]):
        ax.text(value + 0.06, bar.get_y() + bar.get_height() / 2, f"{value:.1f}", va="center", fontweight="bold")
    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    save_figure(fig, output_dir, "uat_metric_averages")

    # 2. Stacked Likert distribution.
    percentages = distribution.div(distribution.sum(axis=1), axis=0) * 100
    likert_colors = ["#B91C1C", "#F97316", "#D1D5DB", "#60A5FA", "#1D4ED8"]
    fig, ax = plt.subplots(figsize=(9.5, 5.6))
    left = np.zeros(len(percentages))
    for score, color in zip(range(1, 6), likert_colors):
        values = percentages[f"Rating {score}"].to_numpy()
        ax.barh(percentages.index, values, left=left, color=color, label=str(score), height=0.68)
        left += values
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("Share of responses (%)")
    ax.set_title("Checkly UAT: distribution of 1–5 ratings")
    ax.legend(title="Rating", ncol=5, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    ax.grid(axis="x", color="#E5E7EB", linewidth=0.7)
    ax.set_axisbelow(True)
    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    fig.subplots_adjust(left=0.30, right=0.98, top=0.90, bottom=0.24)
    save_figure(fig, output_dir, "uat_likert_distribution")

    # 3. Improvement themes.
    theme_plot = improvement_theme_summary[improvement_theme_summary["Mentions"] > 0].sort_values("Mentions")
    if not theme_plot.empty:
        fig, ax = plt.subplots(figsize=(8.5, 4.5))
        bars = ax.barh(theme_plot["Theme"], theme_plot["Mentions"], color="#2563EB", height=0.65)
        ax.set_xlabel("Number of participants mentioning theme")
        ax.set_title("Repeated improvement themes in open-text feedback")
        ax.set_xlim(0, max(theme_plot["Mentions"].max() + 1, 2))
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        ax.grid(axis="x", color="#D1D5DB", linewidth=0.8)
        ax.set_axisbelow(True)
        for bar, value in zip(bars, theme_plot["Mentions"]):
            ax.text(value + 0.05, bar.get_y() + bar.get_height() / 2, str(value), va="center", fontweight="bold")
        for spine in ["top", "right", "left"]:
            ax.spines[spine].set_visible(False)
        fig.tight_layout()
        save_figure(fig, output_dir, "uat_improvement_themes")

    # Concise console summary.
    print(f"Participants: {len(df)}")
    print(f"Aggregate mean: {aggregate_mean:.2f}/5")
    print(f"Positive ratings: {aggregate_positive:.1f}%")
    print("\nMetric summary:")
    print(metric_summary.round(2).to_string())
    print("\nImportant interpretation:")
    print("Percentages describe this test sample, not precise population estimates.")
    print("Repeated findings can still support cautious, directional conclusions for similar target users.")
    print(f"\nFiles saved to: {output_dir.resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze the Checkly UAT CSV export.")
    parser.add_argument("csv_file", help="Path to the survey CSV file")
    parser.add_argument("--output-dir", default="results_analysis", help="Output directory (default: uat_results)")
    parser.add_argument("--positive-threshold", type=float, default=4, help="Minimum positive rating (default: 4)")
    parser.add_argument("--acceptance-mean", type=float, default=None, help="Optional minimum acceptable mean")
    parser.add_argument("--acceptance-positive", type=float, default=None, help="Optional minimum positive percentage")
    args = parser.parse_args()
    if (args.acceptance_mean is None) != (args.acceptance_positive is None):
        parser.error("Supply both --acceptance-mean and --acceptance-positive, or neither.")
    return args


if __name__ == "__main__":
    analyze(parse_args())