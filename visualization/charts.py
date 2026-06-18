"""
Matplotlib chart generators for the dashboard.
Generates PNG files with a dark theme matching the UI.
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import config

CHARTS_DIR = os.path.join(config.BASE_DIR, "static", "charts")
os.makedirs(CHARTS_DIR, exist_ok=True)

DARK_BG = "#0A0A0F"
SURFACE_BG = "#12121A"
ACCENT = "#6C5CE7"
ACCENT_2 = "#A29BFE"
TEXT_COLOR = "#E4E4E7"
GRID_COLOR = "#1E1E2E"
DANGER = "#FF6B6B"
WARNING = "#FDCB6E"
SUCCESS = "#00B894"

plt.rcParams.update({
    "figure.facecolor": DARK_BG,
    "axes.facecolor": SURFACE_BG,
    "axes.edgecolor": GRID_COLOR,
    "axes.labelcolor": TEXT_COLOR,
    "text.color": TEXT_COLOR,
    "xtick.color": TEXT_COLOR,
    "ytick.color": TEXT_COLOR,
    "grid.color": GRID_COLOR,
    "grid.alpha": 0.3,
    "font.family": "sans-serif",
    "font.size": 11,
})


def _save_fig(fig, filename):
    filepath = os.path.join(CHARTS_DIR, filename)
    fig.savefig(filepath, bbox_inches="tight", facecolor=DARK_BG, edgecolor="none")
    plt.close(fig)
    return filename


def grade_distribution_histogram(grades, semester_label="All Semesters", filename="grade_dist.png"):
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=120)
    if not grades:
        ax.text(0.5, 0.5, "No data available", ha="center", va="center",
                fontsize=14, color=TEXT_COLOR, transform=ax.transAxes)
        return _save_fig(fig, filename)

    bins = [0, 40, 50, 55, 60, 65, 70, 75, 80, 85, 90, 100]
    colors = [DANGER, DANGER, WARNING, WARNING, WARNING, ACCENT_2, ACCENT_2, ACCENT, ACCENT, SUCCESS, SUCCESS]
    _, _, patches = ax.hist(grades, bins=bins, edgecolor=DARK_BG, linewidth=1.5, rwidth=0.85)
    for patch, color in zip(patches, colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.85)
    ax.set_xlabel("Score Range", fontsize=12, fontweight="bold")
    ax.set_ylabel("Number of Students", fontsize=12, fontweight="bold")
    ax.set_title(f"Grade Distribution — {semester_label}", fontsize=14, fontweight="bold", color=ACCENT_2)
    ax.grid(axis="y", alpha=0.2)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return _save_fig(fig, filename)


def gpa_trend_line(trend_data, student_name="Student", filename="gpa_trend.png"):
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=120)
    if not trend_data:
        ax.text(0.5, 0.5, "No data available", ha="center", va="center",
                fontsize=14, color=TEXT_COLOR, transform=ax.transAxes)
        return _save_fig(fig, filename)

    semesters = [d["semester_name"] for d in trend_data]
    gpas = [d["gpa"] for d in trend_data]
    ax.plot(semesters, gpas, color=ACCENT, linewidth=2.5, marker="o", markersize=10,
            markerfacecolor=ACCENT_2, markeredgecolor=DARK_BG, markeredgewidth=2)
    ax.fill_between(semesters, gpas, alpha=0.15, color=ACCENT)
    ax.axhline(y=3.5, color=SUCCESS, linestyle="--", alpha=0.4)
    ax.axhline(y=2.0, color=DANGER, linestyle="--", alpha=0.4)
    ax.set_ylim(0, 4.2)
    ax.set_title(f"GPA Trend — {student_name}", fontsize=14, fontweight="bold", color=ACCENT_2)
    ax.grid(axis="y", alpha=0.2)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return _save_fig(fig, filename)


def performance_radar(radar_data, student_name="Student", filename="radar.png"):
    fig, ax = plt.subplots(figsize=(6, 6), dpi=120, subplot_kw=dict(polar=True))
    fig.patch.set_facecolor(DARK_BG)
    ax.set_facecolor(DARK_BG)
    if not radar_data:
        ax.text(0, 0, "No data", ha="center", va="center", fontsize=14, color=TEXT_COLOR)
        return _save_fig(fig, filename)

    labels = radar_data["labels"]
    values = radar_data["values"]
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    values_loop = values + [values[0]]
    angles_loop = angles + [angles[0]]
    ax.plot(angles_loop, values_loop, color=ACCENT, linewidth=2.5)
    ax.fill(angles_loop, values_loop, color=ACCENT, alpha=0.2)
    ax.set_xticks(angles)
    ax.set_xticklabels(labels, fontsize=10, color=TEXT_COLOR)
    ax.set_ylim(0, 100)
    ax.set_title(f"Performance — {student_name}", fontsize=14, fontweight="bold", color=ACCENT_2, y=1.08)
    fig.tight_layout()
    return _save_fig(fig, filename)


def ranking_bar_chart(rankings, semester_label="All Semesters", filename="rankings.png"):
    fig, ax = plt.subplots(figsize=(8, 5), dpi=120)
    if not rankings:
        ax.text(0.5, 0.5, "No data available", ha="center", va="center",
                fontsize=14, color=TEXT_COLOR, transform=ax.transAxes)
        return _save_fig(fig, filename)

    names = [r["student_name"] for r in reversed(rankings)]
    gpas = [r["gpa"] for r in reversed(rankings)]
    colors = [SUCCESS if g >= 3.5 else ACCENT if g >= 2.5 else WARNING if g >= 2.0 else DANGER for g in gpas]
    ax.barh(names, gpas, color=colors, edgecolor=DARK_BG, height=0.6, alpha=0.85)
    ax.set_xlim(0, 4.2)
    ax.set_title(f"Class Rankings — {semester_label}", fontsize=14, fontweight="bold", color=ACCENT_2)
    ax.grid(axis="x", alpha=0.2)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return _save_fig(fig, filename)


def course_difficulty_bar(course_stats, semester_label="All Semesters", filename="course_difficulty.png"):
    """SP5: Course difficulty comparison chart."""
    fig, ax = plt.subplots(figsize=(8, 5), dpi=120)
    if not course_stats:
        ax.text(0.5, 0.5, "No data available", ha="center", va="center",
                fontsize=14, color=TEXT_COLOR, transform=ax.transAxes)
        return _save_fig(fig, filename)

    names = [c["course_code"] for c in reversed(course_stats)]
    scores = [c["avg_score"] for c in reversed(course_stats)]
    colors = [DANGER if s < 65 else WARNING if s < 75 else SUCCESS for s in scores]
    ax.barh(names, scores, color=colors, edgecolor=DARK_BG, height=0.6, alpha=0.85)
    ax.set_xlim(0, 105)
    ax.axvline(x=65, color=DANGER, linestyle="--", alpha=0.5)
    ax.set_title(f"Course Difficulty — {semester_label}", fontsize=14, fontweight="bold", color=ACCENT_2)
    ax.grid(axis="x", alpha=0.2)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return _save_fig(fig, filename)


def grade_box_plot(grades, semester_label="All Semesters", filename="grade_boxplot.png"):
    """SP5: Box plot of grade distribution."""
    fig, ax = plt.subplots(figsize=(6, 4.5), dpi=120)
    if grades:
        bp = ax.boxplot(grades, patch_artist=True, widths=0.5)
        bp["boxes"][0].set_facecolor(ACCENT)
        bp["boxes"][0].set_alpha(0.7)
        bp["medians"][0].set_color(ACCENT_2)
        ax.set_xticklabels([semester_label])
    else:
        ax.text(0.5, 0.5, "No data available", ha="center", va="center",
                fontsize=14, color=TEXT_COLOR, transform=ax.transAxes)
    ax.set_title(f"Grade Box Plot — {semester_label}", fontsize=14, fontweight="bold", color=ACCENT_2)
    ax.grid(axis="y", alpha=0.2)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return _save_fig(fig, filename)
