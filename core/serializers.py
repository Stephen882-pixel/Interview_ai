from rest_framework import serializers
from .models import User,ProgrammingSkill,Question,Response,Interview


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id','username','email','is_recruiter','password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self,validated_data):
        user = User.objects.create_user(**validated_data)
        return user


class ProgrammingSkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProgrammingSkill
        fields = ['id','language','proficiency']

    def create(self,validated_data):
        skill = ProgrammingSkill.objects.create(**validated_data)
        return skill

class QuestionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ('id', 'type', 'content', 'skill')


class ResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Response
        fields = ('id', 'content', 'score', 'feedback', 'created_at')

class InterviewSerializer(serializers.ModelSerializer):
    questions = QuestionsSerializer(many=True,read_only=True)

    class Meta:
        model = Interview
        fields = '__all__'
        #fields = ('id', 'candidate', 'status', 'total_score', 'created_at', 'questions')
