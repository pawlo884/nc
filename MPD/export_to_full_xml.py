import xlm.etree.ElementTree as ET
from xlm.dom import minidom
from datetime import datetime
from django.utils import timezone
from .models import Sources
from matterhorn.defs_db import s3_client, DO_SPACES_BUCKET, DO_SPACES_REGION

def export_to_full_xml():
    


    root = ET.Element( )