from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import BranchPythonOperator
from airflow.operators.python_operator import PythonOperator
from airflow.utils.trigger_rule import TriggerRule

default_args = {
    'owner': 'AndrewR',
    'start_date': datetime(2019, 11, 7),
    'database': "jdbc:pgsql/localhost:4567",
    'email_on_retry': False,
    'email_on_failure': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=1),
    'catchup': False
}

config = {
    'andrewR_m_1': {
        'schedule_interval': "@hourly",
        "start_date": datetime(2019, 11, 7),
        "db_table": "table_task_1"
    },
    'andrewR_h_2': {
        'schedule_interval': "@hourly",
        "start_date": datetime(2019, 11, 7),
        "db_table": "table_task_2"

    },
    'andrewR_d_3': {
        'schedule_interval': "@daily",
        "start_date": datetime(2019, 11, 7),
        "db_table": "table_task_3"
    }
}


def printDagTask1Str(*args, **kargs):
    print("{} start processing tables in database: {}".format(kargs["dag_id"], kargs["database"]))


def check_table_exists():
    if True:
        return "skip_table_creation"
    else:
        return "create_table"


def createDag(dagId, config, default_args):
    dag_ID = 'dag_{}_{}'.format(dagId, config[dagId]['db_table'])
    dag = DAG(dag_id=dag_ID,
              default_args=default_args,
              start_date=config[dagId]["start_date"],
              schedule_interval=config[dagId]["schedule_interval"])
    with dag:
        say_hello = PythonOperator(
            task_id="print_log_{}".format(dagId),
            python_callable=printDagTask1Str,
            op_kwargs={"dag_id": dag_ID, "database": default_args["database"]},
        )
        inset_new_row = DummyOperator(
            task_id="inset_new_row_{}".format(dag_ID),
            trigger_rule=TriggerRule.ALL_DONE
        )
        query_the_table = DummyOperator(
            task_id="query_the_table_{}".format(dag_ID)
        )
        checkTable = BranchPythonOperator(
            task_id="checkTable",
            python_callable=check_table_exists,
        )
        skip_table_creation = BashOperator(
            task_id="skip_table_creation",
            bash_command=" echo 'skip table creation' "
        )
        create_table = BashOperator(
            task_id="create_table",
            bash_command=" echo 'create table' "
        )

        print_user = BashOperator(
            task_id="print_user",
            bash_command='echo "$USER" '
        )

        say_hello >> print_user >> checkTable >> [skip_table_creation, create_table] >> inset_new_row >> query_the_table

    return dag


for dagId in config:
    dag_ID = 'dag_{}_{}'.format(dagId, config[dagId]['db_table'])
    globals()[dag_ID] = createDag(dagId, config, default_args)
