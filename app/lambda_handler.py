import json


##############################################################################################################
# UN-COMMENT ONE OF THE SECTIONS BELOW
##############################################################################################################


##############################################################################################################
# EventBridge Scheduled Lambda Function Handling
##############################################################################################################
def lambda_handler(event, context):
    print("Event Bridge Hello World")
    
    # EventBridge Handling
    _handle_event_from_eventbridge(event)

    return {"statusCode": 200, "body": "Done"}


def _handle_event_from_eventbridge(event):
    # The event object contains the payload message from eventbridge
    # ... do something with it here
    pass


# ##############################################################################################################
# # SQS Triggered Lambda Function Handling
# ##############################################################################################################
# def lambda_handler(event, context):
#     print("SQS Triggered Hello World")

#     # SQS Trigger Handling
#     _handle_event_from_sqs_trigger(event)

#     return {"statusCode": 200, "body": "Done"}


# def _handle_event_from_sqs_trigger(event):
#     for record in event["Records"]:
#         # Often messages are json and can be handled like this
#         body = json.loads(record["body"])
#         print(body)
#         # ... do something something with this message


# ##############################################################################################################
# # API Gateway Handling
# ##############################################################################################################
# from mangum import Mangum
# import uvicorn
# from fastapi import APIRouter, FastAPI, status
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.middleware.gzip import GZipMiddleware

# app = FastAPI()

# # Enable CORS for all domains
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # Allows all origins
#     allow_credentials=True,
#     allow_methods=["*"],  # Allows all methods
#     allow_headers=["*"],  # Allows all headers
# )

# # Enable gzip compression middleware
# app.add_middleware(GZipMiddleware, minimum_size=500)

# # Mangum handler with lifespan="off"
# lambda_handler = Mangum(app, lifespan="off")

# # NOTE: This would typically be in another file like api/healthcheck_api.py
# #       but is included here to simplify the template - move it to an appropriate place
# #       for your production code
# heathcheck_api_router = APIRouter()
# @heathcheck_api_router.get("/healthcheck", status_code=status.HTTP_200_OK)
# def healthcheck():
#     print("healthcheck")
#     return {"healthcheck": "Everything is OK!"}

# app.include_router(heathcheck_api_router)


# if __name__ == "__main__":
#     uvicorn.run(app, host="0.0.0.0", port=8080)
