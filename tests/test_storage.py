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
