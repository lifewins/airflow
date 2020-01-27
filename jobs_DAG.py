import uuid
import logging
from datetime import datetime, timedelta

from airflow import DAG
from airflow.hooks.postgres_hook import PostgresHook
from airflow.models import Variable
from airflow.operators.bash_operator import BashOperator
from airflow.operators.postgres_sql_count_rows_operator import PostgreSQLCountRowsOperator
from airflow.operators.python_operator import BranchPythonOperator
from airflow.operators.python_operator import PythonOperator
from airflow.utils.trigger_rule import TriggerRule

ex_file = Variable.get('ex_file', default_var='/Users/arazdolskiy/Development/airflow/tmp/ex.txt')

log = logging.getLogger(__name__)


default_args = {
    'owner': 'AndrewR',
    'start_date': datetime(2020, 1, 24),
    'database': "jdbc:pgsql/localhost:4567",
    'email_on_retry': False,
    'email_on_failure': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=1),
    'catchup': False,
    'priority_weight': 150,
    'table_name': 'uct_cust'
}

config = {
    'andrewR_m_1': {
        'schedule_interval': "@once",
        "start_date": datetime(2019, 11, 7),
        "db_table": "table_task_1"
    },
    'andrewR_h_2': {
        'schedule_interval': "@once",
        "start_date": datetime(2019, 11, 7),
        "db_table": "table_task_2"

    },
    'andrewR_d_3': {
        'schedule_interval': "@once",
        "start_date": datetime(2019, 11, 7),
        "db_table": "table_task_3"
    }
}


def print_start_message(**kwargs):
    print("{} start processing tables in database: {}".format(kwargs["dag_id"], kwargs["database"]))


def check_table_exists(check_table_exists_sql):
    print("checking sql={}".format(check_table_exists_sql))
    hook = PostgresHook()
    records = hook.get_first(check_table_exists_sql)
    if records is None:
        return "create_table"
    else:
        return "skip_table_creation"


def create_table(create_table_sql):
    hook = PostgresHook()
    hook.run(create_table_sql, autocommit=True)


def insert_record(insert_user_sql, **kwargs):
    hook = PostgresHook()
    task_instance = kwargs['task_instance']
    user = task_instance.xcom_pull(task_ids="get_user", key="user")
    if user is None:
        log.info("Generating new user id as in XCOM the user is not found")
        user = str(uuid.uuid4())
    else:
        log.info("From XCOM get user={}".format(user))
    hook.run(insert_user_sql.format(user), autocommit=True)
    file = open(kwargs['ex_file'], 'w')
    file.write(kwargs['ts'])
    file.close()


def _get_user(**kwargs):
    task_instance = kwargs['task_instance']
    task_instance.xcom_push(key="user", value=str(uuid.uuid4()))


def query_the_table_create_ts_file(select_sql, **kwargs):
    task_instance = kwargs['task_instance']
    task_instance.xcom_push(key="execution_ext", value=kwargs['ts'])

    # hook = PostgresHook()
    # count = hook.get_first(select_sql)
    # task_instance.xcom_push(key="results", value=count[0])
    #print("Records count=" + str(count[0]))


def createDag(dagId, config, default_args):
    dag_ID = 'dag_{}_{}'.format(dagId, config[dagId]['db_table'])
    dag = DAG(dag_id=dag_ID,
              default_args=default_args,
              start_date=config[dagId]["start_date"],
              schedule_interval=config[dagId]["schedule_interval"])

    with dag:
        say_hello = PythonOperator(
            task_id="print_log_{}".format(dagId),
            python_callable=print_start_message,
            op_kwargs={"dag_id": dag_ID, "database": default_args["database"]}
        )

        get_user = PythonOperator(
            task_id="get_user",
            python_callable=_get_user,
            provide_context=True
        )

        checkTable = BranchPythonOperator(
            task_id="checkTable",
            python_callable=check_table_exists,
            op_args=[
                "SELECT tablename FROM pg_tables t where t.tablename='{}' and t.tableowner='airflow' ;".format(
                    default_args['table_name'])
            ]
        )
        insert_new_row = PythonOperator(
            task_id="inset_new_row_{}".format(dag_ID),
            python_callable=insert_record,
            trigger_rule=TriggerRule.ONE_SUCCESS,
            provide_context=True,
            op_args=[
                "INSERT INTO {} VALUES('{}', '{}', '{}');".format(default_args['table_name'],
                                                                  uuid.uuid4().int % 123456789, '{}', datetime.now())
            ],
            op_kwargs={'run_id': "{{ run_id }} ended", 'ts': "{{ ts }}", 'ex_file': ex_file}
        )
        skip_table_creation = BashOperator(
            task_id="skip_table_creation",
            bash_command="echo 'skip table creation' "
        )
        create_table_op = PythonOperator(
            task_id="create_table",
            python_callable=create_table,
            op_args=[
                "CREATE TABLE {} (custom_id integer NOT NULL,"
                "user_name VARCHAR (50) NOT NULL, timestamp TIMESTAMP NOT NULL default current_timestamp) ;"
                    .format(default_args['table_name'])
            ]
        )

        # query_the_table_op = PythonOperator(
        #     task_id="query_the_table",
        #     python_callable=query_the_table_create_ts_file,
        #     provide_context=True,
        #     op_args=[
        #         "SELECT COUNT(*) FROM {}".format(default_args['table_name'])
        #     ],
        #     op_kwargs={'run_id': "{{ run_id }} ended", 'ts': "{{ ts }}", 'ex_file': ex_file}
        # )
        #
        query_the_table = PostgreSQLCountRowsOperator(
            task_id="query_the_table",
            sql="SELECT COUNT(*) FROM {}".format(default_args['table_name']),
            save_in_context=True,
            context_key="results",
            provide_context=True
        )

    say_hello >> get_user >> checkTable >> [skip_table_creation, create_table_op] >> insert_new_row >> query_the_table

    return dag


for dagId in config:
    dag_ID = 'dag_{}_{}'.format(dagId, config[dagId]['db_table'])
    globals()[dag_ID] = createDag(dagId, config, default_args)
