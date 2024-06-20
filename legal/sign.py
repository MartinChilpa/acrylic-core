from django.apps import apps
from django.conf import settings
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
import weasyprint
from account.models import Document
from legal.signwell import Signwell


def contract_request_signature(artist):
    
    Document = apps.get_model('account', 'Document')

    document_name = 'Master Recording and Compositions Synchronization Representation Agreement'  

    # document in PDF format
    html_string = render_to_string('legal/artist_contract_pdf.html', {'artist': artist})
    pdf_file = weasyprint.HTML(string=html_string).write_pdf()

    # Save the PDF to a model instance
    document = Document(
        type=Document.Type.CONTRACT,
        user=artist.user,
        name=document_name
    )
    document.save()
    document.document.save('contract.pdf', ContentFile(pdf_file))
    document.save()

    subject = f'Sign the {document_name}'
    message = f"""
        Please sign the Acrylic.la {document_name}.

        Best,
        Acrylic.LA
    """

    # Construct the payload
    emails = [(artist.user.email, artist.name)]
    signwell = Signwell()
    response = signwell.request_signatures(documents=[pdf_file], emails=emails, subject=subject, message=message)

    if response.status_code == 201:
        # created
        data = response.json()
        # Save the signature request ID
        document.signature_request_id = data['id']
        document.save()
    return True


def splitsheet_request_signatures(split_sheet):

    SplitSheet = apps.get_model('legal', 'SplitSheet')

    # avoid repeating signature request for same email in master/publishing splits
    master_emails = split_sheet.master_splits.values_list('email', 'name')
    publishing_emails = split_sheet.publishing_splits.values_list('email', 'name')

    # remove master/publishing duplicates
    emails = list(set(list(master_emails) + list(publishing_emails)))

    # document in PDF format
    html_string = render_to_string('legal/split_sheet_pdf.html', {'split_sheet': split_sheet})
    pdf_file = weasyprint.HTML(string=html_string).write_pdf()

    subject = f'Sign split sheet for track {split_sheet.isrc}'
    message = f"""
        Please sign the split sheet of the track with ISRC {split_sheet.isrc}. 

        Best,
        Acrylic.LA
    """

    # Construct the payload
    signwell = Signwell()
    response = signwell.request_signatures(documents=[pdf_file], emails=emails, subject=subject, message=message)

    if response.status_code == 201:
        # created
        data = response.json()
        split_sheet.status = SplitSheet.Status.PENDING
        split_sheet.signature_request_id = data['id']
        split_sheet.save()
