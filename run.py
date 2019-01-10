from gevent import monkey

monkey.patch_all()

from app import app, socketio, config

socketio.run(app, config['app']['host'], config['app']['port'], debug=False)
