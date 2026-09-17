from __future__ import annotations

import os
from fastapi import HTTPException, Request as FastAPIRequest, Response
from pydantic import BaseModel, Field

from api_secure import app
import billing_yookassa
import chat_api
import quota
import web_auth
import yandex_public
from agents.router import AgentError, invoke as invoke_agent, list_agents
from agents.tools import execute_tool, list_tools
from agents.tools.base import ToolError
import security

chat_api.register(app)
yandex_public.register_yandex_chart(app)
SESSION_COOKIE = "sona_session"


class AuthRequest(BaseModel):
    name: str = Field(default="", max_length=120)
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=256)

class ActivityRequest(BaseModel):
    kind: str = Field(default="activity", max_length=40)
    title: str = Field(min_length=1, max_length=160)
    detail: str = Field(default="", max_length=1000)

class AgentRequest(BaseModel):
    agent: str = Field(min_length=1, max_length=80)
    message: str = Field(min_length=1, max_length=12000)
    history: list[dict[str, str]] = Field(default_factory=list, max_length=30)
    context: dict = Field(default_factory=dict)

class ToolRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    arguments: dict = Field(default_factory=dict)

class PlanActivationRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=128)
    plan: str = Field(pattern=r"^(free|creator|pro|studio)$")
    status: str = Field(default="active", max_length=32)
    period_end: str | None = Field(default=None, max_length=64)

class CheckoutRequest(BaseModel):
    plan: str = Field(pattern=r"^(creator|pro|studio)$")
    return_url: str | None = Field(default=None, max_length=1000)

class BillingReconcileRequest(BaseModel):
    limit: int = Field(default=50, ge=1, le=100)


def _token(request: FastAPIRequest) -> str:
    header = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    return header or request.cookies.get(SESSION_COOKIE, "")


def _finish(response: Response, data: dict) -> dict:
    token = data.get("token")
    if token: response.set_cookie(SESSION_COOKIE, token, max_age=60 * 60 * 24 * 30, httponly=True, secure=True, samesite="lax", path="/")
    return {"ok": True, **data}

@app.post("/auth/register")
def auth_register(request: AuthRequest, response: Response):
    try: return _finish(response, web_auth.register(request.name, request.email, request.password))
    except ValueError as exc: raise HTTPException(400, str(exc)) from exc

@app.post("/auth/login")
def auth_login(request: AuthRequest, response: Response):
    try: return _finish(response, web_auth.login(request.email, request.password))
    except ValueError as exc: raise HTTPException(401, str(exc)) from exc

@app.post("/auth/logout")
def auth_logout(response: Response):
    response.delete_cookie(SESSION_COOKIE, path="/"); return {"ok": True}

@app.get("/auth/me")
def auth_me(request: FastAPIRequest):
    user = web_auth.get_user(_token(request))
    if not user: raise HTTPException(401, "Invalid or expired account session")
    return {"ok": True, "user": user, "history": web_auth.get_activity(user["id"]), "billing": quota.usage(user["id"])}

@app.get("/auth/history")
def auth_history(request: FastAPIRequest):
    user = web_auth.get_user(_token(request))
    if not user: raise HTTPException(401, "Invalid or expired account session")
    return {"ok": True, "history": web_auth.get_activity(user["id"])}

@app.post("/auth/history")
def auth_history_add(request: FastAPIRequest, activity: ActivityRequest):
    user = web_auth.get_user(_token(request))
    if not user: raise HTTPException(401, "Invalid or expired account session")
    web_auth.add_activity(user["id"], activity.kind, activity.title, activity.detail); return {"ok": True}

@app.get("/billing/plans")
def billing_plans():
    plans = quota.plan_catalog()
    prices = billing_yookassa.prices()
    for key, price in prices.items(): plans[key]["price_rub"] = price
    return {"ok": True, "plans": plans, "currency": "RUB", "payment_provider": "yookassa", "payments_enabled": billing_yookassa.enabled()}

@app.get("/billing/usage")
def billing_usage():
    return {"ok": True, "usage": quota.usage(security.current_user_id())}

@app.post("/billing/checkout")
def billing_checkout(payload: CheckoutRequest):
    try: return {"ok": True, **billing_yookassa.create_checkout(security.current_user_id(), payload.plan, payload.return_url)}
    except billing_yookassa.YooKassaError as exc: raise HTTPException(503, str(exc)) from exc

@app.post("/billing/yookassa/webhook")
async def billing_yookassa_webhook(request: FastAPIRequest):
    try:
        event = await request.json()
        return billing_yookassa.handle_webhook(event)
    except billing_yookassa.YooKassaError as exc:
        raise HTTPException(400, str(exc)) from exc

@app.post("/billing/admin/reconcile")
def billing_admin_reconcile(request: FastAPIRequest, payload: BillingReconcileRequest):
    configured = os.getenv("SONA_BILLING_ADMIN_KEY", "").strip()
    supplied = request.headers.get("X-Billing-Admin-Key", "").strip()
    if not configured or supplied != configured:
        raise HTTPException(403, "Billing administration is not authorized")
    try:
        return {"ok": True, "reconciliation": billing_yookassa.reconcile_pending(payload.limit)}
    except billing_yookassa.YooKassaError as exc:
        raise HTTPException(503, str(exc)) from exc

@app.post("/billing/admin/activate")
def billing_admin_activate(request: FastAPIRequest, payload: PlanActivationRequest):
    configured = os.getenv("SONA_BILLING_ADMIN_KEY", "").strip(); supplied = request.headers.get("X-Billing-Admin-Key", "").strip()
    if not configured or supplied != configured: raise HTTPException(403, "Billing administration is not authorized")
    try: state = quota.set_plan(payload.user_id, payload.plan, payload.status, payload.period_end)
    except ValueError as exc: raise HTTPException(400, str(exc)) from exc
    return {"ok": True, "usage": state}

@app.get("/agents")
def agents_catalog(): return {"ok": True, "agents": list_agents()}

@app.get("/agents/tools")
def agents_tools_catalog(): return {"ok": True, "tools": list_tools()}

@app.post("/agents/tools/invoke")
def agents_tool_invoke(request: ToolRequest):
    try: return {"ok": True, "tool": request.name, "result": execute_tool(request.name, request.arguments)}
    except ToolError as exc: raise HTTPException(400, str(exc)) from exc

@app.post("/agents/invoke")
def agents_invoke(request: AgentRequest):
    try: return invoke_agent(request.agent, request.message, history=request.history, context=request.context, user_id=security.current_user_id())
    except AgentError as exc: raise HTTPException(400, str(exc)) from exc

__all__ = ["app"]
