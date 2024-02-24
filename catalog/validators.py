from django.core.exceptions import ValidationError
from django.db import models
import re

isrc_pattern = re.compile(r'^[A-Z]{2}-[A-Z0-9]{3}-\d{2}-\d{5}$')

def validate_isrc(value):
    # Define the ISRC regex pattern
    if not isrc_pattern.match(value):
        raise ValidationError(f'{value} is not a valid ISRC code.')
