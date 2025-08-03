import logging
from django.utils import translation

logger = logging.getLogger(__name__)

class LanguageDebugMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Log language information before processing
        logger.info(f"Current language code: {translation.get_language()}")
        logger.info(f"Language from session: {request.session.get('django_language')}")
        logger.info(f"Language from cookie: {request.COOKIES.get('django_language')}")
        
        response = self.get_response(request)
        
        # Log language information after processing
        logger.info(f"Response language: {translation.get_language()}")
        return response
