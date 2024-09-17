from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .serializers import (
    FAQsResponseSerializer,
    SearchHelpArticlesResponseSerializer,
    SubmitSupportTicketRequestSerializer,
    SubmitSupportTicketResponseSerializer
)
from .models import FAQ, HelpArticle, SupportTicket

class SupportViewSet(viewsets.ViewSet):
    def get_permissions(self):
        from rest_framework.permissions import IsAuthenticated, AllowAny
        if self.action in ['submit_support_ticket']:
            return [IsAuthenticated()]
        return [AllowAny()]

    @action(detail=False, methods=['get'], url_path='support/faqs')
    def get_faqs(self, request):
        faqs = FAQ.objects.all()
        categories = {}
        for faq in faqs:
            categories.setdefault(faq.category, []).append({
                "question_id": faq.question_id,
                "question": faq.question,
                "answer": faq.answer
            })
        faq_categories = [{"category": k, "questions": v} for k, v in categories.items()]
        serializer = FAQsResponseSerializer({
            "success": True,
            "faqs": faq_categories
        })
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='support/search')
    def search_help_articles(self, request):
        query = request.query_params.get('q')
        if not query:
            return Response({"success": False, "message": "Query parameter 'q' is required."},
                            status=status.HTTP_400_BAD_REQUEST)
        articles = HelpArticle.objects.filter(title__icontains=query)  # Simple search
        serializer = HelpArticleSerializer(articles, many=True)
        return Response({
            "success": True,
            "results": serializer.data
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='support/tickets')
    def submit_support_ticket(self, request):
        serializer = SubmitSupportTicketRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        ticket = SupportTicket.objects.create(
            user=request.user,
            subject=data['subject'],
            description=data['description'],
            category=data['category']
        )
        # Handle attachments if any
        return Response({
            "success": True,
            "ticket_id": ticket.ticket_id,
            "message": "Support ticket submitted successfully."
        }, status=status.HTTP_201_CREATED)