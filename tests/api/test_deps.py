def test_get_hanflow_returns_stored_instance(app_and_hanflow):
    from hanflow.api.deps import get_hanflow

    app, hf = app_and_hanflow
    assert get_hanflow(app) is hf


def test_get_workflow_store_returns_store(app_and_hanflow):
    from hanflow.api.deps import get_workflow_store

    app, _ = app_and_hanflow
    store = get_workflow_store(app)
    assert store is not None
    # second call returns the same cached instance
    assert get_workflow_store(app) is store
