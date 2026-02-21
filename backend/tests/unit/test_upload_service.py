import uuid

from app.services.upload_service import (
    generate_table_name,
    sanitize_table_name,
    validate_csv_content,
)


class TestSanitizeTableName:
    def test_simple_csv(self) -> None:
        assert sanitize_table_name("sample_data.csv") == "sample_data"

    def test_uppercase(self) -> None:
        assert sanitize_table_name("Sales_Report.csv") == "sales_report"

    def test_spaces_and_special_chars(self) -> None:
        assert sanitize_table_name("my file (1).csv") == "my_file_1"

    def test_multiple_dots(self) -> None:
        assert sanitize_table_name("data.2024.01.csv") == "data_2024_01"

    def test_leading_trailing_specials(self) -> None:
        assert sanitize_table_name("---data---.csv") == "data"

    def test_all_special_chars(self) -> None:
        assert sanitize_table_name("@#$.csv") == "data"

    def test_no_extension(self) -> None:
        assert sanitize_table_name("mydata") == "mydata"

    def test_numbers_only(self) -> None:
        assert sanitize_table_name("12345.csv") == "12345"

    def test_unicode(self) -> None:
        assert sanitize_table_name("données.csv") == "donn_es"

    def test_consecutive_underscores_collapsed(self) -> None:
        assert sanitize_table_name("a___b.csv") == "a_b"


class TestGenerateTableName:
    def test_format(self) -> None:
        sid = uuid.UUID("12345678-1234-5678-1234-567812345678")
        result = generate_table_name(sid, "sales.csv")
        assert result == "s_12345678_sales"

    def test_prefix_length(self) -> None:
        sid = uuid.uuid4()
        result = generate_table_name(sid, "data.csv")
        parts = result.split("_", 2)
        assert parts[0] == "s"
        assert len(parts[1]) == 8

    def test_different_sessions_different_names(self) -> None:
        name1 = generate_table_name(uuid.uuid4(), "data.csv")
        name2 = generate_table_name(uuid.uuid4(), "data.csv")
        assert name1 != name2


class TestValidateCsvContent:
    def test_valid_csv(self) -> None:
        content = b"name,age\nAlice,30\nBob,25\n"
        headers, error = validate_csv_content(content)
        assert error is None
        assert headers == ["name", "age"]

    def test_empty_content(self) -> None:
        headers, error = validate_csv_content(b"")
        assert error == "CSV file is empty"
        assert headers == []

    def test_whitespace_only(self) -> None:
        headers, error = validate_csv_content(b"   \n  \n")
        assert error == "CSV file is empty"
        assert headers == []

    def test_headers_only_no_data(self) -> None:
        content = b"name,age\n"
        headers, error = validate_csv_content(content)
        assert error == "CSV file has no data rows"
        assert headers == []

    def test_empty_headers(self) -> None:
        content = b",\nAlice,30\n"
        headers, error = validate_csv_content(content)
        assert error == "CSV file has no valid headers"
        assert headers == []

    def test_invalid_utf8(self) -> None:
        content = b"\xff\xfe"
        headers, error = validate_csv_content(content)
        assert error == "File is not valid UTF-8 text"
        assert headers == []

    def test_single_column(self) -> None:
        content = b"name\nAlice\n"
        headers, error = validate_csv_content(content)
        assert error is None
        assert headers == ["name"]

    def test_many_rows(self) -> None:
        rows = "name,val\n" + "\n".join(f"r{i},{i}" for i in range(100))
        headers, error = validate_csv_content(rows.encode())
        assert error is None
        assert headers == ["name", "val"]
