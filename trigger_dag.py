from datetime import datetime

from airflow import DAG
from airflow.contrib.sensors.file_sensor import FileSensor
from airflow.models import Variable
from airflow.operators.bash_operator import BashOperator
from airflow.operators.dagrun_operator import TriggerDagRunOperator

dags = ["dag_andrewR_m_1_table_task_1", "dag_andrewR_h_2_table_task_2", "dag_andrewR_d_3_table_task_3"]

dagToCall = 'weekdayJobs'

default_args = {
    'dagToCall': dagToCall,
    'run_file': '/Users/arazdolskiy/Development/airflow/tmp/run',
    'owner': 'AndrewR',
    'start_date': datetime(2019, 11, 15),
    'catchup': False,
    'concurrency': 1,
    'depends_on_past': True
}

path = Variable.get('run_file', default_var=default_args['run_file'])
dag = DAG(
    dag_id="calling_dag",
    schedule_interval="@daily",
    default_args=default_args,
)

with dag:
    check_run_file = FileSensor(
        task_id="check_run_file",
        poke_interval=1,
        default_args=default_args,
        filepath=path
    )
    trigger_task_1 = TriggerDagRunOperator(
        task_id="trigger_task_0",
        trigger_dag_id=default_args['dagToCall']
    )

    remove_run_file = BashOperator(
        task_id="remove_run_file",
        bash_command="rm -f {}".format(path)
    )

    check_run_file >> trigger_task_1 >> remove_run_file
