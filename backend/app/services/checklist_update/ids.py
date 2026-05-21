import uuid


_PREFIX_BY_COMPONENT_TYPE: dict[str, str] = {
    "section": "sec_",
    "textField": "field_",
    "numberField": "field_",
    "checkboxGroup": "group_",
    "checkbox": "check_",
    "table": "table_",
    "imageBlock": "image_",
}


def generate_component_id(component_type: str) -> str:
    prefix = _PREFIX_BY_COMPONENT_TYPE.get(component_type, "cmp_")
    return f"{prefix}{uuid.uuid4().hex[:12]}"
