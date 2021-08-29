from spade import quit_spade
import time
import datetime
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, PeriodicBehaviour
from spade.template import Template
from spade.message import Message
import sys
import pandas as pd
import logging
import argparse
import operative_functions as opf
import os
import json
import socket


class WarehouseAgent(Agent):
    class WHBehav(CyclicBehaviour):
        async def run(self):
            global wh_status_var, my_full_name, wh_status_started_at, stop_time, my_dir, wait_msg_time, ip_machine
            
            """inform log of status"""
            wh_activation_json = opf.activation_df(my_full_name, wh_status_started_at)
            wh_msg_log = opf.msg_to_log(wh_activation_json, my_dir)
            await self.send(wh_msg_log)
            
            "Ask browser to search"  
            if (wh_search != "No")&(datetime.datetime.now() < searching_time):
                msg_to_search = 'Search:' + wh_search + ':' + my_full_name
                order_to_search_json = opf.search_br(my_full_name, msg_to_search).to_json(orient="records")
                wh_search_browser = opf.order_to_search(order_to_search_json, my_full_name, my_dir)
                await self.send(wh_search_browser)
                
            "Ask browser to delete order in register"
            if (wh_delete != "No")&(datetime.datetime.now() < searching_time):
                wh_delete_order = opf.order_to_erase(wh_delete, my_full_name, my_dir)
                await self.send(wh_delete_order)
            "Register as active agent"    
            msg = await self.receive(timeout=wait_msg_time)
            if msg:
                single = msg.body.split(":")
                if single[0] == "Alive":
                    msg_aa_response = f'ActiveAgent: agent_name:{my_full_name}, active_time:{wh_status_started_at}'                    
                    response_active = opf.msg_to_log(msg_aa_response, my_dir)
                    await self.send(response_active)
                elif single[0] == "Search requested":
                    print(msg.body)
            if wh_status_var == "on":
                """inform log of status"""
                wh_inform_json = opf.inform_log_df(my_full_name, wh_status_started_at, wh_status_var).to_json()
                wh_msg_log = opf.msg_to_log(wh_inform_json, my_dir)
                await self.send(wh_msg_log)
                ca_wh_msg = await self.receive(timeout=wait_msg_time)  # wait for a message for 5 seconds
                if ca_wh_msg:
                    ca_data_df = pd.read_json(ca_wh_msg.body)
                    if ca_data_df.loc[0, 'action'] == "book":
                        """Prepare reply to ca of availability"""
                        wh_msg_ca = opf.msg_to_sender(ca_wh_msg)
                        """Evaluate capacity"""
                        wh_msg_ca.body = opf.wh_capacity_check(my_full_name, my_dir)
                        await self.send(wh_msg_ca)
                        """Append booking if available"""
                        if wh_msg_ca.body == "positive":  # if negative, nothing, ca will send a list of the asked wh and the booked one to log. That way we can trace if wh_x was available or not.
                            wh_inform_log_json = opf.wh_append_booking(my_full_name, my_dir, ca_data_df)
                            wh_msg_log = opf.msg_to_log(wh_inform_log_json, my_dir)
                        await self.send(wh_msg_log)  # inform log
                    elif ca_data_df.loc[0, 'action'] == "out":
                        """inform log"""
                        wh_inform_log_json = opf.wh_register(my_full_name, ca_data_df)  # Register coil exit
                        wh_msg_log = opf.msg_to_log(wh_inform_log_json, my_dir)  # inform json of coil exit
                        await self.send(wh_msg_log)
                    elif ca_data_df.loc[0, 'action'] == "in":
                        """inform log"""
                        wh_inform_log_json = opf.wh_register(my_full_name, ca_data_df)  # Register coil entrance
                        wh_msg_log = opf.msg_to_log(wh_inform_log_json, my_dir)
                        await self.send(wh_msg_log)
                    else:
                        """inform log"""
                        ca_id = ca_data_df.loc[0, 'id']
                        wh_msg_log_body = f'{ca_id} did not set a correct action'
                        wh_msg_log = opf.msg_to_log(wh_msg_log_body, my_dir)
                        await self.send(wh_msg_log)
                else:
                    """inform log"""
                    time.sleep(5)
                    coil_msg_log_body = f'{my_full_name} did not receive any msg in the last {wait_msg_time}s at {wh_status_var}'
                    coil_msg_log = opf.msg_to_log(coil_msg_log_body, my_dir)
                    await self.send(coil_msg_log)
            elif wh_status_var == "stand-by":  # stand-by status for WH is not very useful, just in case we need the agent to be alive, but not operative. At the moment, it won      t change to stand-by.
                """inform log of status"""
                wh_inform_json = opf.inform_log_df(my_full_name, wh_status_started_at, wh_status_var).to_json()
                wh_msg_log = opf.msg_to_log(wh_inform_json, my_dir)
                await self.send(wh_msg_log)
                # We could introduce here a condition to be met to change to "on"
                # now it just changes directly to auction
                """inform log of status"""
                wh_status_var = "on"
                wh_inform_json = opf.inform_log_df(my_full_name, wh_status_started_at, wh_status_var).to_json()
                wh_msg_log = opf.msg_to_log(wh_inform_json, my_dir)
                await self.send(wh_msg_log)
            else:
                """inform log of status"""
                wh_inform_json = opf.inform_log_df(my_full_name, wh_status_started_at, wh_status_var).to_json()
                wh_msg_log = opf.msg_to_log(wh_inform_json, my_dir)
                await self.send(wh_msg_log)
                wh_status_var = "stand-by"
        async def on_end(self):
            await self.agent.stop()

        async def on_start(self):
            self.counter = 1

    async def setup(self):
        b = self.WHBehav()
        template = Template()
        template.metadata = {"performative": "inform"}
        self.add_behaviour(b, template)


