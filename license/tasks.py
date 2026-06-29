import logging
from django.conf import settings

logger = logging.getLogger(__name__)

def build_whitelist_email(license_obj):
    """
    Returns (subject, from_email, to_email, body, reply_to) for a License.
    Used by the serializer on create and by the admin resend action.
    """
    club        = license_obj.club
    track       = license_obj.track
    distributor = track.distributor

    # All three platforms are sent to distributor
    platform_lines = []
    if club.instagram_url:
        platform_lines.append(f'  • Instagram: {club.instagram_url}')
    if club.tiktok_url:
        platform_lines.append(f'  • TikTok: {club.tiktok_url}')
    if club.youtube_url:
        platform_lines.append(f'  • YouTube: {club.youtube_url}')

    platforms_block = '\n'.join(platform_lines) if platform_lines else '  (no platforms configured)'

    body = (
        f"Hey {distributor.name},\n\n"
        f"Could you please allowlist the following track from these social channels?\n"
        f"  • Track: {track.name}\n"
        f"  • ISRC: {track.isrc}\n\n"
        f"Please apply this to the following profiles:\n"
        f"{platforms_block}\n\n"
        f"Thanks so much for your help,\n"
        f"Best,\n"
        f"Acrylic"
    )

    subject    = 'Whitelist Request'
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email   = distributor.whitelist_email
    reply_to   = f'whitelist-reply+{license_obj.uuid}@acrylic.la'

    return subject, from_email, to_email, body, reply_to
