from rest_framework import viewsets,status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
import openai
from openai import OpenAI
from django.core.mail import send_mail
from django.conf import settings
from .serializers import InterviewSerializer,UserSerializer,ProgrammingSkillSerializer
from .models import Interview,ProgrammingSkill,Question
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
        return Interview.objects.filter(candidate=self.request.user)

    def generate_technical_questions(self, skill):
        """Generate technical questions based on skill level using Gemini"""
        prompts = {
            'beginner': f"Generate 3 basic technical interview questions for a beginner {skill.language} developer. Questions should test fundamental concepts.",
            'intermediate': f"Generate 3 intermediate technical interview questions for a {skill.language} developer. Include questions about best practices and common patterns.",
            'advanced': f"Generate 3 advanced technical interview questions for an expert {skill.language} developer. Include questions about optimization, architecture, and advanced concepts."
        }

        # Determine skill level
        if skill.proficiency <= 4:
            level = 'beginner'
        elif skill.proficiency <= 7:
            level = 'intermediate'
        else:
            level = 'advanced'

        try:
            # Call Gemini API
            response = model.generate_content(
                prompts[level],
                generation_config={"temperature":0.7,"max_output_tokens":500}
            )

            questions = response.candidates[0].content.parts[0].text.split("\n")
            return [q.strip() for q in questions if q.strip()]
        
        except Exception as e:
            logger.error(f"Gemini API error while generating questions: {str(e)}")
            return None

    @action(detail=True, methods=['post'])
    def generate_questions(self, request, pk=None):
        logger.info(f'Starting question generation for interview {pk}')
        try:
            # Get interview object
            interview = self.get_object()
            skills = ProgrammingSkill.objects.filter(user=interview.candidate)

            if not skills.exists():
                logger.warning(f"No skills found for candidate {interview.candidate.id}")
                return Response({"error": "No programming skills found for candidate"}, status=status.HTTP_400_BAD_REQUEST)
            
            generated_questions = []  # Store all generated questions
            questions_count = 0

            for skill in skills:
                logger.info(f'Generating questions for {skill.language} developer with proficiency level {skill.proficiency}/10')

                questions = self.generate_technical_questions(skill)
                if not questions:
                    return Response({"error": "Failed to generate questions"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                skill_questions = []  # Store questions for this skill
                for question in questions:
                    if len(question) > 10:
                        try:
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
                            logger.info(f'Created question: {question[:50]}...')
                        except Exception as e:
                            logger.error(f'Failed to save question: {str(e)}')
                # Add questions for this skill to the main list
                if skill_questions:
                    generated_questions.append({
                        "language": skill.language,
                        "proficiency": skill.proficiency,
                        "questions": skill_questions
                    })
            if questions_count == 0:
                return Response({"error": "No questions were generated"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Update interview status
            interview.status = 'in_progress'
            interview.save()


            return Response({
                "status": "Questions generated successfully",
                "total_questions": questions_count,
                "questions_by_skill": generated_questions
            })
        except Exception as e:
            logger.error(f"Critical error in generate_questions: {str(e)}")
            return Response({"error": "Critical error occurred", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    @action(detail=True, methods=['post'])
    def submit_response(self, request, pk=None):
        interview = self.get_object()
        question_id = request.data.get('question_id')
        response_content = request.data.get('content')

        try:
            question = Question.objects.get(id=question_id, interview=interview)

            # Use Gemini to evaluate the response
            prompt = f"""
            Question: {question.content}
            Answer: {response_content}
            Evaluate this answer and provide:
            1. Score (0-100)
            2. Detailed feedback
            """

            gpt_response = model.generate_content(prompt)


            evaluation = gpt_response.candidates[0].content.parts[0].text
            score = 75  # Placeholder score, you can extract actual score if Gemini provides structured feedback
            feedback = evaluation

            response = InterviewResponse.objects.create(
                question=question,
                content=response_content,
                score=score,
                feedback=feedback
            )

            return Response(ResponseSerializer(response).data)

        except Question.DoesNotExist:
            return Response({"error": "Question Not Found"}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            logger.error(f"Failed to evaluate the response: {str(e)}")
            return Response({"error": "Failed to evaluate the response", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    @action(detail=True,methods=['post'])
    def complete_interview(self,request,pk=None):
        interview = self.get_object()
        responses = Response.objects.filter(question__interview=interview)

        if responses.exists():
            # calculate total score
            total_score = responses.aggregate(Avg('score'))['score_avg']
            interviewe.total_score = total_score
            interview.status = 'completed'
            interview.save()

            # send email with results
            send_mail(
                'Interview Results',
                f'Your Interview has been completed.Total Score:{total_score}',
                settings.DEFAULT_FROM_EMAIL,
                [interview.candidate.email],
                fail_silently=True
            )

            return Response({"status": "Interview completed", "total_score": total_score})
        return Response(
            {"error": "No responses found"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
