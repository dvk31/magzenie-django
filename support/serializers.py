from rest_framework import serializers

class FAQQuestionSerializer(serializers.Serializer):
    question_id = serializers.CharField()
    question = serializers.CharField()
    answer = serializers.CharField()

class FAQCategorySerializer(serializers.Serializer):
    category = serializers.CharField()
    questions = FAQQuestionSerializer(many=True)

class FAQsResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    faqs = FAQCategorySerializer(many=True)

class HelpArticleSerializer(serializers.Serializer):
    article_id = serializers.CharField()
    title = serializers.CharField()
    snippet = serializers.CharField()

class SearchHelpArticlesResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    results = HelpArticleSerializer(many=True)

class SubmitSupportTicketRequestSerializer(serializers.Serializer):
    subject = serializers.CharField()
    description = serializers.CharField()
    category = serializers.ChoiceField(choices=["Technical Issue", "Billing", "Print Orders", "Other"])
    attachments = serializers.ListField(child=serializers.URLField(), required=False)

class SubmitSupportTicketResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    ticket_id = serializers.CharField()
    message = serializers.CharField()