from django.urls import path
from . import views

app_name = 'voting'

urlpatterns = [
    path('', views.custom_redirect, name='custom_redirect'),
    path('dashboard/', views.main_dashboard, name='main_dashboard'),
    path('visitor/dashboard/', views.visitor_dashboard, name='visitor_dashboard'),
    path('mark_voted/<int:voter_id>/', views.mark_voted, name='mark_voted'),
    path('mark_by_dni_set/', views.mark_voted_by_dni_set, name='mark_by_dni_set'),
    path('search_voter_by_dni/', views.search_voter_by_dni, name='search_voter_by_dni'),
    path('voter_stats/', views.get_voter_stats, name='get_voter_stats'),  # New endpoint
    path('zone_stats/', views.get_zone_stats, name='get_zone_stats'),  # Per-zone stats
    path('pending_voters/', views.pending_voters, name='pending_voters'),  # Paginated pending voters
    path('clear_voters/', views.clear_voters, name='clear_voters'),  # Delete all voters for client
    path('upload_zone/', views.upload_voters_to_zone, name='upload_voters_to_zone'),  # Upload list assigning to a zone
]
