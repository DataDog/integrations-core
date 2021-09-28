from flask import Flask, request

app = Flask('Xenserver Test')
base_path = '/usr/share/responses'


@app.route("/rrd_updates", methods=["GET"])
def rrd_updates():
    f = open(base_path + '/rrd_updates.json', 'r')
    return f.read()


@app.route("/host_rrd", methods=["GET"])
def host_rrd():
    f = open(base_path + '/host_rrd.json', 'r')

    return f.read()


@app.route("/RPC2", methods=["POST"])
def rpc2():
    next_path = ''
    if "session.login_with_password" in str(request.data):
        next_path = '/xmlrpc_login.xml'
    elif "session.get_this_host" in str(request.data):
        next_path = '/xmlrpc_get_host.xml'
    elif "host.get_software_version" in str(request.data):
        next_path = '/xmlrpc_version.xml'
    elif "session.logout" in str(request.data):
        next_path = '/xmlrpc_logout.xml'

    f = open(base_path + next_path, 'r')

    return f.read()


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
