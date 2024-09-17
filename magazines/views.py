from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .serializers import (
    CreateMagazineRequestSerializer,
    CreateMagazineResponseSerializer,
    MagazinesResponseSerializer,
    DuplicateMagazineResponseSerializer,
    SubmitAirbnbURLRequestSerializer,
    SubmitAirbnbURLResponseSerializer,
    StartAIContentGenerationResponseSerializer,
    AIContentGenerationStatusSerializer,
    GetGeneratedContentResponseSerializer,
    UpdatePageContentRequestSerializer,
    UpdatePageContentResponseSerializer,
    AddPageRequestSerializer,
    AddPageResponseSerializer,
    DeletePageResponseSerializer,
    QRCodesResponseSerializer,
    CustomizeQRCodeRequestSerializer,
    CustomizeQRCodeResponseSerializer,
    CTAsResponseSerializer,
    UpdateCTADRequestSerializer,
    UpdateCTAResponseSerializer
)
from .models import Magazine, Template, AIProcess, Page, QRCode, CTA

class TemplateViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    @action(detail=False, methods=['get'], url_path='templates')
    def list_templates(self, request):
        templates = Template.objects.all()
        serializer = TemplateSerializer(templates, many=True)
        return Response({
            "success": True,
            "templates": serializer.data
        }, status=status.HTTP_200_OK)

