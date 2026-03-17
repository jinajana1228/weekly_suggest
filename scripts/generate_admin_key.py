"""Admin API 키 생성 헬퍼.

배포 전 ADMIN_API_KEY 값을 생성한다.
생성된 값을 Railway 환경변수에 그대로 붙여넣으면 된다.

사용법:
    python scripts/generate_admin_key.py
"""
import secrets

key = secrets.token_hex(32)
print("=" * 64)
print("ADMIN_API_KEY:")
print()
print(key)
print()
print("=" * 64)
print("Copy this value to Railway Variables > ADMIN_API_KEY")
print("You will enter this key in the admin UI login form.")
