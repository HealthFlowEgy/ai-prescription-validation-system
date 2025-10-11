"""
JWT Token Manager with blacklisting and enhanced security
File: src/utils/token_manager.py
"""

import os
import jwt
import uuid
import redis
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
from flask import request
import logging

logger = logging.getLogger(__name__)


class TokenManager:
    """
    Enhanced JWT token management with:
    - Token blacklisting
    - Refresh token rotation
    - Device/IP binding
    - Token revocation
    """
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """
        Initialize token manager
        
        Args:
            redis_client: Redis client for token storage (optional)
        """
        self.redis_client = redis_client
        self.secret_key = os.environ.get('JWT_SECRET_KEY')
        if not self.secret_key:
            raise ValueError("JWT_SECRET_KEY environment variable must be set")
    
    def generate_access_token(
        self,
        user_id: int,
        role: str,
        expires_in: int = None
    ) -> Tuple[str, datetime]:
        """
        Generate JWT access token
        
        Args:
            user_id: User ID
            role: User role
            expires_in: Token expiration in seconds (default: 1 hour)
            
        Returns:
            Tuple of (token, expiration_datetime)
        """
        if expires_in is None:
            expires_in = int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRES', 3600))
        
        expiration = datetime.utcnow() + timedelta(seconds=expires_in)
        jti = str(uuid.uuid4())  # Unique token ID for blacklisting
        
        payload = {
            'user_id': user_id,
            'role': role,
            'exp': expiration,
            'iat': datetime.utcnow(),
            'jti': jti,
            'type': 'access'
        }
        
        token = jwt.encode(
            payload,
            self.secret_key,
            algorithm='HS256'
        )
        
        # Store token metadata in Redis (if available)
        if self.redis_client:
            try:
                self.redis_client.setex(
                    f"access_token:{jti}",
                    expires_in,
                    json.dumps({
                        'user_id': user_id,
                        'role': role,
                        'issued_at': datetime.utcnow().isoformat()
                    })
                )
            except Exception as e:
                logger.warning(f"Failed to store token metadata in Redis: {e}")
        
        return token, expiration
    
    def generate_refresh_token(
        self,
        user_id: int,
        role: str = 'user',
        device_id: str = None,
        ip_address: str = None,
        expires_in: int = None
    ) -> Tuple[str, datetime]:
        """
        Generate JWT refresh token with enhanced security
        
        Args:
            user_id: User ID
            role: User role
            device_id: Device identifier for binding
            ip_address: IP address for binding
            expires_in: Token expiration in seconds (default: 7 days)
            
        Returns:
            Tuple of (token, expiration_datetime)
        """
        if expires_in is None:
            expires_in = int(os.environ.get('JWT_REFRESH_TOKEN_EXPIRES', 604800))  # 7 days
        
        expiration = datetime.utcnow() + timedelta(seconds=expires_in)
        jti = str(uuid.uuid4())
        
        # Get device and IP from request if not provided
        if device_id is None and request:
            device_id = request.headers.get('X-Device-ID', 'unknown')
        if ip_address is None and request:
            ip_address = request.remote_addr
        
        payload = {
            'user_id': user_id,
            'role': role,
            'exp': expiration,
            'iat': datetime.utcnow(),
            'jti': jti,
            'type': 'refresh',
            'device_id': device_id,
            'ip': ip_address
        }
        
        token = jwt.encode(
            payload,
            self.secret_key,
            algorithm='HS256'
        )
        
        # Store refresh token metadata in Redis (if available)
        if self.redis_client:
            try:
                self.redis_client.setex(
                    f"refresh_token:{jti}",
                    expires_in,
                    json.dumps({
                        'user_id': user_id,
                        'role': role,
                        'device_id': device_id,
                        'ip': ip_address,
                        'issued_at': datetime.utcnow().isoformat()
                    })
                )
            except Exception as e:
                logger.warning(f"Failed to store refresh token metadata in Redis: {e}")
        
        return token, expiration
    
    def decode_token(self, token: str, verify_blacklist: bool = True) -> Optional[Dict]:
        """
        Decode and validate JWT token
        
        Args:
            token: JWT token string
            verify_blacklist: Whether to check if token is blacklisted
            
        Returns:
            Decoded token payload or None if invalid
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=['HS256']
            )
            
            # Check if token is blacklisted
            if verify_blacklist and self.is_token_blacklisted(payload.get('jti')):
                logger.warning(f"Attempted use of blacklisted token: {payload.get('jti')}")
                return None
            
            # Verify device/IP binding for refresh tokens
            if payload.get('type') == 'refresh':
                if not self._verify_token_binding(payload):
                    logger.warning(f"Token binding verification failed for token: {payload.get('jti')}")
                    return None
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.info("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
        except Exception as e:
            logger.error(f"Error decoding token: {e}")
            return None
    
    def revoke_token(self, jti: str, token_type: str = 'access') -> bool:
        """
        Blacklist a token
        
        Args:
            jti: Token unique identifier
            token_type: Type of token ('access' or 'refresh')
            
        Returns:
            True if successfully blacklisted
        """
        if not self.redis_client:
            logger.warning("Redis not available, cannot blacklist token")
            return False
        
        try:
            # Determine TTL based on token type
            ttl = 3600 if token_type == 'access' else 604800
            
            self.redis_client.setex(
                f"blacklist:{jti}",
                ttl,
                json.dumps({
                    'revoked_at': datetime.utcnow().isoformat(),
                    'type': token_type
                })
            )
            
            logger.info(f"Token {jti} blacklisted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to blacklist token {jti}: {e}")
            return False
    
    def is_token_blacklisted(self, jti: str) -> bool:
        """
        Check if token is blacklisted
        
        Args:
            jti: Token unique identifier
            
        Returns:
            True if token is blacklisted
        """
        if not self.redis_client or not jti:
            return False
        
        try:
            return self.redis_client.exists(f"blacklist:{jti}") > 0
        except Exception as e:
            logger.error(f"Error checking blacklist for token {jti}: {e}")
            return False
    
    def revoke_all_user_tokens(self, user_id: int) -> int:
        """
        Revoke all tokens for a specific user
        
        Args:
            user_id: User ID
            
        Returns:
            Number of tokens revoked
        """
        if not self.redis_client:
            logger.warning("Redis not available, cannot revoke user tokens")
            return 0
        
        try:
            revoked_count = 0
            
            # Find all access tokens for user
            for key in self.redis_client.scan_iter(f"access_token:*"):
                token_data = self.redis_client.get(key)
                if token_data:
                    data = json.loads(token_data)
                    if data.get('user_id') == user_id:
                        jti = key.decode('utf-8').split(':')[1]
                        if self.revoke_token(jti, 'access'):
                            revoked_count += 1
            
            # Find all refresh tokens for user
            for key in self.redis_client.scan_iter(f"refresh_token:*"):
                token_data = self.redis_client.get(key)
                if token_data:
                    data = json.loads(token_data)
                    if data.get('user_id') == user_id:
                        jti = key.decode('utf-8').split(':')[1]
                        if self.revoke_token(jti, 'refresh'):
                            revoked_count += 1
            
            logger.info(f"Revoked {revoked_count} tokens for user {user_id}")
            return revoked_count
            
        except Exception as e:
            logger.error(f"Error revoking tokens for user {user_id}: {e}")
            return 0
    
    def refresh_access_token(self, refresh_token: str) -> Optional[Tuple[str, str, datetime]]:
        """
        Generate new access token from refresh token with rotation
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            Tuple of (new_access_token, new_refresh_token, expiration) or None
        """
        # Decode refresh token
        payload = self.decode_token(refresh_token, verify_blacklist=True)
        
        if not payload or payload.get('type') != 'refresh':
            return None
        
        user_id = payload.get('user_id')
        role = payload.get('role')
        device_id = payload.get('device_id')
        ip_address = payload.get('ip')
        
        # Generate new access token
        access_token, access_exp = self.generate_access_token(user_id, role)
        
        # Rotate refresh token (revoke old, generate new)
        old_jti = payload.get('jti')
        if old_jti:
            self.revoke_token(old_jti, 'refresh')
        
        new_refresh_token, refresh_exp = self.generate_refresh_token(
            user_id, role, device_id, ip_address
        )
        
        return access_token, new_refresh_token, access_exp
    
    def _verify_token_binding(self, payload: Dict) -> bool:
        """
        Verify token device/IP binding
        
        Args:
            payload: Decoded token payload
            
        Returns:
            True if binding is valid
        """
        if not request:
            return True  # Skip verification if no request context
        
        # Verify device ID
        token_device = payload.get('device_id')
        request_device = request.headers.get('X-Device-ID')
        
        if token_device and request_device and token_device != request_device:
            logger.warning(f"Device ID mismatch: token={token_device}, request={request_device}")
            return False
        
        # Verify IP address (optional, can be disabled for mobile apps)
        verify_ip = os.environ.get('JWT_VERIFY_IP', 'false').lower() == 'true'
        if verify_ip:
            token_ip = payload.get('ip')
            request_ip = request.remote_addr
            
            if token_ip and request_ip and token_ip != request_ip:
                logger.warning(f"IP address mismatch: token={token_ip}, request={request_ip}")
                return False
        
        return True


# Initialize global token manager
def get_token_manager() -> TokenManager:
    """
    Get or create token manager instance
    
    Returns:
        TokenManager instance
    """
    # Try to connect to Redis
    redis_client = None
    redis_url = os.environ.get('REDIS_URL')
    
    if redis_url:
        try:
            redis_client = redis.from_url(redis_url, decode_responses=False)
            redis_client.ping()  # Test connection
            logger.info("Redis connected for token management")
        except Exception as e:
            logger.warning(f"Redis not available: {e}. Token blacklisting disabled.")
            redis_client = None
    else:
        logger.warning("REDIS_URL not configured. Token blacklisting disabled.")
    
    return TokenManager(redis_client)