class MagazineViewSet(viewsets.ViewSet):
    def get_permissions(self):
        from rest_framework.permissions import IsAuthenticated
        return [IsAuthenticated()]

    @action(detail=False, methods=['post'], url_path='magazines')
    def create_magazine(self, request):
        serializer = CreateMagazineRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        # Assume Template exists
        template = Template.objects.get(template_id=data['template_id'])
        magazine = Magazine.objects.create(
            user=request.user,
            template=template,
            title=data.get('magazine_title', 'Untitled')
        )
        response_serializer = CreateMagazineResponseSerializer({
            "success": True,
            "magazine_id": magazine.magazine_id,
            "message": "Magazine created successfully."
        })
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='magazines')
    def list_magazines(self, request):
        magazines = Magazine.objects.filter(user=request.user)
        serializer = MagazineSerializer(magazines, many=True)
        return Response({
            "success": True,
            "magazines": serializer.data
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['put'], url_path='magazines/(?P<magazine_id>[^/.]+)')
    def update_magazine(self, request, magazine_id=None):
        serializer = CreateMagazineRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            magazine = Magazine.objects.get(magazine_id=magazine_id, user=request.user)
        except Magazine.DoesNotExist:
            return Response({"success": False, "error": "Magazine not found."}, status=status.HTTP_404_NOT_FOUND)
        magazine.title = serializer.validated_data.get('magazine_title', magazine.title)
        magazine.save()
        return Response({
            "success": True,
            "magazine_id": magazine.magazine_id,
            "message": "Magazine updated successfully."
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['delete'], url_path='magazines/(?P<magazine_id>[^/.]+)')
    def delete_magazine(self, request, magazine_id=None):
        try:
            magazine = Magazine.objects.get(magazine_id=magazine_id, user=request.user)
            magazine.delete()
            return Response({
                "success": True,
                "message": "Magazine deleted successfully."
            }, status=status.HTTP_200_OK)
        except Magazine.DoesNotExist:
            return Response({"success": False, "error": "Magazine not found."}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'], url_path='magazines/(?P<magazine_id>[^/.]+)/duplicate')
    def duplicate_magazine(self, request, magazine_id=None):
        try:
            original_magazine = Magazine.objects.get(magazine_id=magazine_id, user=request.user)
            duplicated_magazine = original_magazine.duplicate()  # Implement duplicate logic in model
            return Response({
                "success": True,
                "new_magazine_id": duplicated_magazine.magazine_id,
                "message": "Magazine duplicated successfully."
            }, status=status.HTTP_201_CREATED)
        except Magazine.DoesNotExist:
            return Response({"success": False, "error": "Magazine not found."}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'], url_path='magazines/(?P<magazine_id>[^/.]+)/input-data')
    def submit_input_data(self, request, magazine_id=None):
        serializer = SubmitAirbnbURLRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            magazine = Magazine.objects.get(magazine_id=magazine_id, user=request.user)
            # Process input data and start AI process
            ai_process = AIProcess.objects.create(magazine=magazine, status='Pending')
            # Implement data submission logic
            return Response({
                "success": True,
                "message": "Data received. AI content generation started.",
                "ai_process_id": ai_process.ai_process_id
            }, status=status.HTTP_202_ACCEPTED)
        except Magazine.DoesNotExist:
            return Response({"success": False, "error": "Magazine not found."}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'], url_path='magazines/(?P<magazine_id>[^/.]+)/generate-content')
    def start_ai_content_generation(self, request, magazine_id=None):
        try:
            magazine = Magazine.objects.get(magazine_id=magazine_id, user=request.user)
            ai_process = AIProcess.objects.create(magazine=magazine, status='In_Progress')
            # Implement AI content generation logic
            return Response({
                "success": True,
                "message": "AI content generation initiated.",
                "ai_process_id": ai_process.ai_process_id
            }, status=status.HTTP_202_ACCEPTED)
        except Magazine.DoesNotExist:
            return Response({"success": False, "error": "Magazine not found."}, status=status.HTTP_404_NOT_FOUND)

class AIProcessViewSet(viewsets.ViewSet):
    def get_permissions(self):
        from rest_framework.permissions import IsAuthenticated
        return [IsAuthenticated()]

    @action(detail=True, methods=['get'], url_path='ai-processes/(?P<ai_process_id>[^/.]+)/status')
    def get_ai_status(self, request, ai_process_id=None):
        try:
            ai_process = AIProcess.objects.get(ai_process_id=ai_process_id, magazine__user=request.user)
            serializer = AIContentGenerationStatusSerializer({
                "success": True,
                "status": ai_process.status,
                "progress": ai_process.progress,
                "estimated_time_remaining": ai_process.estimated_time_remaining
            })
            return Response(serializer.data, status=status.HTTP_200_OK)
        except AIProcess.DoesNotExist:
            return Response({"success": False, "error": "AI process not found."}, status=status.HTTP_404_NOT_FOUND)

class PageViewSet(viewsets.ViewSet):
    def get_permissions(self):
        from rest_framework.permissions import IsAuthenticated
        return [IsAuthenticated()]

    @action(detail=True, methods=['put'], url_path='magazines/(?P<magazine_id>[^/.]+)/pages/(?P<page_id>[^/.]+)')
    def update_page_content(self, request, magazine_id=None, page_id=None):
        serializer = UpdatePageContentRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            page = Page.objects.get(page_id=page_id, magazine__magazine_id=magazine_id, magazine__user=request.user)
            page.content = serializer.validated_data['content']
            page.accepted = serializer.validated_data['accepted']
            page.save()
            return Response({
                "success": True,
                "message": "Page updated successfully."
            }, status=status.HTTP_200_OK)
        except Page.DoesNotExist:
            return Response({"success": False, "error": "Page not found."}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['get'], url_path='magazines/(?P<magazine_id>[^/.]+)/pages/(?P<page_id>[^/.]+)')
    def get_page_details(self, request, magazine_id=None, page_id=None):
        try:
            page = Page.objects.get(page_id=page_id, magazine__magazine_id=magazine_id, magazine__user=request.user)
            content = GeneratedContentSerializer(page.content).data
            return Response({
                "success": True,
                "page": content
            }, status=status.HTTP_200_OK)
        except Page.DoesNotExist:
            return Response({"success": False, "error": "Page not found."}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'], url_path='magazines/(?P<magazine_id>[^/.]+)/pages')
    def add_new_page(self, request, magazine_id=None):
        serializer = AddPageRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            magazine = Magazine.objects.get(magazine_id=magazine_id, user=request.user)
            page = Page.objects.create(magazine=magazine, content=serializer.validated_data['content'])
            return Response({
                "success": True,
                "page_id": page.page_id,
                "message": "Page added successfully."
            }, status=status.HTTP_201_CREATED)
        except Magazine.DoesNotExist:
            return Response({"success": False, "error": "Magazine not found."}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['delete'], url_path='magazines/(?P<magazine_id>[^/.]+)/pages/(?P<page_id>[^/.]+)/delete')
    def delete_page(self, request, magazine_id=None, page_id=None):
        try:
            page = Page.objects.get(page_id=page_id, magazine__magazine_id=magazine_id, magazine__user=request.user)
            page.delete()
            return Response({
                "success": True,
                "message": "Page deleted successfully."
            }, status=status.HTTP_200_OK)
        except Page.DoesNotExist:
            return Response({"success": False, "error": "Page not found."}, status=status.HTTP_404_NOT_FOUND)

class QRCodeViewSet(viewsets.ViewSet):
    def get_permissions(self):
        from rest_framework.permissions import IsAuthenticated
        return [IsAuthenticated()]

    @action(detail=True, methods=['get'], url_path='magazines/(?P<magazine_id>[^/.]+)/qr-codes')
    def list_qrcodes(self, request, magazine_id=None):
        try:
            qr_codes = QRCode.objects.filter(magazine__magazine_id=magazine_id, magazine__user=request.user)
            serializer = QRCodeSerializer(qr_codes, many=True)
            return Response({
                "success": True,
                "qr_codes": serializer.data
            }, status=status.HTTP_200_OK)
        except Magazine.DoesNotExist:
            return Response({"success": False, "error": "Magazine not found."}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['put'], url_path='magazines/(?P<magazine_id>[^/.]+)/qr-codes/(?P<qr_code_id>[^/.]+)')
    def customize_qrcode(self, request, magazine_id=None, qr_code_id=None):
        serializer = CustomizeQRCodeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            qr_code = QRCode.objects.get(qr_code_id=qr_code_id, magazine__magazine_id=magazine_id, magazine__user=request.user)
            qr_code.color = serializer.validated_data.get('color', qr_code.color)
            qr_code.logo_url = serializer.validated_data.get('logo_url', qr_code.logo_url)
            qr_code.linked_url = serializer.validated_data.get('linked_url', qr_code.linked_url)
            qr_code.save()
            return Response({
                "success": True,
                "qr_code_url": qr_code.qr_code_url,
                "message": "QR code customized successfully."
            }, status=status.HTTP_200_OK)
        except QRCode.DoesNotExist:
            return Response({"success": False, "error": "QR code not found."}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['get'], url_path='magazines/(?P<magazine_id>[^/.]+)/qr-codes/(?P<qr_code_id>[^/.]+)/download')
    def download_qrcode(self, request, magazine_id=None, qr_code_id=None):
        try:
            qr_code = QRCode.objects.get(qr_code_id=qr_code_id, magazine__magazine_id=magazine_id, magazine__user=request.user)
            # Assuming qr_code.qr_code_url points to the file location
            from django.http import FileResponse
            import requests
            response = requests.get(qr_code.qr_code_url)
            return Response(response.content, content_type='image/png')
        except QRCode.DoesNotExist:
            return Response({"success": False, "error": "QR code not found."}, status=status.HTTP_404_NOT_FOUND)

class CTAViewSet(viewsets.ViewSet):
    def get_permissions(self):
        from rest_framework.permissions import IsAuthenticated
        return [IsAuthenticated()]

    @action(detail=True, methods=['get'], url_path='magazines/(?P<magazine_id>[^/.]+)/ctas')
    def list_ctas(self, request, magazine_id=None):
        try:
            ctas = CTA.objects.filter(magazine__magazine_id=magazine_id, magazine__user=request.user)
            serializer = CTA_Serializer(ctas, many=True)
            return Response({
                "success": True,
                "ctas": serializer.data
            }, status=status.HTTP_200_OK)
        except Magazine.DoesNotExist:
            return Response({"success": False, "error": "Magazine not found."}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['put'], url_path='magazines/(?P<magazine_id>[^/.]+)/ctas/(?P<page_id>[^/.]+)')
    def update_cta(self, request, magazine_id=None, page_id=None):
        serializer = UpdateCTADRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            cta = CTA.objects.get(page__page_id=page_id, magazine__magazine_id=magazine_id, magazine__user=request.user)
            cta.custom_cta = serializer.validated_data.get('custom_cta', cta.custom_cta)
            cta.linked_url = serializer.validated_data.get('linked_url', cta.linked_url)
            if serializer.validated_data.get('accept_suggestion', False):
                cta.custom_cta = cta.suggested_cta
            cta.save()
            return Response({
                "success": True,
                "message": "CTA updated successfully."
            }, status=status.HTTP_200_OK)
        except CTA.DoesNotExist:
            return Response({"success": False, "error": "CTA not found."}, status=status.HTTP_404_NOT_FOUND)