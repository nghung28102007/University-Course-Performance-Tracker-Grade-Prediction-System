"""
Database schema definition and seed data for the University Performance Tracker.
All tables are normalized. Seed data provides realistic Asia University content.
"""
from database.connection import get_connection


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS Semesters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    year INTEGER NOT NULL,
    start_date TEXT,
    end_date TEXT
);

CREATE TABLE IF NOT EXISTS Students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    email TEXT,
    date_of_birth TEXT,
    role TEXT DEFAULT 'student'
);

CREATE TABLE IF NOT EXISTS Instructors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT,
    department TEXT,
    role TEXT DEFAULT 'instructor'
);

CREATE TABLE IF NOT EXISTS Courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    credits INTEGER NOT NULL,
    semester_id INTEGER NOT NULL,
    instructor_id INTEGER,
    FOREIGN KEY (semester_id) REFERENCES Semesters(id),
    FOREIGN KEY (instructor_id) REFERENCES Instructors(id)
);

CREATE TABLE IF NOT EXISTS Enrollments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    enrolled_date TEXT,
    status TEXT DEFAULT 'active',
    UNIQUE(student_id, course_id),
    FOREIGN KEY (student_id) REFERENCES Students(id),
    FOREIGN KEY (course_id) REFERENCES Courses(id)
);

CREATE TABLE IF NOT EXISTS Assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('assignment', 'midterm', 'final')),
    max_score REAL DEFAULT 100,
    weight REAL NOT NULL,
    FOREIGN KEY (course_id) REFERENCES Courses(id)
);

CREATE TABLE IF NOT EXISTS Grades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    enrollment_id INTEGER NOT NULL,
    assignment_id INTEGER NOT NULL,
    score REAL,
    graded_date TEXT,
    UNIQUE(enrollment_id, assignment_id),
    FOREIGN KEY (enrollment_id) REFERENCES Enrollments(id),
    FOREIGN KEY (assignment_id) REFERENCES Assignments(id)
);

