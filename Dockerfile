# Use an official Python runtime as a parent image
FROM python:3.10

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables (Optional)
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=8080

# Expose port 8080 for the Flask app
EXPOSE 8080

# Run app.py when the container launches
# CMD ["python", "app.py"]

# Run the application using Gunicorn with 4 workers
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]