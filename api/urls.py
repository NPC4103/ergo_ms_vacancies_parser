from django.urls import path, include

urlpatterns = [
    path('headhunter/', include('modules.vacancies_parser.api.headhunter.urls')),
]

