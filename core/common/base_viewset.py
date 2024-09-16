#core/common/base_viewset.py

from rest_framework import viewsets
from .base_api import BaseApiView
from rest_framework import status
from rest_framework import viewsets
from rest_framework.response import Response
from .base_api import BaseApiView



class BaseViewSet(viewsets.ModelViewSet, BaseApiView):
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_data = self.get_paginated_response(serializer.data).data
            data = {
                'status': 'success',
                'message': 'Success',
                'data': paginated_data
            }
            return Response(data)

        serializer = self.get_serializer(queryset, many=True)
        data = {
            'status': 'success',
            'message': 'Success',
            'data': serializer.data
        }
        return Response(data)


    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        data = {
            'status': 'success',
            'message': 'Success',
            'data': serializer.data
        }
        return Response(data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        data = {
            'status': 'success',
            'message': 'Success',
            'data': serializer.data
        }
        return Response(data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        data = {
            'status': 'success',
            'message': 'Success',
            'data': serializer.data
        }
        return Response(data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        data = {
            'status': 'success',
            'message': 'Success',
            'data': None
        }
        return Response(data)