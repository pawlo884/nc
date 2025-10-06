from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import WebAgentTask, WebAgentLog, WebAgentConfig
from unittest.mock import Mock
from .serializers import (
    WebAgentTaskSerializer, WebAgentTaskCreateSerializer, 
    WebAgentTaskUpdateSerializer, WebAgentTaskStatusSerializer,
    WebAgentLogSerializer, WebAgentConfigSerializer,
    WebAgentTaskStatsSerializer
)
# from .tasks import start_web_agent_task, stop_web_agent_task


@extend_schema_view(
    list=extend_schema(
        summary="Lista zadań agenta web",
        description="Pobiera listę wszystkich zadań agenta web z możliwością filtrowania i wyszukiwania",
        tags=['Web Agent Tasks']
    ),
    create=extend_schema(
        summary="Utwórz nowe zadanie",
        description="Tworzy nowe zadanie agenta web",
        tags=['Web Agent Tasks']
    ),
    retrieve=extend_schema(
        summary="Szczegóły zadania",
        description="Pobiera szczegóły konkretnego zadania",
        tags=['Web Agent Tasks']
    ),
    update=extend_schema(
        summary="Aktualizuj zadanie",
        description="Aktualizuje zadanie agenta web",
        tags=['Web Agent Tasks']
    ),
    partial_update=extend_schema(
        summary="Częściowa aktualizacja zadania",
        description="Częściowo aktualizuje zadanie agenta web",
        tags=['Web Agent Tasks']
    ),
    destroy=extend_schema(
        summary="Usuń zadanie",
        description="Usuwa zadanie agenta web",
        tags=['Web Agent Tasks']
    ),
)
class WebAgentTaskViewSet(viewsets.ModelViewSet):
    """ViewSet dla zadań agenta web"""
    
    queryset = WebAgentTask.objects.all()
    serializer_class = WebAgentTaskSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    # filterset_fields = ['status', 'task_type', 'created_at']
    search_fields = ['name', 'url', 'error_message']
    ordering_fields = ['created_at', 'updated_at', 'name']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Zwraca odpowiedni serializer w zależności od akcji"""
        if self.action == 'create':
            return WebAgentTaskCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return WebAgentTaskUpdateSerializer
        return WebAgentTaskSerializer
    
    @extend_schema(
        summary="Uruchom zadanie",
        description="Uruchamia zadanie agenta web w tle",
        tags=['Web Agent Tasks']
    )
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Uruchamia zadanie"""
        task = self.get_object()
        
        if task.status not in ['pending', 'failed']:
            return Response(
                {'error': 'Zadanie można uruchomić tylko gdy ma status "pending" lub "failed"'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Uruchom zadanie w Celery
            # celery_task = start_web_agent_task.delay(task.id)
            celery_task = Mock(id='mock-celery-id')
            
            # Aktualizuj status zadania
            task.status = 'running'
            task.started_at = timezone.now()
            task.celery_task_id = celery_task.id
            task.save()
            
            # Dodaj log
            WebAgentLog.objects.create(
                task=task,
                level='INFO',
                message=f'Zadanie uruchomione z ID Celery: {celery_task.id}'
            )
            
            return Response(
                {'message': 'Zadanie uruchomione pomyślnie', 'celery_task_id': celery_task.id},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            task.status = 'failed'
            task.error_message = str(e)
            task.save()
            
            WebAgentLog.objects.create(
                task=task,
                level='ERROR',
                message=f'Błąd podczas uruchamiania zadania: {str(e)}'
            )
            
            return Response(
                {'error': f'Błąd podczas uruchamiania zadania: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        summary="Zatrzymaj zadanie",
        description="Zatrzymuje uruchomione zadanie agenta web",
        tags=['Web Agent Tasks']
    )
    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        """Zatrzymuje zadanie"""
        task = self.get_object()
        
        if task.status != 'running':
            return Response(
                {'error': 'Zadanie można zatrzymać tylko gdy ma status "running"'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Zatrzymaj zadanie w Celery
            if task.celery_task_id:
                # stop_web_agent_task.delay(task.celery_task_id)
                pass
            
            # Aktualizuj status zadania
            task.status = 'cancelled'
            task.completed_at = timezone.now()
            task.save()
            
            # Dodaj log
            WebAgentLog.objects.create(
                task=task,
                level='INFO',
                message='Zadanie zatrzymane przez użytkownika'
            )
            
            return Response(
                {'message': 'Zadanie zatrzymane pomyślnie'},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            WebAgentLog.objects.create(
                task=task,
                level='ERROR',
                message=f'Błąd podczas zatrzymywania zadania: {str(e)}'
            )
            
            return Response(
                {'error': f'Błąd podczas zatrzymywania zadania: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        summary="Aktualizuj status zadania",
        description="Aktualizuje status zadania (używane przez Celery)",
        tags=['Web Agent Tasks']
    )
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Aktualizuje status zadania"""
        task = self.get_object()
        serializer = WebAgentTaskStatusSerializer(data=request.data)
        
        if serializer.is_valid():
            task.status = serializer.validated_data.get('status', task.status)
            task.result = serializer.validated_data.get('result', task.result)
            task.error_message = serializer.validated_data.get('error_message', task.error_message)
            
            # Aktualizuj daty w zależności od statusu
            if task.status == 'running' and not task.started_at:
                task.started_at = timezone.now()
            elif task.status in ['completed', 'failed', 'cancelled'] and not task.completed_at:
                task.completed_at = timezone.now()
            
            task.save()
            
            return Response(
                {'message': 'Status zadania zaktualizowany pomyślnie'},
                status=status.HTTP_200_OK
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Statystyki zadań",
        description="Pobiera statystyki zadań agenta web",
        tags=['Web Agent Tasks']
    )
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Zwraca statystyki zadań"""
        stats = WebAgentTask.objects.aggregate(
            total_tasks=Count('id'),
            pending_tasks=Count('id', filter=Q(status='pending')),
            running_tasks=Count('id', filter=Q(status='running')),
            completed_tasks=Count('id', filter=Q(status='completed')),
            failed_tasks=Count('id', filter=Q(status='failed')),
            cancelled_tasks=Count('id', filter=Q(status='cancelled')),
        )
        
        serializer = WebAgentTaskStatsSerializer(stats)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(
        summary="Lista logów agenta web",
        description="Pobiera listę logów agenta web",
        tags=['Web Agent Logs']
    ),
    retrieve=extend_schema(
        summary="Szczegóły logu",
        description="Pobiera szczegóły konkretnego logu",
        tags=['Web Agent Logs']
    ),
)
class WebAgentLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet dla logów agenta web (tylko do odczytu)"""
    
    queryset = WebAgentLog.objects.all()
    serializer_class = WebAgentLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    # filterset_fields = ['level', 'task__status', 'timestamp']
    search_fields = ['message', 'task__name']
    ordering_fields = ['timestamp', 'level']
    ordering = ['-timestamp']


@extend_schema_view(
    list=extend_schema(
        summary="Lista konfiguracji agenta web",
        description="Pobiera listę konfiguracji agenta web",
        tags=['Web Agent Configs']
    ),
    create=extend_schema(
        summary="Utwórz nową konfigurację",
        description="Tworzy nową konfigurację agenta web",
        tags=['Web Agent Configs']
    ),
    retrieve=extend_schema(
        summary="Szczegóły konfiguracji",
        description="Pobiera szczegóły konkretnej konfiguracji",
        tags=['Web Agent Configs']
    ),
    update=extend_schema(
        summary="Aktualizuj konfigurację",
        description="Aktualizuje konfigurację agenta web",
        tags=['Web Agent Configs']
    ),
    partial_update=extend_schema(
        summary="Częściowa aktualizacja konfiguracji",
        description="Częściowo aktualizuje konfigurację agenta web",
        tags=['Web Agent Configs']
    ),
    destroy=extend_schema(
        summary="Usuń konfigurację",
        description="Usuwa konfigurację agenta web",
        tags=['Web Agent Configs']
    ),
)
class WebAgentConfigViewSet(viewsets.ModelViewSet):
    """ViewSet dla konfiguracji agenta web"""
    
    queryset = WebAgentConfig.objects.all()
    serializer_class = WebAgentConfigSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    # filterset_fields = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'updated_at']
    ordering = ['name']
