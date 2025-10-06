from rest_framework import serializers
from .models import WebAgentTask, WebAgentLog, WebAgentConfig


class WebAgentConfigSerializer(serializers.ModelSerializer):
    """Serializer dla konfiguracji agenta web"""
    
    class Meta:
        model = WebAgentConfig
        fields = [
            'id', 'name', 'description', 'config_data', 
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class WebAgentLogSerializer(serializers.ModelSerializer):
    """Serializer dla logów agenta web"""
    
    class Meta:
        model = WebAgentLog
        fields = [
            'id', 'level', 'message', 'timestamp', 'extra_data'
        ]
        read_only_fields = ['id', 'timestamp']


class WebAgentTaskSerializer(serializers.ModelSerializer):
    """Serializer dla zadań agenta web"""
    
    logs = WebAgentLogSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    task_type_display = serializers.CharField(source='get_task_type_display', read_only=True)
    
    class Meta:
        model = WebAgentTask
        fields = [
            'id', 'name', 'task_type', 'task_type_display', 'url', 
            'status', 'status_display', 'created_at', 'updated_at',
            'started_at', 'completed_at', 'config', 'result', 
            'error_message', 'celery_task_id', 'logs'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'started_at', 
            'completed_at', 'celery_task_id', 'logs'
        ]
    
    def validate_config(self, value):
        """Walidacja konfiguracji"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Konfiguracja musi być obiektem JSON")
        return value
    
    def validate_result(self, value):
        """Walidacja wyniku"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Wynik musi być obiektem JSON")
        return value


class WebAgentTaskCreateSerializer(serializers.ModelSerializer):
    """Serializer dla tworzenia zadań agenta web"""
    
    class Meta:
        model = WebAgentTask
        fields = [
            'name', 'task_type', 'url', 'config'
        ]
    
    def validate_config(self, value):
        """Walidacja konfiguracji"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Konfiguracja musi być obiektem JSON")
        return value


class WebAgentTaskUpdateSerializer(serializers.ModelSerializer):
    """Serializer dla aktualizacji zadań agenta web"""
    
    class Meta:
        model = WebAgentTask
        fields = [
            'name', 'task_type', 'url', 'config'
        ]
    
    def validate_config(self, value):
        """Walidacja konfiguracji"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Konfiguracja musi być obiektem JSON")
        return value


class WebAgentTaskStatusSerializer(serializers.ModelSerializer):
    """Serializer dla aktualizacji statusu zadania"""
    
    class Meta:
        model = WebAgentTask
        fields = ['status', 'result', 'error_message']
    
    def validate_result(self, value):
        """Walidacja wyniku"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Wynik musi być obiektem JSON")
        return value


class WebAgentTaskStatsSerializer(serializers.Serializer):
    """Serializer dla statystyk zadań"""
    
    total_tasks = serializers.IntegerField()
    pending_tasks = serializers.IntegerField()
    running_tasks = serializers.IntegerField()
    completed_tasks = serializers.IntegerField()
    failed_tasks = serializers.IntegerField()
    cancelled_tasks = serializers.IntegerField()
    
    def to_representation(self, instance):
        """Konwersja danych do reprezentacji"""
        return {
            'total_tasks': instance.get('total_tasks', 0),
            'pending_tasks': instance.get('pending_tasks', 0),
            'running_tasks': instance.get('running_tasks', 0),
            'completed_tasks': instance.get('completed_tasks', 0),
            'failed_tasks': instance.get('failed_tasks', 0),
            'cancelled_tasks': instance.get('cancelled_tasks', 0),
        }
