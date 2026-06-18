"""
GradeBook with polymorphic grading schemes (SP1).
WeightedGrade (default), CurvedGrade, PassFailGrade.
"""
from abc import ABC, abstractmethod
from database.connection import execute_query
import config


class GradeBook(ABC):
    """Abstract grading scheme."""

    @abstractmethod
    def calculate_final_grade(self, enrollment_id, course_id=None):
        """Calculate the final grade for a given enrollment. Returns 0-100 score."""
        pass

    def get_grades(self, enrollment_id):
        """Fetch all grades + assignment info for an enrollment."""
        return execute_query(
            """SELECT g.score, a.type, a.weight, a.max_score, a.name
               FROM Grades g
               JOIN Assignments a ON g.assignment_id = a.id
               WHERE g.enrollment_id = ?""",
            (enrollment_id,), fetchall=True,
        )

    def get_raw_weighted_score(self, enrollment_id):
        """Shared weighted calculation used by multiple schemes."""
        grades = self.get_grades(enrollment_id)
        if not grades:
            return None
        total = 0.0
        weight_sum = 0.0
        for g in grades:
            if g["score"] is not None:
                total += (g["score"] / g["max_score"]) * g["weight"]
                weight_sum += g["weight"]
        if weight_sum == 0:
            return None
        return round((total / weight_sum) * 100, 2)


class WeightedGrade(GradeBook):
    """Default weighted grading: sum of (score/max_score) × weight × 100."""

    def calculate_final_grade(self, enrollment_id, course_id=None):
        return self.get_raw_weighted_score(enrollment_id)


class CurvedGrade(GradeBook):
    """Curved grading: shifts class scores so the mean approaches target_mean."""

    def __init__(self, target_mean=75.0):
        self.target_mean = target_mean

    def calculate_final_grade(self, enrollment_id, course_id=None):
        raw = self.get_raw_weighted_score(enrollment_id)
        if raw is None or not course_id:
            return raw

        enrollments = execute_query(
            "SELECT id FROM Enrollments WHERE course_id = ? AND status = 'active'",
            (course_id,), fetchall=True,
        )
        weighted = WeightedGrade()
        class_scores = [
            weighted.get_raw_weighted_score(e["id"])
            for e in enrollments
        ]
        class_scores = [s for s in class_scores if s is not None]
        if not class_scores:
            return raw

        adjustment = self.target_mean - (sum(class_scores) / len(class_scores))
        return round(min(100.0, max(0.0, raw + adjustment)), 2)


class PassFailGrade(GradeBook):
    """Pass/Fail grading: 100 if weighted score >= threshold, else 0."""

    PASS_THRESHOLD = 60.0

    def calculate_final_grade(self, enrollment_id, course_id=None):
        raw = self.get_raw_weighted_score(enrollment_id)
        if raw is None:
            return None
        return 100.0 if raw >= self.PASS_THRESHOLD else 0.0

    def is_passing(self, enrollment_id):
        raw = self.get_raw_weighted_score(enrollment_id)
        return raw is not None and raw >= self.PASS_THRESHOLD


def get_gradebook_for_course(course_code):
    """Factory: return the correct GradeBook polymorphic instance for a course."""
    scheme = config.GRADING_SCHEMES.get(course_code, "weighted")
    if scheme == "curved":
        return CurvedGrade()
    if scheme == "passfail":
        return PassFailGrade()
    return WeightedGrade()


def calculate_enrollment_grade(enrollment_id, course_code, course_id=None):
    """Calculate final grade using the course's grading scheme."""
    gradebook = get_gradebook_for_course(course_code)
    return gradebook.calculate_final_grade(enrollment_id, course_id)


# Default grading instance
default_gradebook = WeightedGrade()
