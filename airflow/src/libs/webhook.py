"""Webhook-based task activation utilities for Airflow.

This module provides a generic way to implement webhook-activated tasks in Airflow DAGs.
Tasks can wait for external HTTP webhooks to trigger their execution.
"""
from typing import Optional, Any
from airflow.models import XCom, DagRun
from airflow.utils.session import provide_session
from airflow.sensors.base import BaseSensorOperator
from airflow.utils.context import Context
from sqlalchemy import desc


@provide_session
def get_latest_dag_run(dag_id: str, session=None) -> str:
    """Get the latest DAG run ID for a given DAG.
    
    Args:
        dag_id: The DAG ID to get the latest run for
        session: SQLAlchemy session (provided by @provide_session decorator)
    
    Returns:
        The run_id of the latest DAG run
    
    Raises:
        ValueError: If no DAG run is found
    """
    # Get the latest DAG run
    dag_run = (
        session.query(DagRun)
        .filter(DagRun.dag_id == dag_id)
        .order_by(desc(DagRun.execution_date))
        .first()
    )
    
    if not dag_run:
        raise ValueError("No active DAG run found. Please trigger the DAG first.")
    
    return dag_run.run_id


def set_webhook_signal(
    dag_id: str,
    task_id: str,
    run_id: str,
    data: Optional[Any] = None,
    signal_key: str = "webhook_triggered",
    data_key: str = "webhook_data"
) -> None:
    """Set a webhook signal in XCom to activate a waiting task.
    
    Args:
        dag_id: The DAG ID
        task_id: The task ID that is waiting for the webhook
        run_id: The DAG run ID
        data: Optional data to pass to the task (will be stored in XCom)
        signal_key: XCom key for the webhook trigger signal (default: "webhook_triggered")
        data_key: XCom key for the webhook data (default: "webhook_data")
    """
    @provide_session
    def _set_signal(session=None):
        # Set webhook_triggered flag
        XCom.set(
            key=signal_key,
            value=True,
            dag_id=dag_id,
            task_id=task_id,
            run_id=run_id,
            session=session
        )
        
        # Set webhook data if provided
        if data is not None:
            XCom.set(
                key=data_key,
                value=data,
                dag_id=dag_id,
                task_id=task_id,
                run_id=run_id,
                session=session
            )
        
        session.commit()
    
    _set_signal()


def check_webhook_signal(
    dag_id: str,
    task_id: str,
    run_id: str,
    signal_key: str = "webhook_triggered"
) -> bool:
    """Check if a webhook signal exists in XCom.
    
    Args:
        dag_id: The DAG ID
        task_id: The task ID to check
        run_id: The DAG run ID
        signal_key: XCom key for the webhook trigger signal (default: "webhook_triggered")
    
    Returns:
        True if webhook signal exists, False otherwise
    """
    @provide_session
    def _check_signal(session=None):
        xcom_entry = session.query(XCom).filter(
            XCom.dag_id == dag_id,
            XCom.run_id == run_id,
            XCom.task_id == task_id,
            XCom.key == signal_key
        ).first()
        return xcom_entry is not None
    
    return _check_signal()


def get_webhook_data(
    task_instance,
    target_task_id: str,
    dag_id: str,
    data_key: str = "webhook_data"
) -> Optional[Any]:
    """Get webhook data from XCom.
    
    Args:
        task_instance: The current task instance
        target_task_id: The task ID that received the webhook
        dag_id: The DAG ID
        data_key: XCom key for the webhook data (default: "webhook_data")
    
    Returns:
        The webhook data if available, None otherwise
    """
    return task_instance.xcom_pull(
        key=data_key,
        task_ids=target_task_id,
        dag_id=dag_id,
        include_prior_dates=True
    )


class WebhookSensor(BaseSensorOperator):
    """Generic sensor that waits for an HTTP webhook to trigger a task.
    
    This sensor polls XCom for a webhook signal. When the signal is detected,
    it retrieves any associated data and passes it to downstream tasks.
    
    Example:
        ```python
        wait_for_webhook = WebhookSensor(
            task_id="wait_for_webhook",
            target_task_id="my_task",
            poke_interval=5,
            timeout=3600,
            dag=dag
        )
        ```
    
    Attributes:
        target_task_id: The task ID that will receive the webhook signal
        signal_key: XCom key for the webhook trigger signal (default: "webhook_triggered")
        data_key: XCom key for the webhook data (default: "webhook_data")
        output_key: XCom key to store the webhook data for downstream tasks (default: "webhook_data")
    """
    
    def __init__(
        self,
        target_task_id: str,
        signal_key: str = "webhook_triggered",
        data_key: str = "webhook_data",
        output_key: str = "webhook_data",
        **kwargs
    ):
        """Initialize the WebhookSensor.
        
        Args:
            target_task_id: The task ID that will receive the webhook signal
            signal_key: XCom key for the webhook trigger signal
            data_key: XCom key for the webhook data
            output_key: XCom key to store the webhook data for downstream tasks
            **kwargs: Additional arguments passed to BaseSensorOperator
        """
        super().__init__(**kwargs)
        self.target_task_id = target_task_id
        self.signal_key = signal_key
        self.data_key = data_key
        self.output_key = output_key
    
    def poke(self, context: Context) -> bool:
        """Check if webhook has been triggered.
        
        Args:
            context: Airflow task context
            
        Returns:
            True if webhook signal is detected, False otherwise
        """
        task_instance = context['task_instance']
        dag_run = context['dag_run']
        
        # Check if webhook signal exists in XCom
        webhook_triggered = check_webhook_signal(
            dag_id=dag_run.dag_id,
            task_id=self.target_task_id,
            run_id=dag_run.run_id,
            signal_key=self.signal_key
        )
        
        if webhook_triggered:
            # Get webhook data if available
            webhook_data = get_webhook_data(
                task_instance=task_instance,
                target_task_id=self.target_task_id,
                dag_id=dag_run.dag_id,
                data_key=self.data_key
            )
            
            # Pass the data to downstream tasks
            context['ti'].xcom_push(key=self.output_key, value=webhook_data)
            return True
        
        return False

