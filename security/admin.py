from django.contrib import admin
from .models import SecurityGuard

@admin.register(SecurityGuard)
class SecurityGuardAdmin(admin.ModelAdmin):
    list_display = ('user', 'contact_number', 'cnic', 'created_at', 'updated_at')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'contact_number', 'cnic')
    list_filter = ('created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')
