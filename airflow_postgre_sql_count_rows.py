import logging

from airflow.hooks.postgres_hook import PostgresHook
from airflow.models import BaseOperator
from airflow.plugins_manager import AirflowPlugin

log = logging.getLogger(__name__)


class PostgreSQLCountRowsOperator(BaseOperator):

    def __init__(self, sql, save_in_context, context_key, *args, **kwargs):
        super(PostgreSQLCountRowsOperator, self).__init__(*args, **kwargs)
        self.sql = sql
        self.save_in_context = save_in_context
        self.context_key = context_key

    def execute(self, context):
        hook = PostgresHook()
        result = hook.get_first(self.sql)
        if (self.save_in_context):
            if result:
                context["task_instance"].xcom_push(key=self.context_key, value=result[0])
                log.info("saved in context result={}", format(result))
            else:
                raise ValueError("Cannot get value using sql={}".format(self.sql))


# Defining the plugin class
class PostgreSQLCountRowsOperatorPlugin(AirflowPlugin):
    name = "postgres_sql_count_rows_operator"
    operators = [PostgreSQLCountRowsOperator]
