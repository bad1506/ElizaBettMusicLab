"""Static security contract checks that require no third-party test framework."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
security = (ROOT / "security.py").read_text(encoding="utf-8")
api = (ROOT / "api_secure.py").read_text(encoding="utf-8")
auth = (ROOT / "telegram_auth.py").read_text(encoding="utf-8")

assert 'os.getenv("ALLOW_LOCAL_UNAUTH", "false")' in security
assert 'allow_credentials=False' in api
assert 'X-Telegram-Init-Data' in api
assert 'security.security_middleware(app)' in api
assert 'resolve_user_file' in security
assert 'is_relative_to(root)' in security
assert 'uuid.uuid4().hex' in api
assert 'max_upload_bytes()' in api
assert 'docs_url="/docs" if ENABLE_DOCS else None' in api
assert 'if not user or not user.get("id")' in auth
assert 'hmac.compare_digest' in auth

# Production endpoints must not be accidentally added to the public allowlist.
for path in [
    "/upload", "/master", "/stems", "/chat", "/songwriter",
    "/songwriter/memory", "/production/run", "/project", "/files",
]:
    assert path not in security.split("_PUBLIC_PATHS =", 1)[1].split("\n", 1)[0], path

print("security contract: PASS")
