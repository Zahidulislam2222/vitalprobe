"""Minimal local ledger for synthetic Stripe sandbox events and subscriptions."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

from sqlalchemy import Table, update
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlmodel import Field, Session, SQLModel, col, create_engine, select

from vitalprobe.billing.models import BillingPlan, EntitlementState


class BillingEventBusyError(Exception):
    """An active webhook worker owns this event; the sender must retry later."""


class BillingEventRecord(SQLModel, table=True):
    __tablename__ = "billing_sandbox_events"

    id: int | None = Field(default=None, primary_key=True)
    stripe_event_id: str = Field(index=True, unique=True)
    event_type: str = Field(index=True)
    object_id: str = ""
    event_created: int = 0
    outcome: str = "processing"
    detail: str = ""
    processed_at: str = ""


class BillingSubscriptionRecord(SQLModel, table=True):
    __tablename__ = "billing_sandbox_subscriptions"

    stripe_subscription_id: str = Field(primary_key=True)
    stripe_customer_id: str = Field(index=True)
    synthetic_email_hash: str = ""
    plan: str = Field(index=True)
    price_id: str = ""
    status: str = Field(index=True)
    current_period_end: int = 0
    cancel_at_period_end: bool = False
    entitlement_state: str = EntitlementState.PENDING
    license_path: str = ""
    last_event_id: str = ""
    last_event_created: int = 0
    updated_at: str = ""


class BillingPaymentRecord(SQLModel, table=True):
    """Non-sensitive Stripe object IDs used to reconcile refunds and disputes."""

    __tablename__ = "billing_sandbox_payments"

    id: int | None = Field(default=None, primary_key=True)
    stripe_invoice_id: str = Field(index=True, unique=True)
    stripe_subscription_id: str = Field(index=True)
    stripe_payment_intent_id: str = Field(default="", index=True)
    stripe_charge_id: str = Field(default="", index=True)
    recorded_at: str = ""


class BillingPendingReviewRecord(SQLModel, table=True):
    """Payment-risk references awaiting an invoice mapping; no payload or identity data."""

    __tablename__ = "billing_sandbox_pending_reviews"
    stripe_event_id: str = Field(primary_key=True)
    payment_intent_id: str = Field(default="", index=True)
    charge_id: str = Field(default="", index=True)


class BillingStore:
    """Local-only state. Stripe payloads and raw customer details are never stored."""

    def __init__(self, db_path: Path | None = None, *, engine: Engine | None = None) -> None:
        if engine is None:
            if db_path is None:
                raise ValueError("billing store requires a database path or engine")
            db_path.parent.mkdir(parents=True, exist_ok=True)
            engine = create_engine(f"sqlite:///{db_path}")
        self.engine = engine
        SQLModel.metadata.create_all(
            self.engine,
            tables=[
                cast(Table, vars(BillingEventRecord)["__table__"]),
                cast(Table, vars(BillingSubscriptionRecord)["__table__"]),
                cast(Table, vars(BillingPaymentRecord)["__table__"]),
                cast(Table, vars(BillingPendingReviewRecord)["__table__"]),
            ],
        )

    def claim_event(
        self, event_id: str, event_type: str, created: int, object_id: str, *, lease_s: int
    ) -> bool:
        """Atomically claim an event, allowing retries after an interrupted worker's lease."""
        now = datetime.now(UTC)
        stamp = now.isoformat()
        cutoff = (now - timedelta(seconds=lease_s)).isoformat()
        with Session(self.engine) as session:
            existing = session.exec(
                select(BillingEventRecord).where(BillingEventRecord.stripe_event_id == event_id)
            ).first()
            if existing is not None:
                if existing.outcome == "processing" and existing.processed_at > cutoff:
                    raise BillingEventBusyError("sandbox event is processing; retry later")
                if existing.outcome not in {"processing", "error", "retry-required"}:
                    return False
                result = session.execute(
                    update(BillingEventRecord)
                    .where(
                        col(BillingEventRecord.id) == existing.id,
                        col(BillingEventRecord.outcome) == existing.outcome,
                        col(BillingEventRecord.processed_at) == existing.processed_at,
                    )
                    .values(outcome="processing", detail="", processed_at=stamp)
                )
                if getattr(result, "rowcount", 0) != 1:
                    raise BillingEventBusyError("sandbox event was claimed; retry later")
                session.commit()
                return True
            session.add(
                BillingEventRecord(
                    stripe_event_id=event_id,
                    event_type=event_type,
                    object_id=object_id,
                    event_created=created,
                    processed_at=stamp,
                )
            )
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                raise BillingEventBusyError("sandbox event was claimed; retry later") from None
        return True

    def complete_event(self, event_id: str, outcome: str, detail: str = "") -> None:
        with Session(self.engine) as session:
            row = session.exec(
                select(BillingEventRecord).where(BillingEventRecord.stripe_event_id == event_id)
            ).one()
            row.outcome = outcome
            row.detail = detail
            row.processed_at = datetime.now(UTC).isoformat()
            session.add(row)
            session.commit()

    def subscription(self, subscription_id: str) -> BillingSubscriptionRecord | None:
        with Session(self.engine) as session:
            return session.get(BillingSubscriptionRecord, subscription_id)

    def subscriptions(self) -> list[BillingSubscriptionRecord]:
        with Session(self.engine) as session:
            return list(
                session.exec(
                    select(BillingSubscriptionRecord).order_by(
                        col(BillingSubscriptionRecord.updated_at).desc()
                    )
                ).all()
            )

    def record_payment_mapping(
        self,
        *,
        invoice_id: str,
        subscription_id: str,
        payment_intent_id: str = "",
        charge_id: str = "",
    ) -> None:
        """Remember only Stripe IDs needed to associate later payment-risk events."""
        if not invoice_id.startswith("in_") or not subscription_id.startswith("sub_"):
            return
        with Session(self.engine) as session:
            row = session.exec(
                select(BillingPaymentRecord).where(
                    BillingPaymentRecord.stripe_invoice_id == invoice_id
                )
            ).first()
            if row is None:
                row = BillingPaymentRecord(
                    stripe_invoice_id=invoice_id,
                    stripe_subscription_id=subscription_id,
                )
            row.stripe_subscription_id = subscription_id
            row.stripe_payment_intent_id = payment_intent_id or row.stripe_payment_intent_id
            row.stripe_charge_id = charge_id or row.stripe_charge_id
            row.recorded_at = datetime.now(UTC).isoformat()
            session.add(row)
            session.commit()

    def payment_for_invoice(self, invoice_id: str) -> BillingPaymentRecord | None:
        with Session(self.engine) as session:
            return session.exec(
                select(BillingPaymentRecord).where(
                    BillingPaymentRecord.stripe_invoice_id == invoice_id
                )
            ).first()

    def record_pending_review(self, event_id: str, payment_intent_id: str, charge_id: str) -> None:
        with Session(self.engine) as session:
            session.merge(
                BillingPendingReviewRecord(
                    stripe_event_id=event_id,
                    payment_intent_id=payment_intent_id,
                    charge_id=charge_id,
                )
            )
            session.commit()

    def has_pending_review(self, payment_intent_id: str, charge_id: str) -> bool:
        with Session(self.engine) as session:
            for name, value in (("payment_intent_id", payment_intent_id), ("charge_id", charge_id)):
                if (
                    value
                    and session.exec(
                        select(BillingPendingReviewRecord).where(
                            getattr(BillingPendingReviewRecord, name) == value
                        )
                    ).first()
                    is not None
                ):
                    return True
        return False

    def subscription_for_payment(self, *, payment_intent_id: str = "", charge_id: str = "") -> str:
        """Resolve a refund/dispute to the subscription recorded at invoice payment."""
        with Session(self.engine) as session:
            if payment_intent_id:
                row = session.exec(
                    select(BillingPaymentRecord).where(
                        BillingPaymentRecord.stripe_payment_intent_id == payment_intent_id
                    )
                ).first()
                if row is not None:
                    return row.stripe_subscription_id
            if charge_id:
                row = session.exec(
                    select(BillingPaymentRecord).where(
                        BillingPaymentRecord.stripe_charge_id == charge_id
                    )
                ).first()
                if row is not None:
                    return row.stripe_subscription_id
        return ""

    def upsert_subscription(
        self,
        *,
        subscription_id: str,
        customer_id: str,
        email_hash: str,
        plan: BillingPlan,
        price_id: str,
        status: str,
        current_period_end: int,
        cancel_at_period_end: bool,
        entitlement_state: EntitlementState,
        event_id: str,
        event_created: int,
        license_path: str | None = None,
        accept_older_event: bool = False,
    ) -> BillingSubscriptionRecord:
        with Session(self.engine) as session:
            row = session.get(BillingSubscriptionRecord, subscription_id)
            if (
                row is not None
                and event_created < row.last_event_created
                and not accept_older_event
            ):
                return row
            if row is None:
                row = BillingSubscriptionRecord(
                    stripe_subscription_id=subscription_id,
                    stripe_customer_id=customer_id,
                    plan=plan,
                    status=status,
                )
            row.stripe_customer_id = customer_id or row.stripe_customer_id
            row.synthetic_email_hash = email_hash or row.synthetic_email_hash
            row.plan = plan
            row.price_id = price_id or row.price_id
            row.status = status
            row.current_period_end = current_period_end or row.current_period_end
            row.cancel_at_period_end = cancel_at_period_end
            row.entitlement_state = entitlement_state
            if event_created >= row.last_event_created:
                row.last_event_id = event_id
                row.last_event_created = event_created
            row.updated_at = datetime.now(UTC).isoformat()
            if license_path is not None:
                row.license_path = license_path
            session.add(row)
            session.commit()
            session.refresh(row)
            return row

    def events(self) -> list[BillingEventRecord]:
        with Session(self.engine) as session:
            return list(
                session.exec(select(BillingEventRecord).order_by(col(BillingEventRecord.id))).all()
            )
