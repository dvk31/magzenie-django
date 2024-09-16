from rest_framework import serializers
from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import Permission, Group
from django.contrib.contenttypes.models import ContentType
from django.contrib.sessions.models import Session
from rest_framework.authtoken.models import Token, TokenProxy
from django_celery_results.models import TaskResult, ChordCounter, GroupResult
from core.models import RedisConfig, AITools
from mock_data.models import MockData, MockUserInfo

class LogEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = LogEntry
        fields = ['id', 'action_time', 'user', 'content_type', 'object_id', 'object_repr', 'action_flag', 'change_message']

class PermissionSerializer(serializers.ModelSerializer):
    group = serializers.PrimaryKeyRelatedField(read_only=True)
    user_usersmodels = serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model = Permission
        fields = ['id', 'name', 'content_type', 'codename', 'group', 'user_usersmodels']

class GroupSerializer(serializers.ModelSerializer):
    permissions = serializers.PrimaryKeyRelatedField(read_only=True)
    user_usersmodels = serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model = Group
        fields = ['id', 'name', 'permissions', 'user_usersmodels']

class ContentTypeSerializer(serializers.ModelSerializer):
    logentry = serializers.PrimaryKeyRelatedField(read_only=True)
    permission = serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model = ContentType
        fields = ['id', 'app_label', 'model', 'logentry', 'permission']

class SessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Session
        fields = ['session_key', 'session_data', 'expire_date']

class TokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Token
        fields = ['key', 'user', 'created']

class TokenProxySerializer(serializers.ModelSerializer):
    class Meta:
        model = TokenProxy
        fields = ['key', 'user', 'created']

class TaskResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskResult
        fields = ['id', 'task_id', 'periodic_task_name', 'task_name', 'task_args', 'task_kwargs', 'status', 'worker', 'content_type', 'content_encoding', 'result', 'date_created', 'date_done', 'traceback', 'meta']

class ChordCounterSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChordCounter
        fields = ['id', 'group_id', 'sub_tasks', 'count']

class GroupResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupResult
        fields = ['id', 'group_id', 'date_created', 'date_done', 'content_type', 'content_encoding', 'result']

class RedisConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = RedisConfig
        fields = ['id', 'name', 'data']

class AIToolsSerializer(serializers.ModelSerializer):
    class Meta:
        model = AITools
        fields = ['id', 'created_at', 'updated_at', 'name', 'description', 'instruction', 'json_schema']

class MockDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = MockData
        fields = ['created_at', 'updated_at', 'id', 'json_data']

class MockUserInfoSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model = MockUserInfo
        fields = ['created_at', 'updated_at', 'id', 'user_id', 'phone_number', 'user_name', 'full_name', 'email', 'gender', 'age', 'user_story', 'is_created', 'public_display_name', 'profile_thumbnail', 'profile_large_image', 'bio', 'birth_date', 'dalee_image_processed', 'user']

