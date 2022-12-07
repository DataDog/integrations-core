import os
from uuid import uuid4

from flask import Flask, abort, jsonify, request
from flask.cli import FlaskGroup

app = Flask('Avi Integration Tests')

USERS = {'user1': 'dummyPass'}

sessions = {}


@app.route("/login", methods=['POST'])
def login():
    username = request.values['username']
    password = request.values['password']

    if username not in USERS or USERS[username] != password:
        abort(403)

    session_id = str(uuid4())
    csrf_token = str(uuid4())
    sessions[session_id] = {'user': username, 'csrf_token': csrf_token}
    response = jsonify(hello="world")
    response.set_cookie('csrftoken', csrf_token)
    response.set_cookie('avi-sessionid', session_id)
    return response


@app.route("/logout", methods=['POST'])
def logout():
    session_id = request.cookies.get('avi-sessionid')
    if not session_id or session_id not in sessions:
        return "Session id missing or does not exist", 403

    session = sessions[session_id]
    csrf_token = request.headers.get('X-CSRFToken')
    if not csrf_token or csrf_token != session['csrf_token']:
        return "CSRF token missing or invalid", 403

    referer = request.headers.get('Referer')
    if referer is None:
        return "Referer header missing", 403

    del sessions[session_id]
    return '', 200


@app.route("/api/analytics/prometheus-metrics/<resource>")
def get_metrics(resource):
    session_id = request.cookies.get('avi-sessionid')
    if not session_id or session_id not in sessions:
        return "Session id missing or does not exist", 403

    file_path = os.path.join(os.path.dirname(__file__), 'fixtures', f'{resource}_metrics')
    if not os.path.isfile(file_path):
        return "Invalid resource", 404

    with open(file_path, 'r') as f:
        content = f.read()

    return content, 200


@app.route("/api/cluster/version")
def cluster_version():
    return jsonify(Version="20.1.5")


cli = FlaskGroup(app)


if __name__ == "__main__":
    cli()
