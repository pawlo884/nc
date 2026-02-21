"""
Viewy API dla aplikacji web_agent.
"""
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import AutomationRun, ProductProcessingLog
from .serializers import (
    AutomationRunSerializer,
    ProductProcessingLogSerializer,
    StartAutomationSerializer
)
from .tasks import automate_mpd_form_filling, automate_tabu_to_mpd

logger = logging.getLogger(__name__)


class AutomationRunViewSet(viewsets.ModelViewSet):
    """
    ViewSet dla zarządzania uruchomieniami automatyzacji.
    """
    queryset = AutomationRun.objects.all()
    serializer_class = AutomationRunSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filtrowanie queryset"""
        queryset = AutomationRun.objects.all()
        
        # Filtrowanie po statusie
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filtrowanie po brand_id
        brand_id = self.request.query_params.get('brand_id', None)
        if brand_id:
            queryset = queryset.filter(brand_id=brand_id)
        
        # Filtrowanie po category_id
        category_id = self.request.query_params.get('category_id', None)
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        # Filtrowanie po source (matterhorn1 | tabu)
        source = self.request.query_params.get('source', None)
        if source:
            queryset = queryset.filter(source=source)

        return queryset.order_by('-started_at')
    
    @action(detail=False, methods=['post'], url_path='start-automation')
    def start_automation(self, request):
        """
        Endpoint do uruchomienia automatyzacji wypełniania formularzy MPD.
        
        Parametry:
        - brand_id: ID marki (opcjonalne)
        - category_id: ID kategorii (opcjonalne)
        - filters: Dodatkowe filtry (opcjonalne)
        """
        serializer = StartAutomationSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        validated_data = serializer.validated_data
        source = validated_data.get('source', 'matterhorn1')

        try:
            if source == 'tabu':
                run = AutomationRun.objects.create(
                    status='running',
                    source='tabu',
                    brand_id=validated_data.get('brand_id'),
                    category_id=validated_data.get('category_id'),
                    filters=validated_data.get('filters', {}),
                )
                task = automate_tabu_to_mpd.delay(
                    brand_id=validated_data.get('brand_id'),
                    category_id=validated_data.get('category_id'),
                    filters=validated_data.get('filters', {}),
                    automation_run_id=run.id,
                )
                logger.info("Uruchomiono automatyzację Tabu→MPD - run_id=%s task_id=%s", run.id, task.id)
                return Response({
                    'status': 'started',
                    'task_id': task.id,
                    'automation_run_id': run.id,
                    'message': 'Automatyzacja Tabu→MPD została uruchomiona',
                }, status=status.HTTP_202_ACCEPTED)

            task = automate_mpd_form_filling.delay(
                brand_id=validated_data.get('brand_id'),
                category_id=validated_data.get('category_id'),
                filters=validated_data.get('filters', {}),
            )
            logger.info("Uruchomiono automatyzację Matterhorn1 - Task ID: %s", task.id)
            return Response({
                'status': 'started',
                'task_id': task.id,
                'message': 'Automatyzacja została uruchomiona',
            }, status=status.HTTP_202_ACCEPTED)
            
        except Exception as e:
            logger.error(f"Błąd podczas uruchamiania automatyzacji: {e}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'], url_path='logs')
    def get_logs(self, request, pk=None):
        """
        Endpoint do pobrania logów przetwarzania produktów dla danego uruchomienia.
        """
        automation_run = self.get_object()
        logs = ProductProcessingLog.objects.filter(
            automation_run=automation_run
        ).order_by('-processed_at')
        
        serializer = ProductProcessingLogSerializer(logs, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'], url_path='automation-logs')
    def get_automation_logs(self, request, pk=None):
        """
        Endpoint do pobrania logów automatyzacji w czasie rzeczywistym.
        """
        automation_run = self.get_object()
        return Response({
            'logs': automation_run.logs or '',
            'status': automation_run.status,
            'products_processed': automation_run.products_processed,
            'products_success': automation_run.products_success,
            'products_failed': automation_run.products_failed,
        })


class ProductProcessingLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet tylko do odczytu dla logów przetwarzania produktów.
    """
    queryset = ProductProcessingLog.objects.all()
    serializer_class = ProductProcessingLogSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filtrowanie queryset"""
        queryset = ProductProcessingLog.objects.all()
        
        # Filtrowanie po automation_run
        automation_run_id = self.request.query_params.get('automation_run', None)
        if automation_run_id:
            queryset = queryset.filter(automation_run_id=automation_run_id)
        
        # Filtrowanie po statusie
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filtrowanie po product_id
        product_id = self.request.query_params.get('product_id', None)
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        
        return queryset.order_by('-processed_at')
