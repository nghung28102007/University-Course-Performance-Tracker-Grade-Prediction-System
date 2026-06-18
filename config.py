"""
TEC004/05 - University Performance Tracker Configuration
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "university.db")

# Default Weighted Grading Scheme
ASSIGNMENT_WEIGHT = 0.30
MIDTERM_WEIGHT = 0.30
FINAL_WEIGHT = 0.40

# GPA Scale (4.0)
GPA_SCALE = {
    (90, 100): 4.0,
    (85, 89):  3.7,
    (80, 84):  3.3,
    (75, 79):  3.0,
    (70, 74):  2.7,
    (65, 69):  2.3,
    (60, 64):  2.0,
    (55, 59):  1.7,
    (50, 54):  1.3,
    (40, 49):  1.0,
    (0, 39):   0.0,
}

# Scale-10 conversion (Vietnamese)
def score_to_gpa4(score):
    """Convert a 0-100 score to 4.0 GPA point."""
    for (low, high), gpa in GPA_SCALE.items():
        if low <= score <= high:
            return gpa
    return 0.0

def score_to_scale10(score):
    """Convert a 0-100 score to Vietnamese Scale 10."""
    return round(score / 10, 1)

# Grading scheme per course (SP1 polymorphism: weighted | curved | passfail)
GRADING_SCHEMES = {
    "CS101": "weighted",
    "MATH101": "curved",
    "PE101": "passfail",  # demo mapping if course added
    "SE101": "passfail",
}

# Flask
SECRET_KEY = os.environ.get("SECRET_KEY", "hung-acp-2026-secret")
HOST = "127.0.0.1"
PORT = 5000
