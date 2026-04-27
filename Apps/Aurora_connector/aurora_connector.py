import traceback
import boto3
import psycopg2
from nicegui import ui
 
DB_HOST = 'sandbox-auroradb-instance-1.cnsksca2iibu.ap-northeast-1.rds.amazonaws.com'
DB_PORT = 5432
DB_NAME = 'postgres'
DB_USER = 'myaurora'
AWS_REGION = 'ap-northeast-1'
SSL_CERT = './global-bundle.pem'



@ui.page("/")
def main_page():
    # Client variable
    connection_result = { "status": ""}

    # Functions
    def try_connect():
        """
        Attempt Aurora connection. Returns (success, message).
        Fargate needs to be launched with IAM role that allows IAM authentication to Aurora.
        Doing so, AWS will setup the env variable AWS_CONTAINER_CREDENTIALS_RELATIVE_URI that
        boto3 will use to fetch a 15-min utilizable auth token.
        """
        print("Connecting to Aurora...")
        conn = None
        try:
            auth_token = boto3.client('rds', region_name=AWS_REGION).generate_db_auth_token(
                DBHostname=DB_HOST,
                Port=DB_PORT,
                DBUsername=DB_USER,
                Region=AWS_REGION,
            )
            conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                database=DB_NAME,
                user=DB_USER,
                password=auth_token,
                sslmode='verify-full',
                sslrootcert=SSL_CERT,
            )
            conn.autocommit = True
            cur = conn.cursor()
            cur.execute('SELECT version();')
            version = cur.fetchone()[0]
            cur.close()
            print(f"Success, version={version}")

            connection_result["status"] = version
        except Exception:
            stack = traceback.format_exc()
            print(f"Error! {stack}")
            connection_result["status"] = stack
        finally:
            if conn:
                conn.close()

    # Layout
    with ui.card():
        ui.button("Connect", on_click=try_connect)
        ui.label().bind_text_from(connection_result, "status")


# NiceGUI start
ui.run(title="Aurora sandbox", port=8765)
# ui.run(title="Aurora sandbox", host="0.0.0.0", port=8765, reload=False)