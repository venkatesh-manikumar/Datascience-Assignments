import datetime
import os
from airflow import models
from airflow.operators.bash_operator import BashOperator
from airflow.contrib.operators import dataproc_operator
from airflow.contrib.operators.gcs_to_bq import GoogleCloudStorageToBigQueryOperator
from airflow.utils import trigger_rule


yesterday = datetime.datetime.combine(
    datetime.datetime.today() - datetime.timedelta(1),
    datetime.datetime.min.time())

default_dag_args = {
    'start_date': yesterday,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': datetime.timedelta(minutes=2),
    'project_id': models.Variable.get('gcp_project') #gcp_project
}

SPARK_CODE = ('gs://exercise-4-source-file/spark_code.py')
dataproc_job_name = 'spark_job_dataproc'

with models.DAG(
        'Codathon-Exercise-5',
        schedule_interval=datetime.timedelta(days=1),
        default_args=default_dag_args) as dag:
	
	print_date = BashOperator(
    task_id='print_date',
    bash_command='date'
    )
	
	
	
	create_dataproc = dataproc_operator.DataprocClusterCreateOperator(
		task_id='create_dataproc_cluster',
		cluster_name='composer-hadoop-tutorial-cluster-{{ ds_nodash }}',
		num_workers=2,
		region=models.Variable.get('dataproc_region'),
		zone=models.Variable.get('dataproc_zone'),
		image_version='2.0',
		master_machine_type='n1-standard-2',
		worker_machine_type='n1-standard-2',
		master_disk_size=30,
		worker_disk_size=30
		)
	
	GCS_Delete_Staging = BashOperator(
    task_id='Clearing_Staging_bucket', 
    bash_command='gsutil rm -r gs://dataproc-temp-us-central1-390371938153-n72uczea/staging/')
	
	run_spark = dataproc_operator.DataProcPySparkOperator(
	task_id='spark_code_execution',
	region=models.Variable.get('dataproc_region'),
	main=SPARK_CODE,
	cluster_name='composer-hadoop-tutorial-cluster-{{ ds_nodash }}',
	job_name=dataproc_job_name)
	
	delete_dataproc = dataproc_operator.DataprocClusterDeleteOperator(
    task_id='delete_dataproc_cluster',
    region=models.Variable.get('dataproc_region'),
    cluster_name='composer-hadoop-tutorial-cluster-{{ ds_nodash }}',
    trigger_rule=trigger_rule.TriggerRule.ALL_DONE)
	
	Bigquery_load = GoogleCloudStorageToBigQueryOperator(
    task_id = 'Bigquery_data_load',
    bucket = 'dataproc-temp-us-central1-390371938153-n72uczea',
    source_objects = ['staging/part-*'],
    destination_project_dataset_table = 'sparktobq.output_exercise2_covid_data_insights',
    source_format = 'NEWLINE_DELIMITED_JSON',
	create_disposition='CREATE_IF_NEEDED',
    write_disposition='WRITE_TRUNCATE',
    autodetect = True)
	
	GCS_Delete = BashOperator(
    task_id='GCS_Delete', 
    bash_command='gsutil rm  gs://dataproc-temp-us-central1-390371938153-n72uczea/staging/*')
	
	

	print_date >> create_dataproc >>  GCS_Delete_Staging >> run_spark >> delete_dataproc >> Bigquery_load >> GCS_Delete