# tests/test_dag_import.py
from pathlib import Path
from airflow.models.dagbag import DagBag


def test_evaluate_agent_dag_loads():
    dags_folder = str(Path(__file__).resolve().parents[1] / "dags")
    bag = DagBag(dag_folder=dags_folder, include_examples=False)
    assert bag.import_errors == {}, bag.import_errors
    dag = bag.get_dag("evaluate_agent")
    assert dag is not None
    assert set(dag.task_ids) == {"prepare_run", "run_agent", "run_eval", "summarize_and_log"}


def test_evaluate_agent_docker_dag_loads():
    dags_folder = str(Path(__file__).resolve().parents[1] / "dags")
    bag = DagBag(dag_folder=dags_folder, include_examples=False)
    assert bag.import_errors == {}, bag.import_errors
    dag = bag.get_dag("evaluate_agent_docker")
    assert dag is not None
    assert set(dag.task_ids) == {"prepare_run", "run_agent", "run_eval", "summarize_and_log"}
