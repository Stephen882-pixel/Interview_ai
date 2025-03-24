from rest_framework import viewsets,status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
import openai
from openai import OpenAI
from django.core.mail import send_mail
from django.conf import settings
from .serializers import InterviewSerializer,UserSerializer,ProgrammingSkillSerializer
from .models import Interview, ProgrammingSkill, Question, Response as ResponseModel
from rest_framework import generics
from rest_framework.views import APIView
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken

import google.generativeai as genai
# Set up the Gemini API key
genai.configure(api_key=settings.GOOGLE_GEMINI_API_KEY)

# Initialize the model
model = genai.GenerativeModel("gemini-2.0-flash")





import logging
logger = logging.getLogger(__name__)

# Create your views here.


class UserRegistrationView(generics.CreateAPIView):
    serializer_class = UserSerializer


class LoginView(APIView):
    def post(self,request):
        username = request.data.get('username')
        password = request.data.get('password') 

        if not username or not password:
            return Response({
                'error':'Please provide both username and password'
            },status=status.HTTP_400_BAD_REQUEST)
        
        user = authenticate(username=username,password=password)

        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                'access':str(refresh.access_token),
                'refresh':str(refresh),
                'username':user.username,
                'email':user.email,
                'is_recruiter':user.is_recruiter
            })
        else:
            return Response({
                'error':'Invalid credentials'
            },status=status.HTTP_401_UNAUTHORIZED)
            
class ProgrammingSkillViewSet(viewsets.ModelViewSet):
    serializer_class = ProgrammingSkillSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ProgrammingSkill.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user = self.request.user)

# Test openAI key function
def test_gemini_connection():
    try:
        # Configure Gemini API key
        client = genai.GenerativeModel(model="gemini-2.0-flash", api_key=settings.GEMINI_API_KEY)

        # Make a simple API call to test connection
        response = client.generate_content(contents="hello")

        return True, "Gemini API connection successful"
    except Exception as e:
        logger.error(f"Gemini API connection test failed: {e}")
        return False, str(e)


class InterviewViewSet(viewsets.ModelViewSet):
    serializer_class = InterviewSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_recruiter:
            return Interview.objects.all()
        return Interview.objects.filter(candidate=self.request.user)  # Unchanged, still uses 'candidate'

    def _generate_technical_questions(self, skill):
        prompts = {
            'beginner': f"Generate 3 basic technical interview questions for a beginner {skill.language} developer.",
            'intermediate': f"Generate 3 intermediate technical interview questions for a {skill.language} developer.",
            'advanced': f"Generate 3 advanced technical interview questions for an expert {skill.language} developer."
        }
        level = 'beginner' if skill.proficiency <= 4 else 'intermediate' if skill.proficiency <= 7 else 'advanced'
        try:
            response = model.generate_content(
                prompts[level],
                generation_config={"temperature": 0.7, "max_output_tokens": 500}
            )
            questions = response.candidates[0].content.parts[0].text.split("\n")
            return [q.strip() for q in questions if q.strip()]
        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            return None

    @action(detail=True, methods=['post'], url_path='generate-questions')
    def generate_questions(self, request, pk=None):
        logger.info(f'Starting question generation for interview {pk}')
        try:
            # Manually check if the interview exists
            interview = Interview.objects.filter(pk=pk).first()
            if not interview:
                return Response({"error": "Interview not found"}, status=status.HTTP_404_NOT_FOUND)

            skills = ProgrammingSkill.objects.filter(user=interview.candidate)
            logger.info(f"Found skills for candidate {interview.candidate}: {list(skills)}")
            if not skills.exists():
                return Response({"error": "No programming skills found"}, status=status.HTTP_400_BAD_REQUEST)

            generated_questions = []
            questions_count = 0

            for skill in skills:
                questions = self._generate_technical_questions(skill)
                if not questions:
                    return Response({"error": f"Failed to generate questions for {skill.language}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                skill_questions = []
                for question in questions:
                    if len(question) > 10:
                        question_obj = Question.objects.create(
                            interview=interview,
                            type='technical',
                            content=question,
                            skill=skill
                        )
                        questions_count += 1
                        skill_questions.append({
                            "id": question_obj.id,
                            "content": question,
                            "type": "technical"
                        })
                if skill_questions:
                    generated_questions.append({
                        "language": skill.language,
                        "proficiency": skill.proficiency,
                        "questions": skill_questions
                    })

            if questions_count == 0:
                return Response({"error": "No valid questions generated"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            interview.status = 'in_progress'
            interview.save()

            return Response({
                "status": "Questions generated successfully",
                "total_questions": questions_count,
                "questions_by_skill": generated_questions
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Critical error: {str(e)}")
            return Response({"error": "Failed to generate questions", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='submit-response')
    def submit_response(self, request, pk=None):
        interview = self.get_object()
        question_id = request.data.get('question_id')
        response_content = request.data.get('content')

        if not question_id or not response_content:
            return Response({"error": "Missing question_id or content"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            question = Question.objects.get(id=question_id, interview=interview)
            prompt = f"""
            Question: {question.content}
            Answer: {response_content}
            Evaluate this answer and provide:
            1. Score (0-100)
            2. Detailed feedback
            """
            gpt_response = model.generate_content(prompt)
            evaluation = gpt_response.candidates[0].content.parts[0].text

            score = 75  # Placeholder
            feedback = evaluation

            response_obj = Response.objects.create(
                question=question,
                content=response_content,
                score=score,
                feedback=feedback
            )

            return Response(ResponseSerializer(response_obj).data, status=status.HTTP_201_CREATED)

        except Question.DoesNotExist:
            return Response({"error": "Question not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Failed to evaluate response: {str(e)}")
            return Response({"error": "Failed to evaluate response", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='complete-interview')
    def complete_interview(self, request, pk=None):
        interview = self.get_object()
        responses = Response.objects.filter(question__interview=interview)

        if not responses.exists():
            return Response({"error": "No responses found"}, status=status.HTTP_400_BAD_REQUEST)

        total_score = responses.aggregate(Avg('score'))['score__avg']
        interview.total_score = total_score
        interview.status = 'completed'
        interview.save()

        send_mail(
            'Interview Results',
            f'Your interview has been completed. Total Score: {total_score}',
            settings.DEFAULT_FROM_EMAIL,
            [interview.candidate.email],  # Uses 'candidate'
            fail_silently=True
        )

        return Response({"status": "Interview completed", "total_score": total_score}, status=status.HTTP_200_OK)