import sqlite3
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier

# Cấu hình Mốc điểm và Trọng số theo Quy chế
PASSING_MARK = 65.0
WEIGHTS = {
    'midterm': 0.30,
    'assignment': 0.20,
    'final': 0.50
}

def load_data(db_path="university.db"):
    """Đọc dữ liệu crawl phẳng từ SQLite vào Pandas DataFrame."""
    conn = sqlite3.connect(db_path)
    try:
        df = pd.read_sql_query("SELECT * FROM CrawlGrades", conn)
    except Exception:
        df = pd.read_sql_query("SELECT * FROM Grades", conn)
    conn.close()
    return df

def calculate_required_final_score(midterm_score, assignment_rate):
    """
    Reverse Engineering (Tính điểm cứu vớt):
    Tính điểm thi cuối kỳ tối thiểu cần đạt để tổng điểm chạm đúng mốc 65/100.
    """
    assignment_score = assignment_rate * 100 # Quy đổi về thang điểm 100
    
    # Tính tổng điểm hiện có
    current_accumulated = (midterm_score * WEIGHTS['midterm']) + (assignment_score * WEIGHTS['assignment'])
    score_needed = PASSING_MARK - current_accumulated
    
    if score_needed <= 0:
        return 0.0 # Đã đủ điểm qua môn, không cần thi vẫn đậu
        
    required_final = score_needed / WEIGHTS['final']
    
    if required_final > 100.0:
        return -1.0 # Báo hiệu không thể qua môn dù đạt 100 điểm thi cuối kỳ
        
    return round(required_final, 2)

def build_and_predict_model(df):
    """
    Xây dựng mô hình Random Forest phân loại và trả về danh sách sinh viên At-risk.

    Args:
        df (pd.DataFrame): DataFrame chứa các cột: student_id, course_id,
                           midterm_score, attendance_rate, assignment_rate.

    Returns:
        list[dict]: Danh sách dict chứa thông tin dự đoán mỗi sinh viên,
                    bao gồm pass_probability, required_final_score, status.
    """
    if df.empty:
        return []

    # ── FIX-2: Imputation — xử lý NaN/Null trước khi đưa vào model ──
    feature_cols = ['midterm_score', 'attendance_rate', 'assignment_rate']
    # Bước 1: Loại bỏ các hàng mà TẤT CẢ feature đều NaN (dữ liệu rác)
    df = df.dropna(subset=feature_cols, how='all').copy()
    if df.empty:
        return []
    # Bước 2: Điền giá trị mặc định cho các ô NaN còn lại
    df['midterm_score'] = df['midterm_score'].fillna(50.0)       # Mặc định 50/100
    df['attendance_rate'] = df['attendance_rate'].fillna(0.80)    # Mặc định 80%
    df['assignment_rate'] = df['assignment_rate'].fillna(0.50)    # Mặc định 50%

    # BƯỚC 1: Tiền xử lý dữ liệu (Mô phỏng dữ liệu lịch sử để huấn luyện)
    # Trong môi trường thực tế, mô hình sẽ được train bởi tập dữ liệu quá khứ. 
    # Ở đây ta giả lập một trường 'passed' để hệ thống có thể train phân loại.
    np.random.seed(42)
    # Giả lập điểm cuối kỳ ngẫu nhiên của các khóa trước
    df['simulated_final'] = np.random.uniform(30, 100, size=len(df))
    df['total_score'] = (
        df['midterm_score'] * WEIGHTS['midterm'] + 
        (df['assignment_rate'] * 100) * WEIGHTS['assignment'] + 
        df['simulated_final'] * WEIGHTS['final']
    )
    # Nhãn phân loại: 1 (Pass - Tổng kết >= 65), 0 (Fail - Tổng kết < 65)
    df['passed'] = (df['total_score'] >= PASSING_MARK).astype(int)
    
    # BƯỚC 2: Định nghĩa Features (X) và Target (y)
    X = df[feature_cols]
    y = df['passed']

    # ── FIX-2: Edge case — nếu y chỉ có 1 class, predict_proba sẽ lỗi ──
    if y.nunique() < 2:
        single_class = y.iloc[0]
        prob_value = 1.0 if single_class == 1 else 0.0
        results = []
        for idx, row in df.iterrows():
            req_final = calculate_required_final_score(row['midterm_score'], row['assignment_rate'])
            results.append({
                "student_id": str(row['student_id']),
                "course_id": str(row['course_id']),
                "midterm_score": float(row['midterm_score']),
                "assignment_rate": float(row['assignment_rate']),
                "attendance_rate": float(row['attendance_rate']),
                "pass_probability": prob_value,
                "required_final_score": float(req_final),
                "status": "Safe" if prob_value >= 0.5 else "At-risk"
            })
        return results
    
    # BƯỚC 3: Khởi tạo và Huấn luyện mô hình
    rf_model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
    rf_model.fit(X, y)
    
    # BƯỚC 4: Dự đoán trên dữ liệu hiện tại
    pass_probabilities = rf_model.predict_proba(X)[:, 1] # Cột 1 là xác suất Pass (Class 1)
    
    results = []
    for idx, row in df.iterrows():
        prob = pass_probabilities[idx]
        req_final = calculate_required_final_score(row['midterm_score'], row['assignment_rate'])
        
        # BƯỚC 5: Gắn nhãn Cảnh báo
        status = "Safe"
        if prob < 0.5:
            status = "At-risk"
            
        results.append({
            "student_id": str(row['student_id']),
            "course_id": str(row['course_id']),
            "midterm_score": float(row['midterm_score']),
            "assignment_rate": float(row['assignment_rate']),
            "attendance_rate": float(row['attendance_rate']),
            "pass_probability": float(round(prob, 4)),
            "required_final_score": float(req_final),
            "status": str(status)
        })
        
    return results
