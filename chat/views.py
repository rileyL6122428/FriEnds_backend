from django.shortcuts import render
from django.conf import settings
from django.http import HttpResponse

# Create your views here.

# def get_session(request):
#     response = HttpResponse()
#     response.set_cookie(settings.SESSION_COOKIE_NAME, request.session.session_key)
#     return response


def index(request):
    return render(request, template_name="chat/index.html")
