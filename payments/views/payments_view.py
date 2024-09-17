from django.shortcuts import render
from .models import PaymentsModel

class PaymentsView:
    def get(self, request):
        payments_objects = PaymentsModel.objects.all()
        return render(request, 'payments/payments.html', {'payments_objects': payments_objects})
