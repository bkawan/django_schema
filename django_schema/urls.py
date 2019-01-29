from django.urls import path

from .views import LocalInstallApps, ModelsOfLocalApp, LocalInstallAppsStyleOne, SchemaIndexView

app_name = 'django_schema'

urlpatterns = [
    path('', SchemaIndexView.as_view(), name='schema_index'),
    path('local-apps/', LocalInstallApps.as_view(), name='local-apps'),
    path('local-apps/style/one/', LocalInstallAppsStyleOne.as_view(), name='local-apps-style-one'),
    path('local-apps/<app_name>/', ModelsOfLocalApp.as_view(), name='models-of-local-apps'),
    path('local-apps/<app_name>/style/<style>/', ModelsOfLocalApp.as_view(), name='models-of-local-apps-style-one'),

]
