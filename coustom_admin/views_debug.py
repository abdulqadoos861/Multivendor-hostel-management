from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import logging

logger = logging.getLogger(__name__)

@csrf_exempt
def debug_endpoint(request):
    """
    A debug endpoint to test server connectivity and request data.
    """
    try:
        # Log request method and headers
        logger.info(f"Debug endpoint called. Method: {request.method}")
        logger.info(f"Headers: {dict(request.headers)}")
        
        # Log request body if present
        body = {}
        if request.body:
            try:
                body = json.loads(request.body)
                logger.info(f"Request body: {body}")
            except json.JSONDecodeError:
                logger.warning("Could not parse request body as JSON")
                body = request.body.decode('utf-8', errors='replace')
                logger.info(f"Raw request body: {body}")
        
        # Log POST data
        logger.info(f"POST data: {dict(request.POST)}")
        
        # Return success response with request info
        return JsonResponse({
            'status': 'success',
            'method': request.method,
            'content_type': request.content_type,
            'body': body,
            'post_data': dict(request.POST),
            'headers': dict(request.headers)
        })
        
    except Exception as e:
        logger.exception("Error in debug endpoint:")
        return JsonResponse({
            'status': 'error',
            'error': str(e),
            'error_type': type(e).__name__
        }, status=500)
