import pytest
from decimal import Decimal

from domain.entities.data_quality import (
    DataQualityReport,
    DataQualityResult,
    DataQualityRule,
)
from domain.services.data_quality_service import DataQualityService


# ------------------------------------------------------------------ #
# Fixtures
# ------------------------------------------------------------------ #


@pytest.fixture
def service():
    return DataQualityService()


@pytest.fixture
def not_null_rule():
    return DataQualityRule(
        rule_id="test_not_null",
        rule_name="Test Not Null",
        module="GL",
        severity="ERROR",
        rule_type="not_null",
        table_name="TEST_TABLE",
        column_name="COL_A",
    )


@pytest.fixture
def range_rule():
    return DataQualityRule(
        rule_id="test_range",
        rule_name="Test Range",
        module="AP",
        severity="ERROR",
        rule_type="range",
        table_name="TEST_TABLE",
        column_name="AMOUNT",
        min_value=Decimal("0"),
        max_value=Decimal("1000"),
    )


@pytest.fixture
def uniqueness_rule():
    return DataQualityRule(
        rule_id="test_unique",
        rule_name="Test Uniqueness",
        module="HCM",
        severity="ERROR",
        rule_type="uniqueness",
        table_name="TEST_TABLE",
        column_name="EMP_NUM",
    )


@pytest.fixture
def balance_rule():
    return DataQualityRule(
        rule_id="gl_balance_check",
        rule_name="GL Debits Equal Credits",
        module="GL",
        severity="ERROR",
        rule_type="balance",
        table_name="GL_JE_LINES",
    )


@pytest.fixture
def referential_rule():
    return DataQualityRule(
        rule_id="test_referential",
        rule_name="Test Referential",
        module="AP",
        severity="ERROR",
        rule_type="referential",
        table_name="AP_INVOICES_ALL",
        column_name="VENDOR_ID",
        reference_table="AP_SUPPLIERS",
        reference_column="VENDOR_ID",
    )


# ------------------------------------------------------------------ #
# Entity tests
# ------------------------------------------------------------------ #


class TestDataQualityRule:
    def test_frozen(self):
        rule = DataQualityRule(
            rule_id="r1",
            rule_name="Rule 1",
            module="GL",
            severity="ERROR",
            rule_type="not_null",
            table_name="T1",
        )
        with pytest.raises(AttributeError):
            rule.rule_id = "r2"  # type: ignore[misc]

    def test_optional_fields_default_none(self):
        rule = DataQualityRule(
            rule_id="r1",
            rule_name="Rule 1",
            module="GL",
            severity="ERROR",
            rule_type="not_null",
            table_name="T1",
        )
        assert rule.column_name is None
        assert rule.expression is None
        assert rule.min_value is None
        assert rule.max_value is None
        assert rule.reference_table is None
        assert rule.reference_column is None
        assert rule.description == ""


class TestDataQualityReport:
    def test_pass_rate_all_passed(self):
        rule = DataQualityRule(
            rule_id="r", rule_name="R", module="GL",
            severity="ERROR", rule_type="not_null", table_name="T",
        )
        result = DataQualityResult(rule=rule, passed=True)
        report = DataQualityReport(
            module="GL",
            rules_evaluated=3,
            rules_passed=3,
            rules_failed=0,
            rules_warned=0,
            results=[result],
        )
        assert report.pass_rate == 1.0

    def test_pass_rate_zero_evaluated(self):
        report = DataQualityReport(
            module="GL",
            rules_evaluated=0,
            rules_passed=0,
            rules_failed=0,
            rules_warned=0,
        )
        assert report.pass_rate == 0.0

    def test_has_errors_true(self):
        rule = DataQualityRule(
            rule_id="r", rule_name="R", module="GL",
            severity="ERROR", rule_type="not_null", table_name="T",
        )
        result = DataQualityResult(rule=rule, passed=False, violations_count=1)
        report = DataQualityReport(
            module="GL",
            rules_evaluated=1,
            rules_passed=0,
            rules_failed=1,
            rules_warned=0,
            results=[result],
        )
        assert report.has_errors is True

    def test_has_errors_false_when_only_warnings(self):
        rule = DataQualityRule(
            rule_id="r", rule_name="R", module="GL",
            severity="WARNING", rule_type="not_null", table_name="T",
        )
        result = DataQualityResult(rule=rule, passed=False, violations_count=1)
        report = DataQualityReport(
            module="GL",
            rules_evaluated=1,
            rules_passed=0,
            rules_failed=0,
            rules_warned=1,
            results=[result],
        )
        assert report.has_errors is False


# ------------------------------------------------------------------ #
# Service — get_default_rules
# ------------------------------------------------------------------ #


