import io
from dropbox_sign import ApiClient, ApiException, Configuration, apis, models
from django.apps import apps
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
import weasyprint

configuration = Configuration(username=settings.DROPBOX_SIGN_API_KEY)


def send_signature_request_for_ownership_validation(split_sheet):

    SplitSheet = apps.get_model('legal', 'SplitSheet')

    # avoid repeating signature request for same email in master/publishing splits
    emails = {}
    for split in split_sheet.master_splits.all():
        if split.email not in emails:
            emails[split.email] = split.legal_name
    for split in split_sheet.publishing_splits.all():
        if split.email not in emails:
            emails[split.email] = split.legal_name

    with ApiClient(configuration) as api_client:
        signature_request_api = apis.SignatureRequestApi(api_client)
        #signature_request_id = ''
        signers = []

        # add signers
        for email, legal_name in emails.items():
            signer = models.SubSignatureRequestSigner(email_address=email, name=legal_name)
            signers.append(signer)

        # configure options
        signing_options = models.SubSigningOptions(
            draw=True,
            type=True,
            upload=True,
            phone=False,
            default_type='draw',
        )

        # document in PDF format
        html_string = render_to_string('legal/split_sheet_pdf.html', {'split_sheet': split_sheet})
        pdf_file = weasyprint.HTML(string=html_string).write_pdf()
        
        import tempfile
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.pdf') as temp_file:
            temp_file.write(pdf_file)
            temp_file.flush()

            #pdf_io = io.BytesIO(pdf_file)
            #pdf_io.seek(0)  # Go to the beginning of the "file"
            #pdf_content = pdf_io.read() 

            data = models.SignatureRequestSendRequest(
                title=f'Sign split sheet for track {split_sheet.isrc}',
                subject=f'Sign split sheet for track {split_sheet.isrc}',
                message=f"""
                    Please sign the split sheet of the track with ISRC {split_sheet.isrc}. 

                    Click on the link below to validate your ownership.

                    Track information:
                    - ISRC: {split_sheet.isrc}

                    Best,
                    Acrylic.LA
                """,
                signers=signers,
                cc_email_addresses=[
                    "antonio@acrylic.la",
                ],
                files=[open(temp_file.name,  "rb")],
                metadata={
                    "isrc": split_sheet.isrc,
                },
                signing_options=signing_options,
                test_mode=True,
            )

            try:
                response = response = signature_request_api.signature_request_send(data)
                # save signature
                split_sheet.status = SplitSheet.Status.PENDING
                split_sheet.signature_request_id = response.signature_request_id
                split_sheet.save()
                
            except ApiException as e:
                print("Exception when calling Dropbox Sign API: %s\n" % e)

    
    
        
