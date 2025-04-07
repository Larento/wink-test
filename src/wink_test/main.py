from fastapi import FastAPI, Response, status

from wink_test.routers import balancer_api

app = FastAPI()


@app.get("/health")
def health_check():
    return Response(status_code=status.HTTP_200_OK)


app.include_router(balancer_api.router)
