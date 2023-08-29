import os

from flask import Flask
from werkzeug.middleware.dispatcher import DispatcherMiddleware

from slurk.extensions import api as api_ext
from slurk.extensions import database as database_ext
from slurk.extensions import events as event_ext
from slurk.extensions import login as login_ext
from slurk.extensions import openvidu as openvidu_ext
from slurk.models import Token


def create_app(test_config=None, engine=None):
    from .config import API_TITLE, API_VERSION, OPENAPI_VERSION

    slurk_app = Flask(
        __name__,
        static_folder=os.path.join("views", "static"),
        template_folder=os.path.join("views", "templates"),
    )

    if not test_config:
        slurk_app.config.from_object("slurk.config")
    else:
        slurk_app.config.from_mapping(test_config)

        if "API_TITLE" not in slurk_app.config:
            slurk_app.config["API_TITLE"] = API_TITLE
        if "API_VERSION" not in slurk_app.config:
            slurk_app.config["API_VERSION"] = API_VERSION
        if "OPENAPI_VERSION" not in slurk_app.config:
            slurk_app.config["OPENAPI_VERSION"] = OPENAPI_VERSION

    if not engine and "DATABASE" not in slurk_app.config:
        raise ValueError(
            "Database URI not provided. Pass `SLURK_DATABASE_URI` as environment variable or define it in `config.py`."
        )
    if "SECRET_KEY" not in slurk_app.config:
        raise ValueError(
            "Secret key not provided. Pass `SLURK_SECRET_KEY` as environment variable or define it in `config.py`."
        )

    with slurk_app.app_context():
        event_ext.init_app(slurk_app)
        login_ext.init_app(slurk_app)
        openvidu_ext.init_app(slurk_app)  # NOQA
        api_ext.init_app(slurk_app)
        database_ext.init_app(slurk_app, engine)

        if slurk_app.config["DEBUG"]:
            admin_token = "00000000-0000-0000-0000-000000000000"
            if not slurk_app.session.query(Token).get(admin_token):
                Token.get_admin_token(database_ext.db, id=admin_token)
        else:
            admin_token = Token.get_admin_token(database_ext.db)
        print(f"admin token:\n{admin_token}", flush=True)

    app = DispatcherMiddleware(None, {
        '/gaelic': slurk_app
    })

    # The default slurk tests do not expect the subdirectory,
    # and they expect a structure that wrapping with DispatcherMiddleware breaks,
    # so we get rid of the Middleware for testing for now.
    # TODO create tests for the Middleware use case!
    if slurk_app.config['TESTING']:
        app = slurk_app

    return app
