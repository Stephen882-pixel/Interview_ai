"""
URL configuration for interview_ai project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include
from rest_framework.routers import  DefaultRouter
from core.views import InterviewViewSet,UserRegistrationView,LoginView,ProgrammingSkillViewSet

router = DefaultRouter()
router.register(r'interviews', InterviewViewSet, basename='interview')
router.register(r'skills', ProgrammingSkillViewSet, basename='skill')
router.register(r'interviews', InterviewViewSet, basename='interviews')
router.register(r'interviews', InterviewViewSet,basename='int')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include(router.urls)),

    path('register/',UserRegistrationView.as_view(),name='register'),
    path('login/',LoginView.as_view(),name='login'),


]

