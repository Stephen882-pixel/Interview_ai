from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator,MaxValueValidator

# Create your models here.
class User(AbstractUser):
    is_recruiter = models.BooleanField(default=False)
    email = models.EmailField(unique=True)

    groups = models.ManyToManyField(
        "auth.Group",
        related_name="custom_user_groups",  # Unique related_name
        blank=True
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission",
        related_name="custom_user_permissions",  # Unique related_name
        blank=True
    )

class ProgrammingSkill(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='skills')
    language = models.CharField(max_length=50)
    proficiency = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )

    class Meta:
        unique_together = ['user', 'language']

class Interview(models.Model):
    interview_id = models.AutoField(primary_key=True, unique=True)
    recruiter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='interviews')  # Renamed from 'interview'
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed')
        ],
        default='pending'
    )
    candidate = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, related_name='candidate')
    total_score = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"Interview {self.interview_id} for {self.candidate}"

class Question(models.Model):
    interview = models.ForeignKey(Interview, on_delete=models.CASCADE, related_name='questions')
    type = models.CharField(
        max_length=20,
        choices=[
            ('technical', 'Technical'),
            ('behavioural', 'Behavioural')
        ]
    )
    content = models.TextField()
    skill = models.ForeignKey(ProgrammingSkill, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return self.content[:50]

class Response(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='responses')
    content = models.TextField()
    score = models.FloatField(null=True, blank=True)
    feedback = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Response to {self.question}"

    
                             

