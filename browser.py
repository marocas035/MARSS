from spade import quit_spade
import time
import datetime
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, PeriodicBehaviour
from spade.template import Template
from spade.message import Message
import sys
import pandas as pd
import operative_functions as opf
import argparse
import os
import socket
import json


class BrowserAgent(Agent):
    class BRBehav(CyclicBehaviour):
        async def run(self):
            global br_status_var, my_full_name, br_started_at, stop_time, my_dir, wait_msg_time, br_coil_name_int_fab, br_int_fab, br_data_df, ip_machine
            
            """inform log of status"""
            br_activation_json = opf.activation_df(my_full_name, br_started_at)
            br_msg_log = opf.msg_to_log(br_activation_json, my_dir)
            await self.send(br_msg_log)
               
            if br_status_var == "on":
                """inform log of status"""
                br_inform_json = opf.inform_log_df(my_full_name, br_started_at, br_status_var).to_json()
                br_msg_log = opf.msg_to_log(br_inform_json, my_dir)
                await self.send(br_msg_log)
                if br_int_fab == "yes":
                    """Send msg to coil that was interrupted during fab"""
                    int_fab_msg_body = opf.br_int_fab_df(br_data_df).to_json()
                    coil_jid = opf.get_agent_jid(br_coil_name_int_fab, my_dir)
                    br_coil_msg = opf.br_msg_to(int_fab_msg_body)
                    br_coil_msg.to = coil_jid
                    await self.send(br_coil_msg)
                    """inform log of event"""
                    br_msg_log_body = f'{my_full_name} send msg to {br_coil_name_int_fab} because its fab was interrupted '
                    br_msg_log = opf.msg_to_log(br_msg_log_body, my_dir)
                    await self.send(br_msg_log)
                    print(br_msg_log_body)
                msg = await self.receive(timeout=wait_msg_time)  # wait for a message for 60 seconds
                if msg:
                    agent_df = pd.read_json(msg.body)
                    msg_sender_jid0 = str(msg.sender)
                    msg_sender_jid = msg_sender_jid0[:-33]
                    if agent_df.loc[0, 'purpose'] == "delete_order":  #an agent has requested to delete a order
                        code_to_erase = single[1]
                        opf.delete_order(code_to_erase)
                        ack_change = f'Order has been deleted successfully: Code given to erase register is {code_to_erase} at {datetime.datetime.now()}'
                        change_register = opf.msg_to_log(ack_change, my_dir)
                        await self.send(change_register)
                    elif agent_df.loc[0, 'purpose'] == "contact_list":
                        r = 'Request contact list'
                        rq_contact_list = opf.rq_list_log(my_full_name, r).to_json(orient="records")   #request contact list to log 
                        request_contact_list_json = opf.contact_list_log_json(rq_contact_list, my_dir)
                        await self.send(request_contact_list_json)
                        msg_cl = await self.receive(timeout=wait_msg_time)  # wait for a message for 60 seconds
                        if msg_cl:
                            cl_df = pd.read_json(msg_cl.body)
                            if (len(cl_df.columns)) == 5:
                                contact_list = cl_df.loc[0, 'msg1']
                                active_coil_df = cl_df.loc[0, 'msg2']
                                if msg_sender_jid == "launch":
                                    cl_to_agent = opf.rec_list_la(my_full_name, contact_list, active_coil_df).to_json(orient="records")
                                    cl_to_agent_json = opf.contact_list_la_json(cl_to_agent, my_dir)    
                                    await self.send(cl_to_agent_json) 
                                else:
                                    if agent_df.loc[0, 'purpose2'] == "contact_list":
                                        agent = agent_df.loc[0, 'id']
                                        cl_to_agent = opf.rec_list(my_full_name, contact_list,agent).to_json(orient="records")    
                                        cl_to_agent_json = opf.contact_list_json(cl_to_agent,agent, my_dir)
                                        await self.send(cl_to_agent_json)
                                        
                                        inform_log = 'requested contact list of agents in the system'
                                        inform_log_json = opf.inform_log(my_full_name,inform_log,agent).to_json(orient="records")
                                        inform_log_json_msg = opf.msg_to_log(inform_log_json,my_dir)
                                        await self.send(inform_log_json_msg)
                                    elif agent_df.loc[0, 'purpose2'] == "active_coil_df":
                                        agent = agent_df.loc[0, 'id']
                                        cl_to_agent = opf.rec_list(my_full_name,active_coil_df, agent).to_json(orient="records")
                                        cl_to_agent_json = opf.contact_list_json(cl_to_agent, agent, my_dir)
                                        await self.send(cl_to_agent_json)
                                        
                                        inform_log = 'requested dataframe of coil definition in the system'
                                        inform_log_json = opf.inform_log(my_full_name,inform_log,agent).to_json(orient="records")
                                        inform_log_json_msg = opf.msg_to_log(inform_log_json,my_dir)
                                        await self.send(inform_log_json_msg)
                            else:
                               contact_list = cl_df.loc[0, 'msg']
                               cl_to_agent = opf.rq_list_la(my_full_name, contact_list).to_json(orient="records")     
                               cl_to_agent_json = opf.contact_list_la_json(cl_to_agent, my_dir)   
                               await self.send(cl_to_agent_json)  
                    elif agent_df.loc[0, 'purpose'] == "search":    #an agent has requested a search
                        msg_search = agent_df.loc[0, 'msg']
                        single = msg_search.split(':')
                        search = single[1]
                        c = search.split('=')
                        type_code_to_search = c[0]
                        agent_search_request = single[2]
                        register = pd.read_csv('RegisterOrders.csv', header=0, delimiter=",", engine='python')              # Necessary this file needs to exist. This could be improved.
                        filter = pd.DataFrame()
                        if type_code_to_search == 'aa':
                            column = 'Null'
                            a = 'SearchAA: Request active agents list'
                            request_aa = opf.msg_to_log(a, my_dir)
                            await self.send(request_aa)
                            msg_aa = await self.receive(timeout=wait_msg_time)  # wait for a message for 60 seconds
                            if msg_aa:
                                br_msg_aa = opf.order_searched(msg_aa.body, agent_search_request, my_dir)
                                await self.send(br_msg_aa)
                        elif type_code_to_search == 'ty':
                            column = 'type'
                            code_to_search = c[1]
                        elif type_code_to_search == 'oc':
                            column = 'Order_code'
                            code_to_search = c[1]
                        elif type_code_to_search == 'sg':
                            column = 'Steel_grade'
                            code_to_search = c[1]
                        elif type_code_to_search == 'at':
                            column = 'Thickness'
                            code_to_search = float(c[1])
                        elif type_code_to_search == 'wi':
                            column = 'Width_coils'
                            code_to_search = int(c[1])
                        elif type_code_to_search == 'nc':
                            column = 'Number_coils'
                            code_to_search = int(c[1])
                        elif type_code_to_search == 'ic':
                            column = 'ID_coil'
                            code_to_search = c[1]
                        elif type_code_to_search == 'cs':
                            column = 'coil_status'
                            code_to_search = c[1]
                        elif type_code_to_search == 'so':
                            column = 'Operations'
                            code_to_search = c[1]
                        else:
                            column = 'Date'
                            code_to_search = c[1]
                        if column != 'Null':
                            filter = register.loc[register[column] == code_to_search]
                            if len(filter) == 0:
                                br_search_msg = f'error,search requested not found: code to search: {code_to_search}, agent requested search: {agent_search_request}'
                            else:
                                br_search_msg = f'code to search: {code_to_search}, agent requested search: {agent_search_request}'
                            br_msg_search_json = opf.inform_search(agent_search_request, br_search_msg)
                            inform_search_log = opf.msg_to_log(br_msg_search_json, my_dir)
                            await self.send(inform_search_log)
                            searched = filter.to_json()
                            br_msg_search_json = opf.br_msg_search_json(searched, agent_search_request).to_json(orient="records")
                            br_msg_search = opf.order_searched(br_msg_search_json, agent_search_request, my_dir)
                            br_inform_log = opf.msg_to_log(br_msg_search_json, my_dir)
                            await self.send(br_msg_search)      
                    else:
                        if msg_sender_jid == 'ca':
                            print(f'ca_br_msg: {msg.body}')
                            ca_data_df = pd.read_json(msg.body)
                            """Prepare reply"""
                            br_msg_ca = opf.msg_to_sender(msg)
                            if ca_data_df.loc[0, 'purpose'] == "request":  # If the resource requests information, browser provides it.
                                if ca_data_df.loc[0, 'request_type'] == "active users location & op_time":  # provides active users, and saves request.
                                    """Checks for active users and their actual locations and reply"""
                                    ca_name = ca_data_df.loc[0, 'agent_type']
                                    br_msg_ca_body = opf.check_active_users_loc_times(ca_name)  # provides agent_id as argument
                                    br_msg_ca.body = br_msg_ca_body
                                    print(f'br_msg_ca active users: {br_msg_ca.body}')
                                    await self.send(br_msg_ca)
                                    """Inform log of performed request"""
                                    br_msg_log = opf.msg_to_log(br_msg_ca_body, my_dir)
                                    await self.send(br_msg_log)
                                elif ca_data_df.loc[0, 'request_type'] == "coils":
                                    """Checks for active coils and their actual locations and reply"""
                                    coil_request = ca_data_df.loc[0, 'request_type']
                                    br_msg_ca_body = opf.check_active_users_loc_times(my_name,coil_request)  # specifies request as argument
                                    br_msg_ca.body = br_msg_ca_body
                                    print(f'br_msg_ca coils: {br_msg_ca.body}')
                                    await self.send(br_msg_ca)
                                    """Inform log of performed request"""
                                    br_msg_log = opf.msg_to_log(br_msg_ca_body, my_dir)
                                    await self.send(br_msg_log)
                                else:
                                    """inform log"""
                                    ca_id = ca_data_df.loc[0, 'id']
                                    br_msg_log_body = f'{ca_id} did not set a correct type of request'
                                    br_msg_log = opf.msg_to_log(br_msg_log_body, my_dir)
                                    await self.send(br_msg_log)
                            else:
                                """inform log"""
                                ca_id = ca_data_df.loc[0, 'id']
                                br_msg_log_body = f'{ca_id} did not set a correct purpose'
                                br_msg_log = opf.msg_to_log(br_msg_log_body, my_dir)
                                await self.send(br_msg_log)
                else:
                    """inform log"""
                    br_msg_log_body = f'{my_name} did not receive a message in the last {wait_msg_time}s'
                    br_msg_log_body = opf.inform_error(my_full_name,br_msg_log_body)
                    br_msg_log = opf.msg_to_log(br_msg_log_body, my_dir)
                    await self.send(br_msg_log)
            elif br_status_var == "stand-by":  # stand-by status for BR is not very useful, just in case we need the agent to be alive, but not operative. At the moment, it won      t change to stand-by.
                """inform log of status"""
                br_inform_json = opf.log_status(my_full_name, br_status_var, ip_machine)
                br_msg_log = opf.msg_to_log(br_inform_json, my_dir)
                await self.send(br_msg_log)

                """inform log of status"""
                br_status_var = "on"
                br_inform_json = opf.log_status(my_full_name, br_status_var, ip_machine)
                br_msg_log = opf.msg_to_log(br_inform_json, my_dir)
                await self.send(br_msg_log)
                br_inform_json = opf.inform_log_df(my_full_name, br_started_at, br_status_var, br_data_df).to_json(orient="records")
                br_msg_log = opf.msg_to_log(br_inform_json, my_dir)
                await self.send(br_msg_log)
            else:
                """inform log of status"""
                br_inform_json = opf.inform_log_df(my_full_name, br_started_at, br_status_var).to_json()
                br_msg_log = opf.msg_to_log(br_inform_json, my_dir)
                await self.send(br_msg_log)
                br_status_var = "stand-by"

        async def on_end(self):
            """Inform log """
            browser_msg_ended = opf.send_activation_finish(my_full_name, ip_machine, 'end')
            browser_msg_ended = opf.msg_to_log(browser_msg_ended, my_dir)
            await self.send(browser_msg_ended)
            
            '''async def unsuscribe(self):
                """Asks for unsubscription"""
                self.roster.unsubscribe(aioxmpp.JID.fromstr(log@apiict03.etsii.upm.es).bare())'''                            #TODO
                

        async def on_start(self):
            self.counter = 1
            """Inform log """
            browser_msg_start = opf.send_activation_finish(my_full_name, ip_machine, 'start')
            browser_msg_start = opf.msg_to_log(browser_msg_start, my_dir)
            await self.send(browser_msg_start)
            
            '''async def suscribe(self):
                """Asks for subscription"""
                self.roster.subscribe(aioxmpp.JID.fromstr(log@apiict03.etsii.upm.es).bare())'''

            

    async def setup(self):
        b = self.BRBehav()
        template = Template()
        template.metadata = {"performative": "inform"}
        self.add_behaviour(b, template)


