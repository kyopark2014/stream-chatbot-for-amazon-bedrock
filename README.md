# Amazon Bedrock을 이용하여 Stream 방식의 한국어 Chatbot 구현하기 

[2023년 9월 Amazon Bedrock의 상용](https://aws.amazon.com/ko/about-aws/whats-new/2023/09/amazon-bedrock-generally-available/)으로 [Amazon Titan](https://aws.amazon.com/ko/bedrock/titan/), [Anthropic Claude](https://aws.amazon.com/ko/bedrock/claude/)등의 다양한 LLM (Large Language Model)을 AWS 환경에서 편리하게 사용할 수 있습니다. 특히 Anthropic의 Claude 모델은 한국어를 비교적 잘 지원하고 있습니다. Chatbot과 원활한 대화를 위해서는 사용자의 질문(Question)에 대한 전체 답변(Answer)을 얻을 때까지 기다리기 보다는 [Stream 형태](https://blog.langchain.dev/streaming-support-in-langchain/)로 대화하듯이 보여주는것이 사용성에서 좋습니다. 본 게시글에서는 [Amazon Bedrock](https://aws.amazon.com/ko/bedrock/)을 사용하여 Stream을 지원하는 한국어 Chatbot을 만드는 방법을 설명합니다. 

Stream 방식은 하나의 요청에 여러번의 응답을 얻게 되므로, HTTP 방식보다는 세션을 통해 메시지를 교환하는 Websocket 방식이 유용합니다. 또한 서버리스(serverless) 아키텍처를 사용하면 인프라의 유지보수에 대한 부담없이 인프라를 효율적으로 관리할 수 있습니다. 여기서는 서버리스인 [Amazon API Gateway를 이용해 Client와 Websocket을 연결](https://docs.aws.amazon.com/ko_kr/apigateway/latest/developerguide/apigateway-websocket-api-overview.html)하고 [AWS Lambda](https://aws.amazon.com/ko/pm/lambda/?nc1=h_ls)를 이용하여 세션을 관리합니다. 본 게시글에서 사용하는 Client는 Web으로 제공되고, 채팅 이력은 로컬 디바이스가 아니라 서버에 저정되게 됩니다. [Amazon DynamoDB](https://aws.amazon.com/ko/dynamodb/)는 Json형태로 채팅이력을 저장하는데 유용합니다. 이와같이 Client에서는 로그인시에 DynamoDB에 저장된 채팅이력을 로드하여 보여줍니다. 또한 채팅이력은 LLM의 질의시에도 유용하게 사용되므로, Lambda는 채팅시작시에 사용자 아이디를 이용하여 DynamoDB에서 채팅이력을 로드하여 로컬 메모리에 저장하여 활용합니다. 


## Architecture 개요

전체적인 Architecture는 아래와 같습니다. 유연한 대화를 위해서는 채팅이력을 포함하여 데이터 처리하는것이 필요하므로, 채팅이력은 Amazon DynamoDB에 저장되어 LLM이 좀더 적절한 답변을 할 수 있도록 합니다. 

1) CloudFront 주소로 사용자가 접속하면 Amazon S3에서 관련된 리소르를 읽어와서 브라우저 화면에 보여줍니다. 이때 로그인을 수행하고 채팅 화면으로 진입합니다.

2) 사용자 아이디를 이용하여 DynamoDB에 저장된 채팅 이력을 API Gateway와 Lambda-history를 통해 읽어옵니다.

3) 사용자가 채팅에서 메시지를 입력하면 API Gateway와 Websocket으로 세션을 연결하고 메시지를 전송합니다. Lambda-chat-ws은 Websocket connection event를 받으면 API Gateway와 연결하여 메시지를 수신합니다.
  
4) Lambda-chat은 DynamoDB의 기존 채팅이력을 읽어와서, 채팅 메모리에 저장합니다.

5) Lambda-chat은 사용자의 질문(question)과 채팅이력(chat history)을 LLM에 전달합니다. 

7) Amazon Bedrock의 Anthropic LLM은 사용자의 질문과 채팅이력을 이용하여 적절한 답변(answer)를 생선한 후에 사용자에게 전달합니다. 여기에서는 한글 성능이 우수한 Anthropic의 Claude 모델을 사용하였습니다. 

