from rest_framework.response import Response
from rest_framework.views import APIView

from ..views import get_apps_and_models


class AppsAndModelsList(APIView):
    """
    Return all the apps and models from the application
    """

    def get(self, request, format=None):
        """
        """

        apps_and_models = {}
        for app, _models in get_apps_and_models().items():
            models = []
            if _models:
                models = [model.__name__ for model in _models]
            apps_and_models.update({app:models})
        return Response(apps_and_models)
