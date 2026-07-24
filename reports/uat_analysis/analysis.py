#!/usr/bin/env python3
"""Analyze the Checkly UAT survey exported as CSV.

Install dependencies:
    pip install pandas numpy matplotlib

Run:
    python checkly_uat_csv_analysis.py responses.csv

Optional acceptance criteria:
    python checkly_uat_csv_analysis.py responses.csv \
        --acceptance-mean 4.0 --acceptance-positive 70

PNG plots are written to ./results_analysis by default.
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

# Shared palette for every pie chart.
PIE_BLUE = "#0D5ACD"
PIE_GREEN = "#20A658"
PIE_YELLOW = "#F9A825"
PIE_RED = "#C62828"

PIE_COLORS = [PIE_BLUE, PIE_GREEN, PIE_YELLOW, PIE_RED]
PROFESSION_PIE_COLORS = [PIE_BLUE, PIE_RED, PIE_YELLOW]
PRIOR_USE_PIE_COLORS = [PIE_GREEN, PIE_BLUE, PIE_YELLOW]


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

    # Chart styling.
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 13,
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

    # 4. Positive-response rate by metric.
    positive_ordered = metric_summary.sort_values("Positive (%)")
    fig, ax = plt.subplots(figsize=(8.5, 5.0))
    colors = [
        "#16A34A" if value >= 70 else "#D97706"
        for value in positive_ordered["Positive (%)"]
    ]
    bars = ax.barh(
        positive_ordered.index,
        positive_ordered["Positive (%)"],
        color=colors,
        height=0.65,
    )
    ax.axvline(70, color="#374151", linestyle="--", linewidth=1.2, label="70% reference")
    ax.set_xlim(0, 100)
    ax.set_xlabel(f"Ratings at or above {args.positive_threshold:g} (%)")
    ax.set_title("Checkly UAT: positive-response rate by metric")
    ax.grid(axis="x", color="#E5E7EB", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="lower right")
    for bar, value in zip(bars, positive_ordered["Positive (%)"]):
        ax.text(
            min(value + 1.5, 96),
            bar.get_y() + bar.get_height() / 2,
            f"{value:.0f}%",
            va="center",
            fontweight="bold",
        )
    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    save_figure(fig, output_dir, "uat_positive_rates")

    # 5. Participant-level profile lines. This exposes outliers without a heatmap.
    fig, ax = plt.subplots(figsize=(10.5, 5.8))
    x = np.arange(len(ratings.columns))
    for row, participant_id in zip(ratings.to_numpy(dtype=float), participant_ids):
        ax.plot(
            x,
            row,
            marker="o",
            markersize=4,
            linewidth=1.1,
            alpha=0.65,
            label=participant_id,
        )
    ax.plot(
        x,
        ratings.mean(axis=0),
        color="#111827",
        marker="o",
        markersize=6,
        linewidth=3,
        label="Sample mean",
        zorder=5,
    )
    ax.set_xticks(x)
    ax.set_xticklabels(ratings.columns, rotation=38, ha="right")
    ax.set_ylim(0.8, 5.2)
    ax.set_yticks(range(1, 6))
    ax.set_ylabel("Rating (1–5)")
    ax.set_title("Participant-level rating profiles")
    ax.grid(axis="y", color="#E5E7EB", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, ncol=6, fontsize=8, loc="upper center")
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    save_figure(fig, output_dir, "uat_participant_rating_profiles")

    # 6. Score spread by metric.
    fig, ax = plt.subplots(figsize=(9.5, 5.8))
    box_data = [ratings[column].dropna().to_numpy() for column in ratings.columns]
    box = ax.boxplot(
        box_data,
        orientation="horizontal",
        tick_labels=ratings.columns,
        patch_artist=True,
        widths=0.58,
        medianprops={"color": "#111827", "linewidth": 1.8},
    )
    for patch in box["boxes"]:
        patch.set_facecolor("#93C5FD")
        patch.set_edgecolor("#2563EB")
    ax.set_xlim(0.8, 5.2)
    ax.set_xticks(range(1, 6))
    ax.set_xlabel("Rating (1–5)")
    ax.set_title("Checkly UAT: score spread and median by metric")
    ax.grid(axis="x", color="#E5E7EB", linewidth=0.8)
    ax.set_axisbelow(True)
    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    save_figure(fig, output_dir, "uat_metric_boxplots")

    # 7. Ranked correlation pairs to identify metrics that move together.
    correlations = ratings.corr()
    correlation_pairs = []
    for first_index, first_metric in enumerate(correlations.columns):
        for second_index in range(first_index + 1, len(correlations.columns)):
            second_metric = correlations.columns[second_index]
            correlation_pairs.append(
                (
                    f"{first_metric} vs {second_metric}",
                    correlations.iat[first_index, second_index],
                )
            )
    correlation_pairs = sorted(
        correlation_pairs,
        key=lambda item: abs(item[1]),
        reverse=True,
    )[:12]
    pair_labels = [pair[0] for pair in reversed(correlation_pairs)]
    pair_values = [pair[1] for pair in reversed(correlation_pairs)]
    fig, ax = plt.subplots(figsize=(10.0, 6.5))
    bars = ax.barh(
        pair_labels,
        pair_values,
        color=["#2563EB" if value >= 0 else "#D97706" for value in pair_values],
        height=0.65,
    )
    ax.axvline(0, color="#374151", linewidth=0.9)
    ax.set_xlim(-1, 1)
    ax.set_xlabel("Pearson correlation")
    ax.set_title("Strongest correlations between UAT rating metrics")
    ax.grid(axis="x", color="#E5E7EB", linewidth=0.8)
    ax.set_axisbelow(True)
    for bar, value in zip(bars, pair_values):
        ax.text(
            value - 0.03 if value >= 0 else value + 0.03,
            bar.get_y() + bar.get_height() / 2,
            f"{value:.2f}",
            ha="right" if value >= 0 else "left",
            va="center",
            color="white" if abs(value) > 0.25 else "#111827",
            fontweight="bold",
        )
    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    save_figure(fig, output_dir, "uat_metric_correlation_pairs")

    # 8. Overall participant score, useful for spotting influential responses.
    participant_means = ratings.mean(axis=1).sort_values()
    sorted_ids = participant_ids.loc[participant_means.index]
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    colors = [
        "#D97706" if value < aggregate_mean else "#2563EB"
        for value in participant_means
    ]
    bars = ax.barh(sorted_ids, participant_means, color=colors, height=0.65)
    ax.axvline(
        aggregate_mean,
        color="#374151",
        linestyle="--",
        linewidth=1.2,
        label=f"Sample mean ({aggregate_mean:.2f})",
    )
    ax.set_xlim(1, 5)
    ax.set_xticks(range(1, 6))
    ax.set_xlabel("Mean across available rating metrics")
    ax.set_ylabel("Anonymous participant")
    ax.set_title("Overall rating by participant")
    ax.grid(axis="x", color="#E5E7EB", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="lower right")
    for bar, value in zip(bars, participant_means):
        ax.text(
            min(value + 0.06, 4.9),
            bar.get_y() + bar.get_height() / 2,
            f"{value:.1f}",
            va="center",
            fontweight="bold",
        )
    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    save_figure(fig, output_dir, "uat_participant_means")

    # 9. Directional device comparison. Labels expose the small subgroup sizes.
    device_column = other_sources["device"]
    if device_column is not None:
        devices = (
            df[device_column]
            .fillna("Not specified")
            .astype(str)
            .str.replace(r"\s*\(recommended\)\s*", "", regex=True)
            .str.strip()
            .replace("", "Not specified")
        )
        device_means = ratings.assign(Device=devices).groupby("Device").mean()
        device_counts = devices.value_counts().reindex(device_means.index)
        fig, ax = plt.subplots(figsize=(10.5, 5.6))
        x = np.arange(len(device_means.columns))
        width = 0.8 / max(len(device_means), 1)
        palette = ["#2563EB", "#16A34A", "#D97706", "#7C3AED"]
        for position, (device, values) in enumerate(device_means.iterrows()):
            offset = (position - (len(device_means) - 1) / 2) * width
            ax.bar(
                x + offset,
                values,
                width=width,
                label=f"{device} (n={device_counts[device]})",
                color=palette[position % len(palette)],
            )
        ax.set_ylim(1, 5)
        ax.set_yticks(range(1, 6))
        ax.set_xticks(x)
        ax.set_xticklabels(device_means.columns, rotation=38, ha="right")
        ax.set_ylabel("Mean rating (1–5)")
        ax.set_title("Directional comparison of ratings by device")
        ax.grid(axis="y", color="#E5E7EB", linewidth=0.8)
        ax.set_axisbelow(True)
        ax.legend(frameon=False, ncol=min(len(device_means), 3), loc="upper center")
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)
        fig.tight_layout()
        save_figure(fig, output_dir, "uat_ratings_by_device")

    # 10. Grouped rating dot plots for tester characteristics.
    def save_group_rating_dotplot(
        groups: pd.Series,
        title: str,
        filename: str,
    ) -> None:
        cleaned_groups = (
            groups.fillna("Not specified")
            .astype(str)
            .str.strip()
            .replace("", "Not specified")
        )
        grouped = ratings.assign(Group=cleaned_groups).groupby("Group").mean()
        counts = cleaned_groups.value_counts().reindex(grouped.index)
        if grouped.empty:
            return

        fig, ax = plt.subplots(figsize=(10.5, 6.0))
        y = np.arange(len(grouped.columns))
        offsets = np.linspace(-0.24, 0.24, len(grouped))
        palette = ["#2563EB", "#16A34A", "#D97706", "#7C3AED", "#DC2626", "#0891B2"]
        for position, (group, values) in enumerate(grouped.iterrows()):
            ax.scatter(
                values,
                y + offsets[position],
                s=65,
                color=palette[position % len(palette)],
                label=f"{group} (n={counts[group]})",
                zorder=3,
            )
            ax.plot(
                values,
                y + offsets[position],
                color=palette[position % len(palette)],
                linewidth=0.8,
                alpha=0.45,
            )
        ax.set_yticks(y)
        ax.set_yticklabels(grouped.columns)
        ax.invert_yaxis()
        ax.set_xlim(1, 5)
        ax.set_xticks(range(1, 6))
        ax.set_title(title)
        ax.set_xlabel("Subgroup mean rating (1–5)")
        ax.grid(axis="x", color="#E5E7EB", linewidth=0.8)
        ax.set_axisbelow(True)
        ax.legend(
            frameon=False,
            ncol=min(len(grouped), 3),
            loc="upper center",
            bbox_to_anchor=(0.5, -0.12),
        )
        for spine in ["top", "right", "left"]:
            ax.spines[spine].set_visible(False)
        fig.subplots_adjust(left=0.30, right=0.98, top=0.90, bottom=0.24)
        save_figure(fig, output_dir, filename)

    profile_plot_groups: list[tuple[str, pd.Series, str]] = []

    if device_column is not None:
        profile_plot_groups.append(("Device", devices, "uat_rating_profile_by_device"))
        save_group_rating_dotplot(
            devices,
            "Mean UAT ratings by device",
            "uat_rating_profile_by_device",
        )

    browser_column = other_sources["browser"]
    if browser_column is not None:
        browsers = (
            df[browser_column]
            .fillna("Not specified")
            .astype(str)
            .str.replace(r"(?i)^dickduckgo$", "DuckDuckGo", regex=True)
            .str.strip()
            .replace("", "Not specified")
        )
        profile_plot_groups.append(("Browser", browsers, "uat_rating_profile_by_browser"))
        save_group_rating_dotplot(
            browsers,
            "Mean UAT ratings by browser",
            "uat_rating_profile_by_browser",
        )

    occupation_column = other_sources["occupation"]
    if occupation_column is not None:
        backgrounds = (
            df[occupation_column]
            .fillna("Not specified")
            .astype(str)
            .str.replace(";", " / ", regex=False)
            .str.strip()
            .replace("", "Not specified")
        )
        profile_plot_groups.append(
            ("Professional background", backgrounds, "uat_rating_profile_by_background")
        )
        save_group_rating_dotplot(
            backgrounds,
            "Mean UAT ratings by professional background",
            "uat_rating_profile_by_background",
        )

    prior_use_column = other_sources["prior_use"]
    if prior_use_column is not None:
        prior_use = (
            df[prior_use_column]
            .fillna("Not specified")
            .astype(str)
            .str.strip()
            .replace("", "Not specified")
        )
        profile_plot_groups.append(
            ("Previous checklist use", prior_use, "uat_rating_profile_by_prior_use")
        )
        save_group_rating_dotplot(
            prior_use,
            "Mean UAT ratings by previous checklist-software use",
            "uat_rating_profile_by_prior_use",
        )

    # 11. Test each participant-information factor against every rating metric.
    # Permutation tests avoid relying on large-sample assumptions, but the results
    # remain exploratory because several subgroups contain very few participants.
    def eta_squared(group_codes: np.ndarray, values: np.ndarray) -> float:
        valid = ~np.isnan(values)
        group_codes = group_codes[valid]
        values = values[valid]
        grand_mean = values.mean()
        total_variation = ((values - grand_mean) ** 2).sum()
        if total_variation == 0:
            return 0.0
        between_group_variation = sum(
            (group_codes == code).sum()
            * (values[group_codes == code].mean() - grand_mean) ** 2
            for code in np.unique(group_codes)
        )
        return float(between_group_variation / total_variation)

    tested_characteristics = [
        (label, groups)
        for label, groups in [
            ("Professional background", backgrounds if occupation_column is not None else None),
            ("Device", devices if device_column is not None else None),
            ("Browser", browsers if browser_column is not None else None),
        ]
        if groups is not None
    ]

    permutation_rng = np.random.default_rng(42)
    permutation_count = 10_000
    metric_association_rows: list[dict[str, object]] = []
    for characteristic, group_series in tested_characteristics:
        cleaned_groups = (
            group_series.fillna("Not specified")
            .astype(str)
            .str.strip()
            .replace("", "Not specified")
        )
        group_codes = pd.Categorical(cleaned_groups).codes
        if len(np.unique(group_codes)) < 2:
            continue
        for metric in ratings.columns:
            metric_values = ratings[metric].to_numpy(dtype=float)
            observed = eta_squared(group_codes, metric_values)
            valid_values = metric_values[~np.isnan(metric_values)]
            valid_codes = group_codes[~np.isnan(metric_values)]
            exceedances = 0
            for _ in range(permutation_count):
                permuted = permutation_rng.permutation(valid_values)
                if eta_squared(valid_codes, permuted) >= observed:
                    exceedances += 1
            metric_association_rows.append(
                {
                    "Characteristic": characteristic,
                    "Metric": metric,
                    "Eta squared": observed,
                    "Permutation p": (exceedances + 1) / (permutation_count + 1),
                }
            )

    metric_associations = pd.DataFrame(metric_association_rows)
    if not metric_associations.empty:
        p_value_matrix = metric_associations.pivot(
            index="Metric",
            columns="Characteristic",
            values="Permutation p",
        ).reindex(index=ratings.columns)
        fig, ax = plt.subplots(figsize=(15.0, 12.5))
        image = ax.imshow(
            p_value_matrix.to_numpy(),
            cmap="RdYlGn",
            vmin=0,
            vmax=1,
            aspect="auto",
        )
        ax.set_xticks(range(len(p_value_matrix.columns)))
        ax.set_xticklabels(
            [
                "Professional\nbackground"
                if label == "Professional background"
                else label
                for label in p_value_matrix.columns
            ],
            rotation=25,
            ha="right",
            fontsize=32,
        )
        ax.set_yticks(range(len(p_value_matrix.index)))
        ax.set_yticklabels(p_value_matrix.index, fontsize=29)
        significant_count = int((p_value_matrix < 0.05).sum().sum())
        ax.set_title(
            "Testers information vs UAT metrics",
            fontsize=34,
            fontweight="bold",
            pad=16,
        )
        for row_index in range(len(p_value_matrix.index)):
            for column_index in range(len(p_value_matrix.columns)):
                value = p_value_matrix.iat[row_index, column_index]
                ax.text(
                    column_index,
                    row_index,
                    f"{value:.2f}" + ("*" if value < 0.05 else ""),
                    ha="center",
                    va="center",
                    color="white" if value < 0.18 else "#111827",
                    fontweight="bold" if value < 0.05 else "normal",
                    fontsize=30,
                )
        colorbar = fig.colorbar(image, ax=ax, fraction=0.035, pad=0.03)
        colorbar.set_label("p-value", fontsize=32)
        colorbar.ax.tick_params(labelsize=27)
        fig.tight_layout(rect=(0, 0.04, 1, 1))
        save_figure(
            fig,
            output_dir,
            "uat_characteristics_by_metric_significance",
        )

    # 12. Tester-background overview: profession and prior checklist use.
    if occupation_column is not None and prior_use_column is not None:
        profession_counts = backgrounds.value_counts()
        prior_use_counts = prior_use.value_counts()

        fig, axes = plt.subplots(1, 2, figsize=(9.0, 5.2))
        for ax, counts, title, colors in [
            (
                axes[0],
                profession_counts,
                "Professional\nbackground",
                PROFESSION_PIE_COLORS,
            ),
            (
                axes[1],
                prior_use_counts,
                "Previous checklist-\nsoftware use",
                PRIOR_USE_PIE_COLORS,
            ),
        ]:
            wedges, _, percentage_texts = ax.pie(
                counts.values,
                autopct=lambda percentage: f"{percentage:.0f}%",
                startangle=90,
                radius=1.08,
                colors=colors[: len(counts)],
                pctdistance=0.68,
                wedgeprops={"edgecolor": "white", "linewidth": 1.5},
                textprops={"fontsize": 14},
            )
            ax.set_title(title, fontweight="bold")
            ax.legend(
                wedges,
                counts.index,
                frameon=False,
                loc="lower center",
                bbox_to_anchor=(0.5, -0.28),
                fontsize=13,
            )
            for text in percentage_texts:
                text.set_fontweight("bold")

        fig.suptitle("Tester background", fontsize=15)
        fig.subplots_adjust(left=0.03, right=0.97, top=0.86, bottom=0.22, wspace=-0.30)
        save_figure(fig, output_dir, "uat_tester_background_pies")

    # 14. Testing-environment overview: device and browser.
    if device_column is not None and browser_column is not None:
        device_counts = devices.value_counts()
        browser_counts = browsers.value_counts()

        fig, axes = plt.subplots(1, 2, figsize=(9.0, 5.2))
        for ax, counts, title, colors in [
            (axes[0], device_counts, "Device used", PIE_COLORS),
            (axes[1], browser_counts, "Browser used", PIE_COLORS),
        ]:
            wedges, _, percentage_texts = ax.pie(
                counts.values,
                autopct=lambda percentage: f"{percentage:.0f}%",
                startangle=90,
                radius=1.08,
                colors=colors[: len(counts)],
                pctdistance=0.68,
                wedgeprops={"edgecolor": "white", "linewidth": 1.5},
                textprops={"fontsize": 14},
            )
            ax.set_title(title, fontweight="bold")
            ax.legend(
                wedges,
                counts.index,
                frameon=False,
                loc="lower center",
                bbox_to_anchor=(0.5, -0.28),
                fontsize=13,
            )
            for text in percentage_texts:
                text.set_fontweight("bold")

        fig.suptitle("Testing environment", fontsize=15)
        fig.subplots_adjust(left=0.03, right=0.97, top=0.86, bottom=0.27, wspace=-0.30)
        save_figure(fig, output_dir, "uat_testing_environment_pies")

    # 14. Combined participant overview: environment on the left, background on the right.
    if (
        device_column is not None
        and browser_column is not None
        and occupation_column is not None
        and prior_use_column is not None
    ):
        combined_pies = [
            (device_counts, "Device used", PIE_COLORS),
            (browser_counts, "Browser used", PIE_COLORS),
            (profession_counts, "Professional\nbackground", PROFESSION_PIE_COLORS),
            (
                prior_use_counts,
                "Previous checklist-\nsoftware use",
                PRIOR_USE_PIE_COLORS,
            ),
        ]

        fig, axes = plt.subplots(1, 4, figsize=(13.5, 5.4))
        for ax, (counts, title, colors) in zip(axes, combined_pies):
            wedges, _, percentage_texts = ax.pie(
                counts.values,
                autopct=lambda percentage: f"{percentage:.0f}%",
                startangle=90,
                radius=1.12,
                colors=colors[: len(counts)],
                pctdistance=0.68,
                wedgeprops={"edgecolor": "white", "linewidth": 1.5},
                textprops={"fontsize": 13},
            )
            ax.set_title(title, fontweight="bold", fontsize=12)
            ax.legend(
                wedges,
                counts.index,
                frameon=False,
                loc="lower center",
                bbox_to_anchor=(0.5, -0.48),
                fontsize=12,
            )
            for text in percentage_texts:
                text.set_fontweight("bold")

        fig.suptitle("UAT participant overview", fontsize=16, fontweight="bold")
        fig.text(
            0.27,
            0.89,
            "Testing environment",
            ha="center",
            fontsize=14,
            fontweight="bold",
        )
        fig.text(
            0.73,
            0.89,
            "Tester background",
            ha="center",
            fontsize=14,
            fontweight="bold",
        )
        fig.subplots_adjust(
            left=0.02,
            right=0.98,
            top=0.80,
            bottom=0.28,
            wspace=-0.38,
        )
        save_figure(fig, output_dir, "uat_participant_overview_pies")

    # Concise console summary.
    print(f"Participants: {len(df)}")
    print(f"Aggregate mean: {aggregate_mean:.2f}/5")
    print(f"Positive ratings: {aggregate_positive:.1f}%")
    print("\nMetric summary:")
    print(metric_summary.round(2).to_string())
    print("\nImportant interpretation:")
    print("Percentages describe this test sample, not precise population estimates.")
    print("Repeated findings can still support cautious, directional conclusions for similar target users.")
    if not metric_associations.empty:
        significant_tests = metric_associations[
            metric_associations["Permutation p"] < 0.05
        ]
        print(
            "\nParticipant characteristics vs individual rating metrics: "
        )
        closest_tests = metric_associations.nsmallest(5, "Permutation p")
        print("Five smallest p-values:")
        for _, row in closest_tests.iterrows():
            print(
                f"- {row['Characteristic']} vs {row['Metric']}: "
                f"eta-squared={row['Eta squared']:.2f}, "
                f"permutation p={row['Permutation p']:.2f}"
            )
        print(
            "These tests are exploratory and unadjusted for multiple comparisons. "
            "Small and sparse subgroups limit their reliability."
        )
    print(f"\nFiles saved to: {output_dir.resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze the Checkly UAT CSV export.")
    parser.add_argument("csv_file", help="Path to the survey CSV file")
    parser.add_argument("--output-dir", default="results_analysis", help="PNG output directory (default: results_analysis)")
    parser.add_argument("--positive-threshold", type=float, default=4, help="Minimum positive rating (default: 4)")
    parser.add_argument("--acceptance-mean", type=float, default=None, help="Optional minimum acceptable mean")
    parser.add_argument("--acceptance-positive", type=float, default=None, help="Optional minimum positive percentage")
    args = parser.parse_args()
    if (args.acceptance_mean is None) != (args.acceptance_positive is None):
        parser.error("Supply both --acceptance-mean and --acceptance-positive, or neither.")
    return args


if __name__ == "__main__":
    analyze(parse_args())
