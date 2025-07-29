from django.shortcuts import render
from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.contrib.auth.views import LogoutView
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect

@method_decorator(csrf_protect, name='dispatch')
class CustomLogoutView(LogoutView):
    pass

def logout_view(request):
    logout(request)
    return redirect('login')  # Redirect to the login page after logout