class TestGetDefaultRules:
    def test_gl_rules_count(self, service):
        rules = service.get_default_rules("GL")
        assert len(rules) == 3

    def test_ap_rules_count(self, service):
        rules = service.get_default_rules("AP")
        assert len(rules) == 3

    def test_hcm_rules_count(self, service):
        rules = service.get_default_rules("HCM")
        assert len(rules) == 3

    def test_all_rules_count(self, service):
        rules = service.get_default_rules("ALL")
        assert len(rules) == 9

    def test_unknown_module_returns_empty(self, service):
        assert service.get_default_rules("UNKNOWN") == []


# ------------------------------------------------------------------ #
# Service — evaluate_not_null
# ------------------------------------------------------------------ #


class TestEvaluateNotNull:
    def test_passes_when_all_present(self, service, not_null_rule):
        data = [{"COL_A": "x"}, {"COL_A": "y"}]
        result = service.evaluate_not_null(not_null_rule, data)
        assert result.passed is True
        assert result.violations_count == 0

    def test_fails_when_null(self, service, not_null_rule):
        data = [{"COL_A": "x"}, {"COL_A": None}, {"COL_A": "z"}]
        result = service.evaluate_not_null(not_null_rule, data)
        assert result.passed is False
        assert result.violations_count == 1

    def test_fails_when_empty_string(self, service, not_null_rule):
        data = [{"COL_A": "  "}]
        result = service.evaluate_not_null(not_null_rule, data)
        assert result.passed is False
        assert result.violations_count == 1

    def test_gl_no_null_amounts_passes(self, service):
        """Either ACCOUNTED_DR or ACCOUNTED_CR present is enough."""
        rule = DataQualityRule(
            rule_id="gl_no_null_amounts",
            rule_name="GL No Null Amounts",
            module="GL",
            severity="ERROR",
            rule_type="not_null",
            table_name="GL_JE_LINES",
            column_name="ACCOUNTED_DR",
        )
        data = [
            {"ACCOUNTED_DR": Decimal("100"), "ACCOUNTED_CR": None},
            {"ACCOUNTED_DR": None, "ACCOUNTED_CR": Decimal("200")},
        ]
        result = service.evaluate_not_null(rule, data)
        assert result.passed is True

    def test_gl_no_null_amounts_fails(self, service):
        rule = DataQualityRule(
            rule_id="gl_no_null_amounts",
            rule_name="GL No Null Amounts",
            module="GL",
            severity="ERROR",
            rule_type="not_null",
            table_name="GL_JE_LINES",
            column_name="ACCOUNTED_DR",
        )
        data = [
            {"ACCOUNTED_DR": None, "ACCOUNTED_CR": None},
        ]
        result = service.evaluate_not_null(rule, data)
        assert result.passed is False
        assert result.violations_count == 1

    def test_ap_valid_dates_passes(self, service):
        rule = DataQualityRule(
            rule_id="ap_valid_dates",
            rule_name="AP Valid Dates",
            module="AP",
            severity="WARNING",
            rule_type="not_null",
            table_name="AP_INVOICES_ALL",
            column_name="INVOICE_DATE",
        )
        data = [{"INVOICE_DATE": "2026-01-01", "GL_DATE": "2026-01-15"}]
        result = service.evaluate_not_null(rule, data)
        assert result.passed is True

    def test_ap_valid_dates_fails_missing_gl_date(self, service):
        rule = DataQualityRule(
            rule_id="ap_valid_dates",
            rule_name="AP Valid Dates",
            module="AP",
            severity="WARNING",
            rule_type="not_null",
            table_name="AP_INVOICES_ALL",
            column_name="INVOICE_DATE",
        )
        data = [{"INVOICE_DATE": "2026-01-01", "GL_DATE": None}]
        result = service.evaluate_not_null(rule, data)
        assert result.passed is False


# ------------------------------------------------------------------ #
# Service — evaluate_range
# ------------------------------------------------------------------ #


