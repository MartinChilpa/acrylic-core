import celery
from django.apps import apps
from acrylic.celery import app
from legal.sign import splitsheet_request_signatures


@app.task
def request_signatures_task(split_sheet_id):
    SplitSheet = apps.get_model('legal', 'SplitSheet')
    try:
        split_sheet = SplitSheet.objects.get(id=split_sheet_id)
    except SplitSheet.DoesNotExist:
        pass
    else:
        splitsheet_request_signatures(split_sheet)
    return True
