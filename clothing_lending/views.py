from django.shortcuts import render
from django.http import HttpResponse

# Create your views here.
def index(request):
	return HttpResponse("Hello world! If you're seeing this it means my django and heoku have been successfully linked I think.")

def catalog(request):
	return HttpResponse("This is the catalog of items.")

def checkout(request):
	return HttpResponse("I think this is a checkout idk if we need one.")