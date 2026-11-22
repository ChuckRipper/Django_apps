from django import template

register = template.Library()


@register.filter
def pole_bs(pole):
    """Renderuje pole formularza z klasą Bootstrapa (bez |safe na danych użytkownika)."""
    widget = pole.field.widget
    typ = getattr(widget, "input_type", "")
    if typ == "checkbox":
        klasa = "form-check-input"
    elif typ == "radio":
        klasa = "form-check-input"
    elif widget.__class__.__name__ == "Select":
        klasa = "form-select"
    else:
        klasa = "form-control"
    if pole.errors:
        klasa += " is-invalid"
    return pole.as_widget(attrs={"class": klasa})
