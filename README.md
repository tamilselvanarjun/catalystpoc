
# Business Chart Generation Project
This project provides APIs for generating and managing various business charts. It currently supports the creation of Mekko charts, while other chart types are still under development.

## Prerequisites

Before running the project, make sure you have the following:

- Python 3.8 or above installed
- Django framework installed
- Azure Blob Storage account credentials

## Getting Started
Clone the repository
git clone https://github.com/arjunlimat/catalystpoc.git

Install the required dependencies:
pip install -r requirements.txt
Configure Azure Blob Storage credentials:

## Open the config.py file and provide the appropriate values for the following variables:
STORAGE_ACCOUNT_KEY = "your-storage-account-key"
STORAGE_ACCOUNT_NAME = "your-storage-account-name"
CONNECTION_STRING = "your-connection-string"
CONTAINER_NAME = "your-container-name"

##Start the Django server:
python manage.py runserver


##Access the application:

Open your web browser and visit http://localhost:8000 to access the application.

Uploading and Viewing Charts
Upload a chart file:
View existing charts:

##API Endpoints
The following API endpoints are available:

/api/upload/: API endpoint for uploading a chart file.
/api/view-charts/: API endpoint for viewing existing charts.
/api/load-chart/?projectName=chart-name: API endpoint for loading a specific chart.
/api/process-chart/: API endpoint for processing chart requests.

##Chart Processing
To process a chart, send a POST request to the /api/process-chart/ endpoint with the following JSON payload:
{
  // Please refer to test.json file for JSON payload structure
}
Replace the chart and type values as needed. Currently, only the Mekko chart type is supported. The response will contain the processed chart data in JSON format.

##Chart Types
Currently, the project supports the following chart types:

Mekko
Butterfly (under development)
Rank (under development)
OSM (under development)
Other chart types (under development)
Contributing
Contributions to this project are welcome. Feel free to open issues and submit pull requests to help improve the functionality and features.
