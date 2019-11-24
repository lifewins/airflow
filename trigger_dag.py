from datetime import datetime

from airflow import DAG
from airflow.contrib.sensors.file_sensor import FileSensor
from airflow.models import Variable
from airflow.operators.bash_operator import BashOperator
from airflow.operators.dagrun_operator import TriggerDagRunOperator
from airflow.operators.python_operator import PythonOperator
from airflow.operators.subdag_operator import SubDagOperator
from airflow.sensors.external_task_sensor import ExternalTaskSensor

dagToCall = 'dag_andrewR_m_1_table_task_1'

main_dag_id = "calling_dag"
default_path = '/Users/arazdolskiy/Development/airflow/tmp/'

default_args = {
    'dagToCall': dagToCall,
    'run_file': default_path + 'run',
    'owner': 'AndrewR',
    'start_date': datetime(2019, 11, 17),
    'catchup': False,
    'concurrency': 1,
    'depends_on_past': False,
    'priority_weight': 100
}

path = Variable.get('run_file', default_var=default_args['run_file'])
ex_file = Variable.get('ex_file', default_var='/Users/arazdolskiy/Development/airflow/tmp/ex.txt')


def print_ext_result(*kargs, **kwargs):
    task_instance = kwargs['task_instance']
    results = task_instance.xcom_pull(dag_id=dagToCall, task_ids="query_the_table", key='results')
    print("'{}' dag result={}".format(dagToCall, results))
    print(kwargs)


def exec_delta(this_dag_scheduled_date):
    print("Master DAG scheduled date={}".format(this_dag_scheduled_date))
    date_str = ""
    try:
        file = open(ex_file, 'r')
        date_str = file.readline(1)
        ex_date = datetime.fromisoformat(date_str)
        file.close()
        print("Slave DAG scheduled date={}".format(ex_date))
        return ex_date
    except:
        print("Wrong date={} in file={}".format(date_str, ex_file))


def build_process_result_sub_dag(main_dag, default_args):
    s_dag = DAG(
        dag_id="{}.{}".format(main_dag, 'process_result_sub_dag'),
        default_args=default_args,
        schedule_interval='@daily'
    )

    external_dag_sensor = ExternalTaskSensor(
        task_id='external_dag_sensor',
        external_dag_id=dagToCall,
        external_task_id='None',
        execution_date_fn=exec_delta,
        dag=s_dag
    )
    ex_file_sensor = FileSensor(
        task_id="ex_file_sensor",
        filepath=ex_file,
        dag=s_dag
    )
    print_external_dag_result = PythonOperator(
        task_id="print_external_dag_result",
        python_callable=print_ext_result,
        provide_context=True,
        dag=s_dag
    )
    remove_trigger_file = BashOperator(
        task_id="remove_trigger_file",
        bash_command="rm -f {}".format(path),
        dag=s_dag
    )
    create_finished_file = BashOperator(
        task_id="create_finished_file",
        bash_command="touch " + default_path + "finished_#{{ ts_nodash }}",
        dag=s_dag
    )

    ex_file_sensor >> external_dag_sensor >> print_external_dag_result >> remove_trigger_file >> create_finished_file
    return s_dag


# main dag
main_dag = DAG(
    dag_id=main_dag_id,
    default_args=default_args,
    schedule_interval='@daily'
)

remove_ex_file = BashOperator(
    task_id="remove_ex_file",
    bash_command="rm -f {}".format(ex_file),
    dag=main_dag
)

check_run_file = FileSensor(
    task_id="check_run_file",
    poke_interval=1,
    filepath=path,
    dag=main_dag
)

triggering_external_dag = TriggerDagRunOperator(
    task_id="triggering_external_dag",
    trigger_dag_id=dagToCall,
    dag=main_dag
)

process_result_sub_dag = SubDagOperator(
    task_id='process_result_sub_dag',
    subdag=build_process_result_sub_dag(main_dag_id, default_args),
    dag=main_dag
)

remove_ex_file >> check_run_file >> triggering_external_dag >> process_result_sub_dag
