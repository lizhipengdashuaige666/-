"""Payment tracking data models — pure dataclasses, no external dependencies."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class PaymentStatus(Enum):
    WAIT_APPROVAL = "待审批"
    WAIT_FINANCE = "待财务"
    PAID = "已付款"


TRANSITIONS: dict[PaymentStatus, list[PaymentStatus]] = {
    PaymentStatus.WAIT_APPROVAL: [PaymentStatus.WAIT_FINANCE],
    PaymentStatus.WAIT_FINANCE: [PaymentStatus.PAID],
    PaymentStatus.PAID: [],
}

STATUS_DISPLAY: dict[PaymentStatus, tuple[str, str, str]] = {
    PaymentStatus.WAIT_APPROVAL: ("待审批", "tagOrange", "#D97706"),
    PaymentStatus.WAIT_FINANCE: ("待财务", "tagBlue", "#007AFF"),
    PaymentStatus.PAID: ("已付款", "tagGreen", "#2B8A3E"),
}

STATUS_ORDER = [
    PaymentStatus.WAIT_APPROVAL,
    PaymentStatus.WAIT_FINANCE,
    PaymentStatus.PAID,
]


@dataclass
class PaymentRecord:
    id: int = 0
    payment_no: str = ""
    supplier_name: str = ""
    amount: float = 0.0
    apply_date: str = ""
    po_number: str = ""
    status: str = PaymentStatus.WAIT_APPROVAL.value
    notes: str = ""
    created_time: str = ""
    updated_time: str = ""

    @property
    def status_enum(self) -> PaymentStatus:
        return PaymentStatus(self.status)


@dataclass
class PaymentLog:
    id: int = 0
    payment_id: int = 0
    action: str = ""
    old_status: str = ""
    new_status: str = ""
    operator: str = "当前用户"
    timestamp: str = ""
    notes: str = ""


@dataclass
class PaymentAttachment:
    id: int = 0
    payment_id: int = 0
    filename: str = ""
    filepath: str = ""
    created_time: str = ""


@dataclass
class ImportResult:
    imported: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.imported + self.skipped + len(self.errors)
