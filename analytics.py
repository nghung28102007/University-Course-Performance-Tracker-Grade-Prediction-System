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
    """Đọc dữ liệu từ SQLite vào Pandas DataFrame."""
    conn = sqlite3.connect(db_path)
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
    """
    if df.empty:
        return []
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
    X = df[['midterm_score', 'attendance_rate', 'assignment_rate']]
    y = df['passed']
    
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
            "student_id": row['student_id'],
            "course_id": row['course_id'],
            "midterm_score": row['midterm_score'],
            "assignment_rate": row['assignment_rate'],
            "attendance_rate": row['attendance_rate'],
            "pass_probability": round(prob, 4),
            "required_final_score": req_final,
            "status": status
        })
        
    return results
