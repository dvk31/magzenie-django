from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .serializers import (
    AnalyticsOverviewResponseSerializer,
    PageAnalyticsResponseSerializer
)
from magazines.models import Magazine, Page
from django.db.models import Count, Avg

class AnalyticsViewSet(viewsets.ViewSet):
    def get_permissions(self):
        from rest_framework.permissions import IsAuthenticated
        return [IsAuthenticated()]

    @action(detail=False, methods=['get'], url_path='analytics/overview')
    def analytics_overview(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        # Implement filtering based on dates
        total_page_views = Page.objects.filter(magazine__user=request.user).aggregate(total=Count('views'))['total']
        total_qr_scans = 0 # Placeholder
        average_time_per_page = Page.objects.filter(magazine__user=request.user).aggregate(avg=Avg('time_spent'))['avg']
        most_popular_pages = [] # Implement logic to get most popular pages
        device_types = {
            "mobile": 600,
            "tablet": 300,
            "desktop": 100
        }
        serializer = AnalyticsOverviewResponseSerializer({
            "success": True,
            "total_page_views": total_page_views,
            "total_qr_scans": total_qr_scans,
            "average_time_per_page": average_time_per_page,
            "most_popular_pages": most_popular_pages,
            "device_types": device_types
        })
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='analytics/magazines/(?P<magazine_id>[^/.]+)/pages/(?P<page_id>[^/.]+)')
    def page_analytics(self, request, magazine_id=None, page_id=None):
        try:
            page = Page.objects.get(page_id=page_id, magazine__magazine_id=magazine_id, magazine__user=request.user)
            analytics = {
                "page_id": page.page_id,
                "views_over_time": [],  # Implement logic
                "qr_scans": 30,  # Placeholder
                "average_time_spent": 90,
                "device_types": {
                    "mobile": 70,
                    "tablet": 20,
                    "desktop": 10
                },
                "insights": ["Your page views increased by 20% compared to last week."]
            }
            serializer = PageAnalyticsResponseSerializer({
                "success": True,
                "page_analytics": analytics
            })
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Page.DoesNotExist:
            return Response({"success": False, "error": "Page not found."}, status=status.HTTP_404_NOT_FOUND)