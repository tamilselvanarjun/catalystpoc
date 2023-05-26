from django.shortcuts import render
import sys
import os
import plotly.io as pio
import json
import socket
import requests
from rest_framework import renderers
from django.conf import settings
from django.http import JsonResponse, HttpResponse, HttpResponseServerError, FileResponse
from rest_framework.views import APIView
from rest_framework.parsers import JSONParser
from django.shortcuts import render
from django.views.generic import TemplateView
import pyodbc
import sqlalchemy
import openpyxl
from django.core.files.storage import default_storage
from azure.storage.blob import BlobServiceClient, BlobSasPermissions, generate_blob_sas
from django.core.files.base import ContentFile
import pandas as pd
from datetime import datetime, timedelta

from chartgeneration import (
    jsonconverter, mekkochart, butterfly, normativeband, bubblechart,
    normativegrowth, growthshare, osm, rank, growthgrowth, marketvaluedrivers
)
from plotly.offline import plot
import io
import base64
from .config import storage_account_key, storage_account_name, connection_string, container_name

# Create views
class Upload(APIView):
    """
    API endpoint for uploading a file.
    """
    def post(self, request):
        file = request.FILES["file"]
        filename = file.name
        data = request.POST.items()
        json_data = request.data
        test_file = 'Test.xlsx'
        path = default_storage.save(test_file, ContentFile(file.read()))
        project_name = json_data['name'] + ".xlsx"
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=project_name)
        if blob_client.exists():
            project_name = project_name.replace('.xlsx', '')
            return HttpResponse("Chart name '{0}' already exists".format(project_name))
        with open(test_file, 'rb') as data:
            blob_client.upload_blob(data)
        os.remove(test_file)
        return HttpResponse("File uploaded successfully")


class ViewExistingChart(APIView):
    """
    API endpoint for viewing existing charts.
    """
    def get(self, request):
        response = []
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service_client.get_container_client(container=container_name)
        blob_list = container_client.list_blobs()
        for blob in blob_list:
            if not str(blob.name).endswith('.json'):
                project_name = str(blob.name).replace('.xlsx', '')
                project_dict = {
                    'projectName': project_name,
                    'Name': project_name,
                    'Type': 'Mekko'
                }
                response.append(project_dict)
        return JsonResponse(response, safe=False)


class LoadChart(APIView):
    """
    API endpoint for loading a chart.
    """
    def get(self, request):
        filename = request.query_params['projectName']
        filename = filename + ".xlsx"
        sas = generate_blob_sas(
            account_name=storage_account_name,
            container_name=container_name,
            blob_name=filename,
            account_key=storage_account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(hours=1)
        )
        filename = filename.replace(' ', '%20')
        blob_url = f'https://{storage_account_name}.blob.core.windows.net/{container_name}/{filename}?{sas}'
        filename = filename.replace('%20', ' ')
        df = pd.read_excel(blob_url, skiprows=[0])
        project_df = df[list(df.columns)[:2]]
        project_dict = dict(zip(project_df[project_df.columns[0]].to_list(), project_df[project_df.columns[1]].to_list()))
        cols = list(df.columns)[3:]
        data = []
        for col in cols:
            if 'Unnamed' in col:
                break
            else:
                data.append(col)
        df = df[data]
        index_break = 0
        for ind in df.index:
            if df['Series Label'][ind] == "RMS":
                index_break = ind
                break
        df = df.iloc[0:int(index_break), :]
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        filename = filename.replace('.xlsx', '.json')
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=filename)
        if blob_client.exists():
            sas = generate_blob_sas(
                account_name=storage_account_name,
                container_name=container_name,
                blob_name=filename,
                account_key=storage_account_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(hours=1)
            )
            filename = filename.replace(' ', '%20')
            blob_url = f'https://{storage_account_name}.blob.core.windows.net/{container_name}/{filename}?{sas}'
            filename = filename.replace('%20', ' ')
            df.to_json(blob_url, orient='records')
            return HttpResponse(blob_url)
        return HttpResponse("Chart does not exist.")


class Processing(APIView):
    """
    API view for processing chart requests.
    """

    parser_classes = (JSONParser,)

    def post(self, request):
        """
        Handle POST requests for chart processing.

        Parameters:
            request (HttpRequest): The HTTP request object.

        Returns:
            JsonResponse: The JSON response containing the processed chart data.

        Raises:
            HttpResponseServerError: If the input request is not valid.
        """
        try:
            json_data = request.data
        except KeyError:
            return HttpResponseServerError("Input request is not valid!")

        chart_type = json_data.get('type')
        if chart_type == 'plotly':
            chart_name = json_data.get('chart')
            if chart_name == 'mekko':
                response = mekkochart.create_plotly_chart(json_data)
            else:
                response = {}  # Handle other chart types here if needed
        else:
            response = {}  # Handle non-plotly chart types here if needed

        return JsonResponse(response)
