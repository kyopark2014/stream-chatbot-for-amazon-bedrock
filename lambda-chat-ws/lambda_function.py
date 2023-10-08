import json
import boto3
import time
import os

connection_url = os.environ.get('connection_url')
client = boto3.client('apigatewaymanagementapi', endpoint_url=connection_url)

def sendMessage(id, body):
    try:
        client.post_to_connection(
            ConnectionId=id, 
            Data=json.dumps(body)
        )
    except: 
        raise Exception ("Not able to send a message")
    
def lambda_handler(event, context):
    print(event)

    if event['requestContext']: 
        connectionId = event['requestContext']['connectionId']
        print('connectionId: ', connectionId)
        routeKey = event['requestContext']['routeKey']
        print('routeKey: ', routeKey)
        body = json.loads(event['body'])
        print('body: ', body)
        msgId = body['msgId']

    if routeKey == '$connect':
        print('connected!')
    elif routeKey == '$disconnect':
        print('disconnected!')
    else:
        msg = {'msgId': msgId, 'msg': "First: Great!"}
        sendMessage(connectionId, msg)
        msg = {'msgId': msgId, 'msg': "Second: What a great day!!"}
        sendMessage(connectionId, msg)                        

    return {
        'statusCode': 200,
        #'msg': msg,
    }
