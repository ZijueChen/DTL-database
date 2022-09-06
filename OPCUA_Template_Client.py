# OPC UA Octoprint API Client 
# Written by Keenan Granland Aug 2022

import asyncio
from asyncua import Client, Node, ua
import logging
from turtle import delay
import requests
import time


logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger('asyncua')

async def main():
    urlOPCUA = 'oct.tpc://172.31.1.236:4840/server/' #OPC UA Server Endpoint

    # Variables    
    delay = 0.5
    printjobstarted=0
    cooldown = 0
     
    async with Client(url=urlOPCUA) as client:
        # Initalise OPCUA Variables 
        # -Printer 3
        NODE_P3d_State = client.get_node('ns=13;s=P3d_State')
        

        while True: # Main Loop
            await asyncio.sleep(0.01)
            # Read Control Variables
            # -Printer 3 Control Variables
            P3c_Start = await NODE_P3c_Start.get_value() 
            P3c_ProgID = await NODE_P3c_ProgID.get_value() 

            #if (await NODE_P3d_State.get_value=='operational'):
            #    flag=1

            if (await NODE_P3d_State.get_value=='printing')and(printjobstarted==0):
                printjobstarted=1
                #Start entry for Job X
                #Input start time
                #INput Printer number
                #INput Printe details (stl)

            if (await NODE_P3d_State.get_value=='cooldown')and(printjobstarted==1)and(cooldown==0):
                #record time of print finish
                cooldown=1
            
            if (await NODE_P3d_State.get_value=='part on bed')and(printjobstarted==1)and(cooldown==0):
                #record time of print finish
                cooldown=1
            
            






            # -Output to OCPUA Server Example
            #await NODE_P3f_Ready.set_value(P3f_Ready,ua.VariantType.Boolean) # Indicate is a signal can be sent


        
       
            

if __name__ == '__main__':
    asyncio.run(main())