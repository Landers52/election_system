from django.shortcuts import redirect

def root_redirect(request):
    return redirect('voting:custom_redirect')
