import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework import status

from .export_to_xml import FullXMLExporter
from .views import update_all_gateways

logger = logging.getLogger(__name__)


class GenerateFullXMLSecure(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        try:
            exporter = FullXMLExporter()
            result = exporter.export_incremental()
            update_all_gateways()

            return Response(
                {
                    'status': 'success',
                    'message': 'Pełny eksport XML został wygenerowany',
                    'bucket_url': result.get('bucket_url'),
                    'local_path': result.get('local_path'),
                    'skipped': result.get('skipped', False),
                },
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            logger.error(f'Błąd podczas generowania full.xml (secure): {exc}')
            return Response(
                {
                    'status': 'error',
                    'message': f'Błąd podczas generowania pełnego XML: {exc}',
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

