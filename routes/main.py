# routes/main.py

from datetime import datetime
import os
import csv
import io
import subprocess
import uuid
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from flask import Blueprint, abort, current_app, jsonify, render_template, redirect, send_from_directory, url_for, request, flash, Response
from flask_login import login_required, current_user
from weasyprint import HTML, CSS
from models import Course, User, Enrollment, Quiz, QuizSubmission, Lesson, Assignment, AssignmentSubmission, DiscussionPost, Reply, Announcement, CalendarEvent, GeneralAnnouncement
from extensions import db
from sqlalchemy import desc
from sqlalchemy.orm import joinedload
import json

main_bp = Blueprint('main', __name__)

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'zip', 'rar', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'csv', 'mp4', 'avi', 'mkv', 'mov', 'mp3', 'wav', 'ogg', 'flac', 'webm', 'ogg', 'm4a', 'aac'}

def allowed_file(filename):
    """
    Checks if a file has an allowed extension.
    """
    return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# def convert_video_to_mp4(input_path, output_path):
#     """
#     Converts a video file to a web-friendly MP4 format using FFmpeg.
    
#     Args:
#         input_path (str): The path to the input video file.
#         output_path (str): The desired path for the output MP4 file.
        
#     Returns:
#         bool: True if the conversion was successful, False otherwise.
#     """
#     try:
#         # Check if FFmpeg is installed and accessible
#         subprocess.run(['ffmpeg', '-version'], check=True, capture_output=True)
        
#         # FFmpeg command to convert video to H.264 MP4 with AAC audio
#         command = [
#             'ffmpeg',
#             '-i', input_path,  # Input file
#             '-vcodec', 'libx264',  # Video codec
#             '-acodec', 'aac',    # Audio codec
#             '-strict', 'experimental', # Required for some AAC encoders
#             '-movflags', 'faststart', # Optimizes for web streaming
#             '-y', output_path # Overwrite output file if it exists
#         ]
        
#         # Execute the FFmpeg command
#         subprocess.run(command, check=True, capture_output=True)
        
#         return True
#     except FileNotFoundError:
#         print("FFmpeg not found. Please ensure it is installed and in your system's PATH.")
#         return False
#     except subprocess.CalledProcessError as e:
#         print(f"An error occurred during FFmpeg conversion: {e.stderr.decode()}")
#         return False
#     except Exception as e:
#         print(f"An unexpected error occurred: {e}")
#         return False

