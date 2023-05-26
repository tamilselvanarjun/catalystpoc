from django.contrib import admin
from django.urls import path
from .views import Processing, DBProcess, Upload, LoadChart, ViewExistingChart

urlpatterns =  [
   #path('chartgeneration', Processing, name="Processing")
   path('chartgeneration', Processing.as_view(), name="Processing"),
   path('Arsenal', DBProcess.as_view(), name="DBProcess"),
   path('upload', Upload.as_view(), name="Upload"),
   path('loadchart', LoadChart.as_view(), name="LoadChart"),
   path('viewexistingcharts', ViewExistingChart.as_view(), name="ViewExistingChart"),
]

