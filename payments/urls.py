# payments/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
     PaymentMethodViewSet,
    PaymentRecordViewSet, BankDetailsViewSet,
    PaymentStatusViewSet, PaymentNotificationViewSet
)

router = DefaultRouter()

# Register URL patterns - matching frontend expectations

router.register(r'pay/payment-methods/me', PaymentMethodViewSet, basename='payment-methods')
router.register(r'pay/payment-records/me', PaymentRecordViewSet, basename='payment-records')
router.register(r'pay/bank-details/me', BankDetailsViewSet, basename='bank-details')
router.register(r'pay/payment-status/me', PaymentStatusViewSet, basename='payment-status')
router.register(r'pay/payment-notifications/me', PaymentNotificationViewSet, basename='payment-notifications')

urlpatterns = [
    path('', include(router.urls)),
]

# ============================================================================
# API ENDPOINTS (No Authentication Required)
# ============================================================================
"""
Service Requests (from registration app):
    GET    /api/public-requests/                    - List all requests
    GET    /api/public-requests/?phone=0712345678   - Filter by phone
    GET    /api/public-requests/pending/            - Get pending requests
    POST   /api/public-requests/submit/             - Submit new request
    GET    /api/public-requests/{id}/               - Get specific request
    PUT    /api/public-requests/{id}/               - Update request
    PATCH  /api/public-requests/{id}/               - Partial update
    DELETE /api/public-requests/{id}/               - Delete request

Payment Methods:
    GET    /api/pay/payment-methods/                - List all methods
    GET    /api/pay/payment-methods/active/         - List active methods
    GET    /api/pay/payment-methods/{id}/           - Get specific method

Bank Details:
    GET    /api/pay/bank-details/                   - List bank details
    GET    /api/pay/bank-details/current/           - Get current bank details

Payment Records:
    GET    /api/pay/payment-records/                - List all payments
    GET    /api/pay/payment-records/?phone=0712345678 - Filter by phone
    POST   /api/pay/payment-records/                - Create payment (sends email)
    GET    /api/pay/payment-records/my_payments/    - Get payments (use phone param)
    GET    /api/pay/payment-records/pending/        - Get pending payments
    PATCH  /api/pay/payment-records/{id}/confirm/   - Confirm payment (sends email)
    POST   /api/pay/payment-records/{id}/initiate_payment/ - Initiate payment
    POST   /api/pay/payment-records/{id}/submit_manual/   - Submit manual payment (sends email)
    POST   /api/pay/payment-records/{id}/verify/    - Verify payment (admin, sends email)
    POST   /api/pay/payment-records/{id}/complete/  - Complete payment (admin, sends email)
    POST   /api/pay/payment-records/{id}/notify_whatsapp/ - Mark WhatsApp sent

Payment Status:
    GET    /api/pay/payment-status/check/?transaction_id=TX-... - Check status

Payment Notifications:
    GET    /api/pay/payment-notifications/          - List notifications
    GET    /api/pay/payment-notifications/?payment_record=1 - Filter by payment
    POST   /api/pay/payment-notifications/send_status_update/ - Send status update
"""

# ============================================================================
# Main urls.py (project level)
# ============================================================================

"""
# quickfix_backend/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('payments.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
"""