def convert_video_to_mp4(input_path, output_path):
    """
    Converts a video file to a web-friendly MP4 format using FFmpeg.
    
    Args:
        input_path (str): The path to the input video file.
        output_path (str): The desired path for the output MP4 file.
        
    Returns:
        bool: True if the conversion was successful, False otherwise.
    """
    try:
        subprocess.run(['ffmpeg', '-version'], check=True, capture_output=True)
        command = [
            'ffmpeg',
            '-i', input_path,  # Input file
            '-vcodec', 'libx264',  # Video codec
            '-acodec', 'aac',    # Audio codec
            '-strict', 'experimental', # Required for some AAC encoders
            '-movflags', 'faststart', # Optimizes for web streaming
            '-y', output_path # Overwrite output file if it exists
        ]
        subprocess.run(command, check=True, capture_output=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        print(f"Error during FFmpeg conversion: {e}")
        return False

def extract_video_thumbnail(video_path, thumbnail_path):
    """
    Extracts a single frame from a video file using FFmpeg and saves it as a JPEG.
    
    Args:
        video_path (str): The path to the input video file.
        thumbnail_path (str): The desired path for the output thumbnail image.
        
    Returns:
        bool: True if the thumbnail extraction was successful, False otherwise.
    """
    try:
        command = [
            'ffmpeg',
            '-i', video_path,
            '-ss', '00:00:03.000',  # Grab frame at 3 seconds
            '-vframes', '1',
            '-y', thumbnail_path
        ]
        subprocess.run(command, check=True, capture_output=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        print(f"Error extracting thumbnail: {e}")
        return False

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/loading')
def loading():
    load_type = request.args.get('type', 'login')
    username = request.args.get('username', None)
    return render_template('loadings/loading.html', load_type=load_type, username=username)

@main_bp.context_processor
def inject_data():
    current_year = datetime.utcnow().year
    if current_user.is_authenticated:
        username = current_user.username[:10] + ('...' if len(current_user.username) > 10 else '')
    else:
        username = None
    return dict(current_year=current_year, short_username=username)

@main_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        return redirect(url_for('main.admin_dashboard'))
    elif current_user.role == 'teacher':
        return redirect(url_for('main.teacher_dashboard'))
    else: # Default to student dashboard
        return redirect(url_for('main.student_dashboard'))

@main_bp.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('main.dashboard'))
    return render_template('dashboards/admin_dashboard.html', title='Admin Dashboard')

@main_bp.route('/admin/courses', methods=['GET', 'POST'])
@login_required
def manage_courses():
    if current_user.role != 'admin':
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')

        if title:
            new_course = Course(
                title=title,
                description=description,
                created_by_user_id=current_user.id
            )
            db.session.add(new_course)
            db.session.commit()
            flash('New course created successfully!', 'success')
            return redirect(url_for('main.manage_courses'))
        else:
            flash('Course title is required!', 'danger')
            return redirect(url_for('main.manage_courses'))

    courses = Course.query.all()
    teachers = User.query.filter_by(role='teacher').all()
    return render_template('dashboards/manage_courses.html', title='Manage Courses', courses=courses, teachers=teachers)

@main_bp.route('/admin/users', methods=['GET', 'POST'])
@login_required
def manage_users():
    if current_user.role != 'admin':
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        user_id = request.form.get('user_id')
        new_role = request.form.get('new_role')

        if user_id and new_role:
            user = User.query.get(user_id)
            if user:
                user.role = new_role
                db.session.commit()
                flash(f'Role for {user.username} updated to {new_role}.', 'success')
            else:
                flash('User not found!', 'danger')
        else:
            flash('Invalid request!', 'danger')
        return redirect(url_for('main.manage_users'))

    users = User.query.all()
    return render_template('dashboards/manage_users.html', title='Manage Users', users=users)

@main_bp.route('/teacher')
@login_required
def teacher_dashboard():
    if current_user.role not in ['teacher', 'admin']:
        return redirect(url_for('main.dashboard'))
    courses = Course.query.filter_by(created_by_user_id=current_user.id).all()
    return render_template('dashboards/teacher_dashboard.html', title='Teacher Dashboard', courses=courses)

@main_bp.route('/teacher/lessons/select_course', methods=['GET'])
@login_required
def select_course_for_lesson():
    """
    Shows a list of courses for the teacher to select from,
    before creating a new lesson.
    """
    if current_user.role != 'teacher':
        flash("You do not have permission to view this page.", 'danger')
        return redirect(url_for('main.index'))
    
    courses = Course.query.filter_by(created_by_user_id=current_user.id).all()
    
    return render_template('courses/select_course_for_lesson.html', 
                            title='Select a Course',
                            courses=courses)

@main_bp.route('/teacher/assignments/select_course', methods=['GET'])
@login_required
def select_course_for_assignment():
    """
    Shows a list of courses for the teacher to select from,
    before creating a new assignment.
    """
    if current_user.role != 'teacher':
        flash("You do not have permission to view this page.", 'danger')
        return redirect(url_for('main.index'))
    
    courses = Course.query.filter_by(created_by_user_id=current_user.id).all()
    
    return render_template('assignments/select_course_for_assignment.html', 
                            title='Select a Course to Create an Assignment',
                            courses=courses)

@main_bp.route('/teacher/courses', methods=['GET', 'POST'])
@login_required
def teacher_courses():
    if current_user.role not in ['teacher', 'admin']:
        flash("You do not have permission to view this page.", 'danger')
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        content = request.form.get('content') # Ensure content is captured
        file = request.files.get('file')
        file_path = None

        if title:
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                filepath = os.path.join(current_app.config['UPLOAD_FOLDERS'], filename)
                i = 1
                while os.path.exists(filepath):
                    name, ext = os.path.splitext(filename)
                    filename = f"{name}_{i}{ext}"
                    filepath = os.path.join(current_app.config['UPLOAD_FOLDERS'], filename)
                    i += 1
                
                try:
                    file.save(filepath)
                    file_path = filename
                except Exception as e:
                    flash(f'An error occurred while uploading the file: {str(e)}', 'danger')
                    return redirect(url_for('main.teacher_courses'))

            new_course = Course(
                title=title,
                description=description,
                content=content,
                file_path=file_path,
                created_by_user_id=current_user.id
            )
            db.session.add(new_course)
            db.session.commit()
            flash('New course created successfully!', 'success')
            return redirect(url_for('main.teacher_courses'))
        else:
            flash('Course title is required!', 'danger')
            return redirect(url_for('main.teacher_courses'))

    courses = Course.query.filter_by(created_by_user_id=current_user.id).all()
    return render_template('dashboards/teacher_courses.html', title='My Courses', courses=courses)

@main_bp.route('/teacher/courses/<int:course_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_course(course_id):
    course = Course.query.get_or_404(course_id)
    if not (current_user.role == 'admin' or (current_user.role == 'teacher' and course.created_by_user_id == current_user.id)):
        flash("You do not have permission to edit this course.", 'danger')
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        course.title = request.form.get('title')
        course.description = request.form.get('description')
        course.content = request.form.get('content') # Ensure content is captured
        file = request.files.get('file')

        if file and file.filename != '':
            if course.file_path:
                try:
                    os.remove(os.path.join(current_app.config['UPLOAD_FOLDERS'], course.file_path))
                except OSError as e:
                    print(f"Error removing old file: {e}")
            
            filename = secure_filename(file.filename)
            filepath = os.path.join(current_app.config['UPLOAD_FOLDERS'], filename)
            file.save(filepath)
            course.file_path = filename
        
        db.session.commit()
        flash('Course updated successfully!', 'success')
        return redirect(url_for('main.teacher_courses'))
    
    return render_template('dashboards/edit_course.html', title=f'Edit {course.title}', course=course)

@main_bp.route('/teacher/courses/<int:course_id>/delete', methods=['POST'])
@login_required
def delete_course(course_id):
    course = Course.query.get_or_404(course_id)
    assignments = Assignment.query.filter_by(course_id=course_id).all()
    lessons = Lesson.query.filter_by(course_id=course_id).all()
    if not (current_user.role == 'admin' or (current_user.role == 'teacher' and course.created_by_user_id == current_user.id)):
        flash("You do not have permission to delete this course.", 'danger')
        return redirect(url_for('main.dashboard'))
    
    try:
        if course.file_path:
            file_path = os.path.join(current_app.config['UPLOAD_FOLDERS'], course.file_path)
            if os.path.exists(file_path):
                os.remove(file_path)
        for assignment in assignments:
            db.session.delete(assignment)
        for lesson in lessons:
            db.session.delete(lesson)
        db.session.delete(course)
        db.session.commit()
        flash('Course deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred: {str(e)}', 'danger')

    return redirect(url_for('main.teacher_courses'))

@main_bp.route('/download/course_file/<filename>')
def download_course_file(filename):
    if not current_user.is_authenticated:
        flash("You must be logged in to download this file.", 'danger')
        return redirect(url_for('main.login'))

    return send_from_directory(current_app.config['UPLOAD_FOLDERS'], filename, as_attachment=True)

@main_bp.route('/upload-file-tinymce', methods=['POST'])
@login_required
def upload_file_tinymce():
    """Handles file uploads from TinyMCE editor via AJAX."""
    file = request.files.get('file')
    if not file or file.filename == '':
        return jsonify({'error': 'No file uploaded'}), 400

    upload_folder = current_app.config['UPLOAD_FOLDERS']
    os.makedirs(upload_folder, exist_ok=True)

    filename = secure_filename(file.filename)
    original_filepath = os.path.join(upload_folder, filename)
    
    i = 1
    while os.path.exists(original_filepath):
        name, ext = os.path.splitext(filename)
        filename = f"{name}_{i}{ext}"
        original_filepath = os.path.join(upload_folder, filename)
        i += 1
    
    try:
        file.save(original_filepath)
        
        if file.content_type.startswith('video/'):
            name, ext = os.path.splitext(filename)
            output_filename = f"{name}.mp4"
            output_filepath = os.path.join(upload_folder, output_filename)
            
            if convert_video_to_mp4(original_filepath, output_filepath):
                os.remove(original_filepath) # Delete the original file
                
                # Now, extract the thumbnail from the newly converted video
                thumbnail_filename = f"{name}_thumb.jpg"
                thumbnail_filepath = os.path.join(upload_folder, thumbnail_filename)
                
                if extract_video_thumbnail(output_filepath, thumbnail_filepath):
                    # Return both the video URL and the thumbnail URL
                    video_url = url_for('main.download_course_file', filename=output_filename)
                    thumbnail_url = url_for('main.download_course_file', filename=thumbnail_filename)
                    return jsonify({'location': video_url, 'poster': thumbnail_url})
                else:
                    # Conversion was fine, but thumbnail failed.
                    return jsonify({'location': url_for('main.download_course_file', filename=output_filename)})
            else:
                print(f"Video conversion failed for {filename}. Serving original file.")
                return jsonify({'location': url_for('main.download_course_file', filename=filename)})
        else:
            return jsonify({'location': url_for('main.download_course_file', filename=filename)})

    except Exception as e:
        print(f"Error during file upload: {str(e)}")
        return jsonify({'error': str(e)}), 500


@main_bp.route('/teacher/courses/<int:course_id>/students')
@login_required
def manage_students(course_id):
    course = Course.query.get_or_404(course_id)
    if not (current_user.role == 'admin' or (current_user.role == 'teacher' and course.created_by_user_id == current_user.id)):
        flash("You do not have permission to view students for this course.", 'danger')
        return redirect(url_for('main.dashboard'))
    
    # The 'students' backref from the `enrollments` table gives us the list of User objects
    enrolled_students = course.students
    
    return render_template('dashboards/manage_students.html', title=f'Students in {course.title}', course=course, students=enrolled_students)

@main_bp.route('/teacher/courses/<int:course_id>/students/<int:student_id>/remove', methods=['POST'])
@login_required
def remove_student(course_id, student_id):
    course = Course.query.get_or_404(course_id)
    
    # Security check: Ensure the current user has permission to remove students
    if not (current_user.role == 'admin' or (current_user.role == 'teacher' and course.created_by_user_id == current_user.id)):
        flash("You do not have permission to remove this student.", 'danger')
        return redirect(url_for('main.manage_students', course_id=course.id))

    # Find the specific enrollment record
    enrollment = Enrollment.query.filter_by(course_id=course_id, user_id=student_id).first()
    
    if enrollment:
        student_user = User.query.get(student_id)
        try:
            db.session.delete(enrollment)
            db.session.commit()
            flash(f'{student_user.username} was successfully removed from {course.title}.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while removing the student: {str(e)}', 'danger')
    else:
        flash("Enrollment record not found.", 'danger')
    
    return redirect(url_for('main.manage_students', course_id=course.id))

@main_bp.route('/upload-quiz-file', methods=['POST'])
@login_required
def upload_quiz_file():
    """
    Handles file uploads from the TinyMCE editor for embedding media
    within a quiz's description.

    This function reuses the core logic of `upload_file_tinymce`
    to convert videos and create thumbnails.
    """
    # Simply call the existing, reusable file upload function
    return upload_file_tinymce()

@main_bp.route('/teacher/courses/<int:course_id>/quizzes', methods=['GET', 'POST'])
@login_required
def manage_quizzes(course_id):
    course = Course.query.get_or_404(course_id)
    if not (current_user.role == 'admin' or (current_user.role == 'teacher' and course.created_by_user_id == current_user.id)):
        flash("You do not have permission to manage quizzes for this course.", 'danger')
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        quiz_title = request.form.get('quiz_title')
        questions_json_str = request.form.get('questions_json')

        try:
            questions_data = json.loads(questions_json_str)
            if not questions_data:
                flash("Quiz must have at least one question.", 'danger')
                return redirect(url_for('main.manage_quizzes', course_id=course_id))

            # Validate that each question has a 'points' field
            for question in questions_data:
                if 'points' not in question or not isinstance(question['points'], int) or question['points'] <= 0:
                    flash("Each question must have a positive integer value for points.", 'danger')
                    return redirect(url_for('main.manage_quizzes', course_id=course_id))

            new_quiz = Quiz(
                title=quiz_title,
                course_id=course.id,
                questions_json=questions_json_str
            )
            db.session.add(new_quiz)
            db.session.commit()
            flash('Quiz created successfully!', 'success')
        except json.JSONDecodeError:
            flash("Invalid JSON format for questions. Please check your syntax.", 'danger')
        except Exception as e:
            flash(f'An unexpected error occurred: {str(e)}', 'danger')
        
        return redirect(url_for('main.manage_quizzes', course_id=course_id))

    quizzes = Quiz.query.filter_by(course_id=course.id).all()
    return render_template('dashboards/manage_quizzes.html', title=f'Manage Quizzes for {course.title}', quizzes=quizzes, course=course)

@main_bp.route('/teacher/quizzes/<int:quiz_id>/preview')
@login_required
def preview_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    course = quiz.course
    if not (current_user.role == 'admin' or (current_user.role == 'teacher' and course.created_by_user_id == current_user.id)):
        flash("You do not have permission to preview this quiz.", 'danger')
        return redirect(url_for('main.dashboard'))
    
    questions = json.loads(quiz.questions_json)
    
    return render_template('quizzes/preview_quiz.html', title=f'Preview: {quiz.title}', quiz=quiz, questions=questions)

@main_bp.route('/teacher/quizzes/<int:quiz_id>/delete', methods=['POST'])
@login_required
def delete_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    course = quiz.course
    if not (current_user.role == 'admin' or (current_user.role == 'teacher' and course.created_by_user_id == current_user.id)):
        flash("You do not have permission to delete this quiz.", 'danger')
        return redirect(url_for('main.dashboard'))

    try:
        QuizSubmission.query.filter_by(quiz_id=quiz.id).delete()
        db.session.delete(quiz)
        db.session.commit()
        flash('Quiz and all associated submissions deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred: {str(e)}', 'danger')
    
    return redirect(url_for('main.manage_quizzes', course_id=course.id))

@main_bp.route('/student', methods=['GET', 'POST'])
@login_required
def student_dashboard():
    if current_user.role != 'student':
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        course_id = request.form.get('course_id')
        course = Course.query.get(course_id)
        if course:
            is_enrolled = Enrollment.query.filter_by(user_id=current_user.id, course_id=course.id).first()
            if is_enrolled:
                flash('You are already enrolled in this course!', 'info')
            else:
                enrollment = Enrollment(user_id=current_user.id, course_id=course.id)
                db.session.add(enrollment)
                db.session.commit()
                flash(f'Successfully enrolled in {course.title}!', 'success')
        else:
            flash('Course not found!', 'danger')
        return redirect(url_for('main.student_dashboard'))
    
    all_courses = Course.query.all()
    enrolled_course_ids = [c.id for c in current_user.enrolled_courses]
    available_courses = [c for c in all_courses if c.id not in enrolled_course_ids]

    enrolled_courses = []
    for course in current_user.enrolled_courses:
        quizzes = Quiz.query.filter_by(course_id=course.id).all()
        quizzes_with_status = []
        for quiz in quizzes:
            submission = QuizSubmission.query.filter_by(student_id=current_user.id, quiz_id=quiz.id).first()
            questions_data = json.loads(quiz.questions_json)
            total_questions = len(questions_data) if questions_data else 0
            total_points = sum(q['points'] for q in questions_data) if questions_data else 0

            quizzes_with_status.append({
                'id': quiz.id,
                'title': quiz.title,
                'is_completed': submission is not None,
                'score': submission.score if submission else None,
                'submission_id': submission.id if submission else None,
                'total_questions': total_questions,
                'total_points': total_points,
                'percentage': (submission.score / total_points * 100) if submission and total_points > 0 else None
            })
        enrolled_courses.append({
            'course': course,
            'quizzes': quizzes_with_status
        })

    return render_template('dashboards/student_dashboard.html', 
                            title='Student Dashboard', 
                            enrolled_courses=enrolled_courses,
                            available_courses=available_courses)


@main_bp.route('/student/quizzes/<int:quiz_id>')
@login_required
def take_quiz(quiz_id):
    """
    Displays the quiz page to the student with all the questions.
    """
    quiz = Quiz.query.get_or_404(quiz_id)

    # Check for enrollment
    enrolled = Enrollment.query.filter_by(user_id=current_user.id, course_id=quiz.course_id).first()
    if not enrolled:
        flash("You are not enrolled in this course.", 'danger')
        return redirect(url_for('main.student_dashboard'))
    
    # Check if the student has already submitted the quiz
    submission = QuizSubmission.query.filter_by(student_id=current_user.id, quiz_id=quiz.id).first()
    if submission:
        flash("You have already submitted this quiz.", 'info')
        return redirect(url_for('main.quiz_results', submission_id=submission.id))

    # Parse the questions_json string into a Python list
    try:
        quiz_questions = json.loads(quiz.questions_json)
    except (json.JSONDecodeError, TypeError):
        # Handle cases where the JSON is invalid or missing
        quiz_questions = []
        flash("There was an error loading the quiz questions. Please contact your teacher.", 'danger')

    return render_template('quizzes/take_quiz.html', quiz=quiz, quiz_questions=quiz_questions)


@main_bp.route('/student/quizzes/<int:quiz_id>/submit', methods=['POST'])
@login_required
def submit_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)

    enrolled = Enrollment.query.filter_by(user_id=current_user.id, course_id=quiz.course_id).first()
    submission = QuizSubmission.query.filter_by(student_id=current_user.id, quiz_id=quiz.id).first()
    if not enrolled or submission:
        flash("You are not authorized to submit this quiz or have already done so.", 'danger')
        return redirect(url_for('main.student_dashboard'))
    
    quiz_questions = json.loads(quiz.questions_json)
    student_answers = []
    mcq_score = 0
    open_ended_questions_exist = False

    for i, question in enumerate(quiz_questions):
        question_id = f'q-{i}'
        student_answer = request.form.get(question_id)
        
        # We'll only auto-grade multiple choice questions.
        if question['type'] == 'multiple_choice':
            is_correct = (student_answer == question['answer'])
            if is_correct:
                mcq_score += question.get('points', 1)
        elif question['type'] == 'open_ended':
            is_correct = False # Open-ended answers are not auto-graded anymore
            open_ended_questions_exist = True
        
        student_answers.append({
            'question': question['question'],
            'type': question['type'],
            'submitted_answer': student_answer,
            'correct_answer': question['answer'],
            'is_correct': is_correct,
            'points': question.get('points', 1),
            'awarded_points': mcq_score if is_correct else 0 if question['type'] == 'multiple_choice' else None # Initialize awarded points for manual grading
        })

    new_submission = QuizSubmission(
        quiz_id=quiz.id,
        student_id=current_user.id,
        # The score here will only be for multiple choice questions.
        score=mcq_score,
        is_graded= not open_ended_questions_exist, # If no open-ended questions, it's fully graded
        submitted_answers_json=json.dumps(student_answers)
    )
    db.session.add(new_submission)
    db.session.commit()
    flash(f"Quiz '{quiz.title}' submitted successfully! Your multiple-choice score is {mcq_score}.", 'success')

    return redirect(url_for('main.quiz_results', submission_id=new_submission.id))


@main_bp.route('/student/quizzes/results/<int:submission_id>')
@login_required
def quiz_results(submission_id):
    submission = QuizSubmission.query.get_or_404(submission_id)

    if not (current_user.id == submission.student_id or current_user.role in ['teacher', 'admin']):
        flash("You do not have permission to view these results.", 'danger')
        return redirect(url_for('main.student_dashboard'))

    if current_user.role == 'teacher' and submission.quiz.course.created_by_user_id != current_user.id:
        flash("You do not have permission to view these results.", 'danger')
        return redirect(url_for('main.teacher_dashboard'))

    submitted_answers = json.loads(submission.submitted_answers_json)
    quiz_questions = json.loads(submission.quiz.questions_json)
    
    total_possible_score_mcq = sum(q.get('points', 1) for q in quiz_questions if q['type'] == 'multiple_choice')
    total_possible_score_open_ended = sum(q.get('points', 1) for q in quiz_questions if q['type'] == 'open_ended')
    total_possible_score = total_possible_score_mcq + total_possible_score_open_ended

    return render_template('quizzes/quiz_results.html', 
                            title=f'Quiz Results: {submission.quiz.title}', 
                            submission=submission, 
                            submitted_answers=submitted_answers,
                            total_possible_score=total_possible_score,
                            total_possible_score_mcq=total_possible_score_mcq)


@main_bp.route('/student/unenroll/<int:course_id>', methods=['POST'])
@login_required
def unenroll_course(course_id):
    if current_user.role != 'student':
        flash("You do not have permission to unenroll from a course.", 'danger')
        return redirect(url_for('main.dashboard'))

    enrollment = Enrollment.query.filter_by(user_id=current_user.id, course_id=course_id).first()
    
    if enrollment:
        course = Course.query.get(course_id)
        try:
            db.session.delete(enrollment)
            db.session.commit()
            flash(f'You have successfully unenrolled from {course.title}.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'danger')
    else:
        flash("Enrollment record not found.", 'danger')

    return redirect(url_for('main.student_dashboard'))

@main_bp.route('/course/<int:course_id>')
@login_required
def course_detail(course_id):
    course = Course.query.get_or_404(course_id)
    
    if current_user.role in ['teacher', 'admin'] and course.created_by_user_id == current_user.id:
        return render_template('courses/course_detail.html', title=course.title, course=course)

    enrolled = Enrollment.query.filter_by(user_id=current_user.id, course_id=course.id).first()
    if not enrolled:
        flash("You are not enrolled in this course.", 'danger')
        return redirect(url_for('main.student_dashboard'))
    
    return render_template('courses/course_detail.html', title=course.title, course=course)

@main_bp.route('/teacher/grade_submission/<int:submission_id>', methods=['GET', 'POST'])
@login_required
def teacher_grade_submission(submission_id):
    submission = QuizSubmission.query.get_or_404(submission_id)
    quiz = submission.quiz

    # Permission check
    if not (current_user.role == 'admin' or (current_user.role == 'teacher' and quiz.course.created_by_user_id == current_user.id)):
        flash("You do not have permission to grade this submission.", 'danger')
        return redirect(url_for('main.teacher_dashboard'))

    submitted_answers = json.loads(submission.submitted_answers_json)

    if request.method == 'POST':
        # Step 1: Calculate MCQ score fresh
        mcq_score = sum(
            ans['points'] if ans['type'] == 'multiple_choice' and ans.get('is_correct') else 0
            for ans in submitted_answers
        )

        # Step 2: Reset open-ended scores & add teacher-awarded points
        total_score = mcq_score
        for i, answer in enumerate(submitted_answers):
            if answer['type'] == 'open_ended':
                try:
                    awarded_points = int(request.form.get(f'awarded_points_{i}', 0))

                    # Per-question limit check
                    if awarded_points > answer['points']:
                        flash(f"Points for question {i+1} cannot exceed {answer['points']}.", 'danger')
                        return redirect(url_for('main.teacher_grade_submission', submission_id=submission.id))

                    answer['awarded_points'] = awarded_points
                    total_score += awarded_points

                except (ValueError, TypeError):
                    flash(f"Invalid score for question {i+1}. Please enter a valid number.", 'danger')
                    return redirect(url_for('main.teacher_grade_submission', submission_id=submission.id))

        # Step 3: Total quiz score limit check
        quiz_total_points = sum(a['points'] for a in submitted_answers)
        if total_score > quiz_total_points:
            flash(f"Total score {total_score} exceeds quiz maximum of {quiz_total_points}.", 'danger')
            return redirect(url_for('main.teacher_grade_submission', submission_id=submission.id))

        # Step 4: Save updated score
        submission.score = total_score
        submission.submitted_answers_json = json.dumps(submitted_answers)
        submission.is_graded = True
        db.session.commit()

        flash("Submission graded successfully!", 'success')
        return redirect(url_for('main.view_quiz_submissions', quiz_id=quiz.id))

    return render_template(
        'quizzes/teacher_grade_submission.html',
        title=f'Grade Submission for {submission.quiz.title}',
        submission=submission,
        submitted_answers=submitted_answers
    )

@main_bp.route('/teacher/quizzes/<int:quiz_id>/submissions')
@login_required
def view_quiz_submissions(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if not (current_user.role == 'admin' or (current_user.role == 'teacher' and quiz.course.created_by_user_id == current_user.id)):
        flash("You do not have permission to view submissions for this quiz.", 'danger')
        return redirect(url_for('main.dashboard'))
    
    submissions = QuizSubmission.query.filter_by(quiz_id=quiz.id).all()
    quiz_questions = json.loads(quiz.questions_json)
    total_possible_score_mcq = sum(q.get('points', 1) for q in quiz_questions if q['type'] == 'multiple_choice')
    total_possible_score_open_ended = sum(q.get('points', 1) for q in quiz_questions if q['type'] == 'open_ended')
    total_possible_score = total_possible_score_mcq + total_possible_score_open_ended

    return render_template('quizzes/view_quiz_submissions.html', 
                            title=f'Submissions for {quiz.title}', 
                            quiz=quiz, 
                            submissions=submissions,
                            submission_dates=[s.submission_dates for s in submissions],
                            total_possible_score=total_possible_score,
                            total_possible_score_mcq=total_possible_score_mcq)

@main_bp.route('/teacher/quizzes/results/<int:submission_id>')
@login_required
def teacher_quiz_results(submission_id):
    submission = QuizSubmission.query.get_or_404(submission_id)
    quiz = submission.quiz
    
    if not (current_user.role == 'admin' or (current_user.role == 'teacher' and quiz.course.created_by_user_id == current_user.id)):
        flash("You do not have permission to view these results.", 'danger')
        return redirect(url_for('main.dashboard'))

    submitted_answers = json.loads(submission.submitted_answers_json)
    quiz_questions = json.loads(quiz.questions_json)
    total_possible_score = sum(q.get('points', 1) for q in quiz_questions)
    
    return render_template('quizzes/teacher_quiz_results.html', 
                            title=f'Quiz Results: {quiz.title}', 
                            submission=submission, 
                            submitted_answers=submitted_answers,
                            total_possible_score=total_possible_score)

@main_bp.route('/upload-lesson-file', methods=['POST'])
@login_required
def upload_lesson_file():
    """
    Handles file uploads from the TinyMCE editor for embedding media
    within a lesson's description.

    This function reuses the core logic of `upload_file_tinymce`
    to convert videos and create thumbnails.
    """
    # Simply call the existing, reusable file upload function
    return upload_file_tinymce()

@main_bp.route('/course/<int:course_id>/lessons', methods=['GET'])
@login_required
def view_lessons(course_id):
    """
    Displays all lessons for a specific course.
    Accessible to both teachers (who created the course) and enrolled students.
    """
    course = Course.query.get_or_404(course_id)

    # Permission check: A teacher can view if they created the course.
    # A student can view if they are enrolled.
    if current_user.role == 'teacher' and course.created_by_user_id != current_user.id:
        flash("You do not have permission to view this course's lessons.", 'danger')
        return redirect(url_for('main.teacher_dashboard'))
    
    if current_user.role == 'student':
        enrolled = Enrollment.query.filter_by(user_id=current_user.id, course_id=course_id).first()
        if not enrolled:
            flash("You are not enrolled in this course.", 'danger')
            return redirect(url_for('main.student_dashboard'))
    
    lessons = Lesson.query.filter_by(course_id=course_id).order_by(Lesson.created_at).all()
    
    return render_template('courses/view_lessons.html', 
                            title=f'Lessons for {course.title}', 
                            course=course, 
                            lessons=lessons)
    
@main_bp.route('/lesson/<int:lesson_id>')
@login_required
def view_lesson(lesson_id):
    """
    Displays a single lesson's content.
    Accessible to enrolled students and the course's teacher.
    """
    lesson = Lesson.query.get_or_404(lesson_id)
    course = lesson.course

    # Permission check for students
    if current_user.role == 'student':
        enrolled = Enrollment.query.filter_by(user_id=current_user.id, course_id=course.id).first()
        if not enrolled:
            flash("You are not enrolled in this course.", 'danger')
            return redirect(url_for('main.student_dashboard'))
    
    # Permission check for teachers (course creator can also view)
    if current_user.role == 'teacher' and course.created_by_user_id != current_user.id:
        flash("You do not have permission to view this lesson.", 'danger')
        return redirect(url_for('main.teacher_dashboard'))

    return render_template('courses/view_lesson.html', 
                            title=lesson.title, 
                            lesson=lesson,
                            course=course)



@main_bp.route('/course/<int:course_id>/lessons/create', methods=['GET', 'POST'])
@login_required
def create_lesson(course_id):
    """
    Allows a teacher to create a new lesson for their course.
    """
    course = Course.query.get_or_404(course_id)
    if not (current_user.role == 'teacher' and course.created_by_user_id == current_user.id):
        flash("You do not have permission to create lessons for this course.", 'danger')
        return redirect(url_for('main.teacher_dashboard'))

    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        
        if not title or not content:
            flash('Title and content are required.', 'danger')
            return redirect(url_for('main.create_lesson', course_id=course_id, course=course))

        new_lesson = Lesson(title=title, content=content, course_id=course_id)
        db.session.add(new_lesson)
        db.session.commit()
        flash('Lesson created successfully!', 'success')
        return redirect(url_for('main.view_lessons', course_id=course_id, course=course))

    return render_template('courses/create_lesson.html', title='Create New Lesson', course=course)


@main_bp.route('/lesson/<int:lesson_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_lesson(lesson_id):
    """
    Allows a teacher to edit an existing lesson.
    """
    lesson = Lesson.query.get_or_404(lesson_id)
    course = lesson.course

    if not (current_user.role == 'teacher' and course.created_by_user_id == current_user.id):
        flash("You do not have permission to edit this lesson.", 'danger')
        return redirect(url_for('main.teacher_dashboard'))

    if request.method == 'POST':
        lesson.title = request.form.get('title')
        lesson.content = request.form.get('content')
        db.session.commit()
        flash('Lesson updated successfully!', 'success')
        return redirect(url_for('main.view_lessons', course_id=course.id, course=course))

    return render_template('courses/edit_lesson.html', title='Edit Lesson', lesson=lesson, course=course)


@main_bp.route('/lesson/<int:lesson_id>/delete', methods=['POST'])
@login_required
def delete_lesson(lesson_id):
    """
    Allows a teacher to delete a lesson.
    """
    lesson = Lesson.query.get_or_404(lesson_id)
    course = lesson.course

    if not (current_user.role == 'teacher' and course.created_by_user_id == current_user.id):
        flash("You do not have permission to delete this lesson.", 'danger')
        return redirect(url_for('main.teacher_dashboard'))
    
    db.session.delete(lesson)
    db.session.commit()
    flash('Lesson deleted successfully!', 'success')
    return redirect(url_for('main.view_lessons', course_id=course.id,))

@main_bp.route('/upload-assignment-file', methods=['POST'])
@login_required
def upload_assignment_file():
    """
    Handles file uploads from the TinyMCE editor for embedding media
    within an assignment's description.
    
    This function reuses the core logic of `upload_file_tinymce`
    to convert videos and create thumbnails.
    """
    # Simply call the existing, reusable file upload function
    return upload_file_tinymce()

@main_bp.route('/course/<int:course_id>/assignments')
@login_required
def view_assignments(course_id):
    """
    Displays a list of all assignments for a given course.
    """
    course = Course.query.get_or_404(course_id)
    assignments = Assignment.query.filter_by(course_id=course.id).order_by(Assignment.due_date.asc()).all()
    
    # Check if user is enrolled or is the teacher
    if current_user.role == 'student':
        enrollment = Enrollment.query.filter_by(user_id=current_user.id, course_id=course.id).first()
        if not enrollment:
            flash("You are not enrolled in this course.", 'danger')
            return redirect(url_for('main.student_dashboard'))
    elif current_user.role == 'teacher' and course.created_by_user_id != current_user.id:
        flash("You do not have permission to view assignments for this course.", 'danger')
        return redirect(url_for('main.teacher_dashboard'))
        
    return render_template('assignments/view_assignments.html', course=course, assignments=assignments)

@main_bp.route('/course/<int:course_id>/assignments/create', methods=['GET', 'POST'])
@login_required
def create_assignment(course_id):
    """
    Allows a teacher to create a new assignment for their course.
    """
    course = Course.query.get_or_404(course_id)
    if not (current_user.role == 'teacher' and course.created_by_user_id == current_user.id):
        flash("You do not have permission to create assignments for this course.", 'danger')
        return redirect(url_for('main.teacher_dashboard'))

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        due_date_str = request.form.get('due_date')
        max_submissions = request.form.get('max_submissions') # Get new field
        
        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            max_submissions = int(max_submissions) if max_submissions.strip() else 1 # Convert to int, default to 1
        except (ValueError, TypeError):
            flash('Invalid date or submission format. Please check your inputs.', 'danger')
            return redirect(url_for('main.create_assignment', course_id=course_id))

        if not title or not description:
            flash('Title and description are required.', 'danger')
            return redirect(url_for('main.create_assignment', course_id=course_id))

        file_path = None
        if 'file' in request.files and request.files['file'].filename != '':
            file = request.files['file']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_filename = str(uuid.uuid4()) + '_' + filename
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(filepath)
                file_path = unique_filename
            else:
                flash('Invalid file type for assignment. Allowed types are: ' + ', '.join(ALLOWED_EXTENSIONS), 'danger')
                return redirect(url_for('main.create_assignment', course_id=course_id))

        new_assignment = Assignment(
            title=title, 
            description=description, 
            due_date=due_date, 
            course_id=course_id, 
            file_path=file_path,
            max_submissions=max_submissions # Save new field
        )
        db.session.add(new_assignment)
        db.session.commit()
        flash('Assignment created successfully!', 'success')
        return redirect(url_for('main.view_assignments', course_id=course_id))

    return render_template('assignments/create_assignment.html', title='Create New Assignment', course=course)

@main_bp.route('/assignment/<int:assignment_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_assignment(assignment_id):
    """
    Allows a teacher to edit an existing assignment.
    """
    assignment = Assignment.query.get_or_404(assignment_id)
    course = assignment.course

    if not (current_user.role == 'teacher' and course.created_by_user_id == current_user.id):
        flash("You do not have permission to edit this assignment.", 'danger')
        return redirect(url_for('main.teacher_dashboard'))

    if request.method == 'POST':
        assignment.title = request.form.get('title')
        assignment.description = request.form.get('description')
        due_date_str = request.form.get('due_date')
        max_submissions = request.form.get('max_submissions') # Get new field
        
        try:
            assignment.due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            assignment.max_submissions = int(max_submissions) if max_submissions.strip() else 1 # Save new field
        except (ValueError, TypeError):
            flash('Invalid date or submission format. Please check your inputs.', 'danger')
            return redirect(url_for('main.edit_assignment', assignment_id=assignment_id))

        # Handle file upload for editing
        if 'file' in request.files and request.files['file'].filename != '':
            file = request.files['file']
            if file and allowed_file(file.filename):
                if assignment.file_path:
                    old_filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], assignment.file_path)
                    if os.path.exists(old_filepath):
                        os.remove(old_filepath)
                
                filename = secure_filename(file.filename)
                unique_filename = str(uuid.uuid4()) + '_' + filename
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(filepath)
                assignment.file_path = unique_filename
            else:
                flash('Invalid file type for assignment. Allowed types are: ' + ', '.join(ALLOWED_EXTENSIONS), 'danger')
                return redirect(url_for('main.edit_assignment', assignment_id=assignment_id))
        
        db.session.commit()
        flash('Assignment updated successfully!', 'success')
        return redirect(url_for('main.view_assignments', course_id=course.id))

    return render_template('assignments/edit_assignment.html', title='Edit Assignment', assignment=assignment, course=course)


# NEW: This route handles deleting an assignment
@main_bp.route('/assignment/<int:assignment_id>/delete', methods=['POST'])
@login_required
def delete_assignment(assignment_id):
    """
    Allows a teacher to delete an assignment.
    """
    assignment = Assignment.query.get_or_404(assignment_id)
    course = assignment.course
    
    if not (current_user.role == 'teacher' and course.created_by_user_id == current_user.id):
        flash("You do not have permission to delete this assignment.", 'danger')
        return redirect(url_for('main.teacher_dashboard'))

    # Delete associated student submissions first
    submissions = AssignmentSubmission.query.filter_by(assignment_id=assignment.id).all()
    for submission in submissions:
        # Delete the file from the filesystem
        if submission.file_path:
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], submission.file_path)
            if os.path.exists(file_path):
                os.remove(file_path)
        db.session.delete(submission)

    # Delete the teacher's uploaded file
    if assignment.file_path:
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], assignment.file_path)
        if os.path.exists(file_path):
            os.remove(file_path)

    db.session.delete(assignment)
    db.session.commit()
    flash('Assignment and all related submissions deleted successfully!', 'success')
    return redirect(url_for('main.view_assignments', course_id=course.id))