class TestEvaluateRange:
    def test_passes_within_range(self, service, range_rule):
        data = [{"AMOUNT": 500}, {"AMOUNT": 0}, {"AMOUNT": 1000}]
        result = service.evaluate_range(range_rule, data)
        assert result.passed is True

    def test_fails_below_min(self, service, range_rule):
        data = [{"AMOUNT": -1}]
        result = service.evaluate_range(range_rule, data)
        assert result.passed is False
        assert result.violations_count == 1

    def test_fails_above_max(self, service, range_rule):
        data = [{"AMOUNT": 1001}]
        result = service.evaluate_range(range_rule, data)
        assert result.passed is False

    def test_null_values_skipped(self, service, range_rule):
        data = [{"AMOUNT": None}]
        result = service.evaluate_range(range_rule, data)
        assert result.passed is True

    def test_ap_negative_amount_detection(self, service):
        """AP_INVOICES_ALL INVOICE_AMOUNT must be >= 0."""
        rules = service.get_default_rules("AP")
        amount_rule = next(r for r in rules if r.rule_id == "ap_positive_amounts")
        data = [
            {"INVOICE_AMOUNT": Decimal("100.00")},
            {"INVOICE_AMOUNT": Decimal("-50.00")},
            {"INVOICE_AMOUNT": Decimal("0")},
        ]
        result = service.evaluate_range(amount_rule, data)
        assert result.passed is False
        assert result.violations_count == 1
        assert result.sample_violations[0]["INVOICE_AMOUNT"] == Decimal("-50.00")


# ------------------------------------------------------------------ #
# Service — evaluate_uniqueness
# ------------------------------------------------------------------ #


class TestEvaluateUniqueness:
    def test_passes_all_unique(self, service, uniqueness_rule):
        data = [{"EMP_NUM": "E001"}, {"EMP_NUM": "E002"}, {"EMP_NUM": "E003"}]
        result = service.evaluate_uniqueness(uniqueness_rule, data)
        assert result.passed is True

    def test_fails_duplicates(self, service, uniqueness_rule):
        data = [{"EMP_NUM": "E001"}, {"EMP_NUM": "E002"}, {"EMP_NUM": "E001"}]
        result = service.evaluate_uniqueness(uniqueness_rule, data)
        assert result.passed is False
        assert result.violations_count == 1

    def test_nulls_ignored(self, service, uniqueness_rule):
        data = [{"EMP_NUM": None}, {"EMP_NUM": None}]
        result = service.evaluate_uniqueness(uniqueness_rule, data)
        assert result.passed is True

    def test_hcm_unique_employee_number(self, service):
        """HCM EMPLOYEE_NUMBER uniqueness violation detection."""
        rules = service.get_default_rules("HCM")
        uniq_rule = next(r for r in rules if r.rule_id == "hcm_unique_employee_num")
        data = [
            {"EMPLOYEE_NUMBER": "1001", "LAST_NAME": "Smith"},
            {"EMPLOYEE_NUMBER": "1002", "LAST_NAME": "Jones"},
            {"EMPLOYEE_NUMBER": "1001", "LAST_NAME": "Brown"},
        ]
        result = service.evaluate_uniqueness(uniq_rule, data)
        assert result.passed is False
        assert result.violations_count == 1


# ------------------------------------------------------------------ #
# Service — evaluate_referential
# ------------------------------------------------------------------ #


class TestEvaluateReferential:
    def test_passes_all_found(self, service, referential_rule):
        data = [{"VENDOR_ID": 1}, {"VENDOR_ID": 2}]
        ref_data = [{"VENDOR_ID": 1}, {"VENDOR_ID": 2}, {"VENDOR_ID": 3}]
        result = service.evaluate_referential(referential_rule, data, ref_data)
        assert result.passed is True

    def test_fails_orphan(self, service, referential_rule):
        data = [{"VENDOR_ID": 1}, {"VENDOR_ID": 99}]
        ref_data = [{"VENDOR_ID": 1}, {"VENDOR_ID": 2}]
        result = service.evaluate_referential(referential_rule, data, ref_data)
        assert result.passed is False
        assert result.violations_count == 1


# ------------------------------------------------------------------ #
# Service — evaluate_balance (GL debit/credit)
# ------------------------------------------------------------------ #


class TestEvaluateBalance:
    def test_balanced(self, service, balance_rule):
        data = [
            {"ACCOUNTED_DR": Decimal("100"), "ACCOUNTED_CR": None},
            {"ACCOUNTED_DR": None, "ACCOUNTED_CR": Decimal("100")},
        ]
        result = service.evaluate_balance(balance_rule, data)
        assert result.passed is True
        assert result.violations_count == 0

    def test_imbalanced(self, service, balance_rule):
        data = [
            {"ACCOUNTED_DR": Decimal("100"), "ACCOUNTED_CR": None},
            {"ACCOUNTED_DR": None, "ACCOUNTED_CR": Decimal("80")},
        ]
        result = service.evaluate_balance(balance_rule, data)
        assert result.passed is False
        assert result.violations_count == 1
        assert "Imbalance" in result.message

    def test_gl_balance_check_catches_imbalance(self, service):
        """GL balance check must catch mismatched debits and credits."""
        rules = service.get_default_rules("GL")
        bal_rule = next(r for r in rules if r.rule_id == "gl_balance_check")
        data = [
            {"ACCOUNTED_DR": Decimal("5000"), "ACCOUNTED_CR": None},
            {"ACCOUNTED_DR": Decimal("3000"), "ACCOUNTED_CR": None},
            {"ACCOUNTED_DR": None, "ACCOUNTED_CR": Decimal("7000")},
        ]
        result = service.evaluate_balance(bal_rule, data)
        assert result.passed is False
        sample = result.sample_violations[0]
        assert sample["total_dr"] == "8000"
        assert sample["total_cr"] == "7000"
        assert sample["difference"] == "1000"

    def test_empty_data_balanced(self, service, balance_rule):
        result = service.evaluate_balance(balance_rule, [])
        assert result.passed is True


