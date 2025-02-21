# Use a lightweight Python image
FROM python:3.10

# Set the working directory in the container
WORKDIR /app

# Copy only requirements first (for better caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project files
COPY . .

# Expose the port (if your project runs on a specific port, e.g., 8000)
EXPOSE 8000

# Command to run the application (modify if needed)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
