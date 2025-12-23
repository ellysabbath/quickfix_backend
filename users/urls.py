# users/urls.py
from django.urls import path
from django.http import HttpResponse

def test(request):
    return HttpResponse("Working!")

urlpatterns = [
    path('', test),
]