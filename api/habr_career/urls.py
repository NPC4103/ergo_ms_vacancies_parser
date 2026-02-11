from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import VacancyViewSet, ParsingControlViewSet, OAuthViewSet

router = DefaultRouter()
router.register(r'vacancies', VacancyViewSet, basename='vacancy')
router.register(r'parsing', ParsingControlViewSet, basename='parsing')
router.register(r'oauth', OAuthViewSet, basename='oauth')

urlpatterns = [
    path('', include(router.urls)),
]
