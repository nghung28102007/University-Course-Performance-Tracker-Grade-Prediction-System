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

PRIORITY_DATA_SOURCES = [
    # Ưu tiên 1: Cổng bảng điểm công khai (thay URL mẫu bằng endpoint thật của trường)
    "https://raw.githubusercontent.com/plotly/datasets/master/2014_usa_states.csv",
    # Ưu tiên 2: Trang HTML mở trên GitHub (cùng cấu trúc bảng điểm — chỉnh repo/đường dẫn)
    "https://raw.githubusercontent.com/YOUR_ORG/YOUR_REPO/main/data/mock_student_grades.html",
    # Ưu tiên 3 (BACKUP cuối): Cloud Mock-Server hoặc đổi thành "local://mock"
    "https://mock-student-grades.onrender.com",
]

MOCK_SENTINEL_LOCAL = "local://mock"

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

def generate_random_mock_data(num_students=8, courses=("CS201", "MATH201")):
    """Tự sinh dữ liệu điểm ngẫu nhiên khi mọi nguồn mạng đều thất bại."""
    records = []
    for course in courses:
        for i in range(1, num_students + 1):
            student_id = f"AU2024{str(i).zfill(3)}"
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
    rows = soup.find_all('tr')[1:] # Bỏ qua dòng Header
    
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
    Kích hoạt phương án dự phòng cuối cùng: file HTML cục bộ → dữ liệu tĩnh → sinh ngẫu nhiên.
    """
    local_data = get_local_file_data()
    if local_data:
        logger.info(f"Mock fallback: {len(local_data)} bản ghi từ file HTML cục bộ.")
        return local_data

    if use_random:
        random_data = generate_random_mock_data()
        logger.info(f"Mock fallback: sinh {len(random_data)} bản ghi ngẫu nhiên.")
        return random_data

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
                crawled_data = activate_mock_fallback(use_random=False)
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
    API tương thích ngược: gọi adaptive crawl hoặc thử một URL đơn lẻ rồi fallback Mock.
    """
    if target_url is None:
        data, _, _ = execute_adaptive_crawl()
        return data

    try:
        crawled_data = _fetch_and_parse_url(target_url)
        if crawled_data:
            return crawled_data
    except (requests.exceptions.RequestException, Exception) as e:
        logger.error(f"Lỗi khi cào {target_url}: {e}")

    return activate_mock_fallback(use_random=False)



def sync_to_sqlite(crawled_data, db_path="university.db"):
    """
    Đồng bộ dữ liệu cào được vào SQLite sử dụng cú pháp ON CONFLICT DO UPDATE.
    """
    if not crawled_data:
        return
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Cập nhật đè điểm số mới nhất của sinh viên mà không tạo bản ghi mới trùng lặp
    upsert_query = """
        INSERT INTO Grades (student_id, course_id, midterm_score, attendance_rate, assignment_rate, last_updated)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(student_id, course_id) DO UPDATE SET
            midterm_score = excluded.midterm_score,
            attendance_rate = excluded.attendance_rate,
            assignment_rate = excluded.assignment_rate,
            last_updated = CURRENT_TIMESTAMP
    """
    
    try:
        cursor.executemany(upsert_query, crawled_data)
        conn.commit()
        logger.info(f"Đã đồng bộ/ghi đè an toàn {len(crawled_data)} bản ghi vào SQLite.")
    except sqlite3.Error as e:
        logger.error(f"Lỗi Database Transaction: {e}")
    finally:
        conn.close()


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
        logger.warning("Không tìm thấy database.connection — dùng sync_to_sqlite thay thế.")
        sync_to_sqlite(crawled_data)
        return len(crawled_data)

    updated = 0
    with get_connection() as conn:
        for student_code, course_code, midterm, _att_rate, assign_rate in crawled_data:
            enr = conn.execute(
                """
                SELECT e.id AS enrollment_id, c.id AS course_id
                FROM Enrollments e
                JOIN Students s ON e.student_id = s.id
                JOIN Courses c ON e.course_id = c.id
                WHERE s.student_code = ? AND c.course_code = ? AND e.status = 'active'
                """,
                (student_code, course_code),
            ).fetchone()

            if not enr:
                logger.warning(f"Bỏ qua {student_code}/{course_code}: chưa có enrollment trong DB.")
                continue

            enrollment_id = enr["enrollment_id"]
            course_id = enr["course_id"]

            for assign_type, score in (("midterm", midterm), ("assignment", assign_rate * 100)):
                assign_row = conn.execute(
                    "SELECT id FROM Assignments WHERE course_id = ? AND type = ?",
                    (course_id, assign_type),
                ).fetchone()
                if assign_row:
                    conn.execute(
                        """
                        UPDATE Grades SET score = ?, graded_date = date('now')
                        WHERE enrollment_id = ? AND assignment_id = ?
                        """,
                        (score, enrollment_id, assign_row["id"]),
                    )

            updated += 1

    logger.info(f"Đồng bộ crawl vào schema chuẩn: {updated} enrollment(s).")
    return updated
