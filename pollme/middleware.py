from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

class SplitSessionMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.path.startswith('/admin/'):
            request.session_cookie_name = 'admin_sessionid'
            request.COOKIES['sessionid'] = request.COOKIES.get('admin_sessionid', '')
        else:
            request.session_cookie_name = settings.SESSION_COOKIE_NAME

    def process_response(self, request, response):
        if hasattr(request, 'session_cookie_name') and request.session_cookie_name == 'admin_sessionid':
            if 'sessionid' in response.cookies:
                response.cookies['admin_sessionid'] = response.cookies['sessionid']
                del response.cookies['sessionid']
        return response 