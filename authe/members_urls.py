# members_urls.py
from django.urls import path
from . import members_views

urlpatterns = [
    path('', members_views.get_all_members, name='get_all_members'),
    path('<int:member_id>/', members_views.get_member_by_id, name='get_member_by_id'),
    path('create/', members_views.create_member, name='create_member'),
    path('update/<int:member_id>/', members_views.update_member, name='update_member'),
    path('delete/<int:member_id>/', members_views.delete_member, name='delete_member'),
    path('change-password/<int:member_id>/', members_views.change_member_password, name='change_password'),
    path('bulk-update-roles/', members_views.bulk_update_roles, name='bulk_update_roles'),
    path('role/<str:role>/', members_views.get_members_by_role, name='get_members_by_role'),
    path('statistics/', members_views.get_role_statistics, name='role_statistics'),
    path('deactivate/<int:member_id>/', members_views.deactivate_member, name='deactivate_member'),
    path('activate/<int:member_id>/', members_views.activate_member, name='activate_member'),
    path('search/', members_views.search_members, name='search_members'),
]