from django.utils import translation
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

class LanguageMiddleware(MiddlewareMixin):
    def process_request(self, request):
        language = request.COOKIES.get('django_language')
        if not language:
            language = settings.LANGUAGE_CODE
        translation.activate(language)
        request.LANGUAGE_CODE = language

    def process_response(self, request, response):
        language = translation.get_language()
        response.set_cookie(
            settings.LANGUAGE_COOKIE_NAME,
            language,
            max_age=settings.LANGUAGE_COOKIE_AGE,
            path=settings.LANGUAGE_COOKIE_PATH,
        )
        return response
