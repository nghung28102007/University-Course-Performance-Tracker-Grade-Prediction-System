import os
import sqlite3
import requests
from bs4 import BeautifulSoup
import random
import logging

# Cấu hình logging để ghi nhận lỗi thay vì làm sập ứng dụng
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# =============================================================================
# CẤU HÌNH DANH SÁCH NGUỒN DỮ LIỆU ƯU TIÊN
# -----------------------------------------------------------------------------
# Team chỉnh sửa mảng PRIORITY_DATA_SOURCES bên dưới:
#   - Thêm / xóa / đổi thứ tự URL theo mức ưu tiên (index thấp = thử trước).
#   - Phần tử CUỐI CÙNG phải là nguồn Mock (cloud hoặc sentinel "local://mock").
#   - Các URL phía trên là nguồn Production thật (bảng điểm công khai, raw GitHub…).
#   - Timeout mỗi nguồn Internet: 4 giây (hằng số CRAWL_TIMEOUT_SECONDS).
# =============================================================================
CRAWL_TIMEOUT_SECONDS = 4
WEB_CRAWL_TIMEOUT = 5
LIVE_WEB_CRAWL_URL = "https://web-mock-1000-data-cua-ban.onrender.com"
MOCK_SENTINEL_LOCAL = "local://mock"

PRIORITY_DATA_SOURCES = [
    LIVE_WEB_CRAWL_URL,
    "https://mock-student-grades.onrender.com",
    MOCK_SENTINEL_LOCAL,
]


def _resolve_db_path(db_path=None):
    """Trả về đường dẫn tuyệt đối đến file database SQLite.

    Args:
        db_path (str, optional): Đường dẫn tùy chỉnh. Nếu None, dùng config.DB_PATH
                                 hoặc fallback về thư mục gốc dự án.

    Returns:
        str: Đường dẫn đến file university.db.
    """
    if db_path:
        return db_path
    try:
        import config
        return config.DB_PATH
    except ImportError:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "university.db")


