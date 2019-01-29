from rest_framework import serializers


class EmailFieldSerializer(serializers.Serializer):
    max_length = serializers.CharField(default=1, allow_null=True, required=False)
    min_length = serializers.CharField(default=1, allow_null=True, required=False)
    required = serializers.BooleanField(default=False)
    label = serializers.CharField(default='', allow_blank=True, allow_null=True, required=False)
    initial = serializers.CharField(default='', allow_blank=True, allow_null=True, required=False)
    help_text = serializers.CharField(default='', allow_blank=True, allow_null=True, required=False)
    name = serializers.CharField(default='', allow_blank=True, allow_null=True, required=False)

