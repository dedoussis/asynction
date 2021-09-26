import json
from importlib.resources import read_text
from pathlib import Path
from typing import Callable
from typing import Text
from typing import Union

from flask import Blueprint
from flask import Response
from flask import jsonify
from flask import render_template_string

from asynction.types import AsyncApiSpec

from . import templates

View = Callable[[], Union[Text, Response]]


def make_html_rendered_docs_view(spec: AsyncApiSpec) -> View:
    template_string = read_text(templates, "index.html.j2")

    return lambda: render_template_string(
        source=template_string, schema=json.dumps(spec.to_dict()), info=spec.info
    )


def make_raw_spec_view(spec: AsyncApiSpec) -> View:
    return lambda: jsonify(spec.to_dict())


def make_docs_blueprint(spec: AsyncApiSpec, url_prefix: Path) -> Blueprint:
    bp = Blueprint("asynction_docs", __name__, url_prefix=str(url_prefix))
    bp.add_url_rule("/docs", "html_rendered_docs", make_html_rendered_docs_view(spec))
    bp.add_url_rule(
        "/docs/asyncapi.json", "raw_specification", make_raw_spec_view(spec)
    )

    return bp
