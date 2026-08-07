import pytest 
from repro.docker.runner import parse_port_spec, InvalidPortError

def test_single_port_maps_to_itself():
    assert parse_port_spec("3000") == (3000, 3000)

def test_host_container_mapping():
    assert parse_port_spec("8080:3000") == (8080, 3000)

def test_rejects_non_numeric_port():
    with pytest.raises(InvalidPortError):
        parse_port_spec("abc")

def test_rejects_port_out_of_range_high():
    with pytest.raises(InvalidPortError):
        parse_port_spec("99999")

def test_rejects_port_zero():
    with pytest.raises(InvalidPortError):
        parse_port_spec("0")

def test_rejects_malformed_spec_too_many_colons():
    with pytest.raises(InvalidPortError):
        parse_port_spec("1:2:3")

def test_rejects_empty_string():
    with pytest.raises(InvalidPortError):
        parse_port_spec("")

def test_accepts_boundary_port_1():
    assert parse_port_spec("1") == (1, 1)

def test_accepts_boundary_port_65535():
    assert parse_port_spec("65535") == (65535, 65535)