# FixOps

docker run -p 6379:6379 redis

python -m uvicorn main:app --reload

rq worker logs --worker-class rq.worker.SimpleWorker

rq worker analysis --worker-class rq.worker.SimpleWorker