CREATE TABLE IF NOT EXISTS Attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    enrollment_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    status TEXT DEFAULT 'present' CHECK(status IN ('present', 'absent', 'late')),
    FOREIGN KEY (enrollment_id) REFERENCES Enrollments(id)
);
"""


def init_db():
    """Create all tables."""
    with get_connection() as conn:
        conn.executescript(SCHEMA_SQL)
    print("[DB] Schema initialized.")


def seed_data():
    """Insert realistic seed data for Asia University demo."""
    with get_connection() as conn:
        # Check if already seeded
        count = conn.execute("SELECT COUNT(*) FROM Semesters").fetchone()[0]
        if count > 0:
            print("[DB] Already seeded, skipping.")
            return

        # --- Semesters ---
        semesters = [
            ("Semester 1", 2025, "2025-09-01", "2026-01-15"),
            ("Semester 2", 2025, "2026-02-10", "2026-06-20"),
            ("Semester 3", 2025, "2026-07-01", "2026-08-30"),
        ]
        conn.executemany(
            "INSERT INTO Semesters (name, year, start_date, end_date) VALUES (?, ?, ?, ?)",
            semesters,
        )

        # --- Instructors ---
        instructors = [
            ("Dr. Nguyen Van Minh", "minh.nv@au.edu.vn", "Computer Science"),
            ("Dr. Tran Thi Lan", "lan.tt@au.edu.vn", "Mathematics"),
            ("Prof. Le Hoang Duc", "duc.lh@au.edu.vn", "Information Technology"),
            ("Dr. Pham Quoc Bao", "bao.pq@au.edu.vn", "Software Engineering"),
        ]
        conn.executemany(
            "INSERT INTO Instructors (name, email, department) VALUES (?, ?, ?)",
            instructors,
        )

        # --- Students ---
        students = [
            ("AU2024001", "Gia Hung", "hung.gia@au.edu.vn", "2004-03-15"),
            ("AU2024002", "Minh Tuan", "tuan.minh@au.edu.vn", "2004-07-22"),
            ("AU2024003", "Thanh Ngan", "ngan.thanh@au.edu.vn", "2004-01-10"),
            ("AU2024004", "Hoang Nam", "nam.hoang@au.edu.vn", "2004-11-05"),
            ("AU2024005", "Thu Ha", "ha.thu@au.edu.vn", "2004-06-18"),
            ("AU2024006", "Duc Anh", "anh.duc@au.edu.vn", "2004-09-30"),
            ("AU2024007", "Ngoc Linh", "linh.ngoc@au.edu.vn", "2004-04-25"),
            ("AU2024008", "Quang Huy", "huy.quang@au.edu.vn", "2004-12-08"),
        ]
        conn.executemany(
            "INSERT INTO Students (student_code, name, email, date_of_birth) VALUES (?, ?, ?, ?)",
            students,
        )

        # --- Courses (4 per semester = 12 total) ---
        courses = [
            # Semester 1
            ("CS101", "Introduction to Programming", 3, 1, 1),
            ("MATH101", "Calculus I", 3, 1, 2),
            ("IT101", "Computer Fundamentals", 3, 1, 3),
            ("SE101", "Software Engineering Basics", 3, 1, 4),
            # Semester 2
            ("CS201", "Data Structures & Algorithms", 4, 2, 1),
            ("MATH201", "Linear Algebra", 3, 2, 2),
            ("IT201", "Database Systems", 3, 2, 3),
            ("SE201", "OOP with Python", 4, 2, 4),
            # Semester 3
            ("CS301", "Web Development", 3, 3, 3),
            ("MATH301", "Probability & Statistics", 3, 3, 2),
            ("IT301", "Network Security", 3, 3, 1),
            ("SE301", "Software Project Management", 3, 3, 4),
        ]
        conn.executemany(
            "INSERT INTO Courses (course_code, name, credits, semester_id, instructor_id) VALUES (?, ?, ?, ?, ?)",
            courses,
        )

        # --- Assignments (3 per course: assignment=0.30, midterm=0.30, final=0.40) ---
        for course_id in range(1, 13):
            assignments = [
                (course_id, "Coursework", "assignment", 100, 0.30),
                (course_id, "Midterm Exam", "midterm", 100, 0.30),
                (course_id, "Final Exam", "final", 100, 0.40),
            ]
            conn.executemany(
                "INSERT INTO Assignments (course_id, name, type, max_score, weight) VALUES (?, ?, ?, ?, ?)",
                assignments,
            )

        # --- Enrollments (all 8 students in all 12 courses) ---
        for student_id in range(1, 9):
            for course_id in range(1, 13):
                conn.execute(
                    "INSERT INTO Enrollments (student_id, course_id, enrolled_date, status) VALUES (?, ?, '2025-09-01', 'active')",
                    (student_id, course_id),
                )

        # --- Grades (realistic, varied scores) ---
        import random
        random.seed(42)  # Reproducible

        # Student performance profiles (base score range)
        profiles = {
            1: (82, 98),   # Gia Hung - high performer
            2: (70, 88),   # Minh Tuan - good
            3: (75, 92),   # Thanh Ngan - strong
            4: (55, 75),   # Hoang Nam - at-risk
            5: (65, 85),   # Thu Ha - average
            6: (78, 95),   # Duc Anh - strong
            7: (60, 80),   # Ngoc Linh - below average
            8: (45, 70),   # Quang Huy - at-risk
        }

        enrollment_id = 1
        for student_id in range(1, 9):
            low, high = profiles[student_id]
            for course_id in range(1, 13):
                # 3 assignments per course
                for assignment_offset in range(3):
                    assignment_id = (course_id - 1) * 3 + assignment_offset + 1
                    # Vary scores slightly per assignment type
                    score = random.randint(low, high)
                    # Final exams tend to be slightly lower
                    if assignment_offset == 2:
                        score = max(0, score - random.randint(0, 8))
                    conn.execute(
                        "INSERT INTO Grades (enrollment_id, assignment_id, score, graded_date) VALUES (?, ?, ?, '2026-01-10')",
                        (enrollment_id, assignment_id, score),
                    )
                enrollment_id += 1

        # --- Attendance (15 sessions per course, varied attendance) ---
        import datetime
        enrollment_id = 1
        for student_id in range(1, 9):
            for course_id in range(1, 13):
                base_date = datetime.date(2025, 9, 15)
                attend_rate = 0.90 if profiles[student_id][0] > 65 else 0.70
                for week in range(15):
                    date = base_date + datetime.timedelta(weeks=week)
                    roll = random.random()
                    if roll < attend_rate:
                        status = "present"
                    elif roll < attend_rate + 0.05:
                        status = "late"
                    else:
                        status = "absent"
                    conn.execute(
                        "INSERT INTO Attendance (enrollment_id, date, status) VALUES (?, ?, ?)",
                        (enrollment_id, date.isoformat(), status),
                    )
                enrollment_id += 1

    print("[DB] Seed data inserted: 8 students, 12 courses, 3 semesters, 288 grades, 1440 attendance records.")


if __name__ == "__main__":
    init_db()
    seed_data()
