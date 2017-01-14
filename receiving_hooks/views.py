from django.shortcuts import render
import json
import pprint
from django.http import HttpResponse

def new_feedback(request):
    pprint.pprint(request.POST)
    return HttpResponse(json.dumps({"text": "Ok, will be sent."}), content_type="application/json")
