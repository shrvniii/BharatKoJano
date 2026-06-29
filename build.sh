#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Compile static files (CSS, JS)
python manage.py collectstatic --no-input

# Run database migrations
python manage.py migrate
