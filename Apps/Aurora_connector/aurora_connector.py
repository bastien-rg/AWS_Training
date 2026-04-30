import traceback
import boto3
import psycopg2
import asyncio
import logging
from nicegui import ui

APP_VERSION="v0.5"

DB_IDENTIFIERS = ["aurora-sandbox.cluster-cnsksca2iibu", "aurora-sandbox-instance-1.cnsksca2iibu", "aurora-sandbox-reader1.cnsksca2iibu" ]

AWS_REGION = 'ap-northeast-1'
DB_PORT = 5432
DB_NAME = 'postgres'
DB_USER = 'myaurora'
SSL_CERT = './global-bundle.pem'

from nicegui import ui

class LogElementHandler(logging.Handler):
    """A logging handler that emits messages to a log element."""

    def __init__(self, element: ui.log, level: int = logging.NOTSET) -> None:
        self.element = element
        super().__init__(level)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            self.element.push(msg)
        except Exception:
            self.handleError(record)

@ui.page("/")
def main_page():
    # User env
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    DB_CONN = None

    # Layout
    with ui.card().classes("w-full"):
        with ui.grid(columns=12).classes("w-full"):
            # Title block
            with ui.column().classes("col-span-full gap-0"):
                ui.label("Aurora Experiment Dashboard").classes("text-xl font-semibold")
                ui.label(APP_VERSION).classes("text-sm text-gray-400")

            connect_btn = ui.button("Connect to Aurora").classes("col-span-4")
            disconnect_btn = ui.button("Disconnect").classes("col-span-4")
            db_identifier_select = ui.select(options=DB_IDENTIFIERS, label="DB identifier", value=DB_IDENTIFIERS[0]).classes("col-span-4")
            log_box = ui.log(max_lines=50).classes("col-span-full bg-gray-700 text-white").style("font-size: 10px")

    # Post-layout setup        
    log_handler = LogElementHandler(log_box)
    logger.addHandler(log_handler)

    # Functions
    def get_db_host():
        return db_identifier_select.value + "." + AWS_REGION + ".rds.amazonaws.com"

    async def try_connect():
        """
        Attempt Aurora connection. Returns (success, message).
        Fargate needs to be launched with IAM role that allows IAM authentication to Aurora.
        Doing so, AWS will setup the env variable AWS_CONTAINER_CREDENTIALS_RELATIVE_URI that
        boto3 will use to fetch a 15-min utilizable auth token.
        """
        nonlocal DB_CONN
        def blocking_connect() -> tuple[bool, str]:
            DB_HOST = get_db_host()
            print(f"DB HOST IS {DB_HOST}")
            try:
                auth_token = boto3.client('rds', region_name=AWS_REGION).generate_db_auth_token(
                    DBHostname=DB_HOST,
                    Port=DB_PORT,
                    DBUsername=DB_USER,
                    Region=AWS_REGION,
                )
                log_box.push("Connecting with obtained token (timeout=60s)", classes="text-orange")
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

                return True, version, conn
            
            except Exception:
                stack = traceback.format_exc()
                print(f"Error! {stack}")
                return False, stack, None
        
        status, msg, conn = await asyncio.get_event_loop().run_in_executor(None, blocking_connect)
        if status:
            log_box.push("Connected! "+msg, classes="text-green")
            DB_CONN = conn
            connect_btn.disable()
            disconnect_btn.enable()
        else:
            log_box.push("Connection failed", classes="text-red")
            connect_btn.enable()

    def disconnect_db():
        nonlocal DB_CONN
        if DB_CONN:
            DB_CONN.close()
            DB_CONN = None
            disconnect_btn.disable()
            connect_btn.enable()

    # Post function definition setup
    connect_btn.on_click(try_connect)
    disconnect_btn.on_click(disconnect_db)
    disconnect_btn.disable()
    ui.context.client.on_disconnect(lambda: logger.removeHandler(log_handler))

    # CSS
    ui.dark_mode().enable()
    ui.colors(
        primary="#1f3a5f",
        secondary="#2b6cb0",
        accent="#4dabf7", 

        positive="#4caf50",
        warning="#ff9800",
        negative="#f44336",
        info="#29b6f6", 
    )

# NiceGUI start
ui.run(title="Aurora sandbox", host="0.0.0.0", port=8765)