import subprocess
import json
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema


from rest_framework import serializers

class CreateSupabaseInstanceSerializer(serializers.Serializer):
    userId = serializers.UUIDField()

class SupabaseInstanceResponseSerializer(serializers.Serializer):
    project_ref = serializers.CharField()
    db_password = serializers.CharField()


class CreateSupabaseInstanceView(APIView):
    @swagger_auto_schema(
        request_body=CreateSupabaseInstanceSerializer,
        responses={200: SupabaseInstanceResponseSerializer}
    )
    def post(self, request):
        serializer = CreateSupabaseInstanceSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user_id = serializer.validated_data['userId']

        try:
            # Run the shell script to create Supabase instance
            result = subprocess.run(
                ['/usr/local/bin/create_supabase_instance.sh', str(user_id)],
                capture_output=True,
                text=True,
                check=True
            )

            # Parse the output
            instance_data = json.loads(result.stdout)

            response_serializer = SupabaseInstanceResponseSerializer(data=instance_data)
            if response_serializer.is_valid():
                return Response(response_serializer.validated_data)
            else:
                return Response(response_serializer.errors, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except subprocess.CalledProcessError as e:
            return Response({'error': f'Failed to create Supabase instance: {e.stderr}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except json.JSONDecodeError:
            return Response({'error': 'Invalid JSON in script output'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({'error': f'Unexpected error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)