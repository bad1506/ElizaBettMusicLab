"""Static security contract checks that require no third-party test framework."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
security = (ROOT / "security.py").read_text(encoding="utf-8")
api = (ROOT / "api_secure.py").read_text(encoding="utf-8")
auth = (ROOT / "telegram_auth.py").read_text(encoding="utf-8")
project_manager = (ROOT / "project_manager.py").read_text(encoding="utf-8")

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

# API3 / mass-assignment contract: request models must not expose identity,
# privilege, or filesystem ownership fields to the client.
module = ast.parse(api)
request_classes = {
    node.name
    for node in module.body
    if isinstance(node, ast.ClassDef)
    and any(
        isinstance(base, ast.Name) and base.id == "BaseModel"
        for base in node.bases
    )
}
for node in module.body:
    if not isinstance(node, ast.ClassDef) or node.name not in request_classes:
        continue
    fields = {
        target.id
        for stmt in node.body
        if isinstance(stmt, ast.AnnAssign)
        and isinstance(stmt.target, ast.Name)
        for target in [stmt.target]
    }
    forbidden = {"user_id", "owner_id", "role", "is_admin", "storage_path"}
    assert not fields.intersection(forbidden), f"{node.name}: privileged client field exposed"

# Export filenames are generated server-side from a sanitized project name.
assert 'c if c.isalnum() or c in "-_" else "_"' in project_manager
assert 'output_dir / f"{safe}_FINAL_PROJECT_' in project_manager

print("security contract: PASS")
