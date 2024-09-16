# core/base_models.py

import json
import logging
import threading
import uuid
from django.conf import settings
from django.db import models
from django.core.serializers.json import DjangoJSONEncoder

logger = logging.getLogger(__name__)

class UUIDEncoder(DjangoJSONEncoder):
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        return super().default(obj)

def json_serialize(data):
    return json.dumps(data, cls=UUIDEncoder)

class JSONSerializableMixin:
    def to_dict(self):
        return {field.name: getattr(self, field.name) for field in self._meta.fields}

    def to_json(self):
        return json_serialize(self.to_dict())

class BaseModelManager(models.Manager):
    thread_local = threading.local()

    def create(self, **kwargs):
        if 'user' not in kwargs and hasattr(self.model, 'user'):
            request = getattr(self.thread_local, 'request', None)
            if request and request.user.is_authenticated:
                kwargs['user'] = request.user
        return super().create(**kwargs)

class BaseModel(JSONSerializableMixin, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = BaseModelManager()

    class Meta:
        abstract = True
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.__class__.__name__} {self.id}"

    def save(self, *args, **kwargs):
        if hasattr(self, 'user') and not self.user_id:
            request = getattr(self._state, 'request', None)
            if request and request.user.is_authenticated:
                self.user = request.user
        super().save(*args, **kwargs)

    @classmethod
    def get_valid_fields(cls):
        return [f.name for f in cls._meta.get_fields() if not f.is_relation]

    def __getattribute__(self, name):
        attr = super().__getattribute__(name)
        if isinstance(attr, models.JSONField):
            if isinstance(attr, str):
                try:
                    return json.loads(attr)
                except json.JSONDecodeError:
                    return attr
        return attr