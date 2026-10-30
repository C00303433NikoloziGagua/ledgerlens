from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('documents/upload/', views.upload, name='upload'),
    path('documents/<uuid:pk>/', views.detail, name='document_detail'),
    path('documents/<uuid:pk>/file/', views.original_file, name='document_file'),
]
