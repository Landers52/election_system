from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
import pandas as pd
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from .models import Voter, ClientProfile

@login_required
def custom_redirect(request):
    if request.user.is_superuser:
        return redirect('/admin/')
    elif hasattr(request.user, 'clientprofile'):
        return redirect('voting:main_dashboard')
    elif hasattr(request.user, 'visitor_profile'):
        return redirect('voting:visitor_dashboard')
    else:
        return HttpResponseForbidden("Acceso denegado. No se encontró un perfil válido.")

@login_required
def main_dashboard(request):
    if not hasattr(request.user, 'clientprofile'):
        return HttpResponseForbidden("Acceso denegado. Debes ser un cliente para acceder a esta página.")
    client_profile = request.user.clientprofile
    voters = client_profile.voters.all()
    voter_count = voters.count() # Get initial voter count

    if request.method == 'POST' and request.FILES.get('file'):
        uploaded_file = request.FILES['file']

        # --- File Type Validation First ---
        if not uploaded_file.name.endswith('.xlsx'):
            messages.error(request, "Por favor, suba un archivo de Excel (.xlsx).")
            # Redirect immediately without deleting data
            return redirect('voting:main_dashboard')
        # --- End File Type Validation ---

        # Step 2: Read DataFrame
        try:
            df = pd.read_excel(uploaded_file, engine='openpyxl')
        except pd.errors.EmptyDataError:
            messages.error(request, "El archivo de Excel subido está vacío.")
            return redirect('voting:main_dashboard')
        except Exception as e: # Catch other potential read errors (e.g., corrupted file)
            messages.error(request, f"Error al leer el archivo de Excel: {str(e)}")
            return redirect('voting:main_dashboard')

        # Step 3: Validate Columns
        required_columns = ['dni', 'name']
        if not all(col in df.columns for col in df.columns):
            messages.error(request, "El archivo de Excel debe contener las columnas 'dni' y 'name'.")
            return redirect('voting:main_dashboard') # Redirect *before* deletion check

        # --- All file/column validations passed ---

        # Step 4 & 5: Deletion Logic (only if needed and validations passed)
        confirm_replace = request.POST.get('confirm_replace') == 'yes'
        if confirm_replace and voter_count > 0:
            try:
                client_profile.voters.all().delete()
                messages.info(request, "Votantes existentes eliminados.")
                voter_count = 0 # Update local count
            except Exception as e:
                messages.error(request, f"Error al eliminar los votantes existentes: {str(e)}")
                return redirect('voting:main_dashboard') # Stop if deletion fails

        # Step 6 & 7: Import Voters
        try:
            for index, row in df.iterrows():
                # Basic check for NaN or empty strings which might cause issues
                if pd.isna(row.get('dni')) or str(row.get('dni')).strip() == '' or \
                   pd.isna(row.get('name')) or str(row.get('name')).strip() == '':
                    messages.warning(request, f"Fila {index + 2} omitida: Falta DNI o Nombre.")  # +2 for 1-based index + header
                    continue  # Skip this row

                Voter.objects.create(
                    client=client_profile,
                    dni=str(row['dni']),
                    name=str(row['name']),  # Ensure name is also string
                    voted=False
                )
        except Exception as e:  # Catch errors during Voter.objects.create
            if 'UNIQUE constraint' in str(e) or 'duplicate key value violates unique constraint' in str(e):
                messages.error(request, "Error: DNI duplicado encontrado. Asegúrese de que los DNI sean únicos dentro del archivo y confirme el reemplazo si es necesario.")
            else:
                messages.error(request, f"Error al procesar el archivo de Excel: {str(e)}")
            return redirect('voting:main_dashboard')  # Stay on page without success flag

        # Successful import -> redirect with flag for inline toast
        return redirect(f"{reverse('voting:main_dashboard')}?uploaded=1")

    # GET (or POST without file) -> render dashboard
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
        return JsonResponse({"status": "error", "message": "Solo se permite el método POST"})
    
    dni = request.POST.get('dni')
    if not dni:
        return JsonResponse({"status": "error", "message": "El DNI es requerido"})

    # Determine which client's voters to search
    if hasattr(request.user, 'clientprofile'):
        client_profile = request.user.clientprofile
    elif hasattr(request.user, 'visitor_profile'):
        client_profile = get_object_or_404(ClientProfile, visitor_user=request.user)
    else:
        return JsonResponse({"status": "error", "message": "Tipo de usuario inválido"})

    # If there are no voters uploaded yet for this client, return a specific message
    total_for_client = Voter.objects.filter(client=client_profile).count()
    if total_for_client == 0:
        return JsonResponse({
            "status": "no_data",
            "message": "Sin datos, por favor cargue una lista de votantes primero"
        })

    # Try to find the voter by DNI without raising 404s
    voter = Voter.objects.filter(client=client_profile, dni=dni).first()
    if not voter:
        return JsonResponse({
            "status": "not_found",
            "message": "No se encontró ningún votante con ese DNI."
        })

    return JsonResponse({
        "status": "success",
        "voter": {
            "id": voter.id,
            "name": voter.name,
            "dni": voter.dni,
            "voted": voter.voted
        }
    })

@csrf_exempt  # Note: Consider using proper CSRF protection in production
def mark_voted(request, voter_id):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Solo se permite el metodo POST"})
    
    try:
        voter = Voter.objects.get(id=voter_id)
        
        # Check permissions
        if hasattr(request.user, 'clientprofile'):
            if voter.client != request.user.clientprofile:
                return JsonResponse({"status": "error", "message": "Acceso denegado"})
        elif hasattr(request.user, 'visitor_profile'):
            client_profile = get_object_or_404(ClientProfile, visitor_user=request.user)
            if voter.client != client_profile:
                return JsonResponse({"status": "error", "message": "Acceso denegado"})
        else:
            return JsonResponse({"status": "error", "message": "Tipo de usuario inválido"})

        # Toggle the voted status
        voter.voted = not voter.voted
        voter.save()
        
        return JsonResponse({
            "status": "success",
            "voted": voter.voted
        })
    except Voter.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Votante no encontrado"})

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
            return JsonResponse({"status": "error", "message": "Tipo de usuario inválido"})

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

# The translations endpoint has been removed. All client-side text is hardcoded to Spanish
# and served directly from templates and views. No runtime translation activation is used.

@login_required
def clear_voters(request):
    """Delete all voters for the current client's profile. Only allowed for client users."""
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Solo se permite el método POST"})

    # Only client users can clear their list
    if not hasattr(request.user, 'clientprofile'):
        return JsonResponse({"status": "error", "message": "Acceso denegado"})

    client_profile = request.user.clientprofile
    try:
        qs = Voter.objects.filter(client=client_profile)
        deleted_count = qs.count()
        qs.delete()
        return JsonResponse({
            "status": "success",
            "deleted_count": deleted_count,
            "message": "Lista de votantes eliminada correctamente."
        })
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})
