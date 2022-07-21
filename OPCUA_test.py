import asyncio
from asyncua import Client, Node, ua
 
async def main():
    url = 'opc.tcp://130.194.128.134:49320'
    async with Client(url=url) as client:
 
        node_bedTemp = client.get_node('ns=4;s=P1d_bedTemp')
        P1d_bedTemp = await node_bedTemp.get_value();
        print(P1d_bedTemp)
        print(type(P1d_bedTemp))
 
if __name__ == '__main__':
    asyncio.run(main())
