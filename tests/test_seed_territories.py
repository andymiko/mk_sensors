from scripts.seed_territories import DISTRICTS, DIVISIONS, OBJECT_DISTRICTS


def test_catalog_contains_expected_territories():
    assert len(DIVISIONS) == 12
    assert len(DISTRICTS) == 10
    assert all(len(division_codes) == 2 for _, division_codes in DISTRICTS.values())
    assert DISTRICTS["presnenskiy"][0] == "Пресненский"
    assert "operations-presnenskiy" in DISTRICTS["presnenskiy"][1]


def test_object_mapping_contains_all_requested_objects():
    assert len(OBJECT_DISTRICTS) == 19
    assert OBJECT_DISTRICTS[5333] == "tverskoy"
    assert OBJECT_DISTRICTS[4610] == "krasnoselskiy"
    assert OBJECT_DISTRICTS[3388] == "zamoskvorechye"
    assert set(OBJECT_DISTRICTS.values()).issubset(DISTRICTS)
