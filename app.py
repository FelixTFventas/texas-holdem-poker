from flask import Flask
from flask_socketio import SocketIO

from multiplayer.socket_events import register_socket_events
from routes.game_routes import game_bp


socketio = SocketIO(async_mode="threading", cors_allowed_origins="*")


def create_app(testing: bool = False) -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = testing
    app.secret_key = "dev-secret-key"
    app.register_blueprint(game_bp)
    socketio.init_app(app)
    register_socket_events(socketio)
    return app


app = create_app()


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True, allow_unsafe_werkzeug=True)
