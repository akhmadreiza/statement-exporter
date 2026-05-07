from .jenius import JeniusParser

# Maps filename prefix (lowercase) to parser class.
# To add a new bank, create parsers/<bank>.py and register it here.
REGISTRY: dict[str, type] = {
    'jenius': JeniusParser,
}


def get_parser(pdf_path: str):
    filename = pdf_path.split('/')[-1].lower()
    for prefix, parser_cls in REGISTRY.items():
        if filename.startswith(prefix):
            return parser_cls()
    return None
