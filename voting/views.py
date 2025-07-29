from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
import pandas as pd
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.utils.translation import gettext_lazy as _ # Import gettext_lazy
from .models import Voter, ClientProfile

@login_required
def custom_redirect(request):
    if request.user.is_superuser:
        return redirect('/admin/')  # Send superusers to Django's admin panel
    elif hasattr(request.user, 'clientprofile'):
        return redirect('voting:main_dashboard')  # Use namespaced URL
    elif hasattr(request.user, 'visitor_profile'):  # Check for visitor_profile
        return redirect('voting:visitor_dashboard')  # Use namespaced URL
    else:
        return HttpResponseForbidden("Access denied. No valid profile found.")

@login_required
def main_dashboard(request):
    if not hasattr(request.user, 'clientprofile'):
        return HttpResponseForbidden("Access denied. You must be a client to access this page.")
    client_profile = request.user.clientprofile
    voters = client_profile.voters.all()
    voter_count = voters.count() # Get initial voter count

    if request.method == 'POST' and request.FILES.get('file'):
        uploaded_file = request.FILES['file']

        # --- File Type Validation First ---
        if not uploaded_file.name.endswith('.xlsx'):
            messages.error(request, _("Please upload an Excel (.xlsx) file.")) # Translate message
            # Redirect immediately without deleting data
            return redirect('voting:main_dashboard')
        # --- End File Type Validation ---

        # Step 2: Read DataFrame
        try:
            df = pd.read_excel(uploaded_file, engine='openpyxl')
        except pd.errors.EmptyDataError:
            messages.error(request, _("The uploaded Excel file is empty."))
            return redirect('voting:main_dashboard')
        except Exception as e: # Catch other potential read errors (e.g., corrupted file)
            messages.error(request, _("Error reading the Excel file: {error}").format(error=str(e)))
            return redirect('voting:main_dashboard')

        # Step 3: Validate Columns
        required_columns = ['dni', 'name']
        if not all(col in df.columns for col in required_columns):
            messages.error(request, _("Excel file must contain 'dni' and 'name' columns."))
            return redirect('voting:main_dashboard') # Redirect *before* deletion check

        # --- All file/column validations passed ---

        # Step 4 & 5: Deletion Logic (only if needed and validations passed)
        confirm_replace = request.POST.get('confirm_replace') == 'yes'
        if confirm_replace and voter_count > 0:
            try:
                client_profile.voters.all().delete()
                messages.info(request, _("Existing voters deleted."))
                voter_count = 0 # Update local count
            except Exception as e:
                messages.error(request, _("Error deleting existing voters: {error}").format(error=str(e)))
                return redirect('voting:main_dashboard') # Stop if deletion fails

        # Step 6 & 7: Import Voters
        try:
            import_successful = True # Flag to track success
            for index, row in df.iterrows():
                # Basic check for NaN or empty strings which might cause issues
                if pd.isna(row.get('dni')) or str(row.get('dni')).strip() == '' or \
                   pd.isna(row.get('name')) or str(row.get('name')).strip() == '':
                   messages.warning(request, _("Skipped row {row_num}: Missing DNI or Name.").format(row_num=index + 2)) # +2 for 1-based index + header
                   continue # Skip this row

                Voter.objects.create(
                    client=client_profile,
                    dni=str(row['dni']),
                    name=str(row['name']), # Ensure name is also string
                    voted=False
                )
            # Only show success if the loop finished without critical errors
            if import_successful:
                 messages.success(request, _("Voters imported successfully!"))

        except Exception as e: # Catch errors during Voter.objects.create
            import_successful = False # Mark as failed
            # Check if the error is due to duplicate DNI (IntegrityError)
            # We might need more specific error handling here depending on DB backend if needed.
            if 'UNIQUE constraint' in str(e) or 'duplicate key value violates unique constraint' in str(e):
                 # Translate message
                 messages.error(request, _("Error: Duplicate DNI found. Ensure DNIs are unique within the file and confirm replacement if necessary."))
            else:
                 # Translate message with variable
                messages.error(request, _("Error processing the Excel file: {error}").format(error=str(e)))
                
        return redirect('voting:main_dashboard')

    # Pass voter_count to the template for the GET request
    return render(request, 'voting/main_dashboard.html', {'voters': voters, 'voter_count': voter_count})

