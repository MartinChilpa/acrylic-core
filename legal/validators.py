

def validate_percent(value, track_id=None):
    """
    Validator for the percent field to ensure all percents for a track sum up to a maximum of 100.00
    """
    # If track_id is not provided, try to extract it from the instance bound to the form
    # This is useful when the validator is used in forms where the track instance is bound
    if not track_id and 'instance' in locals():
        track_id = instance.track_id

    if track_id:
        # Calculate the total percent for the track excluding the current instance if updating
        total_percent = MasterSplit.objects.filter(track_id=track_id).exclude(id=instance.id).aggregate(models.Sum('percent'))['percent__sum'] or 0.0
        
        # Check if the total percent exceeds 100.00 when adding the new value
        if total_percent + value > 100.00:
            raise ValidationError('The total percent for all splits of a track cannot exceed 100.00.')
