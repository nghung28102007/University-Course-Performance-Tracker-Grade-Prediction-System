"""
OOP Hierarchy: Abstract Person → Student, Instructor.
Each class supports SQLite persistence via save() and from_db().
"""
from abc import ABC, abstractmethod
from database.connection import execute_query, get_connection


class Person(ABC):
    """Abstract base class for all people in the system."""

    def __init__(self, name, email=None, db_id=None):
        self.id = db_id
        self.name = name
        self.email = email

    @abstractmethod
    def get_role(self):
        """Return the role string for access control."""
        pass

    def display_info(self):
        """Return a formatted info string."""
        return f"[{self.get_role().upper()}] {self.name} ({self.email or 'N/A'})"

    def __repr__(self):
        return f"<{self.__class__.__name__} id={self.id} name='{self.name}'>"


class Student(Person):
    """Student with student_code and date_of_birth."""

    def __init__(self, name, student_code, email=None, date_of_birth=None, db_id=None):
        super().__init__(name, email, db_id)
        self.student_code = student_code
        self.date_of_birth = date_of_birth

    def get_role(self):
        return "student"

    def save(self):
        """Insert or update student in the database."""
        if self.id:
            execute_query(
                "UPDATE Students SET name=?, student_code=?, email=?, date_of_birth=? WHERE id=?",
                (self.name, self.student_code, self.email, self.date_of_birth, self.id),
            )
        else:
            self.id = execute_query(
                "INSERT INTO Students (student_code, name, email, date_of_birth) VALUES (?, ?, ?, ?)",
                (self.student_code, self.name, self.email, self.date_of_birth),
            )
        return self

    @classmethod
    def from_db(cls, student_id):
        """Load a Student from the database by ID."""
        row = execute_query(
            "SELECT * FROM Students WHERE id=?", (student_id,), fetchone=True
        )
        if not row:
            return None
        return cls(
            name=row["name"],
            student_code=row["student_code"],
            email=row["email"],
            date_of_birth=row["date_of_birth"],
            db_id=row["id"],
        )

    @classmethod
    def all(cls):
        """Return all students."""
        rows = execute_query("SELECT * FROM Students ORDER BY name", fetchall=True)
        return [
            cls(
                name=r["name"],
                student_code=r["student_code"],
                email=r["email"],
                date_of_birth=r["date_of_birth"],
                db_id=r["id"],
            )
            for r in rows
        ]


class Instructor(Person):
    """Instructor with department."""

    def __init__(self, name, email=None, department=None, db_id=None):
        super().__init__(name, email, db_id)
        self.department = department

    def get_role(self):
        return "instructor"

    def save(self):
        """Insert or update instructor in the database."""
        if self.id:
            execute_query(
                "UPDATE Instructors SET name=?, email=?, department=? WHERE id=?",
                (self.name, self.email, self.department, self.id),
            )
        else:
            self.id = execute_query(
                "INSERT INTO Instructors (name, email, department) VALUES (?, ?, ?)",
                (self.name, self.email, self.department),
            )
        return self

    @classmethod
    def from_db(cls, instructor_id):
        """Load an Instructor from the database by ID."""
        row = execute_query(
            "SELECT * FROM Instructors WHERE id=?", (instructor_id,), fetchone=True
        )
        if not row:
            return None
        return cls(
            name=row["name"],
            email=row["email"],
            department=row["department"],
            db_id=row["id"],
        )

    @classmethod
    def all(cls):
        """Return all instructors."""
        rows = execute_query("SELECT * FROM Instructors ORDER BY name", fetchall=True)
        return [
            cls(name=r["name"], email=r["email"], department=r["department"], db_id=r["id"])
            for r in rows
        ]
