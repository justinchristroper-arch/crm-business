"""Allowlisted structured events; never log payloads, query strings, email, cookies or exception text."""
import json
import logging
import time
from uuid import uuid4
from fastapi.responses import JSONResponse

logger = logging.getLogger('crm.events')
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)
logger.propagate = False


def security_event(event, **fields):
    allowed = {key: value for key, value in fields.items() if key in ('actor_id', 'role', 'status', 'request_id')}
    logger.warning(json.dumps({'event': event, **allowed}, separators=(',', ':')))


def install_observability(app):
    @app.middleware('http')
    async def request_log(request, call_next):
        request_id = uuid4().hex
        request.state.request_id = request_id
        started = time.monotonic()
        try:
            response = await call_next(request)
        except Exception:
            security_event('request_failed', request_id=request_id, status=500)
            response = JSONResponse({'detail': 'Terjadi kesalahan server. Hubungi pengelola dengan ID permintaan.',
                                     'request_id': request_id}, status_code=500)
        response.headers['X-Request-ID'] = request_id
        # Route template excludes record IDs and attacker-controlled path/query strings.
        route = getattr(request.scope.get('route'), 'path', 'unmatched')
        logger.info(json.dumps({'event': 'http_request', 'request_id': request_id, 'route': route,
                               'method': request.method, 'status': response.status_code,
                               'duration_ms': round((time.monotonic() - started) * 1000)}, separators=(',', ':')))
        return response
