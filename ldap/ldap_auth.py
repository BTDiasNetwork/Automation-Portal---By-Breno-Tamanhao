from ldap3 import Server, Connection, ALL
from flask import Flask, request, Response

app = Flask(__name__)

LDAP_SERVER = "10.100.250.10"
BASE_DN = "DC=dc,DC=corp"
SERVICE_USER = "PORTAL-AUTOMATION-LDAP@dc.corp"
SERVICE_PASSWORD = "abc123"

GROUP_DN = "CN=GA-Portal-Automation,OU=Admins,OU=Groups,OU=Datacenter,DC=dc,DC=corp"


@app.route("/auth")
def auth():
    auth = request.authorization
    if not auth:
        return Response(status=401)

    username = auth.username
    password = auth.password

    server = Server(LDAP_SERVER, get_info=ALL)
    conn = Connection(server, SERVICE_USER, SERVICE_PASSWORD, auto_bind=True)

    search_filter = f"(&(sAMAccountName={username})(memberOf={GROUP_DN}))"

    conn.search(BASE_DN, search_filter, attributes=["distinguishedName"])

    if not conn.entries:
        return Response(status=403)

    user_dn = conn.entries[0].entry_dn

    # Agora testa senha do usuário
    user_conn = Connection(server, user=user_dn, password=password)
    if not user_conn.bind():
        return Response(status=401)

    return Response(status=200)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9000)
