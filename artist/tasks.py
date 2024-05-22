import hubspot
from hubspot.crm.contacts import SimplePublicObjectInput, ApiException
from django.conf import settings
from django.urls import reverse


def create_artist_in_hubspot_task(artist_id):

    if settings.HUBSPOT_ACCESS_TOKEN:
        # if the Hubspot integration is being used
        Artist = apps.get_model('artist', 'Artist')
        
        try:
            artist = Artist.objects.get(id=artist_id)
        except Artist.DoesNotExist:
            pass
        else:
            # Initialize the client
            api_client = hubspot.Client.create(access_token=settings.HUBSPOT_ACCESS_TOKEN)

            # Define the contact properties including custom fields
            contact_properties = SimplePublicObjectInput(
                properties={
                    'email': artist.user.email,
                    'firstname': artist.name,
                    'lastname': '',
                    'phone': '',
                    # custom fields
                    'uuid': str(artist.uuid),
                    reverse("admin:artist_artist_change", args=[artist.id])
                }
            )

            try:
                # Create the contact
                api_response = api_client.crm.contacts.basic_api.create(simple_public_object_input=contact_properties)
                print("Contact created with ID:", api_response.id)
            except ApiException as e:
                print("Exception when creating contact: %s\n" % e)
    return True