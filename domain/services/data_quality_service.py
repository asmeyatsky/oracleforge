import logging
import time
from decimal import Decimal
from typing import Any, Dict, List, Optional

from domain.entities.data_quality import (
    DataQualityReport,
    DataQualityResult,
    DataQualityRule,
)

logger = logging.getLogger(__name__)

# Maximum number of sample violations to capture per rule
_MAX_SAMPLES = 10


class DataQualityService:
    """Evaluates data quality rules against extracted/loaded data.

    Works with lists of dicts (flattened entity data) so that the domain
    layer stays independent of any persistence technology.
    """

    # ------------------------------------------------------------------ #
    # Built-in rule catalogues for Oracle EBS modules
    # ------------------------------------------------------------------ #

    GL_RULES: List[DataQualityRule] = [
        DataQualityRule(
            rule_id="gl_balance_check",
            rule_name="GL Debits Equal Credits",
            module="GL",
            severity="ERROR",
            rule_type="balance",
            table_name="GL_JE_LINES",
            description="Total ACCOUNTED_DR must equal total ACCOUNTED_CR across all journal lines.",
        ),
        DataQualityRule(
            rule_id="gl_no_null_amounts",
            rule_name="GL No Null Amounts",
            module="GL",
            severity="ERROR",
            rule_type="not_null",
            table_name="GL_JE_LINES",
            column_name="ACCOUNTED_DR",
            description="ACCOUNTED_DR or ACCOUNTED_CR must exist on every journal line.",
        ),
        DataQualityRule(
            rule_id="gl_valid_period",
            rule_name="GL Valid Period Name",
            module="GL",
            severity="ERROR",
            rule_type="not_null",
            table_name="GL_JE_HEADERS",
            column_name="PERIOD_NAME",
            description="PERIOD_NAME must not be null.",
        ),
    ]

    AP_RULES: List[DataQualityRule] = [
        DataQualityRule(
            rule_id="ap_positive_amounts",
            rule_name="AP Positive Invoice Amounts",
            module="AP",
            severity="ERROR",
            rule_type="range",
            table_name="AP_INVOICES_ALL",
            column_name="INVOICE_AMOUNT",
            min_value=Decimal("0"),
            description="INVOICE_AMOUNT must be >= 0.",
        ),
        DataQualityRule(
            rule_id="ap_valid_vendor",
            rule_name="AP Valid Vendor ID",
            module="AP",
            severity="ERROR",
            rule_type="not_null",
            table_name="AP_INVOICES_ALL",
            column_name="VENDOR_ID",
            description="VENDOR_ID must not be null.",
        ),
        DataQualityRule(
            rule_id="ap_valid_dates",
            rule_name="AP Valid Invoice/GL Dates",
            module="AP",
            severity="WARNING",
            rule_type="not_null",
            table_name="AP_INVOICES_ALL",
            column_name="INVOICE_DATE",
            description="INVOICE_DATE and GL_DATE must both be present.",
        ),
    ]

    HCM_RULES: List[DataQualityRule] = [
        DataQualityRule(
            rule_id="hcm_unique_employee_num",
            rule_name="HCM Unique Employee Number",
            module="HCM",
            severity="ERROR",
            rule_type="uniqueness",
            table_name="PER_ALL_PEOPLE_F",
            column_name="EMPLOYEE_NUMBER",
            description="EMPLOYEE_NUMBER must be unique across all person records.",
        ),
        DataQualityRule(
            rule_id="hcm_valid_names",
            rule_name="HCM Valid Last Name",
            module="HCM",
            severity="ERROR",
            rule_type="not_null",
            table_name="PER_ALL_PEOPLE_F",
            column_name="LAST_NAME",
            description="LAST_NAME must not be null.",
        ),
        DataQualityRule(
            rule_id="hcm_valid_hire_date",
            rule_name="HCM Valid Hire Date",
            module="HCM",
            severity="WARNING",
            rule_type="not_null",
            table_name="PER_ALL_PEOPLE_F",
            column_name="ORIGINAL_DATE_OF_HIRE",
            description="ORIGINAL_DATE_OF_HIRE must not be null.",
        ),
    ]

    # ------------------------------------------------------------------ #
    # Rule catalogue helpers
    # ------------------------------------------------------------------ #

    def get_default_rules(self, module: str) -> List[DataQualityRule]:
        """Return the built-in rules for a given module."""
        module = module.upper()
        if module == "GL":
            return list(self.GL_RULES)
        if module == "AP":
            return list(self.AP_RULES)
        if module == "HCM":
            return list(self.HCM_RULES)
        if module == "ALL":
            return list(self.GL_RULES) + list(self.AP_RULES) + list(self.HCM_RULES)
        return []

    # ------------------------------------------------------------------ #
    # Individual evaluation methods
    # ------------------------------------------------------------------ #

    def evaluate_not_null(
        self,
        rule: DataQualityRule,
        data: List[Dict[str, Any]],
    ) -> DataQualityResult:
        """Check that *column_name* is not None/empty for every row.

        Special handling for ``gl_no_null_amounts``: a row passes if
        *either* ACCOUNTED_DR or ACCOUNTED_CR is non-null.
        """
        start = time.monotonic()
        violations: List[Dict[str, Any]] = []
        col = rule.column_name

        for idx, row in enumerate(data):
            if rule.rule_id == "gl_no_null_amounts":
                dr = row.get("ACCOUNTED_DR")
                cr = row.get("ACCOUNTED_CR")
                if dr is None and cr is None:
                    violations.append({"row_index": idx, **row})
            elif rule.rule_id == "ap_valid_dates":
                inv_date = row.get("INVOICE_DATE")
                gl_date = row.get("GL_DATE")
                if inv_date is None or gl_date is None:
                    violations.append({"row_index": idx, **row})
            else:
                value = row.get(col)
                if value is None or (isinstance(value, str) and value.strip() == ""):
                    violations.append({"row_index": idx, **row})

        elapsed = time.monotonic() - start
        passed = len(violations) == 0
        return DataQualityResult(
            rule=rule,
            passed=passed,
            violations_count=len(violations),
            sample_violations=violations[:_MAX_SAMPLES],
            execution_time_seconds=round(elapsed, 6),
            message="" if passed else f"{len(violations)} row(s) violate {rule.rule_name}",
        )

    def evaluate_range(
        self,
        rule: DataQualityRule,
        data: List[Dict[str, Any]],
    ) -> DataQualityResult:
        """Check that *column_name* values fall within [min_value, max_value]."""
        start = time.monotonic()
        violations: List[Dict[str, Any]] = []
        col = rule.column_name

        for idx, row in enumerate(data):
            raw_value = row.get(col)
            if raw_value is None:
                continue  # null handling is the responsibility of not_null rules
            try:
                value = Decimal(str(raw_value))
            except Exception:
                violations.append({"row_index": idx, **row})
                continue
            if rule.min_value is not None and value < rule.min_value:
                violations.append({"row_index": idx, **row})
            elif rule.max_value is not None and value > rule.max_value:
                violations.append({"row_index": idx, **row})

        elapsed = time.monotonic() - start
        passed = len(violations) == 0
        return DataQualityResult(
            rule=rule,
            passed=passed,
            violations_count=len(violations),
            sample_violations=violations[:_MAX_SAMPLES],
            execution_time_seconds=round(elapsed, 6),
            message="" if passed else f"{len(violations)} row(s) violate {rule.rule_name}",
        )

    def evaluate_uniqueness(
        self,
        rule: DataQualityRule,
        data: List[Dict[str, Any]],
    ) -> DataQualityResult:
        """Check that all values for *column_name* are unique."""
        start = time.monotonic()
        col = rule.column_name
        seen: Dict[Any, int] = {}
        duplicate_indices: List[int] = []

        for idx, row in enumerate(data):
            value = row.get(col)
            if value is None:
                continue  # nulls don't count toward uniqueness
            if value in seen:
                duplicate_indices.append(idx)
            else:
                seen[value] = idx

        violations = [{"row_index": i, **data[i]} for i in duplicate_indices]
        elapsed = time.monotonic() - start
        passed = len(violations) == 0
        return DataQualityResult(
            rule=rule,
            passed=passed,
            violations_count=len(violations),
            sample_violations=violations[:_MAX_SAMPLES],
            execution_time_seconds=round(elapsed, 6),
            message="" if passed else f"{len(violations)} duplicate(s) found for {col}",
        )

    def evaluate_referential(
        self,
        rule: DataQualityRule,
        data: List[Dict[str, Any]],
        reference_data: List[Dict[str, Any]],
    ) -> DataQualityResult:
        """Check that every *column_name* value exists in *reference_column* of *reference_data*."""
        start = time.monotonic()
        ref_col = rule.reference_column or rule.column_name
        ref_values = {row.get(ref_col) for row in reference_data}
        col = rule.column_name
        violations: List[Dict[str, Any]] = []

        for idx, row in enumerate(data):
            value = row.get(col)
            if value is None:
                continue
            if value not in ref_values:
                violations.append({"row_index": idx, **row})

        elapsed = time.monotonic() - start
        passed = len(violations) == 0
        return DataQualityResult(
            rule=rule,
            passed=passed,
            violations_count=len(violations),
            sample_violations=violations[:_MAX_SAMPLES],
            execution_time_seconds=round(elapsed, 6),
            message="" if passed else f"{len(violations)} orphan(s) for {col}",
        )

    def evaluate_balance(
        self,
        rule: DataQualityRule,
        data: List[Dict[str, Any]],
    ) -> DataQualityResult:
        """Check that total debits equal total credits (GL-specific)."""
        start = time.monotonic()
        total_dr = Decimal("0")
        total_cr = Decimal("0")

        for row in data:
            dr = row.get("ACCOUNTED_DR")
            cr = row.get("ACCOUNTED_CR")
            if dr is not None:
                total_dr += Decimal(str(dr))
            if cr is not None:
                total_cr += Decimal(str(cr))

        elapsed = time.monotonic() - start
        passed = total_dr == total_cr
        diff = total_dr - total_cr
        return DataQualityResult(
            rule=rule,
            passed=passed,
            violations_count=0 if passed else 1,
            sample_violations=(
                []
                if passed
                else [{"total_dr": str(total_dr), "total_cr": str(total_cr), "difference": str(diff)}]
            ),
            execution_time_seconds=round(elapsed, 6),
            message="" if passed else f"Imbalance: DR={total_dr} CR={total_cr} diff={diff}",
        )

    # ------------------------------------------------------------------ #
    # Orchestration
    # ------------------------------------------------------------------ #

    def evaluate_rules(
        self,
        module: str,
        data: List[Dict[str, Any]],
        rules: Optional[List[DataQualityRule]] = None,
        reference_data: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ) -> DataQualityReport:
        """Evaluate a set of rules against *data* and produce a report.

        Parameters
        ----------
        module:
            Oracle EBS module name ("GL", "AP", "HCM").
        data:
            List of row dicts to validate.
        rules:
            Rules to evaluate.  Falls back to ``get_default_rules(module)``.
        reference_data:
            Optional mapping of ``reference_table`` to row-list, used by
            referential-integrity rules.
        """
        if rules is None:
            rules = self.get_default_rules(module)
        if reference_data is None:
            reference_data = {}

        results: List[DataQualityResult] = []

        for rule in rules:
            if rule.rule_type == "not_null":
                result = self.evaluate_not_null(rule, data)
            elif rule.rule_type == "range":
                result = self.evaluate_range(rule, data)
            elif rule.rule_type == "uniqueness":
                result = self.evaluate_uniqueness(rule, data)
            elif rule.rule_type == "balance":
                result = self.evaluate_balance(rule, data)
            elif rule.rule_type == "referential":
                ref = reference_data.get(rule.reference_table or "", [])
                result = self.evaluate_referential(rule, data, ref)
            else:
                # Unsupported rule type — skip with an info message
                logger.warning(
                    "Skipping rule %s: unsupported rule_type '%s'",
                    rule.rule_id,
                    rule.rule_type,
                )
                continue
            results.append(result)

        passed = sum(1 for r in results if r.passed)
        failed = sum(
            1 for r in results if not r.passed and r.rule.severity == "ERROR"
        )
        warned = sum(
            1 for r in results if not r.passed and r.rule.severity in ("WARNING", "INFO")
        )

        report = DataQualityReport(
            module=module.upper(),
            rules_evaluated=len(results),
            rules_passed=passed,
            rules_failed=failed,
            rules_warned=warned,
            results=results,
        )

        logger.info(
            "Data quality report for %s: %d/%d passed (%.1f%%), %d errors, %d warnings",
            module,
            passed,
            len(results),
            report.pass_rate * 100,
            failed,
            warned,
        )
        return report
