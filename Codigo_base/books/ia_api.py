
import os
import openai
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
from dotenv import load_dotenv
load_dotenv()
# Configura tu clave de API de OpenAI aquí o usa variables de entorno
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
openai.api_key = OPENAI_API_KEY

@csrf_exempt
@require_POST
def ia_book_synopsis(request):
    try:
        data = json.loads(request.body)
        book_title = data.get('book_title', '').strip()
        if not book_title:
            return JsonResponse({'error': 'No se proporcionó el título del libro.'}, status=400)
        # Prompt para la IA
        prompt = f"Dame una sinopsis breve y una recomendación para el libro titulado '{book_title}'. Responde en español."
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.7
        )
        text = response.choices[0].message['content'].strip()
        return JsonResponse({'result': text})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