def ensure_crawl_grades_table(db_path=None):
    """
    Bảng CrawlGrades lưu dữ liệu phẳng từ crawler (student_id, course_id).
  Bảng Grades chính của app dùng schema chuẩn hóa (enrollment_id, assignment_id).
    """
    db_path = _resolve_db_path(db_path)
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS CrawlGrades (
            student_id TEXT NOT NULL,
            course_id TEXT NOT NULL,
            midterm_score REAL,
            attendance_rate REAL,
            assignment_rate REAL,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (student_id, course_id)
        )
    """)
    conn.commit()
    conn.close()


def setup_database(db_path="university.db"):
    """
    Tạo bảng cơ sở dữ liệu nếu chưa tồn tại.
    Sử dụng (student_id, course_id) làm Khóa chính hợp nhất (Composite Primary Key).
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Grades (
            student_id TEXT,
            course_id TEXT,
            midterm_score REAL,
            attendance_rate REAL,
            assignment_rate REAL,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (student_id, course_id)
        )
    """)
    conn.commit()
    conn.close()

def generate_random_mock_data(num_samples=None, courses=None):
    """Tự sinh dữ liệu điểm ngẫu nhiên khi mọi nguồn mạng đều thất bại."""
    if num_samples is None:
        num_samples = random.randint(40, 50)
        
    uni_prefixes = ["HUST", "NEU", "FTU", "VNU", "BKA", "UEH", "RMIT", "FPT", "UIT", "USSH", "UEL", "HCMUT", "HCMUS"]
    
    subject_pool = [
        "CS201", "CS301", "SE102",  # IT
        "ECO101", "FIN201", "MKT301", # Eco/Biz
        "MED101", "ANA202", "PHA301", # Med/Phar
        "LAW101", "CIV202", "CRI301", # Law
        "ENG101", "MEC201", "ELE302", # Engineering
        "ART101", "HIS201", "PHI301", # Arts
        "PHY101", "CHE102", "BIO201", # Science
        "MATH201", "STAT101", "ALG202" # Math
    ]
    
    records = []
    seen_combinations = set()
    
    while len(records) < num_samples:
        prefix = random.choice(uni_prefixes)
        year = random.choice(["2020", "2021", "2022", "2023", "2024"])
        student_id_num = str(random.randint(1, 9999)).zfill(4)
        student_id = f"{prefix}{year}{student_id_num}"
        
        course = random.choice(courses if courses else subject_pool)
        
        combo = (student_id, course)
        if combo in seen_combinations:
            continue
            
        seen_combinations.add(combo)
        
        records.append((
            student_id,
            course,
            round(random.uniform(40.0, 95.0), 1),
            round(random.uniform(0.60, 0.99), 2),
            round(random.uniform(0.50, 0.98), 2),
        ))
        
    return records


def get_fallback_mock_data():
    """
    Trả về dữ liệu giả lập dự phòng để hệ thống hoạt động ổn định khi server cào bị lỗi hoặc 404.
    """
    return [
        ("AU2024001", "CS201", 85.0, 0.95, 0.90),
        ("AU2024002", "CS201", 72.0, 0.88, 0.82),
        ("AU2024003", "CS201", 90.0, 0.98, 0.95),
        ("AU2024004", "CS201", 50.0, 0.72, 0.65),
        ("AU2024005", "CS201", 68.0, 0.85, 0.78),
        ("AU2024006", "CS201", 80.0, 0.92, 0.85),
        ("AU2024007", "CS201", 55.0, 0.78, 0.60),
        ("AU2024008", "CS201", 42.0, 0.65, 0.55),
        ("AU2024001", "MATH201", 78.0, 0.90, 0.85),
        ("AU2024002", "MATH201", 65.0, 0.80, 0.75),
        ("AU2024003", "MATH201", 92.0, 0.98, 0.92),
        ("AU2024004", "MATH201", 48.0, 0.70, 0.62),
        ("AU2024005", "MATH201", 70.0, 0.88, 0.80),
        ("AU2024006", "MATH201", 85.0, 0.94, 0.90),
        ("AU2024007", "MATH201", 58.0, 0.80, 0.65),
        ("AU2024008", "MATH201", 45.0, 0.72, 0.50),
    ]

def parse_html_content(html_text):
    """Phân tích nội dung HTML và trích xuất dữ liệu sinh viên."""
    soup = BeautifulSoup(html_text, 'html.parser')
    table = soup.find('table', id='student-grade-table')
    if not table:
        table = soup.find('table', id='grades-table')
    if table:
        tbody = table.find('tbody')
        rows = tbody.find_all('tr') if tbody else table.find_all('tr')[1:]
    else:
        rows = soup.find_all('tr')[1:]

    crawled_data = []
    for row in rows:
        cols = row.find_all('td')
        if len(cols) >= 5:
            try:
                student_id = cols[0].text.strip()
                course_id = cols[1].text.strip()
                midterm_score = float(cols[2].text.strip())
                
                att_text = cols[3].text.strip().replace('%', '')
                attendance_rate = float(att_text) / 100.0 if float(att_text) > 1 else float(att_text)
                
                ass_text = cols[4].text.strip().replace('%', '')
                assignment_rate = float(ass_text) / 100.0 if float(ass_text) > 1 else float(ass_text)
                
                crawled_data.append((student_id, course_id, midterm_score, attendance_rate, assignment_rate))
            except ValueError as ve:
                logger.warning(f"Bỏ qua dữ liệu lỗi định dạng: {cols} - Chi tiết: {ve}")
                continue
    return crawled_data

def _is_mock_source(target_url, index):
    """Xác định nguồn cuối danh sách hoặc sentinel local://mock."""
    return index == len(PRIORITY_DATA_SOURCES) - 1 or target_url == MOCK_SENTINEL_LOCAL


