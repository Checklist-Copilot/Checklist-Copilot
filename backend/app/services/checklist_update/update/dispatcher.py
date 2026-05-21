from app.schemas.checklist_operations import UpdateComponentOperation
from app.services.checklist_update.exceptions import ComponentNotFoundError, UnsupportedComponentTypeError
from app.services.checklist_update.tree_utils import find_component_by_id
from app.services.checklist_update.update.checkbox_group import update_checkbox_group
from app.services.checklist_update.update.checkbox_item import update_checkbox_item
from app.services.checklist_update.update.image_block import update_image_block
from app.services.checklist_update.update.number_field import update_number_field
from app.services.checklist_update.update.section import update_section
from app.services.checklist_update.update.table import update_table
from app.services.checklist_update.update.text_field import update_text_field


def dispatch_update_component(checklist: dict, operation: UpdateComponentOperation) -> dict:
    target = find_component_by_id(checklist, operation.targetId)
    if target is None:
        raise ComponentNotFoundError(f"Component not found: {operation.targetId}")

    component_type = target.get("type")
    if component_type == "section":
        return update_section(checklist, operation)
    if component_type == "textField":
        return update_text_field(checklist, operation)
    if component_type == "numberField":
        return update_number_field(checklist, operation)
    if component_type == "checkboxGroup":
        return update_checkbox_group(checklist, operation)
    if component_type == "checkbox":
        return update_checkbox_item(checklist, operation)
    if component_type == "table":
        return update_table(checklist, operation)
    if component_type == "imageBlock":
        return update_image_block(checklist, operation)

    raise UnsupportedComponentTypeError(f"Unsupported component type: {component_type}")
