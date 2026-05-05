# Use the official lightweight Python image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file first to leverage Docker cache
COPY requirements.txt .

# Install dependencies without storing cache to keep image small
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project into the container
COPY . .

# Expose port 5000 for the web server
EXPOSE 5000

# Set production environment variables
ENV FLASK_ENV=production
ENV HOST_IP=0.0.0.0
# The SECRET_KEY and AGENT_API_KEY should be passed at runtime using -e flag or a .env file
# ENV SECRET_KEY=your-production-secret-key
# ENV AGENT_API_KEY=your-production-agent-key

# Command to run the Waitress production server
CMD ["python", "backend/app.py"]
