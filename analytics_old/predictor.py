"""
AI Grade Predictor using Linear Regression.
Predicts final exam grade from midterm score, assignment average, and attendance rate.
Falls back to weighted heuristic if sklearn is unavailable.
"""
import pandas as pd
from database.connection import get_connection

try:
    from sklearn.linear_model import LinearRegression
    from sklearn.metrics import mean_absolute_error, r2_score
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


class PredictorModel:
    """Predicts final grades using midterm, assignment avg, and attendance."""

    def __init__(self):
        self.model = None
        self.is_trained = False
        self.metrics = {}

    def _build_features(self, semester_id=None):
        """Build feature matrix from database."""
        with get_connection() as conn:
            # Get midterm and assignment scores per enrollment
            query = """
                SELECT
                    e.id AS enrollment_id,
                    e.student_id,
                    c.id AS course_id,
                    c.semester_id,
                    a.type,
                    g.score
                FROM Grades g
                JOIN Enrollments e ON g.enrollment_id = e.id
                JOIN Courses c ON e.course_id = c.id
                JOIN Assignments a ON g.assignment_id = a.id
                WHERE e.status = 'active'
            """
            params = ()
            if semester_id:
                query += " AND c.semester_id = ?"
                params = (semester_id,)

            df = pd.read_sql_query(query, conn, params=params)

            # Get attendance data
            att_query = """
                SELECT
                    e.id AS enrollment_id,
                    COUNT(*) AS total_sessions,
                    SUM(CASE WHEN a.status = 'present' THEN 1
                             WHEN a.status = 'late' THEN 1
                             ELSE 0 END) AS attended
                FROM Attendance a
                JOIN Enrollments e ON a.enrollment_id = e.id
                GROUP BY e.id
            """
            att_df = pd.read_sql_query(att_query, conn)

        if df.empty:
            return pd.DataFrame()

        # Pivot scores by type
        pivoted = df.pivot_table(
            index="enrollment_id",
            columns="type",
            values="score",
            aggfunc="mean",
        ).reset_index()

        # Merge attendance
        if not att_df.empty:
            att_df["attendance_rate"] = (att_df["attended"] / att_df["total_sessions"] * 100).round(1)
            pivoted = pivoted.merge(
                att_df[["enrollment_id", "attendance_rate"]],
                on="enrollment_id",
                how="left",
            )
        else:
            pivoted["attendance_rate"] = 80.0  # default

        pivoted = pivoted.fillna(0)
        return pivoted

    def train(self, semester_id=None):
        """Train the linear regression model on historical data."""
        features_df = self._build_features(semester_id)
        if features_df.empty or "final" not in features_df.columns:
            return {"error": "Insufficient data for training"}

        # Features: midterm, assignment avg, attendance
        feature_cols = []
        if "midterm" in features_df.columns:
            feature_cols.append("midterm")
        if "assignment" in features_df.columns:
            feature_cols.append("assignment")
        if "attendance_rate" in features_df.columns:
            feature_cols.append("attendance_rate")

        if not feature_cols:
            return {"error": "No features available"}

        X = features_df[feature_cols].values
        y = features_df["final"].values

        if HAS_SKLEARN:
            self.model = LinearRegression()
            self.model.fit(X, y)

            predictions = self.model.predict(X)
            self.metrics = {
                "mae": round(mean_absolute_error(y, predictions), 2),
                "r2": round(r2_score(y, predictions), 4),
                "samples": len(y),
                "features": feature_cols,
                "coefficients": {
                    col: round(coef, 4)
                    for col, coef in zip(feature_cols, self.model.coef_)
                },
                "intercept": round(self.model.intercept_, 4),
            }
        else:
            # Fallback: store averages for heuristic
            self.model = {
                "feature_cols": feature_cols,
                "means": {col: features_df[col].mean() for col in feature_cols},
                "target_mean": features_df["final"].mean(),
                "correlation": {
                    col: features_df[col].corr(features_df["final"])
                    for col in feature_cols
                },
            }
            self.metrics = {
                "method": "heuristic_fallback",
                "samples": len(y),
                "features": feature_cols,
            }

        self.is_trained = True
        return self.metrics

    def predict(self, midterm_score, assignment_avg, attendance_rate):
        """Predict final grade for given inputs."""
        if not self.is_trained:
            return {"error": "Model not trained. Call train() first."}

        if HAS_SKLEARN:
            features = [[midterm_score, assignment_avg, attendance_rate]]
            predicted = self.model.predict(features)[0]
            predicted = max(0, min(100, round(predicted, 2)))
            return {
                "predicted_final": predicted,
                "inputs": {
                    "midterm": midterm_score,
                    "assignment_avg": assignment_avg,
                    "attendance_rate": attendance_rate,
                },
                "confidence": self.metrics.get("r2", 0),
            }
        else:
            # Weighted heuristic fallback
            predicted = (midterm_score * 0.4 + assignment_avg * 0.35 + attendance_rate * 0.25)
            predicted = max(0, min(100, round(predicted, 2)))
            return {
                "predicted_final": predicted,
                "inputs": {
                    "midterm": midterm_score,
                    "assignment_avg": assignment_avg,
                    "attendance_rate": attendance_rate,
                },
                "method": "heuristic",
            }

    def predict_for_student(self, student_id, course_id):
        """Predict final grade for a specific student in a specific course."""
        with get_connection() as conn:
            # Get enrollment
            enrollment = conn.execute(
                "SELECT id FROM Enrollments WHERE student_id=? AND course_id=?",
                (student_id, course_id),
            ).fetchone()

            if not enrollment:
                return {"error": "Student not enrolled in this course"}

            # Get midterm score
            midterm = conn.execute(
                """SELECT g.score FROM Grades g
                   JOIN Assignments a ON g.assignment_id = a.id
                   WHERE g.enrollment_id = ? AND a.type = 'midterm'""",
                (enrollment["id"],),
            ).fetchone()

            # Get assignment score
            assignment = conn.execute(
                """SELECT g.score FROM Grades g
                   JOIN Assignments a ON g.assignment_id = a.id
                   WHERE g.enrollment_id = ? AND a.type = 'assignment'""",
                (enrollment["id"],),
            ).fetchone()

            # Get attendance
            att = conn.execute(
                """SELECT COUNT(*) as total,
                          SUM(CASE WHEN status IN ('present','late') THEN 1 ELSE 0 END) as attended
                   FROM Attendance WHERE enrollment_id = ?""",
                (enrollment["id"],),
            ).fetchone()

        midterm_score = midterm["score"] if midterm else 50
        assignment_avg = assignment["score"] if assignment else 50
        attendance_rate = round((att["attended"] / att["total"]) * 100, 1) if att and att["total"] > 0 else 80

        return self.predict(midterm_score, assignment_avg, attendance_rate)


# Singleton predictor
predictor = PredictorModel()
