from __future__ import annotations

import hashlib
import os
import secrets
import time


class YDBStore:
    """Synchronous YDB adapter for accounts, activity, subscriptions and quotas."""
    def __init__(self) -> None:
        try:
            import ydb
        except ImportError as exc:
            raise RuntimeError("ydb package is required when SONA_DB_PROVIDER=ydb") from exc
        endpoint = os.getenv("YDB_ENDPOINT", "").strip(); database = os.getenv("YDB_DATABASE", "").strip()
        if not endpoint or not database: raise RuntimeError("YDB_ENDPOINT and YDB_DATABASE are required when SONA_DB_PROVIDER=ydb")
        self._ydb = ydb; self._table_prefix = os.getenv("YDB_TABLE_PREFIX", "sona").strip("/") or "sona"
        config = ydb.DriverConfig(endpoint, database, credentials=ydb.credentials_from_env_variables(), root_certificates=ydb.load_ydb_root_certificate())
        self._driver = ydb.Driver(config)
        if not self._driver.wait(timeout=10): raise RuntimeError("Unable to connect to YDB")
        self._pool = ydb.QuerySessionPool(self._driver); self._ensure_schema()
    def close(self) -> None:
        try: self._pool.stop()
        finally: self._driver.stop()
    def _table(self, name: str) -> str: return f"{self._table_prefix}_{name}"
    def _ensure_schema(self) -> None:
        statements = [
            f'''CREATE TABLE IF NOT EXISTS `{self._table("users")}` (id Utf8 NOT NULL, name Utf8 NOT NULL, email Utf8 NOT NULL, password_hash Utf8 NOT NULL, created_at Utf8 NOT NULL, PRIMARY KEY (id), INDEX email_idx GLOBAL SYNC ON (email));''',
            f'''CREATE TABLE IF NOT EXISTS `{self._table("sessions")}` (token_hash Utf8 NOT NULL, user_id Utf8 NOT NULL, expires_at Int64 NOT NULL, PRIMARY KEY (token_hash));''',
            f'''CREATE TABLE IF NOT EXISTS `{self._table("activity")}` (id Utf8 NOT NULL, user_id Utf8 NOT NULL, kind Utf8 NOT NULL, title Utf8 NOT NULL, detail Utf8 NOT NULL, created_at Utf8 NOT NULL, PRIMARY KEY (user_id, id));''',
            f'''CREATE TABLE IF NOT EXISTS `{self._table("subscriptions")}` (user_id Utf8 NOT NULL, plan Utf8 NOT NULL, status Utf8 NOT NULL, period_end Utf8 NOT NULL, updated_at Utf8 NOT NULL, PRIMARY KEY (user_id));''',
            f'''CREATE TABLE IF NOT EXISTS `{self._table("usage_monthly")}` (user_id Utf8 NOT NULL, month Utf8 NOT NULL, feature Utf8 NOT NULL, used Int64 NOT NULL, PRIMARY KEY (user_id, month, feature));''',
            f'''CREATE TABLE IF NOT EXISTS `{self._table("billing_payments")}` (payment_id Utf8 NOT NULL, user_id Utf8 NOT NULL, plan Utf8 NOT NULL, claimed_at Utf8 NOT NULL, PRIMARY KEY (payment_id));''',
        ]
        for statement in statements: self._pool.execute_with_retries(statement)
    def _rows(self, query: str, params: dict | None = None):
        result_sets = self._pool.execute_with_retries(query, params or {}); return list(result_sets[0].rows) if result_sets else []
    def register(self, name: str, email: str, password_hash: str) -> dict:
        user_id = secrets.token_hex(16); created_at = str(int(time.time())); normalized_email = email.lower().strip()
        def operation(session):
            tx = session.transaction().begin()
            try:
                check = tx.execute(f"SELECT id FROM `{self._table('users')}` VIEW email_idx WHERE email = $email;", {"$email": normalized_email})
                with check as result_sets:
                    if result_sets and list(result_sets[0].rows): raise ValueError("Email уже зарегистрирован")
                with tx.execute(f'''INSERT INTO `{self._table("users")}` (id,name,email,password_hash,created_at) VALUES ($id,$name,$email,$password_hash,$created_at);''', {"$id": user_id,"$name":name.strip(),"$email":normalized_email,"$password_hash":password_hash,"$created_at":created_at}): pass
                tx.commit()
            except Exception:
                try: tx.rollback()
                except Exception: pass
                raise
        self._pool.retry_operation_sync(operation); return {"user": self.get_user_by_id(user_id)}
    def get_user_by_email(self, email: str) -> dict | None:
        rows=self._rows(f"SELECT id,name,email,password_hash,created_at FROM `{self._table('users')}` VIEW email_idx WHERE email = $email;", {"$email":email.lower().strip()})
        if not rows:return None
        row=rows[0];return {"id":row.id,"name":row.name,"email":row.email,"password_hash":row.password_hash,"created_at":row.created_at}
    def get_user_by_id(self,user_id:str)->dict|None:
        rows=self._rows(f"SELECT id,name,email,created_at FROM `{self._table('users')}` WHERE id = $id;",{"$id":user_id})
        if not rows:return None
        row=rows[0];return {"id":row.id,"name":row.name,"email":row.email,"created_at":row.created_at}
    def create_session(self,user_id:str,token:str,expires_at:int)->None:self._pool.execute_with_retries(f"UPSERT INTO `{self._table('sessions')}` (token_hash,user_id,expires_at) VALUES ($token_hash,$user_id,$expires_at);",{"$token_hash":hashlib.sha256(token.encode()).hexdigest(),"$user_id":user_id,"$expires_at":expires_at})
    def get_user_by_token(self,token:str)->dict|None:
        rows=self._rows(f'''SELECT u.id,u.name,u.email,u.created_at FROM `{self._table("sessions")}` AS s JOIN `{self._table("users")}` AS u ON u.id=s.user_id WHERE s.token_hash=$token_hash AND s.expires_at>$now;''',{"$token_hash":hashlib.sha256(token.encode()).hexdigest(),"$now":int(time.time())})
        if not rows:return None
        row=rows[0];return {"id":row.id,"name":row.name,"email":row.email,"created_at":row.created_at}
    def add_activity(self,user_id,kind,title,detail):self._pool.execute_with_retries(f'''UPSERT INTO `{self._table("activity")}` (id,user_id,kind,title,detail,created_at) VALUES ($id,$user_id,$kind,$title,$detail,$created_at);''',{"$id":f"{time.time_ns()}-{secrets.token_hex(4)}","$user_id":user_id,"$kind":kind[:40],"$title":title[:160],"$detail":detail[:1000],"$created_at":str(int(time.time()))})
    def get_activity(self,user_id,limit=50):
        rows=self._rows(f'''SELECT id,kind,title,detail,created_at FROM `{self._table("activity")}` WHERE user_id=$user_id ORDER BY id DESC LIMIT $limit;''',{"$user_id":user_id,"$limit":max(1,min(limit,100))});return [{"id":r.id,"kind":r.kind,"title":r.title,"detail":r.detail,"created_at":r.created_at} for r in rows]
    def get_subscription(self,user_id):
        rows=self._rows(f"SELECT user_id,plan,status,period_end,updated_at FROM `{self._table('subscriptions')}` WHERE user_id=$user_id;",{"$user_id":user_id})
        if not rows:return None
        r=rows[0];return {"user_id":r.user_id,"plan":r.plan,"status":r.status,"period_end":r.period_end,"updated_at":r.updated_at}
    def set_subscription(self,user_id,plan,status,period_end,updated_at):self._pool.execute_with_retries(f"UPSERT INTO `{self._table('subscriptions')}` (user_id,plan,status,period_end,updated_at) VALUES ($user_id,$plan,$status,$period_end,$updated_at);",{"$user_id":user_id,"$plan":plan,"$status":status,"$period_end":period_end,"$updated_at":updated_at})
    def get_usage(self,user_id,month):
        rows=self._rows(f"SELECT feature,used FROM `{self._table('usage_monthly')}` WHERE user_id=$user_id AND month=$month;",{"$user_id":user_id,"$month":month});return [{"feature":r.feature,"used":int(r.used)} for r in rows]
    def consume_usage(self,user_id,month,feature,units,limit):
        def operation(session):
            tx=session.transaction().begin()
            try:
                result=tx.execute(f"SELECT used FROM `{self._table('usage_monthly')}` WHERE user_id=$user_id AND month=$month AND feature=$feature;",{"$user_id":user_id,"$month":month,"$feature":feature})
                with result as rs: rows=list(rs[0].rows) if rs else []
                used=int(rows[0].used) if rows else 0
                if used+units>limit:tx.rollback();return False,used
                with tx.execute(f"UPSERT INTO `{self._table('usage_monthly')}` (user_id,month,feature,used) VALUES ($user_id,$month,$feature,$used);",{"$user_id":user_id,"$month":month,"$feature":feature,"$used":used+units}):pass
                tx.commit();return True,used+units
            except Exception:
                try:tx.rollback()
                except Exception:pass
                raise
        return self._pool.retry_operation_sync(operation)
    def activate_billing_payment(self,payment_id,user_id,plan,period_end,updated_at):
        def operation(session):
            tx=session.transaction().begin()
            try:
                existing=tx.execute(f"SELECT payment_id FROM `{self._table('billing_payments')}` WHERE payment_id=$payment_id;",{"$payment_id":payment_id})
                with existing as rs:
                    if rs and list(rs[0].rows):
                        tx.rollback()
                        return False
                with tx.execute(f"INSERT INTO `{self._table('billing_payments')}` (payment_id,user_id,plan,claimed_at) VALUES ($payment_id,$user_id,$plan,$claimed_at);",{"$payment_id":payment_id,"$user_id":user_id,"$plan":plan,"$claimed_at":updated_at}):pass
                with tx.execute(f"UPSERT INTO `{self._table('subscriptions')}` (user_id,plan,status,period_end,updated_at) VALUES ($user_id,$plan,$status,$period_end,$updated_at);",{"$user_id":user_id,"$plan":plan,"$status":"active","$period_end":period_end,"$updated_at":updated_at}):pass
                tx.commit()
                return True
            except Exception:
                try:tx.rollback()
                except Exception:pass
                raise
        return self._pool.retry_operation_sync(operation)
    def claim_billing_payment(self,payment_id,user_id,plan):
        def operation(session):
            tx=session.transaction().begin()
            try:
                existing=tx.execute(f"SELECT payment_id FROM `{self._table('billing_payments')}` WHERE payment_id=$payment_id;",{"$payment_id":payment_id})
                with existing as rs:
                    if rs and list(rs[0].rows):tx.rollback();return False
                with tx.execute(f"INSERT INTO `{self._table('billing_payments')}` (payment_id,user_id,plan,claimed_at) VALUES ($payment_id,$user_id,$plan,$claimed_at);",{"$payment_id":payment_id,"$user_id":user_id,"$plan":plan,"$claimed_at":str(int(time.time()))}):pass
                tx.commit();return True
            except Exception:
                try:tx.rollback()
                except Exception:pass
                raise
        return self._pool.retry_operation_sync(operation)

_STORE=None
def get_store():
    global _STORE
    if _STORE is None:_STORE=YDBStore()
    return _STORE
