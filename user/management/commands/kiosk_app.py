from django.core.management.base import BaseCommand, CommandError
from django.core.serializers.json import DjangoJSONEncoder
from user.models import Kiosk, Product, KioskQRCode
import json

class Command(BaseCommand):
    help = 'Fetches kiosk data for the given kiosk ID'

    def add_arguments(self, parser):
        parser.add_argument('kiosk_id', type=str, help='The ID of the kiosk')

    def handle(self, *args, **options):
        kiosk_id = options['kiosk_id']

        try:
            kiosk = Kiosk.objects.get(id=kiosk_id)
        except Kiosk.DoesNotExist:
            raise CommandError(f'Kiosk with ID "{kiosk_id}" does not exist')

        products_data = []
        for qr_code in KioskQRCode.objects.filter(kiosk=kiosk).select_related('product'):
            product = qr_code.product
            products_data.append({
                'id': str(product.id),
                'title': product.title,
                'price': float(product.price) if product.price else None,
                'video_url': product.video_url,
                'qr_code_url': qr_code.image_url,
            })

        kiosk_data = {
            'kiosk_id': str(kiosk.id),
            'products': products_data
        }

        self.stdout.write(json.dumps(kiosk_data, cls=DjangoJSONEncoder, indent=2))