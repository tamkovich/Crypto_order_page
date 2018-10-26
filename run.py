from gevent import monkey

from app import app, socketio

monkey.patch_all()
socketio.run(app, '0.0.0.0', 5000, debug=True)