![image](https://github.com/kyopark2014/stream-chatbot-for-amazon-bedrock/assets/52392004/6e0e5f54-f455-4d65-95ed-438c89baafed)


## 주요 시스템 구성

### 서버리스 기반으로 Websocket 연결하기

[Client](./html/chat.js)는 서버리스인 API Gateway를 이용하여 [Websocket과 연결](https://docs.aws.amazon.com/ko_kr/apigateway/latest/developerguide/apigateway-websocket-api-overview.html)합니다. 이때 client가 연결하는 endpoint는 API Gateway 주소입니다. 아래와 같이 WebSocket을 선언한 후에 onmessage로 메시지가 들어오면, event의 'data'에서 메시지를 추출합니다. 세션을 유지하기 위해 일정간격으로 keep alive 동작을 수행합니다. 

```java
const ws = new WebSocket(endpoint);

ws.onmessage = function (event) {        
    response = JSON.parse(event.data)

    if(response.request_id) {
        addReceivedMessage(response.request_id, response.msg);
    }
};

ws.onopen = function () {
    isConnected = true;
    if(type == 'initial')
        setInterval(ping, 57000); 
};

ws.onclose = function () {
    isConnected = false;
    ws.close();
};
```

발신 메시지는 JSON 포맷으로 아래와 같이 userId, 요청시간, 메시지 타입과 메시지를 포함합니다. 발신시 [websocket의 send()](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket/send)을 이용하여 아래와 같이 발신합니다. 만약 발신시점에 세션이 연결되어 있지 않다면 연결하고 재시도 하도록 알림을 표시합니다.

```java
sendMessage({
    "user_id": userId,
    "request_id": requestId,
    "request_time": requestTime,        
    "type": "text",
    "body": message.value
})

webSocket = connect(endpoint, 'initial');
function sendMessage(message) {
    if(!isConnected) {
        webSocket = connect(endpoint, 'reconnect');
        
        addNotifyMessage("재연결중입니다. 잠시후 다시시도하세요.");
    }
    else {
        webSocket.send(JSON.stringify(message));     
    }     
}
```

### Stream 사용하기

[lambda-chat-ws](./lambda-chat-ws/lambda_function.py)에서는 Bedrock을 사용하기 위하여 [Boto3로 Bedrock client](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock.html)를 정의합니다. 여기서는 Chatbot은 서울리전을 사용하고, Bedrock은 N.Virginia (us-east-1)을 사용합니다.

```python
import boto3

boto3_bedrock = boto3.client(
    service_name='bedrock-runtime',
    region_name=bedrock_region,
)
```

아래와 같이 LLM에서 어플리케이션을 편리하게 만드는 프레임워크인 [LangChain](https://docs.langchain.com/docs/)을 사용하여 [Bedrock](https://python.langchain.com/docs/integrations/llms/bedrock)을 정의합니다. 이때 stream으로 출력을 보여줄 수 있도록 streaming을 True로 설정합니다. 또한 StreamingStdOutCallbackHandler을 callback으로 등록합니다.

```python
from langchain.llms.bedrock import Bedrock
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

llm = Bedrock(
    model_id=modelId, 
    client=boto3_bedrock, 
    streaming=True,
    callbacks=[StreamingStdOutCallbackHandler()],
    model_kwargs=parameters)
```

채팅이력은 [ConversationBufferMemory](https://api.python.langchain.com/en/latest/memory/langchain.memory.buffer.ConversationBufferMemory.html)을 이용하여 chat_memory으로 저장합니다.

```python
from langchain.memory import ConversationBufferMemory
chat_memory = ConversationBufferMemory(human_prefix='Human', ai_prefix='Assistant')
```

채팅이력까지 고려한 응답을 구하기 위하여, [ConversationChain](https://js.langchain.com/docs/api/chains/classes/ConversationChain)을 이용합니다. 사용자가 Websocket을 이용하여 API Gateway로 보낸 메시지가 Lambda-chat에 전달되면, Lambda에서는 아래와 같이 event에서 connectionId와 routeKey를 추출할 수 있습니다. routeKey가 "default"일때 사용자게 보낸 메시지가 들어오는데 여기서 'body"를 추출하여, json포맷의 데이터에서 사용자의 입력인 'text'를 추출합니다. 이후 conversation을 이용하여 LLM으로 부터 응답을 구합니다. 

```python
from langchain.chains import ConversationChain
conversation = ConversationChain(llm=llm, verbose=False, memory=chat_memory)

def lambda_handler(event, context):
    if event['requestContext']: 
        connectionId = event['requestContext']['connectionId']
        routeKey = event['requestContext']['routeKey']

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
            sendMessage(connectionId, result)
    return msg

def sendMessage(id, body):
    try:
        client.post_to_connection(
            ConnectionId=id, 
            Data=json.dumps(body)
        )
    except: 
        raise Exception ("Not able to send a message")
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


