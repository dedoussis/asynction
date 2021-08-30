from ipaddress import IPv4Address
from unittest.mock import patch
from uuid import uuid4

from faker import Faker
from hypothesis.strategies import sampled_from
from hypothesis.strategies._internal.strategies import SearchStrategy
from hypothesis_jsonschema._from_schema import STRING_FORMATS

from asynction.mock_server import generate_fake_data_from_schema
from asynction.mock_server import make_faker_formats


def test_make_faker_formats_with_non_positive_sample_size(faker: Faker):
    assert make_faker_formats(faker, 0) == {}


def test_make_fkr_formats_with_positive_sample_size_gives_strategies_of_str_providers(
    faker: Faker,
):
    sample_size = faker.pyint(min_value=2, max_value=6)
    with patch.object(
        faker, "first_name", return_value=faker.pystr()
    ) as first_name_mock:
        with patch.object(
            faker, "last_name", return_value=faker.pyint()
        ) as last_name_mock:

            custom_formats = make_faker_formats(faker, sample_size)

            # Extra call is theere to check the provider return type
            assert first_name_mock.call_count == sample_size + 1

            # Providers that do not generate str values should not be included
            assert last_name_mock.call_count == 1
            assert "lase_name" not in custom_formats

            for format_name, strategy in custom_formats.items():
                assert format_name not in Faker.generator_attrs
                assert hasattr(faker, format_name)

                # Providers that match pre-existing default JSONSchema formats
                # should not be included:
                assert format_name not in STRING_FORMATS

                assert isinstance(strategy, SearchStrategy)


def test_generate_fake_data_from_schema_str():
    fake_data = generate_fake_data_from_schema({"type": "string"}, custom_formats={})
    assert isinstance(fake_data, str)


def test_generate_fake_data_from_schema_number():
    fake_data = generate_fake_data_from_schema({"type": "number"}, custom_formats={})
    assert isinstance(fake_data, (int, float))


def test_generate_fake_data_from_schema_dict():
    fake_data = generate_fake_data_from_schema(
        {
            "type": "object",
            "properties": {"foo": {"type": "string"}, "bar": {"type": "boolean"}},
            "required": ["foo", "bar"],
        },
        custom_formats={},
    )
    assert isinstance(fake_data, dict)

    assert "foo" in fake_data
    assert isinstance(fake_data["foo"], str)
    assert "bar" in fake_data
    assert isinstance(fake_data["bar"], bool)


def test_generate_fake_data_from_schema_using_default_format():
    fake_data = generate_fake_data_from_schema(
        {"type": "string", "format": "ipv4"}, custom_formats={}
    )
    fake_ip = IPv4Address(fake_data)
    assert isinstance(fake_ip, IPv4Address)


def test_generate_fake_data_from_schema_using_custom_formats(faker: Faker):
    custom_format_name = str(uuid4())
    fake_value = str(uuid4())
    custom_formats = {custom_format_name: sampled_from([fake_value])}

    for _ in range(faker.pyint(min_value=3, max_value=10)):
        fake_data = generate_fake_data_from_schema(
            {"type": "string", "format": custom_format_name},
            custom_formats=custom_formats,
        )
        assert fake_data == fake_value
