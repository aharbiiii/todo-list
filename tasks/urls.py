from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import TaskViewSet, register_view, login_view, logout_view, dashboard, task_action

router = DefaultRouter()
router.register(r'tasks', TaskViewSet, basename='task')

urlpatterns = router.urls + [
    path('dashboard/', dashboard, name='dashboard'),
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('task/<int:task_id>/action/', task_action, name='task_action'),
]
