from rest_framework import serializers

class AnalyticsOverviewResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    total_page_views = serializers.IntegerField()
    total_qr_scans = serializers.IntegerField()
    average_time_per_page = serializers.IntegerField()
    most_popular_pages = serializers.ListField(child=serializers.DictField())
    device_types = serializers.DictField()

class PageAnalyticsSerializer(serializers.Serializer):
    page_id = serializers.CharField()
    views_over_time = serializers.ListField(child=serializers.DictField())
    qr_scans = serializers.IntegerField()
    average_time_spent = serializers.IntegerField()
    device_types = serializers.DictField()
    insights = serializers.ListField(child=serializers.CharField())

class PageAnalyticsResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    page_analytics = PageAnalyticsSerializer()