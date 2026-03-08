import pytest
from domain.entities.plsql_objects import (
    PLSQLProcedure,
    PLSQLTrigger,
    PLSQLPackage,
    PLSQLParameter,
    PostgresFunction,
    PostgresTrigger,
    TranslationResult,
)
from domain.services.plsql_translator_service import PLSQLTranslatorService


@pytest.fixture
def service():
    return PLSQLTranslatorService()


# --- Type Mapping Tests ---


def test_map_varchar2(service):
    assert service.map_parameter_type("VARCHAR2") == "VARCHAR"


def test_map_number(service):
    assert service.map_parameter_type("NUMBER") == "NUMERIC"


def test_map_date(service):
    assert service.map_parameter_type("DATE") == "TIMESTAMP"


def test_map_clob(service):
    assert service.map_parameter_type("CLOB") == "TEXT"


def test_map_blob(service):
    assert service.map_parameter_type("BLOB") == "BYTEA"


def test_map_number_with_precision(service):
    assert service.map_parameter_type("NUMBER(10,2)") == "NUMERIC"


def test_map_unknown_type_passthrough(service):
    assert service.map_parameter_type("MY_CUSTOM_TYPE") == "MY_CUSTOM_TYPE"


# --- Parameter Translation Tests ---


def test_translate_empty_params(service):
    assert service.translate_parameter_list([]) == ""


def test_translate_in_params(service):
    params = [
        PLSQLParameter("p_id", "NUMBER"),
        PLSQLParameter("p_name", "VARCHAR2"),
    ]
    result = service.translate_parameter_list(params)
    assert "p_id NUMERIC" in result
    assert "p_name VARCHAR" in result


def test_translate_out_param(service):
    params = [PLSQLParameter("p_result", "NUMBER", "OUT")]
    result = service.translate_parameter_list(params)
    assert "OUT p_result NUMERIC" in result


def test_translate_inout_param(service):
    params = [PLSQLParameter("p_count", "INTEGER", "IN OUT")]
    result = service.translate_parameter_list(params)
    assert "INOUT p_count INTEGER" in result


def test_translate_param_with_default(service):
    params = [PLSQLParameter("p_status", "VARCHAR2", "IN", "'ACTIVE'")]
    result = service.translate_parameter_list(params)
    assert "DEFAULT 'ACTIVE'" in result


# --- Syntax Replacement Tests ---


def test_nvl_to_coalesce(service):
    body = "SELECT NVL(amount, 0) FROM invoices"
    result, _ = service.apply_syntax_replacements(body)
    assert "COALESCE(" in result
    assert "NVL(" not in result


def test_sysdate_to_current_timestamp(service):
    body = "v_date := SYSDATE;"
    result, _ = service.apply_syntax_replacements(body)
    assert "CURRENT_TIMESTAMP" in result
    assert "SYSDATE" not in result


def test_new_old_references(service):
    body = ":NEW.amount := :OLD.amount * 1.1;"
    result, _ = service.apply_syntax_replacements(body)
    assert "NEW.amount" in result
    assert "OLD.amount" in result
    assert ":NEW" not in result
    assert ":OLD" not in result


def test_dbms_output_to_raise_notice(service):
    body = "DBMS_OUTPUT.PUT_LINE('Hello');"
    result, _ = service.apply_syntax_replacements(body)
    assert "RAISE NOTICE" in result


def test_varchar2_to_varchar(service):
    body = "v_name VARCHAR2(100);"
    result, _ = service.apply_syntax_replacements(body)
    assert "VARCHAR" in result
    assert "VARCHAR2" not in result


# --- Unsupported Construct Detection ---


def test_detect_dbms_sql(service):
    body = "DBMS_SQL.OPEN_CURSOR();"
    found = service.detect_unsupported_constructs(body)
    assert any("DBMS_SQL" in f for f in found)


def test_detect_utl_file(service):
    body = "UTL_FILE.FOPEN('/tmp', 'data.csv', 'W');"
    found = service.detect_unsupported_constructs(body)
    assert any("UTL_FILE" in f for f in found)


def test_detect_bulk_collect(service):
    body = "SELECT col BULK COLLECT INTO v_arr FROM t;"
    found = service.detect_unsupported_constructs(body)
    assert any("BULK COLLECT" in f for f in found)


def test_detect_autonomous_transaction(service):
    body = "PRAGMA AUTONOMOUS_TRANSACTION;"
    found = service.detect_unsupported_constructs(body)
    assert any("Autonomous" in f for f in found)


