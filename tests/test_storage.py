import storage


def test_components_schema_has_expected_keys():
    keys = [c["key"] for c in storage.COMPONENTS]
    assert keys == ["cpu", "ram", "gpu", "storage", "motherboard", "psu"]


def test_every_component_has_label_icon_and_fields():
    for component in storage.COMPONENTS:
        assert component["label"]
        assert component["icon"]
        assert isinstance(component["fields"], list)
        for field in component["fields"]:
            assert field["key"]
            assert field["label"]
            assert field["widget"] in {"text", "number", "select"}
            if field["widget"] == "select":
                assert "" in field["options"]


def test_empty_computer_skeleton():
    record = storage.empty_computer()
    assert record["computer_name"] == ""
    assert record["created_at"] == ""
    assert record["notes"] == ""
    assert record["storage"] == []
    # scalar components are dicts with one entry per schema field
    assert record["cpu"]["model"] == ""
    assert record["cpu"]["cores"] is None          # number defaults to None
    assert record["motherboard"]["form_factor"] == ""
    assert record["psu"]["wattage"] is None


def test_save_then_load_round_trips(tmp_path):
    path = tmp_path / "computers.json"
    record = storage.empty_computer()
    record["computer_name"] = "TEST-RIG"
    record["cpu"]["model"] = "Ryzen 5 5600X"
    record["storage"] = [{"manufacturer": "Kingston", "model": "",
                          "type": "NVMe SSD", "capacity": "1 TB",
                          "form_factor": "M.2 2280"}]

    storage.save_computers([record], path=path)
    loaded = storage.load_computers(path=path)

    assert loaded == [record]


def test_load_missing_file_returns_empty_list(tmp_path):
    assert storage.load_computers(path=tmp_path / "nope.json") == []


def test_add_computer_appends(tmp_path):
    path = tmp_path / "computers.json"
    first = storage.empty_computer()
    first["computer_name"] = "A"
    second = storage.empty_computer()
    second["computer_name"] = "B"

    storage.add_computer(first, path=path)
    storage.add_computer(second, path=path)

    names = [c["computer_name"] for c in storage.load_computers(path=path)]
    assert names == ["A", "B"]


def test_update_computer_preserves_created_at(tmp_path):
    path = tmp_path / "computers.json"
    original = storage.empty_computer()
    original["computer_name"] = "A"
    original["created_at"] = "2026-01-01T00:00:00"
    storage.add_computer(original, path=path)

    edited = storage.empty_computer()
    edited["computer_name"] = "A-renamed"
    edited["created_at"] = "ignored"            # must be overwritten with original
    storage.update_computer(0, edited, path=path)

    result = storage.load_computers(path=path)[0]
    assert result["computer_name"] == "A-renamed"
    assert result["created_at"] == "2026-01-01T00:00:00"


def _write_legacy_csv(path):
    path.write_text(
        "Computer Name,CPU,RAM,GPU,Storage,Motherboard,PSU,Notes,Created At\n"
        "XEON,intel xeon,64gb,quadro p4000,kingston nvme 500gb,"
        "dell precision 3630,stock,main workstation,2026-04-07T15:24:26\n"
        "TEXTRAM,cpu,dual channel,gpu,,mobo,psu,note,2026-04-07T16:00:00\n",
        encoding="utf-8",
    )


def test_migration_converts_rows(tmp_path):
    csv_path = tmp_path / "computers.csv"
    json_path = tmp_path / "computers.json"
    _write_legacy_csv(csv_path)

    storage.migrate_csv_if_present(json_path=json_path, csv_path=csv_path)

    computers = storage.load_computers(path=json_path)
    assert len(computers) == 2

    xeon = computers[0]
    assert xeon["computer_name"] == "XEON"
    assert xeon["created_at"] == "2026-04-07T15:24:26"
    assert xeon["cpu"]["model"] == "intel xeon"
    assert xeon["ram"]["capacity_gb"] == 64           # "64gb" parses to a number
    assert xeon["ram"]["configuration"] == ""
    assert xeon["gpu"]["model"] == "quadro p4000"
    assert xeon["storage"] == [{
        "manufacturer": "", "model": "kingston nvme 500gb",
        "type": "", "capacity": "", "form_factor": "",
    }]
    assert xeon["motherboard"]["model"] == "dell precision 3630"
    assert xeon["psu"]["model"] == "stock"
    assert xeon["notes"] == "main workstation"

    textram = computers[1]
    assert textram["ram"]["capacity_gb"] is None      # "dual channel" has no number
    assert textram["ram"]["configuration"] == "dual channel"
    assert textram["storage"] == []                   # blank storage -> no drives


def test_migration_is_noop_when_json_exists(tmp_path):
    csv_path = tmp_path / "computers.csv"
    json_path = tmp_path / "computers.json"
    _write_legacy_csv(csv_path)
    storage.save_computers([], path=json_path)        # JSON already present

    storage.migrate_csv_if_present(json_path=json_path, csv_path=csv_path)

    assert storage.load_computers(path=json_path) == []  # untouched


def test_migration_backs_up_csv(tmp_path):
    csv_path = tmp_path / "computers.csv"
    json_path = tmp_path / "computers.json"
    _write_legacy_csv(csv_path)

    storage.migrate_csv_if_present(json_path=json_path, csv_path=csv_path)

    assert not csv_path.exists()
    assert (tmp_path / "computers.csv.bak").exists()
