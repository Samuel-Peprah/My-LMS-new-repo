from app import create_app  # Import your Flask app factory

app = create_app()  # Initialize your Flask application

if __name__ == "__main__":
    app.run()