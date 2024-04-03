from hellosign_sdk import HSClient
from django.conf import settings


client = HSClient(api_key=settings.DROPBOX_SIGN_API_KEY)


def send_signature_request_for_ownership_validation(track_id):
    from .models import Track, MasterSplit
    track = Track.objects.get(id=track_id)
    master_splits = MasterSplit.objects.filter(track=track)

    for split in master_splits:
        # Prepare the email and name for the signature request
        signer_email = split.owner_email
        signer_name = split.owner_name
        
        # Define the email subject and message
        email_subject = f"Validate Ownership for {track.name}"
        email_message = f"""
        Dear {signer_name},

        Please validate your ownership of {split.percent}% in the master of track "{track.name}" (ISRC: {track.isrc}) by {track.artist.name}. 

        Click on the link below to validate your ownership:
        [Your validation link here]

        Track information:
        - ISRC: {track.isrc}
        - Name: {track.name}
        - Artist: {track.artist.name}
        - Spotify URL: {track.artist.spotify_url}
        
        Best,
        [Your Company Name]
        """
        
        # Generate the signature request using Dropbox Sign
        response = client.send_signature_request(
            test_mode=True,  # Set to False in production
            title=email_subject,
            subject=email_subject,
            message=email_message,
            signers=[
                {
                    'email_address': signer_email,
                    'name': signer_name
                }
            ],
            files=['/path/to/your/document.pdf']  # Path to the document you want signed
        )
        # save signature
        track.signature_request_id = response.signature_request_id
        track.save()
