from django.urls import path
from user.views.auth.login import LoginView
from user.views.qrscan.scan import scan_product  
from user.views.qrscan.kiosk_products import KioskProductsView
from user.views.auth.signup import UserSignupView
from user.views.kioskapp.kiosk_video import KioskVideoView
from user.views.webhooks.product import ProductUpdateWebhookView
from user.views.kioskapp.scan_event import ScanEventView
from user.views.kioskapp.scan_event_v2 import ScanEventView2

from user.views.webhooks.kiosk_qr_code import KioskQRCodeWebhookView

urlpatterns = [
    path('login/', LoginView.as_view(), name='token_obtain_pair'),
    path('signup/', UserSignupView.as_view(), name='user_signup'),
    path('scan/<uuid:kiosk_id>/<uuid:product_id>/', scan_product, name='scan_product'),
    path('scan/scan-event/', ScanEventView.as_view(), name='scan-event'),
    path('scan/scan-event-v2/', ScanEventView2.as_view(), name='scan-event-v2'),

    path('kiosks/<uuid:kiosk_id>/products/<uuid:scanned_product_id>/', KioskProductsView.as_view(), name='kiosk-products'),
    path('webhooks/product-update/', ProductUpdateWebhookView.as_view(), name='product-update-webhook'),
    path('webhooks/kiosk-qr-code/', KioskQRCodeWebhookView.as_view(), name='kiosk-qr-code-webhook'),
    path('api/kiosk/videos/', KioskVideoView.as_view(), name='kiosk-videos'),
    
]