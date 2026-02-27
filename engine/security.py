import jwt
import datetime
from functools import wraps
from flask import request, jsonify, session
import os

# Use an environment variable or a strong static key for dev
SECRET_KEY = os.environ.get('JWT_SECRET', 'sentinel_super_secret_jwt_key_2026')
ALGORITHM = "HS256"

# Define permission matrices for the RBAC system
# These map roles to specific API actions
ROLE_PERMISSIONS = {
    'super_admin': ['manage_users', 'view_dashboard', 'manage_logic', 'manage_watchlist', 'view_audit', 'approve_workflow'],
    'maker': ['view_dashboard', 'create_watchlist', 'submit_workflow'],
    'checker': ['view_dashboard', 'verify_workflow'],
    'validator': ['view_dashboard', 'validate_logic'],
    'auditor': ['view_dashboard', 'view_audit', 'view_users'],
    'reviewer': ['view_dashboard', 'review_workflow']
}

def generate_token(username, roles):
    """
    Generates a JWT token for the session string to authenticate API calls.
    """
    payload = {
        'sub': username,
        'roles': roles,
        'iat': datetime.datetime.utcnow(),
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token):
    """
    Decodes the JWT token and returns the payload if valid.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def role_required(*allowed_roles):
    """
    Decorator to protect API routes based on user role.
    Checks either the JWT Bearer token or the active Flask session.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            roles = []
            
            # 1. Try to get roles from Auth Header (JWT)
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(" ")[1]
                payload = decode_token(token)
                if payload:
                    roles = payload.get('roles', [])
            
            # 2. Fallback to Flask session (useful if API called from Jinja template via JS safely)
            if not roles and 'roles' in session:
                roles = session.get('roles', [])

            if not roles:
                return jsonify({'error': 'Unauthorized', 'message': 'Missing or invalid token/session.'}), 401
            
            # Check intersection of user roles and allowed roles
            # 'super_admin' explicitly bypasses if needed, or explicitly included in allowed_roles
            has_role = any(role in allowed_roles or role == 'super_admin' for role in roles)
            
            if not has_role:
                return jsonify({'error': 'Forbidden', 'message': 'You do not have the required role.'}), 403
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def permission_required(permission):
    """
    Decorator to protect routes based on granular permissions mapped to roles.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            roles = session.get('roles', [])
            
            # Optional: Allow JWT Bearer fallback for pure API clients
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(" ")[1]
                payload = decode_token(token)
                if payload:
                    roles = payload.get('roles', [])

            if not roles:
                return jsonify({'error': 'Unauthorized'}), 401
            
            # Flatten permissions for the user's active roles
            user_permissions = set()
            for r in roles:
                if r in ROLE_PERMISSIONS:
                    user_permissions.update(ROLE_PERMISSIONS[r])
            
            if permission not in user_permissions and 'super_admin' not in roles:
                return jsonify({'error': 'Forbidden', 'message': f'Requires {permission} permission.'}), 403
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator
