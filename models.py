# models.py

from extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# Intermediate table for the many-to-many relationship between users and courses
class Enrollment(db.Model):
    __tablename__ = 'enrollments'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=db.func.now())
    # The backref on Course is automatically created via the `enrolled_users` backref on User.
    # The backref on User is automatically created via the `enrolled_courses` backref on Course.

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), default='student', nullable=False) # e.g., 'admin', 'teacher', 'student'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Defines the relationship to Course through Enrollment
    # This allows easy access to a user's enrolled courses: user.enrolled_courses
    enrolled_courses = db.relationship('Course', secondary='enrollments', lazy='dynamic', backref=db.backref('enrolled_users', lazy='dynamic'))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

# The Course model
class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=True)
    file_path = db.Column(db.String(300), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # The 'teacher' of the course is linked via the user ID
    teacher = db.relationship('User', backref='courses_created', lazy=True)
    
    # The backrefs for quizzes, lessons, assignments, etc. are defined on the related models
    # and will create properties on this class automatically.

    def __repr__(self):
        return f'<Course {self.title}>'

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    questions_json = db.Column(db.Text, nullable=False) # JSON string of questions, options, and correct answers
    due_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # The `quizzes` backref on Course is created here
    course = db.relationship('Course', backref=db.backref('quizzes', lazy=True))
    submissions = db.relationship('QuizSubmission', backref='quiz', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"Quiz('{self.title}', '{self.course_id}')"

class QuizSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    submitted_answers_json = db.Column(db.Text, nullable=False) # JSON string of student's answers
    student = db.relationship('User', backref=db.backref('quiz_submissions', lazy=True))
    submission_dates = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    is_graded = db.Column(db.Boolean, default=False) # Flag to indicate if the submission has been graded

    def __repr__(self):
        return f"QuizSubmission('{self.student_id}', '{self.quiz.title}', '{self.score}')"

class Lesson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # The `lessons` backref on Course is created here
    course = db.relationship('Course', backref=db.backref('lessons', lazy=True))

    def __repr__(self):
        return f"Lesson('{self.title}', '{self.course_id}')"

class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    due_date = db.Column(db.DateTime, nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    file_path = db.Column(db.String(200), nullable=True)
    max_submissions = db.Column(db.Integer, default=1)

    # The `assignments` backref on Course is created here
    course = db.relationship('Course', backref=db.backref('assignments', lazy=True))
    submissions = db.relationship('AssignmentSubmission', backref='assignment', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"Assignment('{self.title}', 'Due: {self.due_date}')"

# --- NEW MODEL: AssignmentSubmission ---
class AssignmentSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    file_path = db.Column(db.String(200), nullable=False)
    submission_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    grade = db.Column(db.Float, nullable=True) # Can be NULL until graded
    feedback = db.Column(db.Text, nullable=True) # Can be NULL until graded
    
    # The `assignment_submissions` backref on User is created here
    student = db.relationship('User', backref=db.backref('assignment_submissions', lazy=True))

    def __repr__(self):
        return f"AssignmentSubmission('{self.student_id}', '{self.assignment.title}', '{self.grade}')"

class DiscussionPost(db.Model):
    """
    Represents a main discussion post or topic.
    """
    __tablename__ = 'discussion_posts'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Foreign Keys
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    
    # The `discussion_posts` backrefs are created here on User and Course
    author = db.relationship('User', backref=db.backref('discussion_posts', lazy=True))
    course = db.relationship('Course', backref=db.backref('discussion_posts', lazy=True))
    replies = db.relationship('Reply', backref='post', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<DiscussionPost '{self.title}'>"

class Reply(db.Model):
    """
    Represents a reply to a discussion post.
    """
    __tablename__ = 'replies'
    
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Foreign Keys
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('discussion_posts.id'), nullable=False)
    
    # A self-referential foreign key to support nested replies
    parent_reply_id = db.Column(db.Integer, db.ForeignKey('replies.id'), nullable=True)

    # The `replies` and `child_replies` backrefs are created here
    author = db.relationship('User', backref=db.backref('replies', lazy=True))
    parent_reply = db.relationship('Reply', remote_side=[id], backref=db.backref('child_replies', lazy='dynamic', cascade='all, delete-orphan'))

    def __repr__(self):
        return f"<Reply '{self.content[:30]}...'>"

class Announcement(db.Model):
    __tablename__ = 'announcements'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Foreign keys
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # The `course_announcements` and `announcements` backrefs are created here
    course = db.relationship('Course', backref=db.backref('course_announcements', lazy='dynamic'))
    author = db.relationship('User', backref=db.backref('announcements', lazy='dynamic'))

    def __repr__(self):
        return f'<Announcement {self.title}>'

class CalendarEvent(db.Model):
    __tablename__ = 'calendar_events'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    
    # Foreign keys
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=True)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # The `course_calendar_events` and `user_calendar_events` backrefs are created here
    course = db.relationship('Course', backref=db.backref('course_calendar_events', lazy=True))
    author = db.relationship('User', backref=db.backref('user_calendar_events', lazy=True))

    def __repr__(self):
        return f"<CalendarEvent '{self.title}'>"

class GeneralAnnouncement(db.Model):
    __tablename__ = 'general_announcements'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign key to link to the admin/author who created it
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # The `general_announcements` backref is created here
    author = db.relationship('User', backref=db.backref('general_announcements', lazy=True))
    
    def __repr__(self):
        return f"<GeneralAnnouncement '{self.title}'>"






























# # models.py

# from extensions import db
# from flask_login import UserMixin
# from werkzeug.security import generate_password_hash, check_password_hash
# from datetime import datetime

# # Intermediate table for the many-to-many relationship between users and courses
# class Enrollment(db.Model):
#     __tablename__ = 'enrollments'
#     user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
#     course_id = db.Column(db.Integer, db.ForeignKey('course.id'), primary_key=True)
#     timestamp = db.Column(db.DateTime, index=True, default=db.func.now())
#     # You can add more fields here, like a grade, status, etc.

# class User(db.Model, UserMixin):
#     id = db.Column(db.Integer, primary_key=True)
#     username = db.Column(db.String(64), unique=True, nullable=False)
#     email = db.Column(db.String(120), unique=True, nullable=False)
#     password_hash = db.Column(db.String(128), nullable=False)
#     role = db.Column(db.String(20), default='student', nullable=False) # e.g., 'admin', 'teacher', 'student'
    
#     # Define the relationship to Course through Enrollment
#     # This allows easy access to a user's enrolled courses: user.enrolled_courses
#     enrolled_courses = db.relationship('Course', secondary='enrollments', lazy='dynamic', backref=db.backref('students', lazy='dynamic'))

#     def set_password(self, password):
#         self.password_hash = generate_password_hash(password)

#     def check_password(self, password):
#         return check_password_hash(self.password_hash, password)

#     def __repr__(self):
#         return f'<User {self.username}>'

# # The Course model
# class Course(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     title = db.Column(db.String(120), nullable=False)
#     description = db.Column(db.Text, nullable=True)
#     created_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
#     content = db.Column(db.Text, nullable=True)
#     file_path = db.Column(db.String(300), nullable=False)
#     # The 'teacher' of the course is linked via the user ID
#     teacher = db.relationship('User', backref='courses_created', lazy=True)
    
#     def __repr__(self):
#         return f'<Course {self.title}>'

# class Quiz(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     title = db.Column(db.String(100), nullable=False)
#     course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
#     course = db.relationship('Course', backref=db.backref('quizzes', lazy=True))
#     questions_json = db.Column(db.Text, nullable=False) # JSON string of questions, options, and correct answers

#     def __repr__(self):
#         return f"Quiz('{self.title}', '{self.course_id}')"

# class QuizSubmission(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
#     student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
#     score = db.Column(db.Integer, nullable=False)
#     submitted_answers_json = db.Column(db.Text, nullable=False) # JSON string of student's answers
#     quiz = db.relationship('Quiz', backref=db.backref('submissions', lazy=True))
#     student = db.relationship('User', backref=db.backref('quiz_submissions', lazy=True))
#     submission_dates = db.Column(db.DateTime, index=True, default=datetime.utcnow)
#     is_graded = db.Column(db.Boolean, default=False) # Flag to indicate if the submission has been graded

#     def __repr__(self):
#         return f"QuizSubmission('{self.student_id}', '{self.quiz.title}', '{self.score}')"

# class Lesson(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     title = db.Column(db.String(150), nullable=False)
#     content = db.Column(db.Text, nullable=False)
#     course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
#     created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

#     # Relationship to Course
#     course = db.relationship('Course', backref=db.backref('lessons', lazy=True))

#     def __repr__(self):
#         return f"Lesson('{self.title}', '{self.course_id}')"

# class Assignment(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     title = db.Column(db.String(150), nullable=False)
#     description = db.Column(db.Text, nullable=False)
#     due_date = db.Column(db.DateTime, nullable=False)
#     course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
#     created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
#     file_path = db.Column(db.String(200), nullable=True)
#     max_submissions = db.Column(db.Integer, default=1)

#     # Relationships
#     course = db.relationship('Course', backref=db.backref('assignments', lazy=True))
#     # Corrected: Define the relationship and backref on the parent model
#     submissions = db.relationship('AssignmentSubmission', backref='assignment', lazy=True, cascade="all, delete-orphan")
    
#     def __repr__(self):
#         return f"Assignment('{self.title}', 'Due: {self.due_date}')"

# # --- NEW MODEL: AssignmentSubmission ---
# class AssignmentSubmission(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=False)
#     student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
#     file_path = db.Column(db.String(200), nullable=False)
#     submission_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
#     grade = db.Column(db.Float, nullable=True) # Can be NULL until graded
#     feedback = db.Column(db.Text, nullable=True) # Can be NULL until graded
    
#     # Relationships
#     # Corrected: Only define the relationship to the student.
#     # The 'assignment' property is handled by the backref on the Assignment model.
#     student = db.relationship('User', backref=db.backref('assignment_submissions', lazy=True))

#     def __repr__(self):
#         return f"AssignmentSubmission('{self.student_id}', '{self.assignment.title}', '{self.grade}')"

# class DiscussionPost(db.Model):
#     """
#     Represents a main discussion post or topic.
#     """
#     __tablename__ = 'discussion_posts'
    
#     id = db.Column(db.Integer, primary_key=True)
#     title = db.Column(db.String(255), nullable=False)
#     content = db.Column(db.Text, nullable=False)
#     created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
#     # Foreign Keys
#     author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
#     course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    
#     # Relationships
#     author = db.relationship('User', backref=db.backref('discussion_posts', lazy=True))
#     course = db.relationship('Course', backref=db.backref('discussion_posts', lazy=True))
#     replies = db.relationship('Reply', backref='post', lazy='dynamic', cascade='all, delete-orphan')

#     def __repr__(self):
#         return f"<DiscussionPost '{self.title}'>"

# class Reply(db.Model):
#     """
#     Represents a reply to a discussion post.
    
#     This model stores the content of a reply and links it back to
#     the discussion post it belongs to and the user who created it.
#     """
#     __tablename__ = 'replies'
    
#     id = db.Column(db.Integer, primary_key=True)
#     content = db.Column(db.Text, nullable=False)
#     created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
#     # Foreign Keys
#     author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
#     post_id = db.Column(db.Integer, db.ForeignKey('discussion_posts.id'), nullable=False)
    
#     # A self-referential foreign key to support nested replies
#     parent_reply_id = db.Column(db.Integer, db.ForeignKey('replies.id'), nullable=True)

#     # Relationships
#     author = db.relationship('User', backref=db.backref('replies', lazy=True))
#     # Relationship to the parent reply (for nested replies)
#     parent_reply = db.relationship('Reply', remote_side=[id], backref=db.backref('child_replies', lazy='dynamic', cascade='all, delete-orphan'))

#     def __repr__(self):
#         return f"<Reply '{self.content[:30]}...'>"

# class Announcement(db.Model):
#     __tablename__ = 'announcements'
#     id = db.Column(db.Integer, primary_key=True)
#     title = db.Column(db.String(150), nullable=False)
#     content = db.Column(db.Text, nullable=False)
#     created_at = db.Column(db.DateTime, default=datetime.utcnow)

#     # Foreign keys - CORRECTED to use 'course' and 'user' table names
#     course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
#     author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

#     # Relationships
#     course = db.relationship('Course', backref=db.backref('announcements', lazy='dynamic'))
#     author = db.relationship('User', backref=db.backref('announcements', lazy='dynamic'))

#     def __repr__(self):
#         return f'<Announcement {self.title}>'

# class CalendarEvent(db.Model):
#     __tablename__ = 'calendar_events'
#     id = db.Column(db.Integer, primary_key=True)
#     title = db.Column(db.String(255), nullable=False)
#     description = db.Column(db.Text, nullable=True)
#     start_time = db.Column(db.DateTime, nullable=False)
#     end_time = db.Column(db.DateTime, nullable=False)
    
#     # Foreign keys
#     course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
#     author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

#     # Relationships
#     author = db.relationship('User', backref=db.backref('calendar_events', lazy=True))

#     def __repr__(self):
#         return f"<CalendarEvent '{self.title}'>"
