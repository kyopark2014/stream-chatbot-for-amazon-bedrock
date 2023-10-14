# Amazon Bedrock을 이용하여 Stream 기반의 한국어 Chatbot 구현하기 

[2023년 9월 Amazon Bedrock의 상용](https://aws.amazon.com/ko/about-aws/whats-new/2023/09/amazon-bedrock-generally-available/)으로 [Amazon Titan](https://aws.amazon.com/ko/bedrock/titan/), [Anthropic Claude](https://aws.amazon.com/ko/bedrock/claude/)등의 다양한 LLM (Large Language Model)을 편리하게 사용할 수 있습니다. 특히 Anthropic의 Claude 모델은 한국어를 비교적 잘 지원하고 있습니다. Chatbot과 원활한 대화를 위해서는 사용자의 질문(Question)에 대한 전체 답변(Answer)을 얻을 때까지 기다리기 보다는 [Stream 형태](https://blog.langchain.dev/streaming-support-in-langchain/)로 대화하듯이 보여주는것이 사용성에서 좋습니다. 본 게시글에서는 [Amazon Bedrock](https://aws.amazon.com/ko/bedrock/)을 사용하여 Stream을 지원하는 Chatbot을 만드는 방법을 설명합니다. 

Stream 방식은 하나의 요청에 여러번의 응답을 얻게 되므로, HTTP 방식보다는 세션을 통해 메시지를 교환하는 Websocket 방식이 유용합니다. 또한 서버리스(serverless) 아키텍처를 사용하면 인프라의 유지보수에 대한 부담없이 인프라를 효율적으로 관리할 수 있습니다. 여기서는 서버리스인 [Amazon API Gateway를 이용해 Client와 Websocket을 연결](https://docs.aws.amazon.com/ko_kr/apigateway/latest/developerguide/apigateway-websocket-api-overview.html)하고 [AWS Lambda](https://aws.amazon.com/ko/pm/lambda/?nc1=h_ls)를 이용하여 세션을 관리합니다. 본 게시글에서 사용하는 Client는 Web으로 제공되므로, 채팅 이력은 로컬 디바이스가 아니라 서버에 저정되게 됩니다. [Amazon DynamoDB](https://aws.amazon.com/ko/dynamodb/)는 Json형태로 채팅이력을 저장하는데 유용합니다. 이와같이 Client에서는 로그인시 DynamoDB에 저장된 채팅이력을 로드하여 보여줍니다. 또한 채팅이력은 LLM에 질의시에도 유용하게 사용되므로, Lambda는 채팅시작시에 사용자 아이디를 이용하여 DynamoDB에서 채팅이력을 로드하여 로컬 메모리에 저장하여 활용하며, 대화이력을 DynamoDB에 저장합니다.

전체적인 Architecture는 아래와 같습니다.

유연한 대화를 위해서는 채팅이력을 포함하여 데이터 처리하는것이 필요하므로, 채팅이력은 Amazon DynamoDB에 저장되어 LLM이 좀더 적절한 답변을 할 수 있도록 합니다. 


1) CloudFront 주소로 사용자가 접속하면 Amazon S3에서 관련된 리소르를 읽어와서 화면에 보여줍니다. 이때 로그인을 수행하고 채팅 화면으로 진입합니다.

2) 사용자 아이디로 저장된 채팅 이력을 Lambda (history)를 통해 질의하여 Amazon DynamoDB에서 가져옵니다.

3) 사용자가 채팅에서 메시지를 입력하면 API Gateway와 Websocket으로 세션을 연결하고 메시지를 전송합니다. Lambda (chat)은 Websocket connection event를 받으면 API Gateway와 세션을 연결합니다. 이후 DynamoDB에 기존 채팅이력이 있는지 확인하여 있다면, 채팅 메모리에 저장하고 Amazon Bedrock으로 사용자의 질문(query)와 채팅이력(chat history)를 전달합니다.

4) Amazon Bedrock은 사용자의 질문과 채팅이력을 이용하여 적절한 답변(answer)를 구하여 사용자에게 전달합니다. 여기에서는 한글 성능이 우수한 Anthropic의 Claude 모델을 사용하였습니다. 

