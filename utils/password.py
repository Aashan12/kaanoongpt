"""
Password hashing utilities using bcrypt directly (not passlib)
This avoids passlib's bcrypt compatibility issues
"""
import bcrypt
import hashlib

def hash_password(password: str) -> str:
    """
    Hash a password using SHA256 + bcrypt
    
    Why SHA256 first?
    - Bcrypt has a 72-byte limit
    - SHA256 always produces exactly 64 characters
    - This allows ANY length password to be securely hashed
    """
    if not password:
        raise ValueError("Password cannot be empty")
    
    if not isinstance(password, str):
        raise ValueError(f"Password must be a string, got {type(password)}")
    
    # Log for debugging
    password_length = len(password)
    password_bytes = len(password.encode('utf-8'))
    
    print(f"🔐 Hashing password:")
    print(f"   - Length: {password_length} characters")
    print(f"   - Bytes: {password_bytes} bytes")
    print(f"   - First 20 chars: {password[:20]}")
    
    # Pre-hash with SHA256 to ensure consistent length
    sha256_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
    print(f"   - SHA256 hash: {len(sha256_hash)} chars (always 64)")
    
    try:
        # Hash the SHA256 output with bcrypt
        # bcrypt.hashpw requires bytes
        salt = bcrypt.gensalt(rounds=12)  # 12 rounds is a good balance
        bcrypt_hash = bcrypt.hashpw(sha256_hash.encode('utf-8'), salt)
        
        # Convert bytes to string for storage
        hash_string = bcrypt_hash.decode('utf-8')
        
        print(f"   ✅ Password hashed successfully")
        print(f"   - Final hash length: {len(hash_string)} chars")
        
        return hash_string
        
    except Exception as e:
        print(f"   ❌ Bcrypt hashing failed: {e}")
        raise ValueError(f"Password hashing failed: {str(e)}")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash
    Must use the same SHA256 pre-hashing as hash_password()
    """
    if not plain_password or not hashed_password:
        print("⚠️ Empty password or hash provided")
        return False
    
    try:
        # Pre-hash with SHA256 (same as when creating the hash)
        sha256_hash = hashlib.sha256(plain_password.encode('utf-8')).hexdigest()
        
        # bcrypt.checkpw requires bytes
        result = bcrypt.checkpw(
            sha256_hash.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
        
        print(f"🔐 Password verification: {'✅ Success' if result else '❌ Failed'}")
        return result
        
    except Exception as e:
        print(f"❌ Password verification error: {e}")
        return False