if __name__ == "__main__":
    """Parser parameters"""
    parser = argparse.ArgumentParser(description='wh parser')
    parser.add_argument('-an', '--agent_number', type=int, metavar='', required=False, default=1, help='agent_number: 1,2,3,4..')
    parser.add_argument('-w', '--wait_msg_time', type=int, metavar='', required=False, default=20, help='wait_msg_time: time in seconds to wait for a msg. Purpose of system monitoring')
    parser.add_argument('-st', '--stop_time', type=int, metavar='', required=False, default=84600, help='stop_time: time in seconds where agent isnt asleep')
    parser.add_argument('-s', '--status', type=str, metavar='', required=False, default='stand-by', help='status_var: on, stand-by, Off')
    parser.add_argument('--search', type=str, metavar='', required=False, default='No',help='Search order by code. Write depending on your case: aa=list (list active agents), oc(order_code), sg(steel_grade), at(average_thickness),wi(width_coils), ic(id_coil), so(string_operations), date. Example: --search oc=987')
    parser.add_argument('-set', '--search_time', type=int, metavar='', required=False, default=20, help='search_time: time in seconds where agent is searching by code')
    parser.add_argument('-do', '--delete', type=str, metavar='', required=False, default='No', help='Delete order in register given a code to filter')
    args = parser.parse_args()                     
    my_dir = os.getcwd()
    my_name = os.path.basename(__file__)[:-3]
    my_full_name = opf.my_full_name(my_name, args.agent_number)
    wait_msg_time = args.wait_msg_time
    wh_status_started_at = datetime.datetime.now().time()
    wh_status_refresh = datetime.datetime.now() + datetime.timedelta(seconds=5)
    wh_status_var = args.status
    wh_search = args.search
    wh_delete = args.delete
    searching_time = datetime.datetime.now() + datetime.timedelta(seconds=args.search_time)
    
    "IP"
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip_machine = s.getsockname()[0]
    
    """Save to csv who I am"""
    opf.set_agent_parameters(my_dir, my_name, my_full_name)
    #opf.wh_create_register(my_dir, my_full_name)  # register to store entrance and exit
    
    """XMPP info"""
    wh_jid = opf.agent_jid(my_dir, my_full_name)
    wh_passwd = opf.agent_passwd(my_dir, my_full_name)
    wh_agent = WarehouseAgent(wh_jid, wh_passwd)
    future = wh_agent.start(auto_register=True)
    future.result()
    
    """Counter"""
    stop_time = datetime.datetime.now() + datetime.timedelta(seconds=args.stop_time)
    while datetime.datetime.now() < stop_time:
        time.sleep(1)
    else:
        wh_status_var = "off"
        wh_agent.stop()
        quit_spade()