def activate_mock_fallback(use_random=False):
    """
    Kích hoạt phương án dự phòng cuối cùng: sinh ngẫu nhiên -> file HTML cục bộ -> dữ liệu tĩnh.
    """
    if use_random:
        random_data = generate_random_mock_data()
        logger.info(f"Mock fallback: sinh {len(random_data)} bản ghi ngẫu nhiên.")
        return random_data

    local_data = get_local_file_data()
    if local_data:
        logger.info(f"Mock fallback: {len(local_data)} bản ghi từ file HTML cục bộ.")
        return local_data

    static_data = get_fallback_mock_data()
    logger.info(f"Mock fallback: {len(static_data)} bản ghi tĩnh.")
    return static_data


def get_local_file_data():
    """Đọc và phân tích file HTML cục bộ trong thư mục data làm nguồn cào dự phòng."""
    local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "mock_student_grades.html")
    if os.path.exists(local_path):
        logger.info(f"Đang cào dữ liệu từ file HTML cục bộ: {local_path}")
        try:
            with open(local_path, "r", encoding="utf-8") as f:
                html_content = f.read()
            crawled_data = parse_html_content(html_content)
            if crawled_data:
                logger.info(f"Cào thành công {len(crawled_data)} bản ghi từ file HTML cục bộ.")
                return crawled_data
        except Exception as file_err:
            logger.error(f"Lỗi khi đọc và cào file HTML cục bộ: {file_err}")
    return None

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0",
]


def _fetch_and_parse_url(target_url):
    """Tải một URL và parse HTML; trả về list bản ghi hoặc None nếu thất bại."""
    headers = {"User-Agent": random.choice(_USER_AGENTS)}
    response = requests.get(target_url, headers=headers, timeout=CRAWL_TIMEOUT_SECONDS)

    if response.status_code != 200:
        logger.warning(f"HTTP {response.status_code} từ {target_url} — chuyển nguồn tiếp theo.")
        return None

    crawled_data = parse_html_content(response.text)
    if not crawled_data:
        logger.warning(f"Cấu trúc HTML không hợp lệ hoặc rỗng tại {target_url} — chuyển nguồn tiếp theo.")
        return None

    return crawled_data


def execute_adaptive_crawl(url_list=None):
    """
    Quét thích ứng qua danh sách nguồn ưu tiên; chỉ dùng Mock khi mọi nguồn trước đó thất bại.

    Returns:
        tuple: (crawled_data, data_source, source_label)
            data_source: "Production-Real" | "Backup-Mock"
            source_label: URL hoặc mô tả nguồn đã dùng thành công
    """
    sources = url_list if url_list is not None else PRIORITY_DATA_SOURCES
    crawled_data = []
    data_source = "Backup-Mock"
    source_label = "none"

    for index, target_url in enumerate(sources):
        is_mock_slot = _is_mock_source(target_url, index)

        try:
            if target_url == MOCK_SENTINEL_LOCAL:
                crawled_data = activate_mock_fallback(use_random=True)
                if crawled_data:
                    data_source = "Backup-Mock"
                    source_label = MOCK_SENTINEL_LOCAL
                    break
                continue

            crawled_data = _fetch_and_parse_url(target_url)
            if crawled_data:
                data_source = "Backup-Mock" if is_mock_slot else "Production-Real"
                source_label = target_url
                logger.info(
                    f"Cào thành công {len(crawled_data)} bản ghi từ "
                    f"{'[MOCK] ' if is_mock_slot else ''}{target_url}"
                )
                break

        except requests.exceptions.RequestException as net_err:
            logger.warning(f"Lỗi mạng/timeout ({CRAWL_TIMEOUT_SECONDS}s) tại {target_url}: {net_err}")
        except Exception as parse_err:
            logger.warning(f"Lỗi parse BS4 tại {target_url}: {parse_err}")

    if not crawled_data:
        logger.warning("Tất cả nguồn trong danh sách thất bại — kích hoạt Mock fallback cuối cùng.")
        crawled_data = activate_mock_fallback(use_random=True)
        data_source = "Backup-Mock"
        source_label = "local-fallback"

    return crawled_data, data_source, source_label


