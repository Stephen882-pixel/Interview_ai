from django.urls import path,include
from rest_framework.routers import  DefaultRouter
from .views import InterviewViewSet,ProgrammingSkillViewSet

router = DefaultRouter()

router.register(r'interviews', InterviewViewSet, basename='interview')
router.register(r'skills', ProgrammingSkillViewSet, basename='skill')

urlpatterns = [
    path('', include(router.urls)),
]

