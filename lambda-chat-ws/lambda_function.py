import json
import boto3
import os
import time
import datetime
from io import BytesIO
import PyPDF2
import csv
import sys
import re

from langchain.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from langchain.chains.summarize import load_summarize_chain
from langchain.llms.bedrock import Bedrock
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory



# websocket
connection_url = os.environ.get('connection_url')
client = boto3.client('apigatewaymanagementapi', endpoint_url=connection_url)
print('connection_url: ', connection_url)

def sendMessage(id, body):
    try:
        client.post_to_connection(
            ConnectionId=id, 
            Data=json.dumps(body)
        )
    except: 
        raise Exception ("Not able to send a message")



"""
def lambda_handler(event, context):
    print(event)
    
    if event['requestContext']: 
        connectionId = event['requestContext']['connectionId']
        print('connectionId: ', connectionId)
        routeKey = event['requestContext']['routeKey']
        print('routeKey: ', routeKey)
        
        if routeKey == '$connect':
            print('connected!')
        elif routeKey == '$disconnect':
            print('disconnected!')
        else:
            print('routeKey: ', routeKey)
            reqBody = json.loads(event['body'])
            print('reqBody: ', reqBody)
            
            msg = getResponse(reqBody)

            userId  = reqBody['user_id']
            requestId  = reqBody['request_id']
            requestTime  = reqBody['request_time']
            type  = reqBody['type']
            result = {
                'user_id': userId, 
                'request_id': requestId,
                'request_time': requestTime,
                'type': type,
                'msg': msg
            }
            print('result: ', json.dumps(result))
            sendMessage(connectionId, result)

    return {
        'statusCode': 200,
        'msg': routeKey,
    }
"""
def lambda_handler(event, context):
    print('event: ', event)

    if event['requestContext']: 
        connectionId = event['requestContext']['connectionId']
        print('connectionId: ', connectionId)
        routeKey = event['requestContext']['routeKey']
        print('routeKey: ', routeKey)
        
        if routeKey == '$connect':
            print('connected!')
        elif routeKey == '$disconnect':
            print('disconnected!')
        else:
            body = json.loads(event['body'])
            print('body: ', body)
            msgId = body['msgId']

            msg = {'msgId': msgId, 'msg': 'First: Great!'}
            sendMessage(connectionId, msg)
            msg = {'msgId': msgId, 'msg': "Second: What a great day!!"}
            sendMessage(connectionId, msg)                     

    return {
        'statusCode': 200,
        #'msg': msg,
    }
