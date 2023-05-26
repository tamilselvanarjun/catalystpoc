import pytest
import json
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from .config import storage_account_key, storage_account_name, connection_string, container_name

@pytest.fixture
def api_client():
    return APIClient()

@pytest.mark.django_db
def test_upload(api_client):
    url = reverse('upload')
    file_path = '/files/test_file.xlsx'
    file_data = {
        'file': open(file_path, 'rb'),
        'name': 'Test Project'
    }
    response = api_client.post(url, data=file_data, format='multipart')
    assert response.status_code == status.HTTP_200_OK
    assert "File uploaded successfully" in response.content.decode()

@pytest.mark.django_db
def test_view_existing_chart(api_client):
    url = reverse('view-existing-chart')
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.data, list)

@pytest.mark.django_db
def test_load_chart(api_client):
    url = reverse('load-chart')
    project_name = 'Test Project'
    query_params = {
        'projectName': project_name
    }
    response = api_client.get(url, data=query_params)
    assert response.status_code == status.HTTP_200_OK
    assert "https://" in response.content.decode()

@pytest.mark.django_db
def test_processing(api_client):
    url = reverse('processing')
    
    with open('test.json') as file:
        json_data = json.load(file)
    
    response = api_client.post(url, data=json_data, format='json')
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.data, dict)

    # Add assertions for the processed chart data
