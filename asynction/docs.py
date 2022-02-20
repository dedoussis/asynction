from flask import Blueprint
from flask import Flask
from flask import current_app
from flask import jsonify
from flask import render_template

from asynction.types import AsyncApiSpec

blueprint = Blueprint("asynction_docs", __name__, template_folder="templates")


def current_spec(app: Flask) -> AsyncApiSpec:
    return app.config["ASYNCAPI_SPEC_OBJ"]


def set_current_spec(app: Flask, spec: AsyncApiSpec) -> None:
    app.config["ASYNCAPI_SPEC_OBJ"] = spec


@blueprint.route("/docs")
def html_view():
    spec = current_spec(current_app)
    return render_template(
        "index.html.j2",
        schema=spec.to_dict(),
        info=spec.info,
    )


@blueprint.route("/docs/asyncapi.json")
def json_view():
    spec = current_spec(current_app)
    return jsonify(spec.to_dict())