# ------------------------------------------------------------------ #
# Service — evaluate_rules (orchestration)
# ------------------------------------------------------------------ #


class TestEvaluateRules:
    def test_gl_report_all_pass(self, service):
        data = [
            {"ACCOUNTED_DR": Decimal("100"), "ACCOUNTED_CR": None, "PERIOD_NAME": "Jan-26"},
            {"ACCOUNTED_DR": None, "ACCOUNTED_CR": Decimal("100"), "PERIOD_NAME": "Jan-26"},
        ]
        report = service.evaluate_rules("GL", data)
        assert report.module == "GL"
        assert report.rules_evaluated == 3
        assert report.rules_passed == 3
        assert report.rules_failed == 0
        assert report.has_errors is False
        assert report.pass_rate == 1.0

    def test_gl_report_with_failures(self, service):
        data = [
            {"ACCOUNTED_DR": Decimal("100"), "ACCOUNTED_CR": None, "PERIOD_NAME": "Jan-26"},
            {"ACCOUNTED_DR": None, "ACCOUNTED_CR": Decimal("50"), "PERIOD_NAME": None},
        ]
        report = service.evaluate_rules("GL", data)
        assert report.rules_evaluated == 3
        assert report.rules_passed < 3
        assert report.has_errors is True

    def test_ap_report(self, service):
        data = [
            {"INVOICE_AMOUNT": Decimal("100"), "VENDOR_ID": 1, "INVOICE_DATE": "2026-01-01", "GL_DATE": "2026-01-15"},
            {"INVOICE_AMOUNT": Decimal("200"), "VENDOR_ID": 2, "INVOICE_DATE": "2026-02-01", "GL_DATE": "2026-02-15"},
        ]
        report = service.evaluate_rules("AP", data)
        assert report.module == "AP"
        assert report.rules_evaluated == 3
        assert report.rules_passed == 3

    def test_hcm_report(self, service):
        data = [
            {"EMPLOYEE_NUMBER": "E001", "LAST_NAME": "Smith", "ORIGINAL_DATE_OF_HIRE": "2020-01-15"},
            {"EMPLOYEE_NUMBER": "E002", "LAST_NAME": "Jones", "ORIGINAL_DATE_OF_HIRE": "2021-06-01"},
        ]
        report = service.evaluate_rules("HCM", data)
        assert report.module == "HCM"
        assert report.rules_evaluated == 3
        assert report.rules_passed == 3

    def test_custom_rules_override_defaults(self, service):
        custom_rule = DataQualityRule(
            rule_id="custom_1",
            rule_name="Custom Not Null",
            module="GL",
            severity="WARNING",
            rule_type="not_null",
            table_name="T",
            column_name="X",
        )
        data = [{"X": "hello"}]
        report = service.evaluate_rules("GL", data, rules=[custom_rule])
        assert report.rules_evaluated == 1
        assert report.rules_passed == 1

    def test_referential_in_evaluate_rules(self, service):
        rule = DataQualityRule(
            rule_id="ref_check",
            rule_name="Ref Check",
            module="AP",
            severity="ERROR",
            rule_type="referential",
            table_name="AP_INVOICES_ALL",
            column_name="VENDOR_ID",
            reference_table="AP_SUPPLIERS",
            reference_column="VENDOR_ID",
        )
        data = [{"VENDOR_ID": 1}, {"VENDOR_ID": 99}]
        ref = {"AP_SUPPLIERS": [{"VENDOR_ID": 1}, {"VENDOR_ID": 2}]}
        report = service.evaluate_rules("AP", data, rules=[rule], reference_data=ref)
        assert report.rules_evaluated == 1
        assert report.rules_failed == 1

    def test_report_executed_at_populated(self, service):
        data = [{"ACCOUNTED_DR": Decimal("0"), "ACCOUNTED_CR": Decimal("0"), "PERIOD_NAME": "Jan-26"}]
        report = service.evaluate_rules("GL", data)
        assert report.executed_at is not None
