const aws = require('aws-sdk');

const connection_url = process.env.connection_url;
console.log('connection_url: ', connection_url);
const ENDPOINT = connection_url;
const client = new aws.ApiGatewayManagementApi({ endpoint: ENDPOINT });

const sendMessage = async (id, body) => {
    try {
        await client.postToConnection({
            ConnectionId: id,
            Data: Buffer.from(JSON.stringify(body)),
            
        }).promise();
    } catch (err) {
        console.error(err);
    }
};

exports.handler = async (event, context) => {
    // console.log('## ENVIRONMENT VARIABLES: ' + JSON.stringify(process.env));
    // console.log('## EVENT: ' + JSON.stringify(event));
    
    if (!event.requestContext) {
        return {
            statusCode: 500,
            body: JSON.stringify(event)
        };
    }
    console.log('Request: ' + JSON.stringify(event['requestContext']));

    try {
        const connectionId = event.requestContext.connectionId;
        console.log('connectionId: ', connectionId);
        const routeKey = event.requestContext.routeKey;
        console.log('routeKey: ', routeKey);
        const body = JSON.parse(event.body || '{}');
        console.log('body: ', body);
        console.log('msgId: ', body['msgId']);
        let msgId = body['msgId'];

        switch(routeKey) {
            case '$connect':
                console.log('new connection!');
                break;
            case '$disconnect':
                console.log('the session was disconnected!');
                break;
            case '$default':
                await sendMessage(connectionId, {'msgId': msgId, 'msg': `First: Great!`})
                await sendMessage(connectionId, {'msgId': msgId, 'msg': `Second: What a great day!!`})
                
                break;
        }
    } catch (err) {
        console.error(err);
    } 

    const response = {
        statusCode: 200,
        body: "Ok" 
    };
    return response;
};