@login_required
def visitor_dashboard(request):
    """Allows visitors to search voters and mark them as voted"""
    if not hasattr(request.user, 'visitor_profile'):  # Check for visitor_profile
        return redirect('voting:custom_redirect')  # Prevent access for non-visitors

    # Fetch the ClientProfile associated with the visitor user
    client_profile = get_object_or_404(ClientProfile, visitor_user=request.user)
    query = request.GET.get('q', '')
    voters = Voter.objects.filter(client=client_profile)
    if query:
        voters = voters.filter(name__icontains=query) | voters.filter(dni__icontains=query)
    return render(request, 'voting/visitor_dashboard.html', {'voters': voters})

@login_required
def search_voter_by_dni(request):
    """API endpoint to search for a voter by DNI"""
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Only POST method is allowed"})
    
    dni = request.POST.get('dni')
    if not dni:
        return JsonResponse({"status": "error", "message": "DNI is required"})

    try:
        # For clients, search in their own voters
        if hasattr(request.user, 'clientprofile'):
            voter = get_object_or_404(Voter, client=request.user.clientprofile, dni=dni)
        # For visitors, search in their associated client's voters
        elif hasattr(request.user, 'visitor_profile'):
            client_profile = get_object_or_404(ClientProfile, visitor_user=request.user)
            voter = get_object_or_404(Voter, client=client_profile, dni=dni)
        else:
            return JsonResponse({"status": "error", "message": "Invalid user type"})

        return JsonResponse({
            "status": "success",
            "voter": {
                "id": voter.id,
                "name": voter.name,
                "dni": voter.dni,
                "voted": voter.voted
            }
        })
    except Voter.DoesNotExist:
        # Return 200 OK but indicate not found in the payload with a specific message
        return JsonResponse({"status": "not_found", "message": _("No voter found with that DNI.")})

@csrf_exempt  # Note: Consider using proper CSRF protection in production
def mark_voted(request, voter_id):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Only POST method is allowed"})
    
    try:
        voter = Voter.objects.get(id=voter_id)
        
        # Check permissions
        if hasattr(request.user, 'clientprofile'):
            if voter.client != request.user.clientprofile:
                return JsonResponse({"status": "error", "message": "Access denied"})
        elif hasattr(request.user, 'visitor_profile'):
            client_profile = get_object_or_404(ClientProfile, visitor_user=request.user)
            if voter.client != client_profile:
                return JsonResponse({"status": "error", "message": "Access denied"})
        else:
            return JsonResponse({"status": "error", "message": "Invalid user type"})

        # Toggle the voted status
        voter.voted = not voter.voted
        voter.save()
        
        return JsonResponse({
            "status": "success",
            "voted": voter.voted
        })
    except Voter.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Voter not found"})

@login_required
def redirect_to_dashboard(request):
    if hasattr(request.user, "clientprofile"):
        return redirect("voting:main_dashboard")  # Use namespaced URL
    elif hasattr(request.user, "visitor_profile"):  # Update to check visitor_profile
        return redirect("voting:visitor_dashboard")  # Use namespaced URL
    else:
        return redirect("login")

@login_required
def get_voter_stats(request):
    """API endpoint to get voter statistics"""
    try:
        if hasattr(request.user, 'clientprofile'):
            client_profile = request.user.clientprofile
        elif hasattr(request.user, 'visitor_profile'):
            client_profile = get_object_or_404(ClientProfile, visitor_user=request.user)
        else:
            return JsonResponse({"status": "error", "message": "Invalid user type"})

        total_voters = Voter.objects.filter(client=client_profile).count()
        voted_count = Voter.objects.filter(client=client_profile, voted=True).count()
        
        return JsonResponse({
            "status": "success",
            "stats": {
                "total_voters": total_voters,
                "voted_count": voted_count,
                "percentage": round(voted_count / total_voters * 100, 2) if total_voters > 0 else 0
            }
        })
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})