def execute_web_crawl(target_url=None):
    """
    Cào dữ liệu từ web server thật (mặc định 1000 bản ghi ngẫu nhiên).
    Dùng Fake User-Agent, timeout=5s, bẫy lỗi mạng; fallback adaptive nếu thất bại.
    """
    url = target_url or LIVE_WEB_CRAWL_URL
    headers = {"User-Agent": random.choice(_USER_AGENTS)}

    try:
        response = requests.get(url, headers=headers, timeout=WEB_CRAWL_TIMEOUT)
        if response.status_code == 200:
            crawled_data = parse_html_content(response.text)
            if crawled_data:
                logger.info(f"Cào thành công {len(crawled_data)} bản ghi từ {url}")
                return crawled_data
        logger.warning(f"HTTP {response.status_code} hoặc bảng rỗng tại {url}")
    except requests.exceptions.RequestException as net_err:
        logger.error(f"Lỗi mạng/timeout ({WEB_CRAWL_TIMEOUT}s) khi cào {url}: {net_err}")
    except Exception as parse_err:
        logger.error(f"Lỗi parse HTML tại {url}: {parse_err}")

    data, _, _ = execute_adaptive_crawl()
    return data



def sync_crawled_data_to_db(data, db_path=None):
    """
    Đồng bộ dữ liệu cào vào SQLite (bảng CrawlGrades) bằng INSERT OR REPLACE / ON CONFLICT.
    """
    if not data:
        return 0

    db_path = _resolve_db_path(db_path)
    ensure_crawl_grades_table(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    upsert_query = """
        INSERT INTO CrawlGrades (student_id, course_id, midterm_score, attendance_rate, assignment_rate, last_updated)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(student_id, course_id) DO UPDATE SET
            midterm_score = excluded.midterm_score,
            attendance_rate = excluded.attendance_rate,
            assignment_rate = excluded.assignment_rate,
            last_updated = CURRENT_TIMESTAMP
    """

    try:
        cursor.executemany(upsert_query, data)
        conn.commit()
        logger.info(f"Đã đồng bộ/ghi đè an toàn {len(data)} bản ghi vào CrawlGrades.")
        return len(data)
    except sqlite3.Error as e:
        logger.error(f"Lỗi Database Transaction: {e}")
        return 0
    finally:
        conn.close()


def sync_to_sqlite(crawled_data, db_path="university.db"):
    """Alias tương thích ngược — ghi vào CrawlGrades."""
    return sync_crawled_data_to_db(crawled_data, db_path)


def sync_crawl_to_normalized(crawled_data):
    """
    Đồng bộ dữ liệu cào (flat) vào schema chuẩn của ACP Tracker
    (Students / Courses / Enrollments / Assignments / Grades).
    """
    if not crawled_data:
        return 0

    try:
        from database.connection import get_connection
    except ImportError:
        logger.warning("Không tìm thấy database.connection — dùng sync_crawled_data_to_db thay thế.")
        sync_crawled_data_to_db(crawled_data)
        return len(crawled_data)

    updated = 0
    with get_connection() as conn:
        for student_code, course_code, midterm, _att_rate, assign_rate in crawled_data:
            # Kiểm tra và tự động tạo Student, Course, Enrollment nếu chưa có
            enr = conn.execute(
                """
                SELECT e.id AS enrollment_id, c.id AS course_id
                FROM Enrollments e
                JOIN Students s ON e.student_id = s.id
                JOIN Courses c ON e.course_id = c.id
                WHERE s.student_code = ? AND c.course_code = ?
                """,
                (student_code, course_code),
            ).fetchone()

            if not enr:
                # 1. Kiểm tra/Tạo Student
                stu = conn.execute("SELECT id FROM Students WHERE student_code = ?", (student_code,)).fetchone()
                if not stu:
                    import random
                    ho_list = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan", "Vũ", "Võ", "Đặng", "Bùi", "Đỗ", "Hồ", "Ngô", "Dương", "Lý"]
                    ten_dem_list = ["Văn", "Thị", "Hữu", "Minh", "Ngọc", "Thu", "Thanh", "Đức", "Xuân", "Hải", "Tuấn", "Hoài", "Quang"]
                    ten_list = ["Anh", "Bảo", "Dũng", "Hà", "Hải", "Hùng", "Hương", "Linh", "Nga", "Phong", "Phú", "Phương", "Sơn", "Trang", "Trí", "Tài", "Tâm", "Tú"]
                    fake_name = f"{random.choice(ho_list)} {random.choice(ten_dem_list)} {random.choice(ten_list)}"
                    conn.execute(
                        "INSERT INTO Students (student_code, name, email, date_of_birth) VALUES (?, ?, ?, ?)",
                        (student_code, fake_name, f"{student_code.lower()}@au.edu.vn", f"{random.randint(2000, 2005)}-0{random.randint(1, 9)}-1{random.randint(0, 9)}")
                    )
                    student_db_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                else:
                    student_db_id = stu["id"]

                # 2. Kiểm tra/Tạo Course
                crs = conn.execute("SELECT id FROM Courses WHERE course_code = ?", (course_code,)).fetchone()
                if not crs:
                    sem_id = conn.execute("SELECT id FROM Semesters ORDER BY id DESC LIMIT 1").fetchone()
                    sem_id = sem_id["id"] if sem_id else 1
                    conn.execute(
                        "INSERT INTO Courses (course_code, name, credits, semester_id) VALUES (?, ?, ?, ?)",
                        (course_code, f"Môn {course_code}", 3, sem_id)
                    )
                    course_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                    # Tạo luôn Assignment mặc định cho Course mới
                    conn.executemany(
                        "INSERT INTO Assignments (course_id, name, type, weight) VALUES (?, ?, ?, ?)",
                        [
                            (course_id, "Giữa kỳ", "midterm", 0.4),
                            (course_id, "Bài tập", "assignment", 0.1),
                            (course_id, "Cuối kỳ", "final", 0.5)
                        ]
                    )
                else:
                    course_id = crs["id"]

                # 3. Tạo Enrollment
                try:
                    conn.execute(
                        "INSERT INTO Enrollments (student_id, course_id, enrolled_date, status) VALUES (?, ?, date('now'), 'active')",
                        (student_db_id, course_id)
                    )
                    enrollment_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                    updated += 1
                except sqlite3.IntegrityError:
                    # Nếu đã có enrollment (ví dụ status inactive) thì lấy ID
                    enr2 = conn.execute(
                        "SELECT id FROM Enrollments WHERE student_id = ? AND course_id = ?",
                        (student_db_id, course_id)
                    ).fetchone()
                    enrollment_id = enr2["id"] if enr2 else None
                    if enrollment_id:
                        conn.execute("UPDATE Enrollments SET status = 'active' WHERE id = ?", (enrollment_id,))
            else:
                enrollment_id = enr["enrollment_id"]
                course_id = enr["course_id"]
                updated += 1

            if not enrollment_id:
                continue

            for assign_type, score in (("midterm", midterm), ("assignment", assign_rate * 100)):
                assign_row = conn.execute(
                    "SELECT id FROM Assignments WHERE course_id = ? AND type = ?",
                    (course_id, assign_type),
                ).fetchone()
                if assign_row:
                    conn.execute(
                        """
                        INSERT INTO Grades (enrollment_id, assignment_id, score, graded_date)
                        VALUES (?, ?, ?, date('now'))
                        ON CONFLICT(enrollment_id, assignment_id) DO UPDATE SET
                            score = excluded.score,
                            graded_date = excluded.graded_date
                        """,
                        (enrollment_id, assign_row["id"], score),
                    )

            updated += 1

    logger.info(f"Đồng bộ crawl vào schema chuẩn: {updated} enrollment(s).")
    return updated