if __name__ == "__main__":
    """Parser parameters"""
    parser = argparse.ArgumentParser(description='br parser')
    parser.add_argument('-an', '--agent_number', type=int, metavar='', required=False, default=1,
                        help='agent_number: 1,2,3,4..')
    parser.add_argument('-w', '--wait_msg_time', type=int, metavar='', required=False, default=60,
                        help='wait_msg_time: time in seconds to wait for a msg. Purpose of system monitoring.')
    parser.add_argument('-st', '--stop_time', type=int, metavar='', required=False, default=84600,
                        help='stop_time: time in seconds where agent isnt asleep')
    parser.add_argument('-s', '--status', type=str, metavar='', required=False, default='stand-by',
                        help='status_var: on, stand-by, Off')
    parser.add_argument('-if', '--interrupted_fab', type=str, metavar='', required=False, default='no',
                        help='interrupted_fab: yes if it was stopped. We set this while system working and will tell cn:coil_number  that its fab was stopped')
    parser.add_argument('-cn', '--coil_number_interrupted_fab', type=str, metavar='', required=False, default='no',
                        help='agent_number interrupted fab: specify which coil number fab was interrupted: 1,2,3,4.')
    #
    parser.add_argument('-se', '--search', type=str, metavar='', required=False, default='No',
                        help='Search order by code. Writte depending on your case: oc (order_code),sg(steel_grade),at(average_thickness), wi(width_coils), ic(id_coil), so(string_operations),date.Example: --search oc = 987, date.Example: --search oc = 987')
    parser.add_argument('-set', '--search_time', type=float, metavar='', required=False, default=0.3,
                        help='search_time: time in seconds where agent is searching by code')
    parser.add_argument('-do', '--delete', type=str, metavar='', required=False, default='No',
                        help='Delete order in register given a code to filter')
    args = parser.parse_args()
    my_dir = os.getcwd()
    agents = opf.agents_data()
    my_name = os.path.basename(__file__)[:-3]
    my_full_name = opf.my_full_name(my_name, args.agent_number)
    wait_msg_time = args.wait_msg_time
    br_started_at = datetime.datetime.now().time()
    br_status_var = args.status
    br_int_fab = args.interrupted_fab
    br_search = args.search
    coil_agent_name = "coil"
    br_delete = args.delete
    coil_agent_number = args.coil_number_interrupted_fab
    br_coil_name_int_fab = opf.my_full_name(coil_agent_name, coil_agent_number)
    searching_time = datetime.datetime.now() + datetime.timedelta(seconds=args.search_time)

    """Save to csv who I am"""
    br_data_df = opf.set_agent_parameters(my_dir, my_name, my_full_name)

    "IP"
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip_machine = s.getsockname()[0]

    """XMPP info"""
    br_jid = opf.agent_jid(my_dir, my_full_name)
    br_passwd = opf.agent_passwd(my_dir, my_full_name)
    br_agent = BrowserAgent(br_jid, br_passwd)
    future = br_agent.start(auto_register=True)
    future.result()

    """Counter"""
    stop_time = datetime.datetime.now() + datetime.timedelta(seconds=args.stop_time)
    while datetime.datetime.now() < stop_time:
        time.sleep(1)
    else:
        br_status_var = "off"
        br_agent.stop()
        quit_spade()
