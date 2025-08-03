from django.utils import translation
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

class LanguageMiddleware(MiddlewareMixin):
    def process_request(self, request):
        language = request.session.get(translation.LANGUAGE_SESSION_KEY)
        if not language:
            language = settings.LANGUAGE_CODE
        translation.activate(language)
        request.LANGUAGE_CODE = language

    def process_response(self, request, response):
        language = translation.get_language()
        if hasattr(request, 'session'):
            request.session[translation.LANGUAGE_SESSION_KEY] = language
        return response
