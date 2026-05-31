from django.contrib import admin
from .models import (
    User,
    City,
    Category,
    WorkerProfile,
    BookingRequest,
    Review,
    ContactMessage
)


# Basic registration
admin.site.register(City)
admin.site.register(Category)
admin.site.register(BookingRequest)
admin.site.register(Review)
admin.site.register(ContactMessage)


# Custom User Admin
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        'email',
        'name',
        'phone',
        'is_staff',
        'is_worker',
        'is_active'
    )

    search_fields = (
        'email',
        'name'
    )


# Custom WorkerProfile Admin
@admin.register(WorkerProfile)
class WorkerProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'city',
        'experience_years',
        'is_verified',
        'is_available'
    )

    list_filter = (
        'is_verified',
        'city'
    )