![image](https://github.com/kyopark2014/stream-chatbot-for-amazon-bedrock/assets/52392004/6e0e5f54-f455-4d65-95ed-438c89baafed)


## 서버리스 기반의 Websocket 사용하기

API Gateway V2에서 Websocket을 지원하고 있으므로, Lambda와 함께 Stream을 지원하는 Chatbot을 만듧니다.

Langchain을 사용하도록 Bedrock 설정시 아래와 같이 streaming을 enable 시키고 StreamingStdOutCallbackHandler을 등록합니다.

```python
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

llm = Bedrock(
    model_id=modelId, 
    client=boto3_bedrock, 
    streaming=True,
    callbacks=[StreamingStdOutCallbackHandler()],
    model_kwargs=parameters)
```

본 게시글에서는 LLM에서 어플리케이션을 편리하게 만드는 프레임워크인 [LangChain](https://docs.langchain.com/docs/)을 사용하여 streaming을 처리합니다. 이때 채팅이려까지 고려하기 위하여, ConversationChain을 이용하여 사용자의 질문에 대한 답변을 stream으로 얻습니다. 채팅이력은 ConversationBufferMemory을 이용하여 chat_memory로 설정한 후에 ConversationChain을 정의하여 사용합니다.

```python
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain

chat_memory = ConversationBufferMemory(human_prefix='Human', ai_prefix='Assistant')
conversation = ConversationChain(llm=llm, verbose=False, memory=chat_memory)
```
사용자가 보낸 메시지가 Websocket을 이용하여 API Gateway를 거쳐서 Lambda (chat)에 전달되면, Lambda에서는 아래와 같이 event에서 connectionId와 routeKey를 추출할 수 있습니다. routeKey가 "default"일때 사용자게 보낸 메시지가 들어오는데 여기서 'body"를 추출하여, json포맷의 데이터에서 사용자의 입력인 'text'를 추출합니다. 이후 conversation을 이용하여 LLM으로 부터 응답을 구합니다. 

```python
def lambda_handler(event, context):
    if event['requestContext']: 
        connectionId = event['requestContext']['connectionId']
        print('connectionId: ', connectionId)
        routeKey = event['requestContext']['routeKey']
        print('routeKey: ', routeKey)

        if routeKey == '$connect':
            print('connected!')
        elif routeKey == '$disconnect':
            print('disconnected!')
        else:   # $default
            jsonBody = json.loads(event.get("body", ""))
            text = jsonBody['body']

        stream = conversation.predict(input=text)
        msg = readStreamMsg(connectionId, requestId, msg)
```

이때 stream은 아래와 같이 event를 추출한 후에 Websocket을 이용하여 client로 전달합니다. 

```python
def readStreamMsg(connectionId, requestId, stream):
    msg = ""
    if stream:
        for event in stream:
            msg = msg + event

            result = {
                'request_id': requestId,
                'msg': msg
            }
            #print('result: ', json.dumps(result))
            sendMessage(connectionId, result)
    return msg
```

client에 메시지를 보내기 위해 post_to_connection을 이용하여 websocket을 이용합니다.AWS CDK로 인프라설치시 얻은 connection url로 연결을 시도합니다.


```python
import boto3
client = boto3.client('apigatewaymanagementapi', endpoint_url=connection_url)

def sendMessage(id, body):
    try:
        client.post_to_connection(
            ConnectionId=id, 
            Data=json.dumps(body)
        )
    except: 
        raise Exception ("Not able to send a message")
```

## 직접 실습 해보기

### 사전 준비 사항

이 솔루션을 사용하기 위해서는 사전에 아래와 같은 준비가 되어야 합니다.

- [AWS Account 생성](https://repost.aws/ko/knowledge-center/create-and-activate-aws-account)


### CDK를 이용한 인프라 설치
[인프라 설치](https://github.com/kyopark2014/stream-chatbot-for-amazon-bedrock/blob/main/deployment.md)에 따라 CDK로 인프라 설치를 진행합니다. 


