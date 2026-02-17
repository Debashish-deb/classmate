import os
import json
import logging
from typing import Dict, Any, Optional, Tuple
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import base64
import secrets
from datetime import datetime

logger = logging.getLogger(__name__)

class EncryptionService:
    """End-to-end encryption service for ClassMate"""
    
    def __init__(self):
        self.master_key = os.getenv("ENCRYPTION_MASTER_KEY", self._generate_master_key())
        self.fernet = Fernet(self.master_key.encode())
    
    def _generate_master_key(self) -> str:
        """Generate a new master key"""
        return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
    
    def generate_user_keys(self) -> Dict[str, str]:
        """Generate public/private key pair for a user"""
        try:
            # Generate RSA key pair
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            
            public_key = private_key.public_key()
            
            # Serialize keys
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            return {
                "private_key": base64.b64encode(private_pem).decode(),
                "public_key": base64.b64encode(public_pem).decode()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate user keys: {e}")
            raise
    
    def encrypt_audio_data(self, audio_data: bytes, user_public_key: str) -> Dict[str, str]:
        """Encrypt audio data using hybrid encryption"""
        try:
            # Decode public key
            public_key_bytes = base64.b64decode(user_public_key)
            public_key = serialization.load_pem_public_key(
                public_key_bytes,
                backend=default_backend()
            )
            
            # Generate random AES key for audio data
            aes_key = secrets.token_bytes(32)
            iv = secrets.token_bytes(16)
            
            # Encrypt audio data with AES
            cipher = Cipher(
                algorithms.AES(aes_key),
                modes.CBC(iv),
                backend=default_backend()
            )
            encryptor = cipher.encryptor()
            
            # Pad audio data to block size
            padded_data = self._pad_data(audio_data)
            encrypted_audio = encryptor.update(padded_data) + encryptor.finalize()
            
            # Encrypt AES key with RSA public key
            encrypted_aes_key = public_key.encrypt(
                aes_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            return {
                "encrypted_audio": base64.b64encode(encrypted_audio).decode(),
                "encrypted_key": base64.b64encode(encrypted_aes_key).decode(),
                "iv": base64.b64encode(iv).decode(),
                "algorithm": "AES-256-CBC",
                "key_algorithm": "RSA-OAEP"
            }
            
        except Exception as e:
            logger.error(f"Failed to encrypt audio data: {e}")
            raise
    
    def decrypt_audio_data(self, encrypted_data: Dict[str, str], user_private_key: str) -> bytes:
        """Decrypt audio data using hybrid decryption"""
        try:
            # Decode private key
            private_key_bytes = base64.b64decode(user_private_key)
            private_key = serialization.load_pem_private_key(
                private_key_bytes,
                password=None,
                backend=default_backend()
            )
            
            # Decrypt AES key with RSA private key
            encrypted_aes_key = base64.b64decode(encrypted_data["encrypted_key"])
            aes_key = private_key.decrypt(
                encrypted_aes_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            # Decrypt audio data with AES
            iv = base64.b64decode(encrypted_data["iv"])
            encrypted_audio = base64.b64decode(encrypted_data["encrypted_audio"])
            
            cipher = Cipher(
                algorithms.AES(aes_key),
                modes.CBC(iv),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()
            padded_data = decryptor.update(encrypted_audio) + decryptor.finalize()
            
            # Remove padding
            audio_data = self._unpad_data(padded_data)
            
            return audio_data
            
        except Exception as e:
            logger.error(f"Failed to decrypt audio data: {e}")
            raise
    
    def encrypt_transcript(self, transcript: str, user_public_key: str) -> Dict[str, str]:
        """Encrypt transcript text"""
        try:
            # Decode public key
            public_key_bytes = base64.b64decode(user_public_key)
            public_key = serialization.load_pem_public_key(
                public_key_bytes,
                backend=default_backend()
            )
            
            # Encrypt transcript with RSA public key
            encrypted_transcript = public_key.encrypt(
                transcript.encode('utf-8'),
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            return {
                "encrypted_transcript": base64.b64encode(encrypted_transcript).decode(),
                "algorithm": "RSA-OAEP"
            }
            
        except Exception as e:
            logger.error(f"Failed to encrypt transcript: {e}")
            raise
    
    def decrypt_transcript(self, encrypted_data: Dict[str, str], user_private_key: str) -> str:
        """Decrypt transcript text"""
        try:
            # Decode private key
            private_key_bytes = base64.b64decode(user_private_key)
            private_key = serialization.load_pem_private_key(
                private_key_bytes,
                password=None,
                backend=default_backend()
            )
            
            # Decrypt transcript with RSA private key
            encrypted_transcript = base64.b64decode(encrypted_data["encrypted_transcript"])
            transcript_bytes = private_key.decrypt(
                encrypted_transcript,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            return transcript_bytes.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Failed to decrypt transcript: {e}")
            raise
    
    def encrypt_sensitive_data(self, data: Dict[str, Any]) -> str:
        """Encrypt sensitive data using server-side encryption"""
        try:
            json_data = json.dumps(data, default=str)
            encrypted_data = self.fernet.encrypt(json_data.encode())
            return base64.b64encode(encrypted_data).decode()
            
        except Exception as e:
            logger.error(f"Failed to encrypt sensitive data: {e}")
            raise
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> Dict[str, Any]:
        """Decrypt sensitive data using server-side encryption"""
        try:
            encrypted_bytes = base64.b64decode(encrypted_data)
            decrypted_bytes = self.fernet.decrypt(encrypted_bytes)
            return json.loads(decrypted_bytes.decode())
            
        except Exception as e:
            logger.error(f"Failed to decrypt sensitive data: {e}")
            raise
    
    def _pad_data(self, data: bytes) -> bytes:
        """Apply PKCS7 padding"""
        block_size = 16
        padding_length = block_size - (len(data) % block_size)
        padding = bytes([padding_length] * padding_length)
        return data + padding
    
    def _unpad_data(self, padded_data: bytes) -> bytes:
        """Remove PKCS7 padding"""
        padding_length = padded_data[-1]
        return padded_data[:-padding_length]
    
    def generate_session_key(self) -> str:
        """Generate a unique session key for temporary encryption"""
        return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
    
    def create_secure_share_link(self, session_id: str, user_id: str, expires_hours: int = 24) -> Dict[str, str]:
        """Create a secure share link for a session"""
        try:
            # Generate share token
            share_data = {
                "session_id": session_id,
                "user_id": user_id,
                "expires_at": (datetime.utcnow() + timedelta(hours=expires_hours)).isoformat(),
                "created_at": datetime.utcnow().isoformat()
            }
            
            # Encrypt share data
            share_token = self.encrypt_sensitive_data(share_data)
            
            # Generate share ID
            share_id = secrets.token_urlsafe(16)
            
            return {
                "share_id": share_id,
                "share_token": share_token,
                "expires_at": share_data["expires_at"]
            }
            
        except Exception as e:
            logger.error(f"Failed to create secure share link: {e}")
            raise
    
    def validate_share_link(self, share_token: str) -> Optional[Dict[str, Any]]:
        """Validate and decrypt a share link"""
        try:
            share_data = self.decrypt_sensitive_data(share_token)
            
            # Check if expired
            expires_at = datetime.fromisoformat(share_data["expires_at"])
            if datetime.utcnow() > expires_at:
                return None
            
            return share_data
            
        except Exception as e:
            logger.error(f"Failed to validate share link: {e}")
            return None
    
    def hash_password(self, password: str, salt: str = None) -> Tuple[str, str]:
        """Hash password with PBKDF2"""
        try:
            if salt is None:
                salt = secrets.token_hex(16)
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt.encode(),
                iterations=100000,
                backend=default_backend()
            )
            
            hashed_password = kdf.derive(password.encode())
            return base64.b64encode(hashed_password).decode(), salt
            
        except Exception as e:
            logger.error(f"Failed to hash password: {e}")
            raise
    
    def verify_password(self, password: str, hashed_password: str, salt: str) -> bool:
        """Verify password against hash"""
        try:
            new_hash, _ = self.hash_password(password, salt)
            return new_hash == hashed_password
            
        except Exception as e:
            logger.error(f"Failed to verify password: {e}")
            return False

# Global encryption service instance
encryption_service = EncryptionService()
