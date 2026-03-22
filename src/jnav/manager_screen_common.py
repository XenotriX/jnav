from rich.text import Text


def list_option_prompt(label: str, enabled: bool, combine: str = "and") -> Text:
    marker = "\u2713" if enabled else " "
    style = "" if enabled else "dim"
    prefix = "OR " if combine == "or" else "   "
    return Text.assemble(
        (prefix, "italic" if combine == "or" else "dim"),
        (f"{marker} ", style),
        (label, style),
    )
