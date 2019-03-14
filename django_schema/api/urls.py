from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import AppsAndModelsList

router = DefaultRouter()

urlpatterns = [
    path('apps-and-models', AppsAndModelsList.as_view())
]
urlpatterns += router.urls
