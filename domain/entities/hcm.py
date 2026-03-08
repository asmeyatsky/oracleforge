from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from domain.value_objects.common import Money, MultiOrgContext, Period

@dataclass(frozen=True)
class Employee:
    """Represents an Oracle HCM Person/Employee."""
    person_id: int
    employee_number: str
    full_name: str
    first_name: str
    last_name: str
    email_address: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    original_date_of_hire: Optional[datetime] = None
    effective_start_date: datetime = datetime.now()
    effective_end_date: datetime = datetime.max

@dataclass(frozen=True)
class Assignment:
    """Represents an Oracle HCM Employee Assignment (Job, Org, Salary)."""
    assignment_id: int
    person_id: int
    organization_id: int
    job_id: int
    location_id: int
    supervisor_id: Optional[int] = None
    assignment_number: str = ""
    assignment_status: str = "ACTIVE"
    base_salary: Optional[Money] = None
    context: MultiOrgContext = None

@dataclass(frozen=True)
class PayrollSummary:
    """Represents a summary of payroll results for an employee and period."""
    payroll_id: int
    person_id: int
    period: Period
    gross_pay: Money
    net_pay: Money
    deductions: Money
    currency_code: str
    context: MultiOrgContext
