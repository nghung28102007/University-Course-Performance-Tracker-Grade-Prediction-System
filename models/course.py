"""
Course model with enrollment management.
"""
from database.connection import execute_query


class Course:
    """Represents a university course with enrollment capabilities."""

    def __init__(self, course_code, name, credits, semester_id, instructor_id=None, db_id=None):
        self.id = db_id
        self.course_code = course_code
        self.name = name
        self.credits = credits
        self.semester_id = semester_id
        self.instructor_id = instructor_id

    def save(self):
        """Insert or update course."""
        if self.id:
            execute_query(
                "UPDATE Courses SET course_code=?, name=?, credits=?, semester_id=?, instructor_id=? WHERE id=?",
                (self.course_code, self.name, self.credits, self.semester_id, self.instructor_id, self.id),
            )
        else:
            self.id = execute_query(
                "INSERT INTO Courses (course_code, name, credits, semester_id, instructor_id) VALUES (?, ?, ?, ?, ?)",
                (self.course_code, self.name, self.credits, self.semester_id, self.instructor_id),
            )
        return self

    @classmethod
    def from_db(cls, course_id):
        """Load a Course from the database."""
        row = execute_query("SELECT * FROM Courses WHERE id=?", (course_id,), fetchone=True)
        if not row:
            return None
        return cls(
            course_code=row["course_code"],
            name=row["name"],
            credits=row["credits"],
            semester_id=row["semester_id"],
            instructor_id=row["instructor_id"],
            db_id=row["id"],
        )

    @classmethod
    def all(cls, semester_id=None):
        """Return all courses, optionally filtered by semester."""
        if semester_id:
            rows = execute_query(
                "SELECT * FROM Courses WHERE semester_id=? ORDER BY course_code",
                (semester_id,), fetchall=True,
            )
        else:
            rows = execute_query("SELECT * FROM Courses ORDER BY course_code", fetchall=True)
        return [
            cls(
                course_code=r["course_code"], name=r["name"], credits=r["credits"],
                semester_id=r["semester_id"], instructor_id=r["instructor_id"], db_id=r["id"],
            )
            for r in rows
        ]

    def enroll_student(self, student_id):
        """Enroll a student in this course."""
        return execute_query(
            "INSERT OR IGNORE INTO Enrollments (student_id, course_id, enrolled_date, status) VALUES (?, ?, date('now'), 'active')",
            (student_id, self.id),
        )

    def drop_student(self, student_id):
        """Drop a student from this course."""
        execute_query(
            "UPDATE Enrollments SET status='dropped' WHERE student_id=? AND course_id=?",
            (student_id, self.id),
        )

    def get_enrolled_students(self):
        """Return all actively enrolled student rows."""
        return execute_query(
            """SELECT s.* FROM Students s
               JOIN Enrollments e ON s.id = e.student_id
               WHERE e.course_id = ? AND e.status = 'active'
               ORDER BY s.name""",
            (self.id,), fetchall=True,
        )

    def get_semester_name(self):
        """Get the semester name for this course."""
        row = execute_query("SELECT name FROM Semesters WHERE id=?", (self.semester_id,), fetchone=True)
        return row["name"] if row else "Unknown"

    def __repr__(self):
        return f"<Course {self.course_code}: {self.name}>"
