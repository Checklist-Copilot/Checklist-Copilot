from app.schemas.checklist_operations import AddComponentOperation
from app.services.checklist_update.add.checkbox_group import add_checkbox_group
from app.services.checklist_update.add.checkbox_item import add_checkbox_item
from app.services.checklist_update.add.image_block import add_image_block
from app.services.checklist_update.add.number_field import add_number_field
from app.services.checklist_update.add.section import add_section
from app.services.checklist_update.add.table import add_table
from app.services.checklist_update.add.text_field import add_text_field
from app.services.checklist_update.exceptions import UnsupportedComponentTypeError


def dispatch_add_component(checklist: dict, operation: AddComponentOperation) -> dict:
    component = operation.component
    component_type = component.get("type") if isinstance(component, dict) else component.type

    if component_type == "section":
        return add_section(checklist, operation)
    if component_type == "textField":
        return add_text_field(checklist, operation)
    if component_type == "numberField":
        return add_number_field(checklist, operation)
    if component_type == "checkboxGroup":
        return add_checkbox_group(checklist, operation)
    if component_type == "checkbox":
        return add_checkbox_item(checklist, operation)
    if component_type == "table":
        return add_table(checklist, operation)
    if component_type == "imageBlock":
        return add_image_block(checklist, operation)

    raise UnsupportedComponentTypeError(f"Unsupported component type: {component_type}")
