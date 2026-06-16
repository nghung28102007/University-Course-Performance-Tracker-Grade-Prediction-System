"""
GradeBook with polymorphic grading schemes.
WeightedGrade is the default (Assignment 30%, Midterm 30%, Final 40%).
"""
from abc import ABC, abstractmethod
from database.connection import execute_query


class GradeBook(ABC):
    """Abstract grading scheme."""

    @abstractmethod
    def calculate_final_grade(self, enrollment_id):
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


class WeightedGrade(GradeBook):
    """Default weighted grading: sum of (score/max_score) × weight × 100."""

    def calculate_final_grade(self, enrollment_id):
        """Calculate weighted final grade on 0-100 scale."""
        grades = self.get_grades(enrollment_id)
        if not grades:
            return None

        total = 0.0
        weight_sum = 0.0
        for g in grades:
            if g["score"] is not None:
                normalized = (g["score"] / g["max_score"]) * g["weight"]
                total += normalized
                weight_sum += g["weight"]

        if weight_sum == 0:
            return None

        # Normalize to 100 scale (weights should sum to 1.0)
        return round((total / weight_sum) * 100, 2)


class SimpleAverage(GradeBook):
    """Alternative: unweighted average of all scores."""

    def calculate_final_grade(self, enrollment_id):
        grades = self.get_grades(enrollment_id)
        if not grades:
            return None
        scores = [g["score"] for g in grades if g["score"] is not None]
        if not scores:
            return None
        return round(sum(scores) / len(scores), 2)


# Default grading instance
default_gradebook = WeightedGrade()