# NEW: This route handles a teacher grading a submission
@main_bp.route('/assignment/submission/<int:submission_id>/grade', methods=['POST'])
@login_required
def grade_submission(submission_id):
    """
    Allows a teacher to grade a student's assignment submission.
    """
    submission = AssignmentSubmission.query.get_or_404(submission_id)
    assignment = submission.assignment
    course = assignment.course
    
    if not (current_user.role == 'teacher' and course.created_by_user_id == current_user.id):
        flash("You do not have permission to grade this submission.", 'danger')
        return redirect(url_for('main.teacher_dashboard'))

    grade = request.form.get('grade')
    feedback = request.form.get('feedback')

    try:
        # Ensure grade is a valid number between 0 and 100
        grade = int(grade)
        if not (0 <= grade <= 100):
            raise ValueError
    except (ValueError, TypeError):
        flash('Invalid grade. Please enter a number between 0 and 100.', 'danger')
        return redirect(url_for('main.view_assignment', assignment_id=assignment.id))

    submission.grade = grade
    submission.feedback = feedback
    db.session.commit()
    flash('Grade and feedback submitted successfully!', 'success')
    return redirect(url_for('main.view_assignment', assignment_id=assignment.id))

@main_bp.route('/assignment/<int:assignment_id>', methods=['GET', 'POST'])
@login_required
def view_assignment(assignment_id):
    """
    Displays an assignment and allows students to submit their work.
    """
    assignment = Assignment.query.get_or_404(assignment_id)
    course = assignment.course
    
    # Permission check for students
    if current_user.role == 'student':
        enrolled = Enrollment.query.filter_by(user_id=current_user.id, course_id=course.id).first()
        if not enrolled:
            flash("You are not enrolled in this course.", 'danger')
            return redirect(url_for('main.student_dashboard'))
    
    # Permission check for teachers (course creator can also view)
    if current_user.role == 'teacher' and course.created_by_user_id != current_user.id:
        flash("You do not have permission to view this assignment.", 'danger')
        return redirect(url_for('main.teacher_dashboard'))
    
    # Get all existing submissions for this student
    student_submissions = AssignmentSubmission.query.filter_by(
        assignment_id=assignment.id,
        student_id=current_user.id
    ).order_by(AssignmentSubmission.submission_date.desc()).all()
    
    current_submission = student_submissions[0] if student_submissions else None
    submission_count = len(student_submissions)
    
    if request.method == 'POST':
        if datetime.utcnow() > assignment.due_date:
            flash("Submission failed: The assignment due date has passed.", 'danger')
            return redirect(url_for('main.view_assignment', assignment_id=assignment.id))
        
        # Check if the student has reached the submission limit
        if current_user.role == 'student' and submission_count >= assignment.max_submissions:
            flash(f"Submission failed: You have already submitted {submission_count} times, which is the maximum allowed.", 'danger')
            return redirect(url_for('main.view_assignment', assignment_id=assignment.id))

        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_extension = filename.split('.')[-1]
            unique_filename = f"{uuid.uuid4().hex}_{current_user.id}_{assignment.id}.{file_extension}"
            
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(filepath)
            
            # Create a new submission record
            new_submission = AssignmentSubmission(
                assignment_id=assignment.id,
                student_id=current_user.id,
                file_path=unique_filename
            )
            db.session.add(new_submission)
            
            # The feedback will be a flash message for now
            flash(f'Your assignment has been submitted successfully! You have {assignment.max_submissions - (submission_count + 1)} attempts remaining.', 'success')
            
            db.session.commit()
            return redirect(url_for('main.view_assignment', assignment_id=assignment.id))
        else:
            flash('Invalid file type. Allowed file types are: ' + ', '.join(ALLOWED_EXTENSIONS), 'danger')
            return redirect(request.url)

    submissions_for_teacher = None
    if current_user.role == 'teacher':
        submissions_for_teacher = AssignmentSubmission.query.filter_by(assignment_id=assignment.id).order_by(AssignmentSubmission.submission_date.desc()).all()

    return render_template('assignments/view_assignment.html',
                            title=assignment.title,
                            assignment=assignment,
                            course=course,
                            submission=current_submission, # The most recent submission
                            submissions_for_teacher=submissions_for_teacher, # For the teacher's view
                            submission_count=submission_count, # Pass the student's submission count
                            now=datetime.utcnow())

