# Backend Dockerfile for acrylic-core (Django + Gunicorn + Celery)
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for audio processing and other native libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    pulseaudio \
    libblas3 \
    liblapack3 \
    libatlas3-base \
    libmad0 \
    libid3tag0 \
    libsndfile1 \
    libgd3 \
    libboost-program-options-dev \
    libboost-filesystem-dev \
    libboost-regex-dev \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Fetch and install custom audiowaveform .deb from S3
RUN curl -o /tmp/audiowaveform.deb https://acrylic-private-dev.s3.us-east-1.amazonaws.com/binary/audiowaveform_1.10.2-1jammy1_amd64.deb && \
    dpkg -i /tmp/audiowaveform.deb && \
    rm /tmp/audiowaveform.deb

# Copy requirements and install Python dependencies
COPY requirements.txt .

# setuptools is needed for pkg_resources (required by django-countries)
# Pin whitenoise explicitly (currently transitive via django-heroku)
RUN pip install --no-cache-dir setuptools && pip install --no-cache-dir whitenoise -r requirements.txt

# Copy application code
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput --settings=acrylic.settings

# Copy entrypoint script
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Expose port for Gunicorn
EXPOSE 8000

# Run migrations and start Gunicorn via entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
