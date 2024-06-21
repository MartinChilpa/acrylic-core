import json
import hmac
import hashlib
import base64
import requests
from django.apps import apps
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string


class Signwell():
    """
    SignWell Backend
    https://developers.signwell.com/reference/
    """
    base_url = 'https://www.signwell.com/api/v1/'
    api_key = settings.SIGNWELL_API_KEY
    webhook_key = settings.SIGNWELL_WEBHOOK_KEY

    def _request(self, path, method, data={}):
        if method not in ['get', 'post', 'put']:
            raise Exception('Method not supported')
        response = getattr(requests, method)(
            url=f'{self.base_url}{path}',
            headers={
                'X-Api-Key':  self.api_key,
                'accept': 'application/json',
                'content-type': 'application/json'
            },
            data=json.dumps(data)
        )
        return response
    
    def check_signature(self, event):    
        # expected signature
        data = event['type'] + '@' + str(event['time'])
        expected_signature = event['hash']

        # calculated signature
        calculated_signature = hmac.new(self.webhook_key.encode('utf-8'), data.encode('utf-8'), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected_signature, calculated_signature)  # Will be True if signatures match

    def request_signatures(self, documents, emails, subject, message):
        recipients = []

        files = []
        for name, content in documents:
            files.append({
                'name': name,
                # Convert the file to base64 encoding
                'file_base64': base64.b64encode(content).decode('utf-8'),
            })

        for idx, (email, name) in enumerate(emails):
            recipients.append({
                'id': idx,
                'name': name,
                'email': email,
            })
        print(recipients)

        data = {
            'test_mode': settings.SIGNWELL_TEST_MODE,
            'draft': False,
            'subject': subject,
            'message': message,
            'with_signature_page': True,
            'reminders': True,
            'apply_signing_order': False,
            'embedded_signing': False,
            'text_tags': False,
            'allow_decline': True,
            'allow_reassign': False,
            'files': files,
            'recipients': recipients
        }
        return self._request('documents/', 'post', data) 

    def get_signed_document(self, document_id):
        response = self._request('documents/{document_id}/completed_pdf/', 'get')
        return response.content