# This route is correct now because the database is storing the correct filename
@main_bp.route('/assignments/download/<string:filename>')
@login_required
def download_assignment_file(filename):
    """
    Allows a user to download an assignment file securely.
    """
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(file_path):
        flash('The file you requested could not be found.', 'danger')
        # A 404 is good for testing, but a redirect is better for users.
        # Let's redirect to the previous page.
        if request.referrer:
            return redirect(request.referrer)
        else:
            return redirect(url_for('main.teacher_dashboard'))
        
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@main_bp.route('/course/discussion/select_course', methods=['GET'])
@login_required
def select_course_for_discussion():
    """
    Shows a list of courses for the teacher to select from,
    before creating a new discussion post.
    """
    if current_user.role != 'teacher':
        flash("You do not have permission to view this page.", 'danger')
        return redirect(url_for('main.index'))
    
    courses = Course.query.filter_by(created_by_user_id=current_user.id).all()
    
    return render_template('discussions/select_course_for_discussion.html',
                            title='Select a Course to Create a Discussion Post',
                            courses=courses)

@main_bp.route('/course/<int:course_id>/discussion', methods=['GET', 'POST'])
@login_required
def discussion_board(course_id):
    """
    Displays the discussion board for a specific course.
    
    It retrieves the course and all its discussion posts to render the page.
    """
    course = Course.query.get_or_404(course_id)
    
    # Check if the user is a teacher of the course or a student enrolled in it
    is_teacher = course.teacher == current_user
    is_student = course in current_user.enrolled_courses.all()
    
    if not is_teacher and not is_student:
        flash('You do not have access to this course.', 'danger')
        return redirect(url_for('main.dashboard'))
        
    # Get all discussion posts for the course, ordered by creation date
    discussion_posts = DiscussionPost.query.filter_by(course_id=course_id).order_by(desc(DiscussionPost.created_at)).all()
    
    return render_template('discussions/discussion_board.html', course=course, discussion_posts=discussion_posts)

