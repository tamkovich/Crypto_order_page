from gevent import monkey

monkey.patch_all()

from app import app, socketio

socketio.run(app, '0.0.0.0', 5000, debug=True)
