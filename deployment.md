# CDK를 이용한 인프라 설치하기

여기서는 [Cloud9](https://aws.amazon.com/ko/cloud9/)에서 [AWS CDK](https://aws.amazon.com/ko/cdk/)를 이용하여 인프라를 설치합니다.

1) [Cloud9 Console](https://ap-northeast-2.console.aws.amazon.com/cloud9control/home?region=ap-northeast-2#/create)에 접속하여 [Create environment]-[Name]에서 “chatbot”으로 이름을 입력하고, EC2 instance는 “m5.large”를 선택합니다. 나머지는 기본값을 유지하고, 하단으로 스크롤하여 [Create]를 선택합니다.

![noname](https://github.com/kyopark2014/chatbot-based-on-Falcon-FM/assets/52392004/7c20d80c-52fc-4d18-b673-bd85e2660850)

2) [Environment](https://ap-northeast-2.console.aws.amazon.com/cloud9control/home?region=ap-northeast-2#/)에서 “chatbot”를 [Open]한 후에 아래와 같이 터미널을 실행합니다.

![noname](https://github.com/kyopark2014/chatbot-based-on-Falcon-FM/assets/52392004/b7d0c3c0-3e94-4126-b28d-d269d2635239)

3) EBS 크기 변경

아래와 같이 스크립트를 다운로드 합니다. 

```text
curl https://raw.githubusercontent.com/kyopark2014/technical-summary/main/resize.sh -o resize.sh
```

이후 아래 명령어로 용량을 80G로 변경합니다.
```text
chmod a+rx resize.sh && ./resize.sh 80
```


4) 소스를 다운로드합니다.

```java
git clone https://github.com/kyopark2014/stream-chatbot-for-amazon-bedrock
```

5) cdk 폴더로 이동하여 필요한 라이브러리를 설치합니다.

```java
cd stream-chatbot-for-amazon-bedrock/cdk-stream-chatbot/ && npm install
```

7) CDK 사용을 위해 Boostraping을 수행합니다.

아래 명령어로 Account ID를 확인합니다.

```java
aws sts get-caller-identity --query Account --output text
```

아래와 같이 bootstrap을 수행합니다. 여기서 "account-id"는 상기 명령어로 확인한 12자리의 Account ID입니다. bootstrap 1회만 수행하면 되므로, 기존에 cdk를 사용하고 있었다면 bootstrap은 건너뛰어도 됩니다.

```java
cdk bootstrap aws://account-id/ap-northeast-2
```

8) 인프라를 설치합니다.

```java
cdk deploy --all
```

9) 아래와 같이 webSocketUrl을 확인합니다. 여기서는 "wss://etl2hxx4la.execute-api.ap-northeast-1.amazonaws.com/dev" 입니다.

![noname](https://github.com/kyopark2014/stream-chatbot-for-amazon-bedrock/assets/52392004/12d900e6-ec6c-40de-b867-284612ecbb4f)

10) 아래와 같이 "/html/chat.js"파일을 열어서, endpoint를 업데이트합니다.

![noname](https://github.com/kyopark2014/stream-chatbot-for-amazon-bedrock/assets/52392004/99e03119-e8f8-4961-ab13-6f9bb149acbe)

11) 아래와 같이 "UpdateCommendforstreamchatbotsimple"에 있는 명령어를 확인합니다.

![noname](https://github.com/kyopark2014/stream-chatbot-for-amazon-bedrock/assets/52392004/04e72e5f-7f99-440e-a111-c50fad988b3c)

아래와 같이 명령어를 입력합니다. 여기서는 "aws s3 cp ../html/chat.js s3://storage-for-stream-chatbot-simple-ap-northeast-1"를 이용합니다.

![image](https://github.com/kyopark2014/stream-chatbot-for-amazon-bedrock/assets/52392004/bf9e0d0a-cdc8-4931-8a20-182a89aded06)

12) 설치가 완료되면 브라우저에서 아래와 같이 WebUrl를 확인하여 브라우저를 이용하여 접속합니다.

![noname](https://github.com/kyopark2014/stream-chatbot-for-amazon-bedrock/assets/52392004/c2261bd4-1dcf-460d-bfed-a80780f396e8)
