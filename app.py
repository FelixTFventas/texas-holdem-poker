from flask import Flask

from routes.game_routes import game_bp


def create_app(testing: bool = False) -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = testing
    app.secret_key = "dev-secret-key"
    app.register_blueprint(game_bp)
    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
