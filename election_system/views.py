from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

def root_redirect(request):
    # If user is authenticated, send them to their dashboard directly
    if request.user.is_authenticated:
        return redirect('voting:custom_redirect')
    # Otherwise, to the login page
    return redirect('login')
