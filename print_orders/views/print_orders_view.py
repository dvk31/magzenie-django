from django.shortcuts import render
from .models import Print_ordersModel

class Print_ordersView:
    def get(self, request):
        print_orders_objects = Print_ordersModel.objects.all()
        return render(request, 'print_orders/print_orders.html', {'print_orders_objects': print_orders_objects})
