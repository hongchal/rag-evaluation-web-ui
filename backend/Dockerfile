FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
# - build-essential: for compiling Python packages
# - curl: for downloading files
# - libgl1: OpenGL library (required by OpenCV/Docling)
# - libglib2.0-0: GLib library (required by OpenCV/Docling)
# - libgomp1: OpenMP library (for performance)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create uploads directory
RUN mkdir -p /app/uploads

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

