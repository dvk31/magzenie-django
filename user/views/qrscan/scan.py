#user/views/qrscan/scan.py

from django.shortcuts import render, get_object_or_404
from user.models import Kiosk, Product, KioskQRCode

def scan_product(request, kiosk_id, product_id):
    # Get the kiosk and product objects
    kiosk = get_object_or_404(Kiosk, id=kiosk_id)
    product = get_object_or_404(Product, id=product_id)
    
    # Ensure the product is associated with the kiosk
    kiosk_qr_code = get_object_or_404(KioskQRCode, kiosk=kiosk, product=product)
    
    context = {
        'product_name': product.title,
        'product_price': product.price,
        'product_thumbnail': product.thumbnail_url,
        'kiosk_name': kiosk.name,
        'store_name': kiosk.store.name if kiosk.store else None,
    }
    
    return render(request, 'scan_product.html', context)