"""
Serializery DRF dla aplikacji web_agent.
"""
from rest_framework import serializers
from .models import AutomationRun, ProductProcessingLog


class ProductProcessingLogSerializer(serializers.ModelSerializer):
    """Serializer dla ProductProcessingLog"""
    
    class Meta:
        model = ProductProcessingLog
        fields = [
            'id', 'automation_run', 'product_id', 'product_name',
            'status', 'mpd_product_id', 'error_message', 'processed_at',
            'processing_data'
        ]
        read_only_fields = ['id', 'processed_at']


class AutomationRunSerializer(serializers.ModelSerializer):
    """Serializer dla AutomationRun"""
    
    product_logs = ProductProcessingLogSerializer(many=True, read_only=True)
    duration_seconds = serializers.SerializerMethodField()
    
    class Meta:
        model = AutomationRun
        fields = [
            'id', 'started_at', 'completed_at', 'status',
            'products_processed', 'products_success', 'products_failed',
            'error_message', 'brand_id', 'category_id', 'filters', 'source',
            'product_logs', 'duration_seconds'
        ]
        read_only_fields = ['id', 'started_at', 'completed_at']
    
    def get_duration_seconds(self, obj):
        """Oblicza czas trwania w sekundach"""
        if obj.duration:
            return obj.duration.total_seconds()
        return None


class StartAutomationSerializer(serializers.Serializer):
    """Serializer dla parametrów uruchomienia automatyzacji"""

    source = serializers.ChoiceField(
        choices=[('matterhorn1', 'Matterhorn1'), ('tabu', 'Tabu')],
        default='matterhorn1',
        required=False,
    )
    brand_id = serializers.IntegerField(required=False, allow_null=True)
    category_id = serializers.IntegerField(required=False, allow_null=True)
    filters = serializers.DictField(required=False, default=dict)

    def validate(self, data):
        """Walidacja danych – dla matterhorn1 wymagane brand_id lub category_id."""
        if data.get('source', 'matterhorn1') == 'matterhorn1':
            if not data.get('brand_id') and not data.get('category_id'):
                raise serializers.ValidationError(
                    "Dla źródła matterhorn1 podaj przynajmniej brand_id lub category_id"
                )
        return data

