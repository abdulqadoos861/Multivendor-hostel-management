from django import template

register = template.Library()

@register.filter
def get_menu(menus, hostel_id):
    """
    Filter to get all menu items for a specific hostel.
    """
    return menus.filter(hostel_id=hostel_id)

@register.filter
def get_meal(menus, day, meal_type):
    """
    Filter to get menu items for a specific day and meal type.
    """
    try:
        return menus.get(day_of_week=day, meal_type=meal_type)
    except menus.model.DoesNotExist:
        return None
