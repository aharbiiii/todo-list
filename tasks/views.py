from rest_framework import viewsets, permissions, status, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from django.http import HttpResponse
from django.utils import timezone
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect, get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from .serializers import TaskSerializer, UserSerializer
from .models import Task


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    filter_backends = [DjangoFilterBackend,
                       filters.SearchFilter, filters.OrderingFilter]

    filterset_fields = ['status', 'label', 'parent_task']
    search_fields = ['title', 'description']
    ordering_fields = ['created_on', 'completed_on']

    def get_queryset(self):
        return Task.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        task = serializer.save(user=self.request.user)
        self._update_parent_task_status(task.parent_task)

    def perform_update(self, serializer):
        if serializer.instance.user != self.request.user:
            raise PermissionDenied(
                "You do not have permission to edit this task.")
        task = serializer.save()
        self._update_parent_task_status(task.parent_task)

    def perform_destroy(self, instance):
        parent = instance.parent_task
        if instance.user != self.request.user:
            raise PermissionDenied(
                "You do not have permission to delete this task.")
        instance.delete()
        self._update_parent_task_status(parent)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        task = self.get_object()
        if task.user != request.user:
            return Response({"error": "Unauthorized"}, status=403)

        task.status = 'Cancelled'
        task.is_done = False
        task.completed_on = None
        task.save()

        return Response({"status": "Task cancelled."}, status=200)

    def _update_parent_task_status(self, parent_task):
        if parent_task is None:
            return

        sub_tasks = parent_task.sub_tasks.all()

        if all(sub_task.status == 'Done' for sub_task in sub_tasks):
            parent_task.status = 'Done'
            parent_task.is_done = True
            parent_task.completed_on = timezone.now()
        else:
            parent_task.status = 'Pending'
            parent_task.is_done = False
            parent_task.completed_on = None

        parent_task.save()


def home_view(request):
    return HttpResponse("<h1>Welcome to the Todo-List API</h1><p>Go to /api/ to access the API.</p>")


class RegisterUserView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, _ = Token.objects.get_or_create(user=user)
            return Response({'token': token.key}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginUserView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)

        if user is not None:
            token, _ = Token.objects.get_or_create(user=user)
            return Response({'token': token.key}, status=status.HTTP_200_OK)
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)


class LogoutUserView(APIView):

    def post(self, request):
        request.user.auth_token.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


def register_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        user = User.objects.create_user(
            username=username, email=email, password=password)
        login(request, user)
        return redirect('dashboard')
    return render(request, 'tasks/register.html')


def login_view(request):
    if request.method == 'POST':
        user = authenticate(
            request,
            username=request.POST['username'],
            password=request.POST['password']
        )
        if user:
            login(request, user)
            return redirect('dashboard')
        else:
            return render(request, 'tasks/login.html', {'error': 'Invalid credentials'})
    return render(request, 'tasks/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def dashboard(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        label = request.POST.get('label', '')

        Task.objects.create(
            user=request.user,
            title=title,
            description=description,
            label=label,
            status='Pending',
            is_done=False,
            created_on=timezone.now()
        )
        return redirect('dashboard')

    tasks = Task.objects.filter(user=request.user, parent_task__isnull=True)
    return render(request, 'tasks/dashboard.html', {'tasks': tasks})

@require_POST
@login_required
def task_action(request, task_id):
    task = get_object_or_404(Task, id=task_id, user=request.user)
    action = request.POST.get('action')

    if action == 'done':
        task.is_done = True
        task.status = 'Done'
        task.completed_on = timezone.now()
        task.save()

    elif action == 'cancel':
        task.is_done = False
        task.status = 'Cancelled'
        task.completed_on = None
        task.save()

    elif action == 'delete':
        task.delete()

    return redirect('dashboard')