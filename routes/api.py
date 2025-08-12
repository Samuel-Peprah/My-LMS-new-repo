# routes/api.py

from flask import Blueprint, jsonify, request
from flask_restful import Api, Resource, reqparse
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from models import User, Course, Enrollment
from extensions import db

api_bp = Blueprint('api', __name__)
api = Api(api_bp)

# API Login Endpoint
class UserLogin(Resource):
    def post(self):
        # Use a request parser to get username and password
        parser = reqparse.RequestParser()
        parser.add_argument('username', type=str, required=True, help="Username is required")
        parser.add_argument('password', type=str, required=True, help="Password is required")
        args = parser.parse_args()

        username = args['username']
        password = args['password']

        user = User.query.filter_by(username=username).first()
        if user is None or not user.check_password(password):
            return {"msg": "Bad username or password"}, 401

        # Create an access token with the user's ID as the identity
        access_token = create_access_token(identity=user.id)
        return {"access_token": access_token}, 200

# A protected API endpoint for testing authentication
class ProtectedResource(Resource):
    @jwt_required()
    def get(self):
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if user:
            return jsonify({"message": f"Hello from! You are user: {user.username} with role: {user.role}"})
        return {"message": "User not found"}, 404

# Course Management Endpoints
class CourseList(Resource):
    # Endpoint to get a list of all courses
    def get(self):
        courses = Course.query.all()
        return jsonify([
            {
                'id': course.id,
                'title': course.title,
                'description': course.description,
                'teacher': course.teacher.username if course.teacher else None
            } for course in courses
        ])

    # Endpoint for a teacher/admin to create a new course
    @jwt_required()
    def post(self):
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        # Only teachers and admins can create courses
        if user.role not in ['admin', 'teacher']:
            return {"msg": "You do not have permission to create courses."}, 403

        parser = reqparse.RequestParser()
        parser.add_argument('title', type=str, required=True, help="Course title is required")
        parser.add_argument('description', type=str, required=False, default='')
        args = parser.parse_args()

        new_course = Course(
            title=args['title'],
            description=args['description'],
            created_by_user_id=user.id
        )
        db.session.add(new_course)
        db.session.commit()

        return {"message": "Course created successfully", "course_id": new_course.id}, 201

# Endpoint for enrolling in a course
class CourseEnroll(Resource):
    @jwt_required()
    def post(self, course_id):
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        course = Course.query.get(course_id)

        if not user or not course:
            return {"msg": "User or Course not found."}, 404

        # Check if the user is already enrolled
        is_enrolled = db.session.query(Enrollment).filter_by(user_id=user.id, course_id=course.id).first()
        if is_enrolled:
            return {"msg": "You are already enrolled in this course."}, 409
        
        # Create a new enrollment record
        enrollment = Enrollment(user_id=user.id, course_id=course.id)
        db.session.add(enrollment)
        db.session.commit()
        
        return {"msg": f"Successfully enrolled in course: {course.title}"}, 200

# Register API resources with the blueprint
api.add_resource(UserLogin, '/login')
api.add_resource(ProtectedResource, '/protected')
api.add_resource(CourseList, '/courses')
api.add_resource(CourseEnroll, '/courses/<int:course_id>/enroll')