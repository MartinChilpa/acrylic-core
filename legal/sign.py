from django.apps import apps
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
import weasyprint
from legal.signwell import Signwell


def splitsheet_request_signatures(split_sheet):

    SplitSheet = apps.get_model('legal', 'SplitSheet')

    # avoid repeating signature request for same email in master/publishing splits
    master_emails = split_sheet.master_splits.values_list('email', 'legal_name')
    publishing_emails = split_sheet.publishing_splits.values_list('email', 'legal_name')

    # remove master/publishing duplicates
    emails = list(set(list(master_emails) + list(publishing_emails)))

    # document in PDF format
    html_string = render_to_string('legal/split_sheet_pdf.html', {'split_sheet': split_sheet})
    pdf_file = weasyprint.HTML(string=html_string).write_pdf()

    subject = f'Sign split sheet for track {split_sheet.isrc}'
    message = f"""
        Please sign the split sheet of the track with ISRC {split_sheet.isrc}. 

        Click on the link below to validate your ownership.

        Track information:
        - ISRC: {split_sheet.isrc}

        Best,
        Acrylic.LA
    """

    # Construct the payload
    signwell = Signwell()
    response = signwell.request_signatures(documents=[pdf_file], emails=emails, subject=subject, message=message)

    # Print the response
    if response.status_code == 200:
        split_sheet.status = SplitSheet.Status.PENDING
        split_sheet.signature_request_id = response.signature_request_id
        split_sheet.save()

    print(response.json())
