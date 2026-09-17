from __future__ import annotations

from datetime import datetime, timedelta, timezone

import quota


PERIOD_DAYS = 31


def _next_period_end(existing_period_end: str | None, now: datetime) -> str:
    if existing_period_end:
        try:
            current = datetime.fromisoformat(str(existing_period_end).replace("Z", "+00:00"))
            if current.tzinfo is None:
                current = current.replace(tzinfo=timezone.utc)
            if current > now:
                return (current + timedelta(days=PERIOD_DAYS)).isoformat()
        except ValueError:
            pass
    return (now + timedelta(days=PERIOD_DAYS)).isoformat()


def activate_payment(payment_id: str, user_id: str, plan: str) -> tuple[bool, dict]:
    """Claim one succeeded payment and atomically extend the user's paid period."""
    if not payment_id or plan not in quota.PLANS or plan == "free":
        raise ValueError("Invalid paid payment activation")

    now_dt = datetime.now(timezone.utc)
    now = now_dt.isoformat()
    updated_at = str(int(now_dt.timestamp()))

    if quota.DB_PROVIDER == "ydb":
        store = quota._ydb()

        def operation(session):
            tx = session.transaction().begin()
            try:
                existing_payment = tx.execute(
                    f"SELECT payment_id FROM `{store._table('billing_payments')}` WHERE payment_id=$payment_id;",
                    {"$payment_id": payment_id},
                )
                with existing_payment as rs:
                    if rs and list(rs[0].rows):
                        tx.rollback()
                        return False

                subscription = tx.execute(
                    f"SELECT period_end FROM `{store._table('subscriptions')}` WHERE user_id=$user_id;",
                    {"$user_id": user_id},
                )
                with subscription as rs:
                    rows = list(rs[0].rows) if rs else []
                existing_period_end = rows[0].period_end if rows else ""
                period_end = _next_period_end(existing_period_end, now_dt)

                with tx.execute(
                    f"INSERT INTO `{store._table('billing_payments')}` (payment_id,user_id,plan,claimed_at) VALUES ($payment_id,$user_id,$plan,$claimed_at);",
                    {"$payment_id": payment_id, "$user_id": user_id, "$plan": plan, "$claimed_at": now},
                ):
                    pass
                with tx.execute(
                    f"UPSERT INTO `{store._table('subscriptions')}` (user_id,plan,status,period_end,updated_at) VALUES ($user_id,$plan,$status,$period_end,$updated_at);",
                    {"$user_id": user_id, "$plan": plan, "$status": "active", "$period_end": period_end, "$updated_at": updated_at},
                ):
                    pass
                with tx.execute(
                    f"UPDATE `{store._table('billing_pending')}` SET status=$status,updated_at=$updated_at WHERE payment_id=$payment_id;",
                    {"$payment_id": payment_id, "$status": "succeeded", "$updated_at": now},
                ):
                    pass
                tx.commit()
                return True
            except Exception:
                try:
                    tx.rollback()
                except Exception:
                    pass
                raise

        claimed = bool(store._pool.retry_operation_sync(operation))
        return claimed, quota.usage(user_id)

    with quota._LOCK:
        conn = quota._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.execute(
                "INSERT OR IGNORE INTO billing_payments(payment_id,user_id,plan,claimed_at) VALUES(?,?,?,?)",
                (payment_id, user_id, plan, now),
            )
            if cursor.rowcount == 0:
                conn.rollback()
                return False, quota.usage(user_id)

            row = conn.execute(
                "SELECT period_end FROM subscriptions WHERE user_id=?",
                (user_id,),
            ).fetchone()
            period_end = _next_period_end(row[0] if row else None, now_dt)
            conn.execute(
                "INSERT INTO subscriptions(user_id,plan,status,period_end,updated_at) VALUES(?,?,?,?,?) "
                "ON CONFLICT(user_id) DO UPDATE SET plan=excluded.plan,status=excluded.status,period_end=excluded.period_end,updated_at=excluded.updated_at",
                (user_id, plan, "active", period_end, updated_at),
            )
            conn.execute(
                "UPDATE billing_pending SET status='succeeded',updated_at=? WHERE payment_id=?",
                (now, payment_id),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    return True, quota.usage(user_id)
