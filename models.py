from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    subjects = db.relationship('Subject', backref='user', lazy=True)

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    color = db.Column(db.String(20), default="#4361ee")
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    lessons = db.relationship('Lesson', backref='subject', cascade="all, delete-orphan", lazy=True)

class Lesson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    is_completed = db.Column(db.Boolean, default=False) # Đánh dấu khi đạt Test >= 80%
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'))
    tasks = db.relationship('Task', backref='lesson', cascade="all, delete-orphan", lazy=True)
    quizzes = db.relationship('Quiz', backref='lesson', cascade="all, delete-orphan", lazy=True)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)
    is_done = db.Column(db.Boolean, default=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lesson.id'))

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lesson.id'))
    question = db.Column(db.String(500))
    option_a = db.Column(db.String(200))
    option_b = db.Column(db.String(200))
    option_c = db.Column(db.String(200))
    option_d = db.Column(db.String(200))
    correct_option = db.Column(db.String(1))