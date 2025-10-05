from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
import pandas as pd
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.contrib import messages
from .models import Voter, ClientProfile, Zone

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
                with transaction.atomic():
                    # Delete voters then zones belonging to this client
                    client_profile.voters.all().delete()
                    Zone.objects.filter(client=client_profile).delete()
                messages.info(request, "Votantes y zonas existentes eliminados.")
                voter_count = 0 # Update local count
            except Exception as e:
                messages.error(request, f"Error al eliminar los votantes/zona existentes: {str(e)}")
                return redirect('voting:main_dashboard') # Stop if deletion fails

        # Step 6 & 7: Import Voters
        try:
            default_zone, _ = Zone.objects.get_or_create(client=client_profile, name='Sin asignar')
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
                    voted=False,
                    zone=default_zone
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
            "voted": voter.voted,
            "zone": voter.zone.name if voter.zone else 'Sin asignar'
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

@login_required
def get_zone_stats(request):
    """API endpoint to get per-zone voter statistics for the current client/visitor."""
    try:
        if hasattr(request.user, 'clientprofile'):
            client_profile = request.user.clientprofile
        elif hasattr(request.user, 'visitor_profile'):
            client_profile = get_object_or_404(ClientProfile, visitor_user=request.user)
        else:
            return JsonResponse({"status": "error", "message": "Tipo de usuario inválido"})

        zones = Zone.objects.filter(client=client_profile).order_by('name')
        data = []
        for z in zones:
            total = Voter.objects.filter(client=client_profile, zone=z).count()
            voted = Voter.objects.filter(client=client_profile, zone=z, voted=True).count()
            pct = round(voted / total * 100, 2) if total > 0 else 0
            data.append({
                'id': z.id,
                'name': z.name,
                'total_voters': total,
                'voted_count': voted,
                'percentage': pct,
            })
        return JsonResponse({"status": "success", "zones": data})
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
        with transaction.atomic():
            voter_qs = Voter.objects.filter(client=client_profile)
            deleted_count = voter_qs.count()
            voter_qs.delete()
            zones_qs = Zone.objects.filter(client=client_profile)
            zones_deleted = zones_qs.count()
            zones_qs.delete()
        return JsonResponse({
            "status": "success",
            "deleted_count": deleted_count,
            "zones_deleted": zones_deleted,
            "message": "Lista de votantes y zonas eliminadas correctamente."
        })
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})

@login_required
def upload_voters_to_zone(request):
    """Create a zone (if needed) and import voters assigning them to that zone.
    Upsert semantics: if DNI exists for this client, update name and zone; else create.
    Expects POST with 'zone_name' and file in 'file'."""
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Solo se permite POST"}, status=400)
    if not hasattr(request.user, 'clientprofile'):
        return JsonResponse({"status": "error", "message": "Acceso denegado"}, status=403)
    client_profile = request.user.clientprofile
    zone_name = request.POST.get('zone_name', '').strip()
    if not zone_name:
        return JsonResponse({"status": "error", "message": "Nombre de zona requerido"}, status=400)
    if 'file' not in request.FILES:
        return JsonResponse({"status": "error", "message": "Archivo requerido"}, status=400)

    uploaded_file = request.FILES['file']
    if not uploaded_file.name.endswith('.xlsx'):
        return JsonResponse({"status": "error", "message": "Formato inválido, use .xlsx"}, status=400)

    try:
        df = pd.read_excel(uploaded_file, engine='openpyxl')
    except Exception as e:
        return JsonResponse({"status": "error", "message": f"Error leyendo Excel: {str(e)}"})

    required_columns = ['dni', 'name']
    if not all(col in df.columns for col in required_columns):
        return JsonResponse({"status": "error", "message": "El archivo debe tener columnas 'dni' y 'name'"}, status=400)

    zone, _ = Zone.objects.get_or_create(client=client_profile, name=zone_name)
    created = 0
    updated = 0
    skipped = 0
    for index, row in df.iterrows():
        dni_val = str(row.get('dni')).strip() if not pd.isna(row.get('dni')) else ''
        name_val = str(row.get('name')).strip() if not pd.isna(row.get('name')) else ''
        if not dni_val or not name_val:
            skipped += 1
            continue
        voter = Voter.objects.filter(client=client_profile, dni=dni_val).first()
        if voter:
            # Update name + zone (don't touch voted flag)
            changed = False
            if voter.name != name_val:
                voter.name = name_val
                changed = True
            if voter.zone_id != zone.id:
                voter.zone = zone
                changed = True
            if changed:
                voter.save(update_fields=['name', 'zone'])
                updated += 1
        else:
            Voter.objects.create(client=client_profile, dni=dni_val, name=name_val, voted=False, zone=zone)
            created += 1

    return JsonResponse({
        "status": "success",
        "zone": zone.name,
        "created": created,
        "updated": updated,
        "skipped": skipped
    })

@login_required
def pending_voters(request):
    """Return paginated list of not-voted voters for a given zone (or all). Params: zone_id, page, page_size."""
    try:
        if hasattr(request.user, 'clientprofile'):
            client_profile = request.user.clientprofile
        elif hasattr(request.user, 'visitor_profile'):
            client_profile = get_object_or_404(ClientProfile, visitor_user=request.user)
        else:
            return JsonResponse({"status": "error", "message": "Tipo de usuario inválido"}, status=400)

        zone_id = request.GET.get('zone_id')  # may be None or 'all'
        page = int(request.GET.get('page', '1'))
        page_size = int(request.GET.get('page_size', '100'))
        page = max(page, 1)
        page_size = max(10, min(page_size, 500))  # clamp

        qs = Voter.objects.filter(client=client_profile, voted=False)
        if zone_id and zone_id != 'all':
            qs = qs.filter(zone_id=zone_id)

        total = qs.count()
        offset = (page - 1) * page_size
        voters = list(qs.order_by('dni').values('dni', 'name')[offset: offset + page_size])
        has_more = offset + page_size < total

        return JsonResponse({
            'status': 'success',
            'page': page,
            'page_size': page_size,
            'total': total,
            'has_more': has_more,
            'voters': voters,
        })
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})
