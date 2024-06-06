import datetime
import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from legal.models import SplitSheet
from legal.signwell import Signwell


@csrf_exempt
@require_POST
def signwell_webhook(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        event = data.get('event')
        
        sign_backend = Signwell()
        if sign_backend.check_signature(event):
            # signature valid
        
            signed_date = None
            if event['type'] == 'document_completed':
                signature_request_id = data['object']['id']
                #signatures = data['signature_request']['signatures']
                #for signature in signatures:
                #    # The signed_date might be in UNIX timestamp format
                #    signed_timestamp = signature.get('signed_at')
                #    if signed_timestamp:
                #        # Convert the UNIX timestamp to a datetime object
                #        signed_date = datetime.utcfromtimestamp(int(signed_timestamp))
                #        print(f"Document was signed on: {signed_date}")

            SplitSheet.objects.filter(signature_request_id=signature_request_id).update(signed=datetime.datetime.now(), status=SplitSheet.Status.SIGNED)
            return JsonResponse({'status': 'success'})
        return JsonResponse({'status': 'bad request'}, status=400)


@csrf_exempt
@require_POST
def hellosign_webhook(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        event = data.get('event')
        
        signed_date = None
        if event == 'signature_request_signed':
            signature_request_id = data.get('signature_request_id')
            signatures = data['signature_request']['signatures']
            for signature in signatures:
                # The signed_date might be in UNIX timestamp format
                signed_timestamp = signature.get('signed_at')
                if signed_timestamp:
                    # Convert the UNIX timestamp to a datetime object
                    signed_date = datetime.utcfromtimestamp(int(signed_timestamp))
                    print(f"Document was signed on: {signed_date}")

        if signed_date:
            # Here you would update the MasterSplit instance with the datetime of signing
            # This is a simplified example. You will need to map the signature_request_id to your MasterSplit instance appropriately.
            SplitSheet.objects.filter(signature_request_id=signature_request_id).update(signed=signed_date, status=SplitSheet.Status.SIGNED)
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'bad request'}, status=400)
