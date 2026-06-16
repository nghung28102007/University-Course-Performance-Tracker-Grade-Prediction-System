"""
Matplotlib chart generators for the dashboard.
Generates PNG files with a dark theme matching the UI.
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import config

CHARTS_DIR = os.path.join(config.BASE_DIR, "static", "charts")
os.makedirs(CHARTS_DIR, exist_ok=True)

# Dark theme colors matching the UI
DARK_BG = "#0A0A0F"
SURFACE_BG = "#12121A"
ACCENT = "#6C5CE7"
ACCENT_2 = "#A29BFE"
ACCENT_3 = "#00CEC9"
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


def grade_distribution_histogram(grades, semester_label="All Semesters", filename="grade_dist.png"):
    """Generate a grade distribution histogram."""
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=120)

    if not grades:
        ax.text(0.5, 0.5, "No data available", ha="center", va="center",
                fontsize=14, color=TEXT_COLOR, transform=ax.transAxes)
        filepath = os.path.join(CHARTS_DIR, filename)
        fig.savefig(filepath, bbox_inches="tight", facecolor=DARK_BG, edgecolor="none")
        plt.close(fig)
        return filename

    # Create bins
    bins = [0, 40, 50, 55, 60, 65, 70, 75, 80, 85, 90, 100]
    bin_labels = ["F", "D", "D+", "C", "C+", "B-", "B", "B+", "A-", "A", "A+"]

    # Color gradient from red to green
    colors = [DANGER, DANGER, WARNING, WARNING, WARNING, ACCENT_2, ACCENT_2, ACCENT, ACCENT, SUCCESS, SUCCESS]

    n, bins_out, patches = ax.hist(grades, bins=bins, edgecolor=DARK_BG, linewidth=1.5, rwidth=0.85)
    for patch, color in zip(patches, colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.85)

    ax.set_xlabel("Score Range", fontsize=12, fontweight="bold", labelpad=10)
    ax.set_ylabel("Number of Students", fontsize=12, fontweight="bold", labelpad=10)
    ax.set_title(f"Grade Distribution — {semester_label}", fontsize=14, fontweight="bold", pad=15, color=ACCENT_2)
    ax.grid(axis="y", alpha=0.2)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Add count labels on bars
    for rect in patches:
        height = rect.get_height()
        if height > 0:
            ax.annotate(f"{int(height)}",
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 5), textcoords="offset points",
                        ha="center", fontsize=9, color=TEXT_COLOR, fontweight="bold")

    fig.tight_layout()
    filepath = os.path.join(CHARTS_DIR, filename)
    fig.savefig(filepath, bbox_inches="tight", facecolor=DARK_BG, edgecolor="none")
    plt.close(fig)
    return filename


def gpa_trend_line(trend_data, student_name="Student", filename="gpa_trend.png"):
    """Generate a GPA trend line across semesters."""
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=120)

    if not trend_data:
        ax.text(0.5, 0.5, "No data available", ha="center", va="center",
                fontsize=14, color=TEXT_COLOR, transform=ax.transAxes)
        filepath = os.path.join(CHARTS_DIR, filename)
        fig.savefig(filepath, bbox_inches="tight", facecolor=DARK_BG, edgecolor="none")
        plt.close(fig)
        return filename

    semesters = [d["semester_name"] for d in trend_data]
    gpas = [d["gpa"] for d in trend_data]

    # Main line
    ax.plot(semesters, gpas, color=ACCENT, linewidth=2.5, marker="o", markersize=10,
            markerfacecolor=ACCENT_2, markeredgecolor=DARK_BG, markeredgewidth=2, zorder=5)

    # Fill area under
    ax.fill_between(semesters, gpas, alpha=0.15, color=ACCENT)

    # GPA reference lines
    ax.axhline(y=3.5, color=SUCCESS, linestyle="--", alpha=0.4, linewidth=1)
    ax.axhline(y=2.0, color=DANGER, linestyle="--", alpha=0.4, linewidth=1)
    ax.text(len(semesters) - 0.9, 3.55, "Dean's List (3.5)", fontsize=8, color=SUCCESS, alpha=0.7)
    ax.text(len(semesters) - 0.9, 2.05, "At Risk (2.0)", fontsize=8, color=DANGER, alpha=0.7)

    # Value labels
    for i, (sem, gpa) in enumerate(zip(semesters, gpas)):
        ax.annotate(f"{gpa:.2f}", (sem, gpa), xytext=(0, 15), textcoords="offset points",
                    ha="center", fontsize=11, fontweight="bold", color=ACCENT_2)

    ax.set_ylim(0, 4.2)
    ax.set_xlabel("Semester", fontsize=12, fontweight="bold", labelpad=10)
    ax.set_ylabel("GPA (4.0 Scale)", fontsize=12, fontweight="bold", labelpad=10)
    ax.set_title(f"GPA Trend — {student_name}", fontsize=14, fontweight="bold", pad=15, color=ACCENT_2)
    ax.grid(axis="y", alpha=0.2)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.tight_layout()
    filepath = os.path.join(CHARTS_DIR, filename)
    fig.savefig(filepath, bbox_inches="tight", facecolor=DARK_BG, edgecolor="none")
    plt.close(fig)
    return filename


def performance_radar(radar_data, student_name="Student", filename="radar.png"):
    """Generate a performance radar chart."""
    fig, ax = plt.subplots(figsize=(6, 6), dpi=120, subplot_kw=dict(polar=True))
    fig.patch.set_facecolor(DARK_BG)
    ax.set_facecolor(DARK_BG)

    if not radar_data:
        ax.text(0, 0, "No data", ha="center", va="center", fontsize=14, color=TEXT_COLOR)
        filepath = os.path.join(CHARTS_DIR, filename)
        fig.savefig(filepath, bbox_inches="tight", facecolor=DARK_BG, edgecolor="none")
        plt.close(fig)
        return filename

    labels = radar_data["labels"]
    values = radar_data["values"]

    # Complete the loop
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    values_loop = values + [values[0]]
    angles_loop = angles + [angles[0]]

    # Draw the radar
    ax.plot(angles_loop, values_loop, color=ACCENT, linewidth=2.5, linestyle="-")
    ax.fill(angles_loop, values_loop, color=ACCENT, alpha=0.2)

    # Draw value points
    ax.scatter(angles, values, color=ACCENT_2, s=80, zorder=5, edgecolors=DARK_BG, linewidths=2)

    # Value labels
    for angle, val in zip(angles, values):
        ax.annotate(f"{val}", xy=(angle, val), xytext=(0, 12),
                    textcoords="offset points", ha="center", fontsize=10,
                    fontweight="bold", color=ACCENT_2)

    ax.set_xticks(angles)
    ax.set_xticklabels(labels, fontsize=10, color=TEXT_COLOR)
    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=8, color=TEXT_COLOR, alpha=0.5)
    ax.grid(color=GRID_COLOR, alpha=0.3)
    ax.spines["polar"].set_color(GRID_COLOR)

    ax.set_title(f"Performance — {student_name}", fontsize=14, fontweight="bold",
                 pad=20, color=ACCENT_2, y=1.08)

    fig.tight_layout()
    filepath = os.path.join(CHARTS_DIR, filename)
    fig.savefig(filepath, bbox_inches="tight", facecolor=DARK_BG, edgecolor="none")
    plt.close(fig)
    return filename


def ranking_bar_chart(rankings, semester_label="All Semesters", filename="rankings.png"):
    """Generate a horizontal bar chart of student rankings."""
    fig, ax = plt.subplots(figsize=(8, 5), dpi=120)

    if not rankings:
        ax.text(0.5, 0.5, "No data available", ha="center", va="center",
                fontsize=14, color=TEXT_COLOR, transform=ax.transAxes)
        filepath = os.path.join(CHARTS_DIR, filename)
        fig.savefig(filepath, bbox_inches="tight", facecolor=DARK_BG, edgecolor="none")
        plt.close(fig)
        return filename

    names = [r["student_name"] for r in reversed(rankings)]
    gpas = [r["gpa"] for r in reversed(rankings)]

    colors = []
    for gpa in gpas:
        if gpa >= 3.5:
            colors.append(SUCCESS)
        elif gpa >= 2.5:
            colors.append(ACCENT)
        elif gpa >= 2.0:
            colors.append(WARNING)
        else:
            colors.append(DANGER)

    bars = ax.barh(names, gpas, color=colors, edgecolor=DARK_BG, linewidth=1, height=0.6, alpha=0.85)

    for bar, gpa in zip(bars, gpas):
        ax.text(bar.get_width() + 0.05, bar.get_y() + bar.get_height() / 2,
                f"{gpa:.2f}", va="center", fontsize=10, fontweight="bold", color=TEXT_COLOR)

    ax.set_xlim(0, 4.2)
    ax.set_xlabel("GPA (4.0 Scale)", fontsize=12, fontweight="bold", labelpad=10)
    ax.set_title(f"Class Rankings — {semester_label}", fontsize=14, fontweight="bold", pad=15, color=ACCENT_2)
    ax.grid(axis="x", alpha=0.2)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.tight_layout()
    filepath = os.path.join(CHARTS_DIR, filename)
    fig.savefig(filepath, bbox_inches="tight", facecolor=DARK_BG, edgecolor="none")
    plt.close(fig)
    return filename
