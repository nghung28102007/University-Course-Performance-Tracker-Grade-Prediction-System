# TEC004/05 - University Course Performance Tracker
# User Manual

## 1. Overview
ACP Tracker manages student academic records for Asia University (TEC004/05).
It covers OOP grade management, file import/export, SQLite database, Pandas analytics,
Matplotlib visualizations, ML grade prediction, and web-based data entry.

## 2. Installation
```bash
pip install -r requirements.txt
python database/schema.py   # optional: init DB manually
python app.py
```
Open http://127.0.0.1:5000/login

## 3. User Roles (Access Control)
| Role | Access |
|------|--------|
| Admin | Full access to all pages |
| Instructor | Dashboard, Students, Courses, Analytics, Prediction, Import/Export |
| Student | Own records only on Dashboard, Students, Prediction |

## 4. Features by Deliverable

### SP1 — OOP Grade Management
- `models/person.py`: Abstract Person → Student, Instructor
- `models/course.py`: Course with enrollment
- `models/gradebook.py`: WeightedGrade, CurvedGrade, PassFailGrade (polymorphism)
- Scheme mapping in `config.GRADING_SCHEMES`

### SP2 — File I/O
- **Import**: Import Data page — upload CSV/JSON (batch, multi-threaded)
- **Export**: Download JSON/CSV reports from Import Data page
- **Web Crawl**: Adaptive multi-source crawler (Requests + BeautifulSoup)

### SP3 — SQLite Database
- Normalized schema: Students, Courses, Enrollments, Grades, Assignments, Attendance
- GPA calculation, class rankings, GPA-based at-risk identification

### SP4 — Analytics
- Analytics page: pass/fail rates, correlations, course difficulty
- Pandas engine in `analytics/engine.py`

### SP5 — Visualization
- Dashboard: histogram, rankings bar chart
- Analytics: box plot, course difficulty chart
- Students: GPA trend, performance radar

### SP6 — Grade Prediction
- AI Prediction page: Linear Regression model
- Dashboard: ML At-Risk alerts (predicted final < 60)

### SP7 — Web Automation
- Login form at `/login` (Selenium test target)
- Run: `pytest tests/test_selenium.py -v`

## 5. Running Tests
```bash
pytest tests/test_core.py -v
pytest tests/validate.py
pytest tests/test_selenium.py -v   # requires Chrome + selenium
```

## 6. Research Phases
- **Phase 1**: OOP, DB schema, import module, auth decorators
- **Phase 2**: Analytics pipeline, visualizations, multi-threaded import
- **Phase 3**: ML prediction, at-risk alerts, Selenium tests, this manual