# Route to handle the creation of a new discussion post
@main_bp.route('/course/<int:course_id>/discussion/new', methods=['POST'])
@login_required
def create_discussion_post(course_id):
    """
    Handles the form submission for a new discussion post.
    """
    course = Course.query.get_or_404(course_id)
    
    is_teacher = course.teacher == current_user
    is_student = course in current_user.enrolled_courses.all()
    
    if not is_teacher and not is_student:
        flash('You do not have access to this course.', 'danger')
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        title = request.form.get('post-title')
        content = request.form.get('post-content')
        
        if not title or not content:
            flash('Title and content are required.', 'danger')
            return redirect(url_for('main.discussion_board', course_id=course_id))
            
        new_post = DiscussionPost(
            title=title,
            content=content,
            author_id=current_user.id,
            course_id=course.id
        )
        
        db.session.add(new_post)
        db.session.commit()
        
        flash('Discussion topic created successfully!', 'success')
        return redirect(url_for('main.discussion_board', course_id=course_id))
        
# Route to view a single discussion post and its replies
@main_bp.route('/discussion_post/<int:post_id>', methods=['GET'])
@login_required
def view_discussion_post(post_id):
    """
    Displays a single discussion post and all its replies.
    """
    post = DiscussionPost.query.get_or_404(post_id)
    course = post.course
    
    is_teacher = course.teacher == current_user
    is_student = course in current_user.enrolled_courses.all()
    
    if not is_teacher and not is_student:
        flash('You do not have access to this course.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    return render_template('discussions/view_discussion_post.html', post=post)

@main_bp.route('/discussion_post/<int:post_id>/reply', methods=['POST'])
@login_required
def add_reply(post_id):
    """
    Handles the form submission for a new reply to a discussion post.
    """
    post = DiscussionPost.query.get_or_404(post_id)
    course = post.course
    
    is_teacher = course.teacher == current_user
    is_student = course in current_user.enrolled_courses.all()
    
    if not is_teacher and not is_student:
        flash('You do not have access to this course.', 'danger')
        return redirect(url_for('main.dashboard'))
        
    if request.method == 'POST':
        content = request.form.get('reply-content')
        parent_reply_id = request.form.get('parent_reply_id') # Get the parent reply ID
        
        if not content:
            flash('Reply content cannot be empty.', 'danger')
            return redirect(url_for('main.view_discussion_post', post_id=post.id))
            
        new_reply = Reply(
            content=content,
            author_id=current_user.id,
            post_id=post.id,
            parent_reply_id=parent_reply_id if parent_reply_id else None
        )
        
        db.session.add(new_reply)
        db.session.commit()
        
        flash('Reply submitted successfully!', 'success')
        return redirect(url_for('main.view_discussion_post', post_id=post.id))

@main_bp.route('/delete-reply/<int:reply_id>/<int:post_id>', methods=['GET'])
@login_required
def delete_reply(reply_id, post_id):
    """
    Deletes a reply from a discussion post.
    
    This function is only accessible to the author of the reply.
    It takes the reply ID and post ID from the URL.
    """
    reply_to_delete = Reply.query.get_or_404(reply_id)

    # Check if the current user is the author of the reply
    if reply_to_delete.author_id != current_user.id:
        flash('You are not authorized to delete this reply.', 'danger')
        return redirect(url_for('main.view_discussion_post', post_id=post_id))

    try:
        db.session.delete(reply_to_delete)
        db.session.commit()
        flash('Reply has been successfully deleted!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while deleting the reply: {e}', 'danger')

    return redirect(url_for('main.view_discussion_post', post_id=post_id))

@main_bp.route('/edit-reply/<int:reply_id>/<int:post_id>', methods=['POST'])
@login_required
def edit_reply(reply_id, post_id):
    """
    Edits an existing reply.
    
    This function is only accessible to the author of the reply.
    It takes the reply ID and post ID from the URL and new content from the form.
    """
    reply_to_edit = Reply.query.get_or_404(reply_id)

    # Check if the current user is the author of the reply
    if reply_to_edit.author_id != current_user.id:
        flash('You are not authorized to edit this reply.', 'danger')
        return redirect(url_for('main.view_discussion_post', post_id=post_id))

    try:
        new_content = request.form.get('edit-content')
        if new_content:
            reply_to_edit.content = new_content
            db.session.commit()
            flash('Reply has been successfully updated!', 'success')
        else:
            flash('Reply content cannot be empty.', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while updating the reply: {e}', 'danger')

    return redirect(url_for('main.view_discussion_post', post_id=post_id))

@main_bp.route('/discussion/file/download/<string:filename>')
@login_required
def download_discussion_file(filename):
    """
    Allows a user to download a discussion file securely.
    """
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(file_path):
        flash('The file you requested could not be found.', 'danger')
        # A 404 is good for testing, but a redirect is better for users.
        # Let's redirect to the previous page.
        if request.referrer:
            return redirect(request.referrer)
        else:
            return redirect(url_for('main.view_discussion_post'))

    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@main_bp.route('/course/announcements/select_course', methods=['GET'])
@login_required
def select_course_for_announcement():
    """
    Shows a list of courses for the teacher to select from,
    before creating a new announcement.
    """
    if current_user.role != 'teacher':
        flash("You do not have permission to view this page.", 'danger')
        return redirect(url_for('main.index'))
    
    courses = Course.query.filter_by(created_by_user_id=current_user.id).all()
    
    return render_template('announcements/select_course_for_announcement.html',
                            title='Select a Course to Create an Announcement Post',
                            courses=courses)

@main_bp.route('/course/<int:course_id>/announcements')
@login_required
def view_announcements(course_id):
    """
    Displays all announcements for a given course.
    """
    course = Course.query.get_or_404(course_id)
    announcements = Announcement.query.filter_by(course_id=course_id).order_by(Announcement.created_at.desc()).all()
    
    # Check if the current user is an instructor for this course
    is_instructor = current_user.role == 'instructor' and course in current_user.instructed_courses
    
    return render_template('announcements/announcements.html', course=course, announcements=announcements, is_instructor=is_instructor)


@main_bp.route('/course/<int:course_id>/announcements/create', methods=['GET', 'POST'])
@login_required
def create_announcement(course_id):
    """
    Handles the creation of a new announcement for a course.
    Only instructors of the course can create announcements.
    """
    course = Course.query.get_or_404(course_id)
    
    # Check if the current user is an instructor for this course
    if not (current_user.role == 'teacher' or current_user.role == 'admin') and course not in current_user.courses:
        flash('You are not authorized to create announcements for this course.', 'danger')
        return redirect(url_for('main.view_announcements', course_id=course_id))

    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        
        if not title or not content:
            flash('Title and content are required for an announcement.', 'warning')
            return redirect(url_for('main.create_announcement', course_id=course_id))

        new_announcement = Announcement(
            title=title,
            content=content,
            course_id=course_id,
            author_id=current_user.id
        )
        
        try:
            db.session.add(new_announcement)
            db.session.commit()
            flash('Announcement created successfully!', 'success')
            return redirect(url_for('main.view_announcements', course_id=course_id))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {e}', 'danger')

    return render_template('announcements/create_announcement.html', course=course)


@main_bp.route('/announcements/<int:announcement_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_announcement(announcement_id):
    """
    Allows the author of an announcement to edit its content.
    """
    announcement = Announcement.query.get_or_404(announcement_id)
    
    # Check if the current user is the author
    if announcement.author_id != current_user.id:
        flash('You are not authorized to edit this announcement.', 'danger')
        return redirect(url_for('main.view_announcements', course_id=announcement.course_id))
    
    if request.method == 'POST':
        announcement.title = request.form.get('title')
        announcement.content = request.form.get('content')
        
        try:
            db.session.commit()
            flash('Announcement updated successfully!', 'success')
            return redirect(url_for('main.view_announcements', course_id=announcement.course_id))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {e}', 'danger')

    return render_template('announcements/edit_announcement.html', announcement=announcement)


@main_bp.route('/announcements/<int:announcement_id>/delete', methods=['POST'])
@login_required
def delete_announcement(announcement_id):
    """
    Allows the author of an announcement to delete it.
    """
    announcement = Announcement.query.get_or_404(announcement_id)
    
    # Check if the current user is the author
    if announcement.author_id != current_user.id:
        flash('You are not authorized to delete this announcement.', 'danger')
        return redirect(url_for('main.view_announcements', course_id=announcement.course_id))

    try:
        db.session.delete(announcement)
        db.session.commit()
        flash('Announcement deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred: {e}', 'danger')

    return redirect(url_for('main.view_announcements', course_id=announcement.course_id))

@main_bp.route('/@me/dashboard')
@login_required
def student_progress_dashboard():
    """
    Displays a personalized dashboard for a student, showing their progress.
    """
    if current_user.role != 'student':
        # You could redirect them to their own dashboard or homepage
        return redirect(url_for('main.index'))

    student_courses = current_user.enrolled_courses.all()
    dashboard_data = []

    for course in student_courses:
        assignments = Assignment.query.filter_by(course_id=course.id).all()
        quizzes = Quiz.query.filter_by(course_id=course.id).all()
        lessons = Lesson.query.filter_by(course_id=course.id).all()
        
        # Get discussion activity for the student in this course
        discussion_posts = DiscussionPost.query.filter_by(course_id=course.id, author_id=current_user.id).count()
        discussion_replies = Reply.query.filter_by(post_id=DiscussionPost.id, author_id=current_user.id).join(DiscussionPost).filter(DiscussionPost.course_id == course.id).count()

        course_assignments_data = []
        for assignment in assignments:
            submission = AssignmentSubmission.query.filter_by(
                assignment_id=assignment.id,
                student_id=current_user.id
            ).first()
            course_assignments_data.append({
                'assignment': assignment,
                'submission': submission,
                'status': 'Graded' if submission and submission.grade is not None else 'Submitted' if submission else 'Not Submitted'
            })

        course_quizzes_data = []
        for quiz in quizzes:
            submission = QuizSubmission.query.filter_by(
                quiz_id=quiz.id,
                student_id=current_user.id
            ).first()
            course_quizzes_data.append({
                'quiz': quiz,
                'submission': submission,
                'status': 'Graded' if submission and submission.is_graded else 'Submitted' if submission else 'Not Submitted'
            })

        dashboard_data.append({
            'course': course,
            'assignments': course_assignments_data,
            'quizzes': course_quizzes_data,
            'total_lessons': len(lessons),
            'discussion_posts': discussion_posts,
            'discussion_replies': discussion_replies
        })

    return render_template('student/progress_report.html', dashboard_data=dashboard_data)

@main_bp.route('/@me/dashboard/download/csv')
@login_required
def download_progress_csv():
    """
    Generates and downloads a CSV file of the student's progress.
    """
    if current_user.role != 'student':
        return redirect(url_for('main.index'))

    student_courses = current_user.enrolled_courses.all()
    
    csv_output = io.StringIO()
    writer = csv.writer(csv_output)
    writer.writerow(['Course', 'Assignment', 'Status', 'Grade', 'Quiz', 'Quiz Score', 'Lessons Total', 'Discussion Posts', 'Discussion Replies'])

    for course in student_courses:
        assignments = Assignment.query.filter_by(course_id=course.id).all()
        quizzes = Quiz.query.filter_by(course_id=course.id).all()
        lessons_count = Lesson.query.filter_by(course_id=course.id).count()
        discussion_posts = DiscussionPost.query.filter_by(course_id=course.id, author_id=current_user.id).count()
        discussion_replies = Reply.query.filter_by(author_id=current_user.id).join(DiscussionPost).filter(DiscussionPost.course_id == course.id).count()

        # Combine all items to create a single row for each course-item
        all_items = [(a, None) for a in assignments] + [(None, q) for q in quizzes]
        
        for item_index, (assignment, quiz) in enumerate(all_items):
            assignment_title = assignment.title if assignment else ""
            assignment_status = "N/A"
            assignment_grade = "N/A"
            quiz_title = quiz.title if quiz else ""
            quiz_score = "N/A"

            if assignment:
                submission = AssignmentSubmission.query.filter_by(
                    assignment_id=assignment.id,
                    student_id=current_user.id
                ).first()
                if submission:
                    assignment_status = "Graded" if submission.grade is not None else "Submitted"
                    assignment_grade = str(submission.grade) if submission.grade is not None else ""
                else:
                    assignment_status = "Not Submitted"

            if quiz:
                submission = QuizSubmission.query.filter_by(
                    quiz_id=quiz.id,
                    student_id=current_user.id
                ).first()
                if submission:
                    quiz_score = str(submission.score)

            if item_index == 0:
                writer.writerow([
                    course.title,
                    assignment_title,
                    assignment_status,
                    assignment_grade,
                    quiz_title,
                    quiz_score,
                    lessons_count,
                    discussion_posts,
                    discussion_replies
                ])
            else:
                writer.writerow([
                    "",  # Empty course title for subsequent rows
                    assignment_title,
                    assignment_status,
                    assignment_grade,
                    quiz_title,
                    quiz_score,
                    "", # Empty for subsequent rows
                    "", # Empty for subsequent rows
                    ""  # Empty for subsequent rows
                ])


    output = csv_output.getvalue()
    return Response(output, mimetype="text/csv", headers={"Content-disposition": "attachment; filename=student_progress.csv"})

@main_bp.route('/@me/dashboard/download/pdf')
@login_required
def download_progress_pdf():
    """
    Generates and downloads a PDF file of the student's progress.
    """
    if current_user.role != 'student':
        return redirect(url_for('main.index'))

    student_courses = current_user.enrolled_courses.all()
    dashboard_data = []

    for course in student_courses:
        assignments = Assignment.query.filter_by(course_id=course.id).all()
        quizzes = Quiz.query.filter_by(course_id=course.id).all()
        lessons = Lesson.query.filter_by(course_id=course.id).all()

        # Get discussion activity for the student in this course
        discussion_posts = DiscussionPost.query.filter_by(course_id=course.id, author_id=current_user.id).count()
        discussion_replies = Reply.query.filter_by(post_id=DiscussionPost.id, author_id=current_user.id).join(DiscussionPost).filter(DiscussionPost.course_id == course.id).count()

        course_assignments_data = []
        for assignment in assignments:
            submission = AssignmentSubmission.query.filter_by(
                assignment_id=assignment.id,
                student_id=current_user.id
            ).first()
            course_assignments_data.append({
                'assignment': assignment,
                'submission': submission,
                'status': 'Graded' if submission and submission.grade is not None else 'Submitted' if submission else 'Not Submitted'
            })

        course_quizzes_data = []
        for quiz in quizzes:
            submission = QuizSubmission.query.filter_by(
                quiz_id=quiz.id,
                student_id=current_user.id
            ).first()
            course_quizzes_data.append({
                'quiz': quiz,
                'submission': submission,
                'status': 'Graded' if submission and submission.is_graded else 'Submitted' if submission else 'Not Submitted'
            })

        dashboard_data.append({
            'course': course,
            'assignments': course_assignments_data,
            'quizzes': course_quizzes_data,
            'total_lessons': len(lessons),
            'discussion_posts': discussion_posts,
            'discussion_replies': discussion_replies
        })

    # Render the progress data to a simple HTML template for PDF conversion
    html_content = render_template('student/pdf_template.html', dashboard_data=dashboard_data, current_user=current_user)

    # Use WeasyPrint to generate the PDF
    pdf = HTML(string=html_content, base_url=request.url).write_pdf(stylesheets=[CSS(string='''
        body { font-family: sans-serif; }
        h1 { text-align: center; }
        .course-card { margin-bottom: 20px; border: 1px solid #ccc; padding: 15px; }
        .course-title { font-size: 1.2em; font-weight: bold; }
        ul { list-style-type: none; padding-left: 0; }
        li { margin-bottom: 5px; }
    ''')])

    return Response(pdf, mimetype="application/pdf", headers={"Content-disposition": "attachment; filename=student_progress.pdf"})

@main_bp.route('/calendar')
@login_required
def calendar():
    """
    Renders the calendar page for the logged-in user.
    """
    return render_template('calendar/calendar.html')

@main_bp.route('/admin/general_announcements', methods=['GET', 'POST'])
@login_required
def admin_general_announcements():
    """
    Allows admins to create general announcements.
    """
    # Restrict this route to admins only
    if current_user.role != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        if not title or not content:
            flash('Title and content are required.', 'danger')
        else:
            new_announcement = GeneralAnnouncement(
                title=title,
                content=content,
                author_id=current_user.id
            )
            db.session.add(new_announcement)
            db.session.commit()
            flash('General announcement created successfully!', 'success')
            return redirect(url_for('main.admin_general_announcements'))

    # Retrieve all existing general announcements to display on the page
    general_announcements = GeneralAnnouncement.query.order_by(GeneralAnnouncement.created_at.desc()).all()
    return render_template('dashboards/admin_general_announcements.html', general_announcements=general_announcements)

@main_bp.route('/view_general_announcement/<int:announcement_id>')
@login_required
def view_general_announcement(announcement_id):
    """
    Renders a page to view a single general announcement.
    """
    announcement = GeneralAnnouncement.query.get_or_404(announcement_id)
    return render_template('dashboards/view_general_announcement.html', announcement=announcement)

@main_bp.route('/api/calendar/events')
@login_required
def api_calendar_events():
    """
    Returns a JSON list of all calendar events for the user's enrolled courses,
    plus general announcements.
    """
    all_events = []
    
    # 1. Fetch all General Announcements
    general_announcements = GeneralAnnouncement.query.all()
    for ann in general_announcements:
        all_events.append({
            'id': f"general_announcement-{ann.id}",
            'title': f"[General Announcement] {ann.title}",
            'start': ann.created_at.isoformat(),
            'end': ann.created_at.isoformat(),
            'allDay': True,
            'color': '#ffbe0b', # A distinct color for general announcements
            'url': url_for('main.view_general_announcement', announcement_id=ann.id),
            'description': ann.content
        })

    user_courses = current_user.enrolled_courses.all()
    for course in user_courses:
        # 2. Fetch course-specific Announcements
        for ann in course.course_announcements:
            all_events.append({
                'id': f"course_announcement-{ann.id}",
                'title': f"[{course.title}] {ann.title} (by {ann.author.username})",
                'start': ann.created_at.isoformat(),
                'end': ann.created_at.isoformat(),
                'allDay': True,
                'color': '#fb5607', # A distinct color for course announcements
                'url': url_for('main.view_announcements', course_id=course.id), # Placeholder URL, link to the list of announcements
                'description': ann.content
            })

        # 3. Fetch Assignments
        for assignment in course.assignments:
            all_events.append({
                'id': f"assignment-{assignment.id}",
                'title': f"[{course.title}] Due: {assignment.title}",
                'start': assignment.due_date.isoformat(),
                'end': assignment.due_date.isoformat(),
                'allDay': True,
                'color': '#ff006e', # A distinct color for assignments
                'url': url_for('main.view_assignments', course_id=course.id, assignment_id=assignment.id),
                'description': assignment.description
            })

        # 4. Fetch Quizzes
        for quiz in course.quizzes:
            if quiz.due_date: # Only include quizzes with a due date
                all_events.append({
                    'id': f"quiz-{quiz.id}",
                    'title': f"[{course.title}] Quiz: {quiz.title}",
                    'start': quiz.due_date.isoformat(),
                    'end': quiz.due_date.isoformat(),
                    'allDay': True,
                    'color': '#8338ec', # A distinct color for quizzes
                    'url': url_for('main.take_quiz', course_id=course.id, quiz_id=quiz.id),
                    'description': f"Quiz '{quiz.title}' is due."
                })

    return jsonify(all_events)

@main_bp.route('/teacher/course/<int:course_id>/progress_report')
@login_required
def teacher_progress_report(course_id):
    """
    Shows a progress report for all students in a specific course.
    Accessible only to the teacher of that course.
    """
    course = Course.query.get_or_404(course_id)
    if current_user.role != 'teacher' or course.teacher != current_user:
        flash('You do not have permission to view this page.', 'danger')
        return redirect(url_for('main.dashboard'))

    # Fetch all students enrolled in the course
    # The 'enrolled_users' backref on Course provides the list of students
    students = course.enrolled_users.all()
    
    # Fetch all assignments and quizzes for the course
    assignments = course.assignments
    quizzes = course.quizzes

    # Fetch all submissions for these assignments and quizzes in one go
    assignment_submissions = AssignmentSubmission.query.filter(
        AssignmentSubmission.assignment_id.in_([a.id for a in assignments])
    ).options(joinedload(AssignmentSubmission.assignment)).all()
    
    quiz_submissions = QuizSubmission.query.filter(
        QuizSubmission.quiz_id.in_([q.id for q in quizzes])
    ).options(joinedload(QuizSubmission.quiz)).all()

    # Organize submission data for easy access in the template
    progress_data = {}
    for student in students:
        progress_data[student.id] = {
            'student': student,
            'assignments': {sub.assignment_id: sub for sub in assignment_submissions if sub.student_id == student.id},
            'quizzes': {sub.quiz_id: sub for sub in quiz_submissions if sub.student_id == student.id}
        }
    
    return render_template(
        'teacher/progress_report.html',
        course=course,
        students=students,
        assignments=assignments,
        quizzes=quizzes,
        progress_data=progress_data
    )

@main_bp.route('/admin/system_logs')
@login_required
def system_logs():
    """
    Shows a timeline of key system events for the admin.
    """
    if current_user.role != 'admin':
        flash('You do not have permission to view this page.', 'danger')
        return redirect(url_for('main.dashboard'))

    # Fetch ALL recent events from different models (removed .limit(10))
    recent_users = User.query.order_by(User.created_at.desc()).all()
    recent_courses = Course.query.order_by(Course.created_at.desc()).all()
    recent_announcements = GeneralAnnouncement.query.order_by(GeneralAnnouncement.created_at.desc()).all()
    recent_course_announcements = Announcement.query.order_by(Announcement.created_at.desc()).all()
    recent_assignments = Assignment.query.order_by(Assignment.created_at.desc()).all()
    recent_quizzes = Quiz.query.order_by(Quiz.created_at.desc()).all()

    # Combine all events into a single list with correct timestamps and IDs
    all_events = []
    for user in recent_users:
        all_events.append({'timestamp': user.created_at, 'type': 'User Registered', 'description': f'New user: {user.username}', 'model': 'User', 'id': user.id})
    for course in recent_courses:
        all_events.append({'timestamp': course.created_at, 'type': 'Course Created', 'description': f'New course created: {course.title}', 'model': 'Course', 'id': course.id})
    for ann in recent_announcements:
        all_events.append({'timestamp': ann.created_at, 'type': 'General Announcement', 'description': f'Admin posted: {ann.title}', 'model': 'GeneralAnnouncement', 'id': ann.id})
    for ann in recent_course_announcements:
        all_events.append({'timestamp': ann.created_at, 'type': 'Course Announcement', 'description': f'Teacher posted: {ann.title}', 'model': 'Announcement', 'id': ann.id})
    for assign in recent_assignments:
        all_events.append({'timestamp': assign.created_at, 'type': 'Assignment Created', 'description': f'New assignment in "{assign.course.title}": {assign.title}', 'model': 'Assignment', 'id': assign.id})
    for quiz in recent_quizzes:
        all_events.append({'timestamp': quiz.created_at, 'type': 'Quiz Created', 'description': f'New quiz in "{quiz.course.title}": {quiz.title}', 'model': 'Quiz', 'id': quiz.id})

    # Sort the combined list by timestamp in descending order, handling None values
    all_events.sort(key=lambda x: x['timestamp'] if x['timestamp'] is not None else datetime.min, reverse=True)

    return render_template('admin/system_logs.html', logs=all_events)

@main_bp.route('/admin/delete_logs', methods=['POST'])
@login_required
def delete_logs():
    """
    Deletes selected log entries from the database.
    """
    if current_user.role != 'admin':
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('main.dashboard'))

    selected_logs = request.form.getlist('log_entries')
    if not selected_logs:
        flash('No logs were selected for deletion.', 'warning')
        return redirect(url_for('main.system_logs'))

    try:
        for entry in selected_logs:
            model_name, entry_id = entry.split(':')
            entry_id = int(entry_id)

            record = None
            if model_name == 'User':
                record = User.query.get(entry_id)
            # elif model_name == 'Course':
            #     record = Course.query.get(entry_id)
            elif model_name == 'GeneralAnnouncement':
                record = GeneralAnnouncement.query.get(entry_id)
            # elif model_name == 'Announcement':
            #     record = Announcement.query.get(entry_id)
            # elif model_name == 'Assignment':
            #     record = Assignment.query.get(entry_id)
            # elif model_name == 'Quiz':
            #     record = Quiz.query.get(entry_id)
            
            if record: # Check if the record was actually found before trying to delete it
                db.session.delete(record)
        
        db.session.commit()
        flash(f'Successfully deleted {len(selected_logs)} log entries.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred: {e}', 'danger')
    
    return redirect(url_for('main.system_logs'))

@main_bp.route('/profile/<int:user_id>')
@login_required
def user_profile(user_id):
    """
    Shows a detailed profile page for a specific user.
    Accessible to admins, and to a student's class teacher.
    A user can also view their own profile.
    """
    user = User.query.get_or_404(user_id)

    # Permission checks
    is_admin = current_user.role == 'admin'
    is_self = current_user.id == user.id

    # if not is_admin and not is_self:
    #     # We will add logic for a class teacher to view their student's profile here later.
    #     flash('You do not have permission to view this profile.', 'danger')
    #     return redirect(url_for('main.dashboard'))

    # Fetch courses based on the user's role
    courses = []
    if user.role == 'student':
        courses = user.enrolled_courses.all()
    elif user.role == 'teacher':
        courses = user.teaching_courses.all()

    return render_template('profile/user_profile.html', user=user, courses=courses)
