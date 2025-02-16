from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator,MaxValueValidator

# Create your models here.
class User(AbstractUser):
    is_recruiter = models.BooleanField(default=False)
    email = models.EmailField(unique=True)

class ProgrammingSkill(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE,related_name='skills')
    language = models.CharField(max_length=50)
    proficiency = models.IntegerField(
        validators=[MinValueValidator(1),MaxValueValidator(10)]
    )

    class Meta:
        unique_together = ['user','language']

# class Interview(models.Model):
#     interview = models.ForeignKey(User,on_delete=models.CASCADE,related_name='interviews')
    
                             