def test_no_unsupported_in_clean_code(service):
    body = "UPDATE employees SET salary = salary * 1.1 WHERE dept_id = p_dept_id;"
    found = service.detect_unsupported_constructs(body)
    assert found == []


# --- Procedure Translation Tests ---


def test_translate_simple_procedure(service):
    proc = PLSQLProcedure(
        schema_name="APPS",
        object_name="UPDATE_SALARY",
        procedure_name="UPDATE_SALARY",
        parameters=[
            PLSQLParameter("p_emp_id", "NUMBER"),
            PLSQLParameter("p_amount", "NUMBER"),
        ],
        body="UPDATE employees SET salary = salary + p_amount WHERE employee_id = p_emp_id;",
        object_type="PROCEDURE",
    )
    pg_func, issues = service.translate_procedure(proc)
    assert pg_func.function_name == "update_salary"
    assert "p_emp_id NUMERIC" in pg_func.parameters
    assert "RETURNS VOID" in pg_func.body
    assert "CREATE OR REPLACE FUNCTION" in pg_func.body
    assert pg_func.source_object == "APPS.UPDATE_SALARY"


def test_translate_procedure_with_nvl(service):
    proc = PLSQLProcedure(
        schema_name="APPS",
        object_name="CALC",
        procedure_name="CALC_TOTAL",
        parameters=[],
        body="v_total := NVL(amount, 0) + NVL(tax, 0);",
    )
    pg_func, _ = service.translate_procedure(proc)
    assert "COALESCE(" in pg_func.body
    assert "NVL(" not in pg_func.body


# --- Trigger Translation Tests ---


def test_translate_trigger(service):
    trigger = PLSQLTrigger(
        schema_name="APPS",
        trigger_name="TRG_AP_AUDIT",
        table_name="AP_INVOICES_ALL",
        trigger_type="BEFORE",
        triggering_event="INSERT OR UPDATE",
        body=":NEW.last_updated_date := SYSDATE; :NEW.last_updated_by := USER;",
        for_each_row=True,
    )
    pg_func, pg_trigger, issues = service.translate_trigger(trigger)

    assert pg_func.function_name == "fn_trg_ap_audit"
    assert "RETURNS TRIGGER" in pg_func.body
    assert "NEW.last_updated_date" in pg_func.body
    assert "CURRENT_TIMESTAMP" in pg_func.body
    assert "RETURN NEW" in pg_func.body

    assert pg_trigger.trigger_name == "trg_ap_audit"
    assert pg_trigger.table_name == "ap_invoices_all"
    assert pg_trigger.trigger_timing == "BEFORE"
    assert pg_trigger.trigger_event == "INSERT OR UPDATE"
    assert pg_trigger.for_each_row is True


# --- Package Decomposition Tests ---


def test_decompose_package(service):
    package = PLSQLPackage(
        schema_name="APPS",
        package_name="AP_UTILS",
        procedures=[
            PLSQLProcedure("APPS", "AP_UTILS", "GET_VENDOR", [], "SELECT * FROM vendors;"),
            PLSQLProcedure("APPS", "AP_UTILS", "VALIDATE_INVOICE", [], "NULL;"),
        ],
    )
    result = service.decompose_package(package)
    assert len(result) == 2
    assert result[0].procedure_name == "ap_utils_get_vendor"
    assert result[1].procedure_name == "ap_utils_validate_invoice"


# --- Full Translation Tests ---


def test_translate_all(service):
    procedures = [
        PLSQLProcedure("APPS", "P1", "PROC1", [], "UPDATE t SET c = 1;"),
    ]
    triggers = [
        PLSQLTrigger("APPS", "TRG1", "TABLE1", "AFTER", "INSERT", ":NEW.col := SYSDATE;"),
    ]
    packages = []

    result = service.translate_all("APPS", procedures, triggers, packages)

    assert result.source_schema == "APPS"
    assert result.total_objects == 3  # 1 proc func + 1 trigger func + 1 trigger
    assert len(result.functions) == 2  # proc + trigger function
    assert len(result.triggers) == 1


# --- Entity Tests ---


def test_translation_result_properties():
    result = TranslationResult(
        source_schema="APPS",
        functions=[PostgresFunction("fn1", "", body="SELECT 1")],
        triggers=[],
        warnings=["Some warning"],
        unsupported_constructs=["DBMS_SQL dynamic SQL package"],
    )
    assert result.has_warnings is True
    assert result.has_unsupported is True
    assert result.total_objects == 1


def test_translation_result_no_issues():
    result = TranslationResult(source_schema="HR", functions=[], triggers=[])
    assert result.has_warnings is False
    assert result.has_unsupported is False
    assert result.total_objects == 0
