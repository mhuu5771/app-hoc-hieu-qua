import os
import csv
import io
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Subject, Lesson, Quiz, Task

app = Flask(__name__)

# --- CẤU HÌNH HỆ THỐNG ---
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'hung-phat-id-smart-study-2026')

# Tự động chuyển đổi URL Postgres của Render sang chuẩn SQLAlchemy 2.0
uri = os.environ.get('DATABASE_URL', 'sqlite:///study_smart.db')
if uri and uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        # Lấy dữ liệu và ép kiểu string để tránh lỗi NoneType
        username = str(request.form.get('username', '')).strip()
        password = str(request.form.get('password', ''))

        if not username or not password:
            flash("Vui lòng điền đầy đủ thông tin!")
            return redirect(url_for('register'))

        # Kiểm tra user tồn tại
        try:
            user_exists = User.query.filter_by(username=username).first()
            if user_exists:
                flash("Tên đăng nhập này đã được sử dụng!")
                return redirect(url_for('register'))
            
            # Sử dụng pbkdf2:sha256 để tương thích mọi phiên bản Werkzeug
            hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
            new_user = User(username=username, password=hashed_pw)
            
            db.session.add(new_user)
            db.session.commit()
            
            flash("Đăng ký thành công! Mời bạn đăng nhập.")
            return redirect(url_for('login'))
            
        except Exception as e:
            db.session.rollback()
            # Dòng này sẽ in lỗi thực sự ra màn hình Terminal (màu đen)
            print("--- LỖI PHÁT SINH KHI ĐĂNG KÝ ---")
            print(str(e)) 
            print("---------------------------------")
            flash(f"Lỗi hệ thống: {str(e)}")
            return redirect(url_for('register'))
            
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Sai tài khoản hoặc mật khẩu!')
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- QUẢN LÝ MÔN HỌC (SUBJECT) ---

@app.route('/')
@login_required
def dashboard():
    subjects = Subject.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', subjects=subjects)

@app.route('/subject/add', methods=['GET', 'POST'])
@login_required
def add_subject():
    if request.method == 'POST':
        name = request.form.get('name')
        color = request.form.get('color', '#0d6efd')
        if name:
            new_s = Subject(name=name, color=color, user_id=current_user.id)
            db.session.add(new_s)
            db.session.commit()
            return redirect(url_for('dashboard'))
    return render_template('add_subject.html')

@app.route('/subject/<int:id>')
@login_required
def subject_detail(id):
    subject = Subject.query.get_or_404(id)
    return render_template('subject.html', subject=subject)

@app.route('/subject/delete/<int:id>')
@login_required
def delete_subject(id):
    subject = Subject.query.get_or_404(id)
    if subject.user_id != current_user.id:
        flash('Bạn không có quyền xóa môn học này!')
        return redirect(url_for('dashboard'))
    try:
        for lesson in subject.lessons:
            Task.query.filter_by(lesson_id=lesson.id).delete()
            Quiz.query.filter_by(lesson_id=lesson.id).delete()
            db.session.delete(lesson)
        db.session.delete(subject)
        db.session.commit()
        flash(f'Đã xóa môn học {subject.name}')
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi khi xóa: {str(e)}')
    return redirect(url_for('dashboard'))

# --- QUẢN LÝ BÀI HỌC, NHIỆM VỤ & QUIZ ---

@app.route('/lesson/add/<int:subject_id>', methods=['POST'])
@login_required
def add_lesson(subject_id):
    title = request.form.get('title')
    if title:
        new_l = Lesson(title=title, subject_id=subject_id)
        db.session.add(new_l)
        db.session.commit()
        # Mặc định thêm 1 task khi tạo bài mới
        db.session.add(Task(content="Nghiên cứu tài liệu bài học", lesson_id=new_l.id))
        db.session.commit()
        flash('Thêm bài học thành công!')
    return redirect(url_for('subject_detail', id=subject_id))

@app.route('/lesson/delete/<int:lesson_id>')
@login_required
def delete_lesson(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    sid = lesson.subject_id
    Task.query.filter_by(lesson_id=lesson_id).delete()
    Quiz.query.filter_by(lesson_id=lesson_id).delete()
    db.session.delete(lesson)
    db.session.commit()
    return redirect(url_for('subject_detail', id=sid))

@app.route('/task/add/<int:lesson_id>', methods=['POST'])
@login_required
def add_task(lesson_id):
    content = request.form.get('content')
    lesson = Lesson.query.get_or_404(lesson_id)
    if content:
        db.session.add(Task(content=content, lesson_id=lesson_id))
        db.session.commit()
    return redirect(url_for('subject_detail', id=lesson.subject_id))

@app.route('/task/toggle/<int:task_id>')
@login_required
def toggle_task(task_id):
    task = Task.query.get_or_404(task_id)
    task.is_done = not task.is_done
    db.session.commit()
    return redirect(url_for('subject_detail', id=task.lesson.subject_id))

@app.route('/task/delete/<int:task_id>')
@login_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    sid = task.lesson.subject_id
    db.session.delete(task)
    db.session.commit()
    return redirect(url_for('subject_detail', id=sid))

@app.route('/lesson/<int:lesson_id>/manage-quiz', methods=['GET', 'POST'])
@login_required
def manage_quiz(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    if request.method == 'POST':
        new_q = Quiz(
            lesson_id=lesson_id, 
            question=request.form.get('question'),
            option_a=request.form.get('a'), 
            option_b=request.form.get('b'),
            option_c=request.form.get('c'), 
            option_d=request.form.get('d'),
            correct_option=request.form.get('correct').strip().upper()
        )
        db.session.add(new_q)
        db.session.commit()
        return redirect(url_for('manage_quiz', lesson_id=lesson_id))
    quizzes = Quiz.query.filter_by(lesson_id=lesson_id).all()
    return render_template('manage_quiz.html', lesson=lesson, quizzes=quizzes)

@app.route('/lesson/<int:lesson_id>/upload-quiz', methods=['POST'])
@login_required
def upload_quiz(lesson_id):
    file = request.files.get('file')
    if file and file.filename.endswith('.csv'):
        try:
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            csv_input = csv.reader(stream)
            next(csv_input) # Bỏ qua header
            for row in csv_input:
                if len(row) >= 6:
                    db.session.add(Quiz(
                        lesson_id=lesson_id, question=row[0], option_a=row[1], 
                        option_b=row[2], option_c=row[3], option_d=row[4], 
                        correct_option=row[5].strip().upper()))
            db.session.commit()
            flash('Tải lên bộ câu hỏi thành công!')
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi khi xử lý file CSV: {str(e)}')
    return redirect(url_for('manage_quiz', lesson_id=lesson_id))

@app.route('/quiz/<int:lesson_id>', methods=['GET', 'POST'])
@login_required
def quiz(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    quizzes = Quiz.query.filter_by(lesson_id=lesson_id).all()
    if request.method == 'POST':
        correct = sum(1 for q in quizzes if request.form.get(f'q_{q.id}') == q.correct_option)
        score = (correct / len(quizzes)) * 100 if quizzes else 0
        if score >= 80:
            lesson.is_completed = True
            db.session.commit()
        return render_template('result.html', score=score, lesson=lesson)
    return render_template('quiz.html', lesson=lesson, quizzes=quizzes)

# --- KHỞI CHẠY ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.environ.get("PORT", 5001))
    app.run(host='0.0.0.0', port=port